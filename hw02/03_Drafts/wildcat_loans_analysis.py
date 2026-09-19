"""
Wildcat Capital — Loan Portfolio Analysis
==========================================
Combines all exploratory analyses built for wildcat_loans_clean.csv into a
single program:

  1. Data overview: shape, column dtypes, missing value counts
  2. origination_date dtype check/conversion (object -> datetime)
  3. Missing-value audit: count/pct per column, plus a focused look at
     whether credit_score missingness is concentrated by loan_status /
     loan_purpose (random vs. non-random missingness)
  4. Descriptive statistics for all numeric columns (loan_amount to 2dp)
  5. Categorical frequency breakdowns: loan_purpose, loan_status, state
  6. Histogram of loan_amount (30 bins, mean/median lines) -> saved PNG
  7. Box plot of interest_rate by loan_status (horizontal) -> saved PNG
  8. Group-by summary: loan volume/pricing/risk metrics by loan_status
  9. Default rate by loan_purpose
  10. Correlation matrix (numeric columns, ID columns excluded) + top 5
      strongest correlations

Usage:
    python wildcat_loans_analysis.py [path_to_csv] [output_report_path]

If no CSV path is given, defaults to "wildcat_loans_clean.csv" in the current
directory. Chart images are saved to an "outputs" folder (created if needed)
relative to the current working directory. All printed output is also saved
to a text report — by default "outputs/analysis_report.txt" — while still
being shown in the console (pass a second argument to change the report path).
"""

import sys
import os
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
DATE_COLUMN = "origination_date"
ID_COLUMNS = ["loan_id", "borrower_id"]
CREDIT_SCORE_COLUMN = "credit_score"
STATUS_COLUMN = "loan_status"
PURPOSE_COLUMN = "loan_purpose"
STATE_COLUMN = "state"
LOAN_AMOUNT_COLUMN = "loan_amount"
INTEREST_RATE_COLUMN = "interest_rate"
DEBT_TO_INCOME_COLUMN = "debt_to_income_ratio"
ANNUAL_INCOME_COLUMN = "annual_income"

CATEGORICAL_COLUMNS = [PURPOSE_COLUMN, STATUS_COLUMN, STATE_COLUMN]
STATUS_ORDER = ["Current", "Paid Off", "Delinquent", "Default"]
TARGET_DEFAULT_STATUS = "Default"

OUTPUT_DIR = "outputs"
HIST_PATH = os.path.join(OUTPUT_DIR, "hist_loan_amount.png")
BOX_PATH = os.path.join(OUTPUT_DIR, "box_interest_by_status.png")
REPORT_PATH = os.path.join(OUTPUT_DIR, "analysis_report.txt")


class Tee:
    """Writes every print() call to multiple streams (e.g. console + file)."""

    def __init__(self, *streams):
        self.streams = streams

    def write(self, data):
        for stream in self.streams:
            stream.write(data)

    def flush(self):
        for stream in self.streams:
            stream.flush()


def section(title: str) -> None:
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)


# ----------------------------------------------------------------------
# 1. Data overview
# ----------------------------------------------------------------------
def data_overview(df: pd.DataFrame) -> None:
    section("1. DATA OVERVIEW — SHAPE, DTYPES, MISSING VALUES")
    print(f"Rows: {df.shape[0]}, Columns: {df.shape[1]}")

    summary = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing_count": df.isnull().sum(),
    })
    print("\n" + summary.to_string())


# ----------------------------------------------------------------------
# 2. origination_date dtype check/conversion
# ----------------------------------------------------------------------
def convert_origination_date(df: pd.DataFrame) -> pd.DataFrame:
    section("2. ORIGINATION_DATE — DTYPE CHECK / CONVERSION")

    if DATE_COLUMN not in df.columns:
        print(f"Column '{DATE_COLUMN}' not found — skipping.")
        return df

    before_dtype = df[DATE_COLUMN].dtype
    print(f"'{DATE_COLUMN}' dtype BEFORE: {before_dtype}")

    if pd.api.types.is_datetime64_any_dtype(df[DATE_COLUMN]):
        print(f"'{DATE_COLUMN}' is already stored as datetime — no conversion needed.")
        return df

    df = df.assign(**{DATE_COLUMN: pd.to_datetime(df[DATE_COLUMN])})
    after_dtype = df[DATE_COLUMN].dtype
    print(f"'{DATE_COLUMN}' dtype AFTER:  {after_dtype}")
    print(f"Converted '{DATE_COLUMN}' from {before_dtype} to {after_dtype}.")
    return df


