# HW3 Specifications
MIS3060 Business Intelligence with AI | Hannah Dickinson

---

## Specification A — Earnings Pipeline (Item 2.02)

I need help writing a script saved as `hw03/hw03_earnings.py`, using `requests` and `beautifulsoup4`, to help extract specific data regarding the following companies:

| Company | Ticker | SEC CIK |
|---|---|---|
| Apple Inc. | AAPL | 0000320193 |
| Microsoft Corporation | MSFT | 0000789019 |
| NVIDIA Corporation | NVDA | 0001045810 |
| JPMorgan Chase & Co. | JPM | 0000019617 |
| Walmart Inc. | WMT | 0000104169 |

Use these values exactly. At the beginning of the script, set the SEC EDGAR User-Agent to "MIS3060 Villanova hdickins@villanova.edu" on every HTTP request (every `requests.get()` call, not just the first one).

For each of the five companies I listed above, you need to query the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json` and filter for 8-K filings where the `items` field contains "2.02". When looking through, select the four most recent filings per company (one per quarter).

For each filing, the script needs to construct the filing index URL, identify the earnings press release exhibit (.htm file), download it, and strip the HTML to plain text. If the press release exhibit can't be found, print a warning and move on to the next filing instead of crashing.

I need you to extract from the plain text: quarterly revenue, diluted EPS, net income, and the reporting period (e.g., "fourth quarter fiscal 2024"). Store revenue and net income as numbers in millions. Keep in mind the companies label revenue differently (for example, Apple says "net sales"), so the extraction should handle those differences.

Please print the extracted row for each filing as it's processed, in this specific format: `[Ticker] | [Period] | Revenue: $X | EPS: $X | Net Income: $X`.

Please save all the rows to `hw03/earnings_history.csv` with columns: `company`, `ticker`, `cik`, `filing_date`, `period`, `revenue_reported`, `eps_diluted`, `net_income`, and print a message confirming the file was saved.

Where a field cannot be extracted (regex returns no match), store the string "NOT_FOUND" rather than leaving the cell blank, because blank cells and missing data are two different things.

---

## Specification B — Executive Events Pipeline (Item 5.02)

I need help writing another script, saved as `hw03/hw03_executives.py`, using `requests` and `beautifulsoup4`. Set the SEC EDGAR User-Agent to "MIS3060 Villanova hdickins@villanova.edu" on every HTTP request (every `requests.get()` call, not just the first one).

For each of the five companies listed below:

| Company | Ticker | SEC CIK |
|---|---|---|
| Apple Inc. | AAPL | 0000320193 |
| Microsoft Corporation | MSFT | 0000789019 |
| NVIDIA Corporation | NVDA | 0001045810 |
| JPMorgan Chase & Co. | JPM | 0000019617 |
| Walmart Inc. | WMT | 0000104169 |

Please query the EDGAR submissions API at `https://data.sec.gov/submissions/CIK{cik}.json` and filter for 8-K filings where the `items` field contains "5.02" (Departure of Directors or Officers) and the `filingDate` is within the past 12 months.

For each matching filing, download the full 8-K text, strip the HTML, and extract: event type (`"departure"` or `"appointment"` or `"both"`), the person's full name, their title, and the effective date of the change. If a field can't be extracted, store "NOT_FOUND" instead of leaving it blank. If a download fails, print a warning and move on to the next filing. If the filing contains multiple events, such as one departure and one appointment, create separate rows for each event.

Please then print each extracted event as it is processed: `[Ticker] | [Date] | [Event Type] | [Name] | [Title]`

If no Item 5.02 filings are found for a company in the past 12 months, please print `[Ticker]: No executive events in past 12 months` and continue to the next company without crashing. This is valid data, not an error.

Then save all events to `hw03/executive_events.csv` with columns: `company`, `ticker`, `cik`, `filing_date`, `event_type`, `person_name`, `title`, `effective_date`. Save the file with its column headers even if no events are found, and print a message confirming the file was saved.
