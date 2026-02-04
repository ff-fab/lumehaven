"""Mock OpenHAB SSE event data for testing.

These fixtures represent SSE events from OpenHAB's /rest/events endpoint,
including various payload types, error conditions, and edge cases.

Event Types Covered:
- ItemStateEvent: State updates (raw state)
- ItemStateChangedEvent: State changes (old and new)
- ItemStateUpdatedEvent: State updates via subscription
- StateSubscription: Batch state updates from /rest/events/states
- ThingStatusInfoEvent: Device status changes (filtering test)

Payload Types:
- Decimal: Plain numeric values
- Quantity: Values with units (e.g., "22.5 °C")
- Percent: Percentage values
- OnOff: Switch states
- UnDef: UNDEF/NULL states
- HSB: Color values (Hue, Saturation, Brightness)
- PlayPause: Player states

Edge Cases:
- displayState field (alternative display value)
- Malformed JSON payloads
- Encoding issues (double-encoded UTF-8)
- Connection ID responses
"""

import json

# =============================================================================
# Traditional SSE Events (/rest/events)
# =============================================================================

# ItemStateEvent - temperature update with Quantity type
SSE_STATE_EVENT_QUANTITY = {
    "topic": "openhab/items/LivingRoom_Temperature/state",
    "payload": json.dumps(
        {
            "type": "Quantity",
            "value": "22.5 °C",
        }
    ),
    "type": "ItemStateEvent",
}

# ItemStateEvent - simple decimal value
SSE_STATE_EVENT_DECIMAL = {
    "topic": "openhab/items/House_Power/state",
    "payload": json.dumps(
        {
            "type": "Decimal",
            "value": "1250",
        }
    ),
    "type": "ItemStateEvent",
}

# ItemStateChangedEvent - switch state change
SSE_STATE_CHANGED_EVENT = {
    "topic": "openhab/items/LivingRoom_Light/statechanged",
    "payload": json.dumps(
        {
            "type": "OnOff",
            "value": "OFF",
            "oldType": "OnOff",
            "oldValue": "ON",
        }
    ),
    "type": "ItemStateChangedEvent",
}

# ItemStateEvent - percent value (dimmer)
SSE_STATE_EVENT_PERCENT = {
    "topic": "openhab/items/LivingRoom_Dimmer/state",
    "payload": json.dumps(
        {
            "type": "Percent",
            "value": "75",
        }
    ),
    "type": "ItemStateEvent",
}

# ItemStateEvent - UNDEF state
SSE_STATE_EVENT_UNDEF = {
    "topic": "openhab/items/Sensor_Offline/state",
    "payload": json.dumps(
        {
            "type": "UnDef",
            "value": "UNDEF",
        }
    ),
    "type": "ItemStateEvent",
}

# ItemStateEvent - HSB color value
SSE_STATE_EVENT_COLOR = {
    "topic": "openhab/items/LivingRoom_ColorLight/state",
    "payload": json.dumps(
        {
            "type": "HSB",
            "value": "120,100,50",
        }
    ),
    "type": "ItemStateEvent",
}

# ItemStateEvent - player state
SSE_STATE_EVENT_PLAYER = {
    "topic": "openhab/items/MediaRoom_Player/state",
    "payload": json.dumps(
        {
            "type": "PlayPause",
            "value": "PLAY",
        }
    ),
    "type": "ItemStateEvent",
}

# ItemCommandEvent - command sent to item
SSE_COMMAND_EVENT = {
    "topic": "openhab/items/LivingRoom_Light/command",
    "payload": json.dumps(
        {
            "type": "OnOff",
            "value": "ON",
        }
    ),
    "type": "ItemCommandEvent",
}

# ThingStatusInfoEvent - device status change (should be filtered out)
SSE_THING_STATUS_EVENT = {
    "topic": "openhab/things/mqtt:topic:broker:sensor1/status",
    "payload": json.dumps(
        {
            "status": "OFFLINE",
            "statusDetail": "COMMUNICATION_ERROR",
            "description": "Connection timed out",
        }
    ),
    "type": "ThingStatusInfoEvent",
}


# =============================================================================
# State Subscription Events (/rest/events/states)
# =============================================================================

# Connection ID response (first message after connecting)
SSE_CONNECTION_ID = "abc123-def456-ghi789"

