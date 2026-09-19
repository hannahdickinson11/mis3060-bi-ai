# Specification: EDA Script for Transaction Data

## Purpose

Write one single Python script that performs a complete exploratory data analysis (EDA) of a transactions dataset. The script must run start to finish in one execution and produce console output, a saved text summary, and three saved chart images. Do not split this into multiple scripts or multiple files — everything described below belongs in one Python file.

## Input

The script should load the file `data/raw/fact_transactions.csv` into a pandas DataFrame. Assume this path is relative to the location where the script is run.

## Required Behavior

The script must perform each of the following steps, in order, during a single run:

1. Load `data/raw/fact_transactions.csv` into a pandas DataFrame.

2. Print the shape of the DataFrame as rows × columns.

3. Print every column name along with its data type.

4. Print the count of missing (null) values for every column.

5. Print descriptive statistics for all numeric columns: count, mean, standard deviation, minimum, 25th percentile, median, 75th percentile, and maximum.

6. Print value counts and percentages for the `txn_type` column, sorted from most frequent to least frequent.

7. Print the number of unique clients, the number of unique advisors, and the number of unique securities referenced anywhere in the file.

8. Print the earliest and latest values of `txn_date`, showing the overall date range covered by the dataset.

9. Check for duplicate rows based on `txn_id` and print how many duplicates were found.

10. Print the mean, median, and skewness of the `amount` column.

11. Group the data by `txn_type`. For each group, print the count of rows and the mean and median of `amount`, each rounded to 2 decimal places. Sort the groups by mean amount, from highest to lowest.

12. Compute the correlation matrix for the `shares`, `price`, and `amount` columns, rounded to 2 decimal places, and print it. Then identify and print the three strongest correlations among these variables, excluding any variable's correlation with itself.

13. Print the minimum value, maximum value, and count of negative values in the `shares` column, broken out separately for each `txn_type`.

14. Compare the DataFrame's shape to the expected shape of (298772, 9). If the shape does not match, print a clearly visible warning message.

15. Create and save three charts to a folder named `hw02/charts/`:
    - A histogram of the `amount` column, with vertical lines marking the mean and the median, each clearly labeled (e.g., in a legend or with text annotations). Save this as `hw02/charts/hist_amount.png`.
    - A horizontal box plot showing the distribution of `amount` broken out by `txn_type`. Save this as `hw02/charts/box_amount_by_type.png`.
    - A scatter plot with `shares` on the x-axis and `amount` on the y-axis, with points colored according to `txn_type` (include a legend identifying the colors). Save this as `hw02/charts/scatter_shares_amount.png`.

16. Save a plain-text summary containing the output from items 2 through 13 (shape, column names/types, missing values, descriptive statistics, `txn_type` value counts/percentages, unique counts, date range, duplicate count, mean/median/skewness of `amount`, grouped statistics by `txn_type`, the correlation matrix and top three correlations, and the `shares` min/max/negative-count breakdown) to a file named `hw02/hw02_profile.txt`. Everything printed to the console for those items should also be written to this file, in the same order.

17. Include a comment block at the very top of the script identifying: the name/purpose of the script, the dataset it analyzes, the author, and the date the script was generated.

## Output Requirements Summary

- All console output listed above should print when the script is run.
- Three PNG chart files must be saved to `hw02/charts/` with the exact filenames specified.
- One text file, `hw02/hw02_profile.txt`, must be saved containing the summary described in item 16.
- The script itself should be a single `.py` file that accomplishes all of this in one run — no separate scripts, no manual steps in between.

## Notes for Implementation

- The script should handle the data cleanly and use standard, well-documented pandas/matplotlib (or equivalent) functionality.
- Output should be clearly labeled throughout (e.g., section headers or descriptive print statements before each block of output) so that a reader can tell which step's results they are looking at.
- Folders referenced for output (`hw02/charts/`) should be created by the script if they do not already exist, so the script does not fail due to a missing folder.
