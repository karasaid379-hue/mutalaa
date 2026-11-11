// Synthetic fixtures of the OCR queue (A15.4): made-up text only ("Deneme meal metni 1"), never Quran, meal,
// tafsir, hadith or Risale text. The Arabic string is a letter sequence built from code points, not Quran text.
// The scan files are built here byte by byte (a TIFF, a PNG header, a JPEG header); nothing is read from disk.
import { vi } from 'vitest';
import type { components } from '@/api/schema';
import { ok, type Call, type FakeApi } from './fake-api';
import { reviewDetail, reviewItem, unitDetail } from './fixtures';

type S = components['schemas'];

export const ARABIC_AYAH = String.fromCodePoint(
  0x0627,
  0x0628,
  0x062c,
  0x062f,
  0x0020,
  0x0647,
  0x0648,
);

export const SCAN_ATTRS = { baski: 'deneme-baski', sayfa: 'c01-s0001' } as const;
export const SCAN_URL_PATH = `/api/v1/scans/${SCAN_ATTRS.baski}/${SCAN_ATTRS.sayfa}`;

export const MEAL_ANCHOR = 'meal:deneme:1:2';
export const AYAH_ANCHOR = 'q:1:2';

/**
 * `onerilen` of a pipeline record in the real shape (export/pg_meal.py `onerilen_kur`): text and hash, warning codes
 * and the witness agreement (`skor` integer 0..100, `kapsam` `[ilk, son]` or null). Text is made up.
 */
export function pipelineProposal(over: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    metin: 'Deneme meal paragrafı 1',
    content_hash: 'hash-1',
    uyari: ['numarasiz_parca', 'yinelenen_numara'],
    tanik: {
      skor: 97,
      kapsam: [1, 2],
      yontem: 'rapidfuzz.fuzz.ratio/tr_narrow',
      yontem_surumu: '1',
      kaynak: 'elmalili-meal-epub',
    },
    ...over,
  };
}

export const DECIDED = {
  id: 1,
  durum: 'onaylandi',
  eylem: 'onayla',
  ikinci_onay_bekliyor: false,
  hedef_durumu: 'onayli',
  xmin: 101,
};

// --- records ---

export function ocrItem(id: number, over: Partial<S['ReviewItemDto']> = {}): S['ReviewItemDto'] {
  return reviewItem({
    id,
    hedef_anahtar: `meal:deneme:1:${id + 1}`,
    onceki: { metin: 'Deneme meal metni eski', content_hash: 'hash-0' },
    onerilen: { metin: 'Deneme meal metni yeni', content_hash: 'hash-1' },
    xmin: 100 + id,
    ...over,
  });
}

export function ocrDetail(
  id: number,
  over: Partial<S['ReviewDetailDto']> = {},
): S['ReviewDetailDto'] {
  return reviewDetail({ ...ocrItem(id), ...over });
}

/** The unit of an OCR record: a meal with the (provisional) scan mapping in `attrs`. */
export function ocrUnit(anchor: string, over: Partial<S['UnitDetail']> = {}): S['UnitDetail'] {
  return unitDetail({
    anchor,
    kind: 'meal',
    kaynak_tur: 'meal',
    metin: 'Deneme meal metni eski',
    attrs: { ...SCAN_ATTRS },
    marks: [],
    sentences: null,
    duzeltilebilir: true,
    ...over,
  });
}

/** A Tanzil ayah unit (cannot be edited). */
export function ayahUnit(anchor: string = AYAH_ANCHOR): S['UnitDetail'] {
  return unitDetail({
    anchor,
    kind: 'ayet',
    kaynak_tur: 'kuran_metni',
    metin: ARABIC_AYAH,
    attrs: {},
    duzeltilebilir: false,
  });
}

export interface OcrHandlerOptions {
  /** The unit of the reviewed meal (default: `ocrUnit`). */
  unit?: (anchor: string) => S['UnitDetail'];
  detail?: (id: number) => S['ReviewDetailDto'];
}

/** Handlers of the OCR detail: the review, the meal unit and the Tanzil ayah. Register before `signedIn`. */
export function ocrHandlers(fake: FakeApi, options: OcrHandlerOptions = {}): void {
  fake.get('/api/v1/reviews/{id}', (call) =>
    ok((options.detail ?? ((id) => ocrDetail(id)))(Number(call.params.id))),
  );
  fake.get('/api/v1/units/{anchor}', (call) => {
    const anchor = call.params.anchor!;
    if (anchor.startsWith('q:')) return ok(ayahUnit(anchor));
    return ok((options.unit ?? ((a) => ocrUnit(a)))(anchor));
  });
}

// --- scan files ---

/**
 * A little-endian, 8-bit, uncompressed grayscale TIFF written byte by byte. `width` and `height` go into the
 * tags; `pixels` (default `width * height` ascending bytes) is the strip data, so a test can claim a huge size
 * with no data.
 */
