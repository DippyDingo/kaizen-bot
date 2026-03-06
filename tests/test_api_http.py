from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

from aiohttp.test_utils import TestClient, TestServer

from backend.api.app import TELEGRAM_INIT_DATA_HEADER, create_app
from bot.config import settings

from tests.test_api_auth import build_init_data


class ApiHttpTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.client = TestClient(TestServer(create_app()))
        await self.client.start_server()
        self.valid_headers = {TELEGRAM_INIT_DATA_HEADER: build_init_data(bot_token=settings.bot_token)}

    async def asyncTearDown(self) -> None:
        await self.client.close()

    async def test_dashboard_requires_init_data_header(self) -> None:
        response = await self.client.get("/api/v1/dashboard")

        self.assertEqual(401, response.status)
        payload = await response.json()
        self.assertEqual("unauthorized", payload["error"])

    async def test_dashboard_rejects_invalid_init_data(self) -> None:
        response = await self.client.get(
            "/api/v1/dashboard",
            headers={TELEGRAM_INIT_DATA_HEADER: "broken=1"},
        )

        self.assertEqual(401, response.status)
        payload = await response.json()
        self.assertEqual("unauthorized", payload["error"])

    async def test_dashboard_returns_payload_for_valid_init_data(self) -> None:
        expected_payload = {"date": "2026-03-07", "user": {"display_name": "Alex"}}
        with patch("backend.api.handlers.build_dashboard_payload", new=AsyncMock(return_value=expected_payload)) as build_payload:
            response = await self.client.get("/api/v1/dashboard?date=2026-03-07", headers=self.valid_headers)

        self.assertEqual(200, response.status)
        self.assertEqual(expected_payload, await response.json())
        build_payload.assert_awaited_once_with(123, date(2026, 3, 7))

    async def test_stats_passes_period_to_adapter(self) -> None:
        expected_payload = {"period": "30d"}
        with patch("backend.api.handlers.build_stats_payload", new=AsyncMock(return_value=expected_payload)) as build_payload:
            response = await self.client.get("/api/v1/stats?date=2026-03-07&period=30d", headers=self.valid_headers)

        self.assertEqual(200, response.status)
        self.assertEqual(expected_payload, await response.json())
        build_payload.assert_awaited_once_with(123, date(2026, 3, 7), "30d")

    async def test_stats_rejects_unknown_period(self) -> None:
        response = await self.client.get("/api/v1/stats?period=week", headers=self.valid_headers)

        self.assertEqual(400, response.status)
        payload = await response.json()
        self.assertEqual("invalid_query", payload["error"])

    async def test_health_returns_404_for_missing_user(self) -> None:
        with patch("backend.api.handlers.build_health_payload", new=AsyncMock(return_value=None)):
            response = await self.client.get("/api/v1/health?date=2026-03-07", headers=self.valid_headers)

        self.assertEqual(404, response.status)
        payload = await response.json()
        self.assertEqual("user_not_found", payload["error"])

    async def test_webapp_route_serves_index_without_auth(self) -> None:
        response = await self.client.get("/webapp")

        self.assertEqual(200, response.status)
        body = await response.text()
        self.assertIn("KAIZEN Web App", body)
        self.assertIn("tab-dashboard", body)
        self.assertIn("tab-health", body)
        self.assertIn("tab-stats", body)

    async def test_webapp_css_route_serves_stylesheet(self) -> None:
        response = await self.client.get("/webapp/css/app.css")

        self.assertEqual(200, response.status)
        body = await response.text()
        self.assertIn(".screen-tab", body)

    async def test_webapp_js_routes_serve_modules(self) -> None:
        entry_response = await self.client.get("/webapp/js/app.js")
        nested_response = await self.client.get("/webapp/js/renderers/dashboard.js")

        self.assertEqual(200, entry_response.status)
        self.assertEqual(200, nested_response.status)
        self.assertIn("renderActiveScreen", await entry_response.text())
        self.assertIn("renderDashboardScreen", await nested_response.text())
