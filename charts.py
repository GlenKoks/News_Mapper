"""Visualization helpers using Plotly, folium, and wordcloud (optimized)."""
from __future__ import annotations

import base64
from io import BytesIO
from typing import Iterable

import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import folium
from wordcloud import STOPWORDS, WordCloud

import geo

COLOR_PALETTE = px.colors.sequential.Blues

# ---- constants & precompiled helpers ----

# Precompute stopwords once (big speedup on repeated calls)
WC_STOPWORDS = frozenset(set(STOPWORDS) | {"для",
                                           "как",
                                           "что",
                                           "при",
                                           "в",
                                           "на",
                                           "и",
                                           "по",
                                           "над",
                                           "еще",
                                           "чем",
                                           "это",
                                           "быть",
                                           "было",
                                           "под",
                                           "кто"})
CORPUS_STOPWORDS = frozenset(set(STOPWORDS) | {"the", "and", "to", "of", "в", "на", "и", "по"})

# Precompile regex once
WORD_RE = re.compile(r"[\w']+", flags=re.UNICODE)

# Folium base map config
_FOLIUM_DEFAULT_LOCATION = (20, 0)
_FOLIUM_DEFAULT_ZOOM = 2
_FOLIUM_TILES = "cartodbpositron"


def _empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(title=title)
    return fig


def make_world_map(country_counts: pd.DataFrame) -> go.Figure:
    if country_counts is None or country_counts.empty:
        return _empty_figure("Нет данных для отображения карты")

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


def make_folium_map_html(country_counts: pd.DataFrame) -> str:
    """
    Build a folium choropleth map and return it as a data URI HTML string.
    Returns "" on failure.
    """
    if country_counts is None or country_counts.empty:
        return ""

    # Folium Choropleth умеет сам джойнить данные по key_on, так что мутация geojson не обязательна.
    # Но для tooltip со значением mentions нам нужно, чтобы оно было в feature.properties.
    # Вместо deepcopy(geo.geo_list) делаем лёгкую копию только features.
    base_geo = geo.geo_list
    mentions_by_country = country_counts.set_index("country")["mentions"].to_dict()

    # lightweight copy: new dict + new features list + shallow copy of feature/properties
    features = base_geo.get("features", [])
    enriched_geo = {
        **base_geo,
        "features": [
            {
                **f,
                "properties": {
                    **(f.get("properties") or {}),
                    "mentions": int(mentions_by_country.get(f.get("id"), 0)),
                },
            }
            for f in features
        ],
    }

    try:
        fmap = folium.Map(
            location=_FOLIUM_DEFAULT_LOCATION,
            zoom_start=_FOLIUM_DEFAULT_ZOOM,
            tiles=_FOLIUM_TILES,
        )

        choropleth = folium.Choropleth(
            geo_data=enriched_geo,
            name="mentions",
            data=country_counts,
            columns=["country", "mentions"],
            key_on="feature.id",
            fill_color="YlGnBu",
            fill_opacity=0.8,
            line_opacity=0.3,
            highlight=True,
            nan_fill_color="white",
            nan_fill_opacity=0.15,
        )
        choropleth.add_to(fmap)

        # Tooltip now can safely read "mentions" from geojson properties
        choropleth.geojson.add_child(
            folium.features.GeoJsonTooltip(
                fields=["name", "mentions"],
                aliases=["Страна", "Упоминания"],
                localize=True,
                sticky=False,
            )
        )

        fmap_html = fmap.get_root().render()
    except Exception:
        return ""

    encoded = base64.b64encode(fmap_html.encode("utf-8")).decode("ascii")
    return f"data:text/html;base64,{encoded}"


def figure_to_base64(fig: go.Figure, *, width: int = 900, height: int = 450) -> str:
    """Render a Plotly figure to base64 PNG. Returns "" if kaleido unavailable."""
    try:
        png_bytes = fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception:
        return ""
    return base64.b64encode(png_bytes).decode("ascii")


def make_publications_chart(daily_stats: pd.DataFrame) -> go.Figure:
    if daily_stats is None or daily_stats.empty:
        return _empty_figure("Нет данных по датам")

    # Avoid repeatedly indexing columns inside Plotly calls
    dates = daily_stats["date"]
    pubs = daily_stats["publications"]
    shows = daily_stats["shows"]

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(
        go.Bar(x=dates, y=pubs, name="Публикации", marker_color="#4F86F7"),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=shows,
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
    if data is None or data.empty:
        return _empty_figure(f"Нет данных для {title.lower()}")

    y = data[entity_column]
    mentions = data["mentions"]
    shows = data["shows"]

    fig = go.Figure(
        data=[
            go.Bar(
                x=mentions,
                y=y,
                orientation="h",
                marker_color="#5C6BC0",
                name="Упоминания",
                text=mentions,
                textposition="outside",
                texttemplate="%{text}",
            ),
            go.Bar(
                x=shows,
                y=y,
                orientation="h",
                marker_color="#26A69A",
                name="Показы",
                text=shows,
                textposition="outside",
                texttemplate="%{text}",
            ),
        ]
    )
    fig.update_layout(
        barmode="group",
        title=title,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=0, r=0, t=50, b=0),
        legend_orientation="h",
        legend_y=-0.2,
        xaxis_title="Количество",
    )
    return fig


def make_wordcloud_image(text: str) -> str:
    if not isinstance(text, str) or not text.strip():
        return ""

    wc = WordCloud(
        width=800,
        height=400,
        background_color="white",
        stopwords=WC_STOPWORDS,
        collocations=False,
    ).generate(text)

    buffer = BytesIO()
    wc.to_image().save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def normalize_and_tokenize_corpus(lines: Iterable[str]) -> str:
    """Normalize and tokenize text lines for wordcloud generation."""
    tokens: list[str] = []
    stop = CORPUS_STOPWORDS
    find_words = WORD_RE.findall
    append = tokens.append

    for line in lines:
        if not isinstance(line, str):
            line = "" if line is None else str(line)
        for word in find_words(line.lower()):
            cleaned = word.strip("_'")
            if len(cleaned) >= 3 and cleaned not in stop:
                append(cleaned)

    return " ".join(tokens)
