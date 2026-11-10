// `?sonraki=` is user-controlled: only a local path may be followed after login (no open redirect).

const ORIGIN = 'http://panel.invalid';
const BLOCKED = ['/giris', '/yetki-yok'];

function hasControlOrBackslash(value: string): boolean {
  for (let i = 0; i < value.length; i++) {
    const code = value.charCodeAt(i);
    if (code <= 0x1f || code === 0x7f || code === 0x5c) return true;
  }
  return false;
}

/** Returns a same-origin path (path, query, hash) or `fallback` for anything else. */
export function safeNext(raw: string | null | undefined, fallback = '/'): string {
  if (!raw || !raw.startsWith('/') || raw.startsWith('//')) return fallback;
  if (hasControlOrBackslash(raw)) return fallback;
  let url: URL;
  try {
    url = new URL(raw, ORIGIN);
  } catch {
    return fallback;
  }
  if (url.origin !== ORIGIN) return fallback;
  if (BLOCKED.includes(url.pathname)) return fallback;
  return `${url.pathname}${url.search}${url.hash}`;
}

/** Login address that returns to `next` afterwards. */
export function loginHref(next: string): string {
  const params = new URLSearchParams({ sonraki: next });
  return `/giris?${params.toString()}`;
}
