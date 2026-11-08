"""
01_reconcile_measures.py  -  MIS3060 HW6

Recomputes the Power BI DAX measures INDEPENDENTLY in pandas from the cleaned
CSVs, then compares them with the values exported from Power BI.

Inputs  (relative to hw06/):
    02_Data/Cleaned/fact_portfolio_snapshot.csv
    02_Data/Cleaned/fact_fees.csv
    02_Data/Cleaned/fact_transactions.csv
    02_Data/Cleaned/dim_client.csv
    02_Data/Cleaned/dim_date.csv          (checked for presence only; date
                                           shifts are done with date math)
    reports/powerbi_values.csv            (measure, slice, value)
Output:
    reports/measure_reconciliation.csv    (measure, slice, powerbi_value,
                                           pandas_value, abs_diff, match)

The three measure patterns used below:
  * SUM          - additive values (fees, flows), so you can just sum them over
                   the slice.  "AUM (naive SUM)" applies this pattern to a
                   balance on purpose, to show why that's wrong.
  * LAST BALANCE - semi-additive values (AUM, client count): take the
                   latest snapshot date in the slice and sum only that day.
                   Time-intelligence variants (LY, PM) do the same thing
                   over a slice shifted back in time (like DATEADD).
  * RECOMPUTE-AND-WEIGHT - ratios are recomputed from their own numerator and
                   denominator over the slice (never averaged).  Alpha is
                   weighted by AUM, so big accounts count more.

Blank handling mirrors DAX: an aggregate over zero rows is BLANK (NaN here,
not 0), and DIVIDE() returns BLANK when the denominator is blank or zero.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path

import pandas as pd

# --------------------------------------------------------------------------
# Paths: built from this script's own location (hw06/scripts/ -> hw06/)
# --------------------------------------------------------------------------
HW_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = HW_DIR / "02_Data" / "Cleaned"
REPORTS_DIR = HW_DIR / "reports"
PBI_VALUES_PATH = REPORTS_DIR / "powerbi_values.csv"
OUTPUT_PATH = REPORTS_DIR / "measure_reconciliation.csv"

# Full model date range (dim_date covers 2020-01-01 .. 2024-12-31)
MODEL_START = pd.Timestamp("2020-01-01")
MODEL_END = pd.Timestamp("2024-12-31")

# --------------------------------------------------------------------------
# Comparison settings
# --------------------------------------------------------------------------
CURRENCY_MEASURES = {
    "AUM (naive SUM)",
    "Ending AUM",
    "Ending AUM LY",
    "Ending AUM PM",
    "Avg AUM per Client",
    "Avg Monthly AUM",
}
TEXT_MEASURES = {"Alpha Signal"}
CURRENCY_TOL = 0.01
OTHER_TOL = 0.0001

# Measure x slice combinations the assignment expects (used only to warn about
# rows missing from powerbi_values.csv; output rows come from that file).
YEAR_SLICES = [f"year={y}" for y in range(2020, 2025)]
TIER_SLICES = [f"tier={t}|year=2024" for t in ("HNW", "Retail", "UHNW")]
EXPECTED = {
    "Total": None,  # None = every measure
    **{s: ["AUM (naive SUM)", "Ending AUM", "Ending AUM LY", "AUM YoY %",
           "Avg Monthly AUM", "Fee Yield (bps)", "Organic Growth Rate",
           "AUM-Weighted Alpha", "Alpha Signal"] for s in YEAR_SLICES},
    **{s: ["Ending AUM", "Avg AUM per Client", "Ending AUM LY", "AUM YoY %",
           "Fee Yield (bps)", "Organic Growth Rate", "AUM-Weighted Alpha",
           "Alpha Signal", "Top 10 Client Share"] for s in TIER_SLICES},
    "month=2024-12": ["Ending AUM", "Ending AUM PM", "AUM MoM %"],
}


# ==========================================================================
# Data loading
# ==========================================================================
def load_data() -> dict[str, pd.DataFrame]:
    """Read the cleaned CSVs and attach client_tier to every fact table."""
    for name in ("fact_portfolio_snapshot", "fact_fees", "fact_transactions",
                 "dim_client", "dim_date"):
        path = DATA_DIR / f"{name}.csv"
        if not path.exists():
            raise FileNotFoundError(f"Missing input file: {path}")

    # client_id read as text everywhere so the joins can't fail on dtype
    cid = {"client_id": str}
    snap = pd.read_csv(DATA_DIR / "fact_portfolio_snapshot.csv", dtype=cid)
    fees = pd.read_csv(DATA_DIR / "fact_fees.csv", dtype=cid)
    txns = pd.read_csv(DATA_DIR / "fact_transactions.csv", dtype=cid)
    clients = pd.read_csv(DATA_DIR / "dim_client.csv", dtype=cid)

    snap["snapshot_date"] = pd.to_datetime(snap["snapshot_date"])
    fees["fee_date"] = pd.to_datetime(fees["fee_date"])
    txns["txn_date"] = pd.to_datetime(txns["txn_date"])

    for df in (snap, fees, txns):
        df["client_id"] = df["client_id"].str.strip()
    clients["client_id"] = clients["client_id"].str.strip()
    clients["client_tier"] = clients["client_tier"].str.strip()

    # Tier filter = relationship dim_client[client_id] -> fact[client_id]
    tiers = clients[["client_id", "client_tier"]].drop_duplicates("client_id")
    snap = snap.merge(tiers, on="client_id", how="left")
    fees = fees.merge(tiers, on="client_id", how="left")
    txns = txns.merge(tiers, on="client_id", how="left")

    # NOTE: no filter on is_post_departure_txn - Power BI doesn't apply one.
    return {"snap": snap, "fees": fees, "txns": txns}


# ==========================================================================
# Slices (the filter context)
# ==========================================================================
@dataclass(frozen=True)
class Slice:
    label: str
    start: pd.Timestamp
    end: pd.Timestamp
    tier: str | None = None

    def shifted(self, years: int = 0, months: int = 0) -> "Slice":
        """Same tier filter, dates moved back like DATEADD(..., -n, YEAR/MONTH).
        DateOffset clamps month-ends (2024-12-31 - 1 month = 2024-11-30)."""
        off = pd.DateOffset(years=-years, months=-months)
        return replace(self, start=self.start + off, end=self.end + off)


def parse_slice(label: str) -> Slice:
    """Turn a label like 'tier=HNW|year=2024' into a date range + tier."""
    start, end, tier = MODEL_START, MODEL_END, None
    if label != "Total":
        for part in label.split("|"):
            key, val = part.split("=", 1)
            if key == "year":
                start = pd.Timestamp(f"{val}-01-01")
                end = pd.Timestamp(f"{val}-12-31")
            elif key == "month":
                start = pd.Timestamp(f"{val}-01")
                end = start + pd.offsets.MonthEnd(0)
            elif key == "tier":
                tier = val
            else:
                raise ValueError(f"Unknown slice key '{key}' in '{label}'")
    return Slice(label, start, end, tier)


def filter_rows(df: pd.DataFrame, date_col: str, s: Slice) -> pd.DataFrame:
    """Rows of a fact table that fall inside the slice."""
    mask = (df[date_col] >= s.start) & (df[date_col] <= s.end)
    if s.tier is not None:
        mask &= df["client_tier"] == s.tier
    return df[mask]


# ==========================================================================
# Small DAX-like helpers
# ==========================================================================
NaN = float("nan")


def is_blank(x) -> bool:
    return x is None or (isinstance(x, float) and math.isnan(x)) or x == ""


def blank_sum(series: pd.Series) -> float:
    """SUM() over zero rows is BLANK in DAX, not 0."""
    return NaN if series.empty else float(series.sum())


def divide(num, den) -> float:
    """DAX DIVIDE(): blank when the denominator is blank or 0."""
    if is_blank(den) or den == 0 or is_blank(num):
        return NaN
    return num / den


def blank_as_zero(x) -> float:
    """DAX arithmetic treats BLANK as 0 (e.g. Ending AUM - Ending AUM LY)."""
    return 0.0 if is_blank(x) else x


# ==========================================================================
# Measures
# ==========================================================================
class Measures:
    def __init__(self, data: dict[str, pd.DataFrame]):
        self.snap = data["snap"]
        self.fees = data["fees"]
        self.txns = data["txns"]

    # ---- helpers ---------------------------------------------------------
    def _snap(self, s: Slice) -> pd.DataFrame:
        return filter_rows(self.snap, "snapshot_date", s)

    def _last_date_rows(self, s: Slice) -> pd.DataFrame:
        """LAST BALANCE pattern: snapshot rows on the latest snapshot_date
        that exists in the slice (LASTNONBLANK over snapshot dates)."""
        rows = self._snap(s)
        if rows.empty:
            return rows
        return rows[rows["snapshot_date"] == rows["snapshot_date"].max()]

    # ---- SUM pattern (deliberately wrong for a balance) ------------------
    def aum_naive_sum(self, s: Slice) -> float:
        # Adds month-end balances across months, so it counts the same money
        # over and over. Kept here to match Power BI's broken measure.
        return blank_sum(self._snap(s)["aum"])

    # ---- LAST BALANCE pattern --------------------------------------------
    def ending_aum(self, s: Slice) -> float:
        return blank_sum(self._last_date_rows(s)["aum"])

    def ending_clients(self, s: Slice) -> float:
        rows = self._last_date_rows(s)
        return NaN if rows.empty else float(rows["client_id"].nunique())

    def avg_aum_per_client(self, s: Slice) -> float:
        # RECOMPUTE: ending balance / ending headcount, both on the same date
        return divide(self.ending_aum(s), self.ending_clients(s))

    def ending_aum_ly(self, s: Slice) -> float:
        # LAST BALANCE over the slice shifted back one year
        return self.ending_aum(s.shifted(years=1))

    def ending_aum_pm(self, s: Slice) -> float:
        # LAST BALANCE over the slice shifted back one month
        return self.ending_aum(s.shifted(months=1))

    def aum_yoy(self, s: Slice) -> float:
        ly = self.ending_aum_ly(s)
        return divide(blank_as_zero(self.ending_aum(s)) - blank_as_zero(ly), ly)

    def aum_mom(self, s: Slice) -> float:
        pm = self.ending_aum_pm(s)
        return divide(blank_as_zero(self.ending_aum(s)) - blank_as_zero(pm), pm)

    def avg_monthly_aum(self, s: Slice) -> float:
        # Proper average balance: total of the monthly balances / number of months
        rows = self._snap(s)
        return divide(blank_sum(rows["aum"]), rows["snapshot_date"].nunique())

    # ---- SUM pattern (flows are additive) --------------------------------
    def total_fees(self, s: Slice) -> float:
        return blank_sum(filter_rows(self.fees, "fee_date", s)["amount"])

    def net_flows(self, s: Slice) -> float:
        rows = filter_rows(self.txns, "txn_date", s)
        dep = rows.loc[rows["txn_type"] == "Deposit", "amount"]
        wdr = rows.loc[rows["txn_type"] == "Withdrawal", "amount"]
        if dep.empty and wdr.empty:
            return NaN
        return blank_as_zero(blank_sum(dep)) - blank_as_zero(blank_sum(wdr))

    # ---- RECOMPUTE-AND-WEIGHT pattern ------------------------------------
    def fee_yield_bps(self, s: Slice) -> float:
        # Monthly fees / summed monthly balances = average monthly rate;
        # x12 annualizes it, x10000 converts it to basis points.
        fees = self.total_fees(s)
        aum = blank_sum(self._snap(s)["aum"])
        return divide(fees * 12 * 10000 if not is_blank(fees) else NaN, aum)

    def organic_growth_rate(self, s: Slice) -> float:
        # Net new money over the slice / starting point (last year's ending AUM)
        return divide(self.net_flows(s), self.ending_aum_ly(s))

    def aum_weighted_alpha(self, s: Slice) -> float:
        # Latest date in the slice, then drop suspect returns, then
        # sum(aum * alpha) / sum(aum): weight by AUM, don't average the clients
        rows = self._last_date_rows(s)
        rows = rows[rows["is_return_suspect"] != 1]
        if rows.empty:
            return NaN
        return divide(float((rows["aum"] * rows["active_alpha_ytd"]).sum()),
                      float(rows["aum"].sum()))

    def alpha_signal(self, s: Slice) -> str:
        a = self.aum_weighted_alpha(s)
        if is_blank(a):
            return ""
        if a >= 0.02:
            return "Outperforming"
        if a <= -0.02:
            return "Lagging"
        return "In line"

    def top10_client_share(self, s: Slice) -> float:
        # Latest date; rank by aum desc, ties -> lower client_id first
        rows = self._last_date_rows(s)
        if rows.empty:
            return NaN
        top = rows.sort_values(["aum", "client_id"], ascending=[False, True]).head(10)
        return divide(float(top["aum"].sum()), float(rows["aum"].sum()))


# Measure name (exactly as in Power BI) -> method name
MEASURE_FUNCS = {
    "AUM (naive SUM)": "aum_naive_sum",
    "Ending AUM": "ending_aum",
    "Ending Clients": "ending_clients",
    "Avg AUM per Client": "avg_aum_per_client",
    "Ending AUM LY": "ending_aum_ly",
    "AUM YoY %": "aum_yoy",
    "Ending AUM PM": "ending_aum_pm",
    "AUM MoM %": "aum_mom",
    "Avg Monthly AUM": "avg_monthly_aum",
    "Total Fees": "total_fees",
    "Fee Yield (bps)": "fee_yield_bps",
    "Net Flows": "net_flows",
    "Organic Growth Rate": "organic_growth_rate",
    "AUM-Weighted Alpha": "aum_weighted_alpha",
    "Alpha Signal": "alpha_signal",
    "Top 10 Client Share": "top10_client_share",
}


# ==========================================================================
# Power BI values + comparison
# ==========================================================================
def load_powerbi_values() -> pd.DataFrame:
    """Read everything as text so blanks stay blank and Alpha Signal stays text."""
    pbi = pd.read_csv(PBI_VALUES_PATH, dtype=str, keep_default_na=False)
    for col in ("measure", "slice", "value"):
        pbi[col] = pbi[col].str.strip()
    return pbi


def to_number(text: str) -> float:
    """Parse an exported value; '' / 'nan' / '(Blank)' -> NaN.
    Handles stray '$', ',' and a trailing '%' (converted to a decimal)."""
    t = str(text).strip()
    if t.lower() in ("", "nan", "none", "null", "(blank)", "blank"):
        return NaN
    pct = t.endswith("%")
    t = t.replace("$", "").replace(",", "").rstrip("%").strip()
    val = float(t)
    return val / 100 if pct else val


def compare(measure: str, pbi_raw: str, pandas_val):
    """Return (powerbi_value, abs_diff, match)."""
    if measure in TEXT_MEASURES:
        p, q = str(pbi_raw).strip(), "" if is_blank(pandas_val) else str(pandas_val)
        return p, NaN, p == q

    p = to_number(pbi_raw)
    if is_blank(p) and is_blank(pandas_val):
        return p, NaN, True
    if is_blank(p) or is_blank(pandas_val):
        return p, NaN, False
    tol = CURRENCY_TOL if measure in CURRENCY_MEASURES else OTHER_TOL
    diff = abs(p - pandas_val)
    return p, diff, diff <= tol


def warn_missing_expected(pbi: pd.DataFrame) -> None:
    have = set(zip(pbi["measure"], pbi["slice"]))
    missing = []
    for slc, measures in EXPECTED.items():
        for m in (measures or MEASURE_FUNCS):
            if (m, slc) not in have:
                missing.append(f"{m} @ {slc}")
    if missing:
        print(f"Note: {len(missing)} expected measure/slice rows are not in "
              f"powerbi_values.csv (no comparison made):")
        for m in missing:
            print(f"  - {m}")
        print()


def main() -> None:
    data = load_data()
    calc = Measures(data)
    pbi = load_powerbi_values()
    warn_missing_expected(pbi)

    records = []
    for _, row in pbi.iterrows():
        measure, label, raw = row["measure"], row["slice"], row["value"]
        func = MEASURE_FUNCS.get(measure)
        if func is None:
            print(f"WARNING: unknown measure '{measure}' - not recomputed")
            pandas_val = NaN
        else:
            pandas_val = getattr(calc, func)(parse_slice(label))
        pbi_val, diff, ok = compare(measure, raw, pandas_val)
        if func is None:
            ok = False
        records.append({
            "measure": measure,
            "slice": label,
            "powerbi_value": pbi_val,
            "pandas_value": pandas_val,
            "abs_diff": diff,
            "match": bool(ok),
        })

    out = pd.DataFrame(records, columns=["measure", "slice", "powerbi_value",
                                         "pandas_value", "abs_diff", "match"])
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_PATH, index=False)

    n, n_match = len(out), int(out["match"].sum())
    print(f"Rows compared : {n}")
    print(f"Matches       : {n_match}")
    print(f"Mismatches    : {n - n_match}")
    bad = out[~out["match"]]
    if not bad.empty:
        print("\nRows that do NOT match:")
        with pd.option_context("display.width", 200, "display.max_columns", None,
                               "display.float_format", "{:,.6f}".format):
            print(bad.to_string(index=False))
    print(f"\nWrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
