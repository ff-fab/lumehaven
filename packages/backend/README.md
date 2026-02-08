# lumehaven Backend

The Backend-For-Frontend (BFF) service for the lumehaven smart home dashboard.

## Architecture

This backend acts as a normalizing layer between smart home systems (OpenHAB, HomeAssistant)
and the React frontend. Key responsibilities:

- **Signal Normalization**: Convert smart home data to a unified `Signal` model
- **Unit Extraction**: Parse state patterns to extract display units
- **Value Formatting**: Apply formatting rules from smart home metadata
- **SSE Streaming**: Real-time updates from smart home → frontend

## Project Structure

```
src/lumehaven/
├── __init__.py
├── main.py              # FastAPI application entry point
├── config.py            # Configuration via pydantic-settings
├── core/
│   ├── __init__.py
│   ├── signal.py        # Signal model (ADR-005)
│   └── exceptions.py    # Custom exceptions
├── adapters/
│   ├── __init__.py
│   ├── protocol.py      # SmartHomeAdapter protocol
│   └── openhab/
│       ├── __init__.py
│       ├── adapter.py   # OpenHAB adapter implementation
│       ├── client.py    # HTTP/SSE client for OpenHAB
│       └── units.py     # Unit extraction and formatting
├── api/
│   ├── __init__.py
│   ├── routes.py        # FastAPI route definitions
│   └── sse.py           # SSE endpoint handling
└── state/
    ├── __init__.py
    └── store.py         # In-memory state storage (ADR-001)

tests/
├── unit/                # pytest unit tests
├── integration/         # Robot Framework tests
└── fixtures/            # Shared test data
```

## Development

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

```bash
# Install dependencies (including dev dependencies)
task sync:be
```

### Running

```bash
# Development server with hot reload
task dev:be
```

### Testing

```bash
# Run all backend tests (unit + integration)
task test:be

# Run unit tests only (fast feedback)
task test:be:unit

# Run with coverage report
task test:be:cov

# Run with HTML coverage report (opens in browser)
task test:be:cov:html

# Run integration tests (Robot Framework)
task test:be:integration

# Check coverage thresholds
task test:be:thresholds
```

### Code Quality

```bash
# Lint and format check
task lint:be

# Auto-fix lint and format issues
task lint:be:fix

# Type checking
task typecheck:be

# Run all checks (lint + typecheck + test)
task check
```

## Configuration

Environment variables (can also be in `.env` file):

| Variable | Default | Description |
|----------|---------|-------------|
| `SMART_HOME_TYPE` | `openhab` | Smart home system type |
| `OPENHAB_URL` | `http://localhost:8080` | OpenHAB REST API URL |
| `OPENHAB_TAG` | `` | Filter items by tag (empty = all) |
| `LOG_LEVEL` | `INFO` | Logging level |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/api/signals` | List all signals |
| `GET` | `/api/signals/{id}` | Get specific signal |
| `GET` | `/api/events/signals` | SSE stream of signal updates |

## Related ADRs

- [ADR-001: State Management](../../docs/adr/ADR-001-state-management.md)
- [ADR-002: Backend Runtime](../../docs/adr/ADR-002-backend-runtime.md)
- [ADR-005: Signal Abstraction](../../docs/adr/ADR-005-signal-abstraction.md)
- [ADR-006: Testing Strategy](../../docs/adr/ADR-006-testing-strategy.md)
