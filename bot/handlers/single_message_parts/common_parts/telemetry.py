from __future__ import annotations

import logging

logger = logging.getLogger("kaizen.telegram_ui")


def log_ui_event(
    event: str,
    *,
    chat_id: int | None = None,
    dashboard_message_id: int | None = None,
    carrier_message_id: int | None = None,
    view_mode: str | None = None,
    entrypoint: str | None = None,
) -> None:
    logger.info(
        "ui_event=%s chat_id=%s dashboard_message_id=%s carrier_message_id=%s view_mode=%s entrypoint=%s",
        event,
        chat_id,
        dashboard_message_id,
        carrier_message_id,
        view_mode,
        entrypoint,
    )
