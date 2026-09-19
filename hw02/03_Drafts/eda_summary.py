"""
Week 2 Exercise - EDA Summary
Loads wildcat_loans_clean.csv and prints basic structural information:
  - shape (rows and columns)
  - column names with data types
  - count of missing values per column

Also saves the same results to a Markdown file (eda_summary.md) in the
same folder as this script.
"""

import pandas as pd
from pathlib import Path

# Path to the CSV file (relative to the project's data folder)
DATA_PATH = Path("02_Data") / "Raw" / "wildcat_loans_clean.csv"

# Where to save the Markdown report (same folder as this script)
OUTPUT_PATH = Path(__file__).resolve().parent / "eda_summary.md"


def build_report(df: pd.DataFrame) -> str:
    n_rows, n_cols = df.shape

    lines = []
    lines.append("# EDA Summary: wildcat_loans_clean.csv")
    lines.append("")

    lines.append("## Shape")
    lines.append("")
    lines.append(f"- Rows: {n_rows}")
    lines.append(f"- Columns: {n_cols}")
    lines.append("")

    lines.append("## Column Names and Data Types")
    lines.append("")
    lines.append("| Column | Data Type |")
    lines.append("|---|---|")
    for col, dtype in df.dtypes.items():
        lines.append(f"| {col} | {dtype} |")
    lines.append("")

    lines.append("## Missing Values per Column")
    lines.append("")
    lines.append("| Column | Missing Values |")
    lines.append("|---|---|")
    for col, count in df.isnull().sum().items():
        lines.append(f"| {col} | {count} |")
    lines.append("")

    return "\n".join(lines)


def main():
    df = pd.read_csv(DATA_PATH)

    # Shape
    n_rows, n_cols = df.shape
    print("=" * 50)
    print("SHAPE")
    print("=" * 50)
    print(f"Rows: {n_rows}")
    print(f"Columns: {n_cols}")
    print()

    # Column names and data types
    print("=" * 50)
    print("COLUMN NAMES AND DATA TYPES")
    print("=" * 50)
    print(df.dtypes.to_string())
    print()

    # Missing values per column
    print("=" * 50)
    print("MISSING VALUES PER COLUMN")
    print("=" * 50)
    print(df.isnull().sum().to_string())

    # Save the same results to a Markdown file
    report = build_report(df)
    OUTPUT_PATH.write_text(report)
    print()
    print(f"Report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
