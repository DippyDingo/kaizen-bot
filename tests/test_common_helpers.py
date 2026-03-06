from datetime import date
import unittest

from bot.handlers.single_message_parts.common import _build_mana_bar, _stats_period_bounds


class CommonHelpersTests(unittest.TestCase):
    def test_stats_period_bounds_day(self) -> None:
        selected = date(2026, 3, 6)
        date_from, date_to = _stats_period_bounds(selected, "day")
        self.assertEqual((selected, selected), (date_from, date_to))

    def test_stats_period_bounds_week(self) -> None:
        selected = date(2026, 3, 6)
        date_from, date_to = _stats_period_bounds(selected, "7d")
        self.assertEqual(date(2026, 2, 28), date_from)
        self.assertEqual(selected, date_to)

    def test_build_mana_bar_uses_custom_target(self) -> None:
        bar, steps = _build_mana_bar(1200, 1500)
        self.assertEqual(4, steps)
        self.assertEqual("🟦🟦🟦🟦⬜️", bar)
