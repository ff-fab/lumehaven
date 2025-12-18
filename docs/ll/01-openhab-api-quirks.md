# OpenHAB REST API Quirks & Learnings

Specific knowledge about OpenHAB's REST API discovered during PoC development.

## SSE Event Subscription Model

**Endpoint:** `{base}/rest/events/states`

OpenHAB uses a two-step subscription:
1. First SSE message contains a `connection_id`
2. POST to `{base}/rest/events/states/{connection_id}` with JSON array of item names to subscribe

```python
# From old/backend/home-observer/openhab.py
event_data = next(messages)
connection_id = event_data.data
requests.post(f"{event_url}/{connection_id}", json=tagged_topics)
```

## Item State Formats

OpenHAB returns states in various formats that need parsing:

### QuantityTypes (e.g., `Number:Temperature`)
- State includes unit: `"23.5 °C"`
- Need to split value from unit
- Default units depend on measurement system (SI/US)

### Pattern-Based Formatting
Items can have `stateDescription.pattern` like `"%.1f °C"` or `"%d %%"`
- `%%` in pattern = literal `%` character
- Format specifiers: `%s`, `%d`, `%.Nf`

### Special Values
- `"UNDEF"` - Item has no value yet
- `"NULL"` - Item explicitly set to null
- These should be passed through, not parsed

### Type-Specific Behaviors
```python
# DateTime - no units, ignore patterns
if item_type[0] == "DateTime":
    return OpenHABItem(name, value=state, event_state_contains_unit=False)

# Rollershutter/Dimmer - implicit percentage
if item_type[0] in ("Rollershutter", "Dimmer"):
    return OpenHABItem(name, unit="%", format="%d", value=state)
```

## Transformed States

If an item has a transformation applied, OpenHAB returns `transformedState`:
- Use this directly, don't try to parse units
- Set `event_state_contains_unit=False`

## Measurement System Detection

**Endpoint:** `{base}/rest/`

Root endpoint returns system info including `measurementSystem`:
```python
response = requests.get(self.rest_url)
resp_json = response.json()
return resp_json.get("measurementSystem", "SI")  # Default to SI
```

## Event Stream Payload

SSE events contain JSON with:
```json
{
  "ItemName": {
    "state": "23.5 °C",
    "displayState": "24°"  // Optional, when transformation exists
  }
}
```

- `state` - Raw state, may contain unit
- `displayState` - Present when item has transformation, use this for display

## Encoding Issues

OpenHAB sometimes returns incorrectly encoded characters.
PoC used `ftfy` library to fix:
```python
from ftfy import fix_encoding
value = fix_encoding(payload["state"])
```

Consider: May be avoidable with proper request headers (`Accept-Charset`).

## Useful Query Parameters

For item listing:
- `tags=TagName` - Filter by tag
- `recursive=false` - Don't include group members
- `fields=name,state,type,stateDescription,transformedState` - Limit response fields

```
GET /rest/items?tags=Dashboard&recursive=false&fields=name%2Cstate%2Ctype%2CstateDescription%2CtransformedState
```

Note: Comma must be URL-encoded as `%2C` in fields parameter.

## Rate Limiting Considerations

The PoC implements periodic full refresh:
```python
SMART_HOME_REFRESH_CYCLE: int = 120  # seconds
```

This catches any missed events. 2 minutes seems reasonable for dashboard use.
