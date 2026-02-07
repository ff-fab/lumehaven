# Getting Started

!!! abstract "What you'll learn"
    Install lumehaven, configure an OpenHAB adapter, start the backend, and see your
    first signals in the API.

## Prerequisites

- Python 3.14+ ([download](https://www.python.org/downloads/))
- [uv](https://docs.astral.sh/uv/) package manager
- [Task](https://taskfile.dev/) runner (optional but recommended)
- Access to an OpenHAB instance with the REST API enabled

!!! tip "No OpenHAB?"
    You can still start lumehaven without a running OpenHAB instance. The backend starts
    in **degraded mode** and the API remains accessible — you just won't see any signals
    until an adapter connects.

## 1. Clone and Install

```bash
git clone https://github.com/ff-fab/lumehaven.git
cd lumehaven/packages/backend
uv sync --group dev
```

You should see uv resolving and installing dependencies:

```
Resolved 87 packages in 1.2s
Installed 87 packages in 0.8s
```

## 2. Configure Your Adapter

Copy the example configuration:

```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` to point to your OpenHAB instance:

```yaml title="config.yaml"
adapters:
  - type: openhab
    name: main-openhab        # Appears in logs and health check
    prefix: oh                 # Signal IDs become "oh:ItemName"
    url: http://your-openhab:8080
    tag: Dashboard             # Only items with this tag (empty = all items)
```

The `tag` field filters which OpenHAB items lumehaven fetches. If you don't use tags,
set it to `""` or remove the line to fetch all items.

For all configuration options, see the
[Configuration Reference](../reference/configuration.md).

## 3. Start the Backend

Using the Task runner (recommended):

```bash
task dev:be
```

Or directly with uvicorn:

```bash
uv run uvicorn lumehaven.main:app --reload --host 0.0.0.0 --port 8000
```

You should see output like:

```
2026-02-07 10:00:00 - lumehaven.main - INFO - Loaded 1 adapter configuration(s)
2026-02-07 10:00:00 - lumehaven.main - INFO - Connecting to openhab adapter 'main-openhab'...
2026-02-07 10:00:01 - lumehaven.main - INFO - Adapter 'main-openhab': loaded 42 signals
2026-02-07 10:00:01 - lumehaven.main - INFO - Started with 1/1 adapter(s) connected
INFO:     Uvicorn running on http://0.0.0.0:8000
```

!!! warning "If connection fails"
    If OpenHAB is not reachable, you'll see:

    ```
    ERROR - Adapter 'main-openhab' failed to connect: ...
    WARNING - No adapters connected - starting in degraded mode
    ```

    The server still starts — it will retry with exponential backoff (5s, 10s, 20s, ...
    up to 5 minutes). Check that your OpenHAB URL and network are correct.

## 4. Explore the API

With the backend running, open these URLs in your browser:

### Swagger UI

Browse the interactive API documentation:

[http://localhost:8000/docs](http://localhost:8000/docs){ .md-button }

### List All Signals

```bash
curl -s http://localhost:8000/api/signals | python -m json.tool
```

```json
{
    "signals": [
        {
            "id": "oh:LivingRoom_Temperature",
            "value": "21.5",
            "unit": "°C",
            "label": "Living Room Temperature"
        },
        {
            "id": "oh:Kitchen_Light",
            "value": "ON",
            "unit": "",
            "label": "Kitchen Light"
        }
    ],
    "count": 2
}
```

### Get a Single Signal

```bash
curl -s http://localhost:8000/api/signals/oh:LivingRoom_Temperature | python -m json.tool
```

```json
{
    "id": "oh:LivingRoom_Temperature",
    "value": "21.5",
    "unit": "°C",
    "label": "Living Room Temperature"
}
```

### Health Check

```bash
curl -s http://localhost:8000/health | python -m json.tool
```

```json
{
    "status": "healthy",
    "signal_count": 42,
    "subscriber_count": 0,
    "adapters": [
        {
            "name": "main-openhab",
            "type": "openhab",
            "connected": true
        }
    ]
}
```

### Live Updates (SSE)

Open a terminal and subscribe to real-time signal updates:

```bash
curl -N http://localhost:8000/api/events/signals
```

When a signal changes in OpenHAB, you'll see events stream in:

```
event: signal
data: {"id": "oh:LivingRoom_Temperature", "value": "22.0", "unit": "°C", "label": "Living Room Temperature"}

event: signal
data: {"id": "oh:Kitchen_Light", "value": "OFF", "unit": "", "label": "Kitchen Light"}
```

Press ++ctrl+c++ to stop the stream.

## Troubleshooting

| Problem                         | Cause                           | Solution                                      |
| ------------------------------- | ------------------------------- | --------------------------------------------- |
| "Connection refused"            | OpenHAB not running / wrong URL | Check `url` in `config.yaml`, verify with `curl http://your-openhab:8080/rest/` |
| Empty signals list              | Wrong tag filter                | Set `tag: ""` in config to fetch all items    |
| "Address already in use"        | Port 8000 occupied              | Set `PORT=8001` env var or stop the other process |
| "No module named 'lumehaven'"   | Not in the right directory      | Run from `packages/backend/`                  |

## Next Steps

- [Configure lumehaven](../how-to/configuration.md) — multi-adapter setups, env vars,
  YAML interpolation
- [Understand the architecture](../explanation/architecture.md) — BFF pattern, data flow,
  SSE streaming
- [Explore the API reference](../reference/rest-api.md) — full endpoint documentation
