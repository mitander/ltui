"""Offline checks for star-chart pagination and regeneration decisions."""

import importlib.util
import io
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / ".github/scripts/star_chart.py"
SPEC = importlib.util.spec_from_file_location("star_chart", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
chart = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(chart)

NOW = datetime(2026, 9, 20, tzinfo=timezone.utc)
DATES = [datetime(2026, 9, 1, tzinfo=timezone.utc)]


class StarChartTests(unittest.TestCase):
    def test_pagination_collects_and_sorts_dates_without_network(self):
        first_page = [{"starred_at": "2026-09-02T00:00:00Z"}] * 100
        last_page = [{"starred_at": "2026-09-01T00:00:00Z"}]
        responses = [io.StringIO(json.dumps(page)) for page in (first_page, last_page)]
        with patch.object(
            chart.urllib.request, "urlopen", side_effect=responses
        ) as fetch:
            dates = chart.fetch_star_dates()
        self.assertEqual(len(dates), 101)
        self.assertEqual(dates[0], DATES[0])
        self.assertIn("page=2", fetch.call_args.args[0].full_url)

    def test_regeneration_requires_changed_count_old_date_or_missing_chart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with (
                patch.object(chart, "OUT_DIR", root),
                patch.object(chart, "datetime", wraps=datetime) as clock,
            ):
                clock.now.return_value = NOW
                self.assertTrue(chart.stale(DATES))
                for theme in chart.THEMES:
                    (root / f"star-history-{theme}.svg").write_text(
                        "&#9733; 1< updated 2026-09-20<"
                    )
                self.assertFalse(chart.stale(DATES))
                self.assertTrue(chart.stale(DATES * 2))

                dark_chart = root / "star-history-dark.svg"
                dark_chart.write_text("&#9733; 1< updated 2026-09-13<")
                self.assertTrue(chart.stale(DATES))
                for malformed in ("missing metadata", "&#9733; 1< updated 2026-99-99<"):
                    dark_chart.write_text(malformed)
                    self.assertTrue(chart.stale(DATES))

    def test_empty_response_leaves_existing_charts_untouched(self):
        with (
            patch.object(chart, "fetch_star_dates", return_value=[]),
            patch.object(chart, "stale") as stale,
            patch.object(chart, "render") as render,
            patch("builtins.print"),
        ):
            chart.main()
        stale.assert_not_called()
        render.assert_not_called()

    def test_render_contains_independent_count_and_date_evidence(self):
        with patch.object(chart, "datetime", wraps=datetime) as clock:
            clock.now.return_value = NOW
            output = chart.render(DATES, chart.THEMES["dark"])
        self.assertIn("&#9733; 1</text>", output)
        self.assertIn("updated 2026-09-20</text>", output)
        self.assertIn('<polyline points="', output)


if __name__ == "__main__":
    unittest.main()
