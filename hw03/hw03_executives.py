"""
HW3 - Executive Events Pipeline (SEC Form 8-K, Item 5.02)
MIS3060 Business Intelligence with AI | Hannah Dickinson

What it does
------------
For five companies (AAPL, MSFT, NVDA, JPM, WMT) this script:
  1. Pulls each company's filing list from the EDGAR submissions API.
  2. Keeps 8-K filings whose `items` include "5.02" (Departure of Directors
     or Certain Officers; Election of Directors; Appointment of Certain
     Officers) and whose filingDate is within the past 12 months.
  3. Downloads each filing's main 8-K document, strips the HTML to plain
     text, and isolates the Item 5.02 section.
  4. Finds every person named in that section and decides whether each one
     is a "departure", an "appointment", or "both", then extracts their
     title and the effective date of the change. One row per person, so a
     filing with a departure AND an appointment produces two rows.
  5. Prints one line per event and saves everything to executive_events.csv
     (in the same folder as this script).

A company with no Item 5.02 filings in the past 12 months prints
"[Ticker]: No executive events in past 12 months" - that is valid data.
A field that cannot be extracted is stored as the string "NOT_FOUND".

How to run
----------
    pip install requests beautifulsoup4
    python hw03/hw03_executives.py

Only requests, beautifulsoup4 and the Python standard library are used.
"""

import csv
import re
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# SEC request rules (same as hw03_earnings.py)
# ---------------------------------------------------------------------------
HEADERS = {"User-Agent": "MIS3060 Villanova hdickins@villanova.edu"}

