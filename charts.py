"""Visualization helpers using Plotly and wordcloud."""
from __future__ import annotations

import base64
from io import BytesIO
from typing import Iterable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import STOPWORDS, WordCloud


COLOR_PALETTE = px.colors.sequential.Blues


def make_world_map(country_counts: pd.DataFrame) -> go.Figure:
    if country_counts.empty:
        fig = go.Figure()
        fig.update_layout(title="Нет данных для отображения карты")
        return fig

    fig = px.choropleth(
        country_counts,
        locations="country",
        color="mentions",
        hover_name="country",
        color_continuous_scale=COLOR_PALETTE,
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=50, b=0),
        title="Упоминания по странам",
        coloraxis_colorbar=dict(title="Количество упоминаний"),
    )
    return fig


def make_publications_chart(daily_stats: pd.DataFrame) -> go.Figure:
    if daily_stats.empty:
        fig = go.Figure()
        fig.update_layout(title="Нет данных по датам")
        return fig

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=daily_stats["date"], y=daily_stats["publications"], name="Публикации", marker_color="#4F86F7"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=daily_stats["date"],
            y=daily_stats["shows"],
            name="Показы",
            mode="lines+markers",
            marker_color="#16A085",
        ),
        secondary_y=True,
    )

    fig.update_yaxes(title_text="Публикации", secondary_y=False)
    fig.update_yaxes(title_text="Показы", secondary_y=True)
    fig.update_layout(
        title="Динамика публикаций и показов",
        legend_orientation="h",
        legend_y=-0.2,
        margin=dict(l=0, r=0, t=50, b=0),
    )
    return fig


def make_top_entities_chart(data: pd.DataFrame, entity_column: str, title: str) -> go.Figure:
    if data.empty:
        fig = go.Figure()
        fig.update_layout(title=f"Нет данных для {title.lower()}")
        return fig

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=data["mentions"],
            y=data[entity_column],
            orientation="h",
            marker_color="#5C6BC0",
            name="Упоминания",
        )
    )
    fig.add_trace(
        go.Bar(
            x=data["shows"],
            y=data[entity_column],
            orientation="h",
            marker_color="#26A69A",
            name="Показы",
        )
    )
    fig.update_layout(
        barmode="group",
        title=title,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=0, r=0, t=50, b=0),
        legend_orientation="h",
        legend_y=-0.2,
    )
    return fig


def make_wordcloud_image(text: str) -> str:
    if not text.strip():
        return ""

    stopwords = set(STOPWORDS)
    stopwords.update({"the", "and", "to", "of", "в", "на", "и", "по"})

    wc = WordCloud(width=800, height=400, background_color="white", stopwords=stopwords, collocations=False)
    wc.generate(text)

    buffer = BytesIO()
    wc.to_image().save(buffer, format="PNG")
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")
