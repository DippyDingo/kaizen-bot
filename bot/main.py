import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from config import settings

# Настройка логов — будем видеть что происходит в терминале
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Создаём экземпляры бота и диспетчера
bot = Bot(token=settings.bot_token)
dp = Dispatcher()


# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_name = message.from_user.first_name
    await message.answer(
        f"👋 Привет, {user_name}!\n\n"
        f"⚔️ Добро пожаловать в <b>KAIZEN</b> —\n"
        f"RPG-трекер который превращает твою жизнь в игру.\n\n"
        f"🧠 Прокачивай персонажа выполняя реальные цели\n"
        f"💧 Следи за здоровьем, сном, водой\n"
        f"👥 Соревнуйся с друзьями в дуэлях\n"
        f"🎮 Собирай легендарную экипировку\n\n"
        f"🚀 <i>改善 — непрерывное улучшение</i>",
        parse_mode="HTML"
    )
    logger.info(f"Новый пользователь: {user_name} (id={message.from_user.id})")


# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📋 <b>Доступные команды:</b>\n\n"
        "/start — начало работы\n"
        "/help — это сообщение\n\n"
        "🔨 Остальные функции в разработке...",
        parse_mode="HTML"
    )


async def main():
    logger.info("🚀 Бот запускается...")
    logger.info(f"Окружение: {settings.environment}")

    # Запускаем polling — бот начинает слушать сообщения
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())