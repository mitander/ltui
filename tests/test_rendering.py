"""Credential-free coverage for filtering and grouping before row publication."""

import copy
import importlib
import unittest
from unittest.mock import Mock, patch


def issue(identifier, state_type, rank, assignee=None, project=None, milestone=None):
    return {
        "id": identifier,
        "identifier": identifier,
        "title": "Example " + identifier,
        "sortOrder": rank,
        "updatedAt": "2026-09-20T12:00:00Z",
        "state": {
            "id": state_type,
            "name": state_type,
            "type": state_type,
            "position": 0,
            "color": None,
        },
        "assignee": {"id": assignee, "displayName": assignee} if assignee else None,
        "project": project,
        "projectMilestone": milestone,
    }


class RenderingPhaseTests(unittest.TestCase):
    def app(self, name):
        module = importlib.import_module(name)
        with patch.object(module, "load_state", return_value={}):
            app = getattr(module, name.upper())()
        app._viewer_id = "me"
        return app

    def test_dependency_icons_and_detail_labels_share_roles(self):
        from rich.console import Console

        record = issue("DEV-1", "unstarted", 1)
        record.update(
            priority=0,
            createdAt="2026-09-20T12:00:00Z",
            labels={"nodes": []},
            relations={"nodes": [{"type": "blocks", "relatedIssue": {"identifier": "DEV-2"}}]},
            inverseRelations={"nodes": [{"type": "blocks", "issue": {"identifier": "DEV-3"}}]},
        )
        console = Console()
        for name in ("ltui", "jtui"):
            with self.subTest(app=name):
                module = importlib.import_module(name)
                app = self.app(name)
                roles = {"blocking": "#705883", "blocked": "#9d395e"}
                meta_widget = Mock()
                with (
                    patch.object(module, "_TRACKER_ROLES", roles),
                    patch.object(app, "query_one", return_value=meta_widget),
                ):
                    row = app._issue_row(record, 120, 5)
                    app._update_detail_meta(record)
                meta = meta_widget.update.call_args.args[0]
                for text in (row, meta):
                    for glyph, role in (("\uf06a", "blocking"), ("\uf056", "blocked")):
                        color = text.get_style_at_offset(console, text.plain.index(glyph)).color
                        self.assertEqual(color.get_truecolor().hex, roles[role])
                for label, role in (("blocks DEV-2", "blocking"), ("blocked by DEV-3", "blocked")):
                    color = meta.get_style_at_offset(console, meta.plain.index(label)).color
                    self.assertEqual(color.get_truecolor().hex, roles[role])

    def test_filters_are_composed_without_mutating_source_records(self):
        for name in ("ltui", "jtui", "sctui"):
            with self.subTest(app=name):
                app = self.app(name)
                project = {"id": "project", "name": "Example", "color": None}
                app._issues = [
                    issue("DEV-1", "unstarted", 1, "me", project),
                    issue("DEV-2", "started", 2, "other", project),
                    issue("DEV-3", "unstarted", 3, "me"),
                    issue("DEV-4", "completed", 4, "me", project),
                ]
                original = copy.deepcopy(app._issues)
                app._mine = True
                app._project_filter = "project"
                app._filter = "EXAMPLE"
                expected = ["DEV-1", "DEV-4"]
                self.assertEqual(
                    [record["id"] for record in app._visible_issues()], expected
                )

                app._filter = "missing"
                self.assertEqual(app._visible_issues(), [])
                self.assertEqual(app._issues, original)

    def test_project_groups_keep_provider_specific_issue_order(self):
        project = {"id": "project", "name": "Example", "color": None}
        records = [
            issue("DEV-2", "unstarted", 2, "me", project),
            issue("DEV-1", "unstarted", 1, "other", project),
            issue("DEV-3", "started", 3, "other", project),
            issue("DEV-4", "unstarted", 4),
        ]
        original = copy.deepcopy(records)
        for name in ("ltui", "jtui", "sctui"):
            with self.subTest(app=name):
                app = self.app(name)
                app._group_by = "project"
                groups = app._issue_groups(records, 80)
                expected = (
                    ["DEV-3", "DEV-1", "DEV-2"]
                    if name == "ltui"
                    else ["DEV-3", "DEV-2", "DEV-1"]
                )
                self.assertEqual([record["id"] for record in groups[0][1]], expected)
                self.assertEqual([record["id"] for record in groups[1][1]], ["DEV-4"])
                self.assertIn("Example", groups[0][0].plain)
                self.assertEqual(records, original)

    def test_linear_milestones_and_initiatives_keep_unassigned_bucket_last(self):
        app = self.app("ltui")
        project = {"id": "project", "name": "Example", "color": None}
        early = {"id": "early", "name": "Soon", "targetDate": "2026-10-01"}
        late = {"id": "late", "name": "Later", "targetDate": "2026-12-01"}
        records = [
            issue("DEV-3", "unstarted", 3, milestone=late),
            issue("DEV-2", "unstarted", 2),
            issue("DEV-1", "unstarted", 1, project=project, milestone=early),
        ]
        original = copy.deepcopy(records)
        app._group_by = "milestone"
        groups = app._issue_groups(records, 80)
        self.assertEqual(
            [[record["id"] for record in group] for _, group in groups],
            [["DEV-1"], ["DEV-3"], ["DEV-2"]],
        )

        app._group_by = "initiative"
        app._init_of_project = {
            "project": {"id": "goal", "name": "Goal", "status": "Active"}
        }
        groups = app._issue_groups(records, 80)
        self.assertEqual(
            [[record["id"] for record in group] for _, group in groups],
            [["DEV-1"], ["DEV-2", "DEV-3"]],
        )
        self.assertEqual(records, original)


if __name__ == "__main__":
    unittest.main()
