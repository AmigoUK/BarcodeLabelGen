/**
 * Client-side mirror of backend/app/services/placeholders.py — used only
 * for the live preview chip in the editor; the authoritative value is
 * computed server-side at generation time.
 */

const DATE_KEY_RE = /^date(?:([+-])(\d+)([dmy]))?(?::(.+))?$/;
const DEFAULT_FORMAT = "DD.MM.YYYY";

function addMonthsClamped(d: Date, months: number): Date {
  const target = new Date(d.getFullYear(), d.getMonth() + months, 1);
  const daysInMonth = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  return new Date(target.getFullYear(), target.getMonth(), Math.min(d.getDate(), daysInMonth));
}

function formatDate(d: Date, fmt: string): string {
  const pad = (n: number, w: number) => String(n).padStart(w, "0");
  return fmt
    .replaceAll("YYYY", pad(d.getFullYear(), 4))
    .replaceAll("YY", pad(d.getFullYear() % 100, 2))
    .replaceAll("DD", pad(d.getDate(), 2))
    .replaceAll("MM", pad(d.getMonth() + 1, 2));
}

/** Returns the formatted date for a date-placeholder key (`date`,
 * `date+14d`, `date-7d:DD/MM/YY`, …) or null when the key isn't valid
 * date syntax — the caller then treats it as an ordinary column. */
export function evaluateDatePlaceholder(key: string, today: Date = new Date()): string | null {
  const m = DATE_KEY_RE.exec(key);
  if (!m) return null;
  const [, sign, amount, unit, fmt] = m;
  let base = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  if (sign) {
    const n = Number(amount) * (sign === "-" ? -1 : 1);
    if (unit === "d") base = new Date(base.getFullYear(), base.getMonth(), base.getDate() + n);
    else if (unit === "m") base = addMonthsClamped(base, n);
    else base = addMonthsClamped(base, n * 12);
  }
  return formatDate(base, fmt ?? DEFAULT_FORMAT);
}

/** True for the bare `date` key (the only form a dataset column may shadow). */
export function isPlainDateKey(key: string): boolean {
  return key === "date";
}
