# HW7: Where Did 2024 Growth Come From?

A two-page Power BI report for Wildcat Capital's managing director. It answers: *"Where did 2024 growth come from, markets or new money, and which client segments and regions drove it?"*

**Answer in one line:** AUM grew $2.08B (+19.6%) to $12.73B in 2024. 96% of that was market change ($2.007B) and only $78M was net new money. UHNW and the Northeast added the most dollars; Retail is the only tier where new money mattered (about half of its growth).

## Structure

```
hw07/
├── README.md                     this file
├── design_plan.md                Part A: audience, wireframes, visual choices, interactions, prototypes, formatting measure
├── design/                       wireframes (page1_wireframe.png, page2_wireframe.png)
│   └── prototypes/               three flows-vs-market prototype charts
├── data/
│   ├── growth_extract.csv        75 rows: year × client tier × region
│   └── README.md                 each column labelled balance or flow
├── scripts/
│   ├── 00_make_extract.py        builds data/growth_extract.csv (pandas)
│   └── 01_reconcile_kpis.py      reconciles Power BI values to pandas + extract check
├── dashboard/
│   ├── hw07.pbix                 the report (Growth Drivers, Segment Detail, hidden TT Segment tooltip page)
│   ├── page1.png                 Page 1, 2024 / All, Filters pane visible
│   ├── page2.png                 Page 2 after an HNW drill-through, drill filters visible
│   └── part_b_build_guide.md     step-by-step build notes with all DAX
├── reports/
│   ├── powerbi_values_query.dax  DAX query used to export the Power BI values
│   ├── powerbi_values.csv        values read from Power BI (measure, slice, value)
│   ├── kpi_reconciliation.csv    Power BI vs pandas: 43 rows, all match
│   └── extract_check.csv         extract vs pandas: 32 rows, all match
├── claude/
│   ├── design_critique.md        Part E log: 7 suggestions, decisions, 2 Claude errors, before/after
│   ├── critique_response.md      Claude Desktop's full critique reply
│   ├── before.png, after.png     the accepted change (waterfall Total recolored)
└── executive_summary.md          Part F
```

## How to run

From the repo root, with the course environment (pandas installed):

```bash
python hw07/scripts/00_make_extract.py
python hw07/scripts/01_reconcile_kpis.py
```

Both scripts read the same cleaned CSVs as Assignment 6 (`hw06/02_Data/Cleaned/`). The first writes `data/growth_extract.csv`. The second reads `reports/powerbi_values.csv` and writes `reports/kpi_reconciliation.csv` and `reports/extract_check.csv`.

**Getting the Power BI values:** open `dashboard/hw07.pbix`, go to DAX query view, and run `reports/powerbi_values_query.dax`. Result 1 has the numeric values and Result 2 has Alpha Signal. Copy both into `reports/powerbi_values.csv`.

## How Claude was used

- **Claude Code** wrote both scripts, the data README, the wireframes and the three prototype images, and drafted `design_plan.md` and the DAX measures. It then guided the Power BI build step by step from my screenshots. The brief asks for Claude Desktop to draft the scripts and prototypes; I used Claude Code for both, and I note it here and in `design_plan.md`.
- **Claude Desktop** was used for the design critique (Part E) and the executive summary draft (Part F).
- I built both report pages in Power BI Desktop myself, checked every number against the extract, and made the design decisions recorded in `design_plan.md`.

## Claude Code review of the scripts

### `00_make_extract.py`

| What was flagged | What I did |
|---|---|
| **Region path.** Both `fact_portfolio_snapshot` and `dim_client` have an `advisor_id`. The extract must use the same one as the model, or region totals won't reconcile. | Checked my HW5 model: the fact tables' own `advisor_id → dim_advisor` relationships are active, and `dim_client → dim_advisor` is inactive. The script joins on each fact table's own `advisor_id`. |
| **2020 has no prior year.** Filling `ending_aum_ly` with 0 would make 2020's market change equal its whole AUM ($8.1B). | Left `ending_aum_ly` and `market_change` blank (NaN) for the 15 rows of 2020, and kept the rows, as the brief asks. |
| **"December snapshot" is an assumption.** Snapshots are dated the 1st of each month. | The script takes each year's last snapshot date (the same as `LASTNONBLANK` in `[Ending AUM]`) and raises an error if it isn't in December. |
| **Orphan keys** would silently drop rows from tier/region totals. | The script raises an error if any fact row has no tier or region. None were found. |
| **Empty combinations.** A tier × region × year with no data would be missing from the grid. | The script builds the full 75-row grid first and asserts 75 rows. Every combination has data, and `net_flows` has no blanks. |

