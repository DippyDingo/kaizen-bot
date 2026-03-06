from aiogram.fsm.state import State, StatesGroup


class DashboardStates(StatesGroup):
    waiting_display_name = State()
    waiting_task_title = State()
    waiting_task_priority = State()
    waiting_task_date = State()
    waiting_diary_text = State()
    waiting_sleep_exact_time = State()
    waiting_medication_title = State()
    waiting_medication_dose = State()
    waiting_medication_time_text = State()
    waiting_medication_days_text = State()
    waiting_workout_duration_text = State()
    waiting_daily_water_target = State()
    waiting_daily_workout_target = State()
