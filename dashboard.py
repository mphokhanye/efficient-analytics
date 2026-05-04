import pandas as pd

# -----------------------------
# LOAD DATA (THIS WAS MISSING)
# -----------------------------
df = pd.read_csv("mixpanel_export.csv")

# safety check
if df.empty:
    print("No data found in mixpanel_export.csv")
    exit()

# ensure required columns exist safely
for col in ["client", "visit_id", "event_prequal", "event_preapproval"]:
    if col not in df.columns:
        df[col] = None

# convert booleans safely
df["event_prequal"] = df["event_prequal"].fillna(False).astype(bool)
df["event_preapproval"] = df["event_preapproval"].fillna(False).astype(bool)

# time features (only if timestamp exists)
if "timestamp" in df.columns:
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["day"] = df["timestamp"].dt.day_name()
    df["hour"] = df["timestamp"].dt.hour
    df["period"] = df["hour"].apply(lambda x: "AM" if x < 12 else "PM")
else:
    df["day"] = "Unknown"
    df["hour"] = 0
    df["period"] = "AM"


# -----------------------------
# STRUCTURED OUTPUT TABLES
# -----------------------------
summary_rows = []
channel_rows = []
device_rows = []
province_rows = []
time_rows = []
peak_rows = []

for client, cdf in df.groupby('client'):

    visits = cdf['visit_id'].nunique()

    prequals = cdf[cdf['event_prequal']]['visit_id'].nunique()
    preapprovals = cdf[cdf['event_preapproval']]['visit_id'].nunique()

    visits_to_leads = prequals / visits if visits else 0

    bounced_users = cdf.groupby('visit_id')['event_prequal'].max() == False
    bounce_rate = bounced_users.sum() / visits if visits else 0

    summary_rows.append({
        "client": client,
        "visits": visits,
        "bounce_rate": round(bounce_rate, 4),
        "visits_to_leads": round(visits_to_leads, 4),
        "prequals": prequals,
        "preapprovals": preapprovals
    })

    if "channel" in cdf.columns:
        channel_dist = cdf.groupby('channel')['visit_id'].nunique() / visits * 100
        for k, v in channel_dist.items():
            channel_rows.append({"client": client, "channel": k, "%": round(v,1)})

    if "device" in cdf.columns:
        device_dist = cdf.groupby('device')['visit_id'].nunique() / visits * 100
        for k, v in device_dist.items():
            device_rows.append({"client": client, "device": k, "%": round(v,1)})

    if "province" in cdf.columns:
        province_dist = cdf.groupby('province')['visit_id'].nunique() / visits * 100
        for k, v in province_dist.items():
            province_rows.append({"client": client, "province": k, "%": round(v,1)})

    time_group = cdf.groupby(['day','hour'])['visit_id'].nunique().reset_index()
    for _, row in time_group.iterrows():
        time_rows.append({
            "client": client,
            "day": row['day'],
            "hour": row['hour'],
            "visits": row['visit_id']
        })

    peak = cdf.groupby(['day','period','hour']).size().reset_index(name='count')
    if not peak.empty:
        peak = peak.loc[peak.groupby(['day','period'])['count'].idxmax()]

        for _, row in peak.iterrows():
            peak_rows.append({
                "client": client,
                "day": row['day'],
                "period": row['period'],
                "hour": row['hour']
            })


# -----------------------------
# SAVE FILES
# -----------------------------
pd.DataFrame(summary_rows).to_csv("client_summary.csv", index=False)
pd.DataFrame(channel_rows).to_csv("channel_distribution.csv", index=False)
pd.DataFrame(device_rows).to_csv("device_distribution.csv", index=False)
pd.DataFrame(province_rows).to_csv("province_distribution.csv", index=False)
pd.DataFrame(time_rows).to_csv("time_activity.csv", index=False)
pd.DataFrame(peak_rows).to_csv("peak_hours.csv", index=False)

print("Structured datasets ready for dashboard upload.")
