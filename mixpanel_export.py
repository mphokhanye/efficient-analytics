import requests
import json
import csv
import os
from datetime import datetime

# ─── CONFIG (reads from environment variables) ──────────────────────────────────
API_SECRET  = os.environ.get("MIXPANEL_API_SECRET")
FROM_DATE   = os.environ.get("FROM_DATE", "2026-03-28")
TO_DATE     = os.environ.get("TO_DATE",   "2026-04-28")
OUTPUT_FILE = "mixpanel_export.csv"
# ───────────────────────────────────────────────────────────────────────────────

if not API_SECRET:
    raise ValueError("MIXPANEL_API_SECRET environment variable is not set.")

def export_mixpanel_data(api_secret, from_date, to_date):
    """Pull raw events from Mixpanel Export API for a given date range."""
    url = "https://data.mixpanel.com/api/2.0/export"

    print(f"Fetching events from {from_date} to {to_date}...")

    response = requests.get(
        url,
        auth=(api_secret, ""),
        params={
            "from_date": from_date,
            "to_date":   to_date,
        },
        stream=True,
        timeout=120,
    )

    if response.status_code != 200:
        print(f"Error {response.status_code}: {response.text}")
        response.raise_for_status()

    events = []
    for line in response.iter_lines():
        if line:
            try:
                event = json.loads(line)
                events.append(event)
            except json.JSONDecodeError as e:
                print(f"Skipping malformed line: {e}")

    print(f"✓ Fetched {len(events)} events.")
    return events


def flatten_event(event):
    """Flatten nested Mixpanel event JSON into a single dict for CSV export."""
    flat = {}
    flat["event"] = event.get("event", "")

    properties = event.get("properties", {})
    for key, value in properties.items():
        # Convert time from Unix timestamp to readable format
        if key == "time":
            try:
                flat["time"] = datetime.utcfromtimestamp(value).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                flat["time"] = value
        else:
            flat[key] = value

    return flat


def save_to_csv(events, output_file):
    """Save a list of flattened events to a CSV file."""
    if not events:
        print("No events to save.")
        return

    # Collect all unique column names across all events
    all_keys = set()
    flattened_events = []
    for event in events:
        flat = flatten_event(event)
        flattened_events.append(flat)
        all_keys.update(flat.keys())

    # Put important columns first
    priority_cols = ["event", "time", "distinct_id", "$insert_id"]
    other_cols    = sorted(k for k in all_keys if k not in priority_cols)
    fieldnames    = [c for c in priority_cols if c in all_keys] + other_cols

    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(flattened_events)

    print(f"✓ Saved {len(flattened_events)} rows to '{output_file}'")


if __name__ == "__main__":
    events = export_mixpanel_data(API_SECRET, FROM_DATE, TO_DATE)
    save_to_csv(events, OUTPUT_FILE)
    print("Done! Open 'mixpanel_export.csv' to view your data.")
