// @vitest-environment node
// ProblemDetails handling (A15.3): the code list, the Turkish messages, the middleware.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';
import { createApi } from '@/api/client';
import { tr } from '@/i18n/tr';
import {
  API_PROBLEM_CODES,
  CLIENT_PROBLEM_CODES,
  problemCode,
  problemIds,
  problemStatus,
  toProblem,
} from '@/lib/problem';
import { kodOf, problemText, showsServerDetail } from '@/lib/problem-text';
import { BASE, createFakeApi, ok, rawReply, problem } from './fake-api';
import { session } from './fixtures';

// The list of OpenApiSetup.cs (server/Mutalaa.Api/Hosting/OpenApiSetup.cs, the `kod` description), as a fixed array.
const OPEN_API_SETUP_CODES = [
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
];

const MARKER = 'Makine tarafindan okunur hata kodu (type son parcasiyla ayni): ';

describe('problem code list', () => {
  it('is the fixed list of OpenApiSetup.cs (18 codes)', () => {
    expect([...API_PROBLEM_CODES]).toEqual(OPEN_API_SETUP_CODES);
    expect(OPEN_API_SETUP_CODES).toHaveLength(18);
  });

  it('is still the list in the server source', () => {
    const source = readFileSync(
      new URL('../../../server/Mutalaa.Api/Hosting/OpenApiSetup.cs', import.meta.url),
      'utf8',
    ).replace(/"\s*\+\s*"/g, '');
    const start = source.indexOf(MARKER);
    expect(start).toBeGreaterThan(-1);
    const end = source.indexOf('.', start + MARKER.length);
    const codes = source
      .slice(start + MARKER.length, end)
      .split(',')
      .map((code) => code.trim());
    expect(codes).toEqual(OPEN_API_SETUP_CODES);
  });

  it('is still the list in the generated schema', () => {
    const schema = readFileSync(new URL('../src/api/schema.d.ts', import.meta.url), 'utf8');
    const start = schema.indexOf(MARKER);
    expect(start).toBeGreaterThan(-1);
    const end = schema.indexOf('.', start + MARKER.length);
    const codes = schema
      .slice(start + MARKER.length, end)
      .split(',')
      .map((code) => code.trim());
    expect(codes).toEqual(OPEN_API_SETUP_CODES);
  });

  it('has a Turkish message for every API and client code', () => {
    for (const kod of [...API_PROBLEM_CODES, ...CLIENT_PROBLEM_CODES]) {
      const text = problemText({ kod });
      expect(text, kod).not.toBe('');
      expect(text, kod).toBe(tr.problem.codes[kod]);
      expect(text, kod).not.toBe(tr.problem.unknownCode(kod));
    }
    expect(Object.keys(tr.problem.codes).sort()).toEqual(
      [...API_PROBLEM_CODES, ...CLIENT_PROBLEM_CODES].sort(),
    );
  });
});

describe('problemText', () => {
  it('words the same code differently per operation', () => {
    expect(problemText({ kod: 'surum-uyusmazligi' }, 'decision')).toBe(
      tr.problem.contexts.decision['surum-uyusmazligi'],
    );
    expect(problemText({ kod: 'surum-uyusmazligi' }, 'bulk')).toBe(
      tr.problem.contexts.bulk['surum-uyusmazligi'],
    );
    expect(problemText({ kod: 'oturum-acilamadi' }, 'login')).toBe(
      tr.problem.contexts.login['oturum-acilamadi'],
    );
    expect(problemText({ kod: 'yayin-suruyor' }, 'release')).toBe(
      tr.problem.contexts.release['yayin-suruyor'],
    );
    expect(problemText({ kod: 'cakisma' }, 'correction')).toBe(
      tr.problem.contexts.correction.cakisma,
    );
    // A code without an override uses the generic message in every context.
    expect(problemText({ kod: 'depo-erisilemiyor' }, 'release')).toBe(
      tr.problem.codes['depo-erisilemiyor'],
    );
  });

  it('shows the offset message verbatim for a 422 about marks and sentences', () => {
    const offset = problemText(
      {
        kod: 'inceleme-desteklenmiyor',
        detail:
          "Ofsetli alanlar (marks, sentences) metin degisimini A20'de hesaplanana kadar desteklenmiyor.",
      },
      'decision',
    );
    expect(offset).toBe(
      "Bu birimin ofsetli alanları (işaretler, cümleler) var; metin düzeltmesi A20'de desteklenecek",
    );
    // Another reason for the same code keeps the generic wording.
    expect(
      problemText(
        { kod: 'inceleme-desteklenmiyor', detail: 'Ikinci onay degeri degistiremez.' },
        'decision',
      ),
    ).toBe(tr.problem.codes['inceleme-desteklenmiyor']);
  });

  it('shows an unknown code raw and falls back to the type when kod is missing', () => {
    expect(problemText({ kod: 'bambaska-bir-kod' })).toBe(
      tr.problem.unknownCode('bambaska-bir-kod'),
    );
    expect(kodOf({ type: 'urn:mutalaa:problem:cakisma' })).toBe('cakisma');
    expect(problemText({ type: 'urn:mutalaa:problem:cakisma' })).toBe(tr.problem.codes.cakisma);
    expect(problemText({})).toBe(tr.problem.codes['yanit-bozuk']);
  });

  it('adds the server message only where it carries information', () => {
    expect(
      showsServerDetail({
        kod: 'durum-gecisi-gecersiz',
        detail: 'Editor kendi onerisini onaylayamaz.',
      }),
    ).toBe(true);
    expect(showsServerDetail({ kod: 'surum-uyusmazligi', detail: 'x' })).toBe(false);
    expect(showsServerDetail({ kod: 'dogrulama' })).toBe(false);
  });
});

