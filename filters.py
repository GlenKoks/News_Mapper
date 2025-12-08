"""Filtering helpers for the dashboard."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Set

import pandas as pd


@dataclass
class FilterState:
    start_date: date | None = None
    end_date: date | None = None
    persons: Set[str] = field(default_factory=set)
    organizations: Set[str] = field(default_factory=set)
    countries: Set[str] = field(default_factory=set)


def _intersects(series: pd.Series, selected: Set[str]) -> pd.Series:
    if not selected:
        return pd.Series([True] * len(series), index=series.index)
    return series.apply(lambda values: bool(set(values or []) & selected))


def apply_filters(df: pd.DataFrame, state: FilterState) -> pd.DataFrame:
    if df.empty:
        return df

    mask = pd.Series([True] * len(df), index=df.index)

    if state.start_date:
        mask &= df["dt"] >= pd.to_datetime(state.start_date)
    if state.end_date:
        mask &= df["dt"] <= pd.to_datetime(state.end_date)

    if state.persons:
        mask &= _intersects(df.get("persons", pd.Series(dtype=object)), state.persons)
    if state.organizations:
        mask &= _intersects(df.get("organizations", pd.Series(dtype=object)), state.organizations)
    if state.countries:
        mask &= _intersects(df.get("country", pd.Series(dtype=object)), state.countries)

    return df[mask].copy()


def extract_unique(series: pd.Series) -> list[str]:
    unique_values = sorted(
        {
            item
            for values in series.dropna()
            for item in (values if isinstance(values, Iterable) and not isinstance(values, (str, bytes)) else [])
            if item
        }
    )
    return unique_values
