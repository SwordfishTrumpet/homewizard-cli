"""The repository's checks are discoverable by tooling (issue #46).

`scripts/context.sh` reads commands from a root `package.json`, so without one
every pipeline gate reported "this repository defines no 'lint' command".
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_package_json_exposes_the_documented_commands():
    scripts = json.loads((ROOT / "package.json").read_text())["scripts"]
    assert "pytest tests/" in scripts["test"]
    assert "ruff check" in scripts["lint"]
    assert "mypy --check-untyped-defs" in scripts["typecheck"]
    assert "pytest" in scripts["test:fast"]


def test_package_lock_declares_npm_so_the_snapshot_reads_these_scripts():
    # context.sh resolves the package manager in a fixed order, and
    # pyproject.toml (pip) comes before nothing: the lock file is what tells it
    # to run these scripts through npm.
    lock = json.loads((ROOT / "package-lock.json").read_text())
    assert lock["lockfileVersion"] == 3
    assert lock["packages"][""]["name"] == "homewizard-cli"


# ── #31: the image is built from the checkout ─────────────────


def test_dockerfile_installs_the_build_context():
    import re

    text = (ROOT / "Dockerfile").read_text()
    assert re.search(r"^\s*(COPY|ADD)\b", text, re.MULTILINE), "no build context"
    assert re.search(r"pip[^\n;]*install[^\n;]*\s\.(?:\s|$)", text), (
        "the image must install the copied source, not a release from the index"
    )


# ── #32: the mypy hook can resolve what it checks ─────────────


def test_mypy_hook_declares_every_third_party_import():
    """#32: an isolated hook env missing a dependency fails every commit."""
    import ast
    import re
    import sys

    config = (ROOT / ".pre-commit-config.yaml").read_text()
    start = config.find("mirrors-mypy")
    assert start >= 0
    end = config.find("\n  - repo:", start)
    block = config[start : end if end > 0 else len(config)]

    declared = set()
    match = re.search(r"additional_dependencies:\s*\n((?:\s*-\s*\S+\s*\n?)+)", block)
    if match:
        for item in re.findall(r"-\s*(\S+)", match.group(1)):
            name = re.split(r"[<>=!~\[; ]", item, maxsplit=1)[0]
            declared.add(name.lower().replace("-", "_"))

    alias = {"paho": "paho_mqtt", "typing_extensions": "typing_extensions"}
    first_party = {"homewizard_cli", "tests", "conftest"}
    imported = set()
    for path in list(ROOT.glob("homewizard_cli/**/*.py")) + list(
        ROOT.glob("tests/**/*.py")
    ):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    imported.add(a.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported.add(node.module.split(".")[0])

    missing = sorted(
        name
        for name in imported
        if name not in sys.stdlib_module_names
        and name not in first_party
        and name not in declared
        and alias.get(name, name) not in declared
    )
    assert missing == [], f"mypy hook cannot import {missing}"