COMPANIES = [
    {"company": "Apple Inc.",            "ticker": "AAPL", "cik": "0000320193"},
    {"company": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
    {"company": "NVIDIA Corporation",    "ticker": "NVDA", "cik": "0001045810"},
    {"company": "JPMorgan Chase & Co.",  "ticker": "JPM",  "cik": "0000019617"},
    {"company": "Walmart Inc.",          "ticker": "WMT",  "cik": "0000104169"},
]

LOOKBACK_DAYS = 365
NOT_FOUND = "NOT_FOUND"

OUTPUT_CSV = Path(__file__).resolve().parent / "executive_events.csv"
CSV_COLUMNS = ["company", "ticker", "cik", "filing_date", "event_type",
               "person_name", "title", "effective_date"]


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
# Step 2 - Find Item 5.02 8-Ks filed in the past 12 months
# ---------------------------------------------------------------------------
def matching_rows(block, cutoff):
    """Yield 8-K / Item 5.02 filings from one parallel-list block of the JSON."""
    forms = block.get("form", [])
    items = block.get("items", [])
    accessions = block.get("accessionNumber", [])
    dates = block.get("filingDate", [])
    primary_docs = block.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form != "8-K":
            continue
        if dates[i] < cutoff:              # ISO dates compare correctly as text
            continue
        item_str = items[i] if i < len(items) and items[i] else ""
        if "5.02" not in [x.strip() for x in item_str.split(",")]:
            continue
        yield {
            "accession": accessions[i],
            "filing_date": dates[i],
            "primary_document": primary_docs[i] if i < len(primary_docs) else "",
        }


def get_executive_filings(cik):
    """Return Item 5.02 8-Ks from the past 12 months, newest first."""
    cutoff = (date.today() - timedelta(days=LOOKBACK_DAYS)).isoformat()

    resp = sec_get(f"https://data.sec.gov/submissions/CIK{cik}.json")
    if resp is None:
        return None                         # None = request failed (not "zero filings")

    try:
        data = resp.json()
        recent = data["filings"]["recent"]
    except (ValueError, KeyError) as exc:
        print(f"  WARNING: unexpected submissions JSON for CIK {cik}: {exc}")
        return None

    filings = list(matching_rows(recent, cutoff))

    # Very active filers (e.g. JPM) can push part of the year into older
    # overflow files. Read those too if they overlap the 12-month window.
    for extra in data["filings"].get("files", []):
        if extra.get("filingTo", "") >= cutoff:
            extra_resp = sec_get(f"https://data.sec.gov/submissions/{extra['name']}")
            if extra_resp is not None:
                try:
                    filings.extend(matching_rows(extra_resp.json(), cutoff))
                except ValueError:
                    print(f"  WARNING: could not read {extra['name']}")

    filings.sort(key=lambda f: f["filing_date"], reverse=True)
    return filings


def build_document_url(cik, accession, primary_document):
    return (f"https://www.sec.gov/Archives/edgar/data/"
            f"{int(cik)}/{accession.replace('-', '')}/{primary_document}")


# ---------------------------------------------------------------------------
# Step 3 - HTML to text and isolate Item 5.02
# ---------------------------------------------------------------------------
BLOCK_TAGS = ["p", "div", "tr", "li", "table", "h1", "h2", "h3", "h4", "h5", "h6"]


def html_to_text(html):
    """Strip HTML to plain text while keeping words separated."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.find_all(["script", "style", "ix:header"]):
        tag.decompose()
    for br in soup.find_all("br"):
        br.replace_with("\n")
    for cell in soup.find_all(["td", "th"]):
        cell.append(" ")
    for tag in soup.find_all(BLOCK_TAGS):
        tag.append("\n")

    text = soup.get_text()
    text = text.replace("\xa0", " ").replace("​", "")
    text = text.replace("“", '"').replace("”", '"').replace("’", "'")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


# The standard Item 5.02 heading contains "Departure", "Election" and
# "Appointment" - remove it so it isn't mistaken for an actual event.
ITEM_502_HEADING = re.compile(
    r"Departure of Directors or (?:Certain )?Officers[^.]*?Compensatory Arrangements of Certain Officers\.?",
    re.IGNORECASE | re.DOTALL)


def isolate_item_502(text):
    """Return only the Item 5.02 section (up to the next Item or SIGNATURES)."""
    start = re.search(r"Item\s*5\.02", text, re.IGNORECASE)
    if not start:
        section = text
    else:
        rest = text[start.end():]
        end = re.search(r"\bItem\s*\d\.\d{2}\b|\bSIGNATURES?\b", rest)
        section = rest[:end.start()] if end else rest
    section = ITEM_502_HEADING.sub(" ", section)
    return re.sub(r"\s+", " ", section).strip()


def split_sentences(text):
    """Sentence split that doesn't break on 'Mr.', 'Inc.' or initials like 'E.'."""
    protected = re.sub(r"\b(Mr|Ms|Mrs|Dr|Jr|Sr|Inc|Co|Corp|No|St)\.", r"\1<DOT>", text)
    protected = re.sub(r"\b([A-Z])\.", r"\1<DOT>", protected)          # initials, U.S.
    parts = re.split(r'(?<=[.;])\s+(?=[A-Z"(])', protected)
    return [p.replace("<DOT>", ".").strip() for p in parts if p.strip()]


# ---------------------------------------------------------------------------
# Step 4 - Extraction (one small function per field)
# ---------------------------------------------------------------------------
MONTH = (r"(?:January|February|March|April|May|June|July|August|September|"
         r"October|November|December)")
DATE_RE = rf"{MONTH}\s+\d{{1,2}},\s*\d{{4}}"

# Capitalized words that are never part of a person's name
STOP_WORDS = {
    # sentence starters / function words
    "on", "the", "in", "as", "at", "by", "for", "from", "to", "with", "upon",
    "his", "her", "their", "he", "she", "they", "following", "prior", "during",
    "until", "effective", "pursuant", "under", "each", "such", "this", "that",
    "a", "an", "if", "also", "any", "all", "item", "items", "mr.", "ms.",
    "mrs.", "dr.", "mr", "ms", "mrs", "dr",
    # companies / places
    "apple", "microsoft", "nvidia", "jpmorgan", "chase", "walmart", "inc.",
    "inc", "corporation", "corp.", "company", "co.", "llc", "bank", "n.a.",
    "stores", "sam's", "club", "international", "holdings", "united", "states",
    "u.s.", "new", "york", "delaware", "california", "washington", "arkansas",
    "cupertino", "redmond", "santa", "clara", "bentonville", "nasdaq", "nyse",
    # governance / titles
    "board", "directors", "director", "committee", "compensation", "human",
    "resources", "talent", "nominating", "governance", "audit", "chief",
    "executive", "senior", "vice", "president", "officer", "officers",
    "chairman", "chair", "general", "counsel", "financial", "accounting",
    "operating", "principal", "treasurer", "controller", "secretary",
    "group", "global", "corporate", "deputy", "independent", "lead",
    # documents / compensation
    "annual", "meeting", "shareholders", "stockholders", "form", "section",
    "exhibit", "securities", "exchange", "act", "commission", "sec", "report",
    "plan", "agreement", "policy", "program", "award", "awards", "letter",
    "offer", "severance", "retention", "transition", "consulting", "stock",
    "equity", "incentive", "restricted", "performance", "units", "shares",
    "cash", "bonus", "salary", "base", "target", "fiscal", "year", "quarter",
    "current", "press", "release", "retirement", "separation", "departure",
    "appointment", "election", "employment", "services", "compensatory",
    "arrangements", "certain", "departure", "elected", "appointed",
    # months / days
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "monday", "tuesday",
    "wednesday", "thursday", "friday",
}

NAME_TOKEN = r"[A-Z][A-Za-zÀ-ÿ'\-]*\.?"
CAP_SEQUENCE = re.compile(rf"{NAME_TOKEN}(?:\s+{NAME_TOKEN})*")
HONORIFIC_SURNAME = re.compile(r"\b(?:Mr|Ms|Mrs|Dr)\.\s+([A-Z][A-Za-zÀ-ÿ'\-]+)")


def is_name_token(tok):
    if tok.lower() in STOP_WORDS:
        return False
    if len(tok) > 1 and tok.rstrip(".").isupper() and len(tok.rstrip(".")) > 1:
        return False                        # acronyms like CEO, NVIDIA
    return True


def find_people(section):
    """Return full names (2-4 words, optional middle initial) found in the section."""
    people = []
    for match in CAP_SEQUENCE.finditer(section):
        tokens = match.group(0).split()
        # trim stop words from both ends ("The Board appointed Jane Doe" -> "Jane Doe")
        while tokens and not is_name_token(tokens[0]):
            tokens.pop(0)
        while tokens and not is_name_token(tokens[-1]):
            tokens.pop()
        if not tokens:
            continue
        # a trailing period on the last word is a sentence end, not part of the name
        if tokens[-1].endswith(".") and len(tokens[-1]) > 2 and tokens[-1] not in ("Jr.", "Sr."):
            tokens[-1] = tokens[-1][:-1]
        real_words = [t for t in tokens if len(t.rstrip(".")) > 1]
        if not (2 <= len(real_words) <= 4):
            continue
        if not all(is_name_token(t) for t in tokens):
            continue
        name = " ".join(tokens)
        if name not in people:
            people.append(name)
    return people


def surname(full_name):
    parts = [p for p in full_name.split() if p not in ("Jr.", "Sr.", "II", "III")]
    return parts[-1]


def person_mentions(sentence, people):
    """Return [(start, end, person)] for each full-name or 'Mr. Surname' mention."""
    mentions = []
    for person in people:
        for m in re.finditer(re.escape(person), sentence):
            mentions.append((m.start(), m.end(), person))
    for m in HONORIFIC_SURNAME.finditer(sentence):
        for person in people:
            if surname(person) == m.group(1):
                mentions.append((m.start(), m.end(), person))
    return sorted(mentions)


DEPARTURE_RE = re.compile(
    r"\b(?:retire[sd]?|retiring|retirement|resign(?:s|ed|ing|ation)?|"
    r"step(?:s|ped|ping)? down|depart(?:s|ed|ing|ure)?|"
    r"leav(?:e|es|ing) (?:the|its|his|her) (?:Company|Corporation|role|position)|"
    r"(?:will )?not (?:to )?stand for re-?election|terminat(?:ed|ion)|"
    r"separat(?:ed|ion) from|transition(?:s|ed|ing)? (?:out )?(?:from|of) (?:his|her|their|the) (?:role|position))\b",
    re.IGNORECASE)

APPOINTMENT_RE = re.compile(
    r"\b(?:appoint(?:s|ed|ing|ment)?|(?<!re-)(?<!re)elect(?:s|ed|ing|ion)?|"
    r"nam(?:e|es|ed)(?! executive officer)|promot(?:e|ed|ion)|"
    r"will (?:become|serve as|assume|succeed)|join(?:s|ed|ing)? the (?:Company|Corporation|Board))\b",
    re.IGNORECASE)

ACTIVE_VERB = re.compile(r"^(?:appoint(?:s|ed)|elect(?:s|ed)|name[sd]|promote[sd])$", re.IGNORECASE)
PASSIVE_BEFORE = re.compile(r"(?:has|have|had|was|were|is|be|been)\s+$", re.IGNORECASE)
NOUN_OF = re.compile(r"^(?:retirement|resignation|departure|appointment|election|"
                     r"separation|termination|promotion)$", re.IGNORECASE)


def assign_keyword(sentence, kw_match, mentions):
    """Decide which person a departure/appointment keyword refers to."""
    word = kw_match.group(0).split()[0]
    pos, end = kw_match.start(), kw_match.end()
    after = [m for m in mentions if m[0] >= end]
    before = [m for m in mentions if m[1] <= pos]

    # "the Board appointed Jane Doe" / "the retirement of John Smith" -> the person AFTER
    if ACTIVE_VERB.match(word) and not PASSIVE_BEFORE.search(sentence[:pos]):
        if after and after[0][0] - end <= 80:
            return after[0][2]
    if NOUN_OF.match(word) and sentence[end:end + 4].lower().startswith(" of"):
        if after and after[0][0] - end <= 60:
            return after[0][2]
    # "Jane Doe will retire" / "John Smith was appointed" -> the person BEFORE
    if before:
        return before[-1][2]
    if after:
        return after[0][2]
    return None


TITLE_CORE = (
    r"(?:(?:Executive|Senior|Group|Corporate|Global|Deputy|Lead|Independent)\s+)*"
    r"(?:Vice\s+Chair(?:man)?|Vice\s+President|Chief\s+(?:[A-Z][a-z]+\s+){1,3}Officer|"
    r"President|Chair(?:man|woman)?(?:\s+of\s+the\s+Board)?|General\s+Counsel|"
    r"Treasurer|Controller|(?:Corporate\s+)?Secretary|"
    r"Principal\s+(?:Accounting|Financial|Executive)\s+Officer|"
    r"member\s+of\s+the\s+Board(?:\s+of\s+Directors)?|[Dd]irector(?!s))"
)
TITLE_RE = (rf"{TITLE_CORE}(?:(?:,\s*|\s+and\s+|\s*&\s*){TITLE_CORE})*"
            rf"(?:,?\s+(?:of|for)\s+(?:[A-Z][\w&.\-]*\s?){{1,4}})?")
TITLE_AFTER_ROLE_WORD = re.compile(
    rf"\b(?:as|become|becoming|serve as|role of|position of|to)\s+(?:the\s+|its\s+|our\s+)?"
    rf"(?:[A-Z][A-Za-z]+'s\s+)?({TITLE_RE})")
TITLE_ANY = re.compile(TITLE_RE)


def extract_title(sentences_with_pos):
    """Find the person's title. Prefer 'as <Title>' after their name."""
    for sentence, pos in sentences_with_pos:
        m = TITLE_AFTER_ROLE_WORD.search(sentence, pos)
        if m:
            return tidy_title(m.group(1))
    for sentence, pos in sentences_with_pos:
        m = TITLE_ANY.search(sentence, pos) or TITLE_ANY.search(sentence)
        if m:
            return tidy_title(m.group(0))
    # Board-seat changes often never spell out a title ("re-election to the Board")
    for sentence, _ in sentences_with_pos:
        if re.search(r"\b(?:to|from|on|join(?:s|ed)?) the Board\b|re-?election", sentence):
            return "Director"
    return NOT_FOUND


def tidy_title(title):
    title = re.sub(r"\s+", " ", title).strip(" ,.;")
    title = re.sub(r"^member of the Board(?: of Directors)?$", "Director", title)
    return title[0].upper() + title[1:] if title else NOT_FOUND


def to_iso(date_text):
    clean = re.sub(r"\s+", " ", date_text.replace(" ,", ","))
    clean = re.sub(r",\s*", ", ", clean)
    try:
        return datetime.strptime(clean, "%B %d, %Y").date().isoformat()
    except ValueError:
        return clean


def extract_effective_date(sentences):
    """Find the effective date of the change in the person's sentences."""
    patterns = [
        rf"effective(?: as of| on| upon)?(?: the close of business| the end of the day)?(?: on)?,?\s+({DATE_RE})",
        rf"effective[^.;]{{0,80}}?({DATE_RE})",
        rf"(?:retire|resign|step down|depart|leave|begin|start|commence)[^.;]{{0,60}}?"
        rf"(?:on|as of|at the end of|end of day on)\s+({DATE_RE})",
    ]
    for pattern in patterns:
        for sentence in sentences:
            m = re.search(pattern, sentence, re.IGNORECASE)
            if m:
                return to_iso(m.group(1))
    # "effective immediately" -> use the date the sentence opens with ("On May 1, 2026, ...")
    for sentence in sentences:
        if re.search(r"effective immediately", sentence, re.IGNORECASE):
            m = re.search(DATE_RE, sentence)
            if m:
                return to_iso(m.group(0))
    return NOT_FOUND


def extract_events(section):
    """Return a list of events: {event_type, person_name, title, effective_date}."""
    people = find_people(section)
    if not people:
        return []

    flags = {p: {"departure": False, "appointment": False} for p in people}
    evidence = {p: [] for p in people}            # [(sentence, mention_pos)]

    for sentence in split_sentences(section):
        mentions = person_mentions(sentence, people)
        if not mentions:
            continue
        for kind, regex in (("departure", DEPARTURE_RE), ("appointment", APPOINTMENT_RE)):
            for kw in regex.finditer(sentence):
                person = assign_keyword(sentence, kw, mentions)
                if person:
                    flags[person][kind] = True
                    pos = next(m[0] for m in mentions if m[2] == person)
                    if (sentence, pos) not in evidence[person]:
                        evidence[person].append((sentence, pos))

    events = []
    for person in people:
        dep, app = flags[person]["departure"], flags[person]["appointment"]
        if not (dep or app):
            continue                               # mentioned, but no change reported
        event_type = "both" if dep and app else ("departure" if dep else "appointment")
        events.append({
            "event_type": event_type,
            "person_name": person,
            "title": extract_title(evidence[person]),
            "effective_date": extract_effective_date([s for s, _ in evidence[person]]),
        })
    return events


# ---------------------------------------------------------------------------
# Per-filing processing, printing, CSV
# ---------------------------------------------------------------------------
def blank_row(company, filing):
    return {
        "company": company["company"], "ticker": company["ticker"],
        "cik": company["cik"], "filing_date": filing["filing_date"],
        "event_type": NOT_FOUND, "person_name": NOT_FOUND,
        "title": NOT_FOUND, "effective_date": NOT_FOUND,
    }


def process_filing(company, filing):
    """Return one row per event found in the filing."""
    url = build_document_url(company["cik"], filing["accession"], filing["primary_document"])
    resp = sec_get(url)
    if resp is None:
        print(f"WARNING: {company['ticker']} {filing['filing_date']} – "
              f"could not download 8-K document, recording NOT_FOUND")
        return [blank_row(company, filing)]

    section = isolate_item_502(html_to_text(resp.text))
    events = extract_events(section)

    if not events:
        print(f"NOTE: {company['ticker']} {filing['filing_date']} – no named "
              f"departure/appointment found (may be a compensation-only 5.02 filing)")
        return [blank_row(company, filing)]

    rows = []
    for event in events:
        row = blank_row(company, filing)
        row.update(event)
        rows.append(row)
    return rows


def print_row(row):
    print(f"{row['ticker']} | {row['filing_date']} | {row['event_type']} | "
          f"{row['person_name']} | {row['title']}")


def main():
    rows = []

    for company in COMPANIES:
        print(f"\n--- Processing {company['ticker']} (CIK {company['cik']}) ---")
        filings = get_executive_filings(company["cik"])

        if filings is None:
            print(f"WARNING: {company['ticker']} – could not retrieve filings, skipping company")
            continue
        if not filings:
            print(f"{company['ticker']}: No executive events in past 12 months")
            continue

        for filing in filings:
            try:
                filing_rows = process_filing(company, filing)
            except Exception as exc:          # one bad filing never stops the run
                print(f"WARNING: {company['ticker']} {filing['filing_date']} – "
                      f"error while processing ({exc}), recording NOT_FOUND")
                filing_rows = [blank_row(company, filing)]
            for row in filing_rows:
                print_row(row)
                rows.append(row)

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    found = sum(1 for r in rows if r["event_type"] != NOT_FOUND)
    print(f"\nSaved {len(rows)} rows to hw03/{OUTPUT_CSV.name} "
          f"({found} extracted events, {len(rows) - found} NOT_FOUND filings)")


if __name__ == "__main__":
    main()
