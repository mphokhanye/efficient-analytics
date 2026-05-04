import requests
import json
import csv
import os
from datetime import datetime

# ─────────────────────────────────────────────
# CONFIG (GitHub Secrets or local env vars)
# ─────────────────────────────────────────────
API_SECRET = os.environ.get("MIXPANEL_API_SECRET")
FROM_DATE  = os.environ.get("FROM_DATE", "2026-03-28")
TO_DATE    = os.environ.get("TO_DATE", "2026-04-28")

OUTPUT_FILE = "mixpanel_export.csv"

if not API_SECRET:
    raise ValueError("Missing MIXPANEL_API_SECRET environment variable")

# ─────────────────────────────────────────────
# CLIENT MAPPING (based on referring domain)
# ─────────────────────────────────────────────
def map_client(event):
    props = event.get("properties", {})
    domain = str(props.get("$referring_domain", "")).lower()

    if "raceviewmotors.co.za" in domain:
        return "GFI Motor Corporation"
    elif "northwesternmotors.co.za" in domain:
        return "North Western Ford"
    elif "yonda.co.za" in domain:
        return "Yonda Bike Finance"
    return "Other"


# ─────────────────────────────────────────────
# MIXPANEL EXPORT (STREAMING - SAFE FOR LARGE DATA)
# ─────────────────────────────────────────────
def fetch_events():
    url = "https://data-eu.mixpanel.com/api/2.0/export"

    response = requests.get(
        url,
        auth=(API_SECRET, ""),
        params={
            "from_date": FROM_DATE,
            "to_date": TO_DATE,
        },
        stream=True,
        timeout=300,
    )

    response.raise_for_status()

    for line in response.iter_lines():
        if line:
            yield json.loads(line)


# ─────────────────────────────────────────────
# FLATTEN EVENT
# ─────────────────────────────────────────────
def flatten(event):
    flat = {}

    props = event.get("properties", {})

    flat["event"] = event.get("event", "")
    flat["client"] = map_client(event)

    for k, v in props.items():
        if k == "time":
            try:
                flat["time"] = datetime.utcfromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
            except:
                flat["time"] = v
        else:
            flat[k] = v

    return flat


# ─────────────────────────────────────────────
# SAVE TO CSV (STREAM SAFE)
# ─────────────────────────────────────────────
def save_csv(events):
    first = True
    all_keys = set()
    rows = []

    for event in events:
        flat = flatten(event)
        rows.append(flat)
        all_keys.update(flat.keys())

    priority = ["client", "event", "time", "distinct_id", "$insert_id"]
    fields = [c for c in priority if c in all_keys] + sorted(k for k in all_keys if k not in priority)

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"✓ Export complete: {len(rows)} rows → {OUTPUT_FILE}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Fetching Mixpanel data {FROM_DATE} → {TO_DATE} ...")

    events = list(fetch_events())

    print(f"Fetched {len(events)} events")

    save_csv(events)

    print("Done.")
