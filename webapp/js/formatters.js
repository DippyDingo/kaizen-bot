export function $(id) {
    return document.getElementById(id);
}

export function clampPercent(value) {
    return Math.max(0, Math.min(100, Number(value || 0)));
}

export function minutesToLabel(minutes) {
    const safe = Math.max(0, Number(minutes || 0));
    const hours = Math.floor(safe / 60);
    const rest = safe % 60;
    if (rest === 0) {
        return `${hours} ч`;
    }
    return `${hours} ч ${rest} м`;
}

export function formatDateLabel(dateString) {
    if (!dateString) {
        return "-";
    }
    return new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
        weekday: "long",
    }).format(new Date(`${dateString}T00:00:00`));
}

export function formatShortDate(dateString) {
    if (!dateString) {
        return "-";
    }
    return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    }).format(new Date(`${dateString}T00:00:00`));
}

export function formatPeriodLabel(period) {
    const labels = {
        day: "День",
        "7d": "7 дней",
        "30d": "30 дней",
        all: "Всё время",
    };
    return labels[period] || period;
}

export function setText(id, value) {
    const element = $(id);
    if (element) {
        element.textContent = value;
    }
}

export function setProgress(id, percent) {
    const element = $(id);
    if (element) {
        element.style.width = `${clampPercent(percent)}%`;
    }
}

export function formatMaybeDate(value) {
    return value ? formatShortDate(value) : "нет данных";
}
