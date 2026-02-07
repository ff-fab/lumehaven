# Configure lumehaven

!!! abstract "Goal"
    Set up lumehaven's configuration file, customize adapter connections, and use
    environment variables for deployment flexibility.

## Quick Start

Copy the example configuration and edit it:

```bash
cd packages/backend
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your smart home system's URL:

```yaml title="config.yaml"
adapters:
  - type: openhab
    url: http://your-openhab:8080
```

That's it — lumehaven will connect to your OpenHAB instance using sensible defaults for
all other fields. Start the backend with `task dev:be` or
`uv run uvicorn lumehaven.main:app --reload`.

## Configuration File

lumehaven looks for `config.yaml` in the working directory by default. The file must
contain an `adapters` list with at least one adapter entry.

### Single Adapter

The minimal config — most fields have sensible defaults:

```yaml title="config.yaml"
adapters:
  - type: openhab
    url: http://openhab.local:8080
    tag: Dashboard              # Only items with this tag (optional)
```

### Multiple Adapters

Connect to multiple smart home systems simultaneously. Each adapter operates
independently — one failing doesn't affect the others:

```yaml title="config.yaml"
adapters:
  # Primary OpenHAB
  - type: openhab
    name: main-openhab          # Unique name (shown in logs, health check)
    prefix: oh                  # Signal IDs: "oh:ItemName"
    url: http://openhab.local:8080
    tag: Dashboard

  # Secondary OpenHAB (e.g., garage)
  - type: openhab
    name: garage-openhab
    prefix: oh2                 # Different prefix to avoid ID collisions
    url: http://192.168.1.100:8080
    tag: Garage
```

!!! tip "Prefixes must be unique"
    Each adapter instance needs a unique `prefix` to namespace its signal IDs. Two
    adapters with the same prefix would cause signal ID collisions.

### Using Secrets with Environment Variables

Keep sensitive values (API tokens, passwords) out of config files using `${VAR_NAME}`
interpolation:

```yaml title="config.yaml"
adapters:
  - type: homeassistant
    name: home
    prefix: ha
    url: ${HA_URL}
    token: ${HA_TOKEN}         # Expanded from environment at load time
```

```bash
export HA_URL="http://homeassistant.local:8123"
export HA_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOi..."
task dev:be
```

Missing environment variables are replaced with an empty string — no error is raised.

## Environment Variables (No YAML)

For simple single-adapter setups, you can skip the YAML file entirely. If no
`config.yaml` is found, lumehaven creates a single OpenHAB adapter from environment
variables:

```bash
export OPENHAB_URL="http://openhab.local:8080"
export OPENHAB_TAG="Dashboard"
task dev:be
```

Other application settings are also available as environment variables:

```bash
export LOG_LEVEL=DEBUG                         # Verbose logging
export PORT=9000                               # Different port
export CORS_ORIGINS='["http://localhost:3000"]' # Custom frontend URL
```

!!! note "No `LUMEHAVEN_` prefix"
    Environment variable names match the setting field names directly
    (case-insensitive). For example, use `LOG_LEVEL`, not `LUMEHAVEN_LOG_LEVEL`.

## `.env` File Support

lumehaven loads `.env` files automatically (via pydantic-settings). It searches these
locations:

1. `.env` in the working directory
2. `../../.env` (from `packages/backend/`)
3. `../../../.env` (from `packages/backend/src/`)

```bash title=".env"
OPENHAB_URL=http://openhab.local:8080
LOG_LEVEL=DEBUG
```

## Common Scenarios

### Development (Local OpenHAB)

```yaml title="config.yaml"
adapters:
  - type: openhab
    url: http://localhost:8080
```

### Production (Environment-Based)

```yaml title="config.yaml"
adapters:
  - type: openhab
    url: ${OPENHAB_URL}
    tag: ${OPENHAB_TAG}
```

```bash title="docker-compose.yaml or deployment env"
OPENHAB_URL=http://openhab:8080
OPENHAB_TAG=Dashboard
LOG_LEVEL=WARNING
```

## Reference

For the **complete list of all settings** with types, defaults, and validation rules,
see the [Configuration Reference](../reference/configuration.md).

For how configuration flows into adapters, see
[Adapter System](../explanation/adapter-system.md).
