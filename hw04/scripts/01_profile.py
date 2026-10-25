"""
HW4 Part A — Audit of the raw Wildcat Capital tables
MIS3060 Business Intelligence with AI

What this script does
---------------------
1. Reads every raw table AS TEXT (dtype=str, keep_default_na=False), so nothing
   is silently converted before we look at it.
2. Runs one GENERIC profiler (`profile_column`) on every column of every table.
   The profiler knows nothing about Wildcat Capital: it works on any DataFrame.
3. Runs four groups of data-quality checks, driven by the SCHEMA config below:
      1. Column level        — type, allowed values, ranges, key uniqueness
      2. Single-table rules  — duplicates, near-duplicates, row contradictions
      3. Referential integrity — every foreign key points to an existing key
      4. Cross-table rules   — facts that disagree with dimensions / each other
   Each finding is tagged ERROR, WARN or INFO.
4. Writes:
      reports/profile_raw.csv     one row per table x column
      reports/dq_summary_raw.csv  one row per finding

The check *engine* is generic; the *business knowledge* (types, allowed values,
keys, relationships) lives in the SCHEMA / RELATIONSHIPS config, so a new table
can be audited by adding a config entry instead of new code.

Run from the hw04 folder:
    python scripts/01_profile.py
    python scripts/01_profile.py --raw-dir "02_Data/Raw" --out-dir reports
"""

from __future__ import annotations   # lets "str | None" hints work on Python 3.7–3.9

import argparse
import re
import sys
from pathlib import Path

import pandas as pd
from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday, USLaborDay,
                                    USMartinLutherKingJr, USMemorialDay, USPresidentsDay,
                                    USThanksgivingDay, nearest_workday, sunday_to_monday)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HW_DIR = Path(__file__).resolve().parent.parent          # .../hw04
DEFAULT_RAW = HW_DIR / "02_Data" / "Raw"
DEFAULT_OUT = HW_DIR / "reports"

# Strings that mean "no value" in at least some source systems.
NULL_TOKENS = {"", "none", "null", "nan", "n/a", "na", "-", "?"}

# ---------------------------------------------------------------------------
# Generic type parsers: value (str) -> True if it is valid for the type.
# Blank / null-token values are handled separately (completeness), so the
# parsers only see non-blank values.
# ---------------------------------------------------------------------------
TYPE_PATTERNS = {
    "int":        r"-?\d+",
    "float":      r"-?\d+(\.\d+)?([eE][-+]?\d+)?",   # scientific notation (1.9e-05) is a valid number
    "date":       r"\d{4}-\d{2}-\d{2}",
    "bool":       r"True|False",
    "flag01":     r"[01]",
    "zip":        r"\d{5}",
    "state_code": r"[A-Z]{2}",
    "text":       r".*",
}


def valid_for_type(s: pd.Series, typ: str) -> pd.Series:
    """Boolean Series: does each value parse as `typ`? (exact match, no coercion)"""
    ok = s.str.fullmatch(TYPE_PATTERNS[typ], na=False)
    if typ == "date":                      # right shape AND a real calendar date
        ok &= pd.to_datetime(s.where(ok), format="%Y-%m-%d", errors="coerce").notna()
    return ok


def infer_type(s: pd.Series) -> str:
    """Guess a column's type from its values (used when the config is silent)."""
    s = s[~is_blank(s)]
    if s.empty:
        return "text"
    for typ in ["flag01", "bool", "int", "float", "date"]:
        if valid_for_type(s, typ).mean() >= 0.9:
            return typ
    return "text"


def is_blank(s: pd.Series) -> pd.Series:
    return s.str.strip().str.lower().isin(NULL_TOKENS)


def to_num(s: pd.Series) -> pd.Series:
    """Strict numeric conversion: anything that is not a plain number -> NaN."""
    return pd.to_numeric(s.where(s.str.fullmatch(TYPE_PATTERNS["float"], na=False)), errors="coerce")


def to_num_lenient(s: pd.Series) -> pd.Series:
    """Lenient conversion used ONLY for profiling min/max: strips $ , % and spaces."""
    cleaned = s.str.replace(r"[\s$,%]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce")


def to_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, format="%Y-%m-%d", errors="coerce")


def int_text(s: pd.Series) -> pd.Series:
    """Number/bool Series -> integer text ('2020', not '2020.0'), safe when some values are missing."""
    return s.astype("Int64").astype(str)


