# HW4 Part A — Claude Code review notes (for README)

**Script reviewed:** `scripts/01_profile.py`
**Review date:** 2026-10-19
**Result after fixes:** 65 findings — 9 ERROR, 18 WARN, 38 INFO — in 41 issue groups

## Before the review: run error in VS Code

| Problem | What I did |
|---|---|
| Script crashed on my Python version (`TypeError: unsupported operand type(s) for \|`): the `str \| None` type hint needs Python 3.10+ | Added `from __future__ import annotations` so it runs on older Python, and removed a pandas option (`include_groups`) that only exists in newer pandas |

## Claude Code findings and what I did

| # | Claude Code flagged | What I did |
|---|---|---|
| 1 | Mixed-format warnings counted scientific notation as a different format | Scientific notation now counts as an ordinary number. `active_alpha_ytd` no longer shows up; `return_ytd` dropped from 435 to 300 (the real "9.28%" strings). |
| 2 | One issue counted by several checks makes totals misleading | Added an `issue_group` column. The console now says not to add up findings that share a group. |
| 3 | One bad date would flag every row in the year/month checks | Calendar comparisons now skip unreadable dates and compare whole-number text. Tested: one bad date now flags 1 row, not 1,827. |
| 4 | Missing values counted as contradictions | The tier, account-type and fee-formula checks now skip rows they can't compute. The fee check also reports how many rows it couldn't compute. |
| 5 | Inconsistent counting | Duplicate checks now report extra records (a pair counts as 1), with total rows involved in the detail. Case variants count rows. The truncated-name check lower-cases names and ignores blanks. |
| 6 | Snapshot/fee join could multiply rows | Blank keys are left out, and the script now checks that each client-month key is unique before joining. |
| 7 | Trading-day check only looked one way | Added a market-holiday calendar. **New findings:** 47 holidays are marked as trading days in `dim_date`, and 3,613 Buy/Sell trades fall on them. |
| 8 | Hard-coded "1000.0" and an assumed orphan ID range | AUM is now compared as a number, and the orphan ID range is calculated from the data. Comments say where the tier cut-offs and the ÷12 come from: they're assumptions the data confirms. |
| 9 | Smaller issues | The script now stops if two files match one table, or if a table is missing columns. Calendar gaps are checked against the full 2020–2024 range. The last month uses real dates. Blank risk profiles use the same blank test as everything else. Double spaces are now reported. |

**Note:** The near-duplicate client count changed from 50 to 25 because duplicates are now counted as extra records. It's the same 25 duplicate clients.

---

# HW4 Part C — Claude Code review notes

**Script reviewed:** `scripts/02_clean.py`
**Review date:** 2026-10-23
**What Claude Code confirmed:** the script ran cleanly; every cell that differs between raw and clean was logged in `value_changes.csv`, and every logged change really happened.
**Result after fixes:** the clean tables are byte-for-byte the same as before the fixes, so only the proof and the audit trail changed. 198,303 value changes on kept rows; 25 + 200 rows quarantined; all 13 relationships 100%.

| # | Claude Code flagged | What I did |
|---|---|---|
| 1 | Script counts didn't match the decision log (836 vs 835, 76 vs 75, 44,262 vs 44,241, 101,597 vs 101,528, 1,475) | These differences come from the cleaning order (orphans and duplicates are quarantined first). Added a "Counts after applying the cleaning order" table to the decision log explaining each one. |
| 2 | Decision log wording didn't match the script (D03 "truncated" for all 25, D02 "7-name lookup", D10 assert pattern, D18 listing alpha) | Corrected all four in the decision log. D03 now says 23 shortened + 2 with an extra letter (Leen/Lee, Pacen/Pace). |
| 3 | Quarantine files held rows that had already been format-fixed (e.g. `237` instead of the raw `237.0`) | Quarantine files are now built from the **original raw rows**. The 132 format fixes on those rows are no longer in `value_changes.csv`, and the cleaning log records this. |
| 4 | Some replacements ran on the whole column but only the checked rows were logged | Added one `change()` helper that applies **and** logs on exactly the same cells, so the log can't drift from what happened. |
| 5 | D12 didn't check transaction type | It now stops if a negative share appears on anything other than a Buy, and treats `-0` as negative too. |
| 6 | D15 checked the unrounded value but wrote a rounded one | It now re-checks the value actually written against benchmark + alpha. |
| 7 | D03 never checked that the kept record is the one the facts use | It now asserts that every kept original has fact rows and that the 2,500 kept clients = the distinct clients in fees + snapshots. The last-name rule allows at most 2 letters of difference. |
| 8 | Several asserts were true by construction and could never fail | Replaced them with independent checks: D09 checks exactly which dates changed and that every other weekday is still a trading day; D14 recomputes the flag count from the weekday and holiday list without `dim_date`; D18 checks no extreme alpha is left unflagged. |
| 9 | D12's after-check treated unreadable values as passing | Unreadable shares, price or amount on a trade now fail the check. |
| 10 | No overall raw-vs-clean check | Added a cell-by-cell comparison of every kept row: every difference must be in `value_changes.csv` with the right old and new values, and every logged change must be real. |
| 11 | Checks promised in the decision log weren't in the script (D07 1:1 with ETFs, D11 blanks on cash rows, D17 34 snapshots with no fee) | All three are now asserted or computed. |
| 12 | Code that would break on other data (non-numeric IDs, " pa" state spacing, holiday list ending in 2024, text date comparisons, uppercase "E", divide-by-zero, blank primary keys, README KeyErrors, hard-coded notes) | Each fixed: clear error messages instead of crashes, the holiday list must cover every year in `dim_date`, dates are parsed, and log notes and README numbers are now computed. |

