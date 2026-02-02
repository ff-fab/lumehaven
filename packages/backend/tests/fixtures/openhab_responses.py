"""Mock OpenHAB API response data for testing.

These fixtures represent real (anonymized) OpenHAB API responses to ensure
tests cover actual API shapes and edge cases.

Source: anonymized real data from OpenHAB 5.0.1 instance, supplemented with
synthesized data for missing types based on OpenHAB 5.x REST API documentation.

Item Types Covered:
- Basic: Switch, Contact, String, DateTime
- Numeric: Number, Number:Temperature, Number:Power, Number:Energy,
           Number:Dimensionless, Number:Speed, Number:Angle, Number:Pressure,
           Number:Volume, Number:Length, Number:Density, Number:Illuminance,
           Number:Time, Number:Intensity, Number:Mass, Number:ElectricPotential,
           Number:ElectricCurrent, Number:VolumetricFlowRate
- Percentage: Dimmer, Rollershutter
- Complex: Color, Location, Image, Player, Group, Call

Edge Cases:
- UNDEF and NULL states
- transformedState (JS/MAP transformations)
- stateDescription.options (selectable values)
- QuantityType without stateDescription
- Special characters and encoding
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
# New Item Types (discovered from live data + OpenHAB 5.x docs)
# =============================================================================

# Player item - media player control (PLAY, PAUSE, NEXT, PREVIOUS, REWIND, FASTFORWARD)
PLAYER_ITEM = {
    "link": "http://openhab:8080/rest/items/MediaRoom_Player",
    "state": "PAUSE",
    "type": "Player",
    "name": "MediaRoom_Player",
    "label": "Media Player",
    "category": "player",
    "tags": ["Dashboard"],
    "groupNames": ["gMedia"],
}

# Group item - aggregates multiple items
GROUP_ITEM = {
    "link": "http://openhab:8080/rest/items/gLights",
    "state": "ON",
    "stateDescription": {
        "pattern": "%d",
        "readOnly": True,
        "options": [],
    },
    "type": "Group",
    "name": "gLights",
    "label": "All Lights",
    "category": "lightbulb",
    "tags": ["Dashboard"],
    "groupNames": [],
    "members": [
        {"name": "LivingRoom_Light"},
        {"name": "Kitchen_Light"},
    ],
}

# Color item - HSB (Hue, Saturation, Brightness)
COLOR_ITEM = {
    "link": "http://openhab:8080/rest/items/LivingRoom_ColorLight",
    "state": "120,100,50",
    "type": "Color",
    "name": "LivingRoom_ColorLight",
    "label": "Color Light",
    "category": "colorlight",
    "tags": ["Dashboard", "Lighting"],
    "groupNames": ["gLights"],
}

# Location item - latitude,longitude,altitude
LOCATION_ITEM = {
    "link": "http://openhab:8080/rest/items/Home_Location",
    "state": "52.5200,13.4050,34.0",
    "type": "Location",
    "name": "Home_Location",
    "label": "Home Location",
    "category": "location",
    "tags": [],
    "groupNames": [],
}

# Image item - base64 encoded image data
IMAGE_ITEM = {
    "link": "http://openhab:8080/rest/items/Camera_Snapshot",
    "state": "data:image/png;base64,iVBORw0KGgoAAAANS...",
    "type": "Image",
    "name": "Camera_Snapshot",
    "label": "Camera Snapshot",
    "category": "camera",
    "tags": [],
    "groupNames": ["gSecurity"],
}

# Call item - phone number representation
CALL_ITEM = {
    "link": "http://openhab:8080/rest/items/Phone_LastCall",
    "state": "1234567890",
    "type": "Call",
    "name": "Phone_LastCall",
    "label": "Last Call",
    "category": "phone",
    "tags": [],
    "groupNames": [],
}

# Number:Dimensionless - percentage without unit
DIMENSIONLESS_ITEM = {
    "link": "http://openhab:8080/rest/items/Bathroom_Humidity",
    "state": "65.5 %",
    "stateDescription": {
        "pattern": "%.1f %%",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Dimensionless",
    "name": "Bathroom_Humidity",
    "label": "Bathroom Humidity",
    "category": "humidity",
    "tags": ["Dashboard", "Measurement"],
    "groupNames": ["gClimate"],
}

# Number:Speed - wind speed
SPEED_ITEM = {
    "link": "http://openhab:8080/rest/items/Weather_WindSpeed",
    "state": "15.5 km/h",
    "stateDescription": {
        "pattern": "%.1f km/h",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Speed",
    "name": "Weather_WindSpeed",
    "label": "Wind Speed",
    "category": "wind",
    "tags": ["Dashboard"],
    "groupNames": ["gWeather"],
}

# Number:Angle - wind direction
ANGLE_ITEM = {
    "link": "http://openhab:8080/rest/items/Weather_WindDirection",
    "state": "228 °",
    "stateDescription": {
        "pattern": "%d °",
        "readOnly": True,
        "options": [],
    },
    "transformedState": "SW",
    "type": "Number:Angle",
    "name": "Weather_WindDirection",
    "label": "Wind Direction",
    "category": "wind",
    "tags": ["Dashboard"],
    "groupNames": ["gWeather"],
}

# Number:Pressure - atmospheric pressure
PRESSURE_ITEM = {
    "link": "http://openhab:8080/rest/items/Weather_Pressure",
    "state": "1013.25 hPa",
    "stateDescription": {
        "pattern": "%.1f hPa",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Pressure",
    "name": "Weather_Pressure",
    "label": "Atmospheric Pressure",
    "category": "pressure",
    "tags": ["Dashboard"],
    "groupNames": ["gWeather"],
}

# Number:Volume - water tank
VOLUME_ITEM = {
    "link": "http://openhab:8080/rest/items/Tank_Volume",
    "state": "500 l",
    "stateDescription": {
        "pattern": "%d l",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Volume",
    "name": "Tank_Volume",
    "label": "Tank Volume",
    "category": "water",
    "tags": [],
    "groupNames": [],
}

# Number:Length - rainfall
LENGTH_ITEM = {
    "link": "http://openhab:8080/rest/items/Weather_Rainfall",
    "state": "12.5 mm",
    "stateDescription": {
        "pattern": "%.1f mm",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Length",
    "name": "Weather_Rainfall",
    "label": "Rainfall",
    "category": "rain",
    "tags": ["Dashboard"],
    "groupNames": ["gWeather"],
}

# String item with options (selectable values)
STRING_WITH_OPTIONS_ITEM = {
    "link": "http://openhab:8080/rest/items/Speaker_RepeatMode",
    "state": "ONE",
    "stateDescription": {
        "readOnly": False,
        "options": [
            {"value": "OFF", "label": "Repeat Off"},
            {"value": "ONE", "label": "Repeat One"},
            {"value": "ALL", "label": "Repeat All"},
        ],
    },
    "type": "String",
    "name": "Speaker_RepeatMode",
    "label": "Repeat Mode",
    "category": "player",
    "tags": ["Dashboard"],
    "groupNames": ["gMedia"],
}

# Item with transformedState (JS transformation)
TRANSFORMED_ITEM = {
    "link": "http://openhab:8080/rest/items/System_Uptime",
    "state": "4224248.0",
    "stateDescription": {
        "pattern": "JS(elapsed-time.js):%s",
        "readOnly": True,
        "options": [],
    },
    "transformedState": "48d 21h",
    "type": "Number:Time",
    "name": "System_Uptime",
    "label": "System Uptime",
    "category": "time",
    "tags": [],
    "groupNames": [],
}

# QuantityType without stateDescription (uses default units)
QUANTITY_NO_PATTERN_ITEM = {
    "link": "http://openhab:8080/rest/items/Garage_Temperature",
    "state": "18.5 °C",
    "type": "Number:Temperature",
    "name": "Garage_Temperature",
    "label": "Garage Temperature",
    "category": "temperature",
    "tags": [],
    "groupNames": ["gTemperature"],
}

# Item with empty label (tests name-as-label fallback)
NO_LABEL_ITEM = {
    "link": "http://openhab:8080/rest/items/Sensor_Internal_01",
    "state": "23.5",
    "type": "Number",
    "name": "Sensor_Internal_01",
    "label": "",
    "tags": [],
    "groupNames": [],
}

# Item with special characters (tests ftfy encoding fix)
SPECIAL_CHARS_ITEM = {
    "link": "http://openhab:8080/rest/items/Sensor_Temperature_Ext",
    "state": "22.5 Â°C",  # Double-encoded UTF-8 (°C as Â°C)
    "stateDescription": {
        "pattern": "%.1f °C",
        "readOnly": True,
        "options": [],
    },
    "type": "Number:Temperature",
    "name": "Sensor_Temperature_Ext",
    "label": "External Temperature",
    "category": "temperature",
    "tags": [],
    "groupNames": [],
}

# Rollershutter without stateDescription (tests type-based % unit)
ROLLERSHUTTER_NO_PATTERN_ITEM = {
    "link": "http://openhab:8080/rest/items/Bedroom_Shutter",
    "state": "50",
    "type": "Rollershutter",
    "name": "Bedroom_Shutter",
    "label": "Bedroom Shutter",
    "category": "blinds",
    "tags": [],
    "groupNames": [],
}

# Dimmer without stateDescription (tests type-based % unit)
DIMMER_NO_PATTERN_ITEM = {
    "link": "http://openhab:8080/rest/items/Hallway_Dimmer",
    "state": "80",
    "type": "Dimmer",
    "name": "Hallway_Dimmer",
    "label": "Hallway Dimmer",
    "category": "slider",
    "tags": [],
    "groupNames": [],
}

# =============================================================================
# Collection helpers
# =============================================================================

# All basic item types for parametrized tests
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

# Extended items including new types from analysis
ALL_ITEMS_EXTENDED = ALL_ITEMS + [
    PLAYER_ITEM,
    GROUP_ITEM,
    COLOR_ITEM,
    LOCATION_ITEM,
    IMAGE_ITEM,
    CALL_ITEM,
    DIMENSIONLESS_ITEM,
    SPEED_ITEM,
    ANGLE_ITEM,
    PRESSURE_ITEM,
    VOLUME_ITEM,
    LENGTH_ITEM,
    STRING_WITH_OPTIONS_ITEM,
]

# Items with transformedState (use directly, skip extraction)
TRANSFORMED_ITEMS = [
    ANGLE_ITEM,  # Wind direction with MAP transformation
    TRANSFORMED_ITEM,  # Uptime with JS transformation
]

# Items without stateDescription (tests default unit fallback)
NO_PATTERN_ITEMS = [
    QUANTITY_NO_PATTERN_ITEM,
]

# Edge case items for error guessing
EDGE_CASE_ITEMS = [
    UNDEF_ITEM,
    NULL_ITEM,
    NO_LABEL_ITEM,
    SPECIAL_CHARS_ITEM,
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
