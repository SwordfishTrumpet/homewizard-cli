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
