"""Data loading and preprocessing utilities for the News Analytics dashboard."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

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


@dataclass
class DataModel:
    """In-memory model storing the main dataset and precomputed helpers."""

    data: pd.DataFrame
    persons_exploded: pd.DataFrame
    organizations_exploded: pd.DataFrame
    locations_exploded: pd.DataFrame
    countries_exploded: pd.DataFrame
    daily_stats: pd.DataFrame

    @classmethod
    def from_csv(
        cls,
        csv_path: str,
        cache_path: Optional[str] = "news_cache.parquet",
        chunksize: int = 100_000,
        max_rows: Optional[int] = None,
    ) -> "DataModel":
        """Load CSV (or zipped CSV) efficiently, optionally using parquet cache.

        Args:
            csv_path: Path to CSV or zipped CSV.
            cache_path: Optional parquet cache path. When `max_rows` is provided,
                a distinct cache file with the limit encoded in its name is used
                to avoid re-reading the full dataset.
            chunksize: Number of rows per chunk for streaming reads.
            max_rows: Optional cap on rows to load for faster experimentation.
        """
        csv_file = Path(csv_path)
        cache_file = Path(cache_path) if cache_path else None
        if cache_file and max_rows:
            cache_file = cache_file.with_name(f"{cache_file.stem}_limit{max_rows}{cache_file.suffix}")
        compression = "zip" if csv_file.suffix.lower() == ".zip" else "infer"

        if cache_file and cache_file.exists():
            df = pd.read_parquet(cache_file)
        else:
            chunks: List[pd.DataFrame] = []
            remaining = max_rows
            for chunk in pd.read_csv(csv_file, chunksize=chunksize, compression=compression):
                if remaining is not None and remaining <= 0:
                    break

                if remaining is not None and len(chunk) > remaining:
                    chunk = chunk.iloc[:remaining]

                for column in LIST_COLUMNS:
                    if column in chunk.columns:
                        chunk[column] = chunk[column].apply(parse_list_cell)

                if "shows" in chunk.columns:
                    chunk["shows"] = pd.to_numeric(chunk["shows"], errors="coerce").fillna(0).astype(int)

                if "dt" in chunk.columns:
                    chunk["dt"] = pd.to_datetime(chunk["dt"], errors="coerce")

                if "publication_title_name" in chunk.columns:
                    chunk["title_lower"] = chunk["publication_title_name"].str.lower()

                chunks.append(chunk)
                if remaining is not None:
                    remaining -= len(chunk)

            df = pd.concat(chunks, ignore_index=True) if chunks else pd.DataFrame()

            if cache_file:
                try:
                    df.to_parquet(cache_file, index=False)
                except Exception:
                    # Cache is optional; ignore errors but continue.
                    pass

        # Ensure expected columns exist even if empty dataset
        for column in LIST_COLUMNS:
            if column not in df.columns:
                df[column] = [[] for _ in range(len(df))]

        if "title_lower" not in df.columns:
            df["title_lower"] = df.get("publication_title_name", pd.Series(dtype=str)).str.lower()

        if "shows" not in df.columns:
            df["shows"] = 0

        if "dt" in df.columns:
            df["dt"] = pd.to_datetime(df["dt"], errors="coerce")
        else:
            df["dt"] = pd.NaT

        return cls(
            data=df,
            persons_exploded=explode_column(df, "persons"),
            organizations_exploded=explode_column(df, "organizations"),
            locations_exploded=explode_column(df, "locations"),
            countries_exploded=explode_column(df, "country"),
            daily_stats=aggregate_by_day(df),
        )

    def refresh_daily_stats(self, filtered_df: pd.DataFrame) -> pd.DataFrame:
        self.daily_stats = aggregate_by_day(filtered_df)
        return self.daily_stats


def explode_column(df: pd.DataFrame, column: str) -> pd.DataFrame:
    """Explode list column into a helper dataframe with references."""
    if column not in df.columns:
        return pd.DataFrame(columns=[column, "shows", "dt", "row_id"])

    exploded = df[[column, "shows", "dt"]].copy()
    exploded["row_id"] = exploded.index
    exploded = exploded.explode(column)
    exploded[column] = exploded[column].fillna(" ").astype(str).str.strip()
    exploded = exploded[exploded[column] != ""]
    return exploded


def aggregate_by_day(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "dt" not in df.columns:
        return pd.DataFrame(columns=["date", "publications", "shows"])

    grouped = (
        df.dropna(subset=["dt"])
        .groupby(df["dt"].dt.date)
        .agg(publications=("dt", "size"), shows=("shows", "sum"))
        .reset_index()
        .rename(columns={"dt": "date"})
    )
    grouped = grouped.rename(columns={"dt": "date"})
    grouped["date"] = pd.to_datetime(grouped["date"])
    return grouped
