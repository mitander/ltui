#!/usr/bin/env python3
"""Run with the built ltui package and its runtime dependencies on sys.path."""

import copy
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import ltui


def issue(identifier, rank, kind="unstarted", assignee=None):
    return {
        "id": identifier,
        "identifier": identifier,
        "title": identifier,
        "sortOrder": rank,
        "state": {"id": kind, "name": kind, "type": kind, "position": 0, "color": None},
        "assignee": {"id": assignee, "displayName": assignee} if assignee else None,
        "project": None,
        "projectMilestone": None,
    }


class LinearQueueTests(unittest.TestCase):
    def setUp(self):
        self.state = {}
        self.loader = patch.object(ltui, "load_state", lambda: self.state.copy())
        self.saver = patch.object(
            ltui, "save_state", lambda data: self.state.update(data)
        )
        self.loader.start()
        self.saver.start()
        self.addCleanup(self.loader.stop)
        self.addCleanup(self.saver.stop)
        self.app = ltui.LTUI()
        self.app._status_filter = "active"
        self.app._sidebar_hidden = True
        self.app._viewer_id = "me"
        self.rows = Mock()
        self.rows.highlighted = None
        self.rows.content_size = SimpleNamespace(width=100)
        self.centre = SimpleNamespace(border_subtitle="")
        self.app.query_one = Mock(
            side_effect=lambda selector, *args: (
                self.rows if selector == "#issues" else self.centre
            )
        )
        self.app._issue_row = lambda i, *args: ltui.Text(i["identifier"])

    def render(self, issues):
        self.app._issues = issues
        self.app.render_issues()
        return [o for o in self.rows.add_options.call_args.args[0] if o.id]

    def test_active_manual_order_ignores_assignment(self):
        issues = [
            issue("DEV-2", 20, assignee="me"),
            issue("DEV-1", 0),
            issue("DEV-3", 30, "backlog"),
            issue("DEV-4", 40, "completed"),
            issue("DEV-5", 50, "started"),
        ]
        before = copy.deepcopy(issues)
        rows = self.render(issues)
        self.assertEqual(self.app._status_filter, "active")
        self.assertEqual([r.id for r in rows], ["DEV-5", "DEV-1", "DEV-2"])
        self.assertEqual(
            [r.prompt.plain for r in rows], ["    DEV-5", " 1  DEV-1", " 2  DEV-2"]
        )
        self.assertEqual(issues, before)
        self.assertIn("Active", self.centre.border_subtitle)

    def test_toggle_shows_all_and_persists(self):
        self.render([issue("DEV-1", 1), issue("DEV-2", 2, "backlog")])
        self.app.push_screen = Mock()
        self.app.action_toggle_focus()
        self.app.push_screen.call_args.args[1]("all")
        rows = [o for o in self.rows.add_options.call_args.args[0] if o.id]
        self.assertEqual([r.id for r in rows], ["DEV-1", "DEV-2"])
        self.assertEqual(rows[0].prompt.plain, "DEV-1")
        self.assertEqual(self.state["status_filter"], "all")
        self.assertEqual(ltui.LTUI()._status_filter, "all")
        self.assertIn("All statuses", self.centre.border_subtitle)

    def test_filters_and_empty_queue(self):
        self.app._mine = True
        rows = self.render([issue("DEV-1", 1), issue("DEV-2", 2, assignee="me")])
        self.assertEqual([r.id for r in rows], ["DEV-2"])
        self.app._filter = "missing"
        self.assertEqual(self.render(self.app._issues), [])
        self.app._filter = ""
        self.app._mine = False
        self.assertEqual(self.render([issue("DEV-3", 3, "backlog")]), [])
        self.assertIn(
            "no issues for these statuses",
            self.rows.add_options.call_args.args[0][0].prompt.plain,
        )

    def test_default_workflow_has_four_sections_in_manual_order(self):
        self.assertEqual(ltui.LTUI()._status_filter, "workflow")
        self.app._status_filter = "workflow"
        rows = self.render([
            issue("DEV-4", 1, "completed"),
            issue("DEV-3", 1, "backlog"),
            issue("DEV-2", 2),
            issue("DEV-1", 1, "started"),
            issue("DEV-5", 0, "canceled"),
            issue("DEV-6", 1),
        ])
        self.assertEqual([row.id for row in rows], ["DEV-1", "DEV-6", "DEV-2", "DEV-3", "DEV-4"])

    def test_group_picker_is_explicit_and_does_not_change_filters(self):
        self.app.push_screen = Mock()
        self.app.action_toggle_group()
        self.assertEqual(self.app._group_by, "status")
        self.app.push_screen.call_args.args[1]("milestone")
        self.assertEqual(self.app._group_by, "milestone")
        self.assertEqual(self.app._status_filter, "active")
        self.assertEqual(self.state["group_by"], "milestone")

    def test_project_choice_persists_per_repository_and_scope(self):
        first = issue("DEV-1", 1)
        first["project"] = {"id": "one", "name": "First"}
        second = issue("DEV-2", 2)
        second["project"] = {"id": "two", "name": "Second"}
        self.app._team = {"id": "dev", "key": "DEV"}
        self.app._org = "Workspace"
        self.app._issues = [first, second]
        self.app.push_screen = Mock()
        self.app.action_pick_project()
        self.app.push_screen.call_args.args[1]("proj:two")
        self.assertEqual([i["id"] for i in self.app._visible_issues()], ["DEV-2"])
        self.assertIn("Workspace / DEV / Second", self.centre.border_title)
        self.app._project_choice_key = None
        self.app._project_filter = None
        self.app._resolve_project_filter()
        self.assertEqual(self.app._project_filter, "two")
        self.app._team = {"id": "other", "key": "OTHER"}
        with patch.dict(ltui.os.environ, {"TRACKER_PROJECT": "missing"}):
            self.app._resolve_project_filter()
        self.assertIsNone(self.app._project_filter)
        self.app._team = {"id": "dev", "key": "DEV"}
        self.app._resolve_project_filter()
        self.assertEqual(self.app._project_filter, "two")

    def test_repository_project_match_and_manual_all_override(self):
        first = issue("DEV-1", 1)
        first["project"] = {"id": "one", "name": "My Project"}
        self.app._repository = ltui.Path("/projects/my-project")
        self.app._team = {"id": "dev", "key": "DEV"}
        with patch.dict(ltui.os.environ, {}, clear=True):
            self.app._set_issues([first], [])
            self.assertEqual(self.app._project_filter, "one")
            duplicate = issue("DEV-2", 2)
            duplicate["project"] = {"id": "two", "name": "my-project"}
            self.app._set_issues([first, duplicate], [])
            self.assertIsNone(self.app._project_filter)
            self.app._set_issues([first], [])
            self.assertEqual(self.app._project_filter, "one")
        self.app.push_screen = Mock()
        self.app.action_pick_project()
        self.app.push_screen.call_args.args[1]("all:")
        self.app._project_choice_key = None
        with patch.dict(ltui.os.environ, {}, clear=True):
            self.app._set_issues([first], [])
        self.assertIsNone(self.app._project_filter)
        self.assertEqual(self.app._group_by, "status")

    def test_project_match_rejects_ambiguous_and_missing_names(self):
        projects = [{"id": "one", "name": "My Project"}, {"id": "two", "name": "my-project"}]
        with patch.dict(ltui.os.environ, {}, clear=True):
            self.assertIsNone(ltui.matching_project(projects, ltui.Path("/my-project")))
            self.assertIsNone(ltui.matching_project(projects, ltui.Path("/unknown")))
        with patch.dict(ltui.os.environ, {"TRACKER_PROJECT": "two"}):
            self.assertEqual(ltui.matching_project(projects, ltui.Path("/unknown")), projects[1])

    def test_repository_context_uses_git_root_or_directory(self):
        with patch.object(ltui.subprocess, "run", return_value=SimpleNamespace(stdout="/projects/repo\n")):
            self.assertEqual(ltui.repository_context(), ltui.Path("/projects/repo").resolve())
        with patch.object(ltui.subprocess, "run", side_effect=FileNotFoundError):
            self.assertEqual(ltui.repository_context(), ltui.Path.cwd().resolve())

    def test_project_grouping_keeps_manual_order(self):
        self.app._group_by = "project"
        rows = self.render([issue("DEV-2", 2, assignee="me"), issue("DEV-1", 1)])
        self.assertEqual([r.id for r in rows], ["DEV-1", "DEV-2"])

    def test_milestone_grouping_orders_by_due_date(self):
        self.app._group_by = "milestone"
        first = issue("DEV-2", 2)
        first["projectMilestone"] = {
            "id": "m2",
            "name": "Later",
            "targetDate": "2026-12-01",
        }
        second = issue("DEV-1", 1)
        second["projectMilestone"] = {
            "id": "m1",
            "name": "Soon",
            "targetDate": "2026-10-01",
        }
        rows = self.render([first, second])
        self.assertEqual([r.id for r in rows], ["DEV-1", "DEV-2"])
        self.assertIn("Soon", self.rows.add_options.call_args.args[0][0].prompt.plain)

    def test_old_cache_rank_is_unknown_and_last(self):
        rows = self.render([issue("DEV-2", None), issue("DEV-1", -1)])
        self.assertEqual([r.id for r in rows], ["DEV-1", "DEV-2"])
        self.assertTrue(rows[1].prompt.plain.startswith(" ?"))

    def test_focus_rows_keep_due_dates_and_update_time(self):
        dated = issue("DEV-1", 1)
        dated.update(
            dueDate="2026-12-31",
            updatedAt="2026-09-14T00:00:00Z",
            priority=2,
            labels={"nodes": []},
            relations={"nodes": []},
            inverseRelations={"nodes": []},
        )
        self.app._issue_row = lambda record, *args: ltui.LTUI._issue_row(
            self.app, record, *args
        )
        row = self.render([dated])[0].prompt.plain
        self.assertTrue(row.startswith(" 1  "))
        self.assertIn(ltui.due_date_cell("2026-12-31"), row)
        self.assertIn(ltui.rel_time(dated["updatedAt"]), row)

        self.rows.content_size.width = ltui.DUE_COL_MIN_WIDTH
        narrow_row = self.render([dated])[0].prompt.plain
        self.assertNotIn("\uf133", narrow_row)
        self.assertTrue(narrow_row.startswith(" 1  "))

    def test_query_and_keybinding(self):
        self.assertIn("dueDate", ltui.ISSUE_FIELDS)
        self.assertIn("sortOrder", ltui.ISSUE_FIELDS)
        self.assertIn("pageInfo", ltui.QL_ISSUES)
        self.assertEqual(ltui.DEFAULT_KEYBINDS["toggle_focus"][0], ["f"])
        self.assertEqual(ltui.DEFAULT_KEYBINDS["pick_project"][0], ["p", "V"])
        self.assertEqual(ltui.DEFAULT_KEYBINDS["change_priority"][0], ["P"])
        self.assertEqual(ltui.DEFAULT_KEYBINDS["move_project"][0], ["M"])
        self.assertIn("milestone", ltui.GROUP_MODES)
        self.assertIn("projectMilestone", ltui.ISSUE_FIELDS)


class PaginationTests(unittest.IsolatedAsyncioTestCase):
    def page(self, ids, more=False, cursor=None):
        return {
            "team": {
                "issues": {
                    "nodes": [{"id": i} for i in ids],
                    "pageInfo": {"hasNextPage": more, "endCursor": cursor},
                },
                "states": {"nodes": []},
            }
        }

    async def test_fetches_all_pages_and_deduplicates(self):
        app = SimpleNamespace(
            gql=AsyncMock(
                side_effect=[
                    self.page(["old", "shared"], True, "cursor"),
                    self.page(["shared", "ready"]),
                ]
            )
        )
        result = await ltui.LTUI.fetch_team_issues(app, "team")
        self.assertEqual(
            [i["id"] for i in result["team"]["issues"]["nodes"]],
            ["old", "shared", "ready"],
        )
        self.assertEqual(
            app.gql.call_args.args[1], {"teamId": "team", "after": "cursor"}
        )

    async def test_nonadvancing_cursor_fails(self):
        app = SimpleNamespace(gql=AsyncMock(return_value=self.page([], True, "same")))
        with self.assertRaisesRegex(RuntimeError, "did not advance"):
            await ltui.LTUI.fetch_team_issues(app, "team")

    async def test_later_failure_does_not_return_partial_queue(self):
        app = SimpleNamespace(
            gql=AsyncMock(
                side_effect=[
                    self.page(["old"], True, "cursor"),
                    RuntimeError("offline"),
                ]
            )
        )
        with self.assertRaisesRegex(RuntimeError, "offline"):
            await ltui.LTUI.fetch_team_issues(app, "team")


if __name__ == "__main__":
    unittest.main()
