"""
HW4 Part C — Cleaning program for the Wildcat Capital tables
MIS3060 Business Intelligence with AI

Implements decision_log.md, one decision at a time, in the order defended there:
    1. file names (D01)
    2. type / format fixes        D10 security_id, D15 return_ytd, D02 state
    3. quarantine duplicates      D03 dim_client
    4. quarantine orphans         D13 fact_transactions (needs the cleaned client list)
    5. sign fix                   D12 shares
    6. calendar correction        D09 is_trading_day
    7. flags                      D04, D14, D17, D18
    8. final proof                raw rows = clean + quarantined, keys unique, every relationship 100%

Rules followed (from the HW4 brief):
  * Raw files are read as TEXT and never modified (checked with a file hash at the end).
  * Same file names and columns; only 0/1 flag columns are added.
  * After EVERY step: print rows affected + a before/after check, and `assert` the after-state.
  * Repairs are reconciled against other columns before they are applied.
  * Nothing is deleted silently: removed rows go to data/audit/quarantine_*.csv.
  * Audit trail: data/audit/cleaning_log.csv and data/audit/value_changes.csv.

Run from the hw04 folder:
    python scripts/02_clean.py
"""
from __future__ import annotations   # type hints work on Python 3.7–3.9

import argparse
import hashlib
import sys
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HW_DIR = Path(__file__).resolve().parent.parent           # .../hw04
DEFAULT_RAW = HW_DIR / "02_Data" / "Raw"
DEFAULT_OUT = HW_DIR / "data"

# Table name -> glob for the raw file (raw exports carry " (2)" suffixes — see D01)
TABLES = {
    "dim_advisor": "dim_advisor*.csv",
    "dim_benchmark": "dim_benchmark*.csv",
    "dim_client": "dim_client*.csv",
    "dim_date": "dim_date*.csv",
    "dim_security": "dim_security*.csv",
    "fact_fees": "fact_fees*.csv",
    "fact_portfolio_snapshot": "fact_portfolio_snapshot*.csv",
    "fact_transactions": "fact_transactions*.csv",
}
PK = {
    "dim_advisor": "advisor_id", "dim_benchmark": "benchmark_id", "dim_client": "client_id",
    "dim_date": "date_id", "dim_security": "security_id", "fact_fees": "fee_id",
    "fact_portfolio_snapshot": "snapshot_id", "fact_transactions": "txn_id",
}
# (fact table, FK column, dim table, PK column, blanks allowed?)
RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id", False),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_fees", "client_id", "dim_client", "client_id", False),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id", False),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id", False),
    ("fact_transactions", "client_id", "dim_client", "client_id", False),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id", False),
    ("fact_transactions", "security_id", "dim_security", "security_id", True),   # blank on cash rows (D11)
    ("fact_fees", "fee_date", "dim_date", "date", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date", False),
    ("fact_transactions", "txn_date", "dim_date", "date", False),
]

US_STATES = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD",
    "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT", "Virginia": "VA", "Washington": "WA",
    "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

# D09 — NYSE full-day market closures on weekdays, 2020–2024 (from NYSE's published holiday
# schedule; 2022-01-01 fell on a Saturday and was not observed). Listed explicitly so each
# date can be checked by eye.
NYSE_HOLIDAYS = [
    # 2020
    "2020-01-01", "2020-01-20", "2020-02-17", "2020-04-10", "2020-05-25", "2020-07-03", "2020-09-07",
    "2020-11-26", "2020-12-25",
    # 2021
    "2021-01-01", "2021-01-18", "2021-02-15", "2021-04-02", "2021-05-31", "2021-07-05", "2021-09-06",
    "2021-11-25", "2021-12-24",
    # 2022
    "2022-01-17", "2022-02-21", "2022-04-15", "2022-05-30", "2022-06-20", "2022-07-04", "2022-09-05",
    "2022-11-24", "2022-12-26",
    # 2023
    "2023-01-02", "2023-01-16", "2023-02-20", "2023-04-07", "2023-05-29", "2023-06-19", "2023-07-04",
    "2023-09-04", "2023-11-23", "2023-12-25",
    # 2024
    "2024-01-01", "2024-01-15", "2024-02-19", "2024-03-29", "2024-05-27", "2024-06-19", "2024-07-04",
    "2024-09-02", "2024-11-28", "2024-12-25",
]

PLACEHOLDER_AUM = 1000.0          # D17: upstream default AUM, found in both snapshots and fees
RETURN_HIGH, RETURN_LOW = 1.0, -0.9   # D18: > +100% or < -90% YTD is implausible for these accounts
CASH_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}
TRADE_TYPES = {"Buy", "Sell"}

# ---------------------------------------------------------------------------
# Audit trail
# ---------------------------------------------------------------------------
CLEANING_LOG = []       # table, issue, action, rows_affected, note
VALUE_CHANGES = []      # DataFrames: table, key_column, key, column, old_value, new_value
QUARANTINE = {}         # name -> (source table, DataFrame of primary key + reason columns); rows are pulled from RAW


def log(decision, table, issue, action, rows, note=""):
    CLEANING_LOG.append({"decision": decision, "table": table, "issue": issue, "action": action,
                         "rows_affected": int(rows), "note": note})


