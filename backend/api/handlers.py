from __future__ import annotations

from aiohttp import web

from .adapters import build_dashboard_payload, build_health_payload, build_stats_payload
from .parsers import parse_request_date, parse_stats_period


def _json_error(status: int, error: str, detail: str) -> web.Response:
    return web.json_response({"error": error, "detail": detail}, status=status)


async def get_dashboard(request: web.Request) -> web.Response:
    try:
        target_date = parse_request_date(request.query.get("date"))
    except ValueError as exc:
        return _json_error(400, "invalid_query", str(exc))

    payload = await build_dashboard_payload(request["telegram_auth"].telegram_id, target_date)
    if payload is None:
        return _json_error(404, "user_not_found", "telegram user is not registered")
    return web.json_response(payload)


async def get_health(request: web.Request) -> web.Response:
    try:
        target_date = parse_request_date(request.query.get("date"))
    except ValueError as exc:
        return _json_error(400, "invalid_query", str(exc))

    payload = await build_health_payload(request["telegram_auth"].telegram_id, target_date)
    if payload is None:
        return _json_error(404, "user_not_found", "telegram user is not registered")
    return web.json_response(payload)


async def get_stats(request: web.Request) -> web.Response:
    try:
        target_date = parse_request_date(request.query.get("date"))
        period = parse_stats_period(request.query.get("period"))
    except ValueError as exc:
        return _json_error(400, "invalid_query", str(exc))

    payload = await build_stats_payload(request["telegram_auth"].telegram_id, target_date, period)
    if payload is None:
        return _json_error(404, "user_not_found", "telegram user is not registered")
    return web.json_response(payload)
