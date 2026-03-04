from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from bot.config import settings

# Движок — это соединение с PostgreSQL
engine = create_async_engine(
    settings.database_url,
    echo=True,  # В режиме разработки показывает SQL запросы в терминале
)

# Фабрика сессий — через сессию мы делаем запросы к БД
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Базовый класс для всех моделей
class Base(DeclarativeBase):
    pass


# Вспомогательная функция — даёт сессию и закрывает её после использования
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session