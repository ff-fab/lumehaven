# DevContainer Configuration

This directory contains the configuration for the **DevContainer development
environment** — the official and exclusive development setup for lumehaven.

## Files

### `devcontainer.json`

The main configuration file that defines:

- **Docker image and features** — Base Ubuntu environment with Git and Docker-in-Docker
- **VS Code settings** — Formatters, linters, rulers, and file rules
- **VS Code extensions** — Auto-installed on container startup
- **Port forwarding** — 8000 (API) and 5173 (frontend dev server)
- **Post-create script** — Runs `post-create.sh` to install dependencies

### `docker-compose.yml`

Defines the Docker Compose configuration for the devcontainer (service called
`devcontainer`).

### `post-create.sh`

Executed automatically after the container is created. Installs:

- Python dependencies: `uv sync --all-extras` (backend + dev tools)
- Node dependencies: `bun install` (frontend)
- Regenerates version number from git tags

### `Dockerfile`

The Docker image for the development environment (Ubuntu-based with Python, Node.js, Git
preinstalled).

## How It Works

1. **First time setup:**

   ```bash
   code .
   # Ctrl+Shift+P → "Dev Containers: Reopen in Container"
   ```

   - VS Code downloads/builds the Docker image
   - Starts a container from the image
   - Installs extensions
   - Runs `post-create.sh` (installs dependencies)
   - You're ready to develop

2. **Subsequent opens:**

   - Container already built and cached
   - Starts immediately
   - You're ready to develop

3. **Settings are applied:**
   - `.devcontainer.json` settings automatically apply to VS Code inside the container
   - All formatters and linters configured
   - No manual VS Code configuration needed

## Configuration Strategy

**Goal:** Single source of truth for all developer settings.

### Tool Configuration Hierarchy

```
Python Linting & Formatting
  packages/backend/pyproject.toml [tool.ruff]
    ↓ (mirrored in)
  .devcontainer/devcontainer.json [customizations.vscode.settings.[python]]

Frontend Formatting
  .prettierrc.json
    ↓ (mirrored in)
  .devcontainer/devcontainer.json [customizations.vscode.settings.[typescript], [javascript], etc.]

Type Checking
  packages/backend/pyproject.toml [tool.mypy]
    ↓ (mirrored in)
  .devcontainer/devcontainer.json [customizations.vscode.settings.python.analysis.typeCheckingMode]

Line Endings
  .gitattributes
    ↓ (mirrored in)
  .devcontainer/devcontainer.json [customizations.vscode.settings.files.eol]
```

### Why Duplication?

Tool-specific config files (like `pyproject.toml`) are the **source of truth** for what
rules apply. But VS Code needs to know them too to provide real-time feedback
(IntelliSense, inline errors, formatting previews).

So we mirror the rules in `.devcontainer/devcontainer.json` so VS Code can apply them
immediately without running external tools.

### Keeping Them in Sync

When you update tool rules:

1. Update the source file (`pyproject.toml`, `.prettierrc.json`, etc.)
2. Update corresponding setting in `.devcontainer/devcontainer.json`
3. Rebuild container: Ctrl+Shift+P → "Dev Containers: Rebuild Container"

Example: If you change `line-length = 88` in `pyproject.toml [tool.ruff]`, also update
`"editor.rulers": [88]` in devcontainer.json.

## Extensions

All extensions are auto-installed in the container:

```json
"extensions": [
  "ms-python.python",              // Python debugging, IntelliSense
  "ms-python.vscode-pylance",      // Advanced Python analysis
  "charliermarsh.ruff",            // Ruff formatter/linter UI
  "tamasfe.even-better-toml",      // TOML highlighting
  "d-biehl.robotcode",             // Robot Framework (integration tests)
  "dbaeumer.vscode-eslint",        // ESLint for JavaScript
  "prettier.prettier-vscode",      // Prettier formatter
  "bradlc.vscode-tailwindcss",     // Tailwind CSS utilities
  "GitHub.copilot",                // AI code assistant
  "GitHub.copilot-chat",           // AI chat
  "eamodio.gitlens",               // Git history/blame
  "yzhang.markdown-all-in-one"     // Markdown editing
]
```

No need to install manually — they appear when you first open the devcontainer.

## Environment Variables

The devcontainer sets up the Python virtual environment automatically:

- Python interpreter: `/workspace/packages/backend/.venv/bin/python`
- Activation: Automatic in VS Code terminal (check prompt for `(.venv)`)
- Package manager: `uv` (installed globally in container)

## Troubleshooting

### Container won't start

- Check Docker daemon is running: `docker ps`
- Rebuild: Ctrl+Shift+P → "Dev Containers: Rebuild Container"
- Check logs: Ctrl+Shift+P → "Dev Containers: Show Container Log"

### Settings not applying

- Rebuild container to re-run `post-create.sh`
- Reload VS Code: Ctrl+Shift+P → "Developer: Reload Window"

### Python not found

- Should auto-activate: check terminal prompt shows `(.venv)`
- Manual activation: `source /workspace/packages/backend/.venv/bin/activate`

### Extensions not installing

- Open extension sidebar and check for errors
- Rebuild container to retry installation

## Next Steps

- See [DEVELOPMENT-ENVIRONMENT.md](/docs/DEVELOPMENT-ENVIRONMENT.md) for full
  development guide
- See [Backend README](/packages/backend/README.md) for API-specific setup
- See [ADRs](/docs/adr/) for architectural decisions
