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

    # SUMMARY
    summary_rows.append({
        "client": client,
        "visits": visits,
        "bounce_rate": round(bounce_rate, 4),
        "visits_to_leads": round(visits_to_leads, 4),
        "prequals": prequals,
        "preapprovals": preapprovals
    })

    # CHANNEL
    channel_dist = cdf.groupby('channel')['visit_id'].nunique() / visits * 100
    for k, v in channel_dist.items():
        channel_rows.append({"client": client, "channel": k, "%": round(v,1)})

    # DEVICE
    device_dist = cdf.groupby('device')['visit_id'].nunique() / visits * 100
    for k, v in device_dist.items():
        device_rows.append({"client": client, "device": k, "%": round(v,1)})

    # PROVINCE
    province_dist = cdf.groupby('province')['visit_id'].nunique() / visits * 100
    for k, v in province_dist.items():
        province_rows.append({"client": client, "province": k, "%": round(v,1)})

    # TIME
    time_group = cdf.groupby(['day','hour'])['visit_id'].nunique().reset_index()
    for _, row in time_group.iterrows():
        time_rows.append({
            "client": client,
            "day": row['day'],
            "hour": row['hour'],
            "visits": row['visit_id']
        })

    # PEAK HOURS
    peak = cdf.groupby(['day','period','hour']).size().reset_index(name='count')
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
