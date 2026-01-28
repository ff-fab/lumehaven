# Versioning Strategy for lumehaven

This document describes the versioning strategy for the **lumehaven project**, a
monorepo containing multiple packages (backend, frontend, etc.). All packages share a
single version number to maintain consistency across the project.

## Monorepo Versioning Principle

In lumehaven, **all packages use the same version**:

- `packages/backend` (Python/FastAPI)
- `packages/frontend` (React/TypeScript)
- Any future packages or utilities

This ensures that:

- Releases are coordinated across all components
- Deployment versions stay synchronized
- Documentation and release notes refer to a single project version

## How It Works

1. **git tags** (e.g., `v0.1.0`) are the single source of truth for project versions
2. **setuptools_scm** (in the backend) reads git history and derives the version
3. The version is written to `packages/backend/src/lumehaven/_version.py` at build time
4. Each package imports this version for its own metadata

## Workflow

### For Development

After pulling changes or updating git tags, regenerate the version:

```bash
python scripts/update_version.py
```

This updates the version file used by all packages during development.

### For Releases

1. **Create a release tag** following semantic versioning:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

2. **Regenerate the version file**:

   ```bash
   python scripts/update_version.py
   ```

3. **Build and deploy all packages**:

   ```bash
   # Backend
   cd packages/backend && uv build

   # Frontend
   cd packages/frontend && bun run build
   ```

   All packages will automatically use the version from the tag.

## Version Format

- **At a release tag**: `0.1.0`
- **During development** (after a tag): `0.1.1.dev0+gXXXXXXX.dYYYYMMDD`

The `.dev` suffix indicates a development version between official releases and includes
git commit hash and date.

## Configuration

### Backend (`packages/backend/`)

- **Configuration**: `[tool.setuptools_scm]` in `pyproject.toml`
- **Output file**: `src/lumehaven/_version.py` (generated, in `.gitignore`)
- **Import logic** in `src/lumehaven/__init__.py`:
  1. Try `_version.py` (latest setuptools_scm output)
  2. Fallback to `importlib.metadata` (installed package version)
  3. Last resort: `"0.0.0+unknown"`

### Frontend (`packages/frontend/`)

- Imports version from backend when needed (shared model)
- Can read `packages/backend/src/lumehaven/_version.py` directly or via API

### Docker & CI/CD

- Version is embedded at build time from git tags
- No manual version management in build scripts
- Multi-stage builds can reference the project version consistently

## Semantic Versioning

Follow **Semantic Versioning (MAJOR.MINOR.PATCH)**:

| Version   | Trigger                                                            | Example       |
| --------- | ------------------------------------------------------------------ | ------------- |
| **MAJOR** | Breaking changes in backend API, signal model, or adapter protocol | 1.0.0 → 2.0.0 |
| **MINOR** | New features (new adapters, new dashboard features)                | 0.1.0 → 0.2.0 |
| **PATCH** | Bug fixes and minor improvements                                   | 0.1.0 → 0.1.1 |

Pre-release tags (e.g., `v0.1.0-alpha.1`) are supported but should be exceptional.

## Why This Approach?

✅ **Single version for entire project** - All packages release together ✅ **Zero
manual version bumps** - Version automatically derives from git tags ✅ **CI/CD
friendly** - Deploy from tags, version is deterministic ✅ **Git integration** - Version
always matches deployed code ✅ **Development clarity** - `.dev` suffix shows code is
between releases ✅ **Monorepo scalability** - Adding packages doesn't complicate
versioning

## Troubleshooting

**Version shows as `0.0.0+unknown`?**

- Verify git is available: `git describe --tags`
- Check you're in a git repository: `git status`
- Regenerate with: `python scripts/update_version.py`

**Version file not updating after pulling changes?**

- `_version.py` is generated and in `.gitignore` (not committed)
- Run `python scripts/update_version.py` after `git pull` or creating new tags

**Different versions between development and production?**

- **Development**: Uses `_version.py` from git (e.g., `0.1.1.dev0+g49f5dee4d`)
- **Production**: Uses stable version from tag (e.g., `0.1.0`)
- This is **intentional** - helps identify development vs. released versions

**Need to test a release version locally?**

```bash
git tag v0.2.0  # Create temporary tag
python scripts/update_version.py  # Updates to 0.2.0
# Test...
git tag -d v0.2.0  # Clean up temporary tag
python scripts/update_version.py  # Back to dev version
```
