# Part D — Verification of `Top 10 Client Share` (measure 11)

Drafted in Claude Desktop from my exported model metadata plus the grain, additivity and business definition (prompt and full response in `dax_session.md`). Verified in Power BI DAX query view and independently in pandas.

## 1. Did Claude's measure run as written?

Yes. I ran Claude's test query unchanged in DAX query view: it defines the measure inside the query, so I could test before adding it. It returned four results with no errors:

| Result | What it showed | Check |
|---|---|---|
| 1. Grand total | Snapshot 2024-12-01, 2,325 clients, Ending AUM $12,729,572,078.86, Top 10 AUM $784,005,019.49, share **0.0616** | 784.0M ÷ 12,729.6M = 6.16% ✅ |
| 2. By year | Every year uses Dec 1 of that year; 2024 = 0.06, same as Result 1 | Last-snapshot lock works ✅ |
| 3. Tiers, 2024 | HNW 0.03, Retail 0.02, UHNW 0.08 | All between 0 and 1 ✅ |
| 4. Top 10 list | Exactly 10 rows, all UHNW, largest = client 1001 ($82.4M) | Sum = $784,005,019.49 (confirmed in pandas) ✅ |

## 2. Reconciliation rows that prove it

From `reports/measure_reconciliation.csv` (tolerance 0.0001, all `match = True`):

| slice | Power BI | pandas | abs_diff |
|---|---:|---:|---:|
| Total | 0.06158926746579308 | 0.06158926746579307 | 1.4e-17 |
| tier=HNW\|year=2024 | 0.03139674749179622 | 0.03139674749179621 | 6.9e-18 |
| tier=Retail\|year=2024 | 0.018348218311311223 | 0.018348218311311205 | 1.7e-17 |
| tier=UHNW\|year=2024 | 0.08126426752227996 | 0.08126426752227994 | 1.4e-17 |

The pandas version ranks clients on the last snapshot date with no DAX involved, so the two tools agree to floating-point precision.

## 3. Edge cases checked

1. **Grand total (no filters):** 6.16%. Matches the 2024 row because both use the 2024-12-01 snapshot (reconciliation row "Total").
2. **`dim_date[year]` = 2022:** Power BI showed 0.06; pandas gives 5.53% (0.055309). 2022 is the only year in which all 2,500 clients are still active, so it's a clean year to test before any churn.
3. **2024 tier table (`VALUES` vs `ALL`):** HNW shows 3.14% and Retail 1.83%. If the measure used `ALL ( dim_client )`, it would rank the firm-wide top 10, which are all UHNW, so HNW and Retail would show 0% or blank. Non-zero tier values prove the ranking stays inside the current filter. UHNW's 8.13% = $784.0M ÷ $9,647.6M, because the firm's top 10 are all UHNW.
4. **Ties at rank 10 (Claude's edge case 1):** at Dec 2024, rank 10 is $74,424,366.68 and rank 11 is $72,106,567.72, so there is no tie at the cutoff and the `client_id` tie-breaker does not change the result.
5. **Zero or negative AUM (Claude's edge case 6):** in pandas, the minimum `aum` is $1,000 and no rows are ≤ 0, so the ratio cannot exceed 1.

## 4. What I changed and why

Nothing in the measure itself. I added only `Top 10 Client Share` to the model, using the per-measure "Update model: Add new measure" link, and did **not** add the two test helpers from Claude's query (`QA Snapshot Date`, `QA Top 10 AUM`). Claude said those exist only to test the query. I formatted the measure as a percentage with 2 decimals and added it to the KPI table and the 2024 tier table.

## 5. A claim I confirmed or refuted

**Claude's claim:** the `LastSnap` lock is needed because, without it, `[Ending AUM]` inside `TOPN` would rank each client by their *own* last balance, so a client who left mid-year could make the top 10 while not being in the year-end total.

**Mechanism confirmed:** Part C(a) shows this per-client last-date behaviour directly. `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` returns $13,149,297,713.80 versus Ending AUM of $12,729,572,078.86. The $419,725,634.94 gap is exactly the last balances of 175 clients who left between Dec 2022 and Nov 2023, confirmed in both Power BI and pandas.

**But it makes no difference in this data:** I recomputed the share in pandas *without* the lock, ranking each client by their own last balance in the slice, for every year and the grand total. The results were identical (for example, 2023: 6.0379% with and without), because none of the 175 departed clients was large enough to rank in a top 10. I confirmed this in Power BI as well: a test-only measure without `LastSnap`, defined in a DAX query and not added to the model, returned the same value as `Top 10 Client Share` for every year 2020–2024. So the lock is a correct safeguard, but Claude's example scenario does not actually occur in Wildcat's data. I kept the lock because it makes the measure correct if a large client ever leaves.
