# Claude Desktop's full critique response (2026-11-22)

Saved as returned by Claude Desktop for the prompt in `design_critique.md`. My decisions on each suggestion are logged in `design_critique.md`.

---

The report's structure is sound: an overview page plus a tier drill-through fits the MD's question, and Page 1's main title is a real insight. The two biggest problems are that blue means different things across Page 1, and Page 2 never answers "markets or new money?" for the tier you drill into.

## Page 1: Growth Drivers

**Chart choice**
- The waterfall is a good choice for splitting growth into net flows plus market change.
- The clustered bars in the region and tier charts don't work well. Market change is 15–40× larger than net flows, so the blue bars are slivers you can barely compare. The titles also make claims about total AUM added ("Northeast added the most"), and clustered bars don't show totals.
- Use a stacked horizontal bar per region or tier instead, with the net-flows segment first. One bar then shows both the total and the mix.

**Preattentive focus (one accent)**
- This is the main failure. In the region and tier charts, blue is Net Flows and gray is Market Change. In the waterfall, Net Flows is gray and blue is the Total.
- So the same color means two different measures on one page, and the waterfall's accent lands on the Total, which isn't the point of the title.
- Fix: pick one rule for the whole report. Blue = Net Flows everywhere, gray = Market Change, and a dark neutral for the Total. The tiny blue sliver in the waterfall then shows "new money barely moved it" without any extra explanation.

**Clutter**
- The definition sentence under the title is useful, but it's a full-width line of body text. Shorten it or move it to a footnote or tooltip.
- There's a leftover sort arrow under "AUM YoY %" in the KPI strip.
- Two legends repeat the same information. Label the first bar directly and drop the legends.

**Axes**
- Bars start at zero and the axes are hidden in favor of data labels. That's fine.
- The region and tier charts use different x-scales, though: UHNW's $1,572M bar and Northeast's $703M bar sit at similar visual lengths. Either share a scale or keep them clearly separate.

**Sorting**
- Regions are sorted descending by total. Good.
- Tiers run UHNW → HNW → Retail, which is both descending and the natural tier order. Good.

**Color and accessibility**
- Blue/gray is safe for colorblind viewers.
- The labels in the bottom two charts are too small, about 8pt; aim for 10pt or more.
- Retail's "$44M" and "$41M" labels overlap.
- Number formats are mixed: "$12.73bn", "$2.08B", "$2.01bn" and "$2,007M" all appear for related figures, and the waterfall shows $78M while the KPI shows $77.5M. Pick one unit style.
- "19.58%" is too precise. Use 19.6%.

**Layout**
- The tier chart is wider than the waterfall above it, which leaves a dead area at bottom-right and breaks the grid.
- Stack the region and tier charts on the right in equal sizes, and give the waterfall the left column as the hero visual.
- Nothing tells the MD that the tier bars can be drilled into. Add a small "Right-click a tier → Drill through" hint.

**Insight titles**
- The page title is strong, and the math checks: $2,007M ÷ $2,085M ≈ 96%.
- "New money vs market change" is a label, not an insight.
- The region title works, but "in 5 of 5 regions" reads awkwardly. "In every region" is cleaner.
- The tier title wastes its second half repeating the page-level 4% figure. It also misses the best finding on the page: Retail is the only tier where new money ($44M) exceeded market change ($41M).
- There are slicers for Year and Risk Profile. If these titles are static text boxes, changing a slicer leaves "2024" and "96%" on screen next to different numbers. Make them DAX-driven, or remove the slicers.

## Page 2: Segment Detail (HNW)

**Chart choice**
- The line chart comparing 2024 to 2023 is right for a monthly trend.
- The table is fine for listing named clients.
- The gap: the page doesn't split HNW's growth into net flows and market change, which is the MD's question. Add a small waterfall or stacked bar for the drilled tier. Fee Yield and Alpha are secondary and could shrink.

**Preattentive focus**
- Blue for 2024 and gray for 2023 is the right call.
- The table weakens it with three competing encodings: blue data bars, green icons and blue header highlights.

**Clutter**
- All ten status icons are green, so they carry no information. Remove them.
- The data bars run $7.8M to $8.3M, so they look almost identical and add little.
- Client IDs in parentheses add noise.
- Month labels are rotated diagonally. Use horizontal Jan–Dec.

**Axes**
- The line chart's y-axis starts near $2.0bn. That's acceptable for a line, since position carries the meaning, not bar length.
- For the data bars, confirm the minimum is set to 0 rather than "Lowest value."

**Sorting**
- The table is sorted by Ending AUM, descending. Correct.

**Color and accessibility**
- Green status icons are a red/green colorblind risk if any ever turn red. Use a text label or an arrow instead.
- Column headers are inconsistent: "region" is lowercase while "Client Name" is title case.
- "Top 10 clients by Ending AUM." ends with a stray period.
- "61.39 bps" should be 61 bps.
- "Alpha Signal: In line" doesn't say what it's in line with.

**Layout**
- About a quarter of the page below the visuals is empty.
- The KPI spacing is uneven: "Alpha Signal" floats far right while the left columns are cramped.
- "Keep all filters" is on, so a Risk Profile filter from Page 1 carries over silently. Add a subtitle that shows the active filters.

**Insight titles**
- "HNW clients — 2024 segment detail" is descriptive. If it's static text, it will also still say "HNW" when someone drills into UHNW or Retail.
- Make it dynamic and make it say something. Example: "HNW AUM grew ~$0.42bn (~20%) in 2024, almost all after May." That's consistent with Page 1's $25M + $393M.
- The table has its own story too: the top 10 grew 23%, faster than the segment's ~20%, and 7 of the 10 are in the Northeast.

## Top 3 changes, in priority order

1. Make each color mean one thing, and put the accent on the message. Use blue for Net Flows everywhere and gray for Market Change, and recolor the waterfall to match. Right now the color coding contradicts itself on the main page.
2. Swap the region and tier charts to stacked bars and rewrite their titles. The tier title should lead with the Retail finding: it's the only segment where new money beat the market. That's the most decision-relevant insight in the report, and it's currently hidden behind overlapping labels.
3. Rebuild Page 2 around the question and make titles dynamic. Add a net flows vs market change breakdown for the drilled tier, give it an insight title that changes with the tier, and remove the all-green icons. Also check that Page 1's titles respond to the slicers. If they don't, the report can show wrong numbers in its headline, and that's worse than any design issue.
