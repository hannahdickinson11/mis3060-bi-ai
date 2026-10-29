## Part A — Keys

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_advisor | Dimension | `advisor_id` | — |
| dim_benchmark | Dimension | `benchmark_id` | — |
| dim_client | Dimension | `client_id` | `advisor_id` → dim_advisor[advisor_id] |
| dim_date | Dimension | `date_id` | — |
| dim_security | Dimension | `security_id` | `benchmark_id` → dim_benchmark[benchmark_id] |
| fact_fees | Fact | `fee_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`fee_date` → dim_date[date] |
| fact_portfolio_snapshot | Fact | `snapshot_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`benchmark_id` → dim_benchmark[benchmark_id]<br>`snapshot_date` → dim_date[date] |
| fact_transactions | Fact | `txn_id` | `client_id` → dim_client[client_id]<br>`advisor_id` → dim_advisor[advisor_id]<br>`security_id` → dim_security[security_id]<br>`txn_date` → dim_date[date] |

**Notes**
- **Fact dates join to `dim_date[date]`, not `dim_date[date_id]`.** The facts store calendar dates (`2020-01-01`), while `date_id` is a row number (1–1,827). `dim_date[date]` is unique and covers 2020-01-01 to 2024-12-31, so it works as the join key.
- **`fact_transactions[security_id]` is legitimately blank on 101,528 rows.** Every blank is a cash movement: Deposit (35,956), Advisory Fee (35,742) and Withdrawal (29,830). Those transactions move cash and don't involve a security. Every non-blank `security_id` matches `dim_security`.
- **Integrity check:** every primary key is unique and non-blank, and every foreign key has zero orphans (see `scripts/01_check_keys.py`).
## Part B — Grain

- **fact_fees:** One row represents one fee charge to one client for one month (unique on `client_id` + `fee_date`; every `fee_date` is the 1st of the month). Each client has one fee type per month, so the grain is client + month, not client + month + fee type.
- **fact_portfolio_snapshot:** One row represents one client's account at the start of one month (unique on `client_id` + `snapshot_date`; every `snapshot_date` is the 1st of the month).
- **fact_transactions:** One row represents one transaction (a trade, dividend, deposit, withdrawal or advisory-fee debit) by one client on one day. `txn_id` is the only key: 622 rows repeat the same client, date, type and security, so no combination of other columns identifies a row.

Checked in `scripts/01_check_keys.py` (results in `reports/key_checks.csv`).

## Part C — Measures

### fact_fees
| Column | Classification | How it may be summed or averaged |
|---|---|---|
| `amount` | Additive | Sum across clients, advisors, fee types and months: total fees charged. |
| `aum_basis` | Semi-additive | The balance a fee was charged on. Sum across clients for one month; never sum across months (12 months of a $1M account is not $12M). |
| `bps_charged` | Non-additive | A rate. Summing basis points is meaningless; recompute the effective rate as Σamount ÷ Σaum_basis × 12 × 10,000. (`amount` = `aum_basis` × `bps_charged` ÷ 10,000 ÷ 12 on every row.) |

### fact_portfolio_snapshot
| Column | Classification | How it may be summed or averaged |
|---|---|---|
| `aum` | Semi-additive | A month-start balance. Sum across clients for one month (firm AUM); across time take the last month, or average the monthly totals. |
| `return_ytd` | Non-additive | A cumulative year-to-date percentage. Summing gives nonsense; use a value for one month, or an AUM-weighted average across clients. Never sum or average across months, because each month already includes the earlier ones. |
| `benchmark_return_ytd` | Non-additive | Same as `return_ytd`; it is the same for every client on the same benchmark and month. |
| `active_alpha_ytd` | Non-additive | Equals `return_ytd` − `benchmark_return_ytd`. Recompute it from weighted returns; don't sum it. |
| `cash_pct` | Non-additive | A share of each account. Recompute as Σ(cash_pct × aum) ÷ Σaum (AUM-weighted), never sum. |

### fact_transactions
| Column | Classification | How it may be summed or averaged |
|---|---|---|
| `amount` | Additive within `txn_type` | Every amount is positive and the direction comes from `txn_type`. Sum within one type (total buys, total deposits); a sum across types mixes inflows and outflows. Net flow = Deposits − Withdrawals. |
| `shares` | Additive within one security | Sum for a single security and type (shares bought of one ticker). Shares of different securities are different units, so a total across securities means nothing. Blank on cash rows. |
| `price` | Non-additive | A per-share price. Never sum; average price paid = Σamount ÷ Σshares for one security. Blank on cash rows. |

### Numeric columns that are not measures
- **Keys:** `fee_id`, `snapshot_id`, `txn_id`, `client_id`, `advisor_id`, `benchmark_id`, `security_id`
- **Date parts:** `fact_portfolio_snapshot[year]`, `[month]` (they repeat `snapshot_date`)
- **Flags (0/1):** `fact_portfolio_snapshot[is_return_suspect]`, `fact_transactions[is_post_departure_txn]`. Count or filter on them; their sum is just a count of flagged rows.
- `fact_portfolio_snapshot[account_type]` looks numeric on 529 accounts but is text (529, Taxable, IRA, Trust, Roth IRA).

### Numeric attributes in dimensions that should never be summed
- `dim_advisor`: `years_experience`, `aum_target_mm` (a target per advisor)
- `dim_client`: `age`, `initial_aum` (a one-time starting balance), `zip_code` (a code, stored as text)
- `dim_security`: `expense_ratio_bps` (a rate; blank on 281 securities)
- `dim_date`: `year`, `quarter`, `month`, `week_of_year`, and the 0/1 flags `is_month_end`, `is_quarter_end`, `is_year_end`, `is_trading_day`
- All `*_id` columns
