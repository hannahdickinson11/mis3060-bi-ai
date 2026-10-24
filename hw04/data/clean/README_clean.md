# Wildcat Capital — clean tables (HW4)

Produced by `scripts/02_clean.py` from the raw files in `02_Data/Raw` (never modified).
Every change is in `data/audit/value_changes.csv` (198,303 cell changes on kept rows); every step is in
`data/audit/cleaning_log.csv`; removed rows are in `data/audit/quarantine_*.csv` with their **original raw values**.
Decision IDs (D01–D21) refer to `decision_log.md`.

## Tables

| File | Rows |
|---|---:|
| `dim_advisor.csv` | 25 |
| `dim_benchmark.csv` | 8 |
| `dim_client.csv` | 2,500 |
| `dim_date.csv` | 1,827 |
| `dim_security.csv` | 500 |
| `fact_fees.csv` | 122,197 |
| `fact_portfolio_snapshot.csv` | 129,547 |
| `fact_transactions.csv` | 298,572 |

## Relationships (all 13 matched 100% in the clean data)

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

`dim_client.client_since` is **not** a date key: 1,532 clients joined before 2020, outside `dim_date` (D05).
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
| `dim_client.flag_risk_profile_missing` | 75 | risk profile blank; not filled (D04) |
| `fact_fees.flag_aum_placeholder` | 386 | AUM / AUM basis is the 1,000 placeholder; real value unknown (D17) |
| `fact_portfolio_snapshot.flag_aum_placeholder` | 420 | AUM / AUM basis is the 1,000 placeholder; real value unknown (D17) |
| `fact_portfolio_snapshot.flag_return_implausible` | 1,475 | YTD return > +100% or < -90% (D18) |
| `fact_transactions.flag_non_trading_day` | 44,241 | Buy/Sell dated on a weekend or NYSE holiday; date not moved (D14) |

## Known limitations (not fixed, on purpose)

- **Blank risk profiles (75 clients).** Not filled: a risk profile is a compliance record. Their snapshots all use the 60/40 benchmark that only Balanced clients use, so re-profiling is recommended (D04).
- **Trade dates on weekends/holidays (44,241 Buy/Sell rows).** No evidence of the correct date, so dates were not moved; day-level trading analysis is unreliable, month-level is fine (D14).
- **AUM placeholder (420 snapshots, 386 fees).** Real AUM unknown; not interpolated. Exclude flagged rows from AUM totals and fee-rate measures (D17).
- **Implausible returns (1,475 snapshots).** Values kept (they reconcile with benchmark + alpha); many come from the placeholder AUM base. Use medians or exclude flagged rows (D18).
- **Snapshot months with no fee (7,350).** Fees are not invented; fee-to-AUM ratios are understated in those months (D20).
- **Cash movements have no security (101,528 rows).** Legitimate; the `security_id` relationship must allow blanks (D11).
- **Fees above 100 bps: 100.38 bps (fee_id 68809).** Left as is: within the client's history and the amount reconciles (D19).
- **Trading calendar.** `is_trading_day` now excludes NYSE full-day holidays; special one-off closures are not modelled (D09).
