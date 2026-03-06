import hashlib
import hmac
import json
import unittest
from urllib.parse import urlencode

from backend.api.auth import TelegramInitDataError, validate_telegram_init_data


BOT_TOKEN = "test-token"


def build_init_data(*, bot_token: str = BOT_TOKEN, telegram_id: int = 123, first_name: str = "Test") -> str:
    payload = {
        "auth_date": "1710000000",
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(
            {
                "id": telegram_id,
                "first_name": first_name,
                "username": "tester",
            },
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


class TelegramInitDataValidationTests(unittest.TestCase):
    def test_validate_returns_auth_context(self) -> None:
        init_data = build_init_data(telegram_id=777)

        context = validate_telegram_init_data(init_data, BOT_TOKEN)

        self.assertEqual(777, context.telegram_id)
        self.assertEqual(1710000000, context.auth_date)
        self.assertEqual("tester", context.user["username"])

    def test_validate_rejects_invalid_signature(self) -> None:
        init_data = build_init_data() + "broken"

        with self.assertRaises(TelegramInitDataError):
            validate_telegram_init_data(init_data, BOT_TOKEN)

    def test_validate_requires_user_payload(self) -> None:
        payload = {"auth_date": "1710000000", "query_id": "abc"}
        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
        secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
        payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

        with self.assertRaises(TelegramInitDataError):
            validate_telegram_init_data(urlencode(payload), BOT_TOKEN)
