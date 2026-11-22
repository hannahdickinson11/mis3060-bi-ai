# Part B Build Guide: Page 1 "Growth Drivers"

Follow these steps in Power BI Desktop on Apporto. All the DAX is here, ready to copy. The layout follows `design/page1_wireframe.png`.

**Expected 2024 values** (from `data/growth_extract.csv`). If a card shows something else, stop and check before going on.

| Measure | 2024 |
|---|---:|
| Ending AUM | $12.73B |
| AUM YoY % | 19.58% |
| Net Flows | $77.5M |
| Market Change | $2.007B |
| Organic Growth Rate | 0.73% |
| AUM Change | $2.085B |

---

## Step 0. Set up the file
1. Open `hw07/ICE12 (1).pbix` and immediately use **File → Save as → `hw07/dashboard/hw07.pbix`**. Work only in this copy.
2. As in ICE 12 Task 1, go to **File → Options and settings → Options → Current file → Data load** and clear **Auto date/time**. Then apply the **Wildcat.json** theme (View → Themes → Browse for themes). The colors in this guide come from that theme: accent blue `#118DFF`, grey `#C8C8C8`, orange `#E66C37`.
3. Open the `_Measures` table and check that these measures exist: `Ending AUM`, `Ending AUM LY`, `AUM YoY %`, `Ending Clients`, `Avg AUM per Client`, `Fee Yield (bps)`, `Organic Growth Rate`, `AUM-Weighted Alpha`, `Alpha Signal`, `Top 10 Client Share`, `Total Fees`, `Net Flows`. Copy any that are missing from `hw06/powerbi/measures.md`.

## Step 1. New measures
Create each one with **Home → New measure**, in the `_Measures` table.

```DAX
Market Change = ( [Ending AUM] - [Ending AUM LY] ) - [Net Flows]
```
```DAX
AUM Change = [Ending AUM] - [Ending AUM LY]
```
```DAX
Flow Share of Growth = DIVIDE ( [Net Flows], [AUM Change] )
```
**Formats:** currency for `Market Change` and `AUM Change`, and percentage with 1 decimal for `Flow Share of Growth`.

`AUM Change` is used to sort the bar charts and in the alt text.

## Step 2. Waterfall helper table
1. Choose **Home → Enter data**, name the table `Growth Component`, and enter:

   | Component | Sort |
   |---|---|
   | Net Flows | 1 |
   | Market Change | 2 |

2. Select the `Component` column, then choose **Column tools → Sort by column → Sort**.
3. Don't create a relationship. The table is meant to stay disconnected.
4. Add this measure:
```DAX
Growth Component Value =
SWITCH (
    SELECTEDVALUE ( 'Growth Component'[Component] ),
    "Net Flows", [Net Flows],
    "Market Change", [Market Change]
)
```

## Step 3. Title, subtitle and alt-text measures
```DAX
Insight Title =
VAR Yr     = SELECTEDVALUE ( dim_date[year] )
VAR LY     = [Ending AUM LY]
VAR Chg    = [Ending AUM] - LY
VAR Flows  = [Net Flows]
VAR Mkt    = [Market Change]
VAR MktLed = ABS ( Mkt ) >= ABS ( Flows )
VAR Share  = DIVIDE ( IF ( MktLed, Mkt, Flows ), Chg )
RETURN
    SWITCH (
        TRUE (),
        ISBLANK ( Yr ) || ISBLANK ( LY ),
            "Select a single year (2021–2024)",
        Chg >= 0,
            IF ( MktLed, "Market change", "Net new money" ) & " drove "
                & FORMAT ( Share, "0%" ) & " of " & Yr & "'s "
                & FORMAT ( Chg / 1e9, "$0.00" ) & "B AUM growth",
        "AUM fell " & FORMAT ( -Chg / 1e9, "$0.00" ) & "B in " & Yr
            & ": market change " & FORMAT ( Mkt / 1e9, "$0.00" ) & "B, net flows +"
            & FORMAT ( Flows / 1e6, "$0" ) & "M"
    )
```
The 2024 result should read: **"Market change drove 96% of 2024's $2.08B AUM growth"**.

