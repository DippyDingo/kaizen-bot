import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.handlers import single_message_router
from bot.handlers.single_message_parts.common import initialize_bot_ui

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

dp.include_router(single_message_router)


async def main() -> None:
    logger.info("Starting KAIZEN bot")
    logger.info("Environment: %s", settings.environment)
    await initialize_bot_ui(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
