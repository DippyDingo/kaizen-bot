export function $(id) {
    return document.getElementById(id);
}

function pad2(value) {
    return String(value).padStart(2, "0");
}

function parseIsoDateParts(dateString) {
    if (!dateString || !/^\d{4}-\d{2}-\d{2}$/.test(dateString)) {
        return null;
    }

    const [year, month, day] = dateString.split("-").map(Number);
    return { year, month, day };
}

function localDateFromIso(dateString) {
    const parts = parseIsoDateParts(dateString);
    if (!parts) {
        return null;
    }
    return new Date(parts.year, parts.month - 1, parts.day);
}

export function getTodayIsoDate() {
    const now = new Date();
    return `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`;
}

export function shiftIsoDate(dateString, diffDays) {
    const parts = parseIsoDateParts(dateString);
    if (!parts) {
        return getTodayIsoDate();
    }

    const utcDate = new Date(Date.UTC(parts.year, parts.month - 1, parts.day));
    utcDate.setUTCDate(utcDate.getUTCDate() + diffDays);

    return `${utcDate.getUTCFullYear()}-${pad2(utcDate.getUTCMonth() + 1)}-${pad2(utcDate.getUTCDate())}`;
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

    const localDate = localDateFromIso(dateString);
    if (!localDate) {
        return dateString;
    }

    return new Intl.DateTimeFormat("ru-RU", {
        day: "numeric",
        month: "long",
        weekday: "long",
    }).format(localDate);
}

export function formatShortDate(dateString) {
    if (!dateString) {
        return "-";
    }

    const localDate = localDateFromIso(dateString);
    if (!localDate) {
        return dateString;
    }

    return new Intl.DateTimeFormat("ru-RU", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
    }).format(localDate);
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
