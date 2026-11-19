export interface CronPreset {
  label: string;
  expression: string;
}

export const CRON_PRESETS: CronPreset[] = [
  { label: "Every 5 min", expression: "*/5 * * * *" },
  { label: "Every 15 min", expression: "*/15 * * * *" },
  { label: "Hourly", expression: "0 * * * *" },
  { label: "Daily 00:00", expression: "0 0 * * *" },
  { label: "Weekdays 09:00", expression: "0 9 * * 1-5" },
  { label: "Weekly Mon", expression: "0 9 * * 1" },
];

export const COMMON_TIMEZONES: string[] = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Denver",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Berlin",
  "Asia/Dhaka",
  "Asia/Kolkata",
  "Asia/Singapore",
  "Asia/Tokyo",
  "Australia/Sydney",
];

const WEEKDAY_NAMES: Record<string, string> = {
  "0": "Sunday",
  "7": "Sunday",
  "1": "Monday",
  "2": "Tuesday",
  "3": "Wednesday",
  "4": "Thursday",
  "5": "Friday",
  "6": "Saturday",
};

function padTwo(value: string): string {
  return value.padStart(2, "0");
}

function isIntegerToken(value: string): boolean {
  return /^\d+$/.test(value);
}

export function isValidFiveFieldCron(expression: string): boolean {
  const parts = expression.trim().split(/\s+/).filter(Boolean);
  if (parts.length !== 5) return false;
  return parts.every((part) => /^[\d*,/-]+$/.test(part));
}

export function describeCronExpression(expression: string): string {
  const parts = expression.trim().split(/\s+/).filter(Boolean);
  if (parts.length !== 5) {
    return "Invalid 5-field cron expression";
  }

  const [minute, hour, dayOfMonth, month, dayOfWeek] = parts;

  if (minute === "*" && hour === "*" && dayOfMonth === "*" && month === "*" && dayOfWeek === "*") {
    return "Every minute";
  }

  if (minute.startsWith("*/") && hour === "*" && dayOfMonth === "*" && month === "*" && dayOfWeek === "*") {
    const step = minute.slice(2);
    if (isIntegerToken(step)) {
      return step === "1" ? "Every minute" : `Every ${step} minutes`;
    }
  }

  if (isIntegerToken(minute) && hour === "*" && dayOfMonth === "*" && month === "*" && dayOfWeek === "*") {
    return minute === "0" ? "Every hour" : `Every hour at :${padTwo(minute)}`;
  }

  if (isIntegerToken(minute) && hour.startsWith("*/") && dayOfMonth === "*" && month === "*" && dayOfWeek === "*") {
    const step = hour.slice(2);
    if (isIntegerToken(step)) {
      const minuteSuffix = minute === "0" ? "" : ` at :${padTwo(minute)}`;
      return `Every ${step} hours${minuteSuffix}`;
    }
  }

  if (isIntegerToken(minute) && isIntegerToken(hour) && month === "*") {
    const timeLabel = `${padTwo(hour)}:${padTwo(minute)}`;

    if (dayOfMonth === "*" && dayOfWeek === "*") {
      return `Daily at ${timeLabel}`;
    }
    if (dayOfMonth === "*" && dayOfWeek === "1-5") {
      return `Weekdays at ${timeLabel}`;
    }
    if (dayOfMonth === "*" && dayOfWeek === "0,6") {
      return `Weekends at ${timeLabel}`;
    }
    if (dayOfMonth === "*" && WEEKDAY_NAMES[dayOfWeek]) {
      return `Every ${WEEKDAY_NAMES[dayOfWeek]} at ${timeLabel}`;
    }
    if (isIntegerToken(dayOfMonth) && dayOfWeek === "*") {
      return `Monthly on day ${dayOfMonth} at ${timeLabel}`;
    }
  }

  return `Custom schedule (${parts.join(" ")})`;
}

export function formatCountdown(iso: string | null, nowMs: number): string {
  if (!iso) return "Paused";
  const targetMs = new Date(iso).getTime();
  if (Number.isNaN(targetMs)) return "—";

  const diffSeconds = Math.floor((targetMs - nowMs) / 1000);
  if (diffSeconds <= 0) return "Due now";
  if (diffSeconds < 60) return `in ${diffSeconds}s`;

  const totalMinutes = Math.floor(diffSeconds / 60);
  if (totalMinutes < 60) return `in ${totalMinutes}m`;

  const totalHours = Math.floor(totalMinutes / 60);
  const remMinutes = totalMinutes % 60;
  if (totalHours < 24) {
    return remMinutes > 0 ? `in ${totalHours}h ${remMinutes}m` : `in ${totalHours}h`;
  }

  const days = Math.floor(totalHours / 24);
  const remHours = totalHours % 24;
  return remHours > 0 ? `in ${days}d ${remHours}h` : `in ${days}d`;
}

export function formatScheduleTimestamp(iso: string | null): string {
  if (!iso) return "Never";
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