---

# HW4 Part D — Claude Code review notes

**Script reviewed:** `scripts/03_validate.py`
**Review date:** 2026-10-25
**Main finding:** the clean "✓" and the raw scorecard looked better than the data really was — rounded asserts, an IQR sentence that wasn't computed, and no rule that could catch the flagged issues.
**Result after fixes:** 48 rules (was 39); every clean-stage check uses exact counts; tested by planting 4 defects in a copy of the clean data (a duplicate `txn_id`, a blank `client_id`, an impossible date, an unflagged weekend trade) — all 4 were caught and the script stopped.

| # | Claude Code flagged | What I did |
|---|---|---|
| 1 | Final asserts compared **rounded** percentages, so one duplicate key in 298,572 rows (99.9993%) passed as 100% | Every clean-stage check now uses exact counts (`duplicate_key_rows`, `invalid_typed_cells`, `rows_not_matched`, …). The scorecard has a count column next to every percentage. |
| 2 | The IQR "flagged ≠ wrong" sentence was hard-coded and partly false (no rule caught the 1,000 placeholder; "all reconcile" was never calculated) | The sentence is now built from computed numbers: % of outliers belonging to UHNW clients, % of large transactions that reconcile (99.6%), and how many placeholder rows the new placeholder rule catches (420). The opening changes if the numbers don't support "not wrong". Removed the dead `aum_basis` branch. |
| 3 | No rule could catch the 1,475 implausible returns or the 420 placeholder AUMs, so raw snapshots scored 100% rule pass | Added plausibility rules for D14, D17 and D18, using the same thresholds as Part C. Raw snapshots now score 98.73%. Clean tables still fail these rules on purpose (the rows were flagged, not fixed), and the script checks that **every** remaining failure carries the matching Part C flag. |
| 4 | Checks reused the cleaning script's own inputs (holiday list, cash types), so a shared mistake would pass both | The trading-day rule now uses the pandas-rule holiday calendar from `01_profile.py`, not Part C's hand-typed list; transaction types are defined in `03_validate.py`. |
| 5 | R1 used an inner join, so fees with no snapshot weren't in the denominator; duplicate snapshots could multiply rows | R1 now checks **every** fee row against the single snapshot for that client-month; a missing or duplicated snapshot counts as a failure. The note says R1 can't detect the placeholder because both tables carry it. |
| 6 | `pct_rule_pass` averaged over rules, so 78 bad states showed as 99.66% | Now "% of rows passing every rule": raw `dim_client` = 96.91%. |
| 7 | `pct_referential_match` ignored blank keys and pooled FKs (raw transactions showed 81.95%) | Now "% of rows whose foreign keys all resolve", with blanks counted as failures except where allowed (`security_id` on cash rows). Raw `fact_transactions` = 33.98%, the true share of rows that join. |
| 8 | Date type validity only checked the format (2024-13-45 passed) | Dates must now be real calendar dates. |
| 9 | Key uniqueness definition unclear; `45.0` IDs counted in two metrics | Wrote `reports/data_quality_scorecard_notes.md` defining every metric (keep=False is stated: 25 duplicate clients = 50 rows), and explaining that `45.0` is genuinely both a type and a join problem. |
| 10 | RI function only works on all-text DataFrames (Assignment 5 risk) | It now converts keys to text itself, and has a `normalize_numeric=True` option for frames loaded without `dtype=str`. |
| 11 | Asserts ran before saving and were skipped under `python -O` | Reports are saved first; checks are explicit, collect **all** problems with messages, and exit with an error. |
| 12 | Gaps against the brief (no rules for period-end flags, month name, week, region, sector, `is_etf`, benchmark asset class, future `client_since`); R2–R5 labelled cross-table | Added all of them. Each reconciliation now has a `scope` column: R1, R6, R7 are cross-table; R2–R5 within-table. |
| 13 | Fragile code (`is_etf == "True"`, misspelt types treated as trades, KeyErrors on renamed columns or missing IQR rows, `drop_duplicates` hiding conflicting clients, R5 comparing numbers as text, no holiday-year guard) | Each fixed: case-insensitive booleans, an explicit list of security-bearing types, clear errors for missing columns, a defensive IQR sentence, duplicated client IDs now count as unmatched instead of silently keeping the first, R5 compares numbers, and the script stops if the holiday calendar doesn't cover every year. |