# ----------------------------------------------------------------------
# 3. Missing-value audit + credit_score missingness pattern
# ----------------------------------------------------------------------
def missing_value_audit(df: pd.DataFrame) -> None:
    section("3. MISSING VALUES — COUNT AND PERCENTAGE BY COLUMN")

    counts = df.isnull().sum()
    pct = (counts / len(df) * 100).round(2)
    print(pd.DataFrame({"missing_count": counts, "missing_pct": pct}).to_string())

    if CREDIT_SCORE_COLUMN not in df.columns:
        return

    n_missing = df[CREDIT_SCORE_COLUMN].isnull().sum()
    if n_missing == 0:
        print(f"\nNo missing values in '{CREDIT_SCORE_COLUMN}' — skipping missingness pattern check.")
        return

    print(f"\nRows with missing '{CREDIT_SCORE_COLUMN}': {n_missing} "
          f"({n_missing / len(df) * 100:.2f}% of {len(df)} total rows)")

    missing_mask = df[CREDIT_SCORE_COLUMN].isnull()
    for col in [STATUS_COLUMN, PURPOSE_COLUMN]:
        if col not in df.columns:
            continue
        full_pct = (df[col].value_counts(normalize=True, dropna=False) * 100).round(2)
        missing_pct = (df.loc[missing_mask, col].value_counts(normalize=True, dropna=False) * 100).round(2)
        comparison = pd.DataFrame({
            "full_dataset_pct": full_pct,
            f"missing_{CREDIT_SCORE_COLUMN}_pct": missing_pct,
        }).fillna(0.0)
        comparison = comparison.assign(
            difference_pct_pts=(
                comparison[f"missing_{CREDIT_SCORE_COLUMN}_pct"] - comparison["full_dataset_pct"]
            ).round(2)
        ).sort_values("difference_pct_pts", ascending=False)

        print(f"\n{col.upper()} DISTRIBUTION: FULL DATASET vs. ROWS MISSING '{CREDIT_SCORE_COLUMN}'")
        print(comparison.to_string())


# ----------------------------------------------------------------------
# 4. Descriptive statistics
# ----------------------------------------------------------------------
def descriptive_statistics(df: pd.DataFrame) -> None:
    section("4. DESCRIPTIVE STATISTICS — NUMERIC COLUMNS")

    numeric_df = df.select_dtypes(include="number")
    stats = numeric_df.describe().round(2)

    pd.set_option("display.float_format", lambda x: f"{x:,.2f}")
    print(stats.to_string())

    if LOAN_AMOUNT_COLUMN in stats.columns:
        print(f"\n'{LOAN_AMOUNT_COLUMN}' statistics (2 decimal places):")
        for stat_name, value in stats[LOAN_AMOUNT_COLUMN].items():
            print(f"  {stat_name:>6}: {value:,.2f}")


# ----------------------------------------------------------------------
# 5. Categorical frequency breakdowns
# ----------------------------------------------------------------------
def categorical_frequencies(df: pd.DataFrame) -> None:
    section("5. CATEGORICAL FREQUENCY BREAKDOWNS")

    for column in CATEGORICAL_COLUMNS:
        if column not in df.columns:
            print(f"Column '{column}' not found — skipping.\n")
            continue

        counts = df[column].value_counts(dropna=False)
        pct = (counts / len(df) * 100).round(1)
        table = pd.DataFrame({"count": counts, "percentage": pct}).sort_values("count", ascending=False)

        print(f"\n{column.upper()} — VALUE COUNTS AND PERCENTAGES")
        for value, row in table.iterrows():
            print(f"  {str(value):<20} count: {int(row['count']):>6}   percentage: {row['percentage']:>5.1f}%")


