# HW4 Decision Log — Wildcat Capital Data Cleaning

> 
>
> Evidence comes from `reports/dq_summary_raw.csv` (65 findings in 41 issue groups, run 2026-10-19) plus targeted checks against the raw files. Findings that describe the same rows (same `issue_group`) are logged once.

## Summary

| ID | Table / column | Decision | Rows |
|---|---|---|---:|
| D01 | all raw files (names) | standardize | 3 files |
| D02 | dim_client.state | standardize | 78 |
| D03 | dim_client (IDs 2501–2525) | quarantine | 25 |
| D04 | dim_client.risk_profile | flag (leave blank) | 76 |
| D05 | dim_client.client_since | leave as is | 1,549 |
| D06 | dim_advisor.certifications | leave as is | 6 |
| D07 | dim_security.sector / expense_ratio_bps | leave as is | 219 / 281 |
| D08 | dim_security.name | leave as is | 3 pairs |
| D09 | dim_date.is_trading_day | standardize (correct) | 47 |
| D10 | fact_transactions.security_id | standardize | 197,175 |
| D11 | fact_transactions.security_id / shares / price (blanks) | leave as is | 101,597 |
| D12 | fact_transactions.shares | convert (sign) | 836 |
| D13 | fact_transactions.client_id | quarantine | 200 |
| D14 | fact_transactions.txn_date | flag | 44,262 |
| D15 | fact_portfolio_snapshot.return_ytd (% text) | convert | 300 |
| D16 | return_ytd / active_alpha_ytd (scientific notation) | leave as is | 891 values |
| D17 | snapshot.aum + fees.aum_basis = 1000.0 | flag | 420 / 386 |
| D18 | snapshot.return_ytd / active_alpha_ytd (extreme) | flag | 976 + 497 |
| D19 | fact_fees.bps_charged | leave as is | 1 |
| D20 | snapshots with no fee row | leave as is | 7,350 |
| D21 | snapshot dated before client_since | leave as is | 930 |

---

## Dimension tables

### D01 — All raw files: file names
| Field | Entry |
|---|---|
| **Table / column** | `dim_benchmark (2).csv`, `dim_date (2).csv`, `dim_security (2).csv` |
| **Evidence** | 3 of 8 raw files carry a ` (2)` suffix. Row and column counts of all 8 match the briefing exactly. |
| **Dimension violated** | Consistency |
| **Decision** | **Standardize**: write clean files under plain table names (`dim_benchmark.csv`, etc.) |
| **Justification** | The briefing requires the same file names; Power BI (HW5) will reference files by name. The suffix is a download artifact, not a different version. |
| **Risk** | If a newer un-suffixed export existed, we could be cleaning the wrong version. Mitigated: the audit now stops if two files match one table. |

