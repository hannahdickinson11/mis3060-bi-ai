"""
00_make_extract.py  -  MIS3060 HW7, Part A item 5

Builds data/growth_extract.csv from the same cleaned CSVs the HW6
reconciliation script reads (hw06/02_Data/Cleaned), NOT from Power BI.

Grain: one row per year x client tier x region (5 x 3 x 5 = 75 rows).

Region follows the Power BI model: each fact table joins to dim_advisor
through its OWN advisor_id (the active relationships). dim_client[advisor_id]
-> dim_advisor is inactive in the model, so it is not used here.
Tier comes from dim_client[client_tier] via client_id.

Columns
  year, client_tier, region
  ending_aum     BALANCE  sum of aum on the December snapshot of that year
                          (same as [Ending AUM]: last snapshot date in the year)
  ending_aum_ly  BALANCE  ending_aum of the same tier/region one year earlier
                          (same as [Ending AUM LY]); blank for the first year
  net_flows      FLOW     Deposits - Withdrawals over the calendar year
                          (same as [Net Flows])
  market_change  FLOW     ending_aum - ending_aum_ly - net_flows
                          (same as [Market Change]); blank for the first year
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent           # hw07/
SRC_DIR = HW_DIR.parent / "hw06" / "02_Data" / "Cleaned"  # same files as HW6
OUT_DIR = HW_DIR / "data"
OUT_PATH = OUT_DIR / "growth_extract.csv"


def main() -> None:
    snap = pd.read_csv(SRC_DIR / "fact_portfolio_snapshot.csv",
                       usecols=["client_id", "advisor_id", "snapshot_date", "aum"],
                       parse_dates=["snapshot_date"])
    txn = pd.read_csv(SRC_DIR / "fact_transactions.csv",
                      usecols=["client_id", "advisor_id", "txn_date", "txn_type", "amount"],
                      parse_dates=["txn_date"])
    client = pd.read_csv(SRC_DIR / "dim_client.csv", usecols=["client_id", "client_tier"])
    advisor = pd.read_csv(SRC_DIR / "dim_advisor.csv", usecols=["advisor_id", "region"])

    def add_dims(df: pd.DataFrame) -> pd.DataFrame:
        out = (df.merge(client, on="client_id", how="left", validate="many_to_one")
                 .merge(advisor, on="advisor_id", how="left", validate="many_to_one"))
        missing = out[["client_tier", "region"]].isna().any(axis=1).sum()
        if missing:
            raise ValueError(f"{missing} fact rows have no tier or region (orphan keys)")
        return out

    keys = ["year", "client_tier", "region"]

    # --- Ending AUM: last snapshot date in each year (December), summed ----
    snap = add_dims(snap)
    snap["year"] = snap["snapshot_date"].dt.year
    last_date = snap.groupby("year")["snapshot_date"].transform("max")
    dec = snap[snap["snapshot_date"] == last_date]
    if not (dec["snapshot_date"].dt.month == 12).all():
        raise ValueError("A year's last snapshot is not in December")
    ending = dec.groupby(keys, as_index=False)["aum"].sum().rename(columns={"aum": "ending_aum"})

    # --- Net Flows: Deposits - Withdrawals, summed over the calendar year ---
    txn = add_dims(txn[txn["txn_type"].isin(["Deposit", "Withdrawal"])].copy())
    txn["year"] = txn["txn_date"].dt.year
    txn["signed"] = txn["amount"].where(txn["txn_type"] == "Deposit", -txn["amount"])
    flows = txn.groupby(keys, as_index=False)["signed"].sum().rename(columns={"signed": "net_flows"})

    # --- Full 75-row grid so every combination appears, even if empty -----
    years = sorted(snap["year"].unique())
    grid = pd.MultiIndex.from_product(
        [years, sorted(client["client_tier"].unique()), sorted(advisor["region"].unique())],
        names=keys,
    ).to_frame(index=False)

    out = (grid.merge(ending, on=keys, how="left")
               .merge(flows, on=keys, how="left"))
    out["net_flows"] = out["net_flows"].fillna(0.0)

    # --- Ending AUM LY: same tier/region, previous year (blank for year 1) --
    prev = out[keys + ["ending_aum"]].copy()
    prev["year"] = prev["year"] + 1
    out = out.merge(prev.rename(columns={"ending_aum": "ending_aum_ly"}), on=keys, how="left")

    out["market_change"] = out["ending_aum"] - out["ending_aum_ly"] - out["net_flows"]

    out = out[keys + ["ending_aum", "ending_aum_ly", "net_flows", "market_change"]]
    out = out.sort_values(keys).reset_index(drop=True)
    for col in ["ending_aum", "ending_aum_ly", "net_flows", "market_change"]:
        out[col] = out[col].round(2)

    if len(out) != 75:
        raise ValueError(f"Expected 75 rows, got {len(out)}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT_PATH, index=False)
    print(f"Wrote {len(out)} rows -> {OUT_PATH.relative_to(HW_DIR)}")

    # Firm-level summary per year (balances summed across tier/region within a
    # single year only, never across years)
    firm = out.groupby("year")[["ending_aum", "ending_aum_ly", "net_flows", "market_change"]].sum(min_count=1)
    print(firm.to_string(float_format=lambda v: f"{v:,.0f}"))


if __name__ == "__main__":
    main()
