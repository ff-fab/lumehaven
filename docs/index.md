---
hide:
  - navigation
---

# lumehaven

**A smart home dashboard supporting common smart home frameworks.**

lumehaven uses a Backend-for-Frontend (BFF) architecture: a React frontend talks
exclusively to a Python/FastAPI backend, which normalizes data from smart home systems
like OpenHAB and HomeAssistant into a clean, uniform signal model.

---

<div class="grid cards" markdown>

- :material-school:{ .lg .middle } **Tutorials**

  ***

  New to lumehaven? Start here to get up and running.

  [:octicons-arrow-right-24: Getting Started](tutorials/getting-started.md)

- :material-tools:{ .lg .middle } **How-To Guides**

  ***

  Step-by-step instructions for specific tasks.

  [:octicons-arrow-right-24: Add a New Adapter](how-to/add-adapter.md)

- :material-book-open-variant:{ .lg .middle } **Reference**

  ***

  Technical reference for APIs, configuration, and decisions.

  [:octicons-arrow-right-24: Python API](reference/api/index.md)

- :material-head-lightbulb:{ .lg .middle } **Explanation**

  ***

  Understand the architecture and design decisions.

  [:octicons-arrow-right-24: Architecture](explanation/architecture.md)

</div>

---

## Key Concepts

| Concept     | Description                                                                                             |
| ----------- | ------------------------------------------------------------------------------------------------------- |
| **Signal**  | The universal data unit — `id`, `value`, `unit`, `label`. All smart home data is normalized to Signals. |
| **Adapter** | Connects to a smart home system (OpenHAB, HomeAssistant) and translates its data into Signals.          |
| **BFF**     | The backend normalizes units, formats, and quirks so the frontend stays simple and "dumb".              |
| **SSE**     | Server-Sent Events stream real-time Signal updates from backend to frontend.                            |

## Current Status

lumehaven is in active development. The backend is functional with an OpenHAB adapter.
See the [project roadmap](https://github.com/ff-fab/lumehaven/blob/main/docs/planning/roadmap.md) for current progress.

## License

lumehaven is released under the
[MIT License](https://github.com/ff-fab/lumehaven/blob/main/LICENSE).
