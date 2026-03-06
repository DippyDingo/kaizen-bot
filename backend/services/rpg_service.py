from backend.models import User


EXP_TABLE: dict[str, int] = {
    "task_completed": 10,
    "water_logged": 2,
    "sleep_logged": 20,
    "diary_logged": 10,
}


def calculate_next_level_exp(current_level: int) -> int:
    # Linear growth is enough for MVP and easy to tune later.
    return 100 + (current_level - 1) * 20


def add_exp(user: User, amount: int) -> int:
    if amount <= 0:
        return 0

    user.exp += amount
    level_ups = 0

    while user.exp >= user.exp_to_next_level:
        user.exp -= user.exp_to_next_level
        user.level += 1
        user.exp_to_next_level = calculate_next_level_exp(user.level)
        level_ups += 1

    return level_ups


def remove_exp(user: User, amount: int) -> int:
    if amount <= 0:
        return 0

    level_downs = 0
    remaining = amount

    while remaining > 0:
        if user.exp >= remaining:
            user.exp -= remaining
            remaining = 0
            break

        remaining -= user.exp

        if user.level <= 1:
            user.level = 1
            user.exp = 0
            user.exp_to_next_level = calculate_next_level_exp(user.level)
            break

        user.level -= 1
        user.exp_to_next_level = calculate_next_level_exp(user.level)
        user.exp = user.exp_to_next_level
        level_downs += 1

    return level_downs
