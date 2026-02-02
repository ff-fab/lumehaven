#!/usr/bin/env python3
"""Analyze recorded OpenHAB data for test fixture extraction.

This script parses raw OpenHAB API recordings, extracts valuable test patterns,
anonymizes sensitive data, and identifies coverage gaps against existing fixtures.

Usage:
    python scripts/analyze_openhab_data.py /tmp/openhab_items_snapshot.json \
        /tmp/openhab_sse_events.log /tmp/openhab_root_snapshot.json

Output:
    - Console summary with discovered types, patterns, and edge cases
    - JSON report at /tmp/openhab_analysis_report.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# =============================================================================
# Anonymization
# =============================================================================

# Patterns for sensitive data
IP_PATTERN = re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")
URL_PATTERN = re.compile(r"https?://[^\s/\"']+")
PHONE_PATTERN = re.compile(r"\b\d{10,15}\b")

# Mapping caches for consistent anonymization
_ip_map: dict[str, str] = {}
_name_map: dict[str, str] = {}
_name_counter = 0


def anonymize_ip(ip: str) -> str:
    """Replace IP with consistent anonymized version."""
    if ip not in _ip_map:
        _ip_map[ip] = f"192.168.1.{len(_ip_map) + 1}"
    return _ip_map[ip]


def anonymize_name(name: str) -> str:
    """Generate consistent anonymized device/item name."""
    global _name_counter
    if name not in _name_map:
        # Extract type hints from name for realistic anonymization
        # e.g., "LivingRoom_Temperature" -> "Room1_Temperature"
        parts = name.split("_")
        if len(parts) > 1:
            _name_counter += 1
            _name_map[name] = f"Device{_name_counter}_{parts[-1]}"
        else:
            _name_counter += 1
            _name_map[name] = f"Item_{_name_counter}"
    return _name_map[name]


def anonymize_string(s: str) -> str:
    """Anonymize IPs and phone numbers in a string."""
    result = IP_PATTERN.sub(lambda m: anonymize_ip(m.group()), s)
    result = PHONE_PATTERN.sub("1234567890", result)
    return result


def anonymize_item(item: dict[str, Any]) -> dict[str, Any]:
    """Anonymize sensitive fields in an item dict."""
    result = item.copy()

    # Anonymize name and related fields
    if "name" in result:
        original_name = result["name"]
        result["name"] = anonymize_name(original_name)

    if "label" in result:
        result["label"] = anonymize_string(result["label"])

    if "link" in result:
        result["link"] = URL_PATTERN.sub("http://openhab:8080", result["link"])

    if "state" in result:
        result["state"] = anonymize_string(str(result["state"]))

    if "transformedState" in result:
        result["transformedState"] = anonymize_string(str(result["transformedState"]))

    if "groupNames" in result:
        result["groupNames"] = [f"g{anonymize_name(g)}" for g in result["groupNames"]]

    return result


# =============================================================================
# Data Structures
# =============================================================================


@dataclass
class ItemTypeInfo:
    """Information about a discovered item type."""

    type_name: str
    count: int = 0
    has_state_description: int = 0
    has_transformed_state: int = 0
    has_pattern: int = 0
    has_options: int = 0
    state_examples: list[str] = field(default_factory=list)
    pattern_examples: list[str] = field(default_factory=list)
    unit_examples: list[str] = field(default_factory=list)


@dataclass
class SSEEventInfo:
    """Information about discovered SSE event types."""

    event_type: str
    count: int = 0
    payload_types: Counter = field(default_factory=Counter)
    has_display_state: int = 0
    example_payloads: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """Complete analysis report."""

    measurement_system: str = "SI"
    total_items: int = 0
    total_events: int = 0

    # Item analysis
    item_types: dict[str, ItemTypeInfo] = field(default_factory=dict)
    special_states: Counter = field(default_factory=Counter)
    encoding_issues: list[str] = field(default_factory=list)

    # SSE analysis
    sse_events: dict[str, SSEEventInfo] = field(default_factory=dict)

    # Coverage gaps
    missing_from_fixtures: list[str] = field(default_factory=list)

    # Extracted examples for fixtures
    fixture_candidates: dict[str, dict[str, Any]] = field(default_factory=dict)


# =============================================================================
# Existing Fixtures (for gap analysis)
# =============================================================================

EXISTING_FIXTURE_TYPES = {
    "Number:Temperature",
    "Switch",
    "Dimmer",
    "Number:Power",
    "Number:Energy",
    "String",
    "Contact",
    "Rollershutter",
    "DateTime",
    "Number",  # via NULL_ITEM
}

EXISTING_SPECIAL_STATES = {"UNDEF", "NULL"}

EXISTING_SSE_EVENTS = {"ItemStateEvent", "ItemStateChangedEvent", "ItemCommandEvent"}


# =============================================================================
# Parsers
# =============================================================================


def parse_items_snapshot(path: Path, report: AnalysisReport) -> None:
    """Parse items snapshot JSON and extract type/pattern information."""
    with open(path) as f:
        items = json.load(f)

    report.total_items = len(items)

    for item in items:
        item_type = item.get("type", "Unknown")

        # Track item type statistics
        if item_type not in report.item_types:
            report.item_types[item_type] = ItemTypeInfo(type_name=item_type)

        info = report.item_types[item_type]
        info.count += 1

        state = item.get("state", "")

        # Track special states
        if state in ("UNDEF", "NULL"):
            report.special_states[state] += 1

        # Track state description features
        state_desc = item.get("stateDescription")
        if state_desc:
            info.has_state_description += 1
            pattern = state_desc.get("pattern")
            if pattern:
                info.has_pattern += 1
                if pattern not in info.pattern_examples:
                    info.pattern_examples.append(pattern)
                # Extract unit from pattern
                unit_match = re.search(r"(?:%[^%]*)?([°%€$£¥a-zA-Z/³²]+)$", pattern)
                if unit_match:
                    unit = unit_match.group(1)
                    if unit not in info.unit_examples:
                        info.unit_examples.append(unit)
            options = state_desc.get("options")
            if options:
                info.has_options += 1

        # Track transformed state
        if "transformedState" in item:
            info.has_transformed_state += 1

        # Keep example states (max 3 per type)
        if len(info.state_examples) < 3 and state not in info.state_examples:
            info.state_examples.append(anonymize_string(state))

        # Check for encoding issues
        if "Â" in state or "â€" in state:
            report.encoding_issues.append(f"{item_type}: {state[:50]}")

        # Store candidate for fixture if type not in existing
        if (
            item_type not in EXISTING_FIXTURE_TYPES
            and item_type not in report.fixture_candidates
        ):
            report.fixture_candidates[item_type] = anonymize_item(item)

        # Also capture transformed state examples
        if (
            "transformedState" in item
            and "transformedState" not in report.fixture_candidates
        ):
            report.fixture_candidates["transformedState"] = anonymize_item(item)


def parse_sse_events(path: Path, report: AnalysisReport) -> None:
    """Parse SSE event log and extract event type/payload information."""
    with open(path) as f:
        content = f.read()

    # SSE format: "event: EventType\ndata: {json}\n\n"
    # Or just "data: {json}\n\n"
    event_blocks = re.split(r"\n\n+", content)

    for block in event_blocks:
        block = block.strip()
        if not block:
            continue

        # Extract data
        data_match = re.search(r"^data:\s*(.+)$", block, re.MULTILINE)
        if not data_match:
            continue

        data_str = data_match.group(1).strip()

        # Try to parse as JSON
        try:
            data = json.loads(data_str)
        except json.JSONDecodeError:
            # Might be a connection ID or malformed
            continue

        report.total_events += 1

        # Handle state subscription events (dict of item -> state)
        if isinstance(data, dict) and "topic" not in data:
            # State subscription batch: {item: {state: ..., displayState: ...}}
            for item_name, payload in data.items():
                if not isinstance(payload, dict):
                    continue

                event_type = "StateSubscription"
                if event_type not in report.sse_events:
                    report.sse_events[event_type] = SSEEventInfo(event_type=event_type)

                info = report.sse_events[event_type]
                info.count += 1

                if "displayState" in payload:
                    info.has_display_state += 1

                # Track payload type
                payload_type = payload.get("type", "Unknown")
                info.payload_types[payload_type] += 1

                # Keep example payloads (max 5)
                if len(info.example_payloads) < 5:
                    info.example_payloads.append(
                        {"item": anonymize_name(item_name), "payload": payload}
                    )

        # Handle traditional SSE events with topic
        elif isinstance(data, dict) and "topic" in data:
            event_type = data.get("type", "Unknown")
            if event_type not in report.sse_events:
                report.sse_events[event_type] = SSEEventInfo(event_type=event_type)

            info = report.sse_events[event_type]
            info.count += 1

            # Parse payload JSON
            payload_str = data.get("payload", "{}")
            try:
                payload = json.loads(payload_str)
                payload_type = payload.get("type", "Unknown")
                info.payload_types[payload_type] += 1

                if "displayState" in payload:
                    info.has_display_state += 1

                # Keep example payloads
                if len(info.example_payloads) < 5:
                    info.example_payloads.append(payload)
            except json.JSONDecodeError:
                pass


def parse_root_snapshot(path: Path, report: AnalysisReport) -> None:
    """Parse root endpoint for measurement system."""
    with open(path) as f:
        data = json.load(f)

    report.measurement_system = data.get("measurementSystem", "SI")


# =============================================================================
# Gap Analysis
# =============================================================================


def analyze_gaps(report: AnalysisReport) -> None:
    """Identify coverage gaps compared to existing fixtures."""
    # Item types not in fixtures
    for item_type in report.item_types:
        if item_type not in EXISTING_FIXTURE_TYPES:
            report.missing_from_fixtures.append(f"Item type: {item_type}")

    # SSE events not in fixtures
    for event_type in report.sse_events:
        if event_type not in EXISTING_SSE_EVENTS:
            report.missing_from_fixtures.append(f"SSE event: {event_type}")

    # Check for features not covered
    for info in report.item_types.values():
        if info.has_transformed_state > 0:
            count = info.has_transformed_state
            report.missing_from_fixtures.append(
                f"transformedState ({info.type_name}: {count} items)"
            )
        if info.has_options > 0:
            report.missing_from_fixtures.append(
                f"stateDescription.options ({info.type_name}: {info.has_options} items)"
            )


# =============================================================================
# Output
# =============================================================================


def print_summary(report: AnalysisReport) -> None:
    """Print human-readable summary to console."""
    print("\n" + "=" * 70)
    print("OPENHAB DATA ANALYSIS REPORT")
    print("=" * 70)

    print(f"\nMeasurement System: {report.measurement_system}")
    print(f"Total Items: {report.total_items}")
    print(f"Total SSE Events: {report.total_events}")

    print("\n" + "-" * 70)
    print("ITEM TYPES")
    print("-" * 70)
    for type_name, info in sorted(report.item_types.items(), key=lambda x: -x[1].count):
        marker = "✓" if type_name in EXISTING_FIXTURE_TYPES else "✗ NEW"
        print(f"\n  {marker} {type_name} (count: {info.count})")
        if info.has_state_description:
            print(f"      stateDescription: {info.has_state_description}")
        if info.has_pattern:
            print(f"      patterns: {info.pattern_examples[:3]}")
        if info.unit_examples:
            print(f"      units: {info.unit_examples[:5]}")
        if info.has_transformed_state:
            print(f"      transformedState: {info.has_transformed_state}")
        if info.has_options:
            print(f"      options: {info.has_options}")
        if info.state_examples:
            print(f"      state examples: {info.state_examples}")

    print("\n" + "-" * 70)
    print("SPECIAL STATES")
    print("-" * 70)
    for state, count in report.special_states.items():
        marker = "✓" if state in EXISTING_SPECIAL_STATES else "✗ NEW"
        print(f"  {marker} {state}: {count}")

    print("\n" + "-" * 70)
    print("SSE EVENTS")
    print("-" * 70)
    for event_type, info in sorted(
        report.sse_events.items(), key=lambda x: -x[1].count
    ):
        marker = "✓" if event_type in EXISTING_SSE_EVENTS else "✗ NEW"
        print(f"\n  {marker} {event_type} (count: {info.count})")
        print(f"      payload types: {dict(info.payload_types)}")
        if info.has_display_state:
            print(f"      has displayState: {info.has_display_state}")

    if report.encoding_issues:
        print("\n" + "-" * 70)
        print("ENCODING ISSUES")
        print("-" * 70)
        for issue in report.encoding_issues[:10]:
            print(f"  ⚠ {issue}")

    print("\n" + "-" * 70)
    print("COVERAGE GAPS (for fixture expansion)")
    print("-" * 70)
    # Deduplicate
    seen = set()
    for gap in report.missing_from_fixtures:
        base = gap.split("(")[0].strip()
        if base not in seen:
            seen.add(base)
            print(f"  • {gap}")

    print("\n" + "=" * 70)


def save_json_report(report: AnalysisReport, output_path: Path) -> None:
    """Save detailed JSON report."""
    data = {
        "measurement_system": report.measurement_system,
        "total_items": report.total_items,
        "total_events": report.total_events,
        "item_types": {
            k: {
                "type_name": v.type_name,
                "count": v.count,
                "has_state_description": v.has_state_description,
                "has_transformed_state": v.has_transformed_state,
                "has_pattern": v.has_pattern,
                "has_options": v.has_options,
                "state_examples": v.state_examples,
                "pattern_examples": v.pattern_examples,
                "unit_examples": v.unit_examples,
            }
            for k, v in report.item_types.items()
        },
        "special_states": dict(report.special_states),
        "sse_events": {
            k: {
                "event_type": v.event_type,
                "count": v.count,
                "payload_types": dict(v.payload_types),
                "has_display_state": v.has_display_state,
                "example_payloads": v.example_payloads,
            }
            for k, v in report.sse_events.items()
        },
        "encoding_issues": report.encoding_issues,
        "missing_from_fixtures": list(set(report.missing_from_fixtures)),
        "fixture_candidates": report.fixture_candidates,
    }

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nJSON report saved to: {output_path}")


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze recorded OpenHAB data for test fixtures"
    )
    parser.add_argument(
        "items_file",
        type=Path,
        help="Path to items snapshot JSON (from /rest/items)",
    )
    parser.add_argument(
        "sse_file",
        type=Path,
        help="Path to SSE events log",
    )
    parser.add_argument(
        "root_file",
        type=Path,
        help="Path to root snapshot JSON (from /rest/)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("/tmp/openhab_analysis_report.json"),
        help="Output path for JSON report",
    )

    args = parser.parse_args()

    # Validate inputs
    for path in [args.items_file, args.sse_file, args.root_file]:
        if not path.exists():
            print(f"Error: File not found: {path}", file=sys.stderr)
            return 1

    report = AnalysisReport()

    # Parse all data sources
    print("Parsing items snapshot...")
    parse_items_snapshot(args.items_file, report)

    print("Parsing SSE events...")
    parse_sse_events(args.sse_file, report)

    print("Parsing root snapshot...")
    parse_root_snapshot(args.root_file, report)

    # Analyze coverage gaps
    analyze_gaps(report)

    # Output
    print_summary(report)
    save_json_report(report, args.output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
