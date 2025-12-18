# Lessons Learned from Proof-of-Concept (old/)

Analysis of the home-dash PoC to inform the lumehaven restart.

## Architecture Patterns That Worked Well

### 1. SSE-Based Real-Time Updates ✓
**Location:** `old/backend/home-observer/openhab.py` (lines 193-234)

The SSE approach proved effective:
- Lower overhead than WebSockets for one-way data
- Native browser support via EventSource API
- OpenHAB's `/rest/events/states` endpoint works well
- Subscription model allows filtering to relevant items

**Carry forward:** Keep SSE for smart home → backend → frontend event flow.

### 2. Unit Normalization in Backend ✓
**Location:** `old/backend/home-observer/openhab.py`, `units_of_measurement.json`

Backend handling of:
- SI/US measurement system detection
- Pattern parsing (`%d Wh` → value + unit)
- Value formatting before sending to frontend

**Carry forward:** Frontend should receive pre-formatted values, not raw data.

### 3. SmartHome Protocol/Interface ✓
**Location:** `old/backend/home-observer/smarthome.py`

The `SmartHome` Protocol class defines a clean interface:
```python
class SmartHome(Protocol):
    items: Dict[str, SmartHomeItem]
    def load_items(self) -> Dict[str, SmartHomeItem]: ...
    def get_event_stream(self) -> Generator[SmartHomeItem, None, None]: ...
```

**Carry forward:** This abstraction pattern enables OpenHAB/HomeAssistant swapping.

### 4. Redis Pub/Sub for Decoupling ✓
**Location:** `old/backend/home-observer/main.py`, `old/backend/home-source/main.py`

Separating:
- `home-observer`: Consumes OpenHAB events, writes to Redis
- `home-source`: Reads Redis, serves frontend via FastAPI/SSE

**Reconsider:** Good pattern, but Redis adds deployment complexity. Evaluate if needed for single-instance deployment.

## Pain Points / Incomplete Items

### 1. No Tests ✗
**From TODO:** "add unit tests for all modules"

The PoC has zero tests. Critical for:
- OpenHAB API response parsing (many edge cases)
- Unit extraction logic (complex regex)
- Event stream handling

### 2. React App Structure ✗
**Location:** `old/frontend/home-front/src/App.js`

Issues:
- EventSource created in `render()` - will create multiple connections
- Class component with manual state management
- No proper cleanup of SSE connection

**Fix in new version:** Use proper hooks (`useEffect` for SSE lifecycle).

### 3. Hardcoded URLs ✗
**Location:** `old/frontend/home-front/src/App.js`

```javascript
fetch("http://localhost:8000/states")
new EventSource("http://localhost:8000/events")
```

**Fix in new version:** Configuration/environment-based URLs.

### 4. Error Handling ✗
**Location:** Throughout `openhab.py`

Many bare `except Exception: continue` blocks that swallow errors silently.

**Fix in new version:** Proper error handling, logging, maybe dead-letter handling.

### 5. No Type Safety in Frontend ✗
Plain JavaScript, no TypeScript, no prop validation.

**Fix in new version:** TypeScript from the start.

## Code Worth Preserving/Referencing

### 1. OpenHAB Item Parsing Logic
`old/backend/home-observer/openhab.py`:
- `extract_smart_home_item()` - Complex but handles many edge cases
- `get_unit_from_pattern()` - Pattern parsing
- `get_value_from_state()` - Value extraction and formatting

### 2. Units of Measurement Table
`old/backend/home-observer/units_of_measurement.json`
Complete SI/US unit mapping for OpenHAB QuantityTypes.

### 3. Docker Compose Structure
`old/docker-compose.yaml`
Clean service separation, environment handling.

### 4. Dashboard Component Structure
`old/frontend/home-front/src/components/`
- `Dashboard.js` → Header/Navigation/Main layout
- `panels/Start.js` → Widget implementations (weather, clock, etc.)

## Technology Choices to Reconsider

| PoC Choice | Issue | Consider |
|------------|-------|----------|
| Poetry | Slower than modern alternatives | uv |
| Node/npm | Slower, more bloated | Bun |
| Redis | Adds ops complexity | In-memory or direct passthrough |
| Class components | Outdated React pattern | Functional + hooks |
| JavaScript | No type safety | TypeScript |
| pydantic v1 | Migration needed | pydantic v2 |

## Specific Bugs/Issues to Avoid

1. **SSE reconnection** - PoC doesn't handle SSE disconnects gracefully
2. **Memory leaks** - EventSource in render() creates accumulating connections
3. **ftfy dependency** - Used for encoding fixes, may not be needed with proper handling
4. **CORS wildcard** - `allow_origins=["*"]` is too permissive for production
