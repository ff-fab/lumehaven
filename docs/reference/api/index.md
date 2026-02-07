# Python API Reference

Auto-generated API documentation from source code docstrings using
[mkdocstrings](https://mkdocstrings.github.io/).

## Modules

| Module                  | Description                                                       |
| ----------------------- | ----------------------------------------------------------------- |
| [Core](core.md)         | Signal model, exceptions, core types                              |
| [Adapters](adapters.md) | SmartHomeAdapter Protocol, AdapterManager, OpenHAB implementation |
| [API Routes](routes.md) | REST endpoints, Pydantic response models                          |
| [State](state.md)       | SignalStore — in-memory state with pub/sub                        |
| [Config](config.md)     | Application configuration (pydantic-settings)                     |

## Conventions

- **Docstring style:** Google format with `Args:`, `Returns:`, `Raises:` sections
- **Type hints:** All public APIs are fully typed (PEP 484 / PEP 604)
- **ADR references:** Docstrings cross-reference relevant Architecture Decision Records
