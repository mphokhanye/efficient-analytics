import pandas as pd
import numpy as np

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv("mixpanel_export.csv")
if df.empty:
    print("No data found")
    exit()

# -----------------------------
# MAP REFERRING DOMAIN TO CLIENT
# -----------------------------
client_map = {
    "raceviewmotors.co.za":    "GFI Motor Corporation",
    "northwesternmotors.co.za": "North Western Ford",
    "yonda.co.za":             "Yonda Bike Finance",
}

def map_client(referrer):
    if pd.isna(referrer):
        return None
    for domain, client in client_map.items():
        if domain in str(referrer):
            return client
    return None

df["client"] = df["$initial_referring_domain"].apply(map_client)
df = df[df["client"].notna()]  # drop rows with no matching client

# -----------------------------
# PARSE TIME
# -----------------------------
df["time"] = pd.to_datetime(df["time"], errors="coerce")
df["hour"] = df["time"].dt.hour
df["day_of_week"] = df["time"].dt.day_name()
df["period"] = df["hour"].apply(lambda h: "AM" if h < 12 else "PM")

# -----------------------------
# EVENT FLAGS
# -----------------------------
df["event_prequal"]    = df["event"] == "Submit Pre-qualification (Pre-Qualifications)"
df["event_preapproval"] = df["event"] == "Submit Prediction (Pre-Approval Completed)"

# -----------------------------
# DEVICE CLASSIFICATION
# -----------------------------
def classify_device(row):
    os_val     = str(row.get("$os", "")).lower()
    width      = row.get("$screen_width", 0)
    try:
        width = float(width)
    except (ValueError, TypeError):
        width = 0

    if any(x in os_val for x in ["android", "ios"]):
        return "Mobile"
    if width and width <= 768:
        return "Mobile"
    if width and width <= 1024:
        return "Tablet"
    return "Desktop"

df["device_type"] = df.apply(classify_device, axis=1)

# -----------------------------
# PROVINCE MAPPING (South Africa)
# -----------------------------
province_map = {
    "gauteng":          "Gauteng",
    "western cape":     "Western Cape",
    "kwazulu-natal":    "KwaZulu-Natal",
    "eastern cape":     "Eastern Cape",
    "limpopo":          "Limpopo",
    "mpumalanga":       "Mpumalanga",
    "north west":       "North West",
    "free state":       "Free State",
    "northern cape":    "Northern Cape",
}

def map_province(region):
    if pd.isna(region):
        return "Unknown"
    region_lower = str(region).lower()
    for key, province in province_map.items():
        if key in region_lower:
            return province
    return "Other"

df["province"] = df["$region"].apply(map_province)

# -----------------------------
# CHANNEL CLASSIFICATION
# -----------------------------
def classify_channel(row):
    referrer = str(row.get("$initial_referrer", "")).lower()
    search   = str(row.get("$search_engine", "")).lower()
    gclid    = row.get("gclid", None)
    ttclid   = row.get("ttclid", None)

    if pd.notna(gclid) and str(gclid).strip():
        return "Paid Search (Google)"
    if pd.notna(ttclid) and str(ttclid).strip():
        return "Paid Social (TikTok)"
    if search and search not in ["nan", ""]:
        return "Organic Search"
    if referrer in ["", "nan", "$direct"]:
        return "Direct"
    if any(x in referrer for x in ["facebook", "instagram", "twitter", "linkedin", "social"]):
        return "Organic Social"
    if referrer:
        return "Referral"
    return "Direct"

df["channel"] = df.apply(classify_channel, axis=1)

# -----------------------------
# PROCESS PER CLIENT
# -----------------------------
summary_rows  = []
channel_rows  = []
device_rows   = []
province_rows = []
time_rows     = []
peak_rows     = []

