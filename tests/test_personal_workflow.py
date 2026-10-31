"""Credential-free native Textual coverage for the personal fork."""

import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


class PersonalWorkflowTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_palette_switch_and_sidebar(self):
        for name, class_name in (("ltui", "LTUI"), ("jtui", "JTUI")):
            module = importlib.import_module(name)
            with self.subTest(app=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "set-mira").mkdir()
                (root / "set-mira/schema").write_text("mira\n")
                (root / "current").symlink_to("set-mira", target_is_directory=True)
                marker = root / "current/schema"
                state = {}
                with (
                    patch.dict(os.environ, {"FLUME_SCHEMA_FILE": str(marker)}),
                    patch.object(
                        module, "load_state", lambda state=state: state.copy()
                    ),
                    patch.object(
                        module,
                        "save_state",
                        lambda data, state=state: state.update(data),
                    ),
                    patch.object(
                        module,
                        "load_api_key" if name == "ltui" else "load_credentials",
                        lambda: "unused-test-key",
                    ),
                    patch.object(getattr(module, class_name), "_start", Mock()),
                ):
                    app = getattr(module, class_name)()
                    async with app.run_test(size=(100, 35)) as pilot:
                        await pilot.pause()
                        self.assertEqual(app.theme, "flume-mira")
                        self.assertEqual(
                            app.query_one("#sidebar").styles.display, "none"
                        )
                        await pilot.press("b")
                        self.assertEqual(
                            app.query_one("#sidebar").styles.display, "block"
                        )
                        self.assertFalse(state["sidebar_hidden"])
                        # Follow the actual watcher through an atomic active-set swap.
                        (root / "set-opal").mkdir()
                        (root / "set-opal/schema").write_text("opal\n")
                        (root / "stage").symlink_to(
                            "set-opal", target_is_directory=True
                        )
                        os.replace(root / "stage", root / "current")
                        for _ in range(30):
                            await pilot.pause(0.1)
                            if app.theme == "flume-opal":
                                break
                        self.assertEqual(app.theme, "flume-opal")
                        if name == "ltui":
                            app.push_screen(module.DueDateModal("DEV-1", None))
                            await pilot.pause()
                        for schema in ("dusk", "opal", "mira", "mesa"):
                            app.theme = "flume-" + schema
                            await pilot.pause()
                            data = json.loads(
                                (
                                    Path(os.environ["FLUME_TRACKER_THEME_DIR"])
                                    / (app.theme + ".json")
                                ).read_text()
                            )
                            self.assertEqual(module.C_TEXT, data["colors"]["text"])
                            self.assertEqual(
                                module.tracker_state_color({"type": "started"}),
                                data["colors"]["warning"],
                            )
                            self.assertEqual(
                                module.tracker_role_color("blocking"),
                                data["colors"]["syntax_type"],
                            )
                            if name == "ltui":
                                title = app.screen.query_one("#duedate-title")
                                field = app.screen.query_one("#duedate-input")
                                self.assertEqual(
                                    title.styles.color,
                                    module.TColor.parse(module.C_SUB),
                                )
                                self.assertEqual(
                                    field.styles.border_top[1],
                                    module.TColor.parse(module.C_FAINT),
                                )
                                app.screen.query_one("#duedate-save").focus()
                                await pilot.pause()
                                self.assertEqual(
                                    field.styles.border_top[1],
                                    module.TColor.parse(module.C_VFAINT),
                                )
                                field.focus()
                                await pilot.pause()
                        app.theme = "mocha"
                        await pilot.pause()
                        self.assertEqual(module.C_TEXT, module._PALETTE["C_TEXT"])

    async def test_linear_view_keys_open_independent_pickers(self):
        import ltui
        from test_rendering import issue

        state = {}
        with (
            patch.object(ltui, "load_state", lambda: state.copy()),
            patch.object(ltui, "save_state", lambda data: state.update(data)),
            patch.object(ltui, "load_api_key", return_value="unused-test-key"),
            patch.object(ltui.LTUI, "_start", Mock()),
        ):
            app = ltui.LTUI()
            async with app.run_test(size=(110, 35)) as pilot:
                app._team = {"id": "dev", "key": "DEV"}
                app._org = "Workspace"
                app._issues = [
                    issue("DEV-1", "started", 1, project={"id": "one", "name": "One"}),
                    issue("DEV-2", "completed", 2, project={"id": "two", "name": "Two"}),
                ]
                for record in app._issues:
                    record.update(
                        labels={"nodes": []}, priority=0,
                        relations={"nodes": []}, inverseRelations={"nodes": []},
                    )
                app.render_issues()
                await pilot.press("p")
                await pilot.pause()
                self.assertIsInstance(app.screen, ltui.PickerModal)
                picker = app.screen.query_one("#picker-list")
                picker.highlighted = 2
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(app._project_filter, "two")
                self.assertEqual(app._group_by, "status")
                self.assertEqual([i["id"] for i in app._visible_issues()], ["DEV-2"])
                await pilot.press("f")
                await pilot.pause()
                app.screen.query_one("#picker-list").highlighted = 1
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(app._status_filter, "active")
                self.assertEqual(app._project_filter, "two")
                self.assertEqual(app._visible_issues(), [])
                await pilot.press("v")
                await pilot.pause()
                app.screen.query_one("#picker-list").highlighted = 1
                await pilot.press("enter")
                await pilot.pause()
                self.assertEqual(app._group_by, "project")
                self.assertEqual(app._status_filter, "active")
                self.assertEqual(app._project_filter, "two")

    async def test_repository_scope_is_explicit_or_unambiguous_hint(self):
        for name in ("ltui", "jtui"):
            module = importlib.import_module(name)
            scopes = [
                {"id": "1", "key": "DEV", "name": "Development"},
                {"id": "2", "key": "FLU", "name": "Flume"},
            ]
            with patch.dict(
                os.environ, {"TRACKER_SCOPE": "FLU", "TRACKER_REPOSITORY": "development"}
            ):
                self.assertEqual(module.preferred_tracker_scope(scopes), scopes[1])
            with patch.dict(
                os.environ, {"TRACKER_SCOPE": "", "TRACKER_REPOSITORY": "development"}
            ):
                self.assertEqual(module.preferred_tracker_scope(scopes), scopes[0])
            with patch.dict(
                os.environ, {"TRACKER_SCOPE": "", "TRACKER_REPOSITORY": "unmatched"}
            ):
                self.assertIsNone(module.preferred_tracker_scope(scopes))


if __name__ == "__main__":
    unittest.main()
