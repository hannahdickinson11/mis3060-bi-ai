"""
Week 2 Exercise - Full Data Exploration
Loads wildcat_loans_clean.csv and produces a comprehensive profile:
  - shape, column types, missing values
  - descriptive statistics for numeric columns
  - value counts for categorical columns
  - duplicate row / duplicate ID checks
  - correlation matrix for numeric columns

Prints everything to the terminal and also saves it all to
explore_wildcat_loans.md in the same folder as this script.
"""

import pandas as pd
from pathlib import Path

pd.set_option("display.max_columns", None)
pd.set_option("display.width", 120)

DATA_PATH = Path("02_Data") / "Raw" / "wildcat_loans_clean.csv"
OUTPUT_PATH = Path(__file__).resolve().parent / "explore_wildcat_loans.md"

# Columns that look like unique identifiers - excluded from "categorical"
# value-count profiling since every value is (near) unique.
ID_LIKE_COLUMNS = {"loan_id", "borrower_id"}


def section(title: str) -> str:
    bar = "=" * 60
    return f"\n{bar}\n{title}\n{bar}"


def main():
    df = pd.read_csv(DATA_PATH)
    md_lines = ["# Full Data Exploration: wildcat_loans_clean.csv", ""]

    # ------------------------------------------------------------------
    # 1. Shape
    # ------------------------------------------------------------------
    n_rows, n_cols = df.shape
    print(section("SHAPE"))
    print(f"Rows: {n_rows}")
    print(f"Columns: {n_cols}")

    md_lines += [
        "## Shape",
        "",
        f"- Rows: {n_rows}",
        f"- Columns: {n_cols}",
        "",
    ]

    # ------------------------------------------------------------------
    # 2. Column names, data types, missing values
    # ------------------------------------------------------------------
    print(section("COLUMNS: DATA TYPE / MISSING / DISTINCT"))
    overview = pd.DataFrame({
        "dtype": df.dtypes.astype(str),
        "missing": df.isnull().sum(),
        "missing_pct": (df.isnull().sum() / n_rows * 100).round(2),
        "distinct": df.nunique(),
    })
    print(overview.to_string())

    md_lines += ["## Column Overview", ""]
    md_lines.append("| Column | Data Type | Missing | Missing % | Distinct Values |")
    md_lines.append("|---|---|---|---|---|")
    for col, row in overview.iterrows():
        md_lines.append(
            f"| {col} | {row['dtype']} | {row['missing']} | {row['missing_pct']}% | {row['distinct']} |"
        )
    md_lines.append("")

    # ------------------------------------------------------------------
    # 3. Descriptive statistics for numeric columns
    # ------------------------------------------------------------------
    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    if numeric_cols:
        print(section("NUMERIC COLUMN STATISTICS"))
        desc = df[numeric_cols].describe().T
        desc["missing"] = df[numeric_cols].isnull().sum()
        print(desc.to_string())

        md_lines += ["## Numeric Column Statistics", ""]
        md_lines.append(
            "| Column | Count | Mean | Std | Min | 25% | 50% | 75% | Max | Missing |"
        )
        md_lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for col, row in desc.iterrows():
            md_lines.append(
                f"| {col} | {row['count']:.0f} | {row['mean']:.2f} | {row['std']:.2f} | "
                f"{row['min']:.2f} | {row['25%']:.2f} | {row['50%']:.2f} | {row['75%']:.2f} | "
                f"{row['max']:.2f} | {int(row['missing'])} |"
            )
        md_lines.append("")

    # ------------------------------------------------------------------
    # 4. Value counts for categorical (non-numeric, non-ID) columns
    # ------------------------------------------------------------------
    categorical_cols = [
        c for c in df.select_dtypes(exclude="number").columns
        if c not in ID_LIKE_COLUMNS
    ]
    if categorical_cols:
        print(section("CATEGORICAL COLUMN VALUE COUNTS"))
        md_lines += ["## Categorical Column Value Counts", ""]
        for col in categorical_cols:
            n_unique = df[col].nunique()
            print(f"\n--- {col} ({n_unique} distinct values) ---")
            counts = df[col].value_counts(dropna=False).head(10)
            print(counts.to_string())

            md_lines.append(f"### {col} ({n_unique} distinct values)")
            md_lines.append("")
            md_lines.append("| Value | Count |")
            md_lines.append("|---|---|")
            for val, cnt in counts.items():
                md_lines.append(f"| {val} | {cnt} |")
            md_lines.append("")

    # ------------------------------------------------------------------
    # 5. Duplicate checks
    # ------------------------------------------------------------------
    print(section("DUPLICATE CHECKS"))
    dup_rows = df.duplicated().sum()
    print(f"Fully duplicate rows: {dup_rows}")

    md_lines += ["## Duplicate Checks", "", f"- Fully duplicate rows: {dup_rows}"]

    for id_col in ID_LIKE_COLUMNS:
        if id_col in df.columns:
            dup_ids = df[id_col].duplicated().sum()
            print(f"Duplicate values in '{id_col}': {dup_ids}")
            md_lines.append(f"- Duplicate values in `{id_col}`: {dup_ids}")
    md_lines.append("")

    # ------------------------------------------------------------------
    # 6. Correlation matrix for numeric columns
    # ------------------------------------------------------------------
    if len(numeric_cols) > 1:
        print(section("CORRELATION MATRIX (numeric columns)"))
        corr = df[numeric_cols].corr().round(2)
        print(corr.to_string())

        md_lines += ["## Correlation Matrix (Numeric Columns)", ""]
        header = "| |" + "".join(f" {c} |" for c in corr.columns)
        sep = "|---|" + "".join("---|" for _ in corr.columns)
        md_lines.append(header)
        md_lines.append(sep)
        for idx, row in corr.iterrows():
            md_lines.append(f"| {idx} |" + "".join(f" {v} |" for v in row))
        md_lines.append("")

    # ------------------------------------------------------------------
    # Save Markdown report
    # ------------------------------------------------------------------
    OUTPUT_PATH.write_text("\n".join(md_lines))
    print(section("DONE"))
    print(f"Full report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
