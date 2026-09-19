# HW2 Validation — fact_transactions.csv EDA

Applying the five Week 4 validation methods to the output of `hw02_eda.py`.

---

## 2A — Known-Answer Benchmarks

| Check | Expected | Your Script Produced | Match? | Notes |
|---|---|---|---|---|
| Dataset shape | (298772, 9) | (298772, 9) | Yes | |
| Null count — `security_id` | 101,597 | 101,597 | Yes | |
| Null count — `amount` | 0 | 0 | Yes | |
| Unique `txn_type` values | 6 | 6 | Yes | |
| Count of `Buy` transactions | 83,556 | 83,556 | Yes | |
| `txn_date` data type | object | str | **No** | Newer pandas (3.0+) gives string columns a dedicated `str` dtype instead of the older generic `object` label. Same underlying issue the benchmark is flagging (still not a real date type) — a pandas-version difference, not a script error. |
| Earliest `txn_date` | 2020-01-01 | 2020-01-01 | Yes | |
| Latest `txn_date` | 2024-12-30 | 2024-12-30 | Yes | |
| Duplicate `txn_id` count | 0 | 0 | Yes | |
| Mean `amount` | $54,075.17 | $54,075.17 | Yes | |
| Median `amount` | $41,220.48 | $41,220.49 | **No** | True value is exactly 41220.485 — a rounding-boundary case. Floating-point representation caused Python to round up (.49) instead of down (.48). One-cent discrepancy, not a calculation error. |
| Skewness of `amount` | 1.15 | 1.15 | Yes | |
| Correlation `shares`–`amount` | 0.65 | 0.65 | Yes | |
| Correlation `price`–`amount` | 0.64 | 0.64 | Yes | |
| Correlation `shares`–`price` | 0.00 | 0.00 | Yes | |
| Negative `shares` count (Buy only) | 836 | 836 | Yes | |
| Profile file created | Yes | Yes | Yes | |
| Chart files created (3) | Yes | Yes | Yes | |

### Investigation notes (for the two mismatches above):

>**txn_date:**    

**Input**: "help me investigate why txn_date shows it as a string and not an object as the independent answer shows us"

**Claude output:** "Good instinct to dig into this — here's what's actually going on, verified by checking pandas behavior directly:

Your requirements.txt doesn't pin a pandas version (it just says pandas with nothing after it), so when you ran pip install -r requirements.txt, you got whichever pandas version is currently latest — pandas 3.0. I confirmed this myself: in pandas 3.0, a brand-new default kicked in where plain text columns read from CSV get a dedicated string dtype that displays as str, instead of the old catch-all object dtype that earlier pandas versions used for any non-numeric column.

This wasn't always the default — pandas 2.x had this string dtype available as an opt-in feature, but pandas 3.0 (a fairly recent release) made it the default behavior. Your assignment's benchmark table was almost certainly generated on an older pandas version (2.x), back when object was still what you'd see for a text column, which is why the benchmark says object and your script says str.

To confirm this on your own machine (worth doing for your validation.md investigation notes), run this in your VS Code terminal with your venv active:

python -c "import pandas; print(pandas.__version__)"

I'd bet it comes back as 3.x. If it does, that confirms the theory directly rather than just trusting my explanation.

The important thing for your writeup: this is a cosmetic labeling difference caused by a pandas version change, not a data problem or a bug in the script. The substantive finding the benchmark is actually testing for — that txn_date is still just text, not a real date type, meaning no calendar math or chronological sorting works on it without converting it first — is identical either way. Both object and str mean "not a date," which is exactly the thing your assignment wants you to notice and flag (tying directly into business question 2C #3 about what breaks if you try to compute date math on it as-is)."

>**Median Amount:**

**Input:** "Why is the median amount .01 off from the independently verified data? 41,220.48 compared to 41,220.49"

**Claude Output:** "Good question — I dug into the actual numbers and found something more precise than "floating point imprecision," which is the real mechanism at play here.

The true median of your amount column is exactly 41220.485 — sitting precisely on the boundary between rounding to .48 and .49. What happens at that boundary depends entirely on which rounding method you use, and different tools disagree:

Python's built-in round(), pandas' .round(), and numpy's .round() all use "round half to even" (banker's rounding) — a convention where a value sitting exactly halfway rounds to whichever neighbor is even. Since 8 is even and 9 isn't, 41220.485 rounds down to 41220.48 under this rule.

