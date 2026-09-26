"""
HW3 - Earnings Pipeline (SEC Form 8-K, Item 2.02)
MIS3060 Business Intelligence with AI | Hannah Dickinson

What it does
------------
For five companies (AAPL, MSFT, NVDA, JPM, WMT) this script:
  1. Pulls each company's filing list from the EDGAR submissions API.
  2. Keeps 8-K filings whose `items` include "2.02" (Results of Operations).
  3. Keeps the four most recent such filings (one per quarter).
  4. Opens each filing's index page, finds the earnings press release
     exhibit (EX-99.1, falling back to EX-99, then to any exhibit described
     as a press release), downloads it and converts
     the HTML to plain text.
  5. Uses regular expressions to extract quarterly revenue, diluted EPS,
     net income, and the reporting period.
  6. Prints one line per filing and saves everything to
     earnings_history.csv (in the same folder as this script).

Any field that cannot be extracted is stored as the string "NOT_FOUND".

How to run
----------
    pip install requests beautifulsoup4
    python hw03/hw03_earnings.py

Only requests, beautifulsoup4 and the Python standard library are used.
"""

import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Step 1 - SEC request rules
# ---------------------------------------------------------------------------
HEADERS = {"User-Agent": "MIS3060 Villanova hdickins@villanova.edu"}

COMPANIES = [
    {"company": "Apple Inc.",           "ticker": "AAPL", "cik": "0000320193"},
    {"company": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"company": "NVIDIA Corporation",   "ticker": "NVDA", "cik": "0001045810"},
    {"company": "JPMorgan Chase & Co.", "ticker": "JPM",  "cik": "0000019617"},
    {"company": "Walmart Inc.",         "ticker": "WMT",  "cik": "0000104169"},
]

FILINGS_PER_COMPANY = 4
MIN_DAYS_BETWEEN_FILINGS = 45   # guarantees "one per quarter"
NOT_FOUND = "NOT_FOUND"

OUTPUT_CSV = Path(__file__).resolve().parent / "earnings_history.csv"
CSV_COLUMNS = ["company", "ticker", "cik", "filing_date", "period",
               "revenue_reported", "eps_diluted", "net_income"]


def sec_get(url):
    """Single gateway for every HTTP request to the SEC.

    Sends HEADERS, uses a 30s timeout, sleeps 0.2s first (SEC limit is
    10 requests/second). Returns the Response, or None on failure.
    """
    time.sleep(0.2)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException as exc:
        print(f"  WARNING: request failed for {url}: {exc}")
        return None

    if resp.status_code == 403:
        print(f"  ERROR 403 Forbidden for {url}\n"
              f"  -> The SEC rejected the request. The User-Agent header is "
              f"probably wrong: {HEADERS['User-Agent']!r}")
        return None
    if resp.status_code != 200:
        print(f"  WARNING: HTTP {resp.status_code} for {url}")
        return None
    return resp


# ---------------------------------------------------------------------------
# Steps 2 & 3 - Find the earnings 8-Ks and keep the four most recent
# ---------------------------------------------------------------------------
def days_between(date_a, date_b):
    """Absolute day difference between two YYYY-MM-DD strings."""
    from datetime import date
    a = date.fromisoformat(date_a)
    b = date.fromisoformat(date_b)
    return abs((a - b).days)


def get_earnings_filings(cik):
    """Return up to four recent 8-K / Item 2.02 filings, newest first."""
    resp = sec_get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if resp is None:
        return []

    try:
        recent = resp.json()["filings"]["recent"]
    except (ValueError, KeyError) as exc:
        print(f"  WARNING: unexpected submissions JSON for CIK {cik}: {exc}")
        return []

    forms = recent.get("form", [])
    items = recent.get("items", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])
    primary_docs = recent.get("primaryDocument", [])

    selected = []
    for i, form in enumerate(forms):
        if form != "8-K":
            continue
        item_str = items[i] if i < len(items) and items[i] else ""
        item_list = [x.strip() for x in item_str.split(",")]
        if "2.02" not in item_list:
            continue

        filing_date = dates[i]
        # One per quarter: skip a second 2.02 filing too close to the last one kept
        if selected and days_between(selected[-1]["filing_date"], filing_date) < MIN_DAYS_BETWEEN_FILINGS:
            continue

        selected.append({
            "accession": accessions[i],
            "filing_date": filing_date,
            "primary_document": primary_docs[i] if i < len(primary_docs) else "",
        })
        if len(selected) == FILINGS_PER_COMPANY:
            break

    return selected


