# Configuration Reference

lumehaven is configured via a **YAML file** (`config.yaml`) and/or **environment
variables**. For a step-by-step setup guide, see the
[Configuration how-to](../how-to/configuration.md).

## Configuration Sources

Configuration is loaded in this priority order:

1. **YAML config file** — If `config.yaml` exists with an `adapters` key, all adapter
   configs are loaded from there.
2. **Environment variables** — If no YAML file is found, a single OpenHAB adapter is
   created from `OPENHAB_URL` and `OPENHAB_TAG` env vars (backwards-compatible fallback).
3. **`.env` files** — Searched in the working directory, `../../.env`, and
   `../../../.env` (for monorepo layouts).

## Config File Search Paths

The YAML config file is searched in these locations (first match wins):

| Location                     | Typical Use Case                      |
| ---------------------------- | ------------------------------------- |
| `<cwd>/config.yaml`         | Running from project root             |
| `<cwd>/../../config.yaml`   | Running from `packages/backend/`      |
| `<cwd>/../../../config.yaml`| Running from `packages/backend/src/`  |

Override the filename with the `CONFIG_FILE` environment variable.

## Environment Variable Interpolation

YAML values support `${VAR_NAME}` syntax for environment variable expansion. Missing
variables are replaced with an empty string.

```yaml title="config.yaml"
adapters:
  - type: homeassistant
    name: home
    prefix: ha
    url: ${HA_URL}       # Expanded from environment at load time
    token: ${HA_TOKEN}   # Keep secrets out of config files
```

## Application Settings

These settings control server behavior. They're defined as fields on the `Settings`
model and can be set via environment variables (field name in uppercase).

| Field                  | Type                               | Default                    | Env Var                | Description                                        |
| ---------------------- | ---------------------------------- | -------------------------- | ---------------------- | -------------------------------------------------- |
| `openhab_url`          | `str`                              | `http://localhost:8080`    | `OPENHAB_URL`          | OpenHAB REST API URL (legacy single-adapter mode)  |
| `openhab_tag`          | `str`                              | `""`                       | `OPENHAB_TAG`          | Filter OpenHAB items by tag (legacy mode)          |
| `log_level`            | `DEBUG\|INFO\|WARNING\|ERROR`      | `INFO`                     | `LOG_LEVEL`            | Application log level                              |
| `cors_origins`         | `list[str]`                        | `["http://localhost:5173"]`| `CORS_ORIGINS`         | Allowed CORS origins for the frontend              |
| `host`                 | `str`                              | `0.0.0.0`                  | `HOST`                 | Server bind address                                |
| `port`                 | `int`                              | `8000`                     | `PORT`                 | Server port                                        |
| `subscriber_queue_size`| `int`                              | `10000`                    | `SUBSCRIBER_QUEUE_SIZE`| Max SSE subscriber queue depth                     |
| `drop_log_interval`    | `float`                            | `10.0`                     | `DROP_LOG_INTERVAL`    | Seconds between "queue full" log warnings          |
| `config_file`          | `str`                              | `config.yaml`              | `CONFIG_FILE`          | Path to YAML config file                           |

!!! note "No `LUMEHAVEN_` prefix"
    Environment variable names match field names directly (case-insensitive). There is
    no `LUMEHAVEN_` prefix. For example, use `LOG_LEVEL=DEBUG`, not
    `LUMEHAVEN_LOG_LEVEL=DEBUG`.

## Adapter Configuration

Adapters are configured in the YAML file's `adapters` list. Each entry is a
**discriminated union** — the `type` field determines which config model validates the
entry.

### OpenHAB Adapter

::: lumehaven.config.OpenHABAdapterConfig
    options:
      show_docstring_description: false
      show_source: false
      members: false

| Field    | Type              | Default                | Description                              |
| -------- | ----------------- | ---------------------- | ---------------------------------------- |
| `type`   | `Literal["openhab"]` | `"openhab"`         | Discriminator (must be `"openhab"`)      |
| `name`   | `str`             | `"openhab"`            | Unique identifier for this instance      |
| `prefix` | `str`             | `"oh"`                 | Signal ID namespace prefix               |
| `url`    | `str`             | `http://localhost:8080`| OpenHAB REST API base URL                |
| `tag`    | `str`             | `""`                   | Filter items by OpenHAB tag (empty = all)|

### Home Assistant Adapter

::: lumehaven.config.HomeAssistantAdapterConfig
    options:
      show_docstring_description: false
      show_source: false
      members: false

| Field    | Type                     | Default                | Description                          |
| -------- | ------------------------ | ---------------------- | ------------------------------------ |
| `type`   | `Literal["homeassistant"]` | `"homeassistant"`   | Discriminator (must be `"homeassistant"`) |
| `name`   | `str`                    | `"homeassistant"`      | Unique identifier for this instance  |
| `prefix` | `str`                    | `"ha"`                 | Signal ID namespace prefix           |
| `url`    | `str`                    | `http://localhost:8123`| Home Assistant API base URL          |
| `token`  | `str`                    | `""`                   | Long-lived access token              |

!!! warning "Home Assistant adapter not yet implemented"
    The `HomeAssistantAdapterConfig` model exists for forward compatibility. The
    adapter implementation is planned — see the
    [Adapter System](../explanation/adapter-system.md) overview.

## Full Example

```yaml title="config.yaml"
# Application settings (can also be set via env vars)
# log_level: DEBUG    # Uncomment for verbose logging

adapters:
  # Primary OpenHAB instance
  - type: openhab
    name: main-openhab
    prefix: oh
    url: http://localhost:8080
    tag: Dashboard

  # Home Assistant (future)
  # - type: homeassistant
  #   name: garage-ha
  #   prefix: ha
  #   url: http://localhost:8123
  #   token: ${HA_TOKEN}

# Multiple adapters of the same type are supported:
#  - type: openhab
#    name: secondary-openhab
#    prefix: oh2
#    url: http://192.168.1.100:8080
#    tag: Secondary
```

For the full configuration model with validation logic and source code, see the
[Config API reference](api/config.md).
