from __future__ import annotations

from pathlib import Path

from aiohttp import web

from bot.config import settings

from .auth import TelegramInitDataError, validate_telegram_init_data
from .handlers import get_dashboard, get_health, get_stats

TELEGRAM_INIT_DATA_HEADER = "X-Telegram-Init-Data"
WEBAPP_DIR = Path(__file__).resolve().parents[2] / "webapp"


async def serve_webapp_index(_: web.Request) -> web.FileResponse:
    return web.FileResponse(WEBAPP_DIR / "index.html")


@web.middleware
async def telegram_auth_middleware(request: web.Request, handler):
    if request.path.startswith("/api/"):
        init_data = request.headers.get(TELEGRAM_INIT_DATA_HEADER)
        if not init_data:
            return web.json_response(
                {"error": "unauthorized", "detail": f"missing {TELEGRAM_INIT_DATA_HEADER} header"},
                status=401,
            )

        try:
            request["telegram_auth"] = validate_telegram_init_data(init_data, settings.bot_token)
        except TelegramInitDataError as exc:
            return web.json_response(
                {"error": "unauthorized", "detail": str(exc)},
                status=401,
            )

    return await handler(request)


def create_app() -> web.Application:
    app = web.Application(middlewares=[telegram_auth_middleware])
    app.add_routes(
        [
            web.get("/webapp", serve_webapp_index),
            web.get("/webapp/", serve_webapp_index),
            web.get("/api/v1/dashboard", get_dashboard),
            web.get("/api/v1/health", get_health),
            web.get("/api/v1/stats", get_stats),
        ]
    )
    app.router.add_static("/webapp/css/", WEBAPP_DIR / "css")
    app.router.add_static("/webapp/js/", WEBAPP_DIR / "js")
    return app