def change(table, df, mask, column, new_values):
    """Apply AND log a change on exactly the same cells, so the audit trail can never drift
    from what happened. Only cells whose value really changes are touched. Returns the count."""
    pk = PK[table]
    new = new_values if isinstance(new_values, pd.Series) else pd.Series(new_values, index=df.index)
    mask = mask & (df[column] != new)
    VALUE_CHANGES.append(pd.DataFrame({
        "table": table, "key_column": pk, "key": df.loc[mask, pk].values,
        "column": column, "old_value": df.loc[mask, column].values, "new_value": new[mask].values,
    }))
    df.loc[mask, column] = new[mask]
    return int(mask.sum())


def banner(decision, title):
    print(f"\n[{decision}] {title}")


def show(before, after, rows):
    print(f"    rows affected: {rows:,}")
    print(f"    before: {before}")
    print(f"    after:  {after}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def is_blank(s: pd.Series) -> pd.Series:
    return s.str.strip().str.lower().isin({"", "nan", "null", "n/a", "na"})   # "None" is a real value (D06)


def to_num(s: pd.Series) -> pd.Series:
    """Strict numeric parse: plain or scientific-notation numbers only; anything else -> NaN."""
    ok = s.str.fullmatch(r"-?\d+(\.\d+)?([eE][-+]?\d+)?", na=False)
    return pd.to_numeric(s.where(ok), errors="coerce")


def fmt_decimal(x: float) -> str:
    """0.0928 -> '0.0928' (6 dp like the source column, trailing zeros trimmed)."""
    t = f"{x:.6f}".rstrip("0").rstrip(".")
    return "0" if t in ("", "-0") else t


def orphans(fact, fk, dim, pk, blanks_ok):
    key = fact[fk]
    blank = is_blank(key)
    bad = ~key.isin(set(dim[pk]))
    return (bad & ~blank) | (blank & (not blanks_ok))


def file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
def load_raw(raw_dir: Path):
    raw, paths = {}, {}
    for name, pattern in TABLES.items():
        matches = sorted(raw_dir.glob(pattern))
        if len(matches) != 1:
            sys.exit(f"Expected exactly one file for {name} ({pattern}) in {raw_dir}, found {[m.name for m in matches]}")
        paths[name] = matches[0]
        raw[name] = pd.read_csv(matches[0], dtype=str, keep_default_na=False)   # TEXT ONLY
        print(f"  {name:<25} {len(raw[name]):>8,} rows   <- {matches[0].name}")
    return raw, paths


# ---------------------------------------------------------------------------
# Cleaning steps — each one: check evidence, apply, print, assert
# ---------------------------------------------------------------------------
def d01_file_names(paths):
    banner("D01", "Standardize file names (drop ' (2)' suffix on output)")
    renamed = [p.name for n, p in paths.items() if p.stem != n]
    show(f"{len(renamed)} raw files with suffix: {renamed}", "clean files written as <table>.csv", len(renamed))
    log("D01", "all", "raw file names carry ' (2)' suffix", "standardize", len(renamed),
        "clean output uses plain table names")


def d10_security_id(t):
    banner("D10", "fact_transactions.security_id: '45.0' -> '45'")
    x, sec = t["fact_transactions"], t["dim_security"]
    col = x.security_id
    nonblank = ~is_blank(col)
    # Evidence check BEFORE changing anything: every non-blank ID is a whole number,
    # written either as '45' or '45.0' — no real decimals that stripping would mis-map
    bad_ids = col[nonblank & ~col.str.fullmatch(r"\d+(\.0)?", na=False)]
    assert bad_ids.empty, f"security_id values that are not whole numbers: {bad_ids.unique()[:5]} — stop"
    float_text = col.str.fullmatch(r"\d+\.0", na=False)
    before_orphans = orphans(x, "security_id", sec, "security_id", True).sum()
    n = change("fact_transactions", x, float_text, "security_id", col.str.replace(r"\.0$", "", regex=True))
    after_orphans = orphans(x, "security_id", sec, "security_id", True).sum()
    still_float = x.security_id.str.fullmatch(r"\d+\.0", na=False).sum()
    show(f"{float_text.sum():,} float-text IDs; {before_orphans:,} rows fail to join dim_security",
         f"{still_float} float-text IDs; {after_orphans} rows fail to join", n)
    assert n == float_text.sum() and still_float == 0
    assert after_orphans == 0, "security_id still has orphans after the format fix"
    log("D10", "fact_transactions", "security_id stored as float text ('45.0')", "standardize", n,
        f"stripped '.0'; orphans {before_orphans:,} -> {after_orphans}")


def d15_return_pct(t):
    banner("D15", "fact_portfolio_snapshot.return_ytd: '9.28%' -> 0.0928")
    p = t["fact_portfolio_snapshot"]
    pct = p.return_ytd.str.strip().str.endswith("%")
    recovered = to_num(p.return_ytd.str.strip().str.rstrip("%")) / 100
    bench, alpha = to_num(p.benchmark_return_ytd), to_num(p.active_alpha_ytd)
    # Reconcile BEFORE applying: return = benchmark + alpha must hold for every converted value
    ok_before = pct & ((recovered - (bench + alpha)).abs() < 1e-4)
    print(f"    reconciliation (before): {ok_before.sum():,} of {pct.sum():,} converted values equal "
          f"benchmark + alpha (tol 0.0001)")
    assert ok_before.sum() == pct.sum(), "a converted return does not reconcile — stop, do not guess"
    n = change("fact_portfolio_snapshot", p, pct, "return_ytd", recovered.map(fmt_decimal))
    # Reconcile AFTER: the value actually WRITTEN (rounded to 6 dp) must still reconcile
    written = to_num(p.return_ytd)
    ok_after = pct & ((written - (bench + alpha)).abs() < 1e-4)
    show(f"{pct.sum():,} percent-text values",
         f"{p.return_ytd.str.contains('%').sum()} percent-text; {written.isna().sum()} unparseable; "
         f"{ok_after.sum():,} of {pct.sum():,} written values reconcile", n)
    assert written.notna().all() and not p.return_ytd.str.contains("%").any()
    assert ok_after.sum() == pct.sum(), "a written return no longer reconciles after rounding"
    log("D15", "fact_portfolio_snapshot", "return_ytd stored as percent text", "convert", n,
        f"divided by 100; {ok_after.sum()} of {pct.sum()} written values reconcile to benchmark + alpha")


def d02_state(t):
    banner("D02", "dim_client.state: full names -> USPS codes")
    c = t["dim_client"]
    codes = set(US_STATES.values())
    lookup = {k.lower(): v for k, v in US_STATES.items()}
    lookup.update({v.lower(): v for v in codes})                 # ' pa' / 'pa' -> 'PA' too
    clean_key = c.state.str.strip().str.lower()
    bad = ~c.state.isin(codes)
    mapped = clean_key.map(lookup)
    unmapped = c.state[bad & mapped.isna()]
    assert unmapped.empty, f"state values with no mapping (incl. blanks): {unmapped.unique()[:10]}"
    before = c.state[bad].value_counts().to_dict()
    n = change("dim_client", c, bad, "state", mapped)
    show(f"{bad.sum()} non-code values {before}", f"{(~c.state.isin(codes)).sum()} values outside USPS codes", n)
    assert n == bad.sum() and c.state.isin(codes).all()
    log("D02", "dim_client", "state spelled out instead of 2-letter code", "standardize", n,
        f"mapped with a 51-entry state name->code lookup: {before}")


def d03_duplicate_clients(t):
    banner("D03", "dim_client: quarantine duplicate clients (last name differs only at the end)")
    c = t["dim_client"]
    key_cols = ["first_name", "age", "city", "zip_code", "initial_aum"]
    cid = pd.to_numeric(c.client_id, errors="coerce")
    assert cid.notna().all(), "non-numeric client_id — cannot pick the original by lowest ID"
    key = c[key_cols].apply(lambda s: s.str.strip().str.lower()).agg("|".join, axis=1)
    keeper = c.assign(_cid=cid, _key=key).sort_values("_cid").drop_duplicates("_key").set_index("_key").client_id
    dup = c.client_id != key.map(keeper)
    dups = c[dup]
    matched = key[dup].map(keeper)

    # Verify BEFORE removing anything
    orig = c.set_index("client_id").loc[matched]
    other = [col for col in c.columns if col not in ("client_id", "last_name")]
    same = (dups[other].values == orig[other].values).all(axis=1)
    pairs = list(zip(dups.last_name.str.strip().str.lower(), orig.last_name.str.strip().str.lower()))
    shortened = sum(o.startswith(d) and 0 < len(o) - len(d) <= 2 for d, o in pairs)
    extra = sum(d.startswith(o) and 0 < len(d) - len(o) <= 2 for d, o in pairs)
    used = set().union(*[set(t[f].client_id) for f in ("fact_fees", "fact_portfolio_snapshot", "fact_transactions")])
    print(f"    verification: {same.sum()}/{len(dups)} identical on all {len(other)} other fields; last names: "
          f"{shortened} shortened + {extra} with extra letter(s) at the end (max 2); "
          f"duplicates in facts: {dups.client_id.isin(used).sum()}; originals in facts: {matched.isin(used).sum()}")
    assert same.all(), "a duplicate differs from its match on a field other than last_name — stop and inspect"
    assert shortened + extra == len(dups), "a duplicate's last name differs by more than 1–2 letters at the end"
    assert not dups.client_id.isin(used).any(), "a duplicate client has fact rows — quarantining would orphan them"
    assert matched.isin(used).all(), "a kept original has no fact rows — the wrong record of the pair may be kept"

    QUARANTINE["dim_client_duplicates"] = ("dim_client", pd.DataFrame({
        "client_id": dups.client_id.values, "matched_client_id": matched.values,
        "quarantine_reason": f"D03 duplicate of matched_client_id: same {len(other)} other fields, "
                             f"last name differs only at the end, no fact rows"}))
    before = len(c)
    t["dim_client"] = c[~dup].reset_index(drop=True)
    kept = t["dim_client"]
    fact_clients = set(t["fact_fees"].client_id) | set(t["fact_portfolio_snapshot"].client_id)
    show(f"{before:,} clients", f"{len(kept):,} clients; {len(fact_clients):,} distinct clients in fees + snapshots",
         len(dups))
    assert len(kept) + len(dups) == before
    assert set(kept.client_id) == fact_clients, "kept clients != clients with fees/snapshots"
    log("D03", "dim_client", "duplicate clients (last name shortened or mistyped at the end)", "quarantine",
        len(dups), f"{shortened} shortened + {extra} extra letter; kept the original (lower ID, has fact rows); "
        f"{len(kept):,} clients = distinct clients in fees + snapshots")


def d13_orphan_transactions(t, raw):
    banner("D13", "fact_transactions: quarantine rows whose client_id is not in dim_client")
    x, c = t["fact_transactions"], t["dim_client"]
    bad = orphans(x, "client_id", c, "client_id", False)
    q = x[bad]
    # Independent check: these IDs are absent from the RAW client table too (not created by D03)
    assert not q.client_id.isin(set(raw["dim_client"].client_id)).any(), "an orphan exists in raw dim_client"
    QUARANTINE["fact_transactions_orphan_clients"] = ("fact_transactions", pd.DataFrame({
        "txn_id": q.txn_id.values, "quarantine_reason": "D13 client_id not found in dim_client"}))
    before = len(x)
    t["fact_transactions"] = x[~bad].reset_index(drop=True)
    after = t["fact_transactions"]
    show(f"{before:,} rows; {bad.sum()} orphan rows ({q.client_id.nunique()} distinct IDs, "
         f"${to_num(q.amount).sum():,.2f})", f"{len(after):,} rows; {after.client_id.isin(set(q.client_id)).sum()} "
         f"rows left with those IDs", bad.sum())
    assert len(after) + bad.sum() == before
    assert after.client_id.isin(set(c.client_id)).all()
    log("D13", "fact_transactions", "client_id with no matching client", "quarantine", bad.sum(),
        f"{q.client_id.nunique()} distinct IDs, ${to_num(q.amount).sum():,.2f} total amount kept in quarantine")


def d12_negative_shares(t):
    banner("D12", "fact_transactions.shares: remove sign on negative Buy quantities")
    x = t["fact_transactions"]
    sh, pr, am = to_num(x.shares), to_num(x.price), to_num(x.amount)
    neg = x.shares.str.strip().str.startswith("-")            # catches '-0' too
    types = x.loc[neg, "txn_type"].value_counts().to_dict()
    rec = ((sh.abs() * pr) - am).abs() <= 1.0
    print(f"    evidence: {neg.sum():,} negative rows, types {types}; {(neg & rec).sum():,} match amount once the "
          f"sign is dropped")
    assert set(types) <= {"Buy"}, f"negative shares on non-Buy rows {types} — decision only covers Buys"
    assert rec[neg].all(), "a negative-share row does not reconcile — stop, do not guess"
    n = change("fact_transactions", x, neg, "shares", x.shares.str.strip().str.lstrip("-"))
    sh2, pr2, am2 = to_num(x.shares), to_num(x.price), to_num(x.amount)
    trades = ~x.txn_type.isin(CASH_TYPES)
    unreadable = trades & (sh2.isna() | pr2.isna() | am2.isna())
    mism = trades & ~unreadable & (((sh2 * pr2) - am2).abs() > 1.0)
    show(f"{neg.sum()} negative shares", f"{x.shares.str.startswith('-').sum()} negative; {unreadable.sum()} trades "
         f"with unreadable shares/price/amount; {mism.sum()} where shares x price != amount", n)
    assert n == neg.sum() and not x.shares.str.startswith("-").any()
    assert unreadable.sum() == 0 and mism.sum() == 0
    log("D12", "fact_transactions", "negative shares on Buy rows", "convert", n,
        "absolute value; every row reconciled to amount before the change; all trades reconcile after")


def d09_trading_days(t):
    banner("D09", "dim_date.is_trading_day: market holidays -> 0")
    d = t["dim_date"]
    dt = pd.to_datetime(d.date, format="%Y-%m-%d")
    hol = pd.to_datetime(pd.Series(NYSE_HOLIDAYS))
    covered = set(hol.dt.year)
    assert set(dt.dt.year) <= covered, f"dim_date has years {sorted(set(dt.dt.year) - covered)} with no holiday list"
    assert hol.isin(dt).all() and (hol.dt.dayofweek < 5).all(), "holiday list must be weekdays inside dim_date"
    is_hol = d.date.isin(set(NYSE_HOLIDAYS))
    trading_before = (d.is_trading_day == "1").sum()
    n = change("dim_date", d, is_hol & (d.is_trading_day == "1"), "is_trading_day", "0")
    changed_dates = set(VALUE_CHANGES[-1]["key"].map(d.set_index("date_id").date))
    weekday = dt.dt.dayofweek < 5
    show(f"{n} holidays marked as trading days; {trading_before:,} trading days",
         f"{(is_hol & (d.is_trading_day == '1')).sum()} holidays marked trading; "
         f"{(d.is_trading_day == '1').sum():,} trading days", n)
    assert changed_dates <= set(NYSE_HOLIDAYS), "a non-holiday date was changed"
    assert (d.loc[is_hol, "is_trading_day"] == "0").all()
    assert (d.loc[weekday & ~is_hol, "is_trading_day"] == "1").all(), "an ordinary weekday is not a trading day"
    assert (d.loc[~weekday, "is_trading_day"] == "0").all(), "a weekend is marked as a trading day"
    assert (d.is_trading_day == "1").sum() == trading_before - n
    log("D09", "dim_date", "market holidays marked as trading days", "standardize", n,
        f"set to 0 using NYSE full-day closures {min(covered)}–{max(covered)} (list in script)")


def add_flag(df, name, mask):
    df[name] = mask.astype(int).astype(str)


def flags(t):
    # D04
    banner("D04", "dim_client: flag_risk_profile_missing")
    c = t["dim_client"]
    m = is_blank(c.risk_profile)
    add_flag(c, "flag_risk_profile_missing", m)
    show(f"{m.sum()} blank risk profiles", f"flag = 1 on {(c.flag_risk_profile_missing == '1').sum()} rows; "
         f"{is_blank(c.risk_profile).sum()} still blank (not filled)", m.sum())
    assert (c.flag_risk_profile_missing == "1").sum() == is_blank(c.risk_profile).sum()
    log("D04", "dim_client", "risk_profile blank", "flag", m.sum(),
        "left blank (compliance record); snapshots suggest Balanced (benchmark 3) — see decision log")

    # D14 — flag uses the corrected calendar; the assert recomputes it independently
    # from the weekday + the NYSE list, without dim_date
    banner("D14", "fact_transactions: flag_non_trading_day on Buy/Sell")
    x, d = t["fact_transactions"], t["dim_date"]
    trading = x.txn_date.map(d.set_index("date").is_trading_day)
    assert trading.notna().all(), "a txn_date is missing from dim_date"
    trade = x.txn_type.isin(TRADE_TYPES)
    m = trade & (trading == "0")
    add_flag(x, "flag_non_trading_day", m)
    dow = pd.to_datetime(x.txn_date, format="%Y-%m-%d").dt.dayofweek
    weekend, holiday = trade & (dow >= 5), trade & (dow < 5) & x.txn_date.isin(set(NYSE_HOLIDAYS))
    show(f"{trade.sum():,} Buy/Sell rows", f"flag = 1 on {m.sum():,} ({weekend.sum():,} weekend + "
         f"{holiday.sum():,} holiday); dates unchanged", m.sum())
    assert m.sum() == weekend.sum() + holiday.sum(), "flag disagrees with the independent weekday + holiday count"
    log("D14", "fact_transactions", "Buy/Sell dated on a weekend or market holiday", "flag", m.sum(),
        f"{weekend.sum()} weekend + {holiday.sum()} holiday; dates not moved")

    # D17 — both tables, reconciled to each other
    banner("D17", f"flag_aum_placeholder (AUM = {PLACEHOLDER_AUM:,.0f}) in snapshots and fees")
    p, f = t["fact_portfolio_snapshot"], t["fact_fees"]
    mp, mf = to_num(p.aum) == PLACEHOLDER_AUM, to_num(f.aum_basis) == PLACEHOLDER_AUM
    add_flag(p, "flag_aum_placeholder", mp)
    add_flag(f, "flag_aum_placeholder", mf)
    fee_keys = set(zip(f.loc[mf, "client_id"], f.loc[mf, "fee_date"]))
    snap_keys = set(zip(p.loc[mp, "client_id"], p.loc[mp, "snapshot_date"]))
    all_fee_months = set(zip(f.client_id, f.fee_date))
    no_fee = len(snap_keys - all_fee_months)
    print(f"    reconciliation: {len(fee_keys & snap_keys)} of {len(fee_keys)} flagged fee months match a flagged "
          f"snapshot; {no_fee} flagged snapshots have no fee row at all")
    show(f"{mp.sum()} snapshot + {mf.sum()} fee rows at {PLACEHOLDER_AUM:,.0f}",
         f"flagged {mp.sum()} snapshots ({p.loc[mp, 'client_id'].nunique()} clients) and {mf.sum()} fees; "
         f"values unchanged", mp.sum() + mf.sum())
    assert fee_keys <= snap_keys, "a placeholder fee has no placeholder snapshot — the two tables disagree"
    assert len(snap_keys - fee_keys) == no_fee, "a placeholder snapshot has a fee with a different AUM basis"
    log("D17", "fact_portfolio_snapshot", "AUM = 1000.0 placeholder", "flag", mp.sum(),
        f"{p.loc[mp, 'client_id'].nunique()} clients; {no_fee} have no fee row; not interpolated")
    log("D17", "fact_fees", "aum_basis = 1000.0 placeholder", "flag", mf.sum(),
        f"{len(fee_keys & snap_keys)} of {len(fee_keys)} match a flagged snapshot month")

    # D18 (after D15, so converted percent values are included). Rule uses return_ytd only;
    # the assert confirms no extreme alpha is left unflagged.
    banner("D18", "fact_portfolio_snapshot: flag_return_implausible")
    r, a = to_num(p.return_ytd), to_num(p.active_alpha_ytd)
    m = (r > RETURN_HIGH) | (r < RETURN_LOW)
    add_flag(p, "flag_return_implausible", m)
    from_pct = (m & p.snapshot_id.isin(set(VALUE_CHANGES_KEYS("fact_portfolio_snapshot", "return_ytd")))).sum()
    alpha_unflagged = ((a.abs() > 2) & ~m).sum()
    show(f"{(r > RETURN_HIGH).sum()} returns > +100%, {(r < RETURN_LOW).sum()} < -90%",
         f"flag = 1 on {m.sum():,} rows ({(m & mp).sum()} also AUM placeholder; {from_pct} were converted in D15); "
         f"{alpha_unflagged} extreme alphas left unflagged", m.sum())
    assert alpha_unflagged == 0, "an extreme alpha is not covered by the return rule"
    log("D18", "fact_portfolio_snapshot", "YTD return > +100% or < -90%", "flag", m.sum(),
        f"{from_pct} of these were percent text converted in D15; alpha not used in the rule "
        f"({alpha_unflagged} extreme alphas unflagged)")


def VALUE_CHANGES_KEYS(table, column):
    keys = [v.key for v in VALUE_CHANGES if len(v) and v.table.iloc[0] == table and v.column.iloc[0] == column]
    return pd.concat(keys) if keys else pd.Series(dtype=str)


def leave_as_is(t):
    """Decisions that change nothing — checked and logged so the audit trail shows they were considered."""
    banner("--", "Leave-as-is decisions (checked, logged, no changes)")
    c, s, x, f, p, adv = (t[k] for k in ["dim_client", "dim_security", "fact_transactions", "fact_fees",
                                         "fact_portfolio_snapshot", "dim_advisor"])
    items = []

    since = pd.to_datetime(c.client_since, format="%Y-%m-%d")
    dmin = pd.to_datetime(t["dim_date"].date, format="%Y-%m-%d").min()
    items.append(("D05", "dim_client", "client_since before dim_date coverage", (since < dmin).sum(),
                  "attribute, not a date FK — do not relate to dim_date"))

    items.append(("D06", "dim_advisor", "certifications = 'None'", (adv.certifications == "None").sum(),
                  "'None' means no certification; read with keep_default_na=False"))

    etf = s.is_etf == "True"
    assert (is_blank(s.sector) == etf).all(), "sector blanks no longer line up 1:1 with ETFs"
    assert (is_blank(s.expense_ratio_bps) == ~etf).all(), "expense-ratio blanks no longer line up 1:1 with stocks"
    items.append(("D07", "dim_security", "sector blank on ETFs / expense ratio blank on stocks",
                  is_blank(s.sector).sum() + is_blank(s.expense_ratio_bps).sum(),
                  f"verified 1:1 with is_etf ({etf.sum()} ETFs, {(~etf).sum()} stocks)"))

    assert s.ticker.is_unique, "tickers are not unique — D08 reasoning no longer holds"
    items.append(("D08", "dim_security", "repeated security names", s.name.duplicated(keep=False).sum(),
                  "different tickers/IDs (tickers verified unique) — use ticker, not name"))

    cash = x.txn_type.isin(CASH_TYPES)
    blank3 = is_blank(x.security_id) & is_blank(x.shares) & is_blank(x.price)
    assert (blank3 == cash).all(), "security/shares/price blanks do not line up exactly with cash transactions"
    items.append(("D11", "fact_transactions", "security/shares/price blank on cash movements", blank3.sum(),
                  "verified: blank in all three on every cash row and on no trade/dividend row"))

    sci = sum(p[col].str.contains(r"\d[eE][-+]?\d", regex=True).sum() for col in ("return_ytd", "active_alpha_ytd"))
    items.append(("D16", "fact_portfolio_snapshot", "scientific notation in return columns", sci, "valid numbers"))

    hi = f[to_num(f.bps_charged) > 100]
    items.append(("D19", "fact_fees", "bps_charged above 100", len(hi),
                  f"fee_id {', '.join(hi.fee_id)}; within client's range; amount reconciles"))

    fk = set(zip(f.client_id, f.fee_date))
    unbilled = sum((k not in fk) for k in zip(p.client_id, p.snapshot_date))
    items.append(("D20", "fact_portfolio_snapshot", "snapshot month with no fee row", unbilled,
                  "fees not invented; documented as limitation"))

    cs = pd.to_datetime(p.client_id.map(c.set_index("client_id").client_since), format="%Y-%m-%d")
    sd = pd.to_datetime(p.snapshot_date, format="%Y-%m-%d")
    same_month = ((sd < cs) & (sd.dt.to_period("M") == cs.dt.to_period("M"))).sum()
    earlier = ((sd < cs) & (sd.dt.to_period("M") < cs.dt.to_period("M"))).sum()
    assert earlier == 0, "a snapshot is dated in a month before the client joined"
    items.append(("D21", "fact_portfolio_snapshot", "snapshot on the 1st of the joining month", same_month,
                  "monthly grain; 0 snapshots in an earlier month"))

    for dec, tbl, issue, n, note in items:
        print(f"    {dec} {tbl}: {issue} — {n:,} rows left as is")
        log(dec, tbl, issue, "leave as is", n, note)


# ---------------------------------------------------------------------------
# Final proof
# ---------------------------------------------------------------------------
def build_quarantine(raw):
    """Quarantine files hold the ORIGINAL raw rows (no format fixes) plus reason columns."""
    out = {}
    for qname, (src, keys) in QUARANTINE.items():
        pk = PK[src]
        out[qname] = (src, raw[src].merge(keys, on=pk, how="inner", validate="one_to_one"))
        assert len(out[qname][1]) == len(keys), f"{qname}: quarantined keys not all found in raw"
    return out


def final_value_changes(t):
    """Changes on rows that were later quarantined are dropped: those rows are kept raw in quarantine."""
    vc = pd.concat(VALUE_CHANGES, ignore_index=True)
    kept = pd.Series(False, index=vc.index)
    for tb, g in vc.groupby("table"):
        kept[g.index] = g.key.isin(set(t[tb][PK[tb]]))
    dropped = vc[~kept].groupby("table").size().to_dict()
    return vc[kept].reset_index(drop=True), dropped


def final_checks(raw, t, quarantine, vc):
    print("\n=== FINAL CHECKS ===")
    q_rows = {name: 0 for name in TABLES}
    for src, qdf in quarantine.values():
        q_rows[src] += len(qdf)

    rec = []
    for name in TABLES:
        r, c, q = len(raw[name]), len(t[name]), q_rows[name]
        rec.append({"table": name, "raw_rows": r, "clean_rows": c, "quarantined_rows": q, "balanced": r == c + q})
        assert r == c + q, f"{name}: raw {r} != clean {c} + quarantined {q}"
        assert list(t[name].columns[:len(raw[name].columns)]) == list(raw[name].columns), f"{name}: columns changed"
        for col in t[name].columns[len(raw[name].columns):]:
            assert col.startswith("flag_") and set(t[name][col]) <= {"0", "1"}, f"{name}.{col} is not a 0/1 flag"
        pk = t[name][PK[name]]
        assert pk.is_unique and not is_blank(pk).any(), f"{name}: primary key not unique / has blanks"
    print(pd.DataFrame(rec).to_string(index=False))
    print("  raw rows = clean rows + quarantined rows for every table ✓")
    print("  primary keys unique and non-blank; original columns unchanged; added columns are 0/1 flags ✓")

    # Strongest proof: compare every cell of every kept row, raw vs clean. Every difference must be
    # in value_changes, every logged change must be a real difference, and old/new values must match.
    print("\n  Raw vs clean, cell by cell (kept rows):")
    for name in TABLES:
        pk = PK[name]
        cols = [col for col in raw[name].columns if col != pk]
        r = raw[name].set_index(pk).loc[t[name][pk], cols]
        c = t[name].set_index(pk)[cols]
        diff = r.ne(c)
        actual = {(k, col) for col in cols for k in diff.index[diff[col].values]}
        logged = vc[vc.table == name]
        logged_set = set(zip(logged.key, logged.column))
        assert actual == logged_set, f"{name}: {len(actual - logged_set)} unlogged and {len(logged_set - actual)} " \
                                     f"logged-but-not-made changes"
        for col, g in logged.groupby("column"):
            assert (g.old_value.values == r.loc[g.key, col].values).all(), f"{name}.{col}: old_value != raw"
            assert (g.new_value.values == c.loc[g.key, col].values).all(), f"{name}.{col}: new_value != clean"
        print(f"    {name}: {len(actual):,} cells differ = {len(logged_set):,} logged in value_changes")
    print("  every changed cell is logged, and every logged change happened ✓")

    print("\n  Referential integrity (clean):")
    for ft, fk, dt, pk, blanks_ok in RELATIONSHIPS:
        bad = orphans(t[ft], fk, t[dt], pk, blanks_ok).sum()
        nonblank = (~is_blank(t[ft][fk])).sum()
        rate = 100 * (nonblank - bad) / nonblank if nonblank else 100.0
        print(f"    {ft}.{fk} -> {dt}.{pk}: {rate:.2f}% match, {bad} orphans")
        assert bad == 0
    print(f"  all {len(RELATIONSHIPS)} relationships 100% ✓")


# ---------------------------------------------------------------------------
# Outputs
# ---------------------------------------------------------------------------
def write_outputs(t, out_dir: Path, quarantine, vc):
    clean_dir, audit_dir = out_dir / "clean", out_dir / "audit"
    clean_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)
    for name, df in t.items():
        df.to_csv(clean_dir / f"{name}.csv", index=False)
    pd.DataFrame(CLEANING_LOG).to_csv(audit_dir / "cleaning_log.csv", index=False)
    vc.to_csv(audit_dir / "value_changes.csv", index=False)
    for qname, (src, qdf) in quarantine.items():
        qdf.to_csv(audit_dir / f"quarantine_{qname}.csv", index=False)
    return clean_dir, audit_dir


