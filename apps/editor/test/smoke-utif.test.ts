// A15.2 smoke test: utif2 (CJS, module.exports = UTIF) imports under Vitest and decodes a TIFF built here.
// The TIFF is a 2x1, 8-bit, uncompressed, little-endian grayscale file written byte by byte (no encoder
// from the library, no file on disk). Pixel values 0 and 255.
import * as UTIF from 'utif2';
import { describe, expect, it } from 'vitest';

function syntheticTiff(): Uint8Array {
  const entries: [tag: number, type: number, count: number, value: number][] = [
    [256, 3, 1, 2], // ImageWidth
    [257, 3, 1, 1], // ImageLength
    [258, 3, 1, 8], // BitsPerSample
    [259, 3, 1, 1], // Compression: none
    [262, 3, 1, 1], // PhotometricInterpretation: BlackIsZero
    [273, 4, 1, 0], // StripOffsets (patched below)
    [277, 3, 1, 1], // SamplesPerPixel
    [278, 3, 1, 1], // RowsPerStrip
    [279, 4, 1, 2], // StripByteCounts
  ];
  const ifdSize = 2 + entries.length * 12 + 4;
  const dataOffset = 8 + ifdSize;
  const bytes = new Uint8Array(dataOffset + 2);
  const view = new DataView(bytes.buffer);
  bytes.set([0x49, 0x49], 0); // "II"
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
  view.setUint32(10 + entries.length * 12, 0, true); // no next IFD
  bytes[dataOffset] = 0;
  bytes[dataOffset + 1] = 255;
  return bytes;
}

describe('utif2 smoke', () => {
  it('decodes the synthetic TIFF to RGBA', () => {
    const tiff = syntheticTiff();
    const ifds = UTIF.decode(tiff.buffer as ArrayBuffer);
    expect(ifds).toHaveLength(1);
    const ifd = ifds[0]!;
    UTIF.decodeImage(tiff.buffer as ArrayBuffer, ifd);
    expect(ifd.width).toBe(2);
    expect(ifd.height).toBe(1);
    const rgba = UTIF.toRGBA8(ifd);
    expect(Array.from(rgba)).toEqual([0, 0, 0, 255, 255, 255, 255, 255]);
  });
});