# ----------------------------------------------------------------------
# 6. Histogram of loan_amount
# ----------------------------------------------------------------------
def plot_loan_amount_histogram(df: pd.DataFrame) -> None:
    section("6. CHART — LOAN AMOUNT HISTOGRAM")

    if LOAN_AMOUNT_COLUMN not in df.columns:
        print(f"Column '{LOAN_AMOUNT_COLUMN}' not found — skipping.")
        return

    mean_val = df[LOAN_AMOUNT_COLUMN].mean()
    median_val = df[LOAN_AMOUNT_COLUMN].median()

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.hist(df[LOAN_AMOUNT_COLUMN], bins=30, color="#4C72B0", edgecolor="white")
    ax.axvline(mean_val, color="#C44E52", linestyle="--", linewidth=2,
               label=f"Mean: ${mean_val:,.2f}")
    ax.axvline(median_val, color="#55A868", linestyle="--", linewidth=2,
               label=f"Median: ${median_val:,.2f}")
    ax.set_title("Distribution of Loan Amounts — Wildcat Capital Portfolio", fontsize=14)
    ax.set_xlabel("Loan Amount ($)")
    ax.set_ylabel("Number of Loans")
    ax.legend()
    fig.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.savefig(HIST_PATH, dpi=150)
    plt.close(fig)

    print(f"Saved histogram to: {HIST_PATH}")
    print(f"Mean loan amount:   ${mean_val:,.2f}")
    print(f"Median loan amount: ${median_val:,.2f}")


# ----------------------------------------------------------------------
# 7. Box plot of interest_rate by loan_status
# ----------------------------------------------------------------------
def plot_interest_rate_boxplot(df: pd.DataFrame) -> None:
    section("7. CHART — INTEREST RATE BY LOAN STATUS (BOX PLOT)")

    if INTEREST_RATE_COLUMN not in df.columns or STATUS_COLUMN not in df.columns:
        print("Required columns not found — skipping.")
        return

    data = [df.loc[df[STATUS_COLUMN] == category, INTEREST_RATE_COLUMN].dropna()
            for category in STATUS_ORDER]

    fig, ax = plt.subplots(figsize=(10, 6))
    try:
        ax.boxplot(data, vert=False, tick_labels=STATUS_ORDER, patch_artist=True,
                   boxprops=dict(facecolor="#4C72B0", alpha=0.7),
                   medianprops=dict(color="#C44E52", linewidth=2))
    except TypeError:
        ax.boxplot(data, vert=False, labels=STATUS_ORDER, patch_artist=True,
                   boxprops=dict(facecolor="#4C72B0", alpha=0.7),
                   medianprops=dict(color="#C44E52", linewidth=2))

    ax.set_title("Interest Rate by Loan Status", fontsize=14)
    ax.set_xlabel("Interest Rate (%)")
    ax.set_ylabel("Loan Status")
    fig.tight_layout()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    fig.savefig(BOX_PATH, dpi=150)
    plt.close(fig)

    print(f"Saved box plot to: {BOX_PATH}")
    print("\nMedian interest rate by loan status:")
    for category, series in zip(STATUS_ORDER, data):
        print(f"  {category:<12} n={len(series):>5}   median={series.median():.2f}%")


# ----------------------------------------------------------------------
# 8. Group-by summary by loan_status
# ----------------------------------------------------------------------
def groupby_loan_status(df: pd.DataFrame) -> None:
    section("8. SUMMARY BY LOAN_STATUS (sorted by count, descending)")

    required = [STATUS_COLUMN, LOAN_AMOUNT_COLUMN, INTEREST_RATE_COLUMN,
                CREDIT_SCORE_COLUMN, DEBT_TO_INCOME_COLUMN]
    if not all(c in df.columns for c in required):
        print("Required columns not found — skipping.")
        return

    summary = df.groupby(STATUS_COLUMN).agg(
        count=(STATUS_COLUMN, "size"),
        mean_loan_amount=(LOAN_AMOUNT_COLUMN, "mean"),
        mean_interest_rate=(INTEREST_RATE_COLUMN, "mean"),
        mean_credit_score=(CREDIT_SCORE_COLUMN, "mean"),
        mean_debt_to_income_ratio=(DEBT_TO_INCOME_COLUMN, "mean"),
    )
    summary = summary.assign(
        mean_loan_amount=summary["mean_loan_amount"].round(2),
        mean_interest_rate=summary["mean_interest_rate"].round(4),
        mean_credit_score=summary["mean_credit_score"].round(1),
        mean_debt_to_income_ratio=summary["mean_debt_to_income_ratio"].round(4),
    ).sort_values("count", ascending=False)

    print(summary.to_string())


