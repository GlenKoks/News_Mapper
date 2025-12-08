"""Utilities for loading and preparing news publication data."""
from __future__ import annotations

import ast
from typing import Iterable, List

import pandas as pd

LIST_COLUMNS = [
    "bad_verdicts_list",
    "topics_verdicts_list",
    "persons",
    "organizations",
    "locations",
    "country",
]


def parse_list_cell(value) -> List[str]:
    """Safely parse a column that stores list-like values as text."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []

    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]

    if isinstance(value, str):
        cell = value.strip()
        if cell == "":
            return []

        try:
            parsed = ast.literal_eval(cell)
            if isinstance(parsed, (list, tuple, set)):
                return [str(v).strip() for v in parsed if str(v).strip()]
        except (ValueError, SyntaxError):
            pass

        if cell.startswith("[") and cell.endswith("]"):
            cell = cell[1:-1]

        return [part.strip().strip("'\"") for part in cell.split(",") if part.strip().strip("'\"")]

    return [str(value).strip()]


def format_list(items: Iterable[str]) -> str:
    """Return a human friendly representation of a list column."""
    cleaned = [str(item).strip() for item in items if str(item).strip()]
    return ", ".join(cleaned) if cleaned else "—"


def load_news_data(csv_path: str) -> pd.DataFrame:
    """Load the CSV file and normalize all important columns."""
    df = pd.read_csv(csv_path)

    for column in LIST_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(parse_list_cell)

    if "shows" in df.columns:
        df["shows"] = pd.to_numeric(df["shows"], errors="coerce").fillna(0).astype(int)

    if "dt" in df.columns:
        df["dt"] = pd.to_datetime(df["dt"], errors="coerce")

    if "publication_title_name" in df.columns:
        df["title_lower"] = df["publication_title_name"].str.lower()

    return df
