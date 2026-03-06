from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
APP_JS = ROOT / "webapp" / "js" / "app.js"
FORMATTERS_JS = ROOT / "webapp" / "js" / "formatters.js"


class WebAppDateLogicTests(unittest.TestCase):
    def test_app_state_uses_local_today_helper(self) -> None:
        content = APP_JS.read_text(encoding="utf-8")

        self.assertIn("selectedDate: getTodayIsoDate()", content)
        self.assertIn("appState.selectedDate = shiftIsoDate(appState.selectedDate, diffDays);", content)
        self.assertNotIn("selectedDate: new Date().toISOString().slice(0, 10)", content)
        self.assertNotIn("base.toISOString().slice(0, 10)", content)

    def test_formatters_export_pure_date_helpers(self) -> None:
        content = FORMATTERS_JS.read_text(encoding="utf-8")

        self.assertIn("export function getTodayIsoDate()", content)
        self.assertIn("export function shiftIsoDate(dateString, diffDays)", content)


if __name__ == "__main__":
    unittest.main()
