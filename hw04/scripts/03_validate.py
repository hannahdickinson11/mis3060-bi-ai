"""
HW4 Part D — Referential integrity and validation
MIS3060 Business Intelligence with AI

Runs the SAME checks on the raw tables and on the clean tables, so every number has a
before/after:

  1. check_referential_integrity()  — one reusable function (kept for Assignment 5),
                                      applied to all 13 relationships (10 ID-based + 3 date)
  2. Rule-based checks               — every column with a natural business bound
                                      (ranges, allowed code lists, sign rules, consistency)
  3. Reconciliations                 — recomputed values vs stored values; at least two
                                      are cross-table (R1, R6, R7)
  4. IQR outlier flags               — numeric columns with no natural bound
  5. Scorecard                       — one row per table per stage (definitions are written
                                      to reports/data_quality_scorecard_notes.md)

Independence: the checks here do NOT reuse the cleaning script's fix lists. Trading days are
checked against the holiday calendar built from pandas rules in 01_profile.py (Part C used a
hand-typed NYSE list), and transaction types are defined here, not imported.

Outputs (reports/):
  data_quality_scorecard.csv   data_quality_scorecard_notes.md   referential_integrity.csv
  validation_rules.csv         reconciliations.csv               iqr_outliers.csv

Run from the hw04 folder:
    python scripts/03_validate.py
"""
from __future__ import annotations   # type hints work on Python 3.7–3.9

import argparse
import importlib.util
import sys
from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RAW = HW_DIR / "02_Data" / "Raw"
DEFAULT_CLEAN = HW_DIR / "data" / "clean"
DEFAULT_OUT = HW_DIR / "reports"


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# Schema definitions (which tables, keys and relationships exist) are shared with the cleaning
# script so the two can't disagree about structure. The CHECK inputs below are independent.
_clean = _load_module("clean_script", "02_clean.py")
_profile = _load_module("profile_script", "01_profile.py")
TABLES, PK, RELATIONSHIPS = _clean.TABLES, _clean.PK, _clean.RELATIONSHIPS
USPS = set(_clean.US_STATES.values())
market_holidays = _profile.market_holidays          # pandas-rule calendar, independent of Part C's list

