import { setText, minutesToLabel, formatMaybeDate } from "../formatters.js";

export function renderHealthScreen(payload) {
    setText("health-day-water-value", `${payload.day.water.total_ml}/${payload.day.water.target_ml} мл`);
    setText("health-day-water-subvalue", `${payload.day.water.percent}% от цели`);

    setText("health-day-sleep-value", minutesToLabel(payload.day.sleep.total_minutes));
    setText("health-day-sleep-subvalue", `качество ${payload.day.sleep.avg_quality || 0}`);

    setText("health-day-workout-value", `${payload.day.workout.total_minutes} мин`);
    setText("health-day-workout-subvalue", `${payload.day.workout.percent}% от цели`);

    setText(
        "health-day-wellbeing-value",
        payload.day.wellbeing.has_entry
            ? `${payload.day.wellbeing.energy_level}/5 · ${payload.day.wellbeing.stress_level}/5`
            : "нет записи",
    );
    setText(
        "health-day-wellbeing-subvalue",
        payload.day.wellbeing.has_entry ? "энергия · стресс" : "заполни через Telegram",
    );

    setText("health-day-medications-value", `${payload.day.medications.taken}/${payload.day.medications.total}`);
    setText("health-day-medications-subvalue", `${payload.day.medications.skipped} пропусков`);

    setText("health-week-water-value", `${payload.week.water.total_ml} мл`);
    setText("health-week-water-subvalue", `${payload.week.water.active_days} активных дней`);

    setText("health-week-sleep-value", minutesToLabel(payload.week.sleep.total_minutes));
    setText("health-week-sleep-subvalue", `ср ${payload.week.sleep.avg_quality || 0} · лучший ${minutesToLabel(payload.week.sleep.best_day_minutes)}`);

    setText("health-week-workout-value", `${payload.week.workout.total_minutes} мин`);
    setText("health-week-workout-subvalue", `${payload.week.workout.sessions_count} сессий · лучший ${minutesToLabel(payload.week.workout.best_day_minutes)}`);

    setText(
        "health-week-wellbeing-value",
        `${payload.week.wellbeing.avg_energy || 0}/5 · ${payload.week.wellbeing.avg_stress || 0}/5`,
    );
    setText(
        "health-week-wellbeing-subvalue",
        `лучший ${formatMaybeDate(payload.week.wellbeing.best_energy_day)} · стресс ${formatMaybeDate(payload.week.wellbeing.highest_stress_day)}`,
    );

    setText("health-week-medications-value", `${payload.week.medications.taken_count}/${payload.week.medications.total_logs}`);
    setText(
        "health-week-medications-subvalue",
        payload.week.medications.top_title ? `чаще всего ${payload.week.medications.top_title}` : "нет курса",
    );
}