### D02 — dim_client.state: spelled-out state names
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.state` |
| **Evidence** | 78 of 2,525 rows (3.1%) use full names instead of the 2-letter code: Pennsylvania 25, Florida 15, New York 14, New Jersey 13, California 5, Illinois 4, Texas 2. Shapes: `A` 96.9%, `Aa` 2.0%, `Aa Aa` 1.1%. |
| **Dimension violated** | Validity, Consistency |
| **Decision** | **Standardize** to USPS codes with a fixed 7-name lookup |
| **Justification** | "PA" and "Pennsylvania" are the same state but would show as two bars in any by-state chart, understating PA (the largest state, 414 + 25 clients). |
| **Risk** | Very low — each name maps to exactly one code. A misspelled name not in the lookup would stay unfixed; the script will `assert` 0 values outside the allowed list after the fix. |

### D03 — dim_client: duplicate clients 2501–2525
| Field | Entry |
|---|---|
| **Table / column** | `dim_client` rows with `client_id` 2501–2525 |
| **Evidence** | 25 rows match an existing client (IDs 1–2500) on first name, age, city, zip, initial AUM — and also on state, risk profile, tier, account type, client_since, advisor and is_active (12 of 12 fields, all 25 pairs). Only differences: a new ID and a truncated last name (`Taylo` vs `Taylor`, `Jacobso` vs `Jacobson`). None of the 25 appear in any fact table; all 25 originals do. |
| **Dimension violated** | Uniqueness |
| **Decision** | **Quarantine** the 25 duplicate rows to `quarantine_dim_client_duplicates.csv` (with the matched original's ID). Keep the originals. |
| **Justification** | One person counted twice inflates client counts and onboarded AUM (the duplicates carry $49.1M of initial AUM). Because no fact rows point to them, removing them orphans nothing. |
| **Risk** | If any were genuinely different people, they'd be dropped — very unlikely with 12 identical fields and zero activity. Verify after: 2,500 clients = distinct client_ids in fees and snapshots. |

### D04 — dim_client.risk_profile: blanks
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.risk_profile` |
| **Evidence** | 76 of 2,525 clients blank (3.0%; Retail 49, HNW 18, UHNW 9). All 3,942 of their snapshots are measured against benchmark 3 (60/40 Blend) — a benchmark otherwise used **only** by Balanced clients (38,960 snapshots). |
| **Dimension violated** | Completeness |
| **Decision** | **Flag**: leave blank, add `flag_risk_profile_missing` (0/1). Document the benchmark evidence. |
| **Justification** | A risk profile is a suitability assessment the client signs off on — a compliance record. The benchmark strongly suggests "Balanced," but writing it in would create a record that was never collected. The committee should get these clients re-profiled. |
| **Risk** | Risk-profile breakdowns show a small "(blank)" group. If the instructor treats the benchmark as enough reconciliation, the alternative is to fill "Balanced" and keep the flag — **your call**. |

### D05 — dim_client.client_since before the calendar
| Field | Entry |
|---|---|
| **Table / column** | `dim_client.client_since` |
| **Evidence** | 1,549 clients (1,532 after D03) joined before 2020-01-01; `dim_date` covers 2020–2024 only. Range 2015-01-01 to 2022-12-30. 0 fact rows dated before the client's joining month. |
| **Dimension violated** | None — legitimate structure |
| **Decision** | **Leave as is** |
| **Justification** | `client_since` is a client attribute, not a foreign key to `dim_date`. Long-tenured clients are expected. |
| **Risk** | In Power BI, don't relate `client_since` to `dim_date` or 1,532 clients will lose the join. Note in README_clean. |

### D06 — dim_advisor.certifications = "None"
| Field | Entry |
|---|---|
| **Table / column** | `dim_advisor.certifications` |
| **Evidence** | 6 of 25 advisors have the text value `None`. |
| **Dimension violated** | None — legitimate structure |
| **Decision** | **Leave as is** |
| **Justification** | "None" means the advisor holds no certification — a real answer, not a missing one. |
| **Risk** | Default `pd.read_csv` turns "None" into NaN and makes it look missing — another reason for `keep_default_na=False`. Note in README_clean. |

### D07 — dim_security: blank sector and expense ratio
| Field | Entry |
|---|---|
| **Table / column** | `dim_security.sector`, `dim_security.expense_ratio_bps` |
| **Evidence** | Sector blank on 219 rows = exactly the 219 ETFs. Expense ratio blank on 281 rows = exactly the 281 single stocks. 0 exceptions either way. |
| **Dimension violated** | None — legitimate structure |
| **Decision** | **Leave as is** |
| **Justification** | ETFs span sectors; individual stocks have no expense ratio. Filling either would invent data. |
| **Risk** | Sector charts show a blank bucket for ETFs; label it "Fund / multi-sector" in the BI layer, not in the data. |

### D08 — dim_security: repeated names
| Field | Entry |
|---|---|
| **Table / column** | `dim_security.name` |
| **Evidence** | 3 names appear twice (Jones Inc Fund, Davis PLC Fund, Graham Group Inc.). Each pair has different tickers and security IDs; two pairs also differ in asset class. Tickers are 100% unique. |
| **Dimension violated** | None — legitimate structure |
| **Decision** | **Leave as is** |
| **Justification** | One issuer can offer several funds/share classes; the ticker is the real identifier. |
| **Risk** | Grouping by name instead of ticker would merge different securities — use `security_id`/`ticker` in reports. |