def write_readme(t, clean_dir: Path, vc: pd.DataFrame):
    lg = pd.DataFrame(CLEANING_LOG)
    n = lambda dec, table=None: int(lg[(lg.decision == dec) & ((lg.table == table) if table else True)]
                                    .rows_affected.sum())
    flag_rows = []
    for name, df in t.items():
        for col in [c for c in df.columns if c.startswith("flag_")]:
            flag_rows.append(f"| `{name}.{col}` | {(df[col] == '1').sum():,} | {FLAG_MEANING.get(col, '')} |")
    hi = t["fact_fees"][to_num(t["fact_fees"].bps_charged) > 100]
    text = README_TEMPLATE.format(
        counts="\n".join(f"| `{k}.csv` | {len(v):,} |" for k, v in t.items()),
        flags="\n".join(flag_rows), n_changes=len(vc), n_rel=len(RELATIONSHIPS),
        d05=n("D05"), d11=n("D11"), d14=n("D14"), d17p=n("D17", "fact_portfolio_snapshot"),
        d17f=n("D17", "fact_fees"), d18=n("D18"), d20=n("D20"), d04=n("D04"),
        d19=", ".join(f"{b} bps (fee_id {i})" for b, i in zip(hi.bps_charged, hi.fee_id)) or "none",
    )
    (clean_dir / "README_clean.md").write_text(text, encoding="utf-8")


