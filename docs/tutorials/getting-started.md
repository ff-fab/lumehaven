# Getting Started

!!! abstract "What you'll learn" Install lumehaven, configure an OpenHAB adapter, start
the backend, and see your first signals in the API.

!!! warning "Work in progress" This tutorial will be completed as part of the
documentation content phase. See the
[documentation roadmap](../explanation/architecture.md) for details.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- Access to an OpenHAB instance (or the mock server for testing)

## Steps

### 1. Clone and Install

```bash
git clone https://github.com/ff-fab/lumehaven.git
cd lumehaven/packages/backend
uv sync --group dev
```

### 2. Configure Your Adapter

Copy the example configuration and edit it for your setup:

```bash
cp config.example.yaml config.yaml
```

```yaml title="config.yaml"
adapters:
  - type: openhab
    url: http://your-openhab:8080
    items:
      - name: LivingRoom_Temperature
        label: Living Room Temperature
```

### 3. Start the Backend

```bash
uv run uvicorn lumehaven.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Explore the API

Open your browser:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Signals endpoint:**
  [http://localhost:8000/api/signals](http://localhost:8000/api/signals)

## Next Steps

- [Configure lumehaven](../how-to/configuration.md) for more advanced setups
- [Add a new adapter](../how-to/add-adapter.md) to support another smart home system
- [Understand the architecture](../explanation/architecture.md)
