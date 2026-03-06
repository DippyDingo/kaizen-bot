from .common import router
from . import calendar, diary, health, tasks  # noqa: F401
from . import core  # noqa: F401

__all__ = ["router"]