# ----------------------------------------------------------------------
# 9. Default rate by loan_purpose
# ----------------------------------------------------------------------
def default_rate_by_purpose(df: pd.DataFrame) -> None:
    section(f"9. LOAN COUNT AND '{TARGET_DEFAULT_STATUS}' RATE BY {PURPOSE_COLUMN.upper()}")

    if PURPOSE_COLUMN not in df.columns or STATUS_COLUMN not in df.columns:
        print("Required columns not found — skipping.")
        return

    summary = df.groupby(PURPOSE_COLUMN).agg(
        count=(PURPOSE_COLUMN, "size"),
        default_count=(STATUS_COLUMN, lambda s: (s == TARGET_DEFAULT_STATUS).sum()),
    )
    summary = summary.assign(
        default_pct=(summary["default_count"] / summary["count"] * 100).round(1)
    ).sort_values("default_pct", ascending=False)

    print(summary.to_string())

    overall_default_pct = (df[STATUS_COLUMN] == TARGET_DEFAULT_STATUS).sum() / len(df) * 100
    print(f"\nOverall default rate across all loans: {overall_default_pct:.1f}%")


# ----------------------------------------------------------------------
# 10. Correlation matrix + top 5 strongest correlations
# ----------------------------------------------------------------------
def correlation_analysis(df: pd.DataFrame) -> None:
    section("10. CORRELATION MATRIX (numeric columns, excluding loan_id / borrower_id)")

    numeric_df = df.select_dtypes(include="number").drop(
        columns=[c for c in ID_COLUMNS if c in df.columns]
    )
    corr = numeric_df.corr()
    print(corr.round(2).to_string())

    pairs = corr.stack()
    pairs = pairs[pairs.index.get_level_values(0) < pairs.index.get_level_values(1)]
    pairs = pairs.reindex(pairs.abs().sort_values(ascending=False).index)
    top_5 = pairs.head(5)

    print("\nTOP 5 STRONGEST CORRELATIONS (by absolute value):")
    for (var1, var2), value in top_5.items():
        direction = "positive" if value > 0 else "negative"
        print(f"  {var1} <-> {var2}: r = {value:.2f} ({direction})")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
def main():
    file_path = sys.argv[1] if len(sys.argv) > 1 else "wildcat_loans_clean.csv"
    report_path = sys.argv[2] if len(sys.argv) > 2 else REPORT_PATH

    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)

    original_stdout = sys.stdout
    with open(report_path, "w", encoding="utf-8") as report_file:
        sys.stdout = Tee(original_stdout, report_file)
        try:
            print("WILDCAT CAPITAL — LOAN PORTFOLIO ANALYSIS")
            print(f"Generated: {datetime.now():%Y-%m-%d %H:%M:%S}")
            print(f"Source file: {file_path}")

            df = pd.read_csv(file_path)

            data_overview(df)
            df = convert_origination_date(df)
            missing_value_audit(df)
            descriptive_statistics(df)
            categorical_frequencies(df)
            plot_loan_amount_histogram(df)
            plot_interest_rate_boxplot(df)
            groupby_loan_status(df)
            default_rate_by_purpose(df)
            correlation_analysis(df)

            section("DONE")
            print(f"Charts saved to: {HIST_PATH}, {BOX_PATH}")
            print(f"Full text report saved to: {report_path}")
        finally:
            sys.stdout = original_stdout

    print(f"\n(Report also written to: {report_path})")


if __name__ == "__main__":
    main()
