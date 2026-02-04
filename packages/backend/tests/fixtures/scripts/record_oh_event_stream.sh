#!/bin/bash
# filepath: /workspace/record_event_stream.sh
# Records OpenHAB SSE events using the exact adapter flow

OPENHAB_URL="http://192.168.12.202:8080"
DURATION=300  # 5 minutes

echo "=== OpenHAB SSE Event Recorder ==="
echo "URL: $OPENHAB_URL"
echo "Duration: ${DURATION}s"
echo ""

# Step 1: Fetch item names
echo "Step 1: Fetching item names..."
ITEMS_JSON=$(curl -s "${OPENHAB_URL}/rest/items?fields=name")
ITEM_NAMES=$(echo "$ITEMS_JSON" | python3 -c "
import sys, json
items = json.load(sys.stdin)
names = [item['name'] for item in items]
print(json.dumps(names))
")
ITEM_COUNT=$(echo "$ITEM_NAMES" | python3 -c "import sys,json; print(len(json.load(sys.stdin)))")
echo "Using $ITEM_COUNT items for subscription"

# Step 2: Use Python to handle the async SSE + subscription flow
# (bash can't easily do "read first line, then POST, then continue reading")
echo ""
echo "Step 2: Starting SSE stream with subscription..."
echo "Recording to /tmp/openhab_sse_events.log"
echo "Press Ctrl+C to stop early"
echo "---"

python3 << 'PYTHON_SCRIPT'
import json
import sys
import time
import signal
from urllib.request import urlopen, Request

OPENHAB_URL = "http://192.168.12.202:8080"
DURATION = 300
OUTPUT_FILE = "/tmp/openhab_sse_events.log"

# Get item names
items_resp = urlopen(f"{OPENHAB_URL}/rest/items?fields=name")
items = json.loads(items_resp.read().decode())
item_names = [item["name"] for item in items]
print(f"Subscribing to {len(item_names)} items")

# Open SSE stream
req = Request(
    f"{OPENHAB_URL}/rest/events/states",
    headers={"Accept": "text/event-stream"}
)
stream = urlopen(req, timeout=DURATION + 10)

connection_id = None
subscribed = False
start_time = time.time()
event_count = 0

with open(OUTPUT_FILE, "w") as f:
    try:
        while time.time() - start_time < DURATION:
            line = stream.readline().decode("utf-8").strip()

            if not line:
                continue

            # Write all lines to file
            f.write(line + "\n")
            f.flush()

            if line.startswith("data:"):
                data_str = line[5:].strip()

                # First data message contains connection ID
                if not subscribed and connection_id is None:
                    try:
                        # Connection ID is just a plain string or in JSON
                        if data_str.startswith('"'):
                            connection_id = json.loads(data_str)
                        else:
                            connection_id = data_str
                        print(f"Got connection ID: {connection_id}")

                        # Now subscribe items to this connection
                        subscribe_req = Request(
                            f"{OPENHAB_URL}/rest/events/states/{connection_id}",
                            data=json.dumps(item_names).encode(),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        subscribe_resp = urlopen(subscribe_req)
                        print(f"Subscribed! Status: {subscribe_resp.status}")
                        subscribed = True
                        continue
                    except Exception as e:
                        print(f"Note: {e}, continuing...")

                event_count += 1
                # Print progress every 10 events
                if event_count % 10 == 0:
                    elapsed = int(time.time() - start_time)
                    print(f"  {event_count} events captured ({elapsed}s elapsed)")

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")

print(f"\n---")
print(f"Recording complete!")
print(f"Total events: {event_count}")
print(f"File: {OUTPUT_FILE}")
PYTHON_SCRIPT

echo ""
echo "Preview (first 30 lines):"
head -30 /tmp/openhab_sse_events.log