for client, cdf in df.groupby("client"):

    # Unique visits
    unique_visits = cdf["distinct_id"].nunique()

    # Leads (unique visitors who submitted prequal)
    prequal_visitors = cdf[cdf["event_prequal"]]["distinct_id"].nunique()

    # Pre-approvals
    preapproval_visitors = cdf[cdf["event_preapproval"]]["distinct_id"].nunique()

    # Bounce (visited but never submitted prequal)
    bounced = unique_visits - prequal_visitors

    # Conversion rates
    visit_to_lead_rate   = round((prequal_visitors / unique_visits * 100), 2) if unique_visits else 0
    lead_to_approval_rate = round((preapproval_visitors / prequal_visitors * 100), 2) if prequal_visitors else 0
    bounce_rate          = round((bounced / unique_visits * 100), 2) if unique_visits else 0

    summary_rows.append({
        "Client":                    client,
        "Unique Visits":             unique_visits,
        "Pre-Qualifications":        prequal_visitors,
        "Pre-Approvals":             preapproval_visitors,
        "Bounced Visitors":          bounced,
        "Visit to Lead Rate (%)":    visit_to_lead_rate,
        "Lead to Approval Rate (%)": lead_to_approval_rate,
        "Bounce Rate (%)":           bounce_rate,
    })

    # --- Channel breakdown ---
    channel_counts = cdf.drop_duplicates("distinct_id").groupby("channel").size().reset_index(name="Visitors")
    channel_counts["Client"] = client
    channel_counts["% of Total"] = round(channel_counts["Visitors"] / unique_visits * 100, 2)
    channel_rows.append(channel_counts)

    # --- Device breakdown ---
    device_counts = cdf.drop_duplicates("distinct_id").groupby("device_type").size().reset_index(name="Visitors")
    device_counts["Client"] = client
    device_counts["% of Total"] = round(device_counts["Visitors"] / unique_visits * 100, 2)
    device_rows.append(device_counts)

    # --- Province breakdown ---
    province_counts = cdf.drop_duplicates("distinct_id").groupby("province").size().reset_index(name="Visitors")
    province_counts["Client"] = client
    province_counts["% of Total"] = round(province_counts["Visitors"] / unique_visits * 100, 2)
    province_rows.append(province_counts)

    # --- Hourly activity (by day of week + AM/PM) ---
    time_counts = (
        cdf.groupby(["day_of_week", "period", "hour"])
        .size()
        .reset_index(name="Events")
    )
    time_counts["Client"] = client
    time_rows.append(time_counts)

    # --- Peak hours (top 5) ---
    peak = (
        cdf.groupby(["day_of_week", "hour"])
        .size()
        .reset_index(name="Events")
        .sort_values("Events", ascending=False)
        .head(5)
    )
    peak["Client"] = client
    peak_rows.append(peak)

# -----------------------------
# SAVE OUTPUTS
# -----------------------------
summary_df  = pd.DataFrame(summary_rows)
channel_df  = pd.concat(channel_rows,  ignore_index=True)[["Client", "channel",      "Visitors", "% of Total"]]
device_df   = pd.concat(device_rows,   ignore_index=True)[["Client", "device_type",  "Visitors", "% of Total"]]
province_df = pd.concat(province_rows, ignore_index=True)[["Client", "province",     "Visitors", "% of Total"]]
time_df     = pd.concat(time_rows,     ignore_index=True)[["Client", "day_of_week",  "period",   "hour", "Events"]]
peak_df     = pd.concat(peak_rows,     ignore_index=True)[["Client", "day_of_week",  "hour",     "Events"]]

# Day ordering
day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
time_df["day_of_week"] = pd.Categorical(time_df["day_of_week"], categories=day_order, ordered=True)
time_df = time_df.sort_values(["Client", "day_of_week", "hour"])

summary_df.to_csv("client_summary.csv",   index=False)
channel_df.to_csv("channel_summary.csv",  index=False)
device_df.to_csv("device_summary.csv",    index=False)
province_df.to_csv("province_summary.csv", index=False)
time_df.to_csv("time_summary.csv",        index=False)
peak_df.to_csv("peak_hours.csv",          index=False)

print("✓ client_summary.csv")
print("✓ channel_summary.csv")
print("✓ device_summary.csv")
print("✓ province_summary.csv")
print("✓ time_summary.csv")
print("✓ peak_hours.csv")
print(f"\nDone! Processed {len(df):,} rows across {df['client'].nunique()} clients.")