class MarketHolidays(AbstractHolidayCalendar):
    """Approximate NYSE full-day holidays (special one-off closures not included)."""
    rules = [
        Holiday("New Year's Day", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
        Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
        Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
        USLaborDay, USThanksgivingDay,
        Holiday("Christmas", month=12, day=25, observance=nearest_workday),
    ]


def market_holidays(start, end) -> pd.DatetimeIndex:
    return MarketHolidays().holidays(start=start, end=end)


def shapes_of(s: pd.Series) -> pd.Series:
    """Value 'shape': upper->A, lower->a, digit->9, runs collapsed (vectorised).
    'PA'->'A', 'Pennsylvania'->'Aa', '45.0'->'9.9', '9.28%'->'9.9%', '-1.9e-05'->'-9.9a-9'."""
    return (s.str.replace(r"[A-Z]", "A", regex=True)
             .str.replace(r"[a-z]", "a", regex=True)
             .str.replace(r"\d", "9", regex=True)
             .str.replace(r"(.)\1+", r"\1", regex=True))


def format_of(s: pd.Series) -> pd.Series:
    """Shape used for the mixed-format check. Two things are NOT format differences:
    a leading minus (the sign is part of the value) and scientific notation
    ('-1.9e-05' is the same kind of number as '0.000019')."""
    f = shapes_of(s).str.replace(r"^-", "", regex=True)
    return f.str.replace(r"^9(\.9)?[aA][-+]?9$", "9.9", regex=True)


def count_by(s: pd.Series, fn) -> pd.Series:
    """Row counts per shape/format. Computed on DISTINCT values, then weighted —
    much faster than shaping 300k rows one by one."""
    vc = s.value_counts()
    return vc.groupby(fn(vc.index.to_series()).values).sum().sort_values(ascending=False)


# ---------------------------------------------------------------------------
# SCHEMA CONFIG — business knowledge about each table
#   file:        glob used to find the raw file (handles names like "dim_date (2).csv")
#   rows:        row count stated in the assignment briefing
#   pk:          primary key column
#   columns:     {col: {type, allowed, min, max, severity}}
#                severity of a range breach: ERROR = impossible, WARN = implausible
#   near_dup:    columns that should identify one real-world entity
#   unique:      other columns that should be unique (natural keys)
# ---------------------------------------------------------------------------
US_STATES = set(
    "AL AK AZ AR CA CO CT DE DC FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH "
    "NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY".split()
)

SCHEMA = {
    "dim_advisor": {
        "file": "dim_advisor*.csv", "rows": 25, "pk": "advisor_id",
        "near_dup": ["first_name", "last_name"],
        "columns": {
            "advisor_id": {"type": "int"},
            "first_name": {"type": "text"},
            "last_name": {"type": "text"},
            "region": {"type": "text", "allowed": {"Northeast", "Mid-Atlantic", "Southeast", "Midwest", "West", "Southwest"}},
            "years_experience": {"type": "int", "min": 0, "max": 50},
            "aum_target_mm": {"type": "int", "min": 1, "max": 1000},
            "certifications": {"type": "text", "allowed": {"CFA", "CFP", "CIMA", "CFP, CFA", "CFP, CIMA", "CFA, CIMA", "None"}},
        },
    },
    "dim_benchmark": {
        "file": "dim_benchmark*.csv", "rows": 8, "pk": "benchmark_id",
        "unique": ["name", "ticker_proxy"],
        "columns": {
            "benchmark_id": {"type": "int"},
            "name": {"type": "text"},
            "asset_class": {"type": "text"},
            "ticker_proxy": {"type": "text"},
        },
    },
    "dim_client": {
        "file": "dim_client*.csv", "rows": 2525, "pk": "client_id",
        # Same person = same first name, age, city, zip and starting AUM
        "near_dup": ["first_name", "age", "city", "zip_code", "initial_aum"],
        "columns": {
            "client_id": {"type": "int"},
            "first_name": {"type": "text"},
            "last_name": {"type": "text"},
            "age": {"type": "int", "min": 18, "max": 110},
            "city": {"type": "text"},
            "state": {"type": "state_code", "allowed": US_STATES},
            "zip_code": {"type": "zip"},
            "risk_profile": {"type": "text", "allowed": {"Conservative", "Moderately Conservative", "Balanced",
                                                         "Moderately Aggressive", "Aggressive"}},
            "client_tier": {"type": "text", "allowed": {"Retail", "HNW", "UHNW"}},
            "primary_account_type": {"type": "text", "allowed": {"Taxable", "IRA", "Roth IRA", "Trust", "529"}},
            "initial_aum": {"type": "float", "min": 0.01, "max": 1e9},
            "client_since": {"type": "date", "min": "1980-01-01", "max": "2024-12-31"},
            "advisor_id": {"type": "int"},
            "is_active": {"type": "bool"},
        },
    },
    "dim_date": {
        "file": "dim_date*.csv", "rows": 1827, "pk": "date_id",
        "unique": ["date"],
        "columns": {
            "date_id": {"type": "int"},
            "date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "year": {"type": "int", "min": 2020, "max": 2024},
            "quarter": {"type": "int", "min": 1, "max": 4},
            "month": {"type": "int", "min": 1, "max": 12},
            "month_name": {"type": "text", "allowed": {"January", "February", "March", "April", "May", "June", "July",
                                                       "August", "September", "October", "November", "December"}},
            "week_of_year": {"type": "int", "min": 1, "max": 53},
            "day_of_week": {"type": "text", "allowed": {"Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
                                                        "Saturday", "Sunday"}},
            "is_month_end": {"type": "flag01"},
            "is_quarter_end": {"type": "flag01"},
            "is_year_end": {"type": "flag01"},
            "is_trading_day": {"type": "flag01"},
        },
    },
    "dim_security": {
        "file": "dim_security*.csv", "rows": 500, "pk": "security_id",
        "unique": ["ticker"],
        "near_dup": ["name"],
        "columns": {
            "security_id": {"type": "int"},
            "ticker": {"type": "text"},
            "name": {"type": "text"},
            "asset_class": {"type": "text", "allowed": {"Equity", "Fixed Income", "Alternative", "Cash Equivalent"}},
            "sector": {"type": "text"},
            "benchmark_id": {"type": "int"},
            "is_etf": {"type": "bool"},
            "expense_ratio_bps": {"type": "float", "min": 0, "max": 300},
        },
    },
    "fact_fees": {
        "file": "fact_fees*.csv", "rows": 122197, "pk": "fee_id",
        "near_dup": ["client_id", "fee_date"],            # one fee row per client per month
        "columns": {
            "fee_id": {"type": "int"},
            "client_id": {"type": "int"},
            "advisor_id": {"type": "int"},
            "fee_date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "fee_type": {"type": "text", "allowed": {"Management", "Advisory", "Custodial", "Performance"}},
            "aum_basis": {"type": "float", "min": 0.01, "max": 1e9},
            "bps_charged": {"type": "float", "min": 0, "max": 100, "severity": "WARN"},
            "amount": {"type": "float", "min": 0.01, "max": 1e7},
        },
    },
    "fact_portfolio_snapshot": {
        "file": "fact_portfolio_snapshot*.csv", "rows": 129547, "pk": "snapshot_id",
        "near_dup": ["client_id", "snapshot_date"],       # one snapshot per client per month
        "columns": {
            "snapshot_id": {"type": "int"},
            "client_id": {"type": "int"},
            "advisor_id": {"type": "int"},
            "benchmark_id": {"type": "int"},
            "snapshot_date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "year": {"type": "int", "min": 2020, "max": 2024},
            "month": {"type": "int", "min": 1, "max": 12},
            "aum": {"type": "float", "min": 0.01, "max": 1e9},
            # returns are decimals (0.05 = 5%); -100% is the hard floor, >+100% YTD is implausible
            "return_ytd": {"type": "float", "min": -1, "max": 1, "severity": "WARN"},
            "benchmark_return_ytd": {"type": "float", "min": -1, "max": 1, "severity": "WARN"},
            "active_alpha_ytd": {"type": "float", "min": -2, "max": 2, "severity": "WARN"},
            "cash_pct": {"type": "float", "min": 0, "max": 1},
            "account_type": {"type": "text", "allowed": {"Taxable", "IRA", "Roth IRA", "Trust", "529"}},
        },
    },
    "fact_transactions": {
        "file": "fact_transactions*.csv", "rows": 298772, "pk": "txn_id",
        "columns": {
            "txn_id": {"type": "int"},
            "client_id": {"type": "int"},
            "advisor_id": {"type": "int"},
            "security_id": {"type": "int"},
            "txn_date": {"type": "date", "min": "2020-01-01", "max": "2024-12-31"},
            "txn_type": {"type": "text", "allowed": {"Buy", "Sell", "Dividend", "Deposit", "Withdrawal", "Advisory Fee"}},
            "shares": {"type": "float", "min": 0.0001, "max": 1e7},   # sign rule: direction comes from txn_type
            "price": {"type": "float", "min": 0.01, "max": 1e6},
            "amount": {"type": "float", "min": 0.01, "max": 1e8},
        },
    },
}

# Foreign key -> primary key relationships (10 ID-based + 3 to the date table)
RELATIONSHIPS = [
    ("dim_client", "advisor_id", "dim_advisor", "advisor_id"),
    ("dim_security", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_fees", "client_id", "dim_client", "client_id"),
    ("fact_fees", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "client_id", "dim_client", "client_id"),
    ("fact_portfolio_snapshot", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_portfolio_snapshot", "benchmark_id", "dim_benchmark", "benchmark_id"),
    ("fact_transactions", "client_id", "dim_client", "client_id"),
    ("fact_transactions", "advisor_id", "dim_advisor", "advisor_id"),
    ("fact_transactions", "security_id", "dim_security", "security_id"),
    ("fact_fees", "fee_date", "dim_date", "date"),
    ("fact_portfolio_snapshot", "snapshot_date", "dim_date", "date"),
    ("fact_transactions", "txn_date", "dim_date", "date"),
]

# Columns that are legitimately blank for some rows. The audit still reports them,
# but as INFO with the reason, so the cleaning step does not "fill" real structure.
CONDITIONAL_BLANKS = {
    ("fact_transactions", "security_id"): "blank expected for cash movements (Deposit/Withdrawal/Advisory Fee)",
    ("fact_transactions", "shares"): "blank expected for cash movements (Deposit/Withdrawal/Advisory Fee)",
    ("fact_transactions", "price"): "blank expected for cash movements (Deposit/Withdrawal/Advisory Fee)",
    ("dim_security", "sector"): "blank expected for ETFs (funds span sectors)",
    ("dim_security", "expense_ratio_bps"): "blank expected for single stocks (no expense ratio)",
    ("dim_advisor", "certifications"): "'None' is the text value for 'no certification', not a missing value",
}

# ---------------------------------------------------------------------------
# Findings collector
# ---------------------------------------------------------------------------
FINDINGS = []


def add(table, column, group, check, severity, rows, total, example="", detail="", issue_group=""):
    """Record one finding. Rows=0 findings are skipped unless severity is INFO.

    rows_affected is counted per finding. Several checks can look at the same bad rows
    (e.g. a spelled-out state fails the type check AND the allowed-list check), so
    findings that share an `issue_group` overlap — do not add their rows together.
    Default issue_group is table.column; related findings across columns override it."""
    if rows == 0 and severity != "INFO":
        return
    FINDINGS.append({
        "table": table, "column": column, "check_group": group, "check": check,
        "severity": severity, "rows_affected": int(rows),
        "pct_rows": round(100 * rows / total, 4) if total else 0.0,
        "example": str(example)[:200], "detail": detail,
        "issue_group": issue_group or f"{table}.{column}",
    })


def examples(s: pd.Series, n=3) -> str:
    return " | ".join(map(str, pd.Series(s).astype(str).drop_duplicates().head(n)))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_tables(raw_dir: Path) -> dict:
    tables = {}
    for name, cfg in SCHEMA.items():
        matches = sorted(raw_dir.glob(cfg["file"]))
        if not matches:
            sys.exit(f"Missing raw file for {name}: {raw_dir / cfg['file']}")
        if len(matches) > 1:     # never guess which export is the real one
            sys.exit(f"More than one file matches {cfg['file']}: {[m.name for m in matches]} — "
                     f"remove or rename the extras, or use --raw-dir")
        path = matches[0]
        df = pd.read_csv(path, dtype=str, keep_default_na=False)   # TEXT ONLY — see briefing rule
        tables[name] = df
        print(f"  loaded {name:<25} {len(df):>8,} rows x {df.shape[1]:>2} cols  ({path.name})")
        if path.stem != name:
            add(name, "", "0. File", "file name differs from table name", "INFO", 0, len(df),
                path.name, "raw export has a suffix; clean output should use the plain table name")
        if cfg.get("rows") and len(df) != cfg["rows"]:
            add(name, "", "0. File", "row count differs from briefing", "WARN", abs(len(df) - cfg["rows"]),
                len(df), f"{len(df)} vs {cfg['rows']}")
        extra = set(df.columns) - set(cfg["columns"])
        missing = set(cfg["columns"]) - set(df.columns)
        if extra:
            add(name, ",".join(sorted(extra)), "0. File", "columns not in schema", "WARN",
                len(df), len(df), f"extra={sorted(extra)}", "not audited by the rule checks")
        if missing:
            # Groups 2-4 depend on these columns, so stop with a clear message instead of a KeyError later
            sys.exit(f"{name} ({path.name}) is missing expected columns {sorted(missing)} — "
                     f"fix the file or update SCHEMA before auditing")
    return tables


# ---------------------------------------------------------------------------
# GENERIC PROFILER — works on any column of any table
# ---------------------------------------------------------------------------
def profile_column(table: str, col: str, s: pd.Series, expected_type: str | None = None) -> dict:
    n = len(s)
    blank = is_blank(s)
    nonblank = s[~blank]
    exp_type = expected_type or infer_type(s)

    shapes = count_by(nonblank, shapes_of)
    formats = len(count_by(nonblank, format_of))
    top_shapes = "; ".join(f"{k} ({v / max(len(nonblank), 1):.1%})" for k, v in shapes.head(3).items())

    type_fail = (~valid_for_type(nonblank, exp_type)).sum() if exp_type != "text" else 0
    lead_trail_ws = (s != s.str.strip()).sum()
    double_space = s.str.contains(r"\s{2,}", regex=True).sum()

    # Same value written with different case, e.g. "Equity" vs "equity".
    # Counts ROWS that are not the most common spelling of their value.
    # (Whitespace is reported separately, so it is not stripped here.)
    vc = nonblank.value_counts()
    by_lower = vc.groupby(vc.index.str.lower())
    case_variants = int((by_lower.sum() - by_lower.max())[by_lower.size() > 1].sum())

    nums = to_num_lenient(nonblank)
    numeric_share = nums.notna().mean() if len(nonblank) else 0

    null_tokens = s[blank & (s.str.strip() != "")]
    return {
        "table": table,
        "column": col,
        "rows": n,
        "expected_type": exp_type,
        "blank_count": int(blank.sum()),
        "blank_pct": round(100 * blank.mean(), 2),
        "null_token_values": examples(null_tokens) if len(null_tokens) else "",
        "distinct_count": int(nonblank.nunique()),
        "distinct_pct": round(100 * nonblank.nunique() / max(len(nonblank), 1), 2),
        "top_values": examples(nonblank.value_counts().index.to_series(), 5),
        "top_value_share_pct": round(100 * nonblank.value_counts(normalize=True).iloc[0], 2) if len(nonblank) else 0,
        "dominant_shapes": top_shapes,
        "shape_count": int(len(shapes)),
        "mixed_formats": bool(exp_type != "text" and formats > 1),
        "type_fail_count": int(type_fail),
        "type_fail_pct": round(100 * type_fail / max(len(nonblank), 1), 4),
        "type_fail_examples": examples(nonblank[~valid_for_type(nonblank, exp_type)]) if type_fail else "",
        "whitespace_lead_trail": int(lead_trail_ws),
        "whitespace_double": int(double_space),
        "case_variants": int(case_variants),
        "numeric_min": nums.min() if numeric_share >= 0.9 else "",
        "numeric_max": nums.max() if numeric_share >= 0.9 else "",
        "min_length": int(nonblank.str.len().min()) if len(nonblank) else 0,
        "max_length": int(nonblank.str.len().max()) if len(nonblank) else 0,
    }


def profile_all(tables: dict) -> pd.DataFrame:
    rows = []
    for t, df in tables.items():
        for c in df.columns:
            exp = SCHEMA.get(t, {}).get("columns", {}).get(c, {}).get("type")
            rows.append(profile_column(t, c, df[c], exp))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# GROUP 1 — Column level: completeness, type, allowed values, ranges, keys
# ---------------------------------------------------------------------------
def check_columns(tables: dict, profile: pd.DataFrame):
    G = "1. Column"
    for t, df in tables.items():
        cfg, n = SCHEMA[t], len(df)
        for col, rule in cfg["columns"].items():
            if col not in df:
                continue
            s = df[col]
            blank = is_blank(s)
            p = profile[(profile.table == t) & (profile.column == col)].iloc[0]

            # Completeness
            if blank.any():
                reason = CONDITIONAL_BLANKS.get((t, col))
                sev = "INFO" if reason else ("ERROR" if col == cfg["pk"] else "WARN")
                add(t, col, G, "blank / null-token values", sev, blank.sum(), n,
                    examples(s[blank].replace("", "<blank>")), reason or "missing value — decide fill vs leave vs flag")

            # Type validity (exact parse, no coercion)
            if p.type_fail_count:
                add(t, col, G, f"fails to parse as {rule['type']}", "ERROR", p.type_fail_count, n,
                    p.type_fail_examples, f"shapes seen: {p.dominant_shapes}")
            if p.mixed_formats:
                fmts = count_by(s[~blank], format_of)
                minority = int(fmts.sum() - fmts.iloc[0])   # rows not in the dominant shape
                add(t, col, G, "mixed formats in one column", "WARN", minority, n,
                    p.dominant_shapes, "more than one value shape for a non-text column")

            # Whitespace / case
            if p.whitespace_lead_trail:
                add(t, col, G, "leading/trailing whitespace", "WARN", p.whitespace_lead_trail, n,
                    examples(s[s != s.str.strip()].map(repr)), "breaks equality joins and group-bys")
            if p.whitespace_double:
                add(t, col, G, "double spaces inside value", "WARN", p.whitespace_double, n,
                    examples(s[s.str.contains(r"\s{2,}", regex=True)].map(repr)))
            if p.case_variants:
                add(t, col, G, "same value with different case", "WARN", p.case_variants, n, "",
                    "rows that are not the most common spelling of their value")

            # Allowed values
            if "allowed" in rule:
                bad = ~s.isin(rule["allowed"]) & ~blank
                add(t, col, G, "value not in allowed list", "ERROR", bad.sum(), n,
                    examples(s[bad].value_counts().index.to_series(), 6))

            # Ranges (only on values that parse; type failures were reported above)
            if "min" in rule or "max" in rule:
                sev = rule.get("severity", "ERROR")
                if rule["type"] == "date":
                    v = to_date(s)
                    lo, hi = pd.Timestamp(rule.get("min", "1900-01-01")), pd.Timestamp(rule.get("max", "2100-12-31"))
                else:
                    v = to_num(s)
                    lo, hi = rule.get("min", -float("inf")), rule.get("max", float("inf"))
                out = v.notna() & ((v < lo) | (v > hi))
                add(t, col, G, f"outside range [{rule.get('min')}, {rule.get('max')}]", sev, out.sum(), n,
                    examples(s[out]), f"observed min={v.min()} max={v.max()}")

            # Sentinel / placeholder values: one exact number repeated far too often
            # in a continuous column (e.g. 1000.0 used as a default)
            if rule["type"] == "float" and p.distinct_pct > 50:
                vc = s[~blank].value_counts()
                spikes = vc[(vc >= 50) & (vc / n >= 0.002)]   # >=50 rows AND >=0.2% of the table
                for val, cnt in spikes.items():
                    add(t, col, G, "suspicious repeated value (possible placeholder)", "WARN", cnt, n, val,
                        f"value appears {cnt}x in a column with {p.distinct_count:,} distinct values")

        # Primary key: unique and not blank
        pk = cfg["pk"]
        # Duplicate counts below = EXTRA records (a pair counts as 1); rows involved are in `detail`
        dup = df[pk].duplicated(keep=False)
        add(t, pk, G, "primary key duplicated", "ERROR", df[pk].duplicated().sum(), n,
            examples(df.loc[dup, pk]), f"{dup.sum()} rows involved")
        add(t, pk, G, "primary key unique", "INFO", 0, n, f"{df[pk].nunique():,} distinct of {n:,}",
            "PASS" if not dup.any() else "FAIL")
        for uc in cfg.get("unique", []):
            nb = ~is_blank(df[uc])
            d = df[uc].duplicated(keep=False) & nb
            add(t, uc, G, "natural key duplicated", "ERROR", (df[uc].duplicated() & nb).sum(), n,
                examples(df.loc[d, uc]), f"{d.sum()} rows involved")


# ---------------------------------------------------------------------------
# GROUP 2 — Single-table rules: duplicates, near-duplicates, row contradictions
# ---------------------------------------------------------------------------
def check_single_table(tables: dict):
    G = "2. Single-table"
    for t, df in tables.items():
        cfg, n = SCHEMA[t], len(df)
        pk = cfg["pk"]

        # Exact duplicate rows ignoring the surrogate key
        d = df.drop(columns=pk).duplicated(keep=False)
        add(t, "(all but PK)", G, "exact duplicate rows (ignoring PK)", "ERROR", df.drop(columns=pk).duplicated().sum(),
            n, examples(df.loc[d, pk]), f"extra records; {d.sum()} rows involved")

        # Near-duplicates: normalise text (case, spaces) and compare business key
        if cfg.get("near_dup"):
            key = df[cfg["near_dup"]].apply(lambda c: c.str.strip().str.lower())
            nd = key.duplicated(keep=False)
            add(t, "+".join(cfg["near_dup"]), G, "near-duplicate rows (same business key)",
                "WARN" if t.startswith("dim") else "ERROR", key.duplicated().sum(), n, examples(df.loc[nd, pk], 6),
                f"extra records; {nd.sum()} rows involved — same real-world entity/event under more than one ID",
                issue_group=f"{t}.near_duplicates")

    # --- row-level contradictions (columns of the same row disagree) ---
    c = tables["dim_client"]
    aum, n = to_num(c.initial_aum), len(c)
    # ASSUMPTION: tier cut-offs are not given in the briefing; they are the standard industry
    # bands (Retail < $500k, HNW < $5M, UHNW >= $5M). The data agrees: every readable row fits.
    tier_from_aum = pd.cut(aum, [0, 500_000, 5_000_000, float("inf")], labels=["Retail", "HNW", "UHNW"], right=False)
    bad = aum.notna() & (tier_from_aum.astype(str) != c.client_tier)      # unreadable AUM is a type issue, not a contradiction
    add("dim_client", "client_tier/initial_aum", G, "tier contradicts initial AUM (<500k Retail, <5M HNW, else UHNW)",
        "WARN", bad.sum(), n, examples(c.loc[bad, "client_id"]))

    # Near-duplicate clients: is one name a truncated copy of the other?
    key = c[SCHEMA["dim_client"]["near_dup"]].apply(lambda col: col.str.strip().str.lower()).agg("|".join, axis=1)
    cc = c.assign(_k=key, _ln=c.last_name.str.strip().str.lower())
    grp = cc[key.duplicated(keep=False)].groupby("_k")

    def has_truncated(names):
        names = [x for x in names if x]                    # a blank name would "prefix-match" everything
        return any(a != b and b.startswith(a) for a in names for b in names)

    trunc = grp._ln.apply(has_truncated)
    if len(trunc):
        add("dim_client", "last_name", G, "near-duplicate groups where one last_name is a truncated copy", "WARN",
            int(trunc.sum()), n, examples(grp.client_id.apply(lambda x: "/".join(x))[trunc]),
            f"counted in groups (= extra records for pairs): {int(trunc.sum())} of {len(trunc)} groups",
            issue_group="dim_client.near_duplicates")

    d = tables["dim_date"]
    dt = to_date(d.date)
    ok = dt.notna()                      # rows with an unreadable date are reported by the type check, not here
    checks = {
        "year": int_text(dt.dt.year) != d.year,
        "quarter": int_text(dt.dt.quarter) != d.quarter,
        "month": int_text(dt.dt.month) != d.month,
        "month_name": dt.dt.month_name() != d.month_name,
        "day_of_week": dt.dt.day_name() != d.day_of_week,
        "week_of_year": int_text(dt.dt.isocalendar().week) != d.week_of_year,
        "is_month_end": int_text(dt.dt.is_month_end) != d.is_month_end,
        "is_quarter_end": int_text(dt.dt.is_quarter_end) != d.is_quarter_end,
        "is_year_end": int_text(dt.dt.is_year_end) != d.is_year_end,
        "is_trading_day(weekend)": (dt.dt.day_of_week >= 5) & (d.is_trading_day == "1"),
    }
    for col, bad in checks.items():
        bad = ok & bad
        add("dim_date", col, G, "derived calendar field disagrees with date", "ERROR", bad.sum(), len(d),
            examples(d.loc[bad, "date"]))

    # Trading-day flag, both directions: market holidays (NYSE rules, approximated) vs weekdays
    hol = market_holidays(dt.min(), dt.max())
    is_hol = dt.isin(hol)
    weekday = ok & (dt.dt.day_of_week < 5)
    bad = is_hol & (d.is_trading_day == "1")
    add("dim_date", "is_trading_day", G, "market holiday marked as a trading day", "WARN", bad.sum(), len(d),
        examples(d.loc[bad, "date"], 5), "approximate NYSE calendar (New Year, MLK, Presidents, Good Friday, Memorial, "
        "Juneteenth from 2022, July 4, Labor, Thanksgiving, Christmas); special closures not included")
    bad = weekday & ~is_hol & (d.is_trading_day == "0")
    add("dim_date", "is_trading_day", G, "ordinary weekday marked as non-trading", "WARN", bad.sum(), len(d),
        examples(d.loc[bad, "date"]))

    # Gaps measured against the schema's expected range, not just min..max found in the file
    rule = SCHEMA["dim_date"]["columns"]["date"]
    full = pd.date_range(rule["min"], rule["max"])
    missing_days = full.difference(dt.dropna())
    add("dim_date", "date", G, f"calendar gaps vs expected {rule['min']}..{rule['max']}", "ERROR", len(missing_days),
        len(full), examples(pd.Series(missing_days.strftime("%Y-%m-%d"))))

    s = tables["dim_security"]
    etf = s.is_etf == "True"
    has_er = ~is_blank(s.expense_ratio_bps)
    has_sector = ~is_blank(s.sector)
    add("dim_security", "is_etf/expense_ratio_bps", G, "ETF without expense ratio, or stock with one", "ERROR",
        (etf != has_er).sum(), len(s), examples(s.loc[etf != has_er, "security_id"]))
    add("dim_security", "is_etf/sector", G, "stock without sector, or ETF with one", "WARN",
        (etf == has_sector).sum(), len(s), examples(s.loc[etf == has_sector, "security_id"]))

    f = tables["fact_fees"]
    # ASSUMPTION: bps_charged is an ANNUAL rate billed monthly (hence / 12). Not stated in the
    # briefing — the data confirms it (the INFO line below shows how many rows reconcile).
    calc = to_num(f.aum_basis) * to_num(f.bps_charged) / 10_000 / 12
    amt = to_num(f.amount)
    computable = calc.notna() & amt.notna()
    bad = computable & ((calc - amt).abs() > 0.05)
    add("fact_fees", "amount", G, "amount != aum_basis x bps / 10,000 / 12 (tol $0.05)", "ERROR", bad.sum(), len(f),
        examples(f.loc[bad, "fee_id"]))
    add("fact_fees", "amount", G, "amount recomputes from aum_basis x bps / 12", "INFO", 0, len(f),
        f"{(computable & ~bad).sum():,} of {len(f):,} rows reconcile; {(~computable).sum():,} not computable",
        "fee formula confirmed — usable to verify repairs")

    p = tables["fact_portfolio_snapshot"]
    r, b, a = to_num(p.return_ytd), to_num(p.benchmark_return_ytd), to_num(p.active_alpha_ytd)
    bad = (r - b - a).abs() > 1e-4
    add("fact_portfolio_snapshot", "active_alpha_ytd", G, "alpha != return_ytd - benchmark_return_ytd", "ERROR",
        bad.sum(), len(p), examples(p.loc[bad, "snapshot_id"]))
    # return_ytd that failed to parse: can it be recovered from benchmark + alpha?
    pct = p.return_ytd.str.endswith("%")
    if pct.any():
        recovered = to_num(p.return_ytd.str.rstrip("%")) / 100
        match = ((recovered - (b + a)).abs() < 1e-4) & pct
        add("fact_portfolio_snapshot", "return_ytd", G, "percent-string returns ('9.28%') reconcile to benchmark + alpha",
            "INFO", match.sum(), len(p), examples(p.loc[pct, "return_ytd"]),
            f"{match.sum()} of {pct.sum()} recover exactly when divided by 100")
    sd = to_date(p.snapshot_date)
    bad = sd.notna() & ((int_text(sd.dt.year) != p.year) | (int_text(sd.dt.month) != p.month))
    add("fact_portfolio_snapshot", "year/month", G, "year/month disagree with snapshot_date", "ERROR", bad.sum(), len(p),
        examples(p.loc[bad, "snapshot_id"]))
    bad = sd.notna() & (sd.dt.day != 1)
    add("fact_portfolio_snapshot", "snapshot_date", G, "snapshot not on 1st of month", "WARN", bad.sum(), len(p))

    x = tables["fact_transactions"]
    cash_types = {"Deposit", "Withdrawal", "Advisory Fee"}
    is_cash = x.txn_type.isin(cash_types)
    sec_blank = is_blank(x.security_id)
    bad = is_cash != sec_blank
    add("fact_transactions", "security_id/txn_type", G, "security present on cash txn, or missing on trade/dividend",
        "ERROR", bad.sum(), len(x), examples(x.loc[bad, "txn_id"]))
    sh, pr, am = to_num(x.shares), to_num(x.price), to_num(x.amount)
    neg = sh < 0
    add("fact_transactions", "shares", G, "negative shares (sign rule: direction comes from txn_type)", "ERROR",
        neg.sum(), len(x), examples(x.loc[neg, "txn_id"]),
        "by type: " + str(x.loc[neg, "txn_type"].value_counts().to_dict()))
    trade = ~is_cash
    diff = ((sh * pr).abs() - am).abs()
    bad = trade & (diff > 1.0)
    add("fact_transactions", "amount", G, "amount != |shares x price| (tol $1)", "ERROR", bad.sum(), len(x),
        examples(x.loc[bad, "txn_id"]))
    ok_abs = trade & neg & (diff <= 1.0)
    add("fact_transactions", "shares", G, "negative-share rows reconcile to amount once sign is dropped", "INFO",
        ok_abs.sum(), len(x), "", "evidence that the sign is the error, not the magnitude")
    float_ids = x.security_id.str.fullmatch(r"\d+\.0", na=False)
    add("fact_transactions", "security_id", G, "integer ID stored as float text ('45.0')", "ERROR", float_ids.sum(),
        len(x), examples(x.loc[float_ids, "security_id"]), "will not join to dim_security.security_id ('45')")


# ---------------------------------------------------------------------------
# GROUP 3 — Referential integrity
# ---------------------------------------------------------------------------
def ri_check(fact_df, fact_key, dim_df, dim_key, normalise=False):
    """Return match stats for one FK -> PK relationship (blank FKs excluded from match rate)."""
    fk = fact_df[fact_key]
    pkset = set(dim_df[dim_key])
    if normalise:                                   # e.g. '45.0' -> '45'
        fk = fk.str.replace(r"\.0$", "", regex=True)
    blank = is_blank(fk)
    orphan = ~blank & ~fk.isin(pkset)
    nonblank = (~blank).sum()
    return {
        "rows": len(fk), "null_keys": int(blank.sum()), "orphan_rows": int(orphan.sum()),
        "distinct_orphans": int(fk[orphan].nunique()),
        "match_rate": round(100 * (nonblank - orphan.sum()) / nonblank, 4) if nonblank else 100.0,
        "orphan_examples": examples(fk[orphan], 5),
    }


def check_referential(tables: dict):
    G = "3. Referential"
    for ft, fk, dt_, pk in RELATIONSHIPS:
        r = ri_check(tables[ft], fk, tables[dt_], pk)
        rel = f"{ft}.{fk} -> {dt_}.{pk}"
        add(ft, fk, G, f"RI {rel}", "ERROR" if r["orphan_rows"] else "INFO", r["orphan_rows"], r["rows"],
            r["orphan_examples"],
            f"match={r['match_rate']}% orphans={r['orphan_rows']} distinct_orphans={r['distinct_orphans']} null_keys={r['null_keys']}")
        if r["orphan_rows"]:
            r2 = ri_check(tables[ft], fk, tables[dt_], pk, normalise=True)
            if r2["orphan_rows"] < r["orphan_rows"]:
                add(ft, fk, G, f"RI {rel} after stripping '.0'", "INFO", r2["orphan_rows"], r2["rows"],
                    r2["orphan_examples"], f"match={r2['match_rate']}% — orphans are a format problem, not missing keys")

    # Reverse direction: dimension rows never used by any fact (not an error, but worth knowing)
    used = set().union(*[set(tables[f].client_id) for f in ["fact_fees", "fact_portfolio_snapshot", "fact_transactions"]])
    c = tables["dim_client"]
    unused = ~c.client_id.isin(used)
    add("dim_client", "client_id", G, "clients with no facts in any fact table", "WARN", unused.sum(), len(c),
        examples(c.loc[unused, "client_id"], 6), "check against near-duplicate finding",
        issue_group="dim_client.near_duplicates")
    s = tables["dim_security"]
    sec_used = set(tables["fact_transactions"].security_id.str.replace(r"\.0$", "", regex=True))
    add("dim_security", "security_id", G, "securities never traded", "INFO", (~s.security_id.isin(sec_used)).sum(),
        len(s), examples(s.loc[~s.security_id.isin(sec_used), "security_id"]))


# ---------------------------------------------------------------------------
# GROUP 4 — Cross-table business rules
# ---------------------------------------------------------------------------
def check_cross_table(tables: dict):
    G = "4. Cross-table"
    c = tables["dim_client"]
    cli = c.set_index("client_id")

    # Fact advisor must equal the client's advisor in dim_client
    for ft in ["fact_fees", "fact_portfolio_snapshot", "fact_transactions"]:
        f = tables[ft]
        dim_adv = f.client_id.map(cli.advisor_id)
        bad = dim_adv.notna() & (dim_adv != f.advisor_id)
        add(ft, "advisor_id", G, "advisor differs from dim_client.advisor_id", "WARN", bad.sum(), len(f),
            examples(f.loc[bad, SCHEMA[ft]["pk"]]))

    p = tables["fact_portfolio_snapshot"]
    n = len(p)
    dim_acct = p.client_id.map(cli.primary_account_type)
    bad = dim_acct.notna() & (dim_acct != p.account_type)      # orphans are an RI issue, not a mismatch
    add("fact_portfolio_snapshot", "account_type", G, "account_type differs from dim_client.primary_account_type",
        "WARN", bad.sum(), n, examples(p.loc[bad, "snapshot_id"]))

    # Benchmark should follow the client's risk profile (mapping observed in the data)
    risk = p.client_id.map(cli.risk_profile)
    blank_risk = risk.notna() & is_blank(risk.fillna("x"))
    xt = pd.crosstab(risk.where(~blank_risk, "<blank>"), p.benchmark_id)
    mapping = xt.drop(index="<blank>", errors="ignore").idxmax(axis=1).to_dict()
    expected = risk.map(mapping)
    bad = expected.notna() & (expected != p.benchmark_id)
    add("fact_portfolio_snapshot", "benchmark_id", G, "benchmark inconsistent with client risk_profile", "WARN",
        bad.sum(), n, examples(p.loc[bad, "snapshot_id"]), f"observed mapping risk->benchmark: {mapping}")
    if blank_risk.any():
        add("dim_client", "risk_profile", G, "blank risk_profile: benchmark used in snapshots", "INFO",
            p.loc[blank_risk, "client_id"].nunique(), len(c),
            str(p.loc[blank_risk, "benchmark_id"].value_counts().to_dict()),
            "the benchmark these clients were measured against hints at their real profile — verify before filling")

    # Snapshot AUM must equal the fee aum_basis for the same client-month
    f = tables["fact_fees"]
    # The join assumes ONE row per client-month on each side. Blank keys are left out, and
    # duplicate keys are reported, because they would turn mismatch counts into row-pair counts.
    pk_cols, fk_cols = ["client_id", "snapshot_date"], ["client_id", "fee_date"]
    p_ok = p[~is_blank(p.client_id) & ~is_blank(p.snapshot_date)]
    f_ok = f[~is_blank(f.client_id) & ~is_blank(f.fee_date)]
    for tbl, df_, cols in [("fact_portfolio_snapshot", p_ok, pk_cols), ("fact_fees", f_ok, fk_cols)]:
        dups = df_.duplicated(cols).sum()
        add(tbl, "+".join(cols), G, "client-month key not unique (snapshot<->fee join would multiply rows)", "ERROR",
            dups, len(df_), "", "AUM reconciliation counts below are row-pairs until this is fixed")
    j = p_ok.merge(f_ok, left_on=pk_cols, right_on=fk_cols, how="outer", indicator=True)
    both = j._merge == "both"
    mism = both & ((to_num(j.aum) - to_num(j.aum_basis)).abs() > 0.01)
    add("fact_fees", "aum_basis", G, "fee aum_basis != snapshot aum for same client-month", "ERROR", mism.sum(), len(f),
        examples(j.loc[mism, "fee_id"]))
    add("fact_portfolio_snapshot", "snapshot_id", G, "snapshot client-months with no fee row", "WARN",
        (j._merge == "left_only").sum(), n, examples(j.loc[j._merge == "left_only", "snapshot_id"]),
        "un-billed months? check if they cluster by date/client")
    add("fact_fees", "fee_id", G, "fee rows with no matching snapshot", "ERROR", (j._merge == "right_only").sum(),
        len(f), examples(j.loc[j._merge == "right_only", "fee_id"]))

    # Placeholder AUM shows up in BOTH tables -> same upstream default, not a coincidence
    # Compared as NUMBERS (so 1000, 1000.0 and 1000.00 all match), using the spike rule from Group 1
    aum_num, basis_num = to_num(p.aum), to_num(f.aum_basis)
    vc = aum_num.value_counts()
    for val, cnt in vc[(vc >= 50) & (vc / n >= 0.002)].items():
        in_fees = int((basis_num == val).sum())
        if in_fees:
            add("fact_portfolio_snapshot", "aum", G, f"repeated AUM {val:,.2f} also appears in fact_fees.aum_basis",
                "WARN", cnt, n, val, f"snapshots={cnt}, fees={in_fees}; same upstream default in both tables — "
                "returns and fees on these rows are distorted")

    # Implausible returns: >100% or near -100% YTD for a wealth-management account
    r = to_num(p.return_ytd)
    add("fact_portfolio_snapshot", "return_ytd", G, "YTD return < -90% (near total loss)", "WARN", (r < -0.9).sum(), n,
        examples(p.loc[r < -0.9, "snapshot_id"]))

    # Dates vs client relationship start
    since = to_date(p.client_id.map(cli.client_since))
    sd = to_date(p.snapshot_date)
    early_same_month = (sd < since) & (sd.dt.to_period("M") == since.dt.to_period("M"))
    early_prior = (sd < since) & ~early_same_month
    add("fact_portfolio_snapshot", "snapshot_date", G, "snapshot in a month BEFORE client_since", "ERROR",
        early_prior.sum(), n, examples(p.loc[early_prior, "snapshot_id"]))
    add("fact_portfolio_snapshot", "snapshot_date", G, "first-of-month snapshot in the client's joining month",
        "INFO", early_same_month.sum(), n, examples(p.loc[early_same_month, "snapshot_id"]),
        "snapshot dated the 1st of the month the client joined — likely legitimate month-level grain")
    for ft, dcol in [("fact_fees", "fee_date"), ("fact_transactions", "txn_date")]:
        ff = tables[ft]
        since = to_date(ff.client_id.map(cli.client_since))
        dd = to_date(ff[dcol])
        bad = since.notna() & (dd.dt.to_period("M") < since.dt.to_period("M"))
        add(ft, dcol, G, "activity in a month before client_since", "ERROR", bad.sum(), len(ff),
            examples(ff.loc[bad, SCHEMA[ft]["pk"]]))

    # Client relationships that started before the date dimension begins
    cs = to_date(c.client_since)
    dmin = to_date(tables["dim_date"].date).min()
    add("dim_client", "client_since", G, "client_since earlier than dim_date coverage", "INFO", (cs < dmin).sum(),
        len(c), "", "client_since is an attribute, not a date-table FK — note for Power BI")

    # Trades on non-trading days
    x = tables["fact_transactions"]
    trading = x.txn_date.map(tables["dim_date"].set_index("date").is_trading_day)
    for types, sev in [({"Buy", "Sell"}, "WARN"), ({"Dividend", "Deposit", "Withdrawal", "Advisory Fee"}, "INFO")]:
        m = x.txn_type.isin(types) & (trading == "0")
        add("fact_transactions", "txn_date", G, f"{'/'.join(sorted(types))} on a non-trading day", sev, m.sum(), len(x),
            examples(x.loc[m, "txn_id"]))

    # Buy/Sell on market holidays that dim_date wrongly calls trading days
    d = tables["dim_date"]
    dd = to_date(d.date)
    hol = set(d.loc[dd.isin(market_holidays(dd.min(), dd.max())), "date"])
    m = x.txn_type.isin({"Buy", "Sell"}) & x.txn_date.isin(hol) & (trading == "1")
    add("fact_transactions", "txn_date", G, "Buy/Sell on a market holiday (dim_date says trading day)", "WARN",
        m.sum(), len(x), examples(x.loc[m, "txn_date"]))

    # Orphan client IDs in transactions: inside or outside the dim_client ID range? (computed, not assumed)
    known = set(c.client_id)
    orphan_ids = to_num(x.loc[~x.client_id.isin(known) & ~is_blank(x.client_id), "client_id"])
    if len(orphan_ids):
        lo, hi = to_num(c.client_id).min(), to_num(c.client_id).max()
        outside = ((orphan_ids < lo) | (orphan_ids > hi)).sum()
        add("fact_transactions", "client_id", G, "where orphan client_ids fall vs the dim_client ID range", "INFO",
            len(orphan_ids), len(x), f"orphans {orphan_ids.min():.0f}–{orphan_ids.max():.0f}",
            f"dim_client IDs run {lo:.0f}–{hi:.0f}; {outside} of {len(orphan_ids)} orphan rows fall outside that range")

    # Inactive clients still generating facts in the final month
    sd = to_date(p.snapshot_date)
    last = sd.max()
    inactive = set(c.loc[c.is_active == "False", "client_id"])
    m = (sd == last) & p.client_id.isin(inactive)
    last = last.strftime("%Y-%m-%d")
    add("fact_portfolio_snapshot", "client_id", G, f"inactive clients with a snapshot in the last month ({last})",
        "WARN", m.sum(), n, examples(p.loc[m, "client_id"]))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Audit raw Wildcat Capital tables")
    ap.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    print(f"Reading raw tables from {args.raw_dir}")
    tables = load_tables(args.raw_dir)

    print("Profiling columns ...")
    profile = profile_all(tables)

    print("Running checks ...")
    check_columns(tables, profile)
    check_single_table(tables)
    check_referential(tables)
    check_cross_table(tables)

    dq = pd.DataFrame(FINDINGS)
    sev_order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    dq = dq.sort_values(["severity", "check_group", "table", "column"], key=lambda s: s.map(sev_order) if s.name == "severity" else s)
    dq.insert(0, "finding_id", range(1, len(dq) + 1))

    args.out_dir.mkdir(parents=True, exist_ok=True)
    profile.to_csv(args.out_dir / "profile_raw.csv", index=False)
    dq.to_csv(args.out_dir / "dq_summary_raw.csv", index=False)

    # Console summary
    print("\n=== Findings by severity and group ===")
    print(pd.crosstab(dq.check_group, dq.severity).reindex(columns=["ERROR", "WARN", "INFO"], fill_value=0))
    print(f"\n{len(dq)} findings in {dq.issue_group.nunique()} issue groups. rows_affected is per finding;"
          f" findings in the same issue_group overlap, so do not add them up.")
    print("\n=== ERROR and WARN findings ===")
    with pd.option_context("display.max_rows", 200, "display.width", 200, "display.max_colwidth", 70):
        print(dq[dq.severity != "INFO"][["severity", "issue_group", "check", "rows_affected"]].to_string(index=False))
    print(f"\nSaved {args.out_dir / 'profile_raw.csv'} ({len(profile)} rows)")
    print(f"Saved {args.out_dir / 'dq_summary_raw.csv'} ({len(dq)} findings)")


if __name__ == "__main__":
    main()
