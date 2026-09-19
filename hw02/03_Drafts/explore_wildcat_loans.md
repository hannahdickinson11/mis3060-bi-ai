# Full Data Exploration: wildcat_loans_clean.csv

## Shape

- Rows: 2340
- Columns: 12

## Column Overview

| Column | Data Type | Missing | Missing % | Distinct Values |
|---|---|---|---|---|
| loan_id | int64 | 0 | 0.0% | 2340 |
| origination_date | str | 0 | 0.0% | 1660 |
| borrower_id | int64 | 0 | 0.0% | 2340 |
| loan_amount | float64 | 0 | 0.0% | 2340 |
| interest_rate | float64 | 0 | 0.0% | 1198 |
| loan_term_months | int64 | 0 | 0.0% | 4 |
| credit_score | float64 | 47 | 2.01% | 336 |
| debt_to_income_ratio | float64 | 0 | 0.0% | 1837 |
| loan_purpose | str | 0 | 0.0% | 5 |
| loan_status | str | 0 | 0.0% | 4 |
| annual_income | float64 | 0 | 0.0% | 2340 |
| state | str | 0 | 0.0% | 27 |

## Numeric Column Statistics

| Column | Count | Mean | Std | Min | 25% | 50% | 75% | Max | Missing |
|---|---|---|---|---|---|---|---|---|---|
| loan_id | 2340 | 1170.50 | 675.64 | 1.00 | 585.75 | 1170.50 | 1755.25 | 2340.00 | 0 |
| borrower_id | 2340 | 1258.05 | 732.22 | 1.00 | 619.75 | 1253.50 | 1895.50 | 2525.00 | 0 |
| loan_amount | 2340 | 68398.49 | 92614.38 | 2073.62 | 24498.05 | 40691.79 | 60596.09 | 499030.58 | 0 |
| interest_rate | 2340 | 11.89 | 4.49 | 4.50 | 8.10 | 11.52 | 15.34 | 20.98 | 0 |
| loan_term_months | 2340 | 68.69 | 27.29 | 36.00 | 36.00 | 60.00 | 84.00 | 120.00 | 0 |
| credit_score | 2293 | 674.39 | 75.98 | 500.00 | 614.00 | 676.00 | 725.00 | 850.00 | 47 |
| debt_to_income_ratio | 2340 | 0.32 | 0.14 | 0.08 | 0.20 | 0.32 | 0.44 | 0.55 | 0 |
| annual_income | 2340 | 155095.67 | 182699.38 | 24014.42 | 32742.90 | 42624.11 | 255153.52 | 649768.69 | 0 |

## Categorical Column Value Counts

### origination_date (1660 distinct values)

| Value | Count |
|---|---|
| 2018-03-18 | 6 |
| 2022-08-24 | 5 |
| 2017-08-28 | 5 |
| 2020-07-30 | 4 |
| 2018-02-16 | 4 |
| 2021-06-30 | 4 |
| 2021-02-01 | 4 |
| 2022-04-23 | 4 |
| 2023-06-01 | 4 |
| 2020-12-18 | 4 |

### loan_purpose (5 distinct values)

| Value | Count |
|---|---|
| Home Improvement | 724 |
| Auto | 603 |
| Personal | 475 |
| Business | 328 |
| Education | 210 |

### loan_status (4 distinct values)

| Value | Count |
|---|---|
| Current | 1454 |
| Paid Off | 532 |
| Delinquent | 248 |
| Default | 106 |

### state (27 distinct values)

| Value | Count |
|---|---|
| PA | 384 |
| NJ | 272 |
| NY | 264 |
| TX | 132 |
| FL | 128 |
| CA | 115 |
| DE | 97 |
| VA | 94 |
| MD | 92 |
| MA | 87 |

## Duplicate Checks

- Fully duplicate rows: 0
- Duplicate values in `loan_id`: 0
- Duplicate values in `borrower_id`: 0

## Correlation Matrix (Numeric Columns)

| | loan_id | borrower_id | loan_amount | interest_rate | loan_term_months | credit_score | debt_to_income_ratio | annual_income |
|---|---|---|---|---|---|---|---|---|
| loan_id | 1.0 | -0.0 | 0.01 | -0.02 | -0.01 | 0.03 | 0.02 | 0.01 |
| borrower_id | -0.0 | 1.0 | 0.0 | -0.02 | 0.04 | 0.0 | 0.01 | 0.01 |
| loan_amount | 0.01 | 0.0 | 1.0 | -0.01 | 0.0 | 0.03 | -0.01 | 0.02 |
| interest_rate | -0.02 | -0.02 | -0.01 | 1.0 | 0.01 | -0.84 | -0.0 | 0.05 |
| loan_term_months | -0.01 | 0.04 | 0.0 | 0.01 | 1.0 | -0.01 | 0.02 | -0.0 |
| credit_score | 0.03 | 0.0 | 0.03 | -0.84 | -0.01 | 1.0 | 0.0 | -0.04 |
| debt_to_income_ratio | 0.02 | 0.01 | -0.01 | -0.0 | 0.02 | 0.0 | 1.0 | -0.01 |
| annual_income | 0.01 | 0.01 | 0.02 | 0.05 | -0.0 | -0.04 | -0.01 | 1.0 |
