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

REQUIRED_COLUMNS = [
    "dt",
    "publication_title_name",
    "shows",
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

    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            default_value = 0 if column == "shows" else ""
            df[column] = [default_value for _ in range(len(df))]

    for column in LIST_COLUMNS:
        if column in df.columns:
            df[column] = df[column].apply(parse_list_cell)
        else:
            df[column] = [[] for _ in range(len(df))]

    df["shows"] = pd.to_numeric(df["shows"], errors="coerce").fillna(0).astype(int)

    df["dt"] = pd.to_datetime(df["dt"], errors="coerce").dt.tz_localize(None)

    df["publication_title_name"] = df["publication_title_name"].fillna("")
    df["title_lower"] = df["publication_title_name"].str.lower()

    return df
