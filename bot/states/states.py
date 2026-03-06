from aiogram.fsm.state import State, StatesGroup


class DashboardStates(StatesGroup):
    waiting_task_title = State()
    waiting_task_priority = State()
    waiting_task_date = State()
    waiting_diary_text = State()
