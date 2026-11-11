import { afterEach, describe, expect, it, vi } from 'vitest';
import { MAX_SHOWN_AYAHS, ayahAnchors } from '@/screens/ocr/ayah-anchors';
import {
  MAX_DECODE_PIXELS,
  MAX_DISPLAY_PIXELS,
  ScanError,
  decodeTiff,
  displaySize,
  paintTiff,
  sniffScanKind,
} from '@/screens/ocr/scan-image';
import { readScanRef } from '@/screens/ocr/scan-ref';
import { JPEG_BYTES, PNG_BYTES, stubCanvas, syntheticTiff, type CanvasStub } from './fixtures-ocr';

const asBuffer = (bytes: Uint8Array) =>
  bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer;

function codeOf(run: () => unknown): string | undefined {
  try {
    run();
  } catch (thrown) {
    return thrown instanceof ScanError ? thrown.code : `other:${String(thrown)}`;
  }
  return undefined;
}

describe('readScanRef', () => {
  it('reads baski and sayfa from the unit attrs', () => {
    expect(readScanRef({ baski: 'deneme-baski', sayfa: 'c01-s0001' })).toEqual({
      baski: 'deneme-baski',
      sayfa: 'c01-s0001',
    });
  });

  it.each([
    ['no attrs', null],
    ['an empty object', {}],
    ['an array', ['deneme-baski', 'c01-s0001']],
    ['baski only', { baski: 'deneme-baski' }],
    ['sayfa only', { sayfa: 'c01-s0001' }],
    ['numbers', { baski: 1, sayfa: 2 }],
    ['capital letters', { baski: 'Deneme', sayfa: 'c01-s0001' }],
    ['a path in baski', { baski: '../deneme', sayfa: 'c01-s0001' }],
    ['a baski over 64 characters', { baski: 'a'.repeat(65), sayfa: 'c01-s0001' }],
    ['a page without the volume', { baski: 'deneme', sayfa: 's0001' }],
    ['a trailing newline', { baski: 'deneme', sayfa: 'c01-s0001\n' }],
    ['non-ASCII digits', { baski: 'deneme', sayfa: 'c١٢-s0001' }],
  ])('gives null for %s', (_name, attrs) => {
    expect(readScanRef(attrs)).toBeNull();
  });
});

describe('ayahAnchors', () => {
  it('gives the ayah of a meal anchor', () => {
    expect(ayahAnchors('meal:deneme:1:2')).toEqual({ shown: ['q:1:2'], hidden: 0, isAyah: false });
  });

  it('recognizes an ayah unit', () => {
    expect(ayahAnchors('q:1:2')).toEqual({ shown: ['q:1:2'], hidden: 0, isAyah: true });
  });

  it('cuts a long range and counts what is left out', () => {
    const result = ayahAnchors('tf:deneme:1-2-6:p1');
    expect(result.shown).toEqual(['q:1:2', 'q:1:3', 'q:1:4'].slice(0, MAX_SHOWN_AYAHS));
    expect(result.hidden).toBe(2);
  });

  it.each(['rn:deneme:p1', 'h:deneme:1', 'Q:1:2', '', 'q:1:2 '])(
    'gives no ayah for %j',
    (anchor) => {
      expect(ayahAnchors(anchor).shown).toEqual([]);
    },
  );
});

describe('sniffScanKind', () => {
  it('reads the kind from the magic bytes', () => {
    expect(sniffScanKind(syntheticTiff())).toBe('tiff');
    expect(sniffScanKind(Uint8Array.from([0x4d, 0x4d, 0x00, 0x2a, 0, 0, 0, 8]))).toBe('tiff');
    expect(sniffScanKind(PNG_BYTES)).toBe('png');
    expect(sniffScanKind(JPEG_BYTES)).toBe('jpeg');
  });

  it('gives null for anything else, also for short input', () => {
    expect(sniffScanKind(new Uint8Array())).toBeNull();
    expect(sniffScanKind(Uint8Array.from([0x49, 0x49, 0x2a]))).toBeNull();
    expect(sniffScanKind(new TextEncoder().encode('<html>'))).toBeNull();
    // BigTIFF (version 43) is not supported by the decoder.
    expect(sniffScanKind(Uint8Array.from([0x49, 0x49, 0x2b, 0x00]))).toBeNull();
  });
});

