import * as UTIF from 'utif2';

// Decoding and painting of a scanned page. The API gives the raw file (`image/tiff`, `image/png` or
// `image/jpeg`) and does not convert it (K-48 madde 8); browsers show PNG and JPEG themselves, TIFF is decoded
// here with utif2 and painted on a canvas. Everything is bounded: a file or a decoded size above the limits is
// refused with an error code instead of exhausting memory.

/** Largest file accepted (bytes). */
export const MAX_SCAN_BYTES = 256 * 1024 * 1024;
/** Largest TIFF decoded (pixels); RGBA needs four bytes per pixel. */
export const MAX_DECODE_PIXELS = 50_000_000;
/** Pixels of the canvas that is shown; a larger TIFF is scaled down to this. */
export const MAX_DISPLAY_PIXELS = 36_000_000;

export type ScanKind = 'tiff' | 'png' | 'jpeg';

export type ScanErrorCode = 'too-large' | 'tiff-failed' | 'unknown-format' | 'image-failed';

export class ScanError extends Error {
  readonly code: ScanErrorCode;

  constructor(code: ScanErrorCode) {
    super(code);
    this.name = 'ScanError';
    this.code = code;
  }
}

/** File kind from the magic bytes (the content type of an answer is not trusted). Null for anything else. */
export function sniffScanKind(bytes: Uint8Array): ScanKind | null {
  const at = (index: number) => bytes[index];
  if (bytes.length >= 4) {
    const littleEndian = at(0) === 0x49 && at(1) === 0x49 && at(2) === 0x2a && at(3) === 0x00;
    const bigEndian = at(0) === 0x4d && at(1) === 0x4d && at(2) === 0x00 && at(3) === 0x2a;
    if (littleEndian || bigEndian) return 'tiff';
    if (at(0) === 0x89 && at(1) === 0x50 && at(2) === 0x4e && at(3) === 0x47) return 'png';
  }
  if (bytes.length >= 3 && at(0) === 0xff && at(1) === 0xd8 && at(2) === 0xff) return 'jpeg';
  return null;
}

export interface DecodedTiff {
  width: number;
  height: number;
  /** RGBA, 8 bits per channel, `width * height * 4` bytes. */
  rgba: Uint8Array;
}

function tagNumber(ifd: UTIF.IFD, tag: string): number {
  const value = ifd[tag];
  if (!Array.isArray(value)) return 0;
  const first: unknown = value[0];
  return typeof first === 'number' && Number.isFinite(first) ? first : 0;
}

/**
 * Decodes the largest image of a TIFF (thumbnails and sub-images are skipped). The size is read from the tags
 * before any pixel is decoded, so an oversized file is refused cheaply. Any failure of the decoder (it throws on
 * damaged files and on compressions it does not know) becomes `tiff-failed`.
 */
export function decodeTiff(buffer: ArrayBuffer): DecodedTiff {
  let ifds: UTIF.IFD[];
  try {
    ifds = UTIF.decode(buffer);
  } catch {
    throw new ScanError('tiff-failed');
  }
  let best: { ifd: UTIF.IFD; area: number } | null = null;
  for (const ifd of ifds) {
    const width = tagNumber(ifd, 't256');
    const height = tagNumber(ifd, 't257');
    if (width < 1 || height < 1) continue;
    const area = width * height;
    if (best === null || area > best.area) best = { ifd, area };
  }
  if (best === null) throw new ScanError('tiff-failed');
  if (best.area > MAX_DECODE_PIXELS) throw new ScanError('too-large');
  try {
    UTIF.decodeImage(buffer, best.ifd);
    const rgba = UTIF.toRGBA8(best.ifd);
    const { width, height } = best.ifd;
    if (!(width >= 1 && height >= 1) || rgba.length !== width * height * 4) {
      throw new ScanError('tiff-failed');
    }
    return { width, height, rgba };
  } catch (thrown) {
    throw thrown instanceof ScanError ? thrown : new ScanError('tiff-failed');
  }
}

export interface DisplaySize {
  width: number;
  height: number;
  /** 1 when the image is shown at its own size; below 1 when it was scaled down. */
  scale: number;
}

/** Size of the shown canvas: the image's own size, or scaled down evenly to `MAX_DISPLAY_PIXELS`. */
export function displaySize(width: number, height: number): DisplaySize {
  const pixels = width * height;
  if (pixels <= MAX_DISPLAY_PIXELS) return { width, height, scale: 1 };
  const scale = Math.sqrt(MAX_DISPLAY_PIXELS / pixels);
  return {
    width: Math.max(1, Math.floor(width * scale)),
    height: Math.max(1, Math.floor(height * scale)),
    scale,
  };
}

/**
 * Paints a decoded TIFF on `canvas` (the canvas size becomes the display size). A TIFF above the display limit
 * is first painted on an off-screen canvas and then drawn scaled down; the off-screen canvas is released at once.
 * Throws `image-failed` when the browser gives no 2D context.
 */
export function paintTiff(canvas: HTMLCanvasElement, decoded: DecodedTiff): DisplaySize {
  const size = displaySize(decoded.width, decoded.height);
  const scaled = size.scale < 1;
  const source = scaled ? canvas.ownerDocument.createElement('canvas') : canvas;
  source.width = decoded.width;
  source.height = decoded.height;
  const sourceContext = source.getContext('2d');
  if (!sourceContext) throw new ScanError('image-failed');
  const image = sourceContext.createImageData(decoded.width, decoded.height);
  image.data.set(decoded.rgba);
  sourceContext.putImageData(image, 0, 0);
  if (scaled) {
    canvas.width = size.width;
    canvas.height = size.height;
    const context = canvas.getContext('2d');
    if (!context) throw new ScanError('image-failed');
    context.imageSmoothingQuality = 'high';
    context.drawImage(source, 0, 0, size.width, size.height);
    source.width = 0;
    source.height = 0;
  }
  return size;
}