# Defined here on purpose (not imported) so a shared mistake can't pass both scripts
CASH_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}
SECURITY_TYPES = {"Buy", "Sell", "Dividend"}        # rows that must carry a security, shares and price
PLACEHOLDER_AUM = 1000.0                            # D17
RETURN_LOW, RETURN_HIGH = -0.9, 1.0                 # D18 plausibility band for YTD returns
RISK_PROFILES = {"Conservative", "Moderately Conservative", "Balanced", "Moderately Aggressive", "Aggressive"}
ACCOUNT_TYPES = {"Taxable", "IRA", "Roth IRA", "Trust", "529"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_blank(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin({"", "nan", "null", "n/a", "na", "<na>"})


def to_num(s: pd.Series) -> pd.Series:
    """Strict numeric parse. Range rules only use typed columns, whose type validity is scored
    separately, so a value this rejects is never silently 'passed'."""
    ok = s.astype(str).str.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", na=False)
    return pd.to_numeric(s.where(ok), errors="coerce")


def to_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")


def is_true(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin({"true", "1", "yes"})


def client_lookup(c: pd.DataFrame) -> pd.DataFrame:
    """dim_client indexed by client_id. IDs that appear more than once are DROPPED (not
    first-wins), so a conflicting duplicate shows up as an unmatched row instead of vanishing."""
    return c[~c.client_id.duplicated(keep=False)].set_index("client_id")


def load(folder: Path, raw: bool) -> dict:
    out = {}
    for name, pattern in TABLES.items():
        matches = sorted(folder.glob(pattern if raw else f"{name}.csv"))
        if len(matches) != 1:
            sys.exit(f"Expected one file for {name} in {folder}, found {[m.name for m in matches]}")
        out[name] = pd.read_csv(matches[0], dtype=str, keep_default_na=False)   # TEXT ONLY
    return out


# ---------------------------------------------------------------------------
# 1. Referential integrity — ONE reusable function (keep for Assignment 5)
# ---------------------------------------------------------------------------
def check_referential_integrity(fact_df: pd.DataFrame, fact_key: str,
                                dim_df: pd.DataFrame, dim_key: str,
                                normalize_numeric: bool = False) -> dict:
    """Check that every value of fact_df[fact_key] exists in dim_df[dim_key].

    Keys are compared as stripped text, which is how a BI tool joins them: '45.0' does NOT
    match '45'. Works on any dtype (values are converted to text first). If the frames were
    loaded WITHOUT dtype=str, pandas may have turned an ID column with blanks into floats
    ('45.0') — pass normalize_numeric=True to compare '45.0' and '45' as the same key.

    Blank keys are counted separately and excluded from match_rate; the caller decides whether
    blanks are allowed for this relationship (null_key_rate shows how many there are).

    Returns a dict:
        rows, null_key_rows, null_key_rate (0–1),
        matched_rows, match_rate (matched / non-blank, 0–1; 1.0 if no non-blank keys),
        orphan_row_count, orphan_rows (DataFrame), distinct_orphan_keys, orphan_key_examples,
        dim_key_unique (the dimension side must be unique for a valid one-to-many join)
    """
    def norm(s):
        s = s.astype(str).str.strip()
        return s.str.replace(r"^(-?\d+)\.0+$", r"\1", regex=True) if normalize_numeric else s

    key, dim = norm(fact_df[fact_key]), norm(dim_df[dim_key])
    blank = is_blank(key)
    found = key.isin(set(dim[~is_blank(dim)]))
    orphan = ~blank & ~found
    nonblank = int((~blank).sum())
    return {
        "rows": len(fact_df),
        "null_key_rows": int(blank.sum()),
        "null_key_rate": float(blank.mean()) if len(fact_df) else 0.0,
        "matched_rows": int((~blank & found).sum()),
        "match_rate": float((~blank & found).sum() / nonblank) if nonblank else 1.0,
        "orphan_row_count": int(orphan.sum()),
        "orphan_rows": fact_df[orphan],
        "distinct_orphan_keys": int(key[orphan].nunique()),
        "orphan_key_examples": " | ".join(key[orphan].drop_duplicates().head(5)),
        "dim_key_unique": bool(dim.is_unique),
    }


def run_ri(t: dict, stage: str):
    """Returns the per-relationship table and, per fact table, a mask of rows whose FK fails
    (orphan, or blank where blanks are not allowed)."""
    rows, row_fail = [], {}
    for ft, fk, dt, pk, blanks_ok in RELATIONSHIPS:
        r = check_referential_integrity(t[ft], fk, t[dt], pk)
        blank = is_blank(t[ft][fk])
        fail = t[ft].index.isin(r["orphan_rows"].index) | (blank.values & (not blanks_ok))
        row_fail[ft] = row_fail.get(ft, pd.Series(False, index=t[ft].index)) | fail
        rows.append({"stage": stage, "fact_table": ft, "fact_key": fk, "dim_table": dt, "dim_key": pk,
                     "rows": r["rows"], "matched_rows": r["matched_rows"],
                     "match_rate_pct": round(100 * r["match_rate"], 4),
                     "orphan_rows": r["orphan_row_count"], "distinct_orphan_keys": r["distinct_orphan_keys"],
                     "null_key_rows": r["null_key_rows"], "null_key_rate_pct": round(100 * r["null_key_rate"], 4),
                     "blank_keys_allowed": blanks_ok,
                     "unexpected_blank_keys": 0 if blanks_ok else r["null_key_rows"],
                     "dim_key_unique": r["dim_key_unique"], "orphan_key_examples": r["orphan_key_examples"]})
    return pd.DataFrame(rows), row_fail


# ---------------------------------------------------------------------------
# 2. Rule-based checks
#    Each rule: (table, column, rule text, kind, fn(t) -> (applies, passes), flag column or None)
#    flag column = the Part C flag that is SUPPOSED to mark the rows this rule fails on, for
#    issues that were flagged rather than fixed. In clean data, every failure must be flagged.
# ---------------------------------------------------------------------------
def between(lo, hi):
    def f(s):
        v = to_num(s)
        return v.notna(), v.between(lo, hi)
    return f


def positive(s):
    v = to_num(s)
    return v.notna(), v > 0


def allowed(values):
    return lambda s: (~is_blank(s), s.isin(values))


def pattern(rx):
    return lambda s: (~is_blank(s), s.str.fullmatch(rx, na=False))


def col(table, column, fn):
    return lambda t: fn(t[table][column])


def tier_matches_aum(t):
    c = t["dim_client"]
    aum = to_num(c.initial_aum)
    tier = pd.cut(aum, [0, 500_000, 5_000_000, float("inf")], labels=["Retail", "HNW", "UHNW"], right=False)
    return aum.notna(), tier.astype(str) == c.client_tier


def client_since_not_future(t):
    c = t["dim_client"]
    since, last = to_date(c.client_since), to_date(t["dim_date"].date).max()
    return since.notna(), since <= last


def etf_has_expense_ratio(t):
    s = t["dim_security"]
    return pd.Series(True, index=s.index), is_true(s.is_etf) == ~is_blank(s.expense_ratio_bps)


def stock_has_sector(t):
    s = t["dim_security"]
    return pd.Series(True, index=s.index), ~is_true(s.is_etf) == ~is_blank(s.sector)


def date_fields_match(t):
    """Every derived calendar column agrees with the date itself."""
    d = t["dim_date"]
    dt = to_date(d.date)
    i = lambda x: x.astype("Int64").astype(str)
    ok = ((i(dt.dt.year) == d.year) & (i(dt.dt.month) == d.month) & (i(dt.dt.quarter) == d.quarter)
          & (dt.dt.month_name() == d.month_name) & (dt.dt.day_name() == d.day_of_week)
          & (i(dt.dt.isocalendar().week) == d.week_of_year)
          & (i(dt.dt.is_month_end) == d.is_month_end) & (i(dt.dt.is_quarter_end) == d.is_quarter_end)
          & (i(dt.dt.is_year_end) == d.is_year_end))
    return dt.notna(), ok


def trading_day_rule(t):
    """is_trading_day must be 1 exactly on weekdays that are not market holidays. The holiday
    calendar comes from pandas rules (01_profile.py), NOT from the list Part C used to fix it."""
    d = t["dim_date"]
    dt = to_date(d.date)
    hol = set(market_holidays(dt.min(), dt.max()).strftime("%Y-%m-%d"))
    expected = ((dt.dt.day_of_week < 5) & ~d.date.isin(hol)).astype(int).astype(str)
    return dt.notna(), d.is_trading_day == expected


def snapshot_year_month(t):
    p = t["fact_portfolio_snapshot"]
    sd = to_date(p.snapshot_date)
    i = lambda x: x.astype("Int64").astype(str)
    return sd.notna(), (i(sd.dt.year) == p.year) & (i(sd.dt.month) == p.month) & (sd.dt.day == 1)


def not_placeholder(table, column):
    def f(t):
        v = to_num(t[table][column])
        return v.notna(), v != PLACEHOLDER_AUM
    return f


def shares_positive(t):
    x = t["fact_transactions"]
    applies = x.txn_type.isin(SECURITY_TYPES)
    return applies, to_num(x.shares) > 0


def price_positive(t):
    x = t["fact_transactions"]
    applies = x.txn_type.isin(SECURITY_TYPES)
    return applies, to_num(x.price) > 0


def security_iff_traded(t):
    x = t["fact_transactions"]
    known = x.txn_type.isin(SECURITY_TYPES | CASH_TYPES)          # unknown types fail the code-list rule
    return known, x.txn_type.isin(SECURITY_TYPES) == ~is_blank(x.security_id)


def activity_after_joining(table, date_col):
    def f(t):
        df, c = t[table], client_lookup(t["dim_client"])
        since, d = to_date(df.client_id.map(c.client_since)), to_date(df[date_col])
        return since.notna() & d.notna(), d.dt.to_period("M") >= since.dt.to_period("M")
    return f


def trade_on_trading_day(t):
    x = t["fact_transactions"]
    dt = to_date(x.txn_date)
    hol = set(market_holidays(dt.min(), dt.max()).strftime("%Y-%m-%d"))
    applies = x.txn_type.isin({"Buy", "Sell"}) & dt.notna()
    return applies, (dt.dt.day_of_week < 5) & ~x.txn_date.isin(hol)


RULES = [
    # dim_advisor
    ("dim_advisor", "years_experience", "0–50 years", "range", col("dim_advisor", "years_experience", between(0, 50)), None),
    ("dim_advisor", "aum_target_mm", "> 0", "sign", col("dim_advisor", "aum_target_mm", positive), None),
    ("dim_advisor", "region", "allowed list", "code list", col("dim_advisor", "region", allowed(
        {"Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West", "Southwest"})), None),
    ("dim_advisor", "certifications", "allowed list", "code list", col("dim_advisor", "certifications", allowed(
        {"CFA", "CFP", "CIMA", "CFP, CFA", "CFP, CIMA", "CFA, CIMA", "None"})), None),
    # dim_benchmark
    ("dim_benchmark", "asset_class", "allowed list", "code list", col("dim_benchmark", "asset_class", allowed(
        {"Equity", "Fixed Income", "Multi-Asset", "International", "Small Cap", "Emerging", "Cash"})), None),
    ("dim_benchmark", "ticker_proxy", "uppercase code", "code list", col("dim_benchmark", "ticker_proxy", pattern(r"[A-Z0-9_]+")), None),
    # dim_client
    ("dim_client", "age", "18–110", "range", col("dim_client", "age", between(18, 110)), None),
    ("dim_client", "state", "USPS code", "code list", col("dim_client", "state", allowed(USPS)), None),
    ("dim_client", "zip_code", "5 digits", "code list", col("dim_client", "zip_code", pattern(r"\d{5}")), None),
    ("dim_client", "risk_profile", "allowed list (blanks scored under completeness)", "code list",
     col("dim_client", "risk_profile", allowed(RISK_PROFILES)), None),
    ("dim_client", "client_tier", "allowed list", "code list", col("dim_client", "client_tier", allowed({"Retail", "HNW", "UHNW"})), None),
    ("dim_client", "primary_account_type", "allowed list", "code list", col("dim_client", "primary_account_type", allowed(ACCOUNT_TYPES)), None),
    ("dim_client", "initial_aum", "> 0", "sign", col("dim_client", "initial_aum", positive), None),
    ("dim_client", "client_tier", "tier matches initial AUM band", "consistency", tier_matches_aum, None),
    ("dim_client", "client_since", "not after the end of the calendar", "range", client_since_not_future, None),
    ("dim_client", "is_active", "True/False", "code list", col("dim_client", "is_active", allowed({"True", "False"})), None),
    # dim_date
    ("dim_date", "quarter", "1–4", "range", col("dim_date", "quarter", between(1, 4)), None),
    ("dim_date", "month", "1–12", "range", col("dim_date", "month", between(1, 12)), None),
    ("dim_date", "week_of_year", "1–53", "range", col("dim_date", "week_of_year", between(1, 53)), None),
    ("dim_date", "all derived fields", "year, quarter, month, names, week, period-end flags match the date",
     "consistency", date_fields_match, None),
    ("dim_date", "is_trading_day", "1 only on non-holiday weekdays (pandas-rule calendar)", "consistency",
     trading_day_rule, None),
    # dim_security
    ("dim_security", "asset_class", "allowed list", "code list", col("dim_security", "asset_class",
     allowed({"Equity", "Fixed Income", "Alternative", "Cash Equivalent"})), None),
    ("dim_security", "sector", "allowed list (blank = ETF)", "code list", col("dim_security", "sector", allowed(
        {"Technology", "Healthcare", "Financials", "Energy", "Utilities", "Materials", "Industrials",
         "Consumer Staples", "Consumer Discretionary", "Communication Services", "Real Estate"})), None),
    ("dim_security", "is_etf", "True/False", "code list", col("dim_security", "is_etf", allowed({"True", "False"})), None),
    ("dim_security", "expense_ratio_bps", "0–300 bps", "range", col("dim_security", "expense_ratio_bps", between(0, 300)), None),
    ("dim_security", "is_etf/expense_ratio_bps", "ETF <-> has expense ratio", "consistency", etf_has_expense_ratio, None),
    ("dim_security", "is_etf/sector", "stock <-> has sector", "consistency", stock_has_sector, None),
    # fact_fees
    ("fact_fees", "fee_type", "allowed list", "code list", col("fact_fees", "fee_type",
     allowed({"Management", "Advisory", "Custodial", "Performance"})), None),
    ("fact_fees", "aum_basis", "> 0", "sign", col("fact_fees", "aum_basis", positive), None),
    ("fact_fees", "aum_basis", f"not the {PLACEHOLDER_AUM:,.0f} placeholder (D17)", "plausibility",
     not_placeholder("fact_fees", "aum_basis"), "flag_aum_placeholder"),
    ("fact_fees", "bps_charged", "0–300 bps", "range", col("fact_fees", "bps_charged", between(0, 300)), None),
    ("fact_fees", "amount", "> 0", "sign", col("fact_fees", "amount", positive), None),
    ("fact_fees", "fee_date", "on or after client's joining month", "consistency", activity_after_joining("fact_fees", "fee_date"), None),
    # fact_portfolio_snapshot
    ("fact_portfolio_snapshot", "aum", "> 0", "sign", col("fact_portfolio_snapshot", "aum", positive), None),
    ("fact_portfolio_snapshot", "aum", f"not the {PLACEHOLDER_AUM:,.0f} placeholder (D17)", "plausibility",
     not_placeholder("fact_portfolio_snapshot", "aum"), "flag_aum_placeholder"),
    ("fact_portfolio_snapshot", "cash_pct", "0–1", "range", col("fact_portfolio_snapshot", "cash_pct", between(0, 1)), None),
    ("fact_portfolio_snapshot", "return_ytd", f"between {RETURN_LOW:.0%} and +{RETURN_HIGH:.0%} YTD (D18)", "plausibility",
     col("fact_portfolio_snapshot", "return_ytd", between(RETURN_LOW, RETURN_HIGH)), "flag_return_implausible"),
    ("fact_portfolio_snapshot", "benchmark_return_ytd", "between -100% and +100% (index returns)", "range",
     col("fact_portfolio_snapshot", "benchmark_return_ytd", between(-1, 1)), None),
    ("fact_portfolio_snapshot", "account_type", "allowed list", "code list", col("fact_portfolio_snapshot", "account_type", allowed(ACCOUNT_TYPES)), None),
    ("fact_portfolio_snapshot", "year/month", "match snapshot_date (1st of month)", "consistency", snapshot_year_month, None),
    ("fact_portfolio_snapshot", "snapshot_date", "on or after client's joining month", "consistency",
     activity_after_joining("fact_portfolio_snapshot", "snapshot_date"), None),
    # fact_transactions
    ("fact_transactions", "txn_type", "allowed list", "code list", col("fact_transactions", "txn_type",
     allowed(SECURITY_TYPES | CASH_TYPES)), None),
    ("fact_transactions", "shares", "> 0 on Buy/Sell/Dividend (direction comes from txn_type)", "sign", shares_positive, None),
    ("fact_transactions", "price", "> 0 on Buy/Sell/Dividend", "sign", price_positive, None),
    ("fact_transactions", "amount", "> 0", "sign", col("fact_transactions", "amount", positive), None),
    ("fact_transactions", "security_id", "present exactly on Buy/Sell/Dividend", "consistency", security_iff_traded, None),
    ("fact_transactions", "txn_date", "on or after client's joining month", "consistency",
     activity_after_joining("fact_transactions", "txn_date"), None),
    ("fact_transactions", "txn_date", "Buy/Sell on a trading day (D14)", "plausibility", trade_on_trading_day,
     "flag_non_trading_day"),
]

def run_rules(t: dict, stage: str):
    """Returns the per-rule table and, per table, a mask of rows that fail at least one rule."""
    rows, row_fail = [], {}
    for table, column, rule, kind, fn, flag in RULES:
        df = t[table]
        applies, passes = fn(t)
        applies = applies.fillna(False).astype(bool)
        failed = applies & ~passes.fillna(False).astype(bool)
        row_fail[table] = row_fail.get(table, pd.Series(False, index=df.index)) | failed
        unflagged = ""
        if flag:
            unflagged = int((failed & (df[flag] != "1")).sum()) if flag in df else int(failed.sum())
        n, bad = int(applies.sum()), int(failed.sum())
        rows.append({"stage": stage, "table": table, "column": column, "rule": rule, "kind": kind,
                     "rows_checked": n, "rows_failed": bad, "pass_pct": round(100 * (n - bad) / n, 4) if n else 100.0,
                     "flag_column": flag or "", "failures_not_flagged": unflagged,
                     "fail_examples": " | ".join(df.loc[failed, PK[table]].head(5))})
    return pd.DataFrame(rows), row_fail


# ---------------------------------------------------------------------------
# 3. Reconciliations — recomputed vs stored (scope says which are cross-table)
# ---------------------------------------------------------------------------
def run_reconciliations(t: dict, stage: str) -> pd.DataFrame:
    out = []

    def add(name, scope, tables, compared, rows, ok, note):
        out.append({"stage": stage, "reconciliation": name, "scope": scope, "tables": tables, "compared": compared,
                    "rows_compared": int(rows), "rows_matched": int(ok),
                    "match_pct": round(100 * ok / rows, 4) if rows else 100.0, "rows_not_matched": int(rows - ok),
                    "note": note})

    f, p, x = t["fact_fees"], t["fact_portfolio_snapshot"], t["fact_transactions"]
    cli = client_lookup(t["dim_client"])

    # R1 — every fee row must have exactly one snapshot for the same client-month with the same AUM.
    # Denominator = ALL fee rows; a missing or duplicated snapshot counts as a failure.
    keys = ["client_id", "snapshot_date"]
    dup_snap = p.duplicated(keys, keep=False)
    snap = p[~dup_snap].set_index(keys).aum
    fee_key = pd.MultiIndex.from_arrays([f.client_id, f.fee_date])
    snap_aum = pd.Series(snap.reindex(fee_key).values, index=f.index)
    has_snap = snap_aum.notna()
    ok = has_snap & ((to_num(f.aum_basis) - to_num(snap_aum)).abs() <= 0.01)
    add("R1 fee AUM basis = snapshot AUM", "cross-table", "fact_fees x fact_portfolio_snapshot",
        "every fee row vs the single snapshot for that client-month (tol $0.01)", len(f), ok.sum(),
        f"{(~has_snap).sum():,} fees with no unique snapshot; {dup_snap.sum():,} snapshot rows share a client-month. "
        f"Both tables carry the D17 placeholder, so this check confirms consistency, not correctness")

    # R2 — fee amount recomputed from AUM basis x annual bps / 12
    calc = to_num(f.aum_basis) * to_num(f.bps_charged) / 10_000 / 12
    ok = (calc - to_num(f.amount)).abs() <= 0.05
    add("R2 fee amount = aum_basis x bps / 10,000 / 12", "within-table", "fact_fees",
        "recomputed vs stored amount (tol $0.05)", len(f), ok.sum(), "annual rate billed monthly")

    # R3 — trade amount recomputed from shares x price (rows that must carry a security)
    traded = x.txn_type.isin(SECURITY_TYPES)
    calc = to_num(x.shares) * to_num(x.price)
    ok = traded & ((calc - to_num(x.amount)).abs() <= 1.0)
    add("R3 trade amount = shares x price", "within-table", "fact_transactions",
        "recomputed vs stored amount (tol $1)", traded.sum(), ok.sum(), "a negative share count fails this check")

    # R4 — return identity
    r, b, a = to_num(p.return_ytd), to_num(p.benchmark_return_ytd), to_num(p.active_alpha_ytd)
    ok = (r - b - a).abs() <= 1e-4
    add("R4 return = benchmark + alpha", "within-table", "fact_portfolio_snapshot",
        "return_ytd vs benchmark + alpha (tol 0.0001)", len(p), ok.sum(),
        "percent-text returns ('9.28%') fail in raw because they don't parse")

    # R5 — one benchmark return per benchmark per month (compared as numbers, not text)
    g = p.assign(_b=b).groupby(["benchmark_id", "snapshot_date"])._b.agg(lambda v: v.round(6).nunique(dropna=False))
    add("R5 one benchmark return per benchmark-month", "within-table", "fact_portfolio_snapshot",
        "distinct benchmark_return_ytd per benchmark-month", len(g), (g == 1).sum(), f"{len(g)} benchmark-months")

    # R6/R7 — facts agree with the client dimension
    for ft in ["fact_fees", "fact_portfolio_snapshot", "fact_transactions"]:
        df = t[ft]
        dim_adv = df.client_id.map(cli.advisor_id)
        known = dim_adv.notna()
        add(f"R6 {ft}.advisor_id = dim_client.advisor_id", "cross-table", f"{ft} x dim_client",
            "advisor on fact vs client's advisor", known.sum(), (known & (dim_adv == df.advisor_id)).sum(),
            f"{(~known).sum():,} rows whose client is not (uniquely) in dim_client are excluded — see RI")
    dim_acct = p.client_id.map(cli.primary_account_type)
    known = dim_acct.notna()
    add("R7 snapshot account_type = dim_client.primary_account_type", "cross-table",
        "fact_portfolio_snapshot x dim_client", "account type", known.sum(), (known & (dim_acct == p.account_type)).sum(), "")
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# 4. IQR outliers — numeric columns with NO natural upper bound
# ---------------------------------------------------------------------------
IQR_COLUMNS = [
    ("fact_portfolio_snapshot", "aum"),
    ("fact_transactions", "amount"),
    ("fact_fees", "amount"),
    ("dim_client", "initial_aum"),
]


def run_iqr(t: dict, stage: str) -> pd.DataFrame:
    rows = []
    cli = client_lookup(t["dim_client"])
    for table, column in IQR_COLUMNS:
        df = t[table]
        v = to_num(df[column]).dropna()
        q1, q3 = v.quantile(0.25), v.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        high = v.index[v > hi]
        tier = df.client_tier if table == "dim_client" else df.client_id.map(cli.client_tier)
        row = {"stage": stage, "table": table, "column": column, "rows": len(v), "q1": round(q1, 2),
               "q3": round(q3, 2), "iqr": round(iqr, 2), "lower_fence": round(lo, 2), "upper_fence": round(hi, 2),
               "low_outliers": int((v < lo).sum()), "high_outliers": len(high),
               "outlier_pct": round(100 * ((v < lo).sum() + len(high)) / len(v), 2) if len(v) else 0.0,
               "pct_high_uhnw": round(100 * (tier.loc[high] == "UHNW").mean(), 1) if len(high) else None,
               "pct_high_hnw_or_uhnw": round(100 * tier.loc[high].isin(["UHNW", "HNW"]).mean(), 1) if len(high) else None,
               "pct_high_reconciled": None, "placeholder_rows": None, "placeholder_flagged_by_iqr": None,
               "max": round(v.max(), 2)}
        if table == "fact_transactions" and len(high):
            sub = df.loc[high]
            rec = sub.txn_type.isin(SECURITY_TYPES) & \
                ((to_num(sub.shares) * to_num(sub.price) - to_num(sub.amount)).abs() <= 1.0)
            cash = sub.txn_type.isin(CASH_TYPES)
            row["pct_high_reconciled"] = round(100 * (rec | cash).mean(), 1)   # cash rows have no shares x price
        if (table, column) == ("fact_portfolio_snapshot", "aum"):
            ph = v == PLACEHOLDER_AUM
            row["placeholder_rows"] = int(ph.sum())
            row["placeholder_flagged_by_iqr"] = int((ph & ((v < lo) | (v > hi))).sum())
        rows.append(row)
    return pd.DataFrame(rows)


def iqr_sentence(iqr: pd.DataFrame, rules: pd.DataFrame) -> str:
    """The required one-sentence answer to "does flagged mean wrong?" — every clause is computed."""
    c = iqr[iqr.stage == "raw"].set_index(["table", "column"])
    get = lambda tc: c.loc[tc] if tc in c.index else None
    aum, fee, trade = get(("fact_portfolio_snapshot", "aum")), get(("fact_fees", "amount")), get(("fact_transactions", "amount"))
    parts = []
    if aum is not None and aum.high_outliers:
        parts.append(f"{aum.pct_high_uhnw}% of the {int(aum.high_outliers):,} high AUM outliers belong to UHNW clients")
    if fee is not None and fee.high_outliers:
        parts.append(f"{fee.pct_high_uhnw}% of the {int(fee.high_outliers):,} high fee outliers do too")
    if trade is not None and trade.high_outliers:
        parts.append(f"{trade.pct_high_reconciled}% of the {int(trade.high_outliers):,} large-transaction outliers "
                     f"reconcile to shares x price or are cash movements")
    ph_rule = rules[(rules.stage == "raw") & (rules.table == "fact_portfolio_snapshot") & (rules.column == "aum")
                    & (rules.kind == "plausibility")]
    caught = int(ph_rule.rows_failed.sum()) if len(ph_rule) else 0
    if aum is not None and aum.placeholder_rows:
        parts.append(f"while the {int(aum.placeholder_rows)} rows with the {PLACEHOLDER_AUM:,.0f} placeholder AUM — a real "
                     f"error — sit inside the fences ({int(aum.placeholder_flagged_by_iqr)} flagged, because the lower "
                     f"fence is {aum.lower_fence:,.0f}) and are caught by the placeholder rule ({caught} rows)")
    explained = [x for x in [aum, fee] if x is not None and x.high_outliers]
    mostly_legit = all(x.pct_high_uhnw >= 90 for x in explained) and \
        (trade is None or not trade.high_outliers or trade.pct_high_reconciled >= 90)
    lead = "Flagged does not mean wrong: " if mostly_legit else "Flagged is not proof of an error, but check these: "
    return lead + "; ".join(parts) + "."


# ---------------------------------------------------------------------------
# 5. Scorecard — one row per table per stage
# ---------------------------------------------------------------------------
TYPES = {"int": r"-?\d+", "float": r"-?\d+(\.\d+)?([eE][-+]?\d+)?", "bool": r"True|False", "flag01": r"[01]",
         "zip": r"\d{5}"}
COLUMN_TYPES = {
    "dim_advisor": {"advisor_id": "int", "years_experience": "int", "aum_target_mm": "int"},
    "dim_benchmark": {"benchmark_id": "int"},
    "dim_client": {"client_id": "int", "age": "int", "zip_code": "zip", "initial_aum": "float", "client_since": "date",
                   "advisor_id": "int", "is_active": "bool"},
    "dim_date": {"date_id": "int", "date": "date", "year": "int", "quarter": "int", "month": "int", "week_of_year": "int",
                 "is_month_end": "flag01", "is_quarter_end": "flag01", "is_year_end": "flag01", "is_trading_day": "flag01"},
    "dim_security": {"security_id": "int", "benchmark_id": "int", "is_etf": "bool", "expense_ratio_bps": "float"},
    "fact_fees": {"fee_id": "int", "client_id": "int", "advisor_id": "int", "fee_date": "date", "aum_basis": "float",
                  "bps_charged": "float", "amount": "float"},
    "fact_portfolio_snapshot": {"snapshot_id": "int", "client_id": "int", "advisor_id": "int", "benchmark_id": "int",
                                "snapshot_date": "date", "year": "int", "month": "int", "aum": "float",
                                "return_ytd": "float", "benchmark_return_ytd": "float", "active_alpha_ytd": "float",
                                "cash_pct": "float"},
    "fact_transactions": {"txn_id": "int", "client_id": "int", "advisor_id": "int", "security_id": "int",
                          "txn_date": "date", "shares": "float", "price": "float", "amount": "float"},
}
BUSINESS_KEYS = {
    "dim_client": ["first_name", "age", "city", "zip_code", "initial_aum"],
    "dim_security": ["ticker"],
    "dim_date": ["date"],
    "fact_fees": ["client_id", "fee_date"],
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],
}


def type_ok(s: pd.Series, typ: str) -> pd.Series:
    if typ == "date":                      # a real calendar date, not just the right shape
        return s.str.fullmatch(r"\d{4}-\d{2}-\d{2}", na=False) & to_date(s).notna()
    return s.str.fullmatch(TYPES[typ], na=False)


def expected_blank(table: str, df: pd.DataFrame) -> pd.DataFrame:
    """Cells blank by design (D07, D11) — excluded from completeness."""
    m = pd.DataFrame(False, index=df.index, columns=df.columns)
    if table == "fact_transactions":
        for c in ("security_id", "shares", "price"):
            m[c] = df.txn_type.isin(CASH_TYPES)
    if table == "dim_security":
        m["sector"] = is_true(df.is_etf)
        m["expense_ratio_bps"] = ~is_true(df.is_etf)
    return m


def scorecard(t: dict, stage: str, rule_fail: dict, ri_fail: dict, raw_cols: dict) -> pd.DataFrame:
    rows = []
    for name in TABLES:
        missing = set(raw_cols[name]) - set(t[name].columns)
        if missing:
            sys.exit(f"{stage} {name} is missing columns {sorted(missing)} — cannot score it")
        df = t[name][raw_cols[name]]                       # original columns only (flags excluded)
        exp = expected_blank(name, df)
        blank = df.apply(is_blank)
        cells = int((~exp).values.sum())
        incomplete = int((blank & ~exp).values.sum())

        dup = df[PK[name]].duplicated(keep=False)          # keep=False: every row in a duplicate group counts
        if name in BUSINESS_KEYS:
            dup |= df[BUSINESS_KEYS[name]].apply(lambda s: s.str.strip().str.lower()).duplicated(keep=False)

        typed, invalid = 0, 0
        for c, typ in COLUMN_TYPES[name].items():
            s = df[c][~is_blank(df[c])]
            typed += len(s)
            invalid += int((~type_ok(s, typ)).sum())

        n = len(df)
        rf = rule_fail.get(name, pd.Series(False, index=df.index))
        fk = ri_fail.get(name)
        rows.append({
            "table": name, "stage": stage, "rows": n,
            "pct_completeness": round(100 * (cells - incomplete) / cells, 2) if cells else 100.0,
            "pct_key_uniqueness": round(100 * (n - dup.sum()) / n, 2) if n else 100.0,
            "pct_type_validity": round(100 * (typed - invalid) / typed, 2) if typed else 100.0,
            "pct_rule_pass": round(100 * (n - rf.sum()) / n, 2) if n else 100.0,
            "pct_referential_match": round(100 * (n - fk.sum()) / n, 2) if fk is not None and n else None,
            # exact counts behind each percentage (the checks below use these, never the rounded %)
            "incomplete_cells": incomplete, "duplicate_key_rows": int(dup.sum()), "invalid_typed_cells": invalid,
            "rows_failing_a_rule": int(rf.sum()),
            "rows_with_unmatched_fk": int(fk.sum()) if fk is not None else None,
        })
    return pd.DataFrame(rows)


SCORECARD_NOTES = """# Data quality scorecard — how each metric is calculated

`data_quality_scorecard.csv` has one row per table per stage (raw / clean). Every percentage has
an exact count column next to it; checks use the counts, never the rounded percentage.

| Metric | Definition | Count column |
|---|---|---|
| `pct_completeness` | Non-blank cells ÷ all cells in the original columns, **excluding cells blank by design**: `security_id`/`shares`/`price` on cash transactions (D11), `sector` on ETFs and `expense_ratio_bps` on stocks (D07). Flag columns are not scored. | `incomplete_cells` |
| `pct_key_uniqueness` | Rows that are **not part of a duplicate group** on the primary key or the business key (client: first name + age + city + zip + initial AUM; security: ticker; date: date; fees/snapshots: client + month). Both rows of a duplicate pair count as not unique, so 25 duplicate clients = 50 rows. | `duplicate_key_rows` |
| `pct_type_validity` | Non-blank typed cells that parse as their type (integers, decimals, True/False, 0/1, 5-digit zip, and **real** dates — 2024-13-45 fails). | `invalid_typed_cells` |
| `pct_rule_pass` | Rows that pass **every** rule that applies to them (not an average over rules), so one bad column shows at full weight. Includes plausibility rules for issues that were flagged rather than fixed (D14, D17, D18), so clean tables with flagged rows score below 100% — by design. | `rows_failing_a_rule` |
| `pct_referential_match` | Rows whose foreign keys **all** resolve. A blank key counts as a failure unless blanks are allowed for that relationship (only `fact_transactions.security_id`, on cash rows). Blank for tables with no foreign keys. Per-relationship detail is in `referential_integrity.csv`. | `rows_with_unmatched_fk` |

One issue can lower two metrics when it really is two problems: the `45.0` security IDs (D10) are
both the wrong type (integer stored as decimal text) and unjoinable (0% match), so raw
`fact_transactions` loses points on type validity **and** referential match.

Clean-stage checks (the script stops with a message if any fails): 0 orphan or unexpected-blank
foreign keys, dimension keys unique, 0 duplicate-key rows, 0 invalid typed cells, every
reconciliation 100%, and every remaining rule failure is on a row carrying the matching Part C flag.
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def clean_stage_problems(ri, rules, rec, score) -> list:
    """Exact-count checks on the clean tables. Returned as a list so ALL problems are reported."""
    c_ri, c_rules = ri[ri.stage == "clean"], rules[rules.stage == "clean"]
    c_rec, c_score = rec[rec.stage == "clean"], score[score.stage == "clean"]
    problems = []
    for _, r in c_ri[c_ri.orphan_rows > 0].iterrows():
        problems.append(f"{r.fact_table}.{r.fact_key}: {r.orphan_rows} orphan rows")
    for _, r in c_ri[c_ri.unexpected_blank_keys > 0].iterrows():
        problems.append(f"{r.fact_table}.{r.fact_key}: {r.unexpected_blank_keys} unexpected blank keys")
    for _, r in c_ri[~c_ri.dim_key_unique].iterrows():
        problems.append(f"{r.dim_table}.{r.dim_key} is not unique")
    for _, r in c_score[(c_score.duplicate_key_rows > 0) | (c_score.invalid_typed_cells > 0)].iterrows():
        problems.append(f"{r.table}: {r.duplicate_key_rows} duplicate-key rows, {r.invalid_typed_cells} invalid cells")
    for _, r in c_rec[c_rec.rows_not_matched > 0].iterrows():
        problems.append(f"{r.reconciliation}: {r.rows_not_matched} rows do not reconcile")
    hard = c_rules[(c_rules.flag_column == "") & (c_rules.rows_failed > 0)]
    for _, r in hard.iterrows():
        problems.append(f"rule {r.table}.{r.column} '{r.rule}': {r.rows_failed} rows fail")
    soft = c_rules[(c_rules.flag_column != "")]
    for _, r in soft[soft.failures_not_flagged.astype(int) > 0].iterrows():
        problems.append(f"rule {r.table}.{r.column} '{r.rule}': {r.failures_not_flagged} failures are not flagged")
    return problems


def main():
    ap = argparse.ArgumentParser(description="Validate raw and clean Wildcat Capital tables")
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--clean-dir", type=Path, default=DEFAULT_CLEAN)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    # Range/sign rules skip values that don't parse, so they may only run on typed columns —
    # there, an unparseable value is counted as invalid in the scorecard instead of being skipped
    for table, column, _, kind, _, _ in RULES:
        if kind in ("range", "sign") and column not in COLUMN_TYPES[table]:
            sys.exit(f"{kind} rule on untyped column {table}.{column} — add it to COLUMN_TYPES")

    stages = {"raw": load(args.raw_dir, raw=True), "clean": load(args.clean_dir, raw=False)}
    raw_cols = {n: list(df.columns) for n, df in stages["raw"].items()}
    dmin = to_date(stages["raw"]["dim_date"].date).min()
    dmax = to_date(stages["raw"]["dim_date"].date).max()
    cal_years = set(market_holidays(dmin, dmax).year)
    if set(range(dmin.year, dmax.year + 1)) - cal_years:
        sys.exit(f"holiday calendar does not cover years {sorted(set(range(dmin.year, dmax.year + 1)) - cal_years)}")

    ri, rules, rec, iqr, score = [], [], [], [], []
    for stage, t in stages.items():
        print(f"Validating {stage} tables ...")
        ri_df, ri_fail = run_ri(t, stage)
        rule_df, rule_fail = run_rules(t, stage)
        ri.append(ri_df)
        rules.append(rule_df)
        rec.append(run_reconciliations(t, stage))
        iqr.append(run_iqr(t, stage))
        score.append(scorecard(t, stage, rule_fail, ri_fail, raw_cols))
    ri, rules, rec, iqr = (pd.concat(x, ignore_index=True) for x in (ri, rules, rec, iqr))
    score = pd.concat(score, ignore_index=True).sort_values(["table", "stage"], ascending=[True, False])
    sentence = iqr_sentence(iqr, rules)

    # ---- Save FIRST, so a failing check still leaves the reports to inspect ----
    args.out_dir.mkdir(parents=True, exist_ok=True)
    score.to_csv(args.out_dir / "data_quality_scorecard.csv", index=False)
    (args.out_dir / "data_quality_scorecard_notes.md").write_text(SCORECARD_NOTES, encoding="utf-8")
    ri.to_csv(args.out_dir / "referential_integrity.csv", index=False)
    rules.to_csv(args.out_dir / "validation_rules.csv", index=False)
    rec.to_csv(args.out_dir / "reconciliations.csv", index=False)
    iqr.assign(does_flagged_mean_wrong=sentence).to_csv(args.out_dir / "iqr_outliers.csv", index=False)

    # ---- Print ----
    pd.set_option("display.width", 220)
    pd.set_option("display.max_colwidth", 70)
    print("\n=== Referential integrity (match % of non-blank keys — raw vs clean) ===")
    piv = ri.pivot_table(index=["fact_table", "fact_key", "dim_table"], columns="stage",
                         values=["match_rate_pct", "orphan_rows"], aggfunc="first")
    print(piv[[("match_rate_pct", "raw"), ("match_rate_pct", "clean"), ("orphan_rows", "raw"),
               ("orphan_rows", "clean")]].to_string())

    print("\n=== Rules that fail in either stage (rows failed) ===")
    rp = rules.pivot_table(index=["table", "column", "rule"], columns="stage", values="rows_failed", aggfunc="first")
    print(rp[(rp > 0).any(axis=1)][["raw", "clean"]].to_string())
    print(f"  ({len(RULES)} rules; the rest pass 100% in both stages. Clean failures on plausibility rules are "
          f"rows Part C flagged rather than fixed.)")

    print("\n=== Reconciliations (match %) ===")
    print(rec.pivot_table(index=["scope", "reconciliation"], columns="stage", values="match_pct", aggfunc="first")
          [["raw", "clean"]].to_string())

    print("\n=== IQR outliers (raw) ===")
    print(iqr[iqr.stage == "raw"][["table", "column", "lower_fence", "upper_fence", "high_outliers", "outlier_pct",
                                   "pct_high_uhnw", "pct_high_reconciled"]].to_string(index=False))
    print(f"  {sentence}")

    print("\n=== DATA QUALITY SCORECARD ===")
    print(score[["table", "stage", "rows", "pct_completeness", "pct_key_uniqueness", "pct_type_validity",
                 "pct_rule_pass", "pct_referential_match"]].to_string(index=False))
    print(f"  definitions: {args.out_dir / 'data_quality_scorecard_notes.md'}")

    # ---- Clean-stage checks on exact counts (explicit, so they also run under python -O) ----
    problems = clean_stage_problems(ri, rules, rec, score)
    if problems:
        print("\nCLEAN-STAGE CHECKS FAILED:\n  " + "\n  ".join(problems))
        sys.exit(1)
    print("\n  clean data: 0 orphans or unexpected blank keys, 0 duplicate keys, 0 invalid cells, every "
          "reconciliation 100%, every remaining rule failure is a flagged row ✓")
    print(f"\nSaved 6 reports to {args.out_dir}")


if __name__ == "__main__":
    main()
