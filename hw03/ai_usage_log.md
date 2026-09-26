# HW3 AI Usage Log
MIS3060 Business Intelligence with AI | Hannah Dickinson

## 1. Prompts sent to Claude Cowork

### Prompt 1 — Specification A (Earnings Pipeline → `hw03_earnings.py`)

> I need help writing a script saved as `hw03/hw03_earnings.py`, using `requests` and `beautifulsoup4`, to help extract specific data regarding the following companies:
>
> | Company | Ticker | SEC CIK |
> |---|---|---|
> | Apple Inc. | AAPL | 0000320193 |
> | Microsoft Corporation | MSFT | 0000789019 |
> | NVIDIA Corporation | NVDA | 0001045810 |
> | JPMorgan Chase & Co. | JPM | 0000019617 |
> | Walmart Inc. | WMT | 0000104169 |
>
> Use these values exactly. At the beginning of the script, set the SEC EDGAR User-Agent to "MIS3060 Villanova hdickins@villanova.edu" on every HTTP request (every `requests.get()` call, not just the first one).
>
> For each of the five companies I listed above, you need to query the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json` and filter for 8-K filings where the `items` field contains "2.02". When looking through, select the four most recent filings per company (one per quarter).
>
> For each filing, the script needs to construct the filing index URL, identify the earnings press release exhibit (.htm file), download it, and strip the HTML to plain text. If the press release exhibit can't be found, print a warning and move on to the next filing instead of crashing.
>
> I need you to extract from the plain text: quarterly revenue, diluted EPS, net income, and the reporting period (e.g., "fourth quarter fiscal 2024"). Store revenue and net income as numbers in millions. Keep in mind the companies label revenue differently (for example, Apple says "net sales"), so the extraction should handle those differences.
>
> Please print the extracted row for each filing as it's processed, in this specific format: `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`.
>
> Please save all the rows to `hw03/earnings_history.csv` with columns: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`, and print a message confirming the file was saved.
>
> Where a field cannot be extracted (regex returns no match), store the string "NOT_FOUND" rather than leaving the cell blank, because blank cells and missing data are two different things.

### Prompt 2 — Specification B (Executive Events Pipeline → `hw03_executives.py`)

> I need help writing another script, saved as `hw03/hw03_executives.py`, using `requests` and `beautifulsoup4`. Set the SEC EDGAR User-Agent to "MIS3060 Villanova hdickins@villanova.edu" on every HTTP request (every `requests.get()` call, not just the first one).
>
> For each of the five companies listed below:
>
> | Company | Ticker | SEC CIK |
> |---|---|---|
> | Apple Inc. | AAPL | 0000320193 |
> | Microsoft Corporation | MSFT | 0000789019 |
> | NVIDIA Corporation | NVDA | 0001045810 |
> | JPMorgan Chase & Co. | JPM | 0000019617 |
> | Walmart Inc. | WMT | 0000104169 |
>
> Please query the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json` and filter for 8-K filings where the `items` field contains "5.02" (Departure of Directors or Officers) and the `filingDate` is within the past 12 months.
>
> For each matching filing, download the full 8-K text, strip the HTML, and extract: event type (`"departure"` or `"appointment"` or `"both"`), the person's full name, their title, and the effective date of the change. If a field can't be extracted, store "NOT_FOUND" instead of leaving it blank. If a download fails, print a warning and move on to the next filing. If the filing contains multiple events, such as one departure and one appointment, create separate rows for each event.
>
> Please then print each extracted event as it is processed: `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`
>
> If no Item 5.02 filings are found for a company in the past 12 months, please print `[Ticker]: No executive events in past 12 months` and continue to the next company without crashing. This is valid data, not an error.
>
> Then save all events to `hw03/executive_events.csv` with columns: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. Save the file with its column headers even if no events are found, and print a message confirming the file was saved.

### Prompt 3 — Timeline (→ `hw03_timeline.py`)

> Write a Python script that reads `hw03/earnings_history.csv` and `hw03/executive_events.csv`. Do the following:
>
> 1. For each executive event in the events table, calculate the number of days between the executive event's `filing_date` and the nearest earnings filing date for the same company in the earnings table. Call this `days_to_nearest_earnings`.
> 2. Add a column `event_timing` that categorizes each executive event as: `'before earnings'` if the event came before the nearest earnings filing, `'after earnings'` if it came after, or `'same week'` if within 7 days of an earnings filing.
> 3. Save the combined table to `hw03/corporate_events_timeline.csv` with all columns from both source tables plus `days_to_nearest_earnings` and `event_timing`.
> 4. Print a summary: for each company, list any executive events and whether they occurred before or after the nearest earnings announcement.
> 5. Print a final count: how many events occurred before vs. after an earnings announcement across all five companies.

## 2. Extractions that required iteration

- **Walmart (earnings):** For Walmart, net income came out as negative: -163, -160, -155 because the script grabbed "net income attributable to noncontrolling interest"; the regex was then changed to skip "noncontrolling"; after rerunning, the values were changed to 6,366, 5,330, 4,237
- **Executive events:** Four rows had non-person names (NVDA "Worldwide Field Operations", NVDA duplicate "Nora Johnson", JPM "Messrs. Petno", WMT "Non-Competition Agreements") — these issues were identified and documented in validation.md but not fixed. 


## 3. Something the generated script did that I did not specify

- The timeline script renamed the two `filing_date` columns to `event_filing_date` and `earnings_filing_date`. This was a needed change because otherwise the two columns could have clashed.

## 4. Other AI assistance

Additionally, I used Claude Cowork to help me review and edit my draft specifications, and to adjust my code and terminal commands when I got errors (like setting up my venv and installing missing packages). It also helped me check that the data from my terminal output was correct, and it found and fixed a bug in the Walmart net income regex. Claude set up the format for my validation file, wrote the yfinance script for 5C, and found the Apple press release I used for 5B. Claude also drafted my analysis paragraph and the explanations in my validation file, which I reviewed and edited independently. 