Insight titles for the two bar charts. These are dynamic, so they stay true when the year changes:
```DAX
Tier Bars Title =
VAR Yr      = SELECTEDVALUE ( dim_date[year] )
VAR Chg     = [AUM Change]
VAR TopTier = MAXX ( TOPN ( 1, VALUES ( dim_client[client_tier] ), [AUM Change], DESC ), dim_client[client_tier] )
VAR TopVal  = MAXX ( VALUES ( dim_client[client_tier] ), [AUM Change] )
RETURN
    IF (
        ISBLANK ( Yr ),
        "Select a single year",
        TopTier & IF ( TopVal > 0, " added the most AUM in ", " lost the least AUM in " ) & Yr
            & IF (
                Chg > 0,
                "; net flows were " & FORMAT ( [Flow Share of Growth], "0%" ) & " of total growth",
                "; firm AUM fell " & FORMAT ( -Chg / 1e6, "$#,0" ) & "M"
            )
    )
```
```DAX
Region Bars Title =
VAR Yr        = SELECTEDVALUE ( dim_date[year] )
VAR TopRegion = MAXX ( TOPN ( 1, VALUES ( dim_advisor[region] ), [AUM Change], DESC ), dim_advisor[region] )
VAR TopVal    = MAXX ( VALUES ( dim_advisor[region] ), [AUM Change] )
VAR N         = COUNTROWS ( VALUES ( dim_advisor[region] ) )
VAR MktLed    = COUNTROWS ( FILTER ( VALUES ( dim_advisor[region] ), ABS ( [Market Change] ) >= ABS ( [Net Flows] ) ) )
RETURN
    IF (
        ISBLANK ( Yr ),
        "Select a single year",
        TopRegion & IF ( TopVal > 0, " added the most AUM in ", " lost the least AUM in " ) & Yr
            & "; market change outweighed net flows in " & MktLed & " of " & N & " regions"
    )
```
> Both bar titles were rewritten after testing 2022: the first versions claimed "every region grew" and showed a negative "% of growth" when AUM fell, and said "Retail added the most AUM" in 2022 when every tier lost AUM (Retail lost the least).

Alt text (dynamic, applied with fx in Step 8):
```DAX
Alt Ending AUM =
"Card: Ending AUM " & FORMAT ( [Ending AUM] / 1e9, "$0.00" ) & "B at the end of "
    & SELECTEDVALUE ( dim_date[year] ) & ", " & FORMAT ( [AUM YoY %], "+0.0%;-0.0%" )
    & " versus the prior year."
```
```DAX
Alt Net Flows =
"Card: Net flows of " & FORMAT ( [Net Flows] / 1e6, "$#,0.0" ) & "M in "
    & SELECTEDVALUE ( dim_date[year] ) & " (deposits minus withdrawals)."
```
```DAX
Alt Market Change =
"Card: Market change of " & FORMAT ( [Market Change] / 1e6, "$#,0.0" ) & "M in "
    & SELECTEDVALUE ( dim_date[year] ) & ", the AUM change not explained by net flows."
```
```DAX
Alt Organic Growth =
"Card: Organic growth rate of " & FORMAT ( [Organic Growth Rate], "0.00%" ) & " in "
    & SELECTEDVALUE ( dim_date[year] ) & ", net flows as a share of prior-year ending AUM."
```
```DAX
Alt Waterfall =
"Waterfall chart of " & SELECTEDVALUE ( dim_date[year] ) & " AUM change: net flows "
    & FORMAT ( [Net Flows] / 1e6, "$#,0.0" ) & "M plus market change "
    & FORMAT ( [Market Change] / 1e6, "$#,0.0" ) & "M equals a total change of "
    & FORMAT ( [AUM Change] / 1e6, "$#,0.0" ) & "M."
```
```DAX
Alt Tier Bars =
"Clustered bar chart of " & SELECTEDVALUE ( dim_date[year] )
    & " net flows and market change by client tier, largest AUM change first. "
    & CONCATENATEX (
        VALUES ( dim_client[client_tier] ),
        dim_client[client_tier] & ": net flows " & FORMAT ( [Net Flows] / 1e6, "$#,0.0" )
            & "M, market change " & FORMAT ( [Market Change] / 1e6, "$#,0.0" ) & "M",
        "; ", [AUM Change], DESC
    ) & "."
```
```DAX
Alt Region Bars =
"Clustered bar chart of " & SELECTEDVALUE ( dim_date[year] )
    & " net flows and market change by advisor region, largest AUM change first. "
    & CONCATENATEX (
        VALUES ( dim_advisor[region] ),
        dim_advisor[region] & ": net flows " & FORMAT ( [Net Flows] / 1e6, "$#,0.0" )
            & "M, market change " & FORMAT ( [Market Change] / 1e6, "$#,0.0" ) & "M",
        "; ", [AUM Change], DESC
    ) & "."
```

## Step 4. Slicers
1. **S1 Year:** add a slicer with `dim_date[year]`, style **Dropdown**, and turn **Single select** on under Slicer settings → Selection.
   - In the Filters pane, under *Filters on this visual*, set `year` to **2021, 2022, 2023, 2024** (remove 2020).
   - Select **2024**.
2. **S2 Risk profile:** add a slicer with `dim_client[risk_profile]`, style **Dropdown**, multi select, and leave it on **All**.

