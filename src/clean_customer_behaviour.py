"""Clean customer shopping behaviour data and optionally load it to SQL Server."""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "raw" / "customer_shopping_behavior.csv"
DEFAULT_OUTPUT = ROOT / "data" / "processed" / "customers_cleaned.csv"

# Map common header spellings to the canonical names used by the SQL queries.
ALIASES = {
    "customerid": "customer_id",
    "customer_id": "customer_id",
    "itempurchased": "item_purchased",
    "purchaseamountusd": "purchase_amount",
    "purchaseamount": "purchase_amount",
    "reviewrating": "review_rating",
    "subscriptionstatus": "subscription_status",
    "shippingtype": "shipping_type",
    "discountapplied": "discount_applied",
    "promocodeused": "promocode_used",
    "previouspurchases": "previous_purchases",
    "paymentmethod": "payment_method",
    "frequencyofpurchases": "frequency_of_purchases",
}

FREQUENCY_DAYS = {
    "weekly": 7,
    "fortnightly": 14,
    "bi-weekly": 14,
    "biweekly": 14,
    "monthly": 30,
    "quarterly": 90,
    "every 3 months": 90,
    "every three months": 90,
    "annually": 365,
    "annual": 365,
}


def normalise_column_name(name: object) -> str:
    """Convert a CSV header to a stable snake_case name and apply known aliases."""
    value = str(name).strip().lower()
    value = value.replace("&", " and ")
    value = re.sub(r"\(.*?\)", " ", value)
    value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
    compact = value.replace("_", "")
    return ALIASES.get(value, ALIASES.get(compact, value))


def clean_data(input_path: Path) -> pd.DataFrame:
    if not input_path.is_file():
        raise FileNotFoundError(
            f"Input CSV not found: {input_path}\n"
            "Add customer_shopping_behavior.csv to data/raw/ or pass --input."
        )

    df = pd.read_csv(input_path)
    df.columns = [normalise_column_name(column) for column in df.columns]

    duplicates = df.columns[df.columns.duplicated()].tolist()
    if duplicates:
        raise ValueError(
            "Column normalisation produced duplicate names: "
            + ", ".join(sorted(set(duplicates)))
        )

    required = {"age", "category", "purchase_amount", "review_rating", "frequency_of_purchases"}
    missing = sorted(required.difference(df.columns))
    if missing:
        raise ValueError(
            "The input CSV is missing required columns: " + ", ".join(missing)
            + ". Check the dataset headers before running this script."
        )

    # Convert core numeric fields explicitly so downstream calculations are reliable.
    for column in ("age", "purchase_amount", "review_rating", "previous_purchases"):
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    missing_before = int(df.isna().sum().sum())

    # Fill missing review ratings with the median for their product category;
    # use the overall median only if a category has no non-missing ratings.
    category_medians = df.groupby("category", dropna=False)["review_rating"].transform("median")
    overall_median = df["review_rating"].median()
    df["review_rating"] = df["review_rating"].fillna(category_medians)
    if pd.notna(overall_median):
        df["review_rating"] = df["review_rating"].fillna(overall_median)

    # Create four approximately equal-sized age groups. Ranking first avoids qcut
    # failures when multiple customers share the same age.
    labels = ["Young", "Adult", "Middle_aged", "Senior"]
    valid_age = df["age"].notna()
    df["age_group"] = pd.Series(pd.NA, index=df.index, dtype="object")
    age_count = int(valid_age.sum())
    if age_count:
        group_count = min(4, age_count)
        # Rank first so ties do not create duplicate quantile boundaries. This also
        # supports small sample files used to test the workflow.
        ranks = df.loc[valid_age, "age"].rank(method="first")
        df.loc[valid_age, "age_group"] = pd.qcut(
            ranks, q=group_count, labels=labels[:group_count]
        ).astype("object")

    frequency_key = df["frequency_of_purchases"].astype("string").str.strip().str.lower()
    df["purchase_frequency_in_days"] = frequency_key.map(FREQUENCY_DAYS).astype("Int64")

    # The two columns are removed as redundant only if their values are identical.
    if {"discount_applied", "promocode_used"}.issubset(df.columns):
        discount = df["discount_applied"].astype("string").str.strip().str.casefold()
        promo = df["promocode_used"].astype("string").str.strip().str.casefold()
        if discount.equals(promo):
            df = df.drop(columns="promocode_used")
            print("Dropped promocode_used because it duplicates discount_applied.")

    missing_after = int(df.isna().sum().sum())
    print(f"Loaded {len(df):,} rows and {len(df.columns):,} columns.")
    print(f"Missing values before cleaning: {missing_before:,}; after: {missing_after:,}.")
    print("Prepared age_group and purchase_frequency_in_days.")
    return df


def load_to_sql_server(df: pd.DataFrame) -> None:
    """Replace dbo.Customers using Windows integrated authentication."""
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.engine import URL
    except ImportError as exc:
        raise RuntimeError("SQLAlchemy is required. Install requirements.txt first.") from exc

    server = os.getenv("SQLSERVER_SERVER", r"localhost\SQLEXPRESS")
    database = os.getenv("SQLSERVER_DATABASE", "Customer_Behaviour")
    driver = os.getenv("SQLSERVER_DRIVER", "ODBC Driver 17 for SQL Server")
    connection_string = (
        f"DRIVER={{{driver}}};SERVER={server};DATABASE={database};"
        "Trusted_Connection=yes;TrustServerCertificate=yes;"
    )
    url = URL.create("mssql+pyodbc", query={"odbc_connect": connection_string})
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            df.to_sql("Customers", con=connection, schema="dbo", if_exists="replace", index=False)
        print(f"Loaded {len(df):,} rows into {database}.dbo.Customers (table replaced).")
    finally:
        engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to source CSV")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path for cleaned CSV")
    parser.add_argument(
        "--load-to-sql-server", action="store_true",
        help="Also replace dbo.Customers in the configured SQL Server database",
    )
    args = parser.parse_args()

    try:
        df = clean_data(args.input)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.output, index=False)
        print(f"Saved cleaned data to: {args.output}")
        if args.load_to_sql_server:
            load_to_sql_server(df)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
