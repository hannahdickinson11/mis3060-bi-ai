# HW6 — Measure Library (AUM & Performance)

All measures live in the `_Measures_` table of `powerbi/hw06.pbix`. Time always filters through `dim_date` (marked as the date table), never through the fact tables' own `Year` / `Month` columns.

**Additivity patterns used**
- **SUM**: safe to add across any dimension (fees, transactions).
- **Last balance**: `aum` is a month-end balance (semi-additive), so take it at the last snapshot date in the filter (`LASTNONBLANK`), never sum it across months.
- **Recompute-and-weight**: rates and ratios are never summed or averaged; they are rebuilt from additive parts (with a weight where needed).

---

## Base measures (from ICE 9 / ICE 10)

### Total Fees
```DAX
Total Fees = SUM ( fact_fees[amount] )
```
**Pattern:** SUM
**Meaning:** Total fee revenue Wildcat billed in the period.

### Net Flows
```DAX
Deposit   = CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Deposit" )
Withdraws = CALCULATE ( SUM ( fact_transactions[amount] ), fact_transactions[txn_type] = "Withdrawal" )
Net Flows = [Deposit] - [Withdraws]
```
**Pattern:** SUM
**Meaning:** New money clients put in minus money they took out, before any market gains or losses.

### Effective Fee Rate (bps) (ICE 9, used in Part C(b))
```DAX
Effective Fee Rate (bps) = DIVIDE ( [Total Fees] * 12 * 10000, SUM ( fact_fees[aum_basis] ) )
```
**Pattern:** Recompute-and-weight
**Meaning:** Annualized fees per dollar of the AUM the fees were billed on.

---

## 1a. AUM (naive SUM) —  WRONG, kept only to show the trap
```DAX
AUM (naive SUM) = SUM ( fact_portfolio_snapshot[aum] )
```
**Pattern:** SUM applied to a balance (incorrect)
**Meaning:** Adds every client's balance in every month, so a year counts each dollar about 12 times. It is not on any report visual and should never be used to answer "how much do we manage?"

## 1b. Ending AUM
```DAX
Ending AUM =
CALCULATE (
    SUM ( fact_portfolio_snapshot[aum] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
**Pattern:** Last balance
**Meaning:** How much money Wildcat manages at the end of the selected period ($12.73B at Dec 2024).

## 2. Ending Clients
```DAX
Ending Clients =
CALCULATE (
    DISTINCTCOUNT ( fact_portfolio_snapshot[client_id] ),
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
)
```
**Pattern:** Last balance
**Meaning:** How many clients still hold a balance with Wildcat at the end of the period (2,325 at Dec 2024).

## 3. Avg AUM per Client
```DAX
Avg AUM per Client = DIVIDE ( [Ending AUM], [Ending Clients] )
```
**Pattern:** Recompute (ratio of two last balances)
**Meaning:** The size of a typical client relationship at period end, useful for comparing tiers and advisors.

## 4. Ending AUM LY and AUM YoY %
```DAX
Ending AUM LY = CALCULATE ( [Ending AUM], SAMEPERIODLASTYEAR ( dim_date[date] ) )

AUM YoY % = DIVIDE ( [Ending AUM] - [Ending AUM LY], [Ending AUM LY] )
```
**Pattern:** Last balance (shifted one year) / Recompute
**Meaning:** How much the firm's balance grew compared with the same point last year, from both new money and market movement.

## 5. Ending AUM PM and AUM MoM %
```DAX
Ending AUM PM = CALCULATE ( [Ending AUM], DATEADD ( dim_date[date], -1, MONTH ) )

