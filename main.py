from __future__ import annotations

import flet as ft
from flet import icons
import pandas as pd

from data_loader import format_list, load_news_data

DATA_PATH = "Geo_Data.csv"


def create_stat_card(title: str, value: str, icon: str, color: str) -> ft.Container:
    return ft.Container(
        padding=12,
        bgcolor=color,
        border_radius=10,
        content=ft.Column(
            spacing=5,
            controls=[
                ft.Row([ft.Icon(icon, color=ft.colors.WHITE), ft.Text(title, color=ft.colors.WHITE, weight=ft.FontWeight.W_600)]),
                ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=ft.colors.WHITE),
            ],
        ),
    )


def make_bar_chart(series: pd.Series, title: str, color: str) -> ft.Column:
    bar_groups = []
    labels = []
    for index, (label, value) in enumerate(series.items()):
        bar_groups.append(
            ft.BarChartGroup(
                x=index,
                bar_rods=[ft.BarChartRod(from_y=0, to_y=float(value), width=18, color=color)],
            )
        )
        labels.append(ft.ChartAxisLabel(value=index, label=ft.Text(label, size=10)))

    chart = ft.BarChart(
        bar_groups=bar_groups,
        border=ft.Border(side=ft.BorderSide(1, ft.colors.OUTLINE)),
        horizontal_grid_lines=ft.ChartGridLines(interval=1, color=ft.colors.GREY_300),
        bottom_axis=ft.ChartAxis(labels=labels, labels_size=40),
        left_axis=ft.ChartAxis(title=ft.Text(title), labels_size=50),
        tooltip_bgcolor=color,
        max_y=max(series.max() * 1.15, 1),
        expand=True,
    )
    return ft.Column([ft.Text(title, weight=ft.FontWeight.W_600), chart])


def build_table(data: pd.DataFrame) -> ft.DataTable:
    rows = []
    for _, row in data.iterrows():
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(row.get("publication_title_name", ""))),
                    ft.DataCell(ft.Text(row.get("dt", "").strftime("%Y-%m-%d") if pd.notna(row.get("dt")) else "—")),
                    ft.DataCell(ft.Text(format_list(row.get("topics_verdicts_list", [])))),
                    ft.DataCell(ft.Text(str(row.get("shows", "—")))),
                    ft.DataCell(ft.Text(format_list(row.get("country", [])))),
                ]
            )
        )

    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Заголовок")),
            ft.DataColumn(ft.Text("Дата")),
            ft.DataColumn(ft.Text("Темы")),
            ft.DataColumn(ft.Text("Показы")),
            ft.DataColumn(ft.Text("Страны")),
        ],
        rows=rows,
        heading_row_color=ft.colors.BLUE_GREY_50,
        column_spacing=20,
        width=1200,
    )


