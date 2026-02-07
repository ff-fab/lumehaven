# Configure lumehaven

!!! warning "Work in progress" This guide will be completed as part of the documentation
content phase.

## Configuration File

lumehaven uses a YAML configuration file. Copy the example to get started:

```bash
cp config.example.yaml config.yaml
```

## Configuration Options

See the [Configuration Reference](../reference/configuration.md) for all available
options with types, defaults, and examples.

## Environment Variables

Configuration values can be overridden with environment variables using the `LUMEHAVEN_`
prefix:

```bash
export LUMEHAVEN_LOG_LEVEL=debug
```

## Adapter Configuration

Each adapter type has its own configuration options. See:

- [OpenHAB adapter configuration](../reference/api/adapters.md)
- [Architecture: Adapter System](../explanation/adapter-system.md) for how adapters work