# ---------------------------------------------------------------------------
# Step 4 - Locate the press release exhibit and convert it to text
# ---------------------------------------------------------------------------
def build_index_url(cik, accession):
    cik_no_zeros = str(int(cik))
    acc_no_dashes = accession.replace("-", "")
    return (f"https://www.sec.gov/Archives/edgar/data/"
            f"{cik_no_zeros}/{acc_no_dashes}/{accession}-index.htm")


def find_press_release_url(index_html):
    """Return the absolute URL of the EX-99.1 (or EX-99) .htm exhibit, or None."""
    soup = BeautifulSoup(index_html, "html.parser")
    candidates = []  # (type, href, description)

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]
        if "type" not in headers or "document" not in headers:
            continue
        type_idx = headers.index("type")
        doc_idx = headers.index("document")

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) <= max(type_idx, doc_idx):
                continue
            doc_type = cells[type_idx].get_text(strip=True).upper()
            link = cells[doc_idx].find("a")
            if not link or not link.get("href"):
                continue
            href = link["href"]
            if href.startswith("/ix?doc="):          # inline-XBRL viewer link
                href = href[len("/ix?doc="):]
            if href.lower().endswith((".htm", ".html")):
                desc = ""
                if "description" in headers:
                    d_idx = headers.index("description")
                    if d_idx < len(cells):
                        desc = cells[d_idx].get_text(" ", strip=True).lower()
                candidates.append((doc_type, href, desc))

    def absolute(href):
        if href.startswith("http"):
            return href
        return "https://www.sec.gov" + (href if href.startswith("/") else "/" + href)

    for prefix in ("EX-99.1", "EX-99"):
        for doc_type, href, _ in candidates:
            if doc_type.startswith(prefix):
                return absolute(href)
    # Fallback: an exhibit whose description says it is the press release
    for _, href, desc in candidates:
        if "press release" in desc or "earnings release" in desc:
            return absolute(href)
    return None


