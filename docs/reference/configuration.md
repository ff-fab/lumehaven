# Configuration Reference

!!! warning "Work in progress" This reference will be completed as part of the
documentation content phase.

lumehaven is configured via a YAML file (`config.yaml`) and/or environment variables.
See the [Configuration how-to](../how-to/configuration.md) for getting started.

## Configuration File

The configuration file is loaded from `config.yaml` in the working directory by default:

```yaml title="config.yaml"
log_level: info

adapters:
  - type: openhab
    url: http://openhab:8080
```

## Environment Variables

All configuration options can be overridden via environment variables with the
`LUMEHAVEN_` prefix. Nested keys use double underscores:

```bash
LUMEHAVEN_LOG_LEVEL=debug
LUMEHAVEN_ADAPTERS__0__URL=http://openhab:8080
```

## Options

For the full configuration model with types and validation, see the
[Config API reference](api/config.md).
