# Executive Summary: Where 2024 Growth Came From

Wildcat's AUM grew $2,084.6M (+19.6%) in 2024, from $10,645.0M to $12,729.6M. Almost all of it was market change, not new money: market change added $2,007.1M (96% of the growth), while net flows added only $77.5M, an organic growth rate of 0.73%.

UHNW clients drove most of it, adding $1,580.6M (76% of the growth), nearly all market change; their net flows were only $8.1M. HNW added $418.4M (20%), also mostly market change. Retail is the exception: its $44.2M of net flows was larger than its $41.5M market change, and it brought in 57% of the firm's new money while holding about 4% of AUM. Every tier grew at nearly the same rate (19.1% to 19.6%), which points to a firm-wide lift.

By region, the Northeast ($735.3M) and Mid-Atlantic ($621.0M) produced 65% of the growth, and market change outweighed net flows in all five regions.

**Takeaway:** outside Retail, Wildcat brought in very little new money. In a flat year, growth would have been close to the 0.73% organic rate.

**Limitation:** Market Change is a residual. It includes fees and other cash effects as well as investment performance, so it is not pure market return and can't separate performance from fee drag.

---

## How this was written

I gave Claude Desktop the verified 2024 values from `reports/kpi_reconciliation.csv` as text (no screenshot) and asked for a 150–200 word summary answering the business question, with one limitation. I then edited the draft:
- **"Markets, not new money, drove it" became "market change, not new money".** Market Change includes fees and other cash effects (the Page 1 caveat), so calling it "markets" overstates what the measure shows.
- **HNW's growth was corrected from $418.3M to $418.4M** (see the audit table).
- I rewrote the takeaway to tie it to the organic growth rate, so it rests on a reconciled number rather than an opinion.

## Audit table

Every number and claim in the summary is listed below, with the measure and the reconciliation row that supports it. All reconciliation rows are for 2024 and match Power BI (`reports/kpi_reconciliation.csv`, 43/43). Derived figures are computed from those rows.

| # | Number or claim in the summary | Measure(s) | Reconciliation row(s) | Check | Status |
|---|---|---|---|---|---|
| 1 | AUM grew $2,084.6M | Ending AUM − Ending AUM LY | `Ending AUM, year=2024` ($12,729,572,079); `Ending AUM LY, year=2024` ($10,644,971,737) | 12,729.6 − 10,645.0 = 2,084.6 | Correct |
| 2 | +19.6% | AUM YoY % | `AUM YoY %, year=2024` (0.19583) | 19.58% → 19.6% | Correct |
| 3 | from $10,645.0M to $12,729.6M | Ending AUM LY, Ending AUM | same as #1 | — | Correct |
| 4 | Market change added $2,007.1M | Market Change | `Market Change, year=2024` ($2,007,087,287) | — | Correct |
| 5 | 96% of the growth | Market Change ÷ (Ending AUM − LY) | #4 and #1 | 2,007.1 ÷ 2,084.6 = 96.3% | Correct |
| 6 | Net flows added only $77.5M | Net Flows | `Net Flows, year=2024` ($77,513,055) | — | Correct |
| 7 | Organic growth rate of 0.73% | Organic Growth Rate | `Organic Growth Rate, year=2024` (0.00728) | — | Correct |
| 8 | "market change, not new money" | Market Change vs Net Flows | #4, #6 | 2,007.1 vs 77.5 | **Corrected**: Claude wrote "Markets"; Market Change also includes fees and cash effects |
| 9 | UHNW added $1,580.6M | Ending AUM − Ending AUM LY | `Ending AUM, tier=UHNW` ($9,647,598,427); `Ending AUM LY, tier=UHNW` ($8,067,021,938) | 9,647.6 − 8,067.0 = 1,580.6 | Correct |
| 10 | UHNW = 76% of the growth | — | #9 ÷ #1 | 1,580.6 ÷ 2,084.6 = 75.8% | Correct |
| 11 | UHNW net flows only $8.1M | Net Flows | `Net Flows, tier=UHNW` ($8,101,601) | — | Correct |
| 12 | UHNW growth "nearly all market change" | Market Change | `Market Change, tier=UHNW` ($1,572,474,887) | 1,572.5 ÷ 1,580.6 = 99.5% | Correct |
| 13 | HNW added $418.4M | Ending AUM − Ending AUM LY | `Ending AUM, tier=HNW` ($2,548,521,154); `Ending AUM LY, tier=HNW` ($2,130,154,150) | 2,548.52 − 2,130.15 = 418.37 → 418.4 | **Corrected**: Claude wrote $418.3M |
| 14 | HNW = 20% of the growth | — | #13 ÷ #1 | 418.4 ÷ 2,084.6 = 20.1% | Correct |
| 15 | HNW "mostly market change" | Market Change, Net Flows | `Market Change, tier=HNW` ($393,139,598); `Net Flows, tier=HNW` ($25,227,406) | 393.1 vs 25.2 (94% market change) | Correct |
| 16 | Retail net flows $44.2M | Net Flows | `Net Flows, tier=Retail` ($44,184,048) | — | Correct |
| 17 | Retail market change $41.5M | Market Change | `Market Change, tier=Retail` ($41,472,802) | — | Correct |
| 18 | Retail's net flows larger than its market change | Net Flows vs Market Change | #16, #17 | 44.2 > 41.5 | Correct |
| 19 | Retail brought in 57% of the firm's new money | Net Flows | #16 ÷ #6 | 44.2 ÷ 77.5 = 57.0% | Correct |
| 20 | Retail holds about 4% of AUM | Ending AUM | `Ending AUM, tier=Retail` ($533,452,498) ÷ #1's Ending AUM | 533.5 ÷ 12,729.6 = 4.2% | Correct |
| 21 | Every tier grew 19.1% to 19.6% | AUM YoY % (from Ending AUM and LY) | `Ending AUM` / `Ending AUM LY` for each tier | Retail 19.13%, UHNW 19.59%, HNW 19.64% | Correct (HNW rounds to 19.6%) |
| 22 | Northeast $735.3M | Ending AUM − Ending AUM LY | `Ending AUM, region=Northeast` ($4,530,738,631); `Ending AUM LY, region=Northeast` ($3,795,456,742) | 4,530.7 − 3,795.5 = 735.3 | Correct |
| 23 | Mid-Atlantic $621.0M | Ending AUM − Ending AUM LY | `Ending AUM, region=Mid-Atlantic` ($3,763,923,872); `Ending AUM LY, region=Mid-Atlantic` ($3,142,940,677) | 3,763.9 − 3,142.9 = 621.0 | Correct |
| 24 | Northeast + Mid-Atlantic = 65% of growth | — | (#22 + #23) ÷ #1 | 1,356.3 ÷ 2,084.6 = 65.1% | Correct |
| 25 | Market change outweighed net flows in all five regions | Market Change, Net Flows | `Market Change` and `Net Flows` for each region | NE 703.1/32.2, MA 598.8/22.2, SE 479.3/16.8, W 167.3/4.6, MW 58.7/1.8 | Correct |
| 26 | In a flat year, growth would be close to 0.73% | Organic Growth Rate | #7 | With market change ≈ 0, AUM change ≈ net flows = 0.73% of starting AUM | Correct (an inference from the measure's definition, not a forecast) |
| 27 | Limitation: Market Change includes fees and cash effects | Market Change definition | `design_plan.md` Section 1; Page 1 caveat | — | Correct (stated limitation) |