describe('toProblem', () => {
  it('keeps a problem body and fills kod from type and status from the answer', () => {
    expect(toProblem({ type: 'urn:mutalaa:problem:bulunamadi' }, 404)).toMatchObject({
      kod: 'bulunamadi',
      status: 404,
    });
    expect(toProblem({ kod: 'cakisma', status: 409, kimlikler: [1, 2] })).toMatchObject({
      kod: 'cakisma',
      status: 409,
      kimlikler: [1, 2],
    });
  });

  it('turns a failed fetch into ag-hatasi and anything else into yanit-bozuk', () => {
    expect(toProblem(new TypeError('Failed to fetch'))).toMatchObject({
      kod: 'ag-hatasi',
      status: 0,
    });
    expect(toProblem(new SyntaxError('Unexpected token <'))).toMatchObject({ kod: 'yanit-bozuk' });
    expect(toProblem('metin')).toMatchObject({ kod: 'yanit-bozuk' });
    expect(toProblem(undefined)).toMatchObject({ kod: 'yanit-bozuk' });
    expect(toProblem(null, 502)).toMatchObject({ kod: 'yanit-bozuk', status: 502 });
  });

  it('exposes status, code and ids', () => {
    expect(problemStatus({ status: 412 })).toBe(412);
    expect(problemStatus(new TypeError('x'))).toBeUndefined();
    expect(problemCode({ kod: 'hata' })).toBe('hata');
    expect(problemIds({ kimlikler: [3, 5] })).toEqual([3, 5]);
    expect(problemIds({})).toEqual([]);
  });
});

describe('problem middleware (createApi)', () => {
  function client() {
    const fake = createFakeApi();
    const { client: c } = createApi({ baseUrl: BASE, fetch: fake.fetch });
    return { fake, c };
  }

  it('passes a successful answer through', async () => {
    const { fake, c } = client();
    fake.get('/api/v1/auth/me', ok(session()));
    const { data, error } = await c.GET('/api/v1/auth/me');
    expect(error).toBeUndefined();
    expect(data?.roller).toEqual(['editor']);
  });

  it('keeps a JSON problem body and always writes status', async () => {
    const { fake, c } = client();
    fake.get(
      '/api/v1/auth/me',
      rawReply(
        404,
        JSON.stringify({ type: 'urn:mutalaa:problem:bulunamadi' }),
        'application/problem+json',
      ),
    );
    const { error } = await c.GET('/api/v1/auth/me');
    expect(error).toMatchObject({ kod: 'bulunamadi', status: 404 });
  });

  it('turns an HTML error page into yanit-bozuk with the real status', async () => {
    const { fake, c } = client();
    fake.get('/api/v1/auth/me', rawReply(502, '<html><body>Bad Gateway</body></html>'));
    const { error } = await c.GET('/api/v1/auth/me');
    expect(error).toMatchObject({
      kod: 'yanit-bozuk',
      status: 502,
      type: 'urn:mutalaa:problem:yanit-bozuk',
    });
  });

  it('turns an empty error body and a JSON array into yanit-bozuk with status', async () => {
    const { fake, c } = client();
    fake.get('/api/v1/auth/me', rawReply(500, ''));
    expect((await c.GET('/api/v1/auth/me')).error).toMatchObject({
      kod: 'yanit-bozuk',
      status: 500,
    });
    fake.get('/api/v1/auth/me', rawReply(400, '[1,2]', 'application/json'));
    expect((await c.GET('/api/v1/auth/me')).error).toMatchObject({
      kod: 'yanit-bozuk',
      status: 400,
    });
  });

  it('keeps the extensions of a real problem', async () => {
    const { fake, c } = client();
    fake.get('/api/v1/auth/me', problem(412, 'surum-uyusmazligi', { kimlikler: [4, 9] }));
    const { error } = await c.GET('/api/v1/auth/me');
    expect(error).toMatchObject({ kod: 'surum-uyusmazligi', status: 412, kimlikler: [4, 9] });
  });

  it('lets a network failure throw (it is shown as ag-hatasi)', async () => {
    const failing = (() =>
      Promise.reject(new TypeError('Failed to fetch'))) as unknown as typeof fetch;
    const { client: c } = createApi({ baseUrl: BASE, fetch: failing });
    const thrown = await c.GET('/api/v1/auth/me').catch((e: unknown) => e);
    expect(toProblem(thrown)).toMatchObject({ kod: 'ag-hatasi' });
  });
});
