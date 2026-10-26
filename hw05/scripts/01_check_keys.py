"""
HW5 Parts A and B — Prove the keys and the grain in code
MIS3060 Business Intelligence with AI

Checks the eight clean Wildcat Capital tables, exactly as they will be loaded into Power BI:

  1. Row and column counts — each table matches the counts in the HW5 brief (Part D: counts reconcile)
  2. Primary keys        — every PK is unique and never blank (Part A)
  3. Date join column    — dim_date[date] is unique, so the facts can join on it (Part A note)
  4. Foreign keys        — every FK value exists in its dimension; blanks are allowed only
                           where Part A says so (fact_transactions[security_id] on cash rows).
                           Uses check_referential_integrity() from HW4 scripts/03_validate.py
  5. Grain               — each fact is unique on the columns its grain sentence names (Part B);
                           for transactions, shows that no combination of other columns is unique
  6. Advisor paths       — the advisor_id on each fact row equals the client's advisor in
                           dim_client (evidence for Part E question b)

Every check prints PASS, FAIL or INFO (evidence, not a test) and is saved to
reports/key_checks.csv. A data fault shows as FAIL rather than crashing the script.
The script exits with code 1 if any check fails.

Dependency: importing hw04/scripts/03_validate.py also runs the top level of HW4's
02_clean.py and 01_profile.py (definitions only). If those files move, this script stops.

Run from the hw05 folder (the HW4 virtual environment has everything this needs):
    source ../hw04/.venv/bin/activate
    python scripts/01_check_keys.py
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

HW_DIR = Path(__file__).resolve().parent.parent            # .../hw05
DATA_DIR = HW_DIR / "02_Data" / "Cleaned"
OUT_DIR = HW_DIR / "reports"
HW4_VALIDATE = HW_DIR.parent / "hw04" / "scripts" / "03_validate.py"


# ---------------------------------------------------------------------------
# Reuse the HW4 referential-integrity function (the brief asks for this)
# ---------------------------------------------------------------------------
def load_hw4_function():
    """Import check_referential_integrity() and is_blank() from HW4's 03_validate.py.
    The file name starts with a digit, so it can't be imported with a normal import line."""
    if not HW4_VALIDATE.exists():
        sys.exit(f"Can't find {HW4_VALIDATE}. This script expects hw04/ next to hw05/ in the repo.")
    spec = importlib.util.spec_from_file_location("hw04_validate", HW4_VALIDATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.check_referential_integrity, mod.is_blank


check_referential_integrity, is_blank = load_hw4_function()


# ---------------------------------------------------------------------------
# What Part A and Part B claim (the script tests these claims)
# ---------------------------------------------------------------------------
# table -> (expected rows, expected columns from the HW5 brief, primary key)
TABLES = {
    "dim_advisor":             (25,      7,  "advisor_id"),
    "dim_benchmark":           (8,       4,  "benchmark_id"),
    "dim_client":              (2_500,   14, "client_id"),
    "dim_date":                (1_827,   12, "date_id"),
    "dim_security":            (500,     8,  "security_id"),
    "fact_fees":               (122_197, 8,  "fee_id"),
    "fact_portfolio_snapshot": (129_547, 14, "snapshot_id"),
    "fact_transactions":       (298_572, 10, "txn_id"),
}

# (from table, foreign key, to table, to column, blanks allowed?)
FOREIGN_KEYS = [
    ("dim_client",              "advisor_id",    "dim_advisor",   "advisor_id",   False),
    ("dim_security",            "benchmark_id",  "dim_benchmark", "benchmark_id", False),
    ("fact_fees",               "client_id",     "dim_client",    "client_id",    False),
    ("fact_fees",               "advisor_id",    "dim_advisor",   "advisor_id",   False),
    ("fact_fees",               "fee_date",      "dim_date",      "date",         False),
    ("fact_portfolio_snapshot", "client_id",     "dim_client",    "client_id",    False),
    ("fact_portfolio_snapshot", "advisor_id",    "dim_advisor",   "advisor_id",   False),
    ("fact_portfolio_snapshot", "benchmark_id",  "dim_benchmark", "benchmark_id", False),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date",      "date",         False),
    ("fact_transactions",       "client_id",     "dim_client",    "client_id",    False),
    ("fact_transactions",       "advisor_id",    "dim_advisor",   "advisor_id",   False),
    ("fact_transactions",       "security_id",   "dim_security",  "security_id",  True),   # cash rows
    ("fact_transactions",       "txn_date",      "dim_date",      "date",         False),
]

# Transaction types that move cash and carry no security (Part A note, Part E question a)
CASH_TYPES = {"Deposit", "Withdrawal", "Advisory Fee"}

# Part B: the columns each grain sentence names. The fact must be unique on them.
GRAIN = {
    "fact_fees":               ["client_id", "fee_date"],        # one fee charge per client per month
                                                                 # (one fee_type per client-month, not one row per type)
    "fact_portfolio_snapshot": ["client_id", "snapshot_date"],   # one snapshot per client per month
    "fact_transactions":       ["txn_id"],                       # one row per transaction (no natural key;
                                                                 # this repeats the PK check, see the INFO row)
}
# Monthly facts are dated the 1st of the month; checked so "per month" is really true
MONTHLY_DATE = {"fact_fees": "fee_date", "fact_portfolio_snapshot": "snapshot_date"}


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------
results = []


def record(part, check, table, column, passed, detail):
    """passed: True -> PASS, False -> FAIL, None -> INFO (evidence that is saved but not tested)."""
    result = "INFO" if passed is None else ("PASS" if passed else "FAIL")
    results.append({"part": part, "check": check, "table": table, "column": column,
                    "result": result, "detail": detail})
    print(f"  [{result}] {table}.{column}: {detail}")


def load_tables() -> dict:
    """Read every column as text, the way a key is compared in a join. A blank cell stays ''."""
    t = {}
    for name in TABLES:
        path = DATA_DIR / f"{name}.csv"
        if not path.exists():
            sys.exit(f"Missing {path}. Check the file name (no ' (2)' suffix) and folder.")
        t[name] = pd.read_csv(path, dtype=str, keep_default_na=False)
    return t


def check_row_counts(t):
    print("\n1. Row and column counts vs the HW5 brief")
    for name, (rows, cols, _) in TABLES.items():
        n, c = t[name].shape
        record("D", "row_col_count", name, "*", n == rows and c == cols,
               f"{n:,} rows x {c} columns (brief says {rows:,} x {cols})")


def check_primary_keys(t):
    print("\n2. Primary keys are unique and never blank")
    for name, (_, _, pk) in TABLES.items():
        s = t[name][pk]
        blanks, dupes = int(is_blank(s).sum()), int(s.duplicated().sum())
        record("A", "pk_unique_not_blank", name, pk, blanks == 0 and dupes == 0,
               f"{s.nunique():,} distinct values, {dupes} duplicates, {blanks} blanks")


def check_date_join_column(t):
    print("\n3. dim_date[date] can be the one side of the date relationships")
    s = t["dim_date"]["date"]
    ok = s.is_unique and not is_blank(s).any()
    record("A", "date_join_unique", "dim_date", "date", ok,
           f"{s.nunique():,} distinct dates, {s.min()} to {s.max()}")


def check_foreign_keys(t):
    print("\n4. Foreign keys match their dimension (HW4 check_referential_integrity)")
    for src, fk, dim, dim_col, blanks_ok in FOREIGN_KEYS:
        r = check_referential_integrity(t[src], fk, t[dim], dim_col)
        bad_blanks = 0 if blanks_ok else r["null_key_rows"]
        ok = r["orphan_row_count"] == 0 and bad_blanks == 0 and r["dim_key_unique"]
        detail = (f"-> {dim}[{dim_col}]: {r['matched_rows']:,} matched, "
                  f"{r['orphan_row_count']} orphans, {r['null_key_rows']:,} blanks"
                  f"{' (allowed)' if blanks_ok and r['null_key_rows'] else ''}")
        if r["orphan_row_count"]:
            detail += f"; orphan examples: {r['orphan_key_examples']}"
        record("A", "fk_integrity", src, fk, ok, detail)

    # The blank security_ids must be exactly the cash rows, and no cash row may carry a security
    tx = t["fact_transactions"]
    blank = is_blank(tx["security_id"])
    is_cash = tx["txn_type"].isin(CASH_TYPES)
    by_type = tx.loc[blank, "txn_type"].value_counts().to_dict()
    ok = bool((blank == is_cash).all())
    record("A", "blank_fk_explained", "fact_transactions", "security_id", ok,
           f"blank on {int(blank.sum()):,} rows, all cash types: {by_type}; "
           f"{int((blank & ~is_cash).sum())} non-cash rows blank, "
           f"{int((~blank & is_cash).sum())} cash rows with a security")


def check_grain(t):
    print("\n5. Grain: each fact is unique on the columns its grain sentence names")
    for fact, cols in GRAIN.items():
        df = t[fact]
        dupes = int(df.duplicated(cols).sum())
        record("B", "grain_unique", fact, " + ".join(cols), dupes == 0,
               f"{dupes} duplicate rows on ({', '.join(cols)})")
    for fact, col in MONTHLY_DATE.items():
        dates = pd.to_datetime(t[fact][col], format="%Y-%m-%d", errors="coerce")   # unreadable -> NaT
        bad = int((dates.isna() | (dates.dt.day != 1)).sum())
        record("B", "monthly_date", fact, col, bad == 0,
               f"{bad} dates unreadable or not on the 1st of the month")

    # Transactions have no natural key: show it, so Part B can say why txn_id is the grain
    tx = t["fact_transactions"]
    natural = ["client_id", "txn_date", "txn_type", "security_id"]
    repeats = int(tx.duplicated(natural).sum())
    record("B", "no_natural_key", "fact_transactions", " + ".join(natural), None,
           f"{repeats:,} rows repeat ({', '.join(natural)}), so only txn_id identifies a transaction")


def check_advisor_paths(t):
    print("\n6. advisor_id on each fact agrees with the client's advisor in dim_client (Part E b)")
    # Drop duplicate client_ids so a bad dim_client can't crash .map(); the PK check reports them.
    # Duplicated clients map to NaN and show up here as mismatches.
    dc = t["dim_client"]
    client_advisor = dc[~dc["client_id"].duplicated(keep=False)].set_index("client_id")["advisor_id"]
    for fact in GRAIN:
        df = t[fact]
        mismatch = int((df["client_id"].map(client_advisor) != df["advisor_id"]).sum())
        record("E", "advisor_paths_agree", fact, "advisor_id", mismatch == 0,
               f"{mismatch:,} rows where it differs from dim_client[advisor_id]")


def main():
    print(f"Reading clean tables from {DATA_DIR}")
    t = load_tables()
    check_row_counts(t)
    check_primary_keys(t)
    check_date_join_column(t)
    check_foreign_keys(t)
    check_grain(t)
    check_advisor_paths(t)

    OUT_DIR.mkdir(exist_ok=True)
    out = pd.DataFrame(results)
    out.to_csv(OUT_DIR / "key_checks.csv", index=False)
    tested = out[out["result"] != "INFO"]
    failed = int((tested["result"] == "FAIL").sum())
    print(f"\n{len(tested) - failed} of {len(tested)} checks passed "
          f"({len(out) - len(tested)} INFO rows). Results: {OUT_DIR / 'key_checks.csv'}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
