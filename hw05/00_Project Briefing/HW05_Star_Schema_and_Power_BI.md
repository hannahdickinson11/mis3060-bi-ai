# HW5: Modeling the Wildcat Capital Data as a Star Schema in Power BI
## MIS3060 Business Intelligence with AI | Villanova University
### Covers Week 8: dimensional modeling and Power BI

> **Due:** *(instructor: set date)* | **Weight:** *(set in Brightspace)* | **Individual** | 
> **Submission:** push to your `mis3060-bi-ai` repo, folder `hw05/`, and paste the folder URL into Brightspace
> **Tools:** Claude Desktop drafts every script · VS Code runs it · Claude Code reviews it before you commit · Power BI Desktop (Apporto virtual desktop) for the model

---

## Overview

In HW4 you cleaned the Wildcat Capital tables. Here you work out **how the clean tables fit together** and show it in Power BI. You do not build new tables: no surrogate keys, no flattening, no new columns. The work is understanding what each table is, which columns link them, and how each number is allowed to be added up.

You will:
1. Identify every **primary key** and **foreign key**
2. State the **grain** of each fact table
3. Classify every fact **measure** as additive, semi-additive or non-additive
4. Load the tables into Power BI and build the **star schema** with its relationships

Your model is the foundation for Assignment 6 (DAX measures). A wrong key type or relationship here will break every measure there.

## Data

Folder: `Wildcat Capital Clean/`, released after HW4 is due. Use only these eight files so that everyone models identical data:

| File | Rows | Cols | Role |
|---|---:|---:|---|
| `dim_advisor.csv` | 25 | 7 | Advisors |
| `dim_benchmark.csv` | 8 | 4 | Performance benchmarks |
| `dim_client.csv` | 2,500 | 14 | Clients |
| `dim_date.csv` | 1,827 | 12 | Calendar, 2020–2024 |
| `dim_security.csv` | 500 | 8 | Securities and ETFs |
| `fact_fees.csv` | 122,197 | 8 | Monthly fee charges |
| `fact_portfolio_snapshot.csv` | 129,547 | 14 | Monthly account snapshots |
| `fact_transactions.csv` | 298,572 | 10 | Trades, income, cash flows, fee debits |


---

## Part A — Keys (20 points)
In `star_design.md`, give a table with one row per table: **fact or dimension**, **primary key**, and every **foreign key** with the table and column it points to.

**Example of the table format** (a different dataset: a small retail sales star). Your table has one row for each of the eight Wildcat tables:

| Table | Type | Primary key | Foreign keys (column → table[column]) |
|---|---|---|---|
| dim_store | Dimension | `store_id` | `region_id` → dim_region[region_id] |
| dim_region | Dimension | `region_id` | — |
| dim_product | Dimension | `product_id` | — |
| dim_date | Dimension | `date_id` | — |
| fact_sales | Fact | `sale_id` | `store_id` → dim_store[store_id]<br>`product_id` → dim_product[product_id]<br>`sale_date` → dim_date[date] |

- List **every** foreign key, including any in dimension tables (here `dim_store` points to `dim_region`)
- Name the **column** each foreign key matches, not just the table: `sale_date` matches `dim_date[date]`, not `dim_date[date_id]`. Check which column the Wildcat fact dates actually match
- Write "—" when a table has no foreign keys; note any key that can legitimately be blank and why

## Part B — Grain (10 points)
In star_design.md, for each fact table, write one sentence beginning "One row represents …". 

## Part C — Measures (20 points)
In `star_design.md`, list **every numeric column in every fact table**. For each, state whether it is **additive**, **semi-additive** or **non-additive**, and say in one sentence what that means for how it may be summed or averaged. Then list separately:
- numeric columns that are **not measures** (keys, date parts, flags)
- numeric **attributes in the dimension tables** that should never be summed

*Hint:* ask "if I add this value across the dimension, what does the total represent?" about clients, about months, and about both.

## Part D — Power BI model (25 points)
Follow `powerbi_guide.md`. Load the eight tables, set the column types, create your relationships, and mark the date table. Not every foreign key from Part A has to become a relationship; you will explain your choices in Part E. Deliver:

- `powerbi/hw05.pbix` — your saved model. 
- `powerbi/model_view.png` — full Model view screenshot, every table and relationship visible

## Part E — Relationships and design questions (15 points)
In `star_design.md`, explain the model you built in Part D:

Answer each design question in a short paragraph:
   - **(a)** Some transaction rows have no `security_id`. Why? and is that a defect?
   - **(b)** `advisor_id` appears in `dim_client` and on all three fact tables. Which relationship(s) did you keep active, and why?
   - **(c)** The date dimension has its own `date_id`, but the facts store calendar dates. Which column did you join on, and why?
   - **(d)** Star or snowflake: does anything in the eight tables connect one dimension to another? Did you keep it?

## Part F — Reflection (10 points)
Write three business questions a Wildcat Capital manager might ask, one for each fact table. Which could you answer in a single visual with no DAX workaround? Which could not, and what would you change in the schema to fix that? (in `star_design.md`)

---

## Submission checklist
- [ ] `README.md` (structure, how to run, Claude Code findings)
- [ ] `star_design.md` (Parts A, B, C, E and F)
- [ ] `powerbi/hw05.pbix` · `powerbi/model_view.png` ·

> If your `.pbix` exceeds GitHub's 100 MB file limit, upload it to Brightspace and say so in `README.md`.

## Grading rubric *(indicative — set final weights in Brightspace)*
| Component | Pts | Full credit |
|---|---:|---|
| A Keys | 20 | Every PK and FK identified; uniqueness and integrity proven in code |
| B Grain | 10 | Correct one-sentence grains with a uniqueness check in the script |
| C Measures | 20 | Every fact measure classified correctly with a reason; non-measures separated |
| D Power BI model | 25 | `.pbix` submitted; correct relationships, cardinality, direction and types; date table marked; row counts reconcile |
| E Relationships and design | 15 | Conformed dimensions named; omitted/inactive relationships explained; defended answers to (a)–(d) |
| F Reflection | 10 | Honest assessment of what the model can and cannot answer |