### D09 — dim_date.is_trading_day: market holidays
| Field | Entry |
|---|---|
| **Table / column** | `dim_date.is_trading_day` |
| **Evidence** | All 522 weekend days are 0 and every weekday is 1 — so 47 market holidays (e.g. 2020-01-01, 2020-04-10 Good Friday, 2020-11-26 Thanksgiving) are marked as trading days. All other calendar fields (year, quarter, month, week, day name, month/quarter/year-end) reconcile to the date with 0 errors; no missing days. |
| **Dimension violated** | Accuracy |
| **Decision** | **Standardize (correct)** the 47 holidays to 0, logging each in `value_changes.csv` |
| **Justification** | The exchange holiday calendar is an external fact, so this is a correction, not invented data. Trading-day counts drive any "per trading day" measure. |
| **Risk** | The audit's holiday rules are an approximation of the NYSE calendar — **check the 47 dates against NYSE's published holiday list before applying.** Correcting this moves 3,613 trades into the "non-trading day" flag in D14. |

## Fact tables

### D10 — fact_transactions.security_id stored as "45.0"
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.security_id` |
| **Evidence** | 197,175 of 197,175 non-blank values are float text (`45.0`, `174.0`); `dim_security.security_id` is `45`. Raw join match rate: 0%. After stripping `.0`: 100% match, 0 orphans. |
| **Dimension violated** | Validity, Referential Integrity |
| **Decision** | **Standardize**: remove the trailing `.0` to make whole-number text |
| **Justification** | Without this, no trade or dividend joins to a security, so nothing can be reported by asset class, sector or benchmark. |
| **Risk** | If any ID had a real decimal part (e.g. `45.5`), stripping would mis-map it — none do; the script will `assert` every value matches `^\d+\.0$` before converting. |

### D11 — fact_transactions: blank security/shares/price on cash movements
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.security_id`, `shares`, `price` |
| **Evidence** | 101,597 rows blank in all three — exactly the Deposit (35,981), Withdrawal (29,850) and Advisory Fee (35,766) rows. 0 trades/dividends missing a security; 0 cash rows with one. |
| **Dimension violated** | None — legitimate structure |
| **Decision** | **Leave as is** |
| **Justification** | Cash moving in or out of an account involves no security. Filling these would invent trades. |
| **Risk** | The RI check must exclude blank keys from the match rate (it does), and Power BI must allow blank `security_id` on the relationship. |

### D12 — fact_transactions.shares: negative Buy quantities
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.shares` |
| **Evidence** | 836 rows (0.28%) have negative shares — all `Buy`. For all 836, `amount` equals \|shares × price\| within $1 (`amount` itself is always positive). |
| **Dimension violated** | Validity, Consistency |
| **Decision** | **Convert**: take the absolute value of `shares` |
| **Justification** | Direction is carried by `txn_type`, and `amount` confirms the magnitude is right — only the sign is wrong. Left alone, a net-shares measure (Buys − Sells) would subtract these buys twice. |
| **Risk** | If a negative Buy meant a cancelled trade, we'd now count it as a real purchase. There is no reversal transaction type in the data, so a sign entry error is the likelier explanation. Log every row in `value_changes.csv`. |

### D13 — fact_transactions.client_id: orphans
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.client_id` |
| **Evidence** | 200 rows (0.07%) reference 200 different client IDs (2702–3192) that don't exist in `dim_client` (IDs 1–2525). One row each, all types (Buy 58, Dividend 38, Sell 35, Deposit 25, Advisory Fee 24, Withdrawal 20), $10.89M total amount. Their advisor IDs are valid. |
| **Dimension violated** | Referential Integrity |
| **Decision** | **Quarantine** to `quarantine_fact_transactions_orphan_clients.csv` |
| **Justification** | With no client record, these can't be tied to a risk profile, tier or account, and we can't invent one. Keeping them would put a "(blank)" client into every client-level report. |
| **Risk** | If the client extract is simply incomplete, $10.9M of real activity drops out of client reporting. The quarantine file keeps it for follow-up with the source system. |

