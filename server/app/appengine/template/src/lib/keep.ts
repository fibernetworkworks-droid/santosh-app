// Hoola App Engine - locked by Hoola. v0.999.82 D8: a small value kept in the VISITOR's browser - only where the page
// is allowed one: a website on its own address (her domain / its free address). Under Hoola's address every page runs
// sealed and there is no storage: then nothing is kept and nothing breaks (the value lasts while the page is open).
// Keep only what the visitor would expect a website to remember (a cart, ticks) - never anything secret.
const PREFIX = "hoola:";

export function keepGet<T>(key: string, fallback: T): T {
  try {
    const raw = window.localStorage.getItem(PREFIX + key);
    return raw === null ? fallback : (JSON.parse(raw) as T);
  } catch {
    return fallback;
  }
}

export function keepSet(key: string, value: unknown): void {
  try {
    window.localStorage.setItem(PREFIX + key, JSON.stringify(value).slice(0, 20000));
  } catch {
    /* a sealed page keeps nothing */
  }
}
