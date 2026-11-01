#!/usr/bin/env python3

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path

import flume_tracker_theme as flume

THEME = {
    "name": "flume-dusk",
    "dark": True,
    "primary": "#111111",
    "secondary": "#222222",
    "accent": "#333333",
    "background": "#444444",
    "surface": "#555555",
    "panel": "#666666",
    "foreground": "#eeeeee",
    "success": "#00aa00",
    "warning": "#aaaa00",
    "error": "#aa0000",
    "variables": {
        "border": "#777777",
        "border_focus": "#888888",
        "border_detail": "#999999",
        "modal_bg": "#555555",
        "cursor": "#666666",
        "overlay": "black 40%",
        "scrollbar": "#777777",
        "scrollbar_hover": "#888888",
        "scrollbar_active": "#999999",
        "scrollbar_background": "#444444",
        "selection_background": "#333333 30%",
        "selection_foreground": "#444444",
    },
    "roles": {
        "text": "#eeeeee",
        "text_subtle": "#dddddd",
        "text_muted": "#cccccc",
        "border": "#bbbbbb",
        "border_subtle": "#aaaaaa",
        "accent": "#333333",
        "accent_secondary": "#aa00aa",
        "accent_tertiary": "#999999",
        "success": "#00aa00",
        "warning": "#aa5500",
        "error": "#aa0000",
        "status_triage": "#aa5500",
        "status_started": "#aa5500",
        "status_unstarted": "#333333",
        "status_backlog": "#cccccc",
        "status_completed": "#00aa00",
        "status_canceled": "#cccccc",
        "team": "#333333",
        "project": "#aa5500",
        "initiative": "#aa00aa",
        "label": "#999999",
        "blocked": "#aa0000",
        "blocking": "#aa5500",
        "priority_urgent": "#aa0000",
    },
}


class FlumeTrackerThemeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.extras = self.root / "extras"
        self.themes = self.extras / "tracker-tui"
        self.themes.mkdir(parents=True)
        (self.themes / "flume-dusk.json").write_text(json.dumps(THEME))
        os.environ["FLUME_TRACKER_THEME_DIR"] = str(self.themes)
        os.environ["FLUME_SCHEMA_FILE"] = str(self.extras / "current" / "schema")

    def tearDown(self) -> None:
        os.environ.pop("FLUME_TRACKER_THEME_DIR", None)
        os.environ.pop("FLUME_SCHEMA_FILE", None)
        self.temp.cleanup()

    def activate(self, schema: str) -> None:
        target = self.extras / f"set-{schema}"
        target.mkdir()
        (target / "schema").write_text(schema + "\n")
        staged = self.extras / ".current-stage"
        staged.symlink_to(target.name, target_is_directory=True)
        os.replace(staged, self.extras / "current")

    def test_loads_themes_and_chrome_palette(self) -> None:
        themes = flume.load_flume_themes("ltui")
        self.assertEqual([theme.name for theme in themes], ["flume-dusk"])
        self.assertEqual(themes[0].variables["ltui-border"], "#777777")
        self.assertEqual(themes[0].variables["tracker-text"], "#eeeeee")
        self.assertEqual(themes[0].variables["tracker-mauve"], "#aa00aa")
        self.assertEqual(themes[0].variables["text-primary"], "#333333")
        self.assertEqual(themes[0].variables["footer-background"], "#666666")
        self.assertEqual(themes[0].luminosity_spread, 0.0)
        self.assertEqual(themes[0].text_alpha, 1.0)
        self.assertEqual(flume.theme_roles("flume-dusk")["status_completed"], "#00aa00")
        self.assertEqual(flume.theme_palette("flume-dusk")["C_TEXT"], "#eeeeee")

    def test_reads_live_semantic_exports_without_generation(self) -> None:
        palette = {
            "format_version": 1,
            "schema": "dusk",
            "appearance": "dark",
            "colors": {
                **dict.fromkeys(
                    (
                        "text",
                        "fg",
                        "syntax_comment",
                        "muted",
                        "magenta",
                        "border",
                        "border_variant",
                        "accent",
                        "syntax_keyword",
                        "cyan",
                        "success",
                        "warning",
                        "error",
                        "syntax_type",
                        "bg",
                        "surface_alt",
                        "surface",
                        "border_focused",
                        "element_active",
                        "on_accent",
                    ),
                    "#222222",
                ),
                "bg": "#232136",
                "text": "#eeeeee",
                "warning": "#aa5500",
                "syntax_type": "#705883",
                "error": "#9d395e",
                "muted": "#a6a2bb",
                "magenta": "#b99add",
                "accent": "#7dacbb",
                "on_accent": "#232136",
            },
        }
        path = self.themes / "flume-dusk.json"
        path.write_text(json.dumps(palette))
        loaded = flume.load_flume_themes("ltui")
        self.assertEqual([theme.name for theme in loaded], ["flume-dusk"])
        self.assertEqual(loaded[0].background, "#232136")
        self.assertEqual(loaded[0].variables["text"], "#eeeeee")
        self.assertEqual(flume.theme_roles("flume-dusk")["status_started"], "#aa5500")
        roles = flume.theme_roles("flume-dusk")
        self.assertEqual(roles["blocking"], "#705883")
        self.assertEqual(roles["blocked"], "#9d395e")
        self.assertEqual(roles["warning"], "#aa5500")
        for role in ("team", "project", "initiative", "accent_secondary"):
            self.assertEqual(roles[role], "#b99add")
        self.assertEqual(roles["text_muted"], "#a6a2bb")
        self.assertEqual(loaded[0].accent, "#7dacbb")
        self.assertEqual(loaded[0].secondary, "#b99add")
        self.assertEqual(loaded[0].variables["ltui-border-detail"], "#7dacbb")
        self.assertEqual(loaded[0].variables["input-cursor-background"], "#7dacbb")
        self.assertEqual(loaded[0].variables["input-cursor-foreground"], "#232136")

        palette["colors"]["bg"] = "#ded4d1"
        palette["appearance"] = "light"
        path.write_text(json.dumps(palette))
        changed = flume.load_flume_themes("jtui")[0]
        self.assertEqual(changed.background, "#ded4d1")
        self.assertFalse(changed.dark)
        self.assertEqual(changed.variables["jtui-overlay"], "black 15%")

        for key, value in (("format_version", 2), ("format_version", True), ("colors", [])):
            invalid = {**palette, key: value}
            path.write_text(json.dumps(invalid))
            self.assertEqual(flume.load_flume_themes("ltui"), [])
        palette["colors"]["bg"] = "not-a-color"
        path.write_text(json.dumps(palette))
        self.assertEqual(flume.load_flume_themes("ltui"), [])

    def test_deeply_nested_json_is_ignored(self) -> None:
        path = self.themes / "flume-dusk.json"
        path.write_text("[" * 2000 + "0" + "]" * 2000)
        self.assertEqual(flume.load_flume_themes("ltui"), [])
        self.assertIsNone(flume.theme_roles("flume-dusk"))

    def test_reads_active_schema(self) -> None:
        self.assertIsNone(flume.active_flume_theme())
        self.activate("dusk")
        self.assertEqual(flume.active_flume_theme(), "flume-dusk")

    def test_follows_atomic_current_swap(self) -> None:
        async def run() -> str:
            self.activate("dusk")
            changes = flume.watch_flume_theme_changes()
            pending = asyncio.create_task(anext(changes))
            await asyncio.sleep(0.1)
            self.activate("opal")
            return await asyncio.wait_for(pending, 3)

        self.assertEqual(asyncio.run(run()), "flume-opal")


if __name__ == "__main__":
    unittest.main()
