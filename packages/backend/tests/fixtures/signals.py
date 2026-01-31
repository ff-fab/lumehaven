"""Signal test data factories and collections."""

from lumehaven.core.signal import Signal


def create_signal(
    id: str = "test_signal",
    value: str = "100",
    unit: str = "",
    label: str = "",
) -> Signal:
    """Create a test signal with sensible defaults."""
    return Signal(id=id, value=value, unit=unit, label=label)


# =============================================================================
# Pre-built Signal Collections
# =============================================================================

TEMPERATURE_SIGNALS = [
    Signal(id="oh:LivingRoom_Temp", value="21.5", unit="°C", label="Living Room"),
    Signal(id="oh:Bedroom_Temp", value="19.0", unit="°C", label="Bedroom"),
    Signal(id="oh:Outside_Temp", value="-2.5", unit="°C", label="Outside"),
]

SWITCH_SIGNALS = [
    Signal(id="oh:Light_Living", value="ON", unit="", label="Living Room Light"),
    Signal(id="oh:Light_Kitchen", value="OFF", unit="", label="Kitchen Light"),
]

POWER_SIGNALS = [
    Signal(id="oh:House_Power", value="1250", unit="W", label="Current Power"),
    Signal(id="oh:Solar_Power", value="3500", unit="W", label="Solar Production"),
]

SPECIAL_STATE_SIGNALS = [
    Signal(id="oh:Sensor_Offline", value="UNDEF", unit="", label="Offline Sensor"),
    Signal(id="oh:Sensor_NULL", value="NULL", unit="", label="NULL Sensor"),
]

ALL_TEST_SIGNALS = (
    TEMPERATURE_SIGNALS + SWITCH_SIGNALS + POWER_SIGNALS + SPECIAL_STATE_SIGNALS
)
