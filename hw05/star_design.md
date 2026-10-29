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

## Part E — Relationships and design questions

### The model I built (Part D)

| # | From (many) | To (one) | Status |
|---|---|---|---|
| 1 | fact_fees[client_id] | dim_client[client_id] | Active |
| 2 | fact_fees[advisor_id] | dim_advisor[advisor_id] | Active |
| 3 | fact_fees[fee_date] | dim_date[date] | Active |
| 4 | fact_portfolio_snapshot[client_id] | dim_client[client_id] | Active |
| 5 | fact_portfolio_snapshot[advisor_id] | dim_advisor[advisor_id] | Active |
| 6 | fact_portfolio_snapshot[benchmark_id] | dim_benchmark[benchmark_id] | Active |
| 7 | fact_portfolio_snapshot[snapshot_date] | dim_date[date] | Active |
| 8 | fact_transactions[client_id] | dim_client[client_id] | Active |
| 9 | fact_transactions[advisor_id] | dim_advisor[advisor_id] | Active |
| 10 | fact_transactions[security_id] | dim_security[security_id] | Active |
| 11 | fact_transactions[txn_date] | dim_date[date] | Active |
| 12 | dim_security[benchmark_id] | dim_benchmark[benchmark_id] | Active |
| 13 | dim_client[advisor_id] | dim_advisor[advisor_id] | **Inactive** |

Every relationship is many-to-one with single cross-filter direction (the dimension filters the fact). `dim_date` is marked as the date table on `date`. Every foreign key from Part A became a relationship; one is inactive (#13, see b).

**Conformed dimensions:** `dim_client`, `dim_advisor` and `dim_date` are shared by all three fact tables, so one slicer on any of them filters fees, snapshots and transactions the same way. `dim_benchmark` is shared by the snapshot (directly) and the transactions (through `dim_security`). `dim_security` is used only by the transactions.

**Row counts reconcile:** a Count card on each table's primary key shows 25, 8, 2,500, 1,827, 500, 122,197, 129,547 and 298,572, matching the brief (`powerbi/row_counts.png`).

### (a) Some transaction rows have no `security_id`. Why, and is that a defect?

101,528 of the 298,572 transactions (34%) have a blank `security_id`, and every one is a cash movement: Deposit (35,956), Advisory Fee (35,742) and Withdrawal (29,830). These move money in or out of the account and don't involve buying, selling or receiving income from a security, so there is no security to point to. It is **not a defect**: `scripts/01_check_keys.py` shows the blanks are exactly the cash rows (0 trades or dividends are blank, and 0 cash rows carry a security), and every non-blank `security_id` matches `dim_security`. In Power BI these rows appear as a `(Blank)` member when you group by a `dim_security` column; that is expected structure, not an orphan key. A report should label it "Cash" or filter it out when the question is about securities.

### (b) `advisor_id` is in `dim_client` and on all three facts. Which relationship(s) did I keep active, and why?

I kept the **three direct links from each fact to `dim_advisor` active** (#2, #5, #9) and made **`dim_client` → `dim_advisor` inactive** (#13). Power BI allows only one active filter path between two tables. With both active, `dim_advisor` could reach each fact directly and also through `dim_client`, which is ambiguous. I chose the direct links because they keep every fact one hop from the advisor (a pure star), so an advisor slicer filters all three facts without depending on the client table.

The choice doesn't change any numbers today: on every row of all three facts, the fact's `advisor_id` equals the client's advisor in `dim_client` (0 mismatches, checked in the script). That includes the 2,410 transactions flagged `is_post_departure_txn = 1`, so the facts record the client's **current** advisor, not the advisor at the time of the transaction. Neither path can attribute activity to a former advisor; the schema would need the advisor-at-the-time stored on the fact (or a dated client–advisor history) to do that.

### (c) The date dimension has its own `date_id`, but the facts store calendar dates. Which column did I join on, and why?

I joined `txn_date`, `fee_date` and `snapshot_date` to **`dim_date[date]`**. The facts hold calendar dates (`2020-01-01`); `date_id` is a row number (1 to 1,827) that never appears in any fact, so joining on it would match nothing. `dim_date[date]` is unique, has no gaps from 2020-01-01 to 2024-12-31, and covers every fact date (0 orphans in the script). Both sides are typed **Date** (not Date/Time), so the values match exactly. Using `date_id` would have required adding a new key column to each fact, which the brief does not allow. I also marked `dim_date` as the date table on `date`, which time-intelligence DAX in Assignment 6 needs.

### (d) Star or snowflake: does anything connect one dimension to another? Did I keep it?

Yes, two dimension-to-dimension links:

- **`dim_client` → `dim_advisor`:** kept, but **inactive**, because the facts already reach `dim_advisor` directly (see b). It is in the model to document the relationship and can be switched on with `USERELATIONSHIP` in a DAX measure if needed.
- **`dim_security` → `dim_benchmark`:** kept **active**. This makes the model a **star with one snowflake branch**: transactions reach `dim_benchmark` through `dim_security`. It creates no ambiguity, because the transactions have no benchmark of their own, so there is only one path.

`dim_benchmark` therefore means two different things depending on the fact. For a snapshot, it is the **portfolio's** benchmark (only benchmarks 1, 3 and 8 are used). For a transaction, it is the **security's** benchmark. A benchmark slicer filters both, so a report mixing the two facts should say which meaning it uses.
