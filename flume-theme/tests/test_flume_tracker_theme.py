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
