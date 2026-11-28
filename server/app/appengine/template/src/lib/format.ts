// v0.999.334 one way to show numbers, money, dates and times - in the app's own country and language (src/lib/locale.ts).
// The rules come from Ant Design's data-format spec (MIT), read for every country: group the digits, show the currency
// the visitor's way (₹1,499 in India, $1,499.00 in the US, 1.499,00 € in Germany), dates and ranges in her own order,
// "5 minutes ago" for the last day. Pages and blocks call these - never "₹" + n, toFixed(2) on money, or a date built
// from getMonth() + 1.
import { CURRENCY, LOCALE, TIME_ZONE } from "./locale";

export { CURRENCY, LOCALE, TIME_ZONE };

type When = Date | string | number;

function asDate(d: When): Date | null {
  const x = d instanceof Date ? d : new Date(d);
  return Number.isNaN(x.getTime()) ? null : x;
}

/** 1234567.5 -> "12,34,567.5" (en-IN) / "1,234,567.5" (en-US). `decimals` fixes the places. */
export function num(n: number, decimals?: number): string {
  if (!Number.isFinite(n)) return "";
  const o = decimals === undefined ? {} : { minimumFractionDigits: decimals, maximumFractionDigits: decimals };
  return new Intl.NumberFormat(LOCALE, o).format(n);
}

/** An amount in the app's currency (or another one): 1499 -> "₹1,499" / "$1,499.00". compact: 120000 -> "₹1.2L". */
export function money(n: number, currency: string = CURRENCY, opts: { compact?: boolean; decimals?: number } = {}): string {
  if (!Number.isFinite(n)) return "";
  const o: Intl.NumberFormatOptions = { style: "currency", currency };
  if (opts.compact) Object.assign(o, { notation: "compact", maximumFractionDigits: 1 });
  else if (opts.decimals !== undefined) Object.assign(o, { minimumFractionDigits: opts.decimals, maximumFractionDigits: opts.decimals });
  else if (Number.isInteger(n)) Object.assign(o, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  try {
    return new Intl.NumberFormat(LOCALE, o).format(n);
  } catch {
    return `${currency} ${num(n)}`;
  }
}

/** A share given as a percent number: 12.3 -> "12.3%". */
export function percent(n: number, decimals = 1): string {
  if (!Number.isFinite(n)) return "";
  return new Intl.NumberFormat(LOCALE, { style: "percent", maximumFractionDigits: decimals }).format(n / 100);
}

/** A big count kept short: 12400 -> "12K" / "12 हज़ार". */
export function compact(n: number): string {
  if (!Number.isFinite(n)) return "";
  return new Intl.NumberFormat(LOCALE, { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

/** A date in the app's own order: "28 Nov 2026" / "Nov 28, 2026". */
export function date(d: When, style: "short" | "medium" | "long" = "medium"): string {
  const x = asDate(d);
  return x ? new Intl.DateTimeFormat(LOCALE, { dateStyle: style, timeZone: TIME_ZONE }).format(x) : "";
}

/** A time of day, the way the country reads it (24-hour or am / pm). */
export function time(d: When): string {
  const x = asDate(d);
  return x ? new Intl.DateTimeFormat(LOCALE, { timeStyle: "short", timeZone: TIME_ZONE }).format(x) : "";
}

/** A date and its time together. */
export function dateTime(d: When): string {
  const x = asDate(d);
  return x ? new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeStyle: "short", timeZone: TIME_ZONE }).format(x) : "";
}

/** From - to, said once: "28 Nov – 2 Dec 2026". */
export function range(a: When, b: When): string {
  const x = asDate(a), y = asDate(b);
  if (!x || !y) return "";
  const f = new Intl.DateTimeFormat(LOCALE, { dateStyle: "medium", timeZone: TIME_ZONE }) as Intl.DateTimeFormat & {
    formatRange?: (p: Date, q: Date) => string;
  };
  return f.formatRange ? f.formatRange(x, y) : `${f.format(x)} – ${f.format(y)}`;
}

/** How long ago, for the last week ("just now", "5 minutes ago", "yesterday"); older = the date itself. */
export function ago(d: When, now: number = Date.now()): string {
  const x = asDate(d);
  if (!x) return "";
  const s = Math.round((x.getTime() - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(LOCALE, { numeric: "auto" });
  const a = Math.abs(s);
  if (a < 45) return rtf.format(0, "second");
  if (a < 3600) return rtf.format(Math.round(s / 60), "minute");
  if (a < 86400) return rtf.format(Math.round(s / 3600), "hour");
  if (a < 7 * 86400) return rtf.format(Math.round(s / 86400), "day");
  return date(x);
}