### `01_reconcile_kpis.py` (extends the HW6 `01_reconcile_measures.py`)

| What was flagged | What I did |
|---|---|
| **Silent region orphans.** If a fact row's `advisor_id` had no region, it would drop out of every region slice. Power BI would show it under (Blank), so the totals could still "match" while missing money. | Added a check that raises an error if any snapshot, fee or transaction row has no region. None do. |
| **Market Change blanks.** DAX treats BLANK as 0 in subtraction. | `market_change()` mirrors that: (Ending AUM − LY) − Net Flows with blanks as 0, and is blank only when all three are blank. |
| **Tolerance for the new dollar measures.** HW6 used 0.01 for currency and 0.0001 for everything else. Net Flows fell into "everything else" in HW6. | Kept both tolerances. Net Flows and Market Change are dollar amounts, so they now use the currency tolerance (0.01). The largest difference in the run is $0.0000095, so they would also pass the stricter 0.0001. |
| **Withdrawal sign.** Net Flows assumes withdrawal amounts are stored as positive numbers. | Checked: every Withdrawal amount is positive ($506.77 to $99,996.46), the same assumption as the DAX `[Net Flows]` measure. |

## Verification (Part D)

**Reconciliation:** 43 of 43 rows match (`reports/kpi_reconciliation.csv`).
- **Page 1 cards, firm level, 2024:** Ending AUM, Ending AUM LY, AUM YoY %, Net Flows, Market Change, Organic Growth Rate
- **Flows/market split** (Ending AUM, Ending AUM LY, Net Flows, Market Change) for each tier (HNW, Retail, UHNW) and each region (Northeast, Mid-Atlantic, Southeast, West, Midwest)
- **Page 2 cards for HNW:** Ending AUM, Ending Clients, Avg AUM per Client, Fee Yield (bps), AUM-Weighted Alpha, Alpha Signal

The largest absolute difference is $0.0000095 (floating-point rounding).

**Extract check:** 32 of 32 values match (`reports/extract_check.csv`). The 2024 rows of `data/growth_extract.csv`, summed to each tier and each region, match the pandas values in the reconciliation for Ending AUM, Ending AUM LY, Net Flows and Market Change. Those pandas values match Power BI, so the extract, pandas and Power BI all agree. The firm total of the extract (sum of all 15 rows for 2024) also matches the Page 1 cards: $12,729,572,078.86 Ending AUM, $77,513,055 Net Flows and $2,007,087,287 Market Change.

### Model fix found while building

ICE12's `AUM-Weighted Alpha` showed **0.46%** for 2024. It averaged all twelve months and included the `is_return_suspect` rows. I replaced it with the HW6 last-snapshot version (suspect rows excluded), which gives **1.45%**. Alpha Signal stays "In line".

## Filter audit (Part D, item 4)

No report-level ("Filters on all pages") filters exist, and no page-level ("Filters on this page") filters exist on any page. The `page1.png` and `page2.png` screenshots show both sections empty.

### Page 1: Growth Drivers

