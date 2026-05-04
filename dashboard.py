import pandas as pd

# -----------------------------
# LOAD DATA (THIS MUST BE FIRST)
# -----------------------------
df = pd.read_csv("mixpanel_export.csv")

if df.empty:
    print("No data found")
    exit()

# ensure required columns exist
for col in ["client", "visit_id", "event_prequal", "event_preapproval"]:
    if col not in df.columns:
        df[col] = None

df["event_prequal"] = df["event_prequal"].fillna(False).astype(bool)
df["event_preapproval"] = df["event_preapproval"].fillna(False).astype(bool)

# -----------------------------
# NOW YOUR EXISTING CODE STARTS
# -----------------------------

summary_rows = []
channel_rows = []
device_rows = []
province_rows = []
time_rows = []
peak_rows = []

for client, cdf in df.groupby('client'):
