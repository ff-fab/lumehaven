"""Signal test data factories and collections.

Updated for ADR-010 enriched Signal model: typed value, display_value,
available, signal_type.
"""

from lumehaven.core.signal import Signal, SignalType, SignalValue


def create_signal(
    id: str = "test_signal",
    value: SignalValue = "100",
    unit: str = "",
    label: str = "",
    display_value: str | None = None,
    available: bool = True,
    signal_type: SignalType = SignalType.STRING,
) -> Signal:
    """Create a test signal with sensible defaults.

    If ``display_value`` is not given, it defaults to ``str(value)``
    when ``value`` is not None, or ``""`` when ``value`` is None.
    """
    if display_value is None:
        display_value = str(value) if value is not None else ""
    return Signal(
        id=id,
        value=value,
        unit=unit,
        label=label,
        display_value=display_value,
        available=available,
        signal_type=signal_type,
    )


# =============================================================================
# Pre-built Signal Collections
# =============================================================================

TEMPERATURE_SIGNALS = [
    Signal(
        id="oh:LivingRoom_Temp",
        value=21.5,
        display_value="21.5",
        unit="°C",
        label="Living Room",
        signal_type=SignalType.NUMBER,
    ),
    Signal(
        id="oh:Bedroom_Temp",
        value=19.0,
        display_value="19.0",
        unit="°C",
        label="Bedroom",
        signal_type=SignalType.NUMBER,
    ),
    Signal(
        id="oh:Outside_Temp",
        value=-2.5,
        display_value="-2.5",
        unit="°C",
        label="Outside",
        signal_type=SignalType.NUMBER,
    ),
]

SWITCH_SIGNALS = [
    Signal(
        id="oh:Light_Living",
        value=True,
        display_value="An",
        unit="",
        label="Living Room Light",
        signal_type=SignalType.BOOLEAN,
    ),
    Signal(
        id="oh:Light_Kitchen",
        value=False,
        display_value="Aus",
        unit="",
        label="Kitchen Light",
        signal_type=SignalType.BOOLEAN,
    ),
]

POWER_SIGNALS = [
    Signal(
        id="oh:House_Power",
        value=1250,
        display_value="1250",
        unit="W",
        label="Current Power",
        signal_type=SignalType.NUMBER,
    ),
    Signal(
        id="oh:Solar_Power",
        value=3500,
        display_value="3500",
        unit="W",
        label="Solar Production",
        signal_type=SignalType.NUMBER,
    ),
]

SPECIAL_STATE_SIGNALS = [
    Signal(
        id="oh:Sensor_Offline",
        value=None,
        display_value="",
        unit="",
        label="Offline Sensor",
        available=False,
    ),
    Signal(
        id="oh:Sensor_NULL",
        value=None,
        display_value="",
        unit="",
        label="NULL Sensor",
        available=False,
    ),
]

ALL_TEST_SIGNALS = (
    TEMPERATURE_SIGNALS + SWITCH_SIGNALS + POWER_SIGNALS + SPECIAL_STATE_SIGNALS
)
