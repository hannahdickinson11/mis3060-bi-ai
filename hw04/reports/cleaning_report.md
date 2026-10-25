# Wildcat Capital — Data Cleaning Report
**To:** Portfolio Committee · **From:** MIS3060 HW4 · **Scope:** 8-table warehouse extract, 2020–2024

## Executive summary
The extract (555,401 rows across 5 dimension and 3 fact tables) was **not usable as delivered**: two-thirds of transaction rows could not be linked to a security or client, and several fields mixed formats. After cleaning, **all 13 table relationships match 100%**, every recomputed amount agrees with the stored amount, and no value was invented. 225 rows (0.04%) were moved to quarantine files rather than deleted, and every one of the 198,303 changed cells on kept rows is logged.

Four issues could not be fixed without guessing and are **flagged instead**: a $1,000 placeholder AUM on 420 snapshots, 1,475 implausible year-to-date returns, 44,241 trades dated on non-trading days, and 75 clients with no risk profile. Reports built on this data should filter on the four 0/1 flag columns added to the clean tables: `flag_aum_placeholder` (snapshots and fees), `flag_return_implausible`, `flag_non_trading_day` and `flag_risk_profile_missing`.

## What was wrong and what we did
From `data/audit/cleaning_log.csv` (decision IDs refer to `decision_log.md`):

| Issue | Rows | Action |
|---|---:|---|
| Transaction `security_id` stored as `45.0`, so no trade joined to a security (D10) | 197,175 | Standardized to `45` |
| Negative share counts on Buy trades; amount confirmed the size, only the sign was wrong (D12) | 835 | Sign removed |
| Returns stored as text like `9.28%` (D15) | 300 | Converted to decimals; all 300 match benchmark + alpha |
| State written in full (`Pennsylvania`) instead of `PA` (D02) | 78 | Standardized |
| 47 market holidays marked as trading days (D09) | 47 | Corrected against the NYSE calendar |
| Duplicate clients with shortened or mistyped last names, no activity (D03) | 25 | Quarantined |
| Transactions for client IDs that don't exist ($10,888,495.37) (D13) | 200 | Quarantined |
| Trades on weekends/holidays (D14) · placeholder AUM (D17) · implausible returns (D18) · blank risk profile (D04) | 44,241 · 420 snapshots + 386 fees · 1,475 · 75 | Flagged (0/1 column), values unchanged |
| Legitimate blanks and formats: no security on cash movements, no sector on ETFs, "None" certifications, etc. (D05–D08, D11, D16, D19–D21) | — | Left as is, documented |

Row counts above are rows cleaned. `value_changes.csv` lists 197,044 and 77 for the first and fourth lines because it records kept rows only; the other 131 + 1 were on rows that were then quarantined, and the quarantine files keep their original values.

## Data quality before and after
From `reports/data_quality_scorecard.csv` (definitions in `data_quality_scorecard_notes.md`):

| Table | Metric | Raw | Clean |
|---|---|---:|---:|
| fact_transactions | Rows whose keys all link | 33.98% | 100.00% |
| fact_transactions | Valid data types | 90.54% | 100.00% |
| dim_client | Rows with a unique key | 98.02% | 100.00% |
| dim_client | Rows passing every rule | 96.91% | 100.00% |
| dim_date | Rows passing every rule | 97.43% | 100.00% |
| fact_portfolio_snapshot | Valid data types | 99.98% | 100.00% |

Clean `fact_transactions` (85.18%), `fact_portfolio_snapshot` (98.73%) and `fact_fees` (99.68%) still score below 100% on rules **by design**: those are the flagged rows, and the validation script confirms every remaining failure carries a flag. Clean `dim_client` completeness is 99.79% because the 75 blank risk profiles were not filled.

## Key judgment calls

**1. Blank risk profiles were flagged, not filled (D04).** All 75 clients' snapshots are measured against the 60/40 benchmark, which in the rest of the data is used only by Balanced clients, so "Balanced" is a strong guess. But a risk profile is normally a suitability assessment collected from the client; writing one in would create a compliance record that was never collected. *Risk:* risk-profile breakdowns show a small blank group. *Recommendation:* re-profile these 75 clients.

**2. The $1,000 AUM placeholder was flagged, not estimated (D17).** The value appears in 420 snapshots (92 clients) and the matching 386 fee rows; no other AUM value appears more than twice. It shows up in 206 separate runs, every one starting after a normal balance; 198 return to a normal balance (e.g. $33,871 → $1,000 for four months → $33,979) and 8 run to the end of the data. Filling from neighbouring months would invent balances, and fees were recorded on the placeholder — those 386 fees total only $282.85. *Risk:* AUM totals and fee revenue are understated for those months unless flagged rows are excluded.

**3. Unmatched transactions were quarantined, not kept or deleted (D13).** 200 transactions point to 200 client IDs that do not exist. Keeping them would add a "(blank)" client to every client report; deleting them would lose $10.9M of activity. Quarantine keeps the rows intact for follow-up. *Risk:* if the client list was simply incomplete, real activity is missing from client-level reporting until the source system supplies those clients.

**4. Weekend and holiday trade dates were flagged, not moved (D14).** 28.4% of Buy/Sell rows fall on weekends — almost exactly 2 days in 7 — so the dates look spread over the whole week by the source system, not mistyped one by one. There is no evidence of the true date, so none was invented. *Risk:* daily and day-of-week trading analysis is unreliable; monthly figures are unaffected.

## Limitations
- **Implausible returns (1,475 snapshots)** were kept because they reconcile exactly with benchmark + alpha; 981 of them (66.5%) belong to the 92 clients with the $1,000 placeholder AUM. Use medians or exclude flagged rows.
- **7,350 snapshot months have no fee record.** These may be waivers or billing gaps; fees were not created, so fee-to-AUM ratios are understated in those months.
- **Large values are not errors.** IQR screening flags the biggest balances and trades, but 98.9% of high AUM outliers belong to ultra-high-net-worth clients, and 99.6% of large transactions reconcile or are cash movements (`reports/iqr_outliers.csv`).
- **1,532 clients joined before 2020**, before the calendar starts; `client_since` should not be joined to the date table.
- The trading calendar covers NYSE full-day holidays only; one-off market closures are not modelled.

---
`AI-assisted report — reviewed for factual accuracy on 10/24/2026 by Hannah Dickinson`
