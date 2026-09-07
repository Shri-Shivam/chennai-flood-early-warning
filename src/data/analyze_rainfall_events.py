import pandas as pd

# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

file_path = "data/raw/chennai_weather_2016_2025.csv"

df = pd.read_csv(file_path, parse_dates=["time"])

df = df.sort_values("time").reset_index(drop=True)

# ---------------------------------------------------------
# FUTURE 6-HOUR RAINFALL
# ---------------------------------------------------------

df["future_6h_rain"] = sum(
    df["precipitation"].shift(-i)
    for i in range(1, 7)
)

# ---------------------------------------------------------
# DEFINE CANDIDATE EVENT
# ---------------------------------------------------------
# We are investigating 20 mm / 6h first.

threshold = 20

df["heavy_event"] = df["future_6h_rain"] >= threshold

# ---------------------------------------------------------
# FIND START OF EACH EVENT
# ---------------------------------------------------------
#
# Consecutive positive windows belong to the same rainfall
# episode.
#
# Example:
#
# 0 0 1 1 1 0 0 1 1 0
#
# becomes:
#
#       Event 1       Event 2
#
# ---------------------------------------------------------

df["event_start"] = (
    df["heavy_event"]
    & ~df["heavy_event"].shift(1, fill_value=False)
)

df["event_id"] = df["event_start"].cumsum()

events = df[df["heavy_event"]].copy()

# Keep only actual events
events = events[events["event_id"] > 0]

# ---------------------------------------------------------
# SUMMARIZE EVENTS
# ---------------------------------------------------------

event_summary = (
    events
    .groupby("event_id")
    .agg(
        start_time=("time", "min"),
        end_time=("time", "max"),
        peak_6h_rain=("future_6h_rain", "max"),
        positive_windows=("heavy_event", "size")
    )
    .reset_index()
)

# ---------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------

print("=" * 70)
print("RAINFALL EVENT ANALYSIS")
print("=" * 70)

print(f"\nThreshold: >= {threshold} mm in future 6 hours")

print(f"\nTotal positive windows: {len(events)}")

print(f"Distinct rainfall events: {len(event_summary)}")

print("\nEvent summary:")
print("-" * 70)

print(
    event_summary[
        [
            "start_time",
            "end_time",
            "peak_6h_rain",
            "positive_windows"
        ]
    ].to_string(index=False)
)

# ---------------------------------------------------------
# STRONGEST EVENTS
# ---------------------------------------------------------

print("\n" + "=" * 70)
print("TOP 20 RAINFALL EVENTS")
print("=" * 70)

top_events = event_summary.sort_values(
    "peak_6h_rain",
    ascending=False
).head(20)

print(
    top_events[
        [
            "start_time",
            "end_time",
            "peak_6h_rain",
            "positive_windows"
        ]
    ].to_string(index=False)
)

print("\n" + "=" * 70)
print("ANALYSIS COMPLETE")
print("=" * 70)