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
        self.saver = patch.object(ltui, "save_state", lambda data: self.state.update(data))
        self.loader.start()
        self.saver.start()
        self.addCleanup(self.loader.stop)
        self.addCleanup(self.saver.stop)
        self.app = ltui.LTUI()
        self.app._sidebar_hidden = True
        self.app._viewer_id = "me"
        self.rows = Mock()
        self.rows.highlighted = None
        self.rows.content_size = SimpleNamespace(width=100)
        self.centre = SimpleNamespace(border_subtitle="")
        self.app.query_one = Mock(
            side_effect=lambda selector, *args: self.rows if selector == "#issues" else self.centre
        )
        self.app._issue_row = lambda i, *args: ltui.Text(i["identifier"])

    def render(self, issues):
        self.app._issues = issues
        self.app.render_issues()
        return [o for o in self.rows.add_options.call_args.args[0] if o.id]

    def test_default_focus_and_manual_order_ignore_assignment(self):
        issues = [
            issue("KAP-2", 20, assignee="me"),
            issue("KAP-1", 0),
            issue("KAP-3", 30, "backlog"),
            issue("KAP-4", 40, "completed"),
            issue("KAP-5", 50, "started"),
        ]
        before = copy.deepcopy(issues)
        rows = self.render(issues)
        self.assertTrue(self.app._focus)
        self.assertEqual([r.id for r in rows], ["KAP-5", "KAP-1", "KAP-2"])
        self.assertEqual([r.prompt.plain for r in rows], ["    KAP-5", " 1  KAP-1", " 2  KAP-2"])
        self.assertEqual(issues, before)
        self.assertIn("Now and next", self.centre.border_subtitle)

    def test_toggle_shows_all_and_persists(self):
        self.render([issue("KAP-1", 1), issue("KAP-2", 2, "backlog")])
        self.app.action_toggle_focus()
        rows = [o for o in self.rows.add_options.call_args.args[0] if o.id]
        self.assertEqual([r.id for r in rows], ["KAP-1", "KAP-2"])
        self.assertEqual(rows[0].prompt.plain, "KAP-1")
        self.assertFalse(self.state["focus"])
        self.assertFalse(ltui.LTUI()._focus)
        self.assertIn("All issues", self.centre.border_subtitle)

    def test_filters_and_empty_queue(self):
        self.app._mine = True
        rows = self.render([issue("KAP-1", 1), issue("KAP-2", 2, assignee="me")])
        self.assertEqual([r.id for r in rows], ["KAP-2"])
        self.app._filter = "missing"
        self.assertEqual(self.render(self.app._issues), [])
        self.app._filter = ""
        self.app._mine = False
        self.assertEqual(self.render([issue("KAP-3", 3, "backlog")]), [])
        self.assertIn("no active or ready", self.rows.add_options.call_args.args[0][0].prompt.plain)

    def test_project_grouping_keeps_manual_order(self):
        self.app._group_by = "project"
        rows = self.render([issue("KAP-2", 2, assignee="me"), issue("KAP-1", 1)])
        self.assertEqual([r.id for r in rows], ["KAP-1", "KAP-2"])

    def test_milestone_grouping_orders_by_due_date(self):
        self.app._group_by = "milestone"
        first = issue("KAP-2", 2)
        first["projectMilestone"] = {"id": "m2", "name": "Later", "targetDate": "2026-12-01"}
        second = issue("KAP-1", 1)
        second["projectMilestone"] = {"id": "m1", "name": "Soon", "targetDate": "2026-10-01"}
        rows = self.render([first, second])
        self.assertEqual([r.id for r in rows], ["KAP-1", "KAP-2"])
        self.assertIn("Soon", self.rows.add_options.call_args.args[0][0].prompt.plain)

    def test_old_cache_rank_is_unknown_and_last(self):
        rows = self.render([issue("KAP-2", None), issue("KAP-1", -1)])
        self.assertEqual([r.id for r in rows], ["KAP-1", "KAP-2"])
        self.assertTrue(rows[1].prompt.plain.startswith(" ?"))

    def test_query_and_keybinding(self):
        self.assertIn("sortOrder", ltui.ISSUE_FIELDS)
        self.assertIn("pageInfo", ltui.QL_ISSUES)
        self.assertEqual(ltui.DEFAULT_KEYBINDS["toggle_focus"][0], ["f"])
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
            [i["id"] for i in result["team"]["issues"]["nodes"]], ["old", "shared", "ready"]
        )
        self.assertEqual(app.gql.call_args.args[1], {"teamId": "team", "after": "cursor"})

    async def test_nonadvancing_cursor_fails(self):
        app = SimpleNamespace(gql=AsyncMock(return_value=self.page([], True, "same")))
        with self.assertRaisesRegex(RuntimeError, "did not advance"):
            await ltui.LTUI.fetch_team_issues(app, "team")

    async def test_later_failure_does_not_return_partial_queue(self):
        app = SimpleNamespace(
            gql=AsyncMock(side_effect=[self.page(["old"], True, "cursor"), RuntimeError("offline")])
        )
        with self.assertRaisesRegex(RuntimeError, "offline"):
            await ltui.LTUI.fetch_team_issues(app, "team")


if __name__ == "__main__":
    unittest.main()
