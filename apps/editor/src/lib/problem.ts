import type { Middleware } from 'openapi-fetch';
import type { components } from '@/api/schema';
import { isRecord } from '@/lib/payload';

/** RFC 9457 error body of the API. Validation errors (400) add `errors` (field -> messages). */
export type Problem = components['schemas']['ProblemDetails'] & {
  errors?: Record<string, string[]>;
};

/** The 18 codes of the API (ProblemDetails.kod, Backend API 6; same list as OpenApiSetup.cs). */
export const API_PROBLEM_CODES = [
  'dogrulama',
  'capa-gecersiz',
  'degistirilemez-metin',
  'oturum-acilamadi',
  'yetki-yok',
  'bulunamadi',
  'yontem-desteklenmiyor',
  'durum-gecisi-gecersiz',
  'cakisma',
  'surum-uyusmazligi',
  'surum-gerekli',
  'inceleme-desteklenmiyor',
  'yayin-suruyor',
  'kalite-kapisi',
  'onceki-yayin-bozuk',
  'depo-erisilemiyor',
  'hata',
  'sunucu-hatasi',
] as const;

/** Codes made up by the client: no HTTP answer at all, or an answer that is not a problem body. */
export const CLIENT_PROBLEM_CODES = ['ag-hatasi', 'yanit-bozuk'] as const;

export type ApiProblemCode = (typeof API_PROBLEM_CODES)[number];
export type ClientProblemCode = (typeof CLIENT_PROBLEM_CODES)[number];
export type ProblemCode = ApiProblemCode | ClientProblemCode;

export const PROBLEM_TYPE_PREFIX = 'urn:mutalaa:problem:';

function codeFromType(type: unknown): string | undefined {
  return typeof type === 'string' && type.startsWith(PROBLEM_TYPE_PREFIX)
    ? type.slice(PROBLEM_TYPE_PREFIX.length)
    : undefined;
}

function clientProblem(kod: ClientProblemCode, status: number): Problem {
  return { type: `${PROBLEM_TYPE_PREFIX}${kod}`, kod, status };
}

/**
 * Any thrown or returned error to a Problem. Problem bodies keep their fields (`kod` is taken from `type`
 * when missing, `status` from `status` when given); a TypeError (fetch failed) is `ag-hatasi`; everything
 * else is `yanit-bozuk`. Never throws.
 */
export function toProblem(error: unknown, status?: number): Problem {
  if (isRecord(error) && (typeof error.kod === 'string' || typeof error.type === 'string')) {
    const problem = { ...error } as Problem;
    if (typeof problem.kod !== 'string') {
      const kod = codeFromType(problem.type);
      if (kod) problem.kod = kod;
    }
    if (typeof problem.status !== 'number' && status !== undefined) problem.status = status;
    return problem;
  }
  if (error instanceof TypeError) return clientProblem('ag-hatasi', 0);
  return clientProblem('yanit-bozuk', status ?? 0);
}

/** HTTP status of a problem-shaped error, or undefined when it is not one (network error, plain Error). */
export function problemStatus(error: unknown): number | undefined {
  return isRecord(error) && typeof error.status === 'number' ? error.status : undefined;
}

/** `kod` of a problem-shaped error. */
export function problemCode(error: unknown): string | undefined {
  return toProblem(error).kod;
}

/** Positive integers of an `kimlikler` extension; anything else is dropped. */
export function problemIds(problem: Problem): number[] {
  const ids = problem.kimlikler;
  return Array.isArray(ids) ? ids.filter((id) => Number.isSafeInteger(id)) : [];
}

/**
 * Turns every non-JSON (or status-less) error answer into the ProblemDetails shape: the body of a
 * 502 from the reverse proxy, an HTML page or an empty body becomes `yanit-bozuk` with the real
 * `status`; a JSON problem body gets `status` filled in when the server left it out. Successful
 * answers pass untouched.
 */
export const problemMiddleware: Middleware = {
  async onResponse({ response }) {
    if (response.status < 400) return undefined;
    let parsed: unknown;
    try {
      const text = await response.clone().text();
      parsed = text ? JSON.parse(text) : undefined;
    } catch {
      parsed = undefined;
    }
    const problem = isRecord(parsed)
      ? toProblem(parsed, response.status)
      : clientProblem('yanit-bozuk', response.status);
    if (typeof problem.status !== 'number') problem.status = response.status;
    return new Response(JSON.stringify(problem), {
      status: response.status,
      statusText: response.statusText,
      headers: { 'Content-Type': 'application/problem+json' },
    });
  },
};
