# Release Process

## Versioning Policy

homewizard-cli uses **Semantic Versioning (semver)** — `MAJOR.MINOR.PATCH`.

- **MAJOR**: Breaking changes (CLI interface changes, removed commands/options, format changes)
- **MINOR**: New features (new commands, new formatters, new options), deprecation additions
- **PATCH**: Bug fixes, documentation updates, test improvements, internal refactors

The single source of truth for version is in two places that MUST stay in sync:
- `pyproject.toml` → `project.version`
- `homewizard_cli/__init__.py` → `__version__`

A test in `tests/test_commands.py` (`test_version_matches_pyproject`) enforces this invariant.

## Version Bump Checklist

1. Run `./scripts/bump_version.sh X.Y.Z` (updates both files)
2. Add a new section in `CHANGELOG.md` for the version
3. Create a commit: `git commit -m "chore: bump version to X.Y.Z"`
4. Create a tag: `git tag vX.Y.Z`
5. Push: `git push origin main --tags`

## Automated Publishing

Pushing a tag matching `v*` triggers the `Release` workflow (`.github/workflows/release.yml`), which:

1. Builds the Python package (sdist + wheel)
2. Verifies a CHANGELOG entry exists for the version (warning if missing)
3. Publishes to PyPI via Trusted Publishing (OIDC)

## Manual Publishing

If automated publishing is unavailable:

```bash
# Install build tools
pip install build twine

# Build
python -m build

# Check
twine check dist/*

# Upload to Test PyPI
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

Use `__token__` as username and a PyPI API token as password when prompted.

## Trusted Publishing Setup (One-Time)

1. Go to https://pypi.org/manage/project/homewizard-cli/settings/publishing/
2. Add a "Trusted Publisher":
   - Owner: `SwordfishTrumpet`
   - Repository: `homewizard-cli`
   - Workflow: `release.yml`
3. After this, every `git push --tags` auto-publishes to PyPI
