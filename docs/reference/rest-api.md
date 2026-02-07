# REST API

lumehaven's REST API is built with FastAPI, which provides automatic interactive
documentation via OpenAPI (Swagger) specification.

## Interactive Documentation

When the backend is running (`task dev:be`), the following endpoints are available:

| URL                                                                      | Tool             | Description                                      |
| ------------------------------------------------------------------------ | ---------------- | ------------------------------------------------ |
| [http://localhost:8000/docs](http://localhost:8000/docs)                 | **Swagger UI**   | Interactive API explorer — try requests directly |
| [http://localhost:8000/redoc](http://localhost:8000/redoc)               | **ReDoc**        | Clean, readable API reference                    |
| [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json) | **OpenAPI spec** | Raw JSON schema for code generation              |

## Key Endpoints

| Method | Path                       | Description                            |
| ------ | -------------------------- | -------------------------------------- |
| `GET`  | `/api/signals`             | List all current signals               |
| `GET`  | `/api/signals/{signal_id}` | Get a specific signal by ID            |
| `GET`  | `/api/signals/stream`      | SSE stream of real-time signal updates |
| `GET`  | `/health`                  | Health check with adapter status       |

## Authentication

Currently, lumehaven does not require authentication. This will be revisited when
deployment guides are added.

## Python API Reference

For the implementation details behind these endpoints, see the
[API Routes](api/routes.md) reference.