describe('decodeTiff', () => {
  it('decodes grayscale to opaque RGBA', () => {
    const decoded = decodeTiff(
      asBuffer(syntheticTiff(3, 2, Uint8Array.from([0, 10, 20, 30, 40, 255]))),
    );
    expect(decoded.width).toBe(3);
    expect(decoded.height).toBe(2);
    expect(Array.from(decoded.rgba.slice(0, 8))).toEqual([0, 0, 0, 255, 10, 10, 10, 255]);
    expect(decoded.rgba).toHaveLength(3 * 2 * 4);
    expect(Array.from(decoded.rgba.slice(-4))).toEqual([255, 255, 255, 255]);
  });

  it.each([
    ['an empty file', new Uint8Array()],
    ['text', new TextEncoder().encode('Deneme paragrafı 1')],
    [
      'a header with a directory outside the file',
      Uint8Array.from([0x49, 0x49, 0x2a, 0, 0xff, 0xff, 0xff, 0x7f]),
    ],
  ])('gives tiff-failed for %s', (_name, bytes) => {
    expect(codeOf(() => decodeTiff(asBuffer(bytes)))).toBe('tiff-failed');
  });

  it('still gives a full-size image when the strip is shorter than the tags claim (the decoder pads it)', () => {
    const decoded = decodeTiff(asBuffer(syntheticTiff(4, 4, new Uint8Array(2))));
    expect(decoded.rgba).toHaveLength(4 * 4 * 4);
  });

  it('refuses more pixels than the limit from the tags alone', () => {
    const side = Math.ceil(Math.sqrt(MAX_DECODE_PIXELS)) + 1;
    expect(codeOf(() => decodeTiff(asBuffer(syntheticTiff(side, side, new Uint8Array(1)))))).toBe(
      'too-large',
    );
  });
});

describe('displaySize', () => {
  it('keeps the size up to the display limit', () => {
    expect(displaySize(2480, 3508)).toEqual({ width: 2480, height: 3508, scale: 1 });
    expect(displaySize(6000, 6000)).toEqual({ width: 6000, height: 6000, scale: 1 });
  });

  it('scales down evenly above the limit and stays within it', () => {
    const size = displaySize(9000, 6000);
    expect(size.scale).toBeLessThan(1);
    expect(size.width * size.height).toBeLessThanOrEqual(MAX_DISPLAY_PIXELS);
    expect(size.width / size.height).toBeCloseTo(1.5, 2);
  });

  it('never gives a zero side', () => {
    const size = displaySize(1_000_000_000, 1);
    expect(size.width).toBeGreaterThanOrEqual(1);
    expect(size.height).toBeGreaterThanOrEqual(1);
  });
});

describe('paintTiff', () => {
  let stub: CanvasStub | null = null;
  afterEach(() => {
    stub?.restore();
    stub = null;
  });

  it('paints straight on the shown canvas when the image fits', () => {
    stub = stubCanvas();
    const canvas = document.createElement('canvas');
    const size = paintTiff(canvas, {
      width: 2,
      height: 1,
      rgba: Uint8Array.from([1, 2, 3, 255, 4, 5, 6, 255]),
    });
    expect(size).toEqual({ width: 2, height: 1, scale: 1 });
    expect(canvas.width).toBe(2);
    expect(canvas.height).toBe(1);
    expect(stub.context.putImageData).toHaveBeenCalledTimes(1);
    expect(stub.context.drawImage).not.toHaveBeenCalled();
  });

  it('paints a large image off screen, draws it scaled down and releases the off-screen canvas', () => {
    stub = stubCanvas({ lightweight: true });
    const canvas = document.createElement('canvas');
    const decoded = { width: 9000, height: 6000, rgba: new Uint8Array(4) };
    const size = paintTiff(canvas, decoded);
    expect(size.scale).toBeLessThan(1);
    expect(canvas.width).toBe(size.width);
    expect(canvas.height).toBe(size.height);
    expect(stub.context.putImageData).toHaveBeenCalledTimes(1);
    expect(stub.context.drawImage).toHaveBeenCalledTimes(1);
    const [source, x, y, width, height] = stub.context.drawImage.mock.calls[0] as [
      HTMLCanvasElement,
      number,
      number,
      number,
      number,
    ];
    expect(source).not.toBe(canvas);
    expect([x, y, width, height]).toEqual([0, 0, size.width, size.height]);
    // The big off-screen canvas was shrunk to nothing after the draw.
    expect(source.width).toBe(0);
    expect(source.height).toBe(0);
  });

  it('throws image-failed without a 2D context', () => {
    const canvas = document.createElement('canvas');
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    expect(codeOf(() => paintTiff(canvas, { width: 1, height: 1, rgba: new Uint8Array(4) }))).toBe(
      'image-failed',
    );
  });
});