FLAG_MEANING = {
    "flag_risk_profile_missing": "risk profile blank; not filled (D04)",
    "flag_non_trading_day": "Buy/Sell dated on a weekend or NYSE holiday; date not moved (D14)",
    "flag_aum_placeholder": "AUM / AUM basis is the 1,000 placeholder; real value unknown (D17)",
    "flag_return_implausible": "YTD return > +100% or < -90% (D18)",
}

README_TEMPLATE = """# Wildcat Capital — clean tables (HW4)

Produced by `scripts/02_clean.py` from the raw files in `02_Data/Raw` (never modified).
Every change is in `data/audit/value_changes.csv` ({n_changes:,} cell changes on kept rows); every step is in
`data/audit/cleaning_log.csv`; removed rows are in `data/audit/quarantine_*.csv` with their **original raw values**.
Decision IDs (D01–D21) refer to `decision_log.md`.

## Tables

| File | Rows |
|---|---:|
{counts}

## Relationships (all {n_rel} matched 100% in the clean data)

| From (many) | To (one) | Note |
|---|---|---|
| `dim_client.advisor_id` | `dim_advisor.advisor_id` | |
| `dim_security.benchmark_id` | `dim_benchmark.benchmark_id` | |
| `fact_fees.client_id` | `dim_client.client_id` | |
| `fact_fees.advisor_id` | `dim_advisor.advisor_id` | |
| `fact_fees.fee_date` | `dim_date.date` | |
| `fact_portfolio_snapshot.client_id` | `dim_client.client_id` | |
| `fact_portfolio_snapshot.advisor_id` | `dim_advisor.advisor_id` | |
| `fact_portfolio_snapshot.benchmark_id` | `dim_benchmark.benchmark_id` | |
| `fact_portfolio_snapshot.snapshot_date` | `dim_date.date` | |
| `fact_transactions.client_id` | `dim_client.client_id` | |
| `fact_transactions.advisor_id` | `dim_advisor.advisor_id` | |
| `fact_transactions.security_id` | `dim_security.security_id` | blank on cash rows — allow blanks |
| `fact_transactions.txn_date` | `dim_date.date` | |

`dim_client.client_since` is **not** a date key: {d05:,} clients joined before 2020, outside `dim_date` (D05).
Fees and snapshots share the grain *client × month* but should not be joined directly; relate both to the dimensions.

## Column types for a BI tool

| Type | Columns |
|---|---|
| Whole number | all `*_id` columns, `age`, `years_experience`, `aum_target_mm`, `year`, `quarter`, `month`, `week_of_year` |
| Decimal | `initial_aum`, `aum`, `aum_basis`, `amount`, `bps_charged`, `shares`, `price`, `expense_ratio_bps`, `return_ytd`, `benchmark_return_ytd`, `active_alpha_ytd`, `cash_pct` |
| Date (YYYY-MM-DD) | `date`, `client_since`, `fee_date`, `snapshot_date`, `txn_date` |
| True/False | `is_active`, `is_etf` |
| 0/1 (whole number) | `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day`, all `flag_*` |
| Text | everything else — keep `zip_code` as **text** (leading zeros) |

Returns, alpha and `cash_pct` are decimals (0.05 = 5%). Some tiny values are written in scientific notation (`-1.9e-05`); they parse as decimals (D16).
Read `dim_advisor.certifications` as text: the value `None` means "no certification" (D06), and a default CSV reader turns it into a blank.

## Flag columns added

| Column | Rows = 1 | Meaning |
|---|---:|---|
{flags}

## Known limitations (not fixed, on purpose)

- **Blank risk profiles ({d04} clients).** Not filled: a risk profile is a compliance record. Their snapshots all use the 60/40 benchmark that only Balanced clients use, so re-profiling is recommended (D04).
- **Trade dates on weekends/holidays ({d14:,} Buy/Sell rows).** No evidence of the correct date, so dates were not moved; day-level trading analysis is unreliable, month-level is fine (D14).
- **AUM placeholder ({d17p} snapshots, {d17f} fees).** Real AUM unknown; not interpolated. Exclude flagged rows from AUM totals and fee-rate measures (D17).
- **Implausible returns ({d18:,} snapshots).** Values kept (they reconcile with benchmark + alpha); many come from the placeholder AUM base. Use medians or exclude flagged rows (D18).
- **Snapshot months with no fee ({d20:,}).** Fees are not invented; fee-to-AUM ratios are understated in those months (D20).
- **Cash movements have no security ({d11:,} rows).** Legitimate; the `security_id` relationship must allow blanks (D11).
- **Fees above 100 bps: {d19}.** Left as is: within the client's history and the amount reconciles (D19).
- **Trading calendar.** `is_trading_day` now excludes NYSE full-day holidays; special one-off closures are not modelled (D09).
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Clean the raw Wildcat Capital tables")
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    print(f"Reading raw tables from {args.raw_dir}")
    raw, paths = load_raw(args.raw_dir)
    hashes = {n: file_hash(p) for n, p in paths.items()}
    t = {n: df.copy() for n, df in raw.items()}          # work on copies; `raw` stays untouched

    d01_file_names(paths)
    d10_security_id(t)
    d15_return_pct(t)
    d02_state(t)
    d03_duplicate_clients(t)
    d13_orphan_transactions(t, raw)
    d12_negative_shares(t)
    d09_trading_days(t)
    flags(t)
    leave_as_is(t)

    quarantine = build_quarantine(raw)
    vc, dropped = final_value_changes(t)
    if dropped:
        print(f"\n  value_changes: dropped changes on rows that were later quarantined {dropped} "
              f"(quarantine files keep those rows' raw values)")
        log("--", "all", "format fixes on rows later quarantined", "not logged in value_changes",
            sum(dropped.values()), f"quarantine files hold the original raw rows: {dropped}")
    final_checks(raw, t, quarantine, vc)
    clean_dir, audit_dir = write_outputs(t, args.out_dir, quarantine, vc)
    write_readme(t, clean_dir, vc)

    assert all(file_hash(p) == hashes[n] for n, p in paths.items()), "a raw file was modified!"
    print("  raw files unchanged (hash check) ✓")

    print(f"\nSaved {len(t)} clean tables + README_clean.md -> {clean_dir}")
    print(f"Saved cleaning_log.csv ({len(CLEANING_LOG)} steps), value_changes.csv ({len(vc):,} changes), "
          f"{len(quarantine)} quarantine files -> {audit_dir}")


if __name__ == "__main__":
    main()