## Step 5. Title, caveat, and KPI cards
1. **P1-0 title:** use a Card (new) with `[Insight Title]`. Turn the category label off and set a large bold font, left-aligned.
2. **P1-C caveat:** add a text box (Insert → Text box) with this text:
   > *Market Change = the year's AUM change minus net flows. It includes investment performance **and** fees and other cash effects, so it is not pure market return.*
3. **P1-1 to P1-4:** add four cards with `[Ending AUM]`, `[Net Flows]`, `[Market Change]` and `[Organic Growth Rate]`.
   - Display units: Billions for Ending AUM and Market Change, Millions for Net Flows.
   - On the Ending AUM card, add `[AUM YoY %]` as a **Reference label**. If your Card (new) has no reference labels, put `[AUM YoY %]` in a second card directly below it, or turn on a subtitle with fx = `[AUM YoY %]`.

## Step 6. Waterfall (P1-5)
1. **Category:** `'Growth Component'[Component]`. **Y-axis:** `[Growth Component Value]`.
2. Sort by `Component` ascending, so Net Flows comes first, then Market Change, then Total.
3. Data labels **On**, display units Millions. Turn gridlines off.
4. **Title:** *"New money vs market change, {year}"*. Or put fx on the title and use `[Insight Title]`, but then delete the P1-0 card so the headline isn't shown twice.
5. **Colors (limitation):** the waterfall only colors bars by *Increase / Decrease / Total*, not by category. So Net Flows can't be blue while Market Change is grey. Set Increase to grey `#C8C8C8`, Decrease to orange `#E66C37`, and Total to accent blue `#118DFF`. Note this in `design_plan.md` and in the Part E critique; it changes the Section 3 color plan for this one visual.

## Step 7. Clustered bar charts (P1-6, P1-7)
1. **P1-6:** Y-axis `dim_client[client_tier]`, X-axis `[Net Flows]` and `[Market Change]`.
2. **P1-7:** Y-axis `dim_advisor[region]`, same two measures.
3. **Colors:** Net Flows accent blue `#118DFF`, Market Change grey `#C8C8C8` (Format → Bars → Colors), the same blue-plus-grey approach as ICE 12 Task 3.
4. **Sorting:** drag `[AUM Change]` into the **Tooltips** well, then use **More options (…) → Sort axis → AUM Change**, **Sort descending**.
5. Data labels on, display units Millions, gridlines off, X-axis starting at 0 (the default).
6. **Titles:** Format → General → Title → fx → Field value → `[Tier Bars Title]` / `[Region Bars Title]`.

## Step 8. Alt text (every visual)
For each visual, go to **Format → General → Alt text → fx → Format style: Field value** and pick its measure.

| Visual | Alt text |
|---|---|
| P1-0 title card | fx → `[Insight Title]` |
| P1-1 – P1-4 cards | fx → `[Alt Ending AUM]`, `[Alt Net Flows]`, `[Alt Market Change]`, `[Alt Organic Growth]` |
| P1-5 waterfall | fx → `[Alt Waterfall]` |
| P1-6 / P1-7 bars | fx → `[Alt Tier Bars]` / `[Alt Region Bars]` |
| S1 / S2 slicers | Static: "Year slicer, single select, set to 2024" / "Risk profile slicer, all selected" |
| P1-C caveat | Static: the caveat text itself |

## Step 9. Tooltip page (TT)
1. Add a new page called `TT Segment`. Under Page information, turn **Allow use as tooltip** on; set Canvas settings → Type → **Tooltip**.
2. Add four small cards: `[Ending AUM]`, `[AUM YoY %]`, `[Organic Growth Rate]`, `[Flow Share of Growth]`.
3. On P1-6 and P1-7, go to Format → General → Tooltips → Type **Report page** → Page **TT Segment**.
4. Hide the TT page (right-click the page tab → Hide page).

## Step 10. Edited interactions
1. Select P1-6, then **Format → Edit interactions**:
   - On P1-7, click the **Filter** icon.
   - On the P1-0 title card, click **None**.
2. Select P1-7: set P1-6 to **Filter** and the P1-0 title card to **None**.
3. Leave everything else at its default.
4. Turn Edit interactions off.

## Step 11. Check and save
1. **Click-through check:**
   - Click 2024 → 2023 → 2022 and check that every title and card still reads correctly. 2022 should show "AUM fell $0.70B…".
   - Set the slicer back to **2024**.
2. **Value check:** compare every card with the expected values at the top of this guide.
3. **Save** `dashboard/hw07.pbix`. Screenshot the whole page with the slicers visible and save it as `dashboard/page1.png`.
4. **Send me:**
   - a screenshot of Page 1
   - any measure that errors or shows an unexpected value

   I'll check the numbers, then fill in `design_plan.md` Section 6 with what you actually ended up using.