BLOCK_TAGS = ["p", "div", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"]


def html_to_text(html):
    """Strip HTML to plain text while keeping words and numbers separated."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove non-visible content (scripts, styles, hidden inline-XBRL header)
    for tag in soup.find_all(["script", "style", "ix:header"]):
        tag.decompose()

    for br in soup.find_all("br"):
        br.replace_with("\n")
    for cell in soup.find_all(["td", "th"]):
        cell.append(" ")                     # table cells separated by spaces
    for tag in soup.find_all(BLOCK_TAGS):
        tag.append("\n")                     # line break after block elements

    text = soup.get_text()
    text = text.replace("\xa0", " ").replace("​", "")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)    # collapse spaces
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)         # collapse blank lines
    return text.strip()


# ---------------------------------------------------------------------------
# Step 5 - Field extraction (one small function per field)
# ---------------------------------------------------------------------------
# A dollar amount: optional $, optional parentheses (negative), digits with commas,
# optional decimals, optional unit. The lookahead stops us grabbing percentages.
AMOUNT = (r"\$?\s*(?P<num>\(?\s*-?\d[\d,]*(?:\.\d+)?(?![\d.]|,\d)\s*\)?)"
          r"(?!\s*%)\s*(?P<unit>billion|million|B\b|M\b)?")
# What is allowed between a label and its number: spaces, colons, a linking
# verb, and footnote markers such as "(1)" or "(a)" that tables often carry.
GAP = (r"(?:\s*\((?:[a-z]|\d)\))*[\s:]*"
       r"(?:was|were|of|totaled|reached)?[\s:]*")


def to_number(num_str):
    """'(1,234.5)' -> -1234.5 ; '$90,007' -> 90007.0"""
    s = num_str.strip()
    negative = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "").strip()
    value = float(s)
    return -abs(value) if negative else value


def to_millions(num_str, unit):
    """Convert an amount to millions. Table values (no unit) are already in millions."""
    value = to_number(num_str)
    unit = (unit or "").lower()
    if unit in ("billion", "b"):
        value *= 1000
    return clean(value)


def clean(value):
    """Store whole numbers without a trailing .0 (90000.0 -> 90000)."""
    value = round(value, 2)
    return int(value) if value == int(value) else value


def plausible(match):
    """Reject numbers that are clearly not a dollar amount in millions."""
    raw = match.group("num").strip()
    has_unit = bool(match.group("unit"))
    try:
        value = abs(to_number(raw))
    except ValueError:
        return False
    digits = raw.strip("()").strip()
    # a bare 4-digit year like 2025 (no comma, no unit)
    if not has_unit and re.fullmatch(r"(19|20)\d{2}", digits):
        return False
    # a footnote or tiny figure: these companies report thousands of millions
    if not has_unit and value < 10:
        return False
    return True


def first_amount(text, label_patterns):
    """Try each label pattern in order; return the first plausible amount (in millions)."""
    for label in label_patterns:
        for match in re.finditer(label + GAP + AMOUNT, text, flags=re.IGNORECASE):
            if plausible(match):
                return to_millions(match.group("num"), match.group("unit"))
    return NOT_FOUND


def extract_revenue(text):
    patterns = [
        # JPMorgan's summary table: "Net revenue - reported"
        r"\bNet revenues?\s*[-\u2013\u2014]\s*reported\b",
        # income-statement totals (first column = current quarter)
        r"\bTotal net revenues?\b",
        r"\bTotal revenues?\b",
        r"\bTotal net sales\b",
        # headline phrases, e.g. "quarterly revenue of $94.0 billion"
        r"\b(?:quarterly |record |reported |total )?revenues? (?=(?:of|was|were)\b)",
        # plain table labels
        r"\bNet revenues?\b",
        r"\bNet sales\b",
        r"\bRevenues?\b",
    ]
    return first_amount(text, patterns)


def extract_net_income(text):
    patterns = [
        # skip "net income attributable to noncontrolling interest" (a small line
        # item Walmart reports) - we want net income attributable to the company
        r"\bNet income attributable to (?!non-?controlling)[^$\d\n]{1,50}?",
        r"\bNet income\b",
    ]
    return first_amount(text, patterns)


def extract_eps(text):
    """GAAP diluted EPS. Adjusted and non-GAAP figures are skipped."""
    eps = r"\(?\s*-?\d+\.\d{2}\s*\)?"
    not_adjusted = r"(?<!adjusted )(?<!non-gaap )"
    patterns = [
        rf"{not_adjusted}diluted earnings per (?:common )?share(?: attributable to [^$\d\n]{{1,50}}?)?[\s:]*(?:was|were|of)?[\s:]*\$\s*({eps})",
        rf"{not_adjusted}diluted net income per (?:common )?share(?: attributable to [^$\d\n]{{1,50}}?)?[\s:]*\$?\s*({eps})",  # Walmart
        rf"{not_adjusted}earnings per diluted share[^$\n]{{0,60}}\$\s*({eps})",       # NVIDIA
        rf"{not_adjusted}diluted EPS[^$\n]{{0,40}}\$\s*({eps})",
        rf"\bGAAP EPS (?:of|was) \$\s*({eps})",
        rf"{not_adjusted}\bEPS (?:of|was) \$\s*({eps})",
        rf"\(\$\s*({eps}) per share\)",                                        # JPM headline style
        rf"(?:earnings|net income) per (?:common )?share[\s\S]{{0,400}}?\bDiluted\b[\s:]*\$?\s*({eps})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            try:
                return clean(to_number(match.group(1)))
            except ValueError:
                continue
    return NOT_FOUND


def extract_period(text):
    q = r"(?:first|second|third|fourth)"
    patterns = [
        rf"\b{q}[\s-]quarter(?: of)? fiscal(?: year)? \d{{4}}",   # fourth quarter fiscal 2024
        rf"\bfiscal(?: year)? \d{{4}} {q}[\s-]quarter",           # fiscal 2026 fourth quarter
        rf"\b{q}[\s-]quarter(?: of)? \d{{4}}",                    # second quarter 2025 / second-quarter 2025
        r"\bQ[1-4] (?:FY|fiscal )?'?\d{2,4}\b",                   # Q2 FY26
        r"\b(?:quarter|three months) ended [A-Z][a-z]+ \d{1,2}, \d{4}",  # quarter ended June 30, 2026
    ]
    # The headline names the reporting period, so take the EARLIEST match
    # near the top of the release (later text often mentions the next
    # quarter's outlook). Fall back to the whole document.
    for window in (text[:3000], text):
        hits = [m for p in patterns
                for m in [re.search(p, window, flags=re.IGNORECASE)] if m]
        if hits:
            first = min(hits, key=lambda m: m.start())
            return re.sub(r"\s+", " ", first.group(0)).strip()
    return NOT_FOUND


# ---------------------------------------------------------------------------
# Step 6 - Printing
# ---------------------------------------------------------------------------
def fmt_money(value, suffix=""):
    if value == NOT_FOUND:
        return NOT_FOUND
    return f"${value:,}{suffix}"


def print_row(row):
    print(f"{row['ticker']} | {row['period']} | "
          f"Revenue: {fmt_money(row['revenue_reported'], 'M')} | "
          f"EPS: {fmt_money(row['eps_diluted'])} | "
          f"Net Income: {fmt_money(row['net_income'], 'M')}")


# ---------------------------------------------------------------------------
# Per-filing processing
# ---------------------------------------------------------------------------
def process_filing(company, filing):
    row = {
        "company": company["company"],
        "ticker": company["ticker"],
        "cik": company["cik"],
        "filing_date": filing["filing_date"],
        "period": NOT_FOUND,
        "revenue_reported": NOT_FOUND,
        "eps_diluted": NOT_FOUND,
        "net_income": NOT_FOUND,
    }

    index_url = build_index_url(company["cik"], filing["accession"])
    index_resp = sec_get(index_url)
    exhibit_url = find_press_release_url(index_resp.text) if index_resp else None

    if not exhibit_url:
        print(f"WARNING: {company['ticker']} {filing['filing_date']} – "
              f"press release exhibit not found, skipping")
        return row

    exhibit_resp = sec_get(exhibit_url)
    if exhibit_resp is None:
        print(f"WARNING: {company['ticker']} {filing['filing_date']} – "
              f"could not download {exhibit_url}, skipping")
        return row

    text = html_to_text(exhibit_resp.text)
    row["period"] = extract_period(text)
    row["revenue_reported"] = extract_revenue(text)
    row["eps_diluted"] = extract_eps(text)
    row["net_income"] = extract_net_income(text)
    return row


# ---------------------------------------------------------------------------
# Step 7 & 8 - Main loop and CSV output
# ---------------------------------------------------------------------------
def main():
    rows = []

    for company in COMPANIES:
        print(f"\n--- Processing {company['ticker']} (CIK {company['cik']}) ---")
        filings = get_earnings_filings(company["cik"])

        if not filings:
            print(f"NOTE: {company['ticker']} – no 8-K Item 2.02 filings found")
            continue
        if len(filings) < FILINGS_PER_COMPANY:
            print(f"NOTE: {company['ticker']} – only {len(filings)} "
                  f"Item 2.02 filing(s) found; processing what exists")

        for filing in filings:
            try:
                row = process_filing(company, filing)
            except Exception as exc:   # one bad filing never stops the run
                print(f"WARNING: {company['ticker']} {filing['filing_date']} – "
                      f"error while processing ({exc}), recording NOT_FOUND")
                row = {
                    "company": company["company"], "ticker": company["ticker"],
                    "cik": company["cik"], "filing_date": filing["filing_date"],
                    "period": NOT_FOUND, "revenue_reported": NOT_FOUND,
                    "eps_diluted": NOT_FOUND, "net_income": NOT_FOUND,
                }
            print_row(row)
            rows.append(row)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    not_found = sum(1 for r in rows for col in CSV_COLUMNS if r[col] == NOT_FOUND)
    print(f"\nSaved {len(rows)} rows to {OUTPUT_CSV} (revenue and net income in $ millions)")
    print(f"NOT_FOUND cells: {not_found} of {len(rows) * 4} extracted fields")


if __name__ == "__main__":
    main()