### D14 — fact_transactions.txn_date: trades on non-trading days
| Field | Entry |
|---|---|
| **Table / column** | `fact_transactions.txn_date` |
| **Evidence** | 40,649 of 143,311 Buy/Sell rows (28.4%) fall on Saturday/Sunday, plus 3,613 on market holidays (D09). Every transaction type is 28–29% weekend — about 2/7, meaning dates are spread evenly over all days of the week. A systemic pattern, not individual typos. |
| **Dimension violated** | Accuracy / Plausibility |
| **Decision** | **Flag**: add `flag_non_trading_day` (0/1) on Buy/Sell rows dated on a non-trading day. Leave dates unchanged. |
| **Justification** | Exchanges don't execute trades on weekends/holidays, but there's no evidence of the correct date; shifting to the next trading day would invent one. The month is still right, which is the grain the committee reports at. |
| **Risk** | Daily or day-of-week trading analysis is unreliable — state this as a known limitation. Deposits/withdrawals/fees on weekends can be legitimate (posting dates), so they are not flagged. |

### D15 — fact_portfolio_snapshot.return_ytd: percent text
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.return_ytd` |
| **Evidence** | 300 rows stored as percent text (`9.28%`) while the other 129,247 are decimals (`0.0928`). All 300 equal `benchmark_return_ytd + active_alpha_ytd` within 0.0001 once divided by 100. |
| **Dimension violated** | Validity, Consistency |
| **Decision** | **Convert**: strip `%`, divide by 100 |
| **Justification** | Converting the column to numbers would turn these into blanks (losing 300 returns), and just stripping the `%` would make them 100× too large. The alpha identity confirms the repair rather than assuming it. |
| **Risk** | None if the script `assert`s that all 300 reconcile after conversion. |

### D16 — Scientific notation in return columns
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.return_ytd`, `active_alpha_ytd` |
| **Evidence** | 891 values written like `-1.9e-05` (tiny numbers). All parse as valid floats. |
| **Dimension violated** | None — formatting only |
| **Decision** | **Leave as is** (values unchanged; they become ordinary floats when typed) |
| **Justification** | `-1.9e-05` and `-0.000019` are the same number. |
| **Risk** | A tool reading the column as text would see mixed formats — set the column type to Decimal in Power BI. |

### D17 — AUM placeholder 1000.0 (snapshots and fees)
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.aum`, `fact_fees.aum_basis` (and `fact_fees.amount` on those rows) |
| **Evidence** | Exactly 1000.0 appears in 420 snapshots (92 clients) and 386 fee rows — no other AUM value appears more than twice. Fee AUM equals snapshot AUM for every matched client-month (0 mismatches), so it is the same upstream default. Placeholder months sit in the middle of normal AUM (e.g. client 1026: $33,871 → 1,000 × 4 months → $33,979). Fees on those rows average $0.73. |
| **Dimension violated** | Accuracy / Plausibility, Completeness |
| **Decision** | **Flag**: add `flag_aum_placeholder` in both tables. Do not interpolate. |
| **Justification** | The real AUM is unknown; filling from neighbouring months would invent balances, and fees were recorded (and likely billed) on the placeholder. |
| **Risk** | AUM and fee totals are understated for those months and AUM trend lines show false dips — exclude flagged rows from AUM/fee-rate measures. 34 placeholder snapshots have no fee row (see D20). |

### D18 — Extreme YTD returns
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.return_ytd`, `active_alpha_ytd` |
| **Evidence** | 976 rows above +100% YTD (max 94.67 = 9,467%); 497 below −90%; 459 alphas outside ±2 (458 are the same rows as the >100% returns). 476 of the 497 near-total losses and about half of the >100% rows belong to the 92 placeholder clients from D17; 249 are on placeholder rows themselves. The alpha identity still holds on all of them. |
| **Dimension violated** | Accuracy / Plausibility |
| **Decision** | **Flag**: add `flag_return_implausible` (return > 1 or < −0.9). Leave values. |
| **Justification** | Returns can't be recomputed without daily cash flows, and the values are internally consistent; most are a side effect of measuring growth from a $1,000 placeholder base. |
| **Risk** | A single 9,467% row distorts any average return — use median or exclude flagged rows in committee reporting. |

