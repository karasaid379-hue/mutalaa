import { useQuery } from '@tanstack/react-query';
import { useEffect, useId, useRef, useState, type KeyboardEvent } from 'react';
import {
  TransformComponent,
  TransformWrapper,
  type ReactZoomPanPinchContentRef,
} from 'react-zoom-pan-pinch';
import { useApi } from '@/app/api-context';
import { ProblemMessage } from '@/components/problem-message';
import { Button } from '@/components/ui/button';
import { trOcr } from '@/i18n/tr-ocr';
import {
  MAX_SCAN_BYTES,
  ScanError,
  decodeTiff,
  displaySize,
  paintTiff,
  sniffScanKind,
  type DecodedTiff,
  type ScanErrorCode,
} from './scan-image';

const SCAN_PATH = '/api/v1/scans/{baski}/{sayfa}' as const;

/** Pixels one arrow key press moves the page; one Ctrl/Cmd+arrow press changes the scale by `ZOOM_STEP`. */
const PAN_STEP = 60;
const ZOOM_STEP = 0.25;

/** How many bytes are enough to tell the file kind apart. */
const SNIFF_BYTES = 16;

type Shown =
  | { kind: 'tiff'; decoded: DecodedTiff }
  | { kind: 'image'; url: string }
  | { kind: 'error'; code: ScanErrorCode };

const errorMessages: Record<ScanErrorCode, string> = {
  'too-large': trOcr.scan.tooLarge,
  'tiff-failed': trOcr.scan.tiffFailed,
  'unknown-format': trOcr.scan.unknownFormat,
  'image-failed': trOcr.scan.imageFailed,
};

function mimeOf(kind: 'png' | 'jpeg'): string {
  return kind === 'png' ? 'image/png' : 'image/jpeg';
}

/**
 * Decodes the downloaded file. The result belongs to the blob it was made from: while another blob is being
 * decoded the hook returns null. A PNG or JPEG gets an object URL that is revoked when the blob changes or the
 * component goes away; a TIFF is decoded to RGBA (bounded by size limits).
 */
function useShown(blob: Blob | undefined): Shown | null {
  const [done, setDone] = useState<{ blob: Blob; shown: Shown } | null>(null);

  useEffect(() => {
    if (!blob) return;
    let cancelled = false;
    let url: string | null = null;

    async function run(source: Blob): Promise<Shown> {
      if (source.size > MAX_SCAN_BYTES) throw new ScanError('too-large');
      const head = new Uint8Array(await source.slice(0, SNIFF_BYTES).arrayBuffer());
      const kind = sniffScanKind(head);
      if (kind === null) throw new ScanError('unknown-format');
      if (kind === 'tiff') {
        const buffer = await source.arrayBuffer();
        if (cancelled) throw new ScanError('image-failed');
        return { kind: 'tiff', decoded: decodeTiff(buffer) };
      }
      const typed =
        source.type === mimeOf(kind) ? source : source.slice(0, source.size, mimeOf(kind));
      url = URL.createObjectURL(typed);
      return { kind: 'image', url };
    }

    run(blob).then(
      (shown) => {
        if (!cancelled) setDone({ blob, shown });
      },
      (thrown: unknown) => {
        if (cancelled) return;
        const code = thrown instanceof ScanError ? thrown.code : 'image-failed';
        setDone({ blob, shown: { kind: 'error', code } });
      },
    );

    return () => {
      cancelled = true;
      if (url !== null) URL.revokeObjectURL(url);
    };
  }, [blob]);

  return blob && done && done.blob === blob ? done.shown : null;
}

function TiffCanvas({
  decoded,
  label,
  onError,
}: {
  decoded: DecodedTiff;
  label: string;
  onError: (code: ScanErrorCode) => void;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const size = displaySize(decoded.width, decoded.height);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    try {
      paintTiff(canvas, decoded);
    } catch (thrown) {
      onError(thrown instanceof ScanError ? thrown.code : 'image-failed');
    }
  }, [decoded, onError]);

  return (
    <canvas
      ref={ref}
      role="img"
      aria-label={label}
      width={size.width}
      height={size.height}
      style={{ width: size.width, height: size.height }}
      data-testid="scan-canvas"
    />
  );
}

/** The note shown when a large TIFF was scaled down to the display limit. */
function downscaleNote(shown: Shown): string | null {
  if (shown.kind !== 'tiff') return null;
  const { width, height } = shown.decoded;
  const size = displaySize(width, height);
  return size.scale < 1 ? trOcr.scan.downscaled(width, height, size.width, size.height) : null;
}

export interface ScanViewerProps {
  /** Edition id (`^[a-z0-9-]{1,64}$`); the caller checks it, the API checks it again. */
  baski: string;
  /** Page id (`^c[0-9]{2}-s[0-9]{4}$`). */
  sayfa: string;
}

/**
 * The scanned page of an OCR record: fetched from `GET /scans/{baski}/{sayfa}` as a blob (the request is aborted
 * when the component goes away), shown as a canvas (TIFF) or an `img` (PNG, JPEG) and zoomed and panned with
 * react-zoom-pan-pinch. Controls are buttons; the focused viewport takes the arrow keys (pan), Ctrl or Cmd with
 * the up and down arrow (zoom) and Home (fit). There are no single character shortcuts and the library's own
 * keyboard handler (which has them) stays off.
 */
