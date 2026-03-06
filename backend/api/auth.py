from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl


class TelegramInitDataError(ValueError):
    pass


@dataclass(slots=True)
class TelegramAuthContext:
    telegram_id: int
    auth_date: int | None
    user: dict[str, Any]
    fields: dict[str, str]
    raw_init_data: str


def _build_secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()


def _build_data_check_string(fields: dict[str, str]) -> str:
    return "\n".join(f"{key}={value}" for key, value in sorted(fields.items()))


def validate_telegram_init_data(init_data: str, bot_token: str) -> TelegramAuthContext:
    if not init_data:
        raise TelegramInitDataError("missing initData")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise TelegramInitDataError("missing hash")

    data_check_string = _build_data_check_string(pairs)
    secret_key = _build_secret_key(bot_token)
    calculated_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(calculated_hash, received_hash):
        raise TelegramInitDataError("invalid signature")

    raw_user = pairs.get("user")
    if not raw_user:
        raise TelegramInitDataError("missing user payload")

    try:
        user = json.loads(raw_user)
    except json.JSONDecodeError as exc:
        raise TelegramInitDataError("invalid user payload") from exc

    telegram_id = user.get("id")
    if not isinstance(telegram_id, int):
        raise TelegramInitDataError("missing telegram user id")

    auth_date_raw = pairs.get("auth_date")
    auth_date = None
    if auth_date_raw:
        try:
            auth_date = int(auth_date_raw)
        except ValueError as exc:
            raise TelegramInitDataError("invalid auth_date") from exc

    return TelegramAuthContext(
        telegram_id=telegram_id,
        auth_date=auth_date,
        user=user,
        fields=pairs,
        raw_init_data=init_data,
    )