AUM MoM % = DIVIDE ( [Ending AUM] - [Ending AUM PM], [Ending AUM PM] )
```
**Pattern:** Last balance (shifted one month) / Recompute
**Meaning:** Month-over-month change in the balance, for spotting short-term swings (Dec 2024: +4.25% vs Nov 2024).

## 6. Avg Monthly AUM
```DAX
Avg Monthly AUM =
DIVIDE (
    SUM ( fact_portfolio_snapshot[aum] ),
    DISTINCTCOUNT ( fact_portfolio_snapshot[snapshot_date] )
)
```
**Pattern:** Recompute (Σ balance ÷ number of months)
**Meaning:** The average balance Wildcat managed across the months in the period, the fair base for comparing against fees earned over that period.

## 7. Fee Yield (bps)
```DAX
Fee Yield (bps) =
DIVIDE (
    [Total Fees] * 12 * 10000,
    SUM ( fact_portfolio_snapshot[aum] )
)
```
**Pattern:** Recompute-and-weight (fees from `fact_fees` ÷ AUM from `fact_portfolio_snapshot`, same months)
**Meaning:** How many basis points of revenue Wildcat earns per dollar it manages each year.

## 8. Organic Growth Rate
```DAX
Organic Growth Rate = DIVIDE ( [Net Flows], [Ending AUM LY] )
```
**Pattern:** Recompute (SUM of flows ÷ last balance one year earlier)
**Meaning:** Growth from net new client money alone, as a share of where the firm started the year, excluding market gains.

## 9. AUM-Weighted Alpha
```DAX
AUM-Weighted Alpha =
VAR LastSnap =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
RETURN
    CALCULATE (
        DIVIDE (
            SUMX ( fact_portfolio_snapshot, fact_portfolio_snapshot[aum] * fact_portfolio_snapshot[active_alpha_ytd] ),
            SUM ( fact_portfolio_snapshot[aum] )
        ),
        LastSnap,
        fact_portfolio_snapshot[is_return_suspect] <> 1
    )
```
**Pattern:** Recompute-and-weight (alpha weighted by `aum`, at the last snapshot only, suspect rows excluded)
**Meaning:** How much Wildcat's dollars beat (or trailed) their benchmarks year-to-date, where large accounts count more than small ones.

## 10. Alpha Signal
```DAX
Alpha Signal =
VAR a = [AUM-Weighted Alpha]
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( a ), BLANK (),
        a >= 0.02, "Outperforming",
        a <= -0.02, "Lagging",
        "In line"
    )
```
**Pattern:** Recompute (text label on top of #9)
**Meaning:** A plain-language flag that tells a manager at a glance whether performance is beating, trailing, or roughly matching benchmarks (±2%).

## 11. Top 10 Client Share (drafted with Claude Desktop, see `claude/`)
```DAX
Top 10 Client Share =
VAR LastSnap =
    LASTNONBLANK ( dim_date[date], CALCULATE ( COUNTROWS ( fact_portfolio_snapshot ) ) )
VAR TopClients =
    CALCULATETABLE (
        TOPN ( 10, VALUES ( dim_client[client_id] ), [Ending AUM], DESC, dim_client[client_id], ASC ),
        LastSnap
    )
VAR Top10AUM =
    CALCULATE ( [Ending AUM], LastSnap, KEEPFILTERS ( TopClients ) )
VAR TotalAUM =
    CALCULATE ( [Ending AUM], LastSnap )
RETURN
    DIVIDE ( Top10AUM, TotalAUM )