| Filter or interaction | Where | Setting | Changes a number silently? |
|---|---|---|---|
| Year slicer | Visual (slicer) | `dim_date[year]`, single select, saved = 2024 | No. It is visible and named in every title. |
| Year slicer's own filter | Visual-level, on the slicer | `year` is 2021, 2022, 2023 or 2024 (2020 removed) | No. It only limits the choices. 2020 has no prior year, so Market Change would show the whole $8.1B balance. |
| Risk Profile slicer | Visual (slicer) | `dim_client[risk_profile]`, multi select, saved = All | No. It is visible. |
| Slicer sync | View → Sync slicers | Year and Risk Profile sync to Segment Detail and TT Segment (hidden there) | No. It keeps Page 2 and the tooltip on the same year as Page 1. |
| Visual-level field filters | Every chart and table | Only the fields each visual uses, all "is (All)" | No |
| Tier bars → Region bars | Edited interaction | **Filter** (default was Highlight) | No. Clicking a tier redraws the region bars for that tier. |
| Region bars → Tier bars | Edited interaction | **Filter** (default was Highlight) | No |
| Bars → KPI table, waterfall | Interaction | Filter (default) | No. They show the clicked segment, and the selected bar stays highlighted. |
| Bars → headline | Interaction | No interaction setting was reachable for the headline | **It did, at first; fixed.** See below. |
| Tooltip page (TT Segment) | Report-page tooltip on both bar charts | Inherits the hovered bar's tier or region plus the slicers | No. UHNW tooltip = $9.65bn, 19.59%, 0.10%, 0.5%, matching the extract. |

### Page 2: Segment Detail (drill-through)

| Filter or interaction | Where | Setting | Changes a number silently? |
|---|---|---|---|
| Drill-through field | Page | `dim_client[client_tier]`, **Keep all filters: On** | No. The tier is named in the subtitle and the trend title. |
| Carried filters | Drill-through well | `year is 2024` (and Risk Profile, if set) | **It did, at first; fixed.** See below. |
| Top 10 table | Visual-level | `Client Name` Top N = 10 by `[Ending AUM]` | No. It is intended and named in the title. HNW top 10 total $80,015,275 = 3.14% of $2.55B (Top 10 Client Share). |
| Edited interactions | — | None edited | — |

### Problems the audit found, and the fixes

1. **The headline changed when a bar was clicked.** Clicking HNW changed the firm headline to "Market change drove 94% of 2024's $0.42B AUM growth": HNW's numbers presented as the firm's. The headline visual had no reachable interaction setting, so the measure now ignores bar clicks: `Insight Title Firm = CALCULATE ( [Insight Title], REMOVEFILTERS ( dim_client[client_tier] ), REMOVEFILTERS ( dim_advisor[region] ) )`. It still follows the Year and Risk Profile slicers.
2. **Page 2 lost the year when opened from its tab.** HNW Fee Yield showed **61.68**, the 2020–2024 value, instead of **61.39**. Ending AUM, Clients and Alpha still looked right, because they use the last snapshot (Dec 2024) either way. Keep all filters only applies at the moment of a drill-through. Fixed by syncing the Year and Risk Profile slicers to Segment Detail.
3. **Titles that were wrong in other years** (found by clicking through 2022 and 2023):
   - The waterfall title had "2024" typed in. It is now "New money vs market change".
   - The copied region chart was sorted by Net Flows instead of AUM Change, so in 2023 its title ("Northeast added the most AUM") didn't match the top bar. It is now sorted by AUM Change.
   - The first versions of the tier and region titles claimed "every region grew" and "Retail added the most AUM" in 2022, when every tier lost AUM. They now use "lost the least" wording and a falling-AUM branch, and show "Select a single year" if no single year is selected.

   2022 now reads: *"AUM fell $0.70B in 2022: market change -$0.78B, net flows +$76M"* / *"Retail lost the least AUM in 2022; firm AUM fell $702M"* / *"Midwest added the most AUM in 2022; market change outweighed net flows in 5 of 5 regions"*.

## Power BI limitations on Apporto

Card, Card (new) and KPI visuals all rendered **blank** in Power BI Desktop on Apporto: the title and fields appeared, but no value. Tables, slicers, charts and buttons rendered normally. So:
- The Page 1 and Page 2 KPI cards are one-row tables with large bold values.
- The dynamic headline and Page 2 subtitle are tables with a hidden header.
- The Market Change caveat is a blank button with typed text, because typing into a text box on the canvas didn't work in Apporto.

The design reasoning for cards (one glance, one row of headline numbers) still applies; see `design_plan.md`, Section 3.