### D19 — fact_fees.bps_charged slightly above 100
| Field | Entry |
|---|---|
| **Table / column** | `fact_fees.bps_charged` |
| **Evidence** | 1 row (fee_id 68809, client 1402, 2024-07) at 100.38 bps, just above the 100-bps ceiling I set in the audit. That client's 55 fees range 81.3–100.38 (mean 88.9). The fee amount reconciles to the formula. |
| **Dimension violated** | Accuracy / Plausibility (borderline) |
| **Decision** | **Leave as is** |
| **Justification** | 100 bps was my own threshold, not a documented cap; the rate is close to this client's normal range and the amount is consistent. |
| **Risk** | If Wildcat has a contractual 1.00% cap, the client was overcharged by about $0.34 — mention in the report. |

### D20 — Snapshots with no fee row
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot` ↔ `fact_fees` (client-month) |
| **Evidence** | 7,350 of 129,547 snapshots (5.7%) have no fee for the same client-month; 0 fees lack a snapshot. Spread across 2,261 clients (median 3 months each) and every year (1,139–1,684 per year); 95% belong to active clients. |
| **Dimension violated** | Completeness (possible) |
| **Decision** | **Leave as is**; document as a known limitation |
| **Justification** | Fee waivers, billing holidays or minimum-fee rules could explain missing months; the fee table is the record of what was charged, and inventing fees would be fabrication. |
| **Risk** | Fee-to-AUM ratios are understated in those months. In Power BI the snapshot–fee link must allow unmatched snapshots. |

### D21 — Snapshot dated before client_since (same month)
| Field | Entry |
|---|---|
| **Table / column** | `fact_portfolio_snapshot.snapshot_date` |
| **Evidence** | 930 snapshots are dated before the client's `client_since` — every one is the 1st of the month the client joined (e.g. snapshot 2020-11-01, joined 2020-11-18). 0 in an earlier month. |
| **Dimension violated** | None — legitimate structure |
| **Decision** | **Leave as is** |
| **Justification** | Snapshots are monthly and labelled with the 1st; the joining month's snapshot is legitimately dated before the exact joining day. |
| **Risk** | A day-level "activity before onboarding" rule would wrongly flag these — compare at month level. |

---

## Checks that passed (no action needed)
- Primary keys unique and non-blank in all 8 tables.
- `fact_fees.amount` = `aum_basis × bps ÷ 10,000 ÷ 12` on all 122,197 rows.
- `active_alpha_ytd` = `return_ytd − benchmark_return_ytd` on all rows.
- Fact `advisor_id` matches the client's advisor in `dim_client` (0 mismatches in 3 tables); snapshot `account_type` matches `primary_account_type`.
- One fee and one snapshot per client-month (no duplicates); no exact duplicate rows in any table.
- 11 of 13 relationships match 100% in the raw data, including all 3 fact date columns to `dim_date`. The other 2 are D10 and D13.
- Client tier agrees with initial AUM on every row.

## Proposed cleaning order (for Part C)
1. D01 file names → 2. type/format fixes (D10, D15, D02) → 3. D03 quarantine duplicates → 4. D13 quarantine orphans (needs the cleaned client list) → 5. D12 sign fix → 6. D09 calendar → 7. flags (D04, D14, D17, D18) → 8. final asserts: raw rows = clean + quarantined, every relationship 100%.
Formats come first so the later checks compare like with like; quarantines come before flags so flag counts reflect only the rows that are kept.
