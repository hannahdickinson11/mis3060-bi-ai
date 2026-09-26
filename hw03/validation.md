# HW3 Validation

## 5A — Known-Answer Check: Earnings

Company/quarter checked: Apple fiscal 2025 fourth quarter (filed 2025-10-30)
Official source: (https://www.apple.com/newsroom/2025/10/apple-reports-fourth-quarter-results/)

| Check | Official Source | Your CSV | Match? |
|---|---|---|---|
| Apple Q4 FY2025 Revenue | $102,466M | $102,466M | Yes (Rounding difference) |
| Apple Q4 FY2025 EPS Diluted | $1.85| $1.85 | Yes |

### Regex fix — Walmart net income

For Walmart:

 Walmart's original net income came out as -163, -160 and -155 (in millions) for three quarters. That seemed incorrect, since Walmart makes billions in profit each quarter. The problem was that Walmart's income statement has a line called "net income attributable to noncontrolling interest," which is a small amount, and the script grabbed that line first instead of "net income attributable to Walmart." Claude changed the regex pattern so it skips any line that says "noncontrolling." After rerunning the script, Walmart's net income changed to 6,366, 5,330 and 4,237 (in millions), which makes sense given Walmart's reported EPS.

- Before: `\bNet income attributable to [^$\d\n]{1,50}?`
- After: `\bNet income attributable to (?!non-?controlling)[^$\d\n]{1,50}?`

## 5B — Known-Answer Check: Executive Events

Event checked: Apple 2026-04-20, Tim Cook departure as CEO
Source: (https://www.apple.com/newsroom/2026/04/tim-cook-to-become-apple-executive-chairman-john-ternus-to-become-apple-ceo/)

| Check | News Source Confirms? | Notes |
|---|---|---|
| Person name and title | Yes | Tim Cook, CEO |
| Event type (departure/appointment) | Yes, partially | Cook did leave CEO role, but he didn't leave Apple. Cook stayed at Apple as executive chairman of the board, so "both" may accurately describe the event rather than "departure" |
| Effective date | Yes | The change took effect on September 1, 2026, which matches the CSV (2026-09-01).|

## 5C — Cross-Validation: Earnings via Yahoo Finance

| Metric | From 8-K text extraction | From yfinance | Match? |
|---|---|---|---|
| Revenue | $102,466M | 102,466M | Yes |
| Net Income | $27,466M | 27,466M | Yes |

Explanation: Both sources match.
## 5D — Pipeline Integrity Checks

| Check | Expected | Actual | Pass/Fail |
|---|---|---|---|
| `earnings_history.csv` row count | Up to 20 (5 companies × 4 quarters) | 20 | Pass|
| `executive_events.csv` row count | At least 0 (document actual) | 32 | Pass |
| `corporate_events_timeline.csv` created | Yes | Yes (32 rows) | Pass |
| Rows with all three fields `"NOT_FOUND"` | 0 (investigate if > 0) | 0 |Pass  |

Notes on data quality:
- Four rows in `executive_events.csv` have incorrect names because the script picked up text that isn't a person: NVDA "Worldwide Field Operations" (a department name), NVDA "Nora Johnson" (a duplicate of the Suzanne Nora Johnson row in the same filing), JPM "Messrs. Petno" (a partial name that came from "Messrs."), and WMT "Non-Competition Agreements" (a section heading). These shouldn't be treated as real executive events, but I kept them in the file and noted them here. Also, since they carry into the timeline, they also slightly inflate the before/after counts.
- Three Item 5.02 filings had no named departure or appointment: MSFT 2025-12-08, NVDA 2026-03-06, and JPM 2026-01-22. These may be  compensation or plan-related filings, which also fall under Item 5.02. The script written by Claude stored them as NOT_FOUND rows instead of crashing.
- Some earnings values came from rounded headline figures instead of the exact financial table, for example Microsoft's net income of 35,800 vs. the exact 35,766 (in millions). This affects some Microsoft, NVIDIA and JPMorgan values. The numbers are close but not exact.