export function syntheticTiff(width = 2, height = 1, pixels?: Uint8Array): Uint8Array {
  const data = pixels ?? Uint8Array.from({ length: width * height }, (_, i) => (i * 85) % 256);
  const entries: [tag: number, type: number, count: number, value: number][] = [
    [256, 3, 1, width],
    [257, 3, 1, height],
    [258, 3, 1, 8],
    [259, 3, 1, 1],
    [262, 3, 1, 1],
    [273, 4, 1, 0],
    [277, 3, 1, 1],
    [278, 3, 1, height],
    [279, 4, 1, data.length],
  ];
  const ifdSize = 2 + entries.length * 12 + 4;
  const dataOffset = 8 + ifdSize;
  const bytes = new Uint8Array(dataOffset + data.length);
  const view = new DataView(bytes.buffer);
  bytes.set([0x49, 0x49], 0);
  view.setUint16(2, 42, true);
  view.setUint32(4, 8, true);
  view.setUint16(8, entries.length, true);
  entries.forEach(([tag, type, count, value], i) => {
    const at = 10 + i * 12;
    view.setUint16(at, tag, true);
    view.setUint16(at + 2, type, true);
    view.setUint32(at + 4, count, true);
    if (type === 3) view.setUint16(at + 8, value, true);
    else view.setUint32(at + 8, tag === 273 ? dataOffset : value, true);
  });
  view.setUint32(10 + entries.length * 12, 0, true);
  bytes.set(data, dataOffset);
  return bytes;
}

/** The first bytes of a PNG file (enough for the kind check; the browser would decode it, jsdom does not). */
export const PNG_BYTES = Uint8Array.from([
  0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a, 0, 0, 0, 0,
]);
/** The first bytes of a JPEG file. */
export const JPEG_BYTES = Uint8Array.from([
  0xff, 0xd8, 0xff, 0xe0, 0, 0x10, 0x4a, 0x46, 0x49, 0x46,
]);

export interface ScanReply {
  status?: number;
  body?: Uint8Array | string;
  contentType?: string;
}

export interface ScanFake extends FakeApi {
  /** Requests for a page image, in order. */
  readonly scanCalls: { path: string; signal: AbortSignal }[];
}

/**
 * Wraps a fake so `GET /api/v1/scans/...` is answered with a binary body (the fake's replies are JSON only);
 * every other request goes to the fake unchanged. Pass the result to `renderApp` and friends.
 */
export function withScanFetch(
  fake: FakeApi,
  respond: (call: { path: string }) => ScanReply | Promise<ScanReply>,
): ScanFake {
  const scanCalls: { path: string; signal: AbortSignal }[] = [];
  const fetch = async (input: Request | string | URL, init?: RequestInit): Promise<Response> => {
    const request = input instanceof Request ? input : new Request(input, init);
    const url = new URL(request.url);
    if (!url.pathname.startsWith('/api/v1/scans/')) return fake.fetch(request);
    scanCalls.push({ path: url.pathname, signal: request.signal });
    const reply = await respond({ path: url.pathname });
    const status = reply.status ?? 200;
    const body = reply.body ?? new Uint8Array();
    return new Response(status === 204 ? null : (body as BodyInit), {
      status,
      headers: { 'Content-Type': reply.contentType ?? 'image/tiff' },
    });
  };
  return Object.assign(Object.create(fake) as FakeApi, {
    fetch: fetch as typeof globalThis.fetch,
    scanCalls,
  });
}

// --- jsdom has no canvas and no object URLs ---

export interface CanvasStub {
  context: {
    createImageData: ReturnType<typeof vi.fn>;
    putImageData: ReturnType<typeof vi.fn>;
    drawImage: ReturnType<typeof vi.fn>;
    imageSmoothingQuality: string;
  };
  restore: () => void;
}

/** Replaces `getContext('2d')` with a recording fake; `createImageData` returns a real-sized buffer unless `lightweight`. */
export function stubCanvas(options: { lightweight?: boolean } = {}): CanvasStub {
  const context = {
    createImageData: vi.fn((width: number, height: number) => ({
      width,
      height,
      data: options.lightweight
        ? ({ set: vi.fn() } as unknown as Uint8ClampedArray)
        : new Uint8ClampedArray(width * height * 4),
    })),
    putImageData: vi.fn(),
    drawImage: vi.fn(),
    imageSmoothingQuality: 'low',
  };
  const spy = vi
    .spyOn(HTMLCanvasElement.prototype, 'getContext')
    .mockImplementation(() => context as unknown as RenderingContext);
  return { context, restore: () => spy.mockRestore() };
}

export interface ObjectUrlStub {
  created: Blob[];
  revoked: string[];
  restore: () => void;
}

/** `URL.createObjectURL` and `revokeObjectURL` as recording fakes (`blob:deneme-1`, `blob:deneme-2`, ...). */
export function stubObjectUrls(): ObjectUrlStub {
  const created: Blob[] = [];
  const revoked: string[] = [];
  const originalCreate = URL.createObjectURL;
  const originalRevoke = URL.revokeObjectURL;
  URL.createObjectURL = (blob: Blob | MediaSource) => {
    created.push(blob as Blob);
    return `blob:deneme-${created.length}`;
  };
  URL.revokeObjectURL = (url: string) => {
    revoked.push(url);
  };
  return {
    created,
    revoked,
    restore() {
      URL.createObjectURL = originalCreate;
      URL.revokeObjectURL = originalRevoke;
    },
  };
}

export type { Call };
