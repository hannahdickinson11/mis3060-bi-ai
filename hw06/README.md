# HW6: DAX Measure Library — AUM & Performance

MIS3060 Business Intelligence with AI · Villanova University · Hannah Dickinson

This folder adds a library of 12 DAX measures to the posted Wildcat Capital star model, reconciles every measure to an independent pandas calculation, answers four filter-context design questions, and documents one measure drafted with Claude Desktop and verified by me.

## Folder structure

```
hw06/
├── README.md                        this file
├── powerbi/
│   ├── hw06.pbix                    posted model + _Measures_ table + "Measures" report page (Part A)
│   └── measures.md                  DAX, pattern and meaning for every measure (Part A) + design questions (Part C)
├── scripts/
│   └── 01_reconcile_measures.py     recomputes every measure in pandas and compares to Power BI (Part B)
├── reports/
│   ├── powerbi_values.csv           Power BI values exported from DAX query view (measure, slice, value)
│   └── measure_reconciliation.csv   powerbi_value vs pandas_value for every row, with abs_diff and match
├── claude/
│   ├── model_metadata.md            INFO.VIEW exports: columns, relationships, measures (Part D)
│   ├── dax_session.md               my Claude Desktop prompt and its full response for Top 10 Client Share
│   └── verification.md              how I tested and judged Claude's measure
├── 00_Project Briefing/             assignment brief and DAX guide
└── 02_Data/Cleaned/                 the instructor's Wildcat Capital Clean CSVs (not committed: the repo ignores CSVs) and the starter .pbix
```

## How to run the reconciliation

From the `hw06` folder, in the conda `base` environment (pandas 3.1):

```bash
python scripts/01_reconcile_measures.py
```

The script reads `02_Data/Cleaned/` and `reports/powerbi_values.csv`, recomputes each measure in pandas without reading anything from Power BI, and writes `reports/measure_reconciliation.csv`. Tolerance is 0.01 for currency measures and 0.0001 for ratios, bps and counts; `Alpha Signal` is compared as text, and blank-vs-blank counts as a match.

**Result: 89 rows compared, 89 match, 0 mismatches.** Every row matched on the first run, so there were no mismatches to fix.

Slices covered:
- every measure at the **grand total** (14 rows, including `AUM (naive SUM)`)
- measures 0, 1, 4, 6–10 **by year**, 2020–2024 (45 rows)
- measures 1, 3, 4, 7–11 **by client tier for 2024** (27 rows)
- measure 5 for **December 2024** (3 rows)

`AUM (naive SUM)` matches in both tools ($566,681,084,542.48 at the grand total), which shows both tools make the same mistake. Three 2020 rows (`Ending AUM LY`, `AUM YoY %`, `Organic Growth Rate`) are blank in both tools because there is no 2019 data.

## Power BI model (Part A)

Built on the Apporto virtual desktop from the posted `Wildcat_Star_Model.pbix`, saved as `hw06.pbix`.

- **Measures:** 12 HW6 measures plus the ICE base measures (`Total Fees`, `Net Flows`, `Effective Fee Rate (bps)`) live in the `_Measures_` table. Every measure is formatted: currency and percentages with 2 decimals, Fee Yield as a 2-decimal number (bps), Ending Clients as a whole number.
- **`AUM (naive SUM)`** is in the model only to show the trap; it is not on any report visual.
- **Measures page:** a KPI row (Ending AUM, Ending Clients, Avg AUM per Client, Top 10 Client Share), a table by `dim_date[year]`, and a table by `dim_client[client_tier]` with a **visual-level** filter on `dim_date[year]` = 2024.
- **Date table:** `dim_date` is marked as the date table on `date`.
- `hw06.pbix` is about 21 MB, under GitHub's 100 MB limit.

## Workflow and AI use

- **Claude Desktop** drafted `Top 10 Client Share` (Part D, see `claude/`) and drafted `scripts/01_reconcile_measures.py` from a prompt that gave the folder layout, grain, every measure's definition, the slices and the comparison rules.
- **I** ran the script in VS Code, built every measure and the report page in Power BI myself, and ran every DAX test and export query.
- **Claude Code** reviewed the script before I committed (findings below), guided the Power BI steps and checked my screenshots, helped write the Claude Desktop prompts, reshaped my four DAX query results into `powerbi_values.csv`, and helped draft `measures.md` (including the Part C answers, from pandas checks it ran on the CSVs), `verification.md` and this README. I reviewed and edited each of these.

## What Claude Code flagged and what I did (`scripts/01_reconcile_measures.py`)

Claude Code found no correctness bugs: the LY/PM date shifts, blank handling, last-snapshot logic, alpha suspect filter, Top 10 tie-breaker and tolerances all match the DAX.

| # | Claude Code flagged | What I did |
|---|---|---|
| 1 | `warn_missing_expected` checks every measure in `MEASURE_FUNCS` for the "Total" slice, including the helpers `Total Fees` and `Net Flows`, so it prints a false "2 expected rows missing" note | No change. Confirmed on the run: the note appears, but those helpers are not required slices, and all 89 required rows are compared |
| 2 | `client_id` is read as text, so the Top 10 tie-breaker sorts IDs alphabetically while DAX sorts numerically | No change. It only matters for an exact tie at rank 10; at Dec 2024, rank 10 is $74.42M and rank 11 is $72.11M |
| 3 | Top 10 ranks rows, not clients, which is correct only because the snapshot grain is one row per client per month | No change. Grain confirmed in pandas: no duplicate `client_id` + `snapshot_date` |
| 4 | `dim_date.csv` is only checked for existence; the model date range is hard-coded as 2020-01-01 to 2024-12-31 | No change. That range matches `dim_date` (1,827 days) |

## Notes
- **Relationships:** the starter model has **12** relationships, not the 11 the brief mentions (plus two hidden auto date/time tables). The extra one is `dim_security[benchmark_id]` → `dim_benchmark`, which no HW6 measure uses, so I left it as posted.
- **Cards:** the Card visual rendered blank on Apporto's Power BI version (its Format pane loaded no Visual settings), so the four card KPIs are shown as a single-row table at the top of the Measures page.
- **Measure table name:** my measure table is named `_Measures_` rather than `_Measures`.
- **Data:** the clean CSVs are the instructor's `Wildcat Capital Clean` release; December 2024 Ending AUM is $12,729,572,078.86 in both pandas and Power BI.
