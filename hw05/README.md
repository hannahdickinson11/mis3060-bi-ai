# HW5: Wildcat Capital Star Schema in Power BI

MIS3060 Business Intelligence with AI · Villanova University · Hannah Dickinson

This folder models the eight clean Wildcat Capital tables as a star schema. It identifies every key and grain, classifies every measure, proves the keys in code, and builds the model in Power BI Desktop. No new tables or columns were created; the tables are loaded exactly as released.

## Folder structure

```
hw05/
├── README.md                      this file
├── star_design.md                 Parts A, B, C, E and F
├── scripts/
│   └── 01_check_keys.py           proves keys (Part A) and grain (Part B) in code
├── reports/
│   └── key_checks.csv             every check the script ran, with PASS / FAIL / INFO
├── powerbi/
│   ├── hw05.pbix                  the Power BI model (Part D)
│   ├── model_view.png             Model view: every table and relationship
│   └── row_counts.png             one Count card per table, matching the brief
├── 00_Project Briefing/           assignment brief and Power BI guide
└── 02_Data/Cleaned/               the eight instructor-provided clean CSVs (not committed: the repo ignores CSVs)
```

## How to run the key check

The script needs pandas and reuses `check_referential_integrity()` from HW4, so it runs in the HW4 virtual environment. From the `hw05` folder:

```bash
source ../hw04/.venv/bin/activate
python scripts/01_check_keys.py
```

It reads `02_Data/Cleaned/`, prints each check, writes `reports/key_checks.csv`, and exits with code 1 if anything fails. Result on the clean data: **39 of 39 checks passed (1 INFO row)**.

What it checks:
1. Row and column counts match the brief for all eight tables
2. Every primary key is unique and never blank
3. `dim_date[date]` is unique, so the fact date columns can join to it
4. All 13 foreign keys have zero orphans; `fact_transactions[security_id]` is blank only on the 101,528 cash rows (Deposit, Withdrawal, Advisory Fee)
5. Grain: fees and snapshots are unique on client + month, and every fee/snapshot date is the 1st of the month; transactions have no natural key, so only `txn_id` identifies a row (INFO row: 622 repeats)
6. The `advisor_id` on every fact row equals the client's advisor in `dim_client` (evidence for Part E b)

**Dependency:** importing `hw04/scripts/03_validate.py` also loads HW4's `02_clean.py` and `01_profile.py` (definitions only). If those files move, this script stops.

## Power BI model (Part D)

Built in Power BI Desktop on the Apporto virtual desktop, following `00_Project Briefing/powerbi_guide.md`.

- **Types:** keys are Whole Number (including `fact_transactions[security_id]`, which is blank on cash rows); date columns are Date, not Date/Time; amounts, AUM, prices and returns are Decimal. Power BI guessed `dim_client[zip_code]` as a number and dropped leading zeros (`03897` became `3897`), so I changed it to Text with "Replace current". `account_type` and `primary_account_type` were checked as Text, since their first row is "529".
- **Relationships:** 13 total, all many-to-one with single cross-filter direction. 12 are active; `dim_client[advisor_id]` → `dim_advisor` is inactive because each fact already joins to `dim_advisor` directly. The fact dates join to `dim_date[date]`, not `date_id`. Full list and reasons in `star_design.md`, Part E.
- **Date table:** `dim_date` is marked as the date table on `date`.
- **Row counts:** one Count card per table's primary key shows 25, 8, 2,500, 1,827, 500, 122,197, 129,547 and 298,572, matching the brief (`powerbi/row_counts.png`).
- No DAX measures were written, as the brief asks. `hw05.pbix` is about 21 MB, under GitHub's 100 MB limit.

## Workflow

Claude (desktop app) drafted the script; I ran it in VS Code; Claude Code in VS Code reviewed it before I committed, using a "don't edit any files, just list what you find" prompt. I applied the fixes and re-ran the script before committing.

Claude also helped draft `star_design.md` (Parts A, B, C, E and F) and this README from the script's results and my Power BI model. I reviewed and edited every section, and asked for Part E (c), (d) and Part F to be rewritten in plainer language. I built the Power BI model myself on Apporto (loading, column types, relationships, date table and row-count cards), with Claude guiding the steps and checking my screenshots.

## What Claude Code flagged and what I did (`scripts/01_check_keys.py`)

Claude Code found no correctness bugs. It checked the script's assumptions against the data read-only (row and column counts, grain, advisor agreement, date formats) and confirmed they hold.

| # | Claude Code flagged | What I did |
|---|---|---|
| 1 | The transaction grain check only repeated the primary-key check; the real evidence (622 rows repeat client, date, type and security) was printed but not saved | Saved it as an INFO row in `key_checks.csv` |
| 2 | A duplicate `client_id` or an unreadable date would crash the script before the report was written, when the script exists to catch exactly those faults | Duplicate client IDs are dropped before the advisor lookup, and dates are parsed with `errors="coerce"`, so both show as FAIL. Tested by breaking a copy of the data: 10 FAIL rows, no crash |
| 3 | The brief gives column counts too, but only rows were checked | Added expected column counts; labelled the count checks Part D, where the rubric grades them |
| 4 | Importing HW4's `03_validate.py` also runs the top level of `02_clean.py` and `01_profile.py` | No change; harmless today. Dependency noted in the script docstring and this README |
| 5 | `is_blank` counts fewer values as blank than HW4's profile (`"none"`, `"-"`, `"?"`) | No change; no key column contains those values |
| 6 | Smaller points: the fee grain sentence should say each client has one fee type per month; the docstring said every check prints PASS or FAIL, though one prints INFO | Added the fee-type sentence to Part B; updated the docstring |

## Notes
- The clean CSVs are the instructor's `Wildcat Capital Clean` release. Three file names arrived with a ` (2)` suffix and were renamed to match the brief.
- The `powerbi/` model was built from those same eight files uploaded to Apporto, not from my own HW4 output, so everyone's model uses identical data.
