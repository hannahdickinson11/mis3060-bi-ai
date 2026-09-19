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

   The structure and logic of Claude's predicted outputs match what what I saw. They show the same section order, same header, same descending sort order, same rounding, and same chart filenames. However, there were no actual numeric predictions to compare since Prompt 1's session had no data and used placeholders when answering. The one specific discrepancy across the two: Claude showed `security_id` as `int64`, but the real output shows `float64`. A column with missing values can not stay an integer in the pandas version so it gets upgraded to float automatically. The response also showed `txn_date`/`txn_type` as `object`dtype , while the real output `str`. This was also addressed in Question 2A above.


**2. What did Claude flag as potentially unexpected or worth investigating (Prompt 2)?**

   The three main things that Claude flagged as unexpected or worth investigating were: The Advisory Fee Group's mean ($7,375.17) being over 8x its median ($859.12). This is a much bigger mean/median gap that any other transaction type in the dataset, suggesting either outlier fees (e.g., flat fees vs. AUM-based fees) or two blended fee structures. The other aspect Claude suggested I investigate was the negative share Buy transactions. It suggested that prior to running the program, I should pull those 836 rows out and look for a pattern in the data. Finally, Claude noted the round bounds on `price` ($10-$500) `shares` (~500 max) as a sign that the data may be simulated rather than real market data, and also flagged that `security_id` should be cast to a nullable integer type bedore using it as a join key.

**3. Did Claude mention the 101,597 null values in `security_id`? What explanation did it give?**

   Yes, and it gave a specific, verifiable explanation: 101,597 exactly equals Deposit (35,981) + Advisory Fee (35,766) + Withdrawal (29,850) rows added together. Claude's point was that these three transaction types never involve a security (you don't buy shares when making a deposit). So, these nulls are not due to data quality defects.

**4. Did Claude flag the `txn_date` column as a concern? Why would that matter for a time-series analysis?**

   No, it didn't flag `txn_date`'s string type as a concern in this response. Claude only confirmed the date range looked correct. It did not comment on the fact that it's stored as test rather than an actual date type. This would matter for a time-series analysis because as long as it stays a string, you can't do real math on it. All operations with the data would fail outright or produce the wrong results on text. Due to this, I would need to convert it to pd.`pd.to_datetime` first, same as the internal script does for section 8.

**5. Open your three chart files. Does what you see in each image match Claude's explanation of that section of the output? Note any differences.**

   For the most part yes with one interesting mismatch worth noting: the histogram and scatter plot match what was described. But the box plot has a subtle ordering difference - the code `txn_type` by mean amount descending (Dividend highest, Advisory Fee lowest) before building the chart, but when you actually open `box_amount_by_type.png`, Advisory Fee appears at the top and Dividend at the bottom. This is what the reverse of what "sort descending" would suggest. This happens because matplotlib's horizontal box plot draws the first item in the list at the bottom, not the top. 

**6. Paste one follow-up question you asked Claude, and Claude's answer.**

   *Input:* "You said the negative shares values on those Buy transactions help suppress the correlation between shares and amount — can you explain simply, why negative values would weaken that correlation?"


   *Output:* "Negative shares means those rows move in the opposite direction from the rest of the data - amount stays positive while shares goes negative, instead of both rising and falling together like normal rows do. That mismatch pulls the overall correlation down a bit, since correlation measures how consistently two variables move the same way."


---

## 2C — Business Check & Cross-Validation

### Business-reasonableness questions



*1. `security_id`, `shares`, and `price` are all null in exactly 101,597 rows. Looking at the `txn_type` value counts, which three transaction types would you expect to have no security — and why? Do the counts add up to 101,597?*

   *Deposit and withdrawal is just cash moving in or out of your account, so there no stock or bond changes hands - therefore there is nothing to fill in for `security_id`, `shares`, and `price`. Only Buy, Sell, and Dividend involve securities and thus do not have null values. The counts do check out with Deposit (35,981) + Advisory Fee (35,766) + Withdrawal (29,850) = 101,597. This matches the null count exactly. 

*2. There are 83,556 Buy transactions and 59,755 Sell transactions. What does it mean for a wealth management firm to have significantly more Buys than Sells over a five-year period?*

   Having more Buys (83,556) than Sells (59,755) over five years shows there is a higher demand than supply, signaling net accumulation. So, essentially, clients are adding to their portfolios faster than they are liquidatig them. This is consistent with a growing client group bringing in new money to invest and/or a longer term buy and hold investment strategy.

*3. The `txn_date` column is stored as a string rather than a date. If Claude Cowork generated code to compute the average number of days between transactions, what would go wrong if the dates remained as strings?*

   Since the data is in string form, you can't subtract two text strings to get a number and so Python would most likely show an error. Simple arthmetic would not work e.g. "days between transaction A and B" because it requires real date objects. 

*4. Wildcat Capital has 2,700 clients served by 25 advisors. Is that ratio — roughly 108 clients per advisor — plausible for a registered investment advisory firm?*

   Yes, 108 clients per advisor is a plausible ratio for a registered investment advisory firm. Typical advisor have roughly 50 to 150+ clients depending on their firm's level of services. More personal boutiqe level shops run lower while larger firms with more staff have higher client numbers. 

*5. 836 `Buy` transactions have negative `shares` values (as low as −499.63), while every other transaction type has only positive share values. What are two plausible business explanations for a negative share count on a Buy transaction, and what would you do next to determine which is more likely?*

   Two plausible business explanations could be 1)a data entry error where someone recorded the value incorrectly or 2)it could be on purpose - like the systemm logging a cancelled or corrected purchase as a negative Buy instead of using a separate reveal category. To determine which is more likely, I would look at those 836 rows for a pattern - possibly the same advisor, same security type, same dates - and then check if any of them matches the earlier Buy of the same size. If there is a clear pattern, it was probably intentional while randomness suggests an error. 

### Cross-validation

- **Prompt A:** "Write Python to count rows in fact_transactions.csv where txn_type equals exactly 'Buy'."
- **Prompt B:** "Write Python to count the total rows in fact_transactions.csv, then subtract the count of rows where txn_type is Sell, Deposit, Withdrawal, Dividend, or Advisory Fee."

#### 6. What did each script return?

*Prompt A*: 83,556 Buy transactions

*Prompt B*: 83,556 Buy transactions

#### 7. Do the results agree? If not, which one is wrong and why?

Yes they agree, both result in 83,556 Buy transactions. Both counting methods land on the same number and it also matches the known benchmark from the assignment, so there is strong evidence that this count is correct. 

#### 8. Why is it useful to verify a count using subtraction rather than direct filtering?

Direct filtering just trusts that one line of code is right. If there's a typo or mistake in it, you'd never know. Subtraction gives you an secondary independent way to get the same number, so if something were to be wrong, the two counts wouldn't match. 