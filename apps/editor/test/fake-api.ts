// A small fake of the API for component and route tests (no MSW): handlers are registered per method and
// path template; answers are typed with the generated schema; a request nobody handled is answered with
// 501 and fails the test in `afterEach` (see useFakeApi), so a screen cannot silently call an endpoint
// the test did not think about.
import { afterEach, beforeEach, expect } from 'vitest';
import type { paths } from '@/api/schema';
import type { Problem } from '@/lib/problem';

export const BASE = 'http://panel.test';

type Paths = keyof paths & string;
type Method = 'get' | 'post';

type PathsWith<M extends Method> = {
  [P in Paths]: paths[P] extends Record<M, unknown> ? P : never;
}[Paths];

type JsonBody<R, S extends number> =
  R extends Record<S, { content: { 'application/json': infer B } }> ? B : never;

type SuccessBody<P extends Paths, M extends Method> =
  paths[P] extends Record<M, infer Op>
    ? Op extends { responses: infer R }
      ? JsonBody<R, 200> | JsonBody<R, 201> | JsonBody<R, 202>
      : never
    : never;

/** What a handler answers. `T` is the body type of the endpoint (see `ok`). */
export interface Reply<T = unknown> {
  readonly status: number;
  readonly body: T | undefined;
  readonly contentType: string;
  readonly raw?: string;
}

/** A successful JSON answer, checked against the endpoint's response type. */
export function ok<T>(body: T, status = 200): Reply<T> {
  return { status, body, contentType: 'application/json' };
}

/** An RFC 9457 error answer with the API's fields (`kod`, `type`, `status`, extensions). */
export function problem(status: number, kod: string, extra: Partial<Problem> = {}): Reply<never> {
  const body: Problem = {
    type: `urn:mutalaa:problem:${kod}`,
    title: kod,
    status,
    kod,
    traceId: 'deneme-iz-1',
    ...extra,
  };
  return { status, body: body as never, contentType: 'application/problem+json' };
}

export function noContent(): Reply<never> {
  return { status: 204, body: undefined, contentType: 'application/json' };
}

/** A body that is not JSON (an HTML error page of a proxy, for instance). */
export function rawReply(status: number, text: string, contentType = 'text/html'): Reply<never> {
  return { status, body: undefined, contentType, raw: text };
}

/** One request the fake saw. */
export interface Call {
  method: string;
  path: string;
  search: URLSearchParams;
  headers: Headers;
  /** Parsed JSON body; undefined when there was none. */
  json: unknown;
  /** Path template parameters, decoded. */
  params: Record<string, string>;
}

type Handler<T> = Reply<T> | ((call: Call) => Reply<T> | Promise<Reply<T>>);

interface Route {
  method: string;
  template: string;
  pattern: RegExp;
  keys: string[];
  handler: Handler<unknown>;
}

function compile(template: string): { pattern: RegExp; keys: string[] } {
  const keys: string[] = [];
  const source = template
    .split('/')
    .map((part) => {
      const match = /^\{(.+)\}$/.exec(part);
      if (!match) return part.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      keys.push(match[1]!);
      return '([^/]+)';
    })
    .join('/');
  return { pattern: new RegExp(`^${source}$`), keys };
}

export interface FakeApi {
  /** Pass as `createApi({ baseUrl: BASE, fetch })`. */
  readonly fetch: typeof globalThis.fetch;
  /** Every request seen, in order. */
  readonly calls: Call[];
  /** Requests no handler matched. */
  readonly unhandled: string[];
  get<P extends PathsWith<'get'>>(path: P, handler: Handler<SuccessBody<P, 'get'>>): void;
  post<P extends PathsWith<'post'>>(path: P, handler: Handler<SuccessBody<P, 'post'>>): void;
  /** Calls whose path template and method match, e.g. `fake.callsTo('get', '/api/v1/auth/me')`. */
  callsTo(method: Method, template: string): Call[];
  reset(): void;
  /** Fails when a request was not handled. */
  assertClean(): void;
}

export function createFakeApi(): FakeApi {
  let routes: Route[] = [];
  const calls: Call[] = [];
  const unhandled: string[] = [];
  const templates = new WeakMap<Call, string>();

  function add(method: Method, template: string, handler: Handler<unknown>) {
    const { pattern, keys } = compile(template);
    routes.push({ method: method.toUpperCase(), template, pattern, keys, handler });
  }

  const fetch = async (input: Request | string | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url);
    const text = await request.clone().text();
    let json: unknown;
    if (text) {
      try {
        json = JSON.parse(text);
      } catch {
        json = text;
      }
    }
    // The last registration wins, so a test can override a default.
    let found: Route | undefined;
    let params: Record<string, string> = {};
    for (let i = routes.length - 1; i >= 0 && !found; i--) {
      const route = routes[i]!;
      if (route.method !== request.method) continue;
      const match = route.pattern.exec(url.pathname);
      if (!match) continue;
      found = route;
      params = Object.fromEntries(
        route.keys.map((key, index) => [key, decodeURIComponent(match[index + 1]!)]),
      );
    }
    const call: Call = {
      method: request.method,
      path: url.pathname,
      search: url.searchParams,
      headers: request.headers,
      json,
      params,
    };
    calls.push(call);
    if (!found) {
      unhandled.push(`${request.method} ${url.pathname}${url.search}`);
      return new Response(JSON.stringify({ kod: 'hata', status: 501 }), {
        status: 501,
        headers: { 'Content-Type': 'application/problem+json' },
      });
    }
    templates.set(call, found.template);
    const reply = typeof found.handler === 'function' ? await found.handler(call) : found.handler;
    if (reply.status === 204) return new Response(null, { status: 204 });
    const body = reply.raw ?? (reply.body === undefined ? '' : JSON.stringify(reply.body));
    return new Response(body, {
      status: reply.status,
      headers: { 'Content-Type': reply.contentType },
    });
  };

  return {
    fetch: fetch as typeof globalThis.fetch,
    calls,
    unhandled,
    get: (path, handler) => add('get', path, handler as Handler<unknown>),
    post: (path, handler) => add('post', path, handler as Handler<unknown>),
    callsTo: (method, template) =>
      calls.filter(
        (call) => call.method === method.toUpperCase() && templates.get(call) === template,
      ),
    reset() {
      routes = [];
      calls.length = 0;
      unhandled.length = 0;
    },
    assertClean() {
      expect(unhandled, 'requests no fake handler answered').toEqual([]);
    },
  };
}

/** Call at `describe` level: a fresh fake for every test, and a test fails when it left a request unhandled. */
export function useFakeApi(): FakeApi {
  const fake = createFakeApi();
  beforeEach(() => fake.reset());
  afterEach(() => fake.assertClean());
  return fake;
}
