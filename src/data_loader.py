"""Load data from SQL, clean it with pandas, save to CSV/Parquet."""
import sqlite3
from pathlib import Path

import pandas as pd


def load_from_sql(db_path: str, query: str) -> pd.DataFrame:
    """Run a SQL query on a SQLite database and return a DataFrame."""
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Basic cleaning: tidy column names, drop duplicates and empty rows."""
    df = df.copy()
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.drop_duplicates()
    df = df.dropna(how="all")
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df.reset_index(drop=True)


def save_data(df: pd.DataFrame, out_path: str) -> None:
    """Save a DataFrame as CSV or Parquet, based on the file extension."""
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix == ".parquet":
        df.to_parquet(path, index=False)
    elif path.suffix == ".csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Use a .csv or .parquet file extension")


if __name__ == "__main__":
    df = load_from_sql("data/sample.db", "SELECT * FROM my_table")
    df = clean_data(df)
    save_data(df, "data/clean/clean_data.parquet")
    print(f"Saved {len(df)} rows")
