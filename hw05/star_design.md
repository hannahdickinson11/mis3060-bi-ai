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