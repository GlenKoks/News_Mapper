"""UI components for the News Analytics dashboard."""
from __future__ import annotations

from typing import Callable, List, Optional, Set

import flet as ft
import pandas as pd

from data_loader import format_list


class MultiSelectDropdown(ft.Column):
    def __init__(
        self,
        label: str,
        options: List[str],
        on_change: Callable[[Set[str]], None],
        width: int = 260,
    ):
        super().__init__(spacing=6)
        self.selected: Set[str] = set()
        self.on_change = on_change
        self.dropdown = ft.Dropdown(
            label=label,
            width=width,
            options=[ft.dropdown.Option(opt) for opt in options],
            on_change=self._handle_change,
        )
        # Using a Row with wrap=True to avoid reliance on ft.Wrap (not available in older flet versions)
        self.chips = ft.Row(spacing=6, run_spacing=6, wrap=True)
        self.controls = [self.dropdown, self.chips]

    def _handle_change(self, e: ft.ControlEvent):
        value = e.control.value
        if value:
            self.selected.add(value)
            e.control.value = None
            self._refresh_chips()
            self.on_change(self.selected)
            self.update()

    def _refresh_chips(self):
        def remove_chip(value: str):
            self.selected.discard(value)
            self._refresh_chips()
            self.on_change(self.selected)
            self.update()

        self.chips.controls = [
            ft.Chip(
                label=ft.Text(item),
                delete_icon=ft.Icon(ft.Icons.CLOSE),
                on_delete=lambda _, v=item: remove_chip(v),
                bgcolor=ft.Colors.BLUE_50,
            )
            for item in sorted(self.selected)
        ]

    def reset(self):
        self.selected = set()
        self._refresh_chips()
        self.update()


class StatCard(ft.Card):
    def __init__(self, title: str, value: str, icon: str, color: str):
        super().__init__(
            elevation=2,
            content=ft.Container(
                padding=12,
                bgcolor=color,
                border_radius=10,
                content=ft.Column(
                    spacing=6,
                    controls=[
                        ft.Row([ft.Icon(icon, color=ft.Colors.WHITE), ft.Text(title, color=ft.Colors.WHITE, weight=ft.FontWeight.W_600)]),
                        ft.Text(value, size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE),
                    ],
                ),
            ),
        )


class PlaceholderCard(ft.Container):
    def __init__(self, text: str):
        super().__init__(
            height=240,
            alignment=ft.alignment.center,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border_radius=10,
            content=ft.Text(text, italic=True, color=ft.Colors.GREY_700),
        )


def build_top_news_table(data: pd.DataFrame) -> ft.DataTable:
    rows = []
    for _, row in data.iterrows():
        rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(row.get("dt").strftime("%Y-%m-%d") if pd.notna(row.get("dt")) else "—")),
                    ft.DataCell(ft.Text(row.get("publication_title_name", "—"))),
                    ft.DataCell(ft.Text(f"{int(row.get('shows', 0)):,}".replace(",", " "))),
                    ft.DataCell(ft.Text(format_list(row.get("bad_verdicts_list", [])))),
                    ft.DataCell(ft.Text(format_list(row.get("topics_verdicts_list", [])))),
                ]
            )
        )

    return ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Дата")),
            ft.DataColumn(ft.Text("Заголовок")),
            ft.DataColumn(ft.Text("Показы")),
            ft.DataColumn(ft.Text("Негативные вердикты")),
            ft.DataColumn(ft.Text("Тематики")),
        ],
        rows=rows,
        column_spacing=12,
        heading_row_color=ft.Colors.BLUE_GREY_50,
    )


def build_wordcloud_image(encoded: str) -> Optional[ft.Image]:
    if not encoded:
        return None
    return ft.Image(src_base64=encoded, width=800, height=400, fit=ft.ImageFit.CONTAIN)
