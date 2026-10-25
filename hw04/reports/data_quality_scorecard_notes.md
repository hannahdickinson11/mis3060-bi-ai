# Data quality scorecard — how each metric is calculated

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