```
**Pattern:** Last balance + Recompute (top-10 Ending AUM ÷ total Ending AUM, ranked within the current filter)
**Meaning:** How dependent Wildcat is on its biggest relationships: the share of AUM that would be at risk if the 10 largest clients in the current view left (6.16% firm-wide at Dec 2024).

---

# Part C — Design questions

## (a) Ending AUM vs SUMX over clients

| Measure (no filters) | Value |
|---|---:|
| `Ending AUM` | $12,729,572,078.86 |
| `SUMX ( VALUES ( dim_client[client_id] ), [Ending AUM] )` | $13,149,297,713.80 |
| **Difference** | **$419,725,634.94** |

With no filters, `Ending AUM` finds one last date for the whole model (2024-12-01) and sums every client's balance on that date. `SUMX` instead evaluates `[Ending AUM]` once per client, so `LASTNONBLANK` finds **each client's own** last snapshot. For the 2,325 clients still active in Dec 2024 that is the same date, but the 175 clients who left (last snapshots between Dec 2022 and Nov 2023) are counted at their final balance. The $419,725,634.94 difference is exactly the sum of those 175 departed clients' last balances (verified in pandas and PowerBI DAX query view).

`Ending AUM` ($12.73B) answers "How much do we manage today?" The SUMX total mixes balances from different dates and includes money that has already left the firm.

## (b) Fee Yield vs Effective Fee Rate (2024)

| 2024 | Value |
|---|---:|
| Total fees | $48,714,005.93 |
| `Fee Yield (bps)` (fees × 12 × 10,000 ÷ Σ `aum`) | 43.15 |
| `Effective Fee Rate (bps)` (fees × 12 × 10,000 ÷ Σ `aum_basis`) | 45.53 |
| Σ `aum` over 2024 snapshot rows (27,900 client-months) | $135,459,843,783.73 |
| Σ `aum_basis` over 2024 fee rows (26,216 rows) | $128,385,303,527.10 |

Both use the same fees in the numerator, so the gap comes entirely from the denominator. In pandas, matching snapshots to fees by client and month shows:
- Where a fee row exists, `aum_basis` equals `aum` (ratio 1.0000), with one fee row per client-month.
- **1,684 client-months in 2024 have a snapshot but no fee row.** Those months hold $7,074,540,256.63 of AUM (5.22% of Σ aum). $128.39B + $7.07B = $135.46B, which accounts for the whole difference.
- Every active client is billed in some months but not others (5 to 12 billed months each, median 11).

So Fee Yield divides fees by AUM that includes unbilled months, while Effective Fee Rate only counts the AUM that was actually billed. **Data limitation:** `fact_fees` does not cover every client-month in `fact_portfolio_snapshot`. From the data alone we can't tell whether those months were genuinely not charged (waived, quarterly billing) or are missing fee records, so Fee Yield may understate the true rate.

## (c) Why AUM-Weighted Alpha uses the last snapshot and excludes suspect rows

**Last snapshot only:** `active_alpha_ytd` is year-to-date, so each month's value already includes all earlier months of that year. Averaging or weighting across months mixes partial-year results (January's alpha covers one month, December's covers twelve) and double-counts early performance. The last snapshot in the period is the only one that represents the full period. For contrast, weighting across all 2024 months gives 0.32%, versus 1.45% at December.

**Excluding `is_return_suspect = 1`:** these rows have unreliable returns. At Dec 2024, 148 of 2,325 rows are flagged. Their alpha values range from −121% to +7,134% (mean 231.6%), compared with −49.8% to +49.5% for the other rows, which is not believable for a portfolio.

| Dec 2024 snapshot (2,177 non-suspect rows unless noted) | Value |
|---|---:|
| `AUM-Weighted Alpha` (weighted, suspects excluded) | 1.448% |
| Simple mean of `active_alpha_ytd`, same rows | 0.879% |
| Weighted, suspects **included** (all 2,325 rows) | 1.668% |

The simple mean is lower because it gives a $50K account the same vote as a $50M account; large accounts outperformed by more. Including suspects inflates the result by about 0.22 percentage points, driven by a small number of impossible values.

## (d) Organic Growth Rate by client tier, 2024

| Tier | Ending AUM | AUM YoY % | Organic Growth Rate |
|---|---:|---:|---:|
| HNW | $2,548,521,154.33 | 19.64% | 1.18% |
| Retail | $533,452,497.89 | 19.13% | 9.87% |
| UHNW | $9,647,598,426.64 | 19.59% | 0.10% |
| **Total** | $12,729,572,078.86 | 19.58% | 0.73% |

**What it says:** net new client money is coming mainly from Retail, which grew 9.87% from flows alone. UHNW, which holds about 76% of AUM, added almost no net new money (0.10%). Since every tier's AUM grew about 19–20%, the difference between YoY and organic growth shows that most of 2024's growth came from **market performance, not new money**, especially for UHNW and HNW.

**What it does not tell you:**
- Whether the flows came from new clients or existing ones adding money, or how many clients left.
- In dollars, Retail's 9.87% is small (about $44M on a much smaller base), while UHNW's 0.10% is roughly $8M.
- Why flows differ: it shows the result, not the cause (advisor activity, pricing, client behaviour).
- The tier is each client's **current** tier, so clients who changed tier during the year are grouped by where they are now.
