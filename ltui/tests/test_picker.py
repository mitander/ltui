"""Observe rendered picker surfaces without credentials or network access."""

import unittest
from unittest.mock import patch

from textual.app import App
from textual.theme import Theme
from textual.widgets.option_list import Option

import ltui


class PickerApp(App):
    CSS = ltui.LTUI.CSS

    def get_css_variables(self) -> dict[str, str]:
        variables = super().get_css_variables()
        for name, value in ltui.THEMES[0].variables.items():
            variables.setdefault(name, value)
        return variables


class PickerSurfaceTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_selected_row_has_a_distinct_background(self) -> None:
        light = Theme(
            name="picker-light",
            primary="#005f87",
            background="#ffffff",
            foreground="#202020",
            dark=False,
            variables={"ltui-modal-bg": "#f5f5f5", "ltui-cursor": "#cccccc"},
        )
        for theme in ("mocha", "void", "onyx", light.name):
            with self.subTest(theme=theme):
                app = PickerApp()
                for custom_theme in [*ltui.THEMES, light]:
                    app.register_theme(custom_theme)
                app.theme = theme

                with patch.dict(ltui.CONFIG_OPTIONS, {"animations": True}):
                    async with app.run_test() as pilot:
                        picker = ltui.PickerModal(
                            "filter by project",
                            [Option("all projects", id="all"), Option("flume", id="flume")],
                        )
                        app.push_screen(picker)
                        await pilot.pause(0.25)
                        surface = picker.query_one("#picker-box").rich_style.bgcolor
                        title = picker.query_one("#picker-title")
                        options = picker.query_one("#picker-list", ltui.NavList)

                        def background(widget, label: str):
                            return next(
                                segment.style.bgcolor
                                for strip in widget.render_lines(widget.size.region)
                                for segment in strip
                                if segment.text == label
                            )

                        self.assertEqual(background(title, "filter by project"), surface)
                        self.assertEqual(background(options, "flume"), surface)
                        self.assertNotEqual(background(options, "all projects"), surface)

                        await pilot.press("down")
                        self.assertEqual(background(options, "all projects"), surface)
                        self.assertNotEqual(background(options, "flume"), surface)
                        await pilot.press("escape")
                        self.assertNotIn(picker, app.screen_stack)