But the script I generated for you formats the number using an f-string (f"{amount_median:,.2f}"), and Python's string-formatting machinery uses a different convention — "round half up" — which pushes that same exact value up to 41220.49.

I verified this directly: computing your real median gives the same underlying number either way, but round(median, 2) and pandas.Series.round(2) both produce 41220.48, while the f-string and format() produce 41220.49. Same data, same true value, two different rounding rules producing two different answers.

So the one-cent gap isn't a bug, and it isn't really "floating-point error" in the sense of a wrong calculation — it's that the benchmark was very likely generated using round() (banker's rounding), while my script displays the number using an f-string (round-half-up), and this particular median happens to land on the exact boundary where those two conventions disagree. That's a genuinely useful thing to have caught, since it's the kind of subtle discrepancy real analysts run into when comparing numbers computed by different tools or teams.

For your validation.md notes, you could write something like: "the true median is exactly 41220.485, sitting on a rounding boundary; Python's round()/pandas .round() use banker's rounding and produce 41220.48, while the script's f-string formatting uses round-half-up and produces 41220.49 — same value, different rounding conventions."'

---



## 2B — Explain the Code and Output



**Prompt 1 — paste your complete `hw02_eda.py` and ask:**
> "Walk me through each section of this script, including the grouping, correlation, and charting steps. What should I see in the terminal when I run it? List each expected output value explicitly."

**Prompt 2 — paste your complete terminal output (all lines) and ask:**
> "Here is the terminal output from running an EDA script on a wealth management transaction dataset. What does each value mean? Flag anything that looks unexpected or that I should investigate before using this data in an analysis."

### Questions:

**1. Did Claude's predicted outputs (Prompt 1) match what you actually saw in the terminal? List any discrepancies.** 

   *(your answer)*

**2. What did Claude flag as potentially unexpected or worth investigating (Prompt 2)?**

   *(your answer)*

**3. Did Claude mention the 101,597 null values in `security_id`? What explanation did it give?**

   *(your answer)*

**4. Did Claude flag the `txn_date` column as a concern? Why would that matter for a time-series analysis?**

   *(your answer)*

**5. Open your three chart files. Does what you see in each image match Claude's explanation of that section of the output? Note any differences.**

   *(your answer)*

**6. Paste one follow-up question you asked Claude, and Claude's answer.**

   *(your answer)*

---

## 2C — Business Check & Cross-Validation

### Business-reasonableness questions

*(Answer each in your own words — do not paste Claude's response as your answer here.)*

1. `security_id`, `shares`, and `price` are all null in exactly 101,597 rows. Looking at the `txn_type` value counts, which three transaction types would you expect to have no security — and why? Do the counts add up to 101,597?

   *(your answer)*

2. There are 83,556 Buy transactions and 59,755 Sell transactions. What does it mean for a wealth management firm to have significantly more Buys than Sells over a five-year period?

   *(your answer)*

3. The `txn_date` column is stored as a string rather than a date. If Claude Cowork generated code to compute the average number of days between transactions, what would go wrong if the dates remained as strings?

   *(your answer)*

4. Wildcat Capital has 2,700 clients served by 25 advisors. Is that ratio — roughly 108 clients per advisor — plausible for a registered investment advisory firm?

   *(your answer)*

5. 836 `Buy` transactions have negative `shares` values (as low as −499.63), while every other transaction type has only positive share values. What are two plausible business explanations for a negative share count on a Buy transaction, and what would you do next to determine which is more likely?

   *(your answer)*

### Cross-validation

Run both of the following as separate quick scripts from the VS Code terminal (ask Claude Cowork to write them):

- **Prompt A:** "Write Python to count rows in fact_transactions.csv where txn_type equals exactly 'Buy'."
- **Prompt B:** "Write Python to count the total rows in fact_transactions.csv, then subtract the count of rows where txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee."

6. What did each script return?

   *(your answer)*

7. Do the results agree? If not, which one is wrong and why?

   *(your answer)*

8. Why is it useful to verify a count using subtraction rather than direct filtering?

   *(your answer)*
