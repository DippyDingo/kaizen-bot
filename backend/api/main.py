from __future__ import annotations

from aiohttp import web

from bot.config import settings

from .app import create_app


def main() -> None:
    web.run_app(create_app(), host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    main()