export function ScanViewer({ baski, sayfa }: ScanViewerProps) {
  const api = useApi();
  const hintId = useId();
  const controls = useRef<ReactZoomPanPinchContentRef>(null);
  const [canvasError, setCanvasError] = useState<ScanErrorCode | null>(null);
  const [imageFailed, setImageFailed] = useState(false);

  // The scan is private and `no-store`: it is not kept after the viewer is gone (gcTime 0).
  const query = useQuery({
    queryKey: ['scan', baski, sayfa],
    queryFn: async ({ signal }) => {
      const { data, error } = await api.client.GET(SCAN_PATH, {
        params: { path: { baski, sayfa } },
        parseAs: 'blob',
        signal,
      });
      if (error !== undefined) throw error;
      if (!(data instanceof Blob)) throw new ScanError('image-failed');
      return data;
    },
    gcTime: 0,
    staleTime: 0,
    retry: false,
  });

  const shown = useShown(query.data);

  function onKeyDown(event: KeyboardEvent<HTMLElement>) {
    const handle = controls.current;
    if (!handle || event.altKey) return;
    const zoom = event.ctrlKey || event.metaKey;
    let handled = true;
    if (zoom && event.key === 'ArrowUp') void handle.zoomIn(ZOOM_STEP, 100);
    else if (zoom && event.key === 'ArrowDown') void handle.zoomOut(ZOOM_STEP, 100);
    else if (zoom) handled = false;
    else if (event.key === 'ArrowLeft') void handle.panBy(PAN_STEP, 0, 0);
    else if (event.key === 'ArrowRight') void handle.panBy(-PAN_STEP, 0, 0);
    else if (event.key === 'ArrowUp') void handle.panBy(0, PAN_STEP, 0);
    else if (event.key === 'ArrowDown') void handle.panBy(0, -PAN_STEP, 0);
    else if (event.key === 'Home') void handle.fitToView();
    else handled = false;
    if (handled) event.preventDefault();
  }

  const failure: ScanErrorCode | null =
    canvasError ?? (imageFailed ? 'image-failed' : shown?.kind === 'error' ? shown.code : null);

  let body;
  if (query.isPending) {
    body = <p className="text-sm text-muted-foreground">{trOcr.scan.loading}</p>;
  } else if (query.isError) {
    body = (
      <div className="flex flex-col gap-2">
        <p className="text-sm font-medium">{trOcr.scan.failed}</p>
        <ProblemMessage error={query.error} />
        <div>
          <Button type="button" variant="outline" size="sm" onClick={() => void query.refetch()}>
            {trOcr.scan.retry}
          </Button>
        </div>
      </div>
    );
  } else if (failure !== null) {
    body = (
      <p role="alert" className="text-sm font-medium">
        {errorMessages[failure]}
      </p>
    );
  } else if (shown === null) {
    body = <p className="text-sm text-muted-foreground">{trOcr.scan.decoding}</p>;
  } else {
    const label = trOcr.scan.canvasLabel(baski, sayfa);
    const content =
      shown.kind === 'tiff' ? (
        <TiffCanvas decoded={shown.decoded} label={label} onError={setCanvasError} />
      ) : shown.kind === 'image' ? (
        <img
          src={shown.url}
          alt={label}
          onError={() => setImageFailed(true)}
          data-testid="scan-image"
          className="max-w-none"
        />
      ) : null;
    const note = downscaleNote(shown);
    body = (
      <TransformWrapper
        ref={controls}
        minScale={0.05}
        maxScale={12}
        fitOnInit="contain"
        doubleClick={{ disabled: true }}
        keyboard={{ disabled: true }}
      >
        <div className="flex flex-col gap-2">
          <div role="group" aria-label={trOcr.scan.controls} className="flex flex-wrap gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void controls.current?.zoomIn(ZOOM_STEP, 100)}
            >
              {trOcr.scan.zoomIn}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void controls.current?.zoomOut(ZOOM_STEP, 100)}
            >
              {trOcr.scan.zoomOut}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => void controls.current?.fitToView()}
            >
              {trOcr.scan.fit}
            </Button>
          </div>
          {note ? <p className="text-xs text-muted-foreground">{note}</p> : null}
          {/* The viewport is a keyboard target for panning and zooming, so it must be focusable. */}
          {/* eslint-disable jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions */}
          <div
            role="group"
            tabIndex={0}
            aria-label={trOcr.scan.region}
            aria-describedby={hintId}
            onKeyDown={onKeyDown}
            className="overflow-hidden rounded-lg border bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            data-testid="scan-viewport"
          >
            <TransformComponent wrapperStyle={{ width: '100%', height: '28rem' }}>
              {content}
            </TransformComponent>
          </div>
          {/* eslint-enable jsx-a11y/no-noninteractive-tabindex, jsx-a11y/no-noninteractive-element-interactions */}
          <p id={hintId} className="text-xs text-muted-foreground">
            {trOcr.scan.keyboardHint}
          </p>
        </div>
      </TransformWrapper>
    );
  }

  return (
    <section
      aria-label={trOcr.scan.heading}
      className="flex flex-col gap-2"
      data-testid="scan-viewer"
    >
      <h3 className="text-sm font-medium">{trOcr.scan.heading}</h3>
      {body}
    </section>
  );
}
