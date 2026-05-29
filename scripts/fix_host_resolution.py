"""Bulk edit script to fix host resolution in all subcommands."""

import re
from pathlib import Path

BASE = Path("/home/remcov/homewizard-cli")

# Add resolve_host to config.py
config_file = BASE / "homewizard_cli" / "config.py"
config_content = config_file.read_text()

resolve_host_func = '''

def resolve_host(host: str | None) -> str:
    """Return host from CLI arg, config file, or default."""
    if host is not None:
        return host
    cfg = load_config()
    return cfg.host or DEFAULT_HOST
'''

if "def resolve_host(" not in config_content:
    config_content = config_content.rstrip() + resolve_host_func + "\n"
    config_file.write_text(config_content)

# List of command files to modify
command_files = [
    "homewizard_cli/commands/data.py",
    "homewizard_cli/commands/power.py",
    "homewizard_cli/commands/energy.py",
    "homewizard_cli/commands/gas.py",
    "homewizard_cli/commands/quality.py",
    "homewizard_cli/commands/telegram.py",
    "homewizard_cli/commands/info.py",
    "homewizard_cli/commands/identify.py",
    "homewizard_cli/commands/system.py",
    "homewizard_cli/commands/export.py",
    "homewizard_cli/commands/dashboard.py",
    "homewizard_cli/commands/serve.py",
    "homewizard_cli/commands/reboot.py",
    "homewizard_cli/commands/pair.py",
    "homewizard_cli/commands/users.py",
    "homewizard_cli/commands/batteries.py",
    "homewizard_cli/commands/ping.py",
]

for rel_path in command_files:
    path = BASE / rel_path
    content = path.read_text()

    # 1. Replace host typer option default
    content = content.replace(
        'host: str = typer.Option("192.168.68.109", "--host", "-H", help="P1 meter IP")',
        'host: str | None = typer.Option(None, "--host", "-H", help="P1 meter IP")',
    )

    # 2. Add resolve_host import if not present
    if "from ..config import resolve_host" not in content:
        # Check if already importing from ..config
        if "from ..config import" in content:
            content = content.replace(
                "from ..config import",
                "from ..config import resolve_host,",
            )
        else:
            # Add import after the first from .. import line
            # Find a good spot: after the first from .. import
            lines = content.splitlines()
            import_idx = None
            for i, line in enumerate(lines):
                if line.startswith("from .."):
                    import_idx = i
            if import_idx is not None:
                lines.insert(import_idx + 1, "from ..config import resolve_host")
                content = "\n".join(lines)
            else:
                # Insert after the docstring or first import
                lines.insert(0, "from ..config import resolve_host")
                content = "\n".join(lines)

    # 3. Add host = resolve_host(host) after console = Console() in async functions
    # We need to find all async def functions and add it after the first console = Console() in each.
    # But easier: just replace every occurrence of "    console = Console()\n" with "    console = Console()\n    host = resolve_host(host)\n"
    # But we must be careful not to add it twice.
    if "host = resolve_host(host)" not in content:
        content = content.replace(
            "    console = Console()\n",
            "    console = Console()\n    host = resolve_host(host)\n",
        )

    # 4. Fix async function signatures that have host: str, -> host: str | None,
    # Only in the specific async functions where host is passed.
    content = content.replace(
        "    host: str,\n",
        "    host: str | None,\n",
    )

    # 5. For files with untyped host parameters (reboot, pair, users, batteries)
    # async def _reboot_async(host, timeout, token, no_verify):
    if rel_path in {
        "homewizard_cli/commands/reboot.py",
        "homewizard_cli/commands/pair.py",
        "homewizard_cli/commands/users.py",
        "homewizard_cli/commands/batteries.py",
    }:
        # Add type hint to host in async def lines
        content = re.sub(
            r"async def _\w+_async\(host,",
            lambda m: m.group(0).replace("host,", "host: str | None,"),
            content,
        )

    path.write_text(content)

print("Done.")
