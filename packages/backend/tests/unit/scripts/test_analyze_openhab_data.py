"""Unit tests for tests/scripts/analyze_openhab_data.py — OpenHAB data analysis.

Test Techniques Used:
- Specification-based Testing: Verifying parsers, anonymization, gap analysis
- Equivalence Partitioning: Item types (known vs new),
  event formats (subscription vs topic)
- Error Guessing: Empty data, encoding issues, malformed SSE blocks
- Branch Coverage: Anonymization paths (IP, name with/without underscore, string)
- State Transition: Anonymization caches (consistent mapping across calls)

Note: Module-level mutable globals (_ip_map, _name_map, _name_counter) are reset
in the autouse fixture to prevent cross-test contamination.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from tests.scripts import analyze_openhab_data
from tests.scripts.analyze_openhab_data import (
    AnalysisReport,
    ItemTypeInfo,
    SSEEventInfo,
    analyze_gaps,
    anonymize_ip,
    anonymize_item,
    anonymize_name,
    anonymize_string,
    main,
    parse_items_snapshot,
    parse_root_snapshot,
    parse_sse_events,
    save_json_report,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(autouse=True)
def _reset_anonymization_globals() -> None:
    """Reset module-level anonymization caches before each test.

    The module uses mutable globals (_ip_map, _name_map, _name_counter) for
    consistent anonymization within a single run. Tests must start clean.
    """
    analyze_openhab_data._ip_map.clear()
    analyze_openhab_data._name_map.clear()
    analyze_openhab_data._name_counter = 0


def _write_json(path: Path, data: Any) -> None:
    """Write data as JSON to a file."""
    path.write_text(json.dumps(data))


def _make_item(
    *,
    name: str = "LivingRoom_Temperature",
    item_type: str = "Number:Temperature",
    state: str = "21.5",
    label: str = "Living Room Temp",
    link: str = "http://openhab:8080/rest/items/LivingRoom_Temperature",
    state_description: dict[str, Any] | None = None,
    transformed_state: str | None = None,
    group_names: list[str] | None = None,
) -> dict[str, Any]:
    """Factory for minimal OpenHAB item dicts."""
    item: dict[str, Any] = {
        "name": name,
        "type": item_type,
        "state": state,
        "label": label,
        "link": link,
    }
    if state_description is not None:
        item["stateDescription"] = state_description
    if transformed_state is not None:
        item["transformedState"] = transformed_state
    if group_names is not None:
        item["groupNames"] = group_names
    return item


# =============================================================================
# Anonymization
# =============================================================================


class TestAnonymizeIp:
    """Tests for anonymize_ip() — consistent IP address anonymization.

    Technique: State Transition — same IP always gets same anonymized value.
    """

    def test_first_ip_gets_first_index(self) -> None:
        assert anonymize_ip("10.0.0.1") == "192.168.1.1"

    def test_second_ip_gets_second_index(self) -> None:
        anonymize_ip("10.0.0.1")
        assert anonymize_ip("10.0.0.2") == "192.168.1.2"

    def test_same_ip_returns_same_mapping(self) -> None:
        """Consistency: repeated calls with same IP return identical result."""
        first = anonymize_ip("172.16.0.100")
        second = anonymize_ip("172.16.0.100")
        assert first == second


class TestAnonymizeName:
    """Tests for anonymize_name() — device/item name anonymization.

    Technique: Equivalence Partitioning — names with underscores vs without.
    """

    def test_name_with_underscore_keeps_suffix(self) -> None:
        """Multi-part names preserve the last segment as a type hint."""
        result = anonymize_name("LivingRoom_Temperature")
        assert result == "Device1_Temperature"

    def test_name_without_underscore_uses_item_prefix(self) -> None:
        """Single-word names use the Item_ prefix."""
        result = anonymize_name("Thermostat")
        assert result == "Item_1"

    def test_consistent_mapping(self) -> None:
        """Same name always maps to same anonymized name."""
        first = anonymize_name("Kitchen_Humidity")
        second = anonymize_name("Kitchen_Humidity")
        assert first == second

    def test_different_names_get_different_numbers(self) -> None:
        a = anonymize_name("Device_A")
        b = anonymize_name("Device_B")
        assert a != b


class TestAnonymizeString:
    """Tests for anonymize_string() — general string anonymization.

    Technique: Specification-based Testing — IP and phone number replacement.
    """

    def test_replaces_ip_addresses(self) -> None:
        result = anonymize_string("Connected to 10.0.0.1 OK")
        assert "10.0.0.1" not in result
        assert "192.168.1." in result

    def test_replaces_phone_numbers(self) -> None:
        result = anonymize_string("Phone: 1234567890123")
        assert "1234567890123" not in result
        assert "1234567890" in result

    def test_preserves_non_sensitive_text(self) -> None:
        result = anonymize_string("Temperature is 21.5 °C")
        assert result == "Temperature is 21.5 °C"


class TestAnonymizeItem:
    """Tests for anonymize_item() — full item dict anonymization.

    Technique: Specification-based Testing — each sensitive field is handled.
    """

    def test_anonymizes_name(self) -> None:
        item = _make_item(name="Kitchen_Light")
        result = anonymize_item(item)
        assert result["name"] != "Kitchen_Light"
        assert "Device" in result["name"] or "Item" in result["name"]

    def test_anonymizes_link_urls(self) -> None:
        item = _make_item(link="http://192.168.50.10:8080/rest/items/Foo")
        result = anonymize_item(item)
        assert "192.168.50.10" not in result["link"]

    def test_anonymizes_group_names(self) -> None:
        item = _make_item(group_names=["gLivingRoom_Lights", "gAll"])
        result = anonymize_item(item)
        assert all(g.startswith("g") for g in result["groupNames"])
        assert "gLivingRoom_Lights" not in result["groupNames"]

    def test_does_not_modify_original(self) -> None:
        """Returns a new dict, original is unchanged."""
        item = _make_item(name="Original_Name")
        anonymize_item(item)
        assert item["name"] == "Original_Name"

    def test_anonymizes_transformed_state(self) -> None:
        item = _make_item(transformed_state="10.0.0.1 online")
        result = anonymize_item(item)
        assert "10.0.0.1" not in result["transformedState"]


# =============================================================================
# Parsers
# =============================================================================


class TestParseItemsSnapshot:
    """Tests for parse_items_snapshot() — item JSON parsing.

    Technique: Specification-based Testing — populates report fields correctly.
    """

    def test_counts_total_items(self, tmp_path: Path) -> None:
        items = [
            _make_item(),
            _make_item(
                name="Kitchen_Light",
                item_type="Switch",
                state="ON",
            ),
        ]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        assert report.total_items == 2

    def test_tracks_item_types(self, tmp_path: Path) -> None:
        items = [
            _make_item(item_type="Switch", state="ON"),
            _make_item(item_type="Switch", state="OFF", name="Other_Switch"),
            _make_item(item_type="Dimmer", state="50", name="Hall_Dimmer"),
        ]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        assert report.item_types["Switch"].count == 2
        assert report.item_types["Dimmer"].count == 1

    def test_tracks_special_states(self, tmp_path: Path) -> None:
        items = [
            _make_item(state="UNDEF"),
            _make_item(state="NULL", name="Offline_Sensor"),
        ]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        assert report.special_states["UNDEF"] == 1
        assert report.special_states["NULL"] == 1

    def test_extracts_state_description_patterns(self, tmp_path: Path) -> None:
        items = [
            _make_item(
                state_description={"pattern": "%.1f °C"},
            )
        ]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        info = report.item_types["Number:Temperature"]
        assert info.has_pattern == 1
        assert "%.1f °C" in info.pattern_examples

    def test_detects_encoding_issues(self, tmp_path: Path) -> None:
        """Mojibake markers (Â, â€) are flagged."""
        items = [_make_item(state="21.5 Â°C")]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        assert len(report.encoding_issues) == 1

    def test_stores_fixture_candidates_for_new_types(self, tmp_path: Path) -> None:
        """Types not in EXISTING_FIXTURE_TYPES are stored as fixture candidates."""
        items = [_make_item(item_type="Color", state="120,100,50", name="LED_Strip")]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        assert "Color" in report.fixture_candidates

    def test_tracks_transformed_state(self, tmp_path: Path) -> None:
        items = [_make_item(transformed_state="21.5 °C")]
        _write_json(tmp_path / "items.json", items)

        report = AnalysisReport()
        parse_items_snapshot(tmp_path / "items.json", report)
        info = report.item_types["Number:Temperature"]
        assert info.has_transformed_state == 1


class TestParseSseEvents:
    """Tests for parse_sse_events() — SSE event log parsing.

    Technique: Equivalence Partitioning — subscription batches vs topic events.
    """

    def test_parses_topic_events(self, tmp_path: Path) -> None:
        """Traditional SSE events with 'topic' field."""
        payload = json.dumps({"type": "Decimal", "value": "21.5"})
        event = json.dumps(
            {
                "topic": "openhab/items/Temp/state",
                "type": "ItemStateEvent",
                "payload": payload,
            }
        )
        sse_file = tmp_path / "events.log"
        sse_file.write_text(f"data: {event}\n\n")

        report = AnalysisReport()
        parse_sse_events(sse_file, report)
        assert report.total_events == 1
        assert "ItemStateEvent" in report.sse_events

    def test_parses_subscription_batches(self, tmp_path: Path) -> None:
        """Subscription batch: dict without 'topic' key."""
        batch = json.dumps(
            {
                "Temp_Sensor": {"state": "21.5", "type": "Decimal"},
                "Light_Switch": {"state": "ON", "type": "OnOff"},
            }
        )
        sse_file = tmp_path / "events.log"
        sse_file.write_text(f"data: {batch}\n\n")

        report = AnalysisReport()
        parse_sse_events(sse_file, report)
        assert "StateSubscription" in report.sse_events
        assert report.sse_events["StateSubscription"].count == 2

    def test_skips_malformed_blocks(self, tmp_path: Path) -> None:
        """Blocks without 'data:' prefix are ignored."""
        sse_file = tmp_path / "events.log"
        sse_file.write_text("event: keepalive\n\n")

        report = AnalysisReport()
        parse_sse_events(sse_file, report)
        assert report.total_events == 0

    def test_skips_invalid_json(self, tmp_path: Path) -> None:
        """Non-JSON data lines are silently skipped."""
        sse_file = tmp_path / "events.log"
        sse_file.write_text("data: not-json-content\n\n")

        report = AnalysisReport()
        parse_sse_events(sse_file, report)
        assert report.total_events == 0

    def test_tracks_display_state_in_subscriptions(self, tmp_path: Path) -> None:
        """displayState presence is counted in subscription events."""
        batch = json.dumps(
            {
                "Temp": {"state": "21.5", "type": "Decimal", "displayState": "21.5 °C"},
            }
        )
        sse_file = tmp_path / "events.log"
        sse_file.write_text(f"data: {batch}\n\n")

        report = AnalysisReport()
        parse_sse_events(sse_file, report)
        assert report.sse_events["StateSubscription"].has_display_state == 1


class TestParseRootSnapshot:
    """Tests for parse_root_snapshot() — root endpoint parsing.

    Technique: Specification-based Testing — measurement system extraction.
    """

    def test_extracts_measurement_system(self, tmp_path: Path) -> None:
        _write_json(tmp_path / "root.json", {"measurementSystem": "US"})

        report = AnalysisReport()
        parse_root_snapshot(tmp_path / "root.json", report)
        assert report.measurement_system == "US"

    def test_defaults_to_si(self, tmp_path: Path) -> None:
        """Missing measurementSystem defaults to SI."""
        _write_json(tmp_path / "root.json", {})

        report = AnalysisReport()
        parse_root_snapshot(tmp_path / "root.json", report)
        assert report.measurement_system == "SI"


# =============================================================================
# Gap Analysis
# =============================================================================


class TestAnalyzeGaps:
    """Tests for analyze_gaps() — fixture coverage gap detection.

    Technique: Equivalence Partitioning — known vs unknown item/event types.
    """

    def test_flags_unknown_item_type(self) -> None:
        report = AnalysisReport()
        report.item_types["Color"] = ItemTypeInfo(type_name="Color", count=1)
        analyze_gaps(report)
        assert any("Color" in gap for gap in report.missing_from_fixtures)

    def test_does_not_flag_known_item_type(self) -> None:
        report = AnalysisReport()
        report.item_types["Switch"] = ItemTypeInfo(type_name="Switch", count=5)
        analyze_gaps(report)
        # Switch is in EXISTING_FIXTURE_TYPES
        item_gaps = [
            g for g in report.missing_from_fixtures if g.startswith("Item type")
        ]
        assert not any("Switch" in g for g in item_gaps)

    def test_flags_unknown_sse_event(self) -> None:
        report = AnalysisReport()
        report.sse_events["GroupStateChangedEvent"] = SSEEventInfo(
            event_type="GroupStateChangedEvent", count=3
        )
        analyze_gaps(report)
        assert any(
            "GroupStateChangedEvent" in gap for gap in report.missing_from_fixtures
        )

    def test_flags_transformed_state_presence(self) -> None:
        report = AnalysisReport()
        report.item_types["Switch"] = ItemTypeInfo(
            type_name="Switch", count=2, has_transformed_state=1
        )
        analyze_gaps(report)
        assert any("transformedState" in gap for gap in report.missing_from_fixtures)

    def test_flags_options_presence(self) -> None:
        report = AnalysisReport()
        report.item_types["String"] = ItemTypeInfo(
            type_name="String", count=1, has_options=1
        )
        analyze_gaps(report)
        assert any("options" in gap for gap in report.missing_from_fixtures)


# =============================================================================
# Output
# =============================================================================


class TestSaveJsonReport:
    """Tests for save_json_report() — JSON file output.

    Technique: Specification-based Testing — verifying report structure.
    """

    def test_creates_json_file(self, tmp_path: Path) -> None:
        report = AnalysisReport(measurement_system="SI", total_items=5, total_events=10)
        output = tmp_path / "report.json"
        save_json_report(report, output)

        assert output.exists()
        data = json.loads(output.read_text())
        assert data["measurement_system"] == "SI"
        assert data["total_items"] == 5
        assert data["total_events"] == 10

    def test_includes_item_types(self, tmp_path: Path) -> None:
        report = AnalysisReport()
        report.item_types["Switch"] = ItemTypeInfo(type_name="Switch", count=3)
        output = tmp_path / "report.json"
        save_json_report(report, output)

        data = json.loads(output.read_text())
        assert "Switch" in data["item_types"]
        assert data["item_types"]["Switch"]["count"] == 3


# =============================================================================
# main() CLI
# =============================================================================


class TestMain:
    """Tests for main() — CLI entry point.

    Technique: Error Guessing — missing files, valid execution.
    """

    def test_exit_1_missing_input_file(self, tmp_path: Path) -> None:
        """Exit code 1 when an input file doesn't exist."""
        items = tmp_path / "items.json"
        sse = tmp_path / "events.log"
        root = tmp_path / "root.json"
        # Only create some files
        _write_json(items, [])
        sse.write_text("")
        # root is missing

        with patch("sys.argv", ["prog", str(items), str(sse), str(root)]):
            result = main()
        assert result == 1

    def test_exit_0_valid_files(self, tmp_path: Path) -> None:
        """Exit code 0 with valid input files."""
        items = tmp_path / "items.json"
        sse = tmp_path / "events.log"
        root = tmp_path / "root.json"
        output = tmp_path / "report.json"

        _write_json(items, [_make_item()])
        sse.write_text("")
        _write_json(root, {"measurementSystem": "SI"})

        args = [
            "prog",
            str(items),
            str(sse),
            str(root),
            "-o",
            str(output),
        ]
        with patch("sys.argv", args):
            result = main()
        assert result == 0
        assert output.exists()
