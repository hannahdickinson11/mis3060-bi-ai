"""
HW03 - Corporate Events Timeline
MIS3060 Business Intelligence with AI | Hannah Dickinson

Joins executive events (Item 5.02) to the nearest earnings release (Item 2.02)
for the same company and classifies each event's timing.

Inputs:  hw03/earnings_history.csv, hw03/executive_events.csv
Output:  hw03/corporate_events_timeline.csv
"""

from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent
EARNINGS_CSV = HW_DIR / "earnings_history.csv"
EVENTS_CSV = HW_DIR / "executive_events.csv"
OUTPUT_CSV = HW_DIR / "corporate_events_timeline.csv"

SAME_WEEK_DAYS = 7

# Read everything as text so values like CIK "0000320193" and "NOT_FOUND"
# are preserved exactly as written by the earlier scripts.
earnings = pd.read_csv(EARNINGS_CSV, dtype=str, keep_default_na=False)
events = pd.read_csv(EVENTS_CSV, dtype=str, keep_default_na=False)

earnings["filing_date"] = pd.to_datetime(earnings["filing_date"])
events["filing_date"] = pd.to_datetime(events["filing_date"])

# Both tables have a filing_date column, so give each a clear name.
events = events.rename(columns={"filing_date": "event_filing_date"})
earnings = earnings.rename(columns={"filing_date": "earnings_filing_date"})

# Every event paired with every earnings filing of the same company...
pairs = events.merge(earnings, on=["company", "ticker", "cik"], how="left")

# ...then keep only the closest earnings filing for each event.
# signed_days < 0  -> event came BEFORE the earnings filing
# signed_days > 0  -> event came AFTER the earnings filing
pairs["signed_days"] = (pairs["event_filing_date"] - pairs["earnings_filing_date"]).dt.days
pairs["abs_days"] = pairs["signed_days"].abs()

events = events.reset_index().rename(columns={"index": "event_id"})
pairs = pairs.merge(events[["event_id"]], left_index=False, right_index=False, how="left") if False else pairs
pairs["event_id"] = pairs.groupby(["company", "ticker", "cik", "event_filing_date", "event_type",
                                   "person_name", "title", "effective_date"], sort=False).ngroup()

# Sort so that ties (equally distant earnings dates) resolve to the earlier earnings filing.
nearest = (
    pairs.sort_values(["event_id", "abs_days", "earnings_filing_date"])
    .drop_duplicates(subset="event_id", keep="first")
    .copy()
)


def classify(signed_days: int) -> str:
    if abs(signed_days) <= SAME_WEEK_DAYS:
        return "same week"
    return "before earnings" if signed_days < 0 else "after earnings"


nearest["days_to_nearest_earnings"] = nearest["abs_days"].astype(int)
nearest["event_timing"] = nearest["signed_days"].apply(classify)

# Put rows back in the original order of the events file.
nearest = nearest.sort_values("event_id")

output_cols = [
    # identifiers shared by both tables
    "company", "ticker", "cik",
    # executive event columns
    "event_filing_date", "event_type", "person_name", "title", "effective_date",
    # nearest earnings columns
    "earnings_filing_date", "period", "revenue_reported", "eps_diluted", "net_income",
    # new columns
    "days_to_nearest_earnings", "event_timing",
]
timeline = nearest[output_cols].copy()
signed = nearest["signed_days"].to_numpy()  # kept aside for the summary below

for col in ["event_filing_date", "earnings_filing_date"]:
    timeline[col] = timeline[col].dt.strftime("%Y-%m-%d")

timeline.to_csv(OUTPUT_CSV, index=False)
print(f"Saved {len(timeline)} rows to {OUTPUT_CSV.relative_to(HW_DIR.parent)}\n")

# ---------------------------------------------------------------------------
# Summary by company
# ---------------------------------------------------------------------------
timeline["signed_days"] = signed


def describe(row) -> str:
    days = row["days_to_nearest_earnings"]
    direction = "before" if row["signed_days"] < 0 else "after"
    if row["signed_days"] == 0:
        detail = "same day as"
    else:
        detail = f"{days} day{'s' if days != 1 else ''} {direction}"
    label = row["event_timing"].upper()
    return f"{label} ({detail} {row['period']} earnings, filed {row['earnings_filing_date']})"


print("=" * 80)
print("EXECUTIVE EVENTS vs. NEAREST EARNINGS ANNOUNCEMENT")
print("=" * 80)

for ticker, group in timeline.groupby("ticker", sort=False):
    print(f"\n{group['company'].iloc[0]} ({ticker}) - {len(group)} event(s)")
    for _, row in group.iterrows():
        print(f"  {row['event_filing_date']} | {row['event_type']:<11} | "
              f"{row['person_name']:<28} -> {describe(row)}")

# ---------------------------------------------------------------------------
# Final counts
# ---------------------------------------------------------------------------
counts = timeline["event_timing"].value_counts()
same_week = timeline[timeline["event_timing"] == "same week"]
sw_before = int((same_week["signed_days"] < 0).sum())
sw_after = int((same_week["signed_days"] >= 0).sum())

print("\n" + "=" * 80)
print("FINAL COUNT (all five companies)")
print("=" * 80)
print(f"  Before earnings : {counts.get('before earnings', 0)}")
print(f"  After earnings  : {counts.get('after earnings', 0)}")
print(f"  Same week (<= {SAME_WEEK_DAYS} days): {counts.get('same week', 0)} "
      f"({sw_before} just before, {sw_after} on/just after)")
print(f"  Total events    : {len(timeline)}")