def main(page: ft.Page):
    page.title = "News Mapper"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    df = load_news_data(DATA_PATH)

    def build_dropdown_options(values: set[str], placeholder: str) -> list[ft.dropdown.Option]:
        cleaned = sorted(v for v in values if v)
        return [ft.dropdown.Option(placeholder)] + [ft.dropdown.Option(value) for value in cleaned]

    topic_values = {
        topic for topic_list in df.get("topics_verdicts_list", []) for topic in topic_list if topic
    }
    country_values = {
        country for country_list in df.get("country", []) for country in country_list if country
    }

    topic_filter = ft.Dropdown(
        label="Тема",
        width=250,
        options=build_dropdown_options(topic_values, "Все темы"),
        value="Все темы",
        on_change=lambda e: apply_filters(),
    )

    country_filter = ft.Dropdown(
        label="Страна",
        width=220,
        options=build_dropdown_options(country_values, "Все страны"),
        value="Все страны",
        on_change=lambda e: apply_filters(),
    )

    search_field = ft.TextField(label="Поиск в заголовке", width=300, on_change=lambda e: apply_filters())

    negative_switch = ft.Switch(label="С негативным вердиктом", on_change=lambda e: apply_filters())

    start_date_picker = ft.DatePicker(on_change=lambda e: apply_filters())
    end_date_picker = ft.DatePicker(on_change=lambda e: apply_filters())
    page.overlay.extend([start_date_picker, end_date_picker])

    start_button = ft.ElevatedButton("Дата с", on_click=lambda e: start_date_picker.pick_date())
    end_button = ft.ElevatedButton("Дата по", on_click=lambda e: end_date_picker.pick_date())

    stats_row = ft.Row(wrap=True, spacing=10)
    topics_chart_container = ft.Container()
    countries_chart_container = ft.Container()
    persons_chart_container = ft.Container()

    table_container = ft.Container()

    def filter_dataframe() -> pd.DataFrame:
        filtered = df.copy()

        if start_date_picker.value:
            filtered = filtered[filtered["dt"] >= pd.to_datetime(start_date_picker.value)]
        if end_date_picker.value:
            filtered = filtered[filtered["dt"] <= pd.to_datetime(end_date_picker.value)]

        if topic_filter.value and topic_filter.value != "Все темы":
            filtered = filtered[
                filtered["topics_verdicts_list"].apply(lambda topics: topic_filter.value in topics if isinstance(topics, list) else False)
            ]

        if country_filter.value and country_filter.value != "Все страны":
            filtered = filtered[
                filtered["country"].apply(lambda countries: country_filter.value in countries if isinstance(countries, list) else False)
            ]

        if negative_switch.value:
            filtered = filtered[
                filtered["bad_verdicts_list"].apply(
                    lambda verdicts: bool(verdicts) if isinstance(verdicts, list) else False
                )
            ]

        if search_field.value:
            term = search_field.value.lower()
            filtered = filtered[filtered["title_lower"].str.contains(term, na=False)]

        return filtered

    def update_stats(dataframe: pd.DataFrame):
        stats_row.controls = [
            create_stat_card("Публикации", f"{len(dataframe):,}".replace(",", " "), icons.ARTICLE, ft.colors.BLUE),
            create_stat_card("Показы", f"{int(dataframe['shows'].sum()):,}".replace(",", " "), icons.INSIGHTS, ft.colors.GREEN),
            create_stat_card(
                "Уникальные темы",
                str(dataframe["topics_verdicts_list"].explode().nunique() if not dataframe.empty else 0),
                icons.LABEL,
                ft.colors.ORANGE,
            ),
            create_stat_card(
                "Упомянутые персоны",
                str(dataframe.get("persons", pd.Series(dtype=object)).explode().nunique() if not dataframe.empty else 0),
                icons.GROUP,
                ft.colors.INDIGO,
            ),
        ]

    def update_charts(dataframe: pd.DataFrame):
        topics_series = (
            dataframe["topics_verdicts_list"].explode().value_counts().head(10)
            if "topics_verdicts_list" in dataframe
            else pd.Series()
        )
        if topics_series.empty:
            topics_chart_container.content = ft.Text("Недостаточно данных для отображения тем")
        else:
            topics_chart_container.content = make_bar_chart(topics_series, "ТОП тем", ft.colors.BLUE_400)

        countries_series = dataframe["country"].explode().value_counts().head(10) if "country" in dataframe else pd.Series()
        if countries_series.empty:
            countries_chart_container.content = ft.Text("Страны отсутствуют в выборке")
        else:
            countries_chart_container.content = make_bar_chart(countries_series, "Упоминания стран", ft.colors.PURPLE_300)

        persons_series = dataframe.get("persons", pd.Series(dtype=object)).explode().value_counts().head(10)
        if persons_series.empty:
            persons_chart_container.content = ft.Text("Нет персон для отображения")
        else:
            persons_chart_container.content = make_bar_chart(persons_series, "ТОП персон", ft.colors.GREEN_400)

    def update_table(dataframe: pd.DataFrame):
        preview = dataframe.sort_values(by="shows", ascending=False).head(25)
        if preview.empty:
            table_container.content = ft.Text("Данные не найдены по заданным фильтрам", italic=True)
        else:
            table_container.content = build_table(preview)

    def apply_filters():
        filtered_df = filter_dataframe()
        update_stats(filtered_df)
        update_charts(filtered_df)
        update_table(filtered_df)
        page.update()

    reset_button = ft.TextButton(
        "Сбросить фильтры",
        icon=icons.REFRESH,
        on_click=lambda e: reset_filters(),
    )

    def reset_filters():
        topic_filter.value = "Все темы"
        country_filter.value = "Все страны"
        negative_switch.value = False
        search_field.value = ""
        start_date_picker.value = None
        end_date_picker.value = None
        apply_filters()

    filter_row = ft.ResponsiveRow(
        controls=[
            ft.Container(content=topic_filter, col=3),
            ft.Container(content=country_filter, col=3),
            ft.Container(content=search_field, col=3),
            ft.Container(content=negative_switch, col=2),
            ft.Container(content=ft.Row([start_button, end_button], spacing=10), col=4),
            ft.Container(content=reset_button, col=2),
        ]
    )

    page.add(
        ft.Text("Интерактивная визуализация новостей", size=24, weight=ft.FontWeight.BOLD),
        ft.Text("Фильтруйте и изучайте публикации по темам, странам и дате."),
        filter_row,
        stats_row,
        ft.ResponsiveRow([
            ft.Container(content=topics_chart_container, col=6, padding=10),
            ft.Container(content=countries_chart_container, col=6, padding=10),
            ft.Container(content=persons_chart_container, col=12, padding=10),
        ]),
        table_container,
    )

    apply_filters()


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)