# Batch state update - multiple items in one event
SSE_STATE_SUBSCRIPTION_BATCH = {
    "LivingRoom_Temperature": {
        "state": "22.5 °C",
        "displayState": "22.5 °C",
    },
    "LivingRoom_Light": {
        "state": "ON",
        "displayState": "On",
    },
    "House_Power": {
        "state": "1250 W",
        "displayState": "1.25 kW",  # displayState has different format
    },
}

# Single item with displayState (tests E2 branch - use displayState)
SSE_STATE_WITH_DISPLAY_STATE = {
    "System_Uptime": {
        "state": "4224248.0",
        "displayState": "48d 21h",  # Transformed via JS
    },
}

# Single item without displayState (tests E3 branch - use raw state)
SSE_STATE_WITHOUT_DISPLAY_STATE = {
    "LivingRoom_Dimmer": {
        "state": "75",
    },
}

# QuantityType event (tests E1 branch - extract and format)
SSE_STATE_QUANTITY_TYPE = {
    "Bathroom_Humidity": {
        "state": "65.5 %",
    },
}


# =============================================================================
# Edge Cases and Error Conditions
# =============================================================================

# Malformed JSON payload (tests exception handling)
SSE_MALFORMED_EVENT = {
    "topic": "openhab/items/BadItem/state",
    "payload": "{invalid json",
    "type": "ItemStateEvent",
}

# Event with encoding issues (double-encoded UTF-8)
SSE_ENCODING_ISSUE_EVENT = {
    "topic": "openhab/items/Sensor_External/state",
    "payload": json.dumps(
        {
            "type": "Quantity",
            "value": "22.5 Â°C",  # Should be fixed by ftfy
        }
    ),
    "type": "ItemStateEvent",
}

# Empty payload
SSE_EMPTY_PAYLOAD_EVENT = {
    "topic": "openhab/items/EmptyItem/state",
    "payload": "{}",
    "type": "ItemStateEvent",
}

# Unknown item (not in metadata cache)
SSE_UNKNOWN_ITEM_EVENT = {
    "topic": "openhab/items/UnknownItem/state",
    "payload": json.dumps(
        {
            "type": "Decimal",
            "value": "42",
        }
    ),
    "type": "ItemStateEvent",
}


# =============================================================================
# Raw SSE Stream Data (as received from server)
# =============================================================================


def make_sse_line(event_type: str, data: dict | str) -> str:
    """Generate a raw SSE line as received from the server.

    Args:
        event_type: The SSE event type (e.g., "message", "state")
        data: The data payload (dict will be JSON serialized)

    Returns:
        Formatted SSE line with event type and data.
    """
    data_str = json.dumps(data) if isinstance(data, dict) else data
    return f"event: {event_type}\ndata: {data_str}\n\n"


# Example raw SSE stream for integration testing
RAW_SSE_STREAM = "\n".join(
    [
        f"data: {SSE_CONNECTION_ID}",  # First message is connection ID
        "",  # Empty line separator
        f"data: {json.dumps(SSE_STATE_SUBSCRIPTION_BATCH)}",
        "",
    ]
)


# =============================================================================
# Collection Helpers
# =============================================================================

# All traditional SSE events for parametrized tests
ALL_SSE_EVENTS = [
    SSE_STATE_EVENT_QUANTITY,
    SSE_STATE_EVENT_DECIMAL,
    SSE_STATE_CHANGED_EVENT,
    SSE_STATE_EVENT_PERCENT,
    SSE_STATE_EVENT_UNDEF,
    SSE_STATE_EVENT_COLOR,
    SSE_STATE_EVENT_PLAYER,
    SSE_COMMAND_EVENT,
]

# Events that should yield signals (not filtered)
SIGNAL_YIELDING_EVENTS = [
    SSE_STATE_EVENT_QUANTITY,
    SSE_STATE_EVENT_DECIMAL,
    SSE_STATE_CHANGED_EVENT,
    SSE_STATE_EVENT_PERCENT,
]

# Events that should be filtered out
FILTERED_EVENTS = [
    SSE_THING_STATUS_EVENT,
    SSE_COMMAND_EVENT,
]

# Error condition events
ERROR_EVENTS = [
    SSE_MALFORMED_EVENT,
    SSE_EMPTY_PAYLOAD_EVENT,
    SSE_UNKNOWN_ITEM_EVENT,
]
