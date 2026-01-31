"""Mock OpenHAB API response data for testing.

These fixtures represent real (anonymized) OpenHAB API responses to ensure
tests cover actual API shapes and edge cases.

Source: docs/ll/openhab-example-api-calls.md (anonymized real data)
"""

# =============================================================================
# Item Responses (GET /rest/items)
# =============================================================================

TEMPERATURE_ITEM = {
    "link": "http://openhab:8080/rest/items/LivingRoom_Temperature",
    "state": "21.5 °C",
    "stateDescription": {
        "pattern": "%.1f °C",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Temperature",
    "name": "LivingRoom_Temperature",
    "label": "Living Room Temperature",
    "category": "temperature",
    "tags": ["Dashboard", "Measurement"],
    "groupNames": ["gTemperature"],
}

SWITCH_ITEM = {
    "link": "http://openhab:8080/rest/items/LivingRoom_Light",
    "state": "ON",
    "type": "Switch",
    "name": "LivingRoom_Light",
    "label": "Living Room Light",
    "category": "light",
    "tags": ["Dashboard", "Switchable"],
    "groupNames": ["gLights"],
}

DIMMER_ITEM = {
    "link": "http://openhab:8080/rest/items/LivingRoom_Dimmer",
    "state": "75",
    "stateDescription": {
        "minimum": 0,
        "maximum": 100,
        "step": 1,
        "pattern": "%d %%",
        "readOnly": False,
        "options": [],
    },
    "type": "Dimmer",
    "name": "LivingRoom_Dimmer",
    "label": "Living Room Dimmer",
    "category": "slider",
    "tags": ["Dashboard"],
    "groupNames": ["gLights"],
}

POWER_ITEM = {
    "link": "http://openhab:8080/rest/items/House_Power",
    "state": "1250 W",
    "stateDescription": {
        "pattern": "%d W",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Power",
    "name": "House_Power",
    "label": "Current Power Consumption",
    "category": "energy",
    "tags": ["Dashboard", "Measurement"],
    "groupNames": ["gEnergy"],
}

ENERGY_ITEM = {
    "link": "http://openhab:8080/rest/items/House_Energy",
    "state": "12345.67 kWh",
    "stateDescription": {
        "pattern": "%.2f kWh",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Energy",
    "name": "House_Energy",
    "label": "Total Energy",
    "category": "energy",
    "tags": ["Dashboard"],
    "groupNames": ["gEnergy"],
}

STRING_ITEM = {
    "link": "http://openhab:8080/rest/items/Weather_Condition",
    "state": "Partly Cloudy",
    "type": "String",
    "name": "Weather_Condition",
    "label": "Weather",
    "category": "sun_clouds",
    "tags": ["Dashboard"],
    "groupNames": [],
}

CONTACT_ITEM = {
    "link": "http://openhab:8080/rest/items/FrontDoor_Contact",
    "state": "CLOSED",
    "type": "Contact",
    "name": "FrontDoor_Contact",
    "label": "Front Door",
    "category": "door",
    "tags": ["Dashboard"],
    "groupNames": ["gSecurity"],
}

ROLLERSHUTTER_ITEM = {
    "link": "http://openhab:8080/rest/items/LivingRoom_Blinds",
    "state": "30",
    "stateDescription": {
        "minimum": 0,
        "maximum": 100,
        "step": 10,
        "pattern": "%d %%",
        "readOnly": False,
        "options": [],
    },
    "type": "Rollershutter",
    "name": "LivingRoom_Blinds",
    "label": "Living Room Blinds",
    "category": "blinds",
    "tags": ["Dashboard"],
    "groupNames": [],
}

DATETIME_ITEM = {
    "link": "http://openhab:8080/rest/items/System_LastUpdate",
    "state": "2026-01-31T12:30:45.000+0100",
    "type": "DateTime",
    "name": "System_LastUpdate",
    "label": "Last Update",
    "category": "time",
    "tags": [],
    "groupNames": [],
}

# =============================================================================
# Special States
# =============================================================================

UNDEF_ITEM = {
    "link": "http://openhab:8080/rest/items/Sensor_Offline",
    "state": "UNDEF",
    "type": "Number:Temperature",
    "name": "Sensor_Offline",
    "label": "Offline Sensor",
    "tags": ["Dashboard"],
    "groupNames": [],
}

NULL_ITEM = {
    "link": "http://openhab:8080/rest/items/Sensor_NULL",
    "state": "NULL",
    "type": "Number",
    "name": "Sensor_NULL",
    "label": "NULL Sensor",
    "tags": [],
    "groupNames": [],
}

# =============================================================================
# Collection helpers
# =============================================================================

ALL_ITEMS = [
    TEMPERATURE_ITEM,
    SWITCH_ITEM,
    DIMMER_ITEM,
    POWER_ITEM,
    ENERGY_ITEM,
    STRING_ITEM,
    CONTACT_ITEM,
    ROLLERSHUTTER_ITEM,
    DATETIME_ITEM,
    UNDEF_ITEM,
    NULL_ITEM,
]

DASHBOARD_ITEMS = [item for item in ALL_ITEMS if "Dashboard" in item.get("tags", [])]


# =============================================================================
# SSE Event Data
# =============================================================================

SSE_STATE_CHANGE_EVENT = {
    "topic": "openhab/items/LivingRoom_Temperature/state",
    "payload": '{"type":"Decimal","value":"22.0 °C"}',
    "type": "ItemStateEvent",
}

SSE_STATE_CHANGED_EVENT = {
    "topic": "openhab/items/LivingRoom_Light/statechanged",
    "payload": '{"type":"OnOff","value":"OFF","oldType":"OnOff","oldValue":"ON"}',
    "type": "ItemStateChangedEvent",
}

SSE_COMMAND_EVENT = {
    "topic": "openhab/items/LivingRoom_Light/command",
    "payload": '{"type":"OnOff","value":"ON"}',
    "type": "ItemCommandEvent",
}
