from __future__ import annotations

from typing import Set

import flet as ft
import pandas as pd

from charts import (
    figure_to_base64,
    make_folium_map_html,
    make_publications_chart,
    make_top_entities_chart,
    make_wordcloud_image,
    make_world_map,
)
from components import MultiSelectDropdown, PlaceholderCard, StatCard, build_top_news_table, build_wordcloud_image
from data_loader import DataModel
from filters import FilterState, apply_filters, extract_unique

DATA_PATH = "Geo_Data.csv"
CACHE_PATH = "news_cache.parquet"


class Dashboard:
    def __init__(self, page: ft.Page):
        self.page = page
        self.model = DataModel.from_csv(DATA_PATH, CACHE_PATH)
        self.filter_state = FilterState()

        self._build_filters()
        self._build_layout()
        self.apply_filters()

    def _build_filters(self):
        df = self.model.data
        self.person_filter = MultiSelectDropdown(
            label="Персоны",
            options=extract_unique(df.get("persons", pd.Series(dtype=object))),
            on_change=self._on_person_filter,
        )
        self.organization_filter = MultiSelectDropdown(
            label="Организации",
            options=extract_unique(df.get("organizations", pd.Series(dtype=object))),
            on_change=self._on_organization_filter,
        )
        self.country_filter = MultiSelectDropdown(
            label="Страны",
            options=extract_unique(df.get("country", pd.Series(dtype=object))),
            on_change=self._on_country_filter,
        )

        self.start_date = ft.DatePicker(on_change=lambda _: self.apply_filters())
        self.end_date = ft.DatePicker(on_change=lambda _: self.apply_filters())
        self.page.overlay.extend([self.start_date, self.end_date])

        self.date_controls = ft.Row(
            controls=[
                ft.ElevatedButton("Дата с", icon=ft.Icons.CALENDAR_MONTH, on_click=lambda _: self.start_date.pick_date()),
                ft.ElevatedButton("Дата по", icon=ft.Icons.CALENDAR_TODAY, on_click=lambda _: self.end_date.pick_date()),
            ]
        )

    def _build_layout(self):
        self.page.title = "News Analytics Dashboard"
        self.page.padding = 16
        self.page.scroll = ft.ScrollMode.AUTO
        self.page.theme_mode = ft.ThemeMode.LIGHT

        self.app_bar = ft.AppBar(title=ft.Text("News Analytics Dashboard", weight=ft.FontWeight.BOLD), bgcolor=ft.Colors.BLUE_100)
        self.page.appbar = self.app_bar

        self.stats_row = ft.ResponsiveRow([])
        self.map_chart = ft.Container(height=360)
        self.daily_chart = ft.Container(height=360)
        self.persons_chart = ft.Container(height=320)
        self.organizations_chart = ft.Container(height=320)
        self.locations_chart = ft.Container(height=320)
        self.wordcloud_image = ft.Container()
        self.top_news_table = ft.Container()

        filters_panel = ft.Container(
            width=300,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=12,
            padding=12,
            content=ft.Column(
                spacing=12,
                controls=[
                    ft.Text("Фильтры", size=18, weight=ft.FontWeight.BOLD),
                    self.person_filter,
                    self.organization_filter,
                    self.country_filter,
                    ft.Row([ft.Text("Дата с:"), ft.IconButton(ft.Icons.DATE_RANGE, on_click=lambda _: self.start_date.pick_date())]),
                    ft.Row([ft.Text("Дата по:"), ft.IconButton(ft.Icons.DATE_RANGE, on_click=lambda _: self.end_date.pick_date())]),
                    ft.ElevatedButton("Сбросить", icon=ft.Icons.REFRESH, on_click=self.reset_filters),
                ],
            ),
        )

        visuals = ft.Column(
            spacing=16,
            controls=[
                self.stats_row,
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(content=self.map_chart, col=6, padding=8, bgcolor=ft.Colors.WHITE, border_radius=10, ink=True),
                        ft.Container(content=self.daily_chart, col=6, padding=8, bgcolor=ft.Colors.WHITE, border_radius=10, ink=True),
                    ]
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(content=self.persons_chart, col=4, padding=8, bgcolor=ft.Colors.WHITE, border_radius=10, ink=True),
                        ft.Container(content=self.organizations_chart, col=4, padding=8, bgcolor=ft.Colors.WHITE, border_radius=10, ink=True),
                        ft.Container(content=self.locations_chart, col=4, padding=8, bgcolor=ft.Colors.WHITE, border_radius=10, ink=True),
                    ]
                ),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    padding=12,
                    border_radius=10,
                    content=ft.Column([
                        ft.Text("ТОП-10 новостей по показам", weight=ft.FontWeight.W_600),
                        self.top_news_table,
                    ]),
                ),
                ft.Container(
                    bgcolor=ft.Colors.WHITE,
                    padding=12,
                    border_radius=10,
                    content=ft.Column([
                        ft.Text("Облако слов", weight=ft.FontWeight.W_600),
                        self.wordcloud_image,
                    ]),
                ),
            ],
        )

        # Use an expanding container instead of ft.Expanded for compatibility with older flet versions
        visuals_container = ft.Container(content=visuals, expand=True)
        self.page.add(ft.Row(controls=[filters_panel, ft.VerticalDivider(width=1), visuals_container], expand=True))

    def _on_person_filter(self, values: Set[str]):
        self.filter_state.persons = set(values)
        self.apply_filters()

    def _on_organization_filter(self, values: Set[str]):
        self.filter_state.organizations = set(values)
        self.apply_filters()

    def _on_country_filter(self, values: Set[str]):
        self.filter_state.countries = set(values)
        self.apply_filters()

    def reset_filters(self, _=None):
        self.filter_state = FilterState()
        self.person_filter.reset()
        self.organization_filter.reset()
        self.country_filter.reset()
        self.start_date.value = None
        self.end_date.value = None
        self.apply_filters()

    def apply_filters(self):
        self.filter_state.start_date = self.start_date.value
        self.filter_state.end_date = self.end_date.value

        filtered_df = apply_filters(self.model.data, self.filter_state)
        self.model.refresh_daily_stats(filtered_df)

        self._update_stats(filtered_df)
        self._update_visuals(filtered_df)
        self.page.update()

    def _update_stats(self, df: pd.DataFrame):
        publications = len(df)
        shows = int(df["shows"].sum()) if not df.empty else 0
        topics = int(df.get("topics_verdicts_list", pd.Series(dtype=object)).explode().nunique()) if not df.empty else 0
        persons = int(df.get("persons", pd.Series(dtype=object)).explode().nunique()) if not df.empty else 0

        self.stats_row.controls = [
            ft.Container(content=StatCard("Публикации", f"{publications:,}".replace(",", " "), ft.Icons.ARTICLE, ft.Colors.BLUE_300), col=3),
            ft.Container(content=StatCard("Показы", f"{shows:,}".replace(",", " "), ft.Icons.INSIGHTS, ft.Colors.GREEN_300), col=3),
            ft.Container(content=StatCard("Уникальные темы", str(topics), ft.Icons.LABEL, ft.Colors.ORANGE_300), col=3),
            ft.Container(content=StatCard("Персоны", str(persons), ft.Icons.GROUP, ft.Colors.INDIGO_300), col=3),
        ]

    def _update_visuals(self, df: pd.DataFrame):
        # Map
        country_counts = (
            df[["country", "shows"]]
            .explode("country")
            .dropna(subset=["country"])
            .assign(country=lambda x: x["country"].str.strip())
        )
        country_grouped = (
            country_counts.groupby("country")
            .agg(mentions=("country", "size"), shows=("shows", "sum"))
            .reset_index()
            .sort_values("mentions", ascending=False)
        )
        folium_map = make_folium_map_html(country_grouped)
        iframe_cls = getattr(ft, "IFrame", None) or getattr(ft, "Iframe", None)
        webview_cls = getattr(ft, "WebView", None)

        if folium_map and iframe_cls:
            try:
                self.map_chart.content = iframe_cls(src=folium_map, width=900, height=360)
                if hasattr(self.map_chart.content, "expand"):
                    self.map_chart.content.expand = True
            except Exception:
                folium_map = ""
        elif folium_map and webview_cls:
            try:
                self.map_chart.content = webview_cls(url=folium_map, width=900, height=360)
                if hasattr(self.map_chart.content, "expand"):
                    self.map_chart.content.expand = True
            except Exception:
                folium_map = ""

        if not folium_map:
            map_fig = make_world_map(country_grouped)
            map_img = figure_to_base64(map_fig)
            if map_img:
                self.map_chart.content = ft.Image(src_base64=map_img, fit=ft.ImageFit.CONTAIN)
            else:
                self.map_chart.content = PlaceholderCard("Нет данных или недоступен движок визуализации карты")

        # Daily chart
        daily_fig = make_publications_chart(self.model.daily_stats)
        daily_img = figure_to_base64(daily_fig)
        if daily_img:
            self.daily_chart.content = ft.Image(src_base64=daily_img, fit=ft.ImageFit.CONTAIN)
        else:
            self.daily_chart.content = PlaceholderCard("Нет данных или недоступен движок визуализации графика")

        # Top entities
        persons_top = (
            df[["persons", "shows"]]
            .explode("persons")
            .dropna(subset=["persons"])
            .groupby("persons")
            .agg(mentions=("persons", "size"), shows=("shows", "sum"))
            .reset_index()
            .sort_values(["mentions", "shows"], ascending=False)
            .head(5)
        )
        orgs_top = (
            df[["organizations", "shows"]]
            .explode("organizations")
            .dropna(subset=["organizations"])
            .groupby("organizations")
            .agg(mentions=("organizations", "size"), shows=("shows", "sum"))
            .reset_index()
            .sort_values(["mentions", "shows"], ascending=False)
            .head(5)
        )
        locations_top = (
            df[["locations", "shows"]]
            .explode("locations")
            .dropna(subset=["locations"])
            .groupby("locations")
            .agg(mentions=("locations", "size"), shows=("shows", "sum"))
            .reset_index()
            .sort_values(["mentions", "shows"], ascending=False)
            .head(5)
        )

        persons_fig = make_top_entities_chart(persons_top, "persons", "Топ-5 персон")
        persons_img = figure_to_base64(persons_fig)
        self.persons_chart.content = (
            ft.Image(src_base64=persons_img, fit=ft.ImageFit.CONTAIN)
            if persons_img
            else PlaceholderCard("Нет данных для персон или недоступен движок визуализации")
        )

        orgs_fig = make_top_entities_chart(orgs_top, "organizations", "Топ-5 компаний")
        orgs_img = figure_to_base64(orgs_fig)
        self.organizations_chart.content = (
            ft.Image(src_base64=orgs_img, fit=ft.ImageFit.CONTAIN)
            if orgs_img
            else PlaceholderCard("Нет данных для компаний или недоступен движок визуализации")
        )

        locations_fig = make_top_entities_chart(locations_top, "locations", "Топ-5 геоназваний")
        locations_img = figure_to_base64(locations_fig)
        self.locations_chart.content = (
            ft.Image(src_base64=locations_img, fit=ft.ImageFit.CONTAIN)
            if locations_img
            else PlaceholderCard("Нет данных для геоназваний или недоступен движок визуализации")
        )

        # Top news table
        top_news = df.sort_values("shows", ascending=False).head(10)[["dt", "publication_title_name", "shows"]]
        if top_news.empty:
            self.top_news_table.content = PlaceholderCard("Нет данных для отображения новостей")
        else:
            self.top_news_table.content = build_top_news_table(top_news)

        # Wordcloud
        titles = df.get("publication_title_name", pd.Series(dtype=str)).dropna().astype(str)
        topics = df.get("topics_verdicts_list", pd.Series(dtype=object)).explode().dropna().astype(str)
        verdicts = df.get("bad_verdicts_list", pd.Series(dtype=object)).explode().dropna().astype(str)
        text = " ".join(titles.tolist() + topics.tolist() + verdicts.tolist())
        encoded = make_wordcloud_image(text)
        if encoded:
            self.wordcloud_image.content = build_wordcloud_image(encoded)
        else:
            self.wordcloud_image.content = PlaceholderCard("Недостаточно текста для облака слов")


def main(page: ft.Page):
    Dashboard(page)


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
