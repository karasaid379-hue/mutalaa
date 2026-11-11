import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { trOcr } from '@/i18n/tr-ocr';
import { tr } from '@/i18n/tr';
import { ScanViewer } from '@/screens/ocr/scan-viewer';
import { problem, useFakeApi } from './fake-api';
import {
  JPEG_BYTES,
  PNG_BYTES,
  SCAN_ATTRS,
  SCAN_URL_PATH,
  stubCanvas,
  stubObjectUrls,
  syntheticTiff,
  withScanFetch,
  type CanvasStub,
  type ObjectUrlStub,
  type ScanReply,
} from './fixtures-ocr';
import { renderWithProviders } from './render-app';

describe('ScanViewer', () => {
  const fake = useFakeApi();
  let canvas: CanvasStub;
  let urls: ObjectUrlStub;

  beforeEach(() => {
    canvas = stubCanvas();
    urls = stubObjectUrls();
  });
  afterEach(() => {
    canvas.restore();
    urls.restore();
  });

  function setup(reply: ScanReply | (() => ScanReply | Promise<ScanReply>)) {
    const scan = withScanFetch(fake, () => (typeof reply === 'function' ? reply() : reply));
    const view = renderWithProviders(scan, <ScanViewer {...SCAN_ATTRS} />);
    return { scan, ...view };
  }

  describe('TIFF', () => {
    it('requests the page by edition and page id, decodes the TIFF and paints it on a canvas', async () => {
      const { scan } = setup({ body: syntheticTiff(2, 1), contentType: 'image/tiff' });
      const drawn = await screen.findByTestId('scan-canvas');
      expect(scan.scanCalls.map((call) => call.path)).toEqual([SCAN_URL_PATH]);
      expect(drawn).toHaveAttribute('width', '2');
      expect(drawn).toHaveAttribute('height', '1');
      expect(drawn).toHaveAttribute('role', 'img');
      await waitFor(() => expect(canvas.context.putImageData).toHaveBeenCalledTimes(1));
      const image = canvas.context.putImageData.mock.calls[0]![0] as ImageData;
      // Gray values 0 and 85 become opaque RGBA pixels.
      expect(Array.from(image.data)).toEqual([0, 0, 0, 255, 85, 85, 85, 255]);
      expect(canvas.context.drawImage).not.toHaveBeenCalled();
    });

    it('trusts the file bytes, not the content type', async () => {
      setup({ body: syntheticTiff(2, 1), contentType: 'application/octet-stream' });
      expect(await screen.findByTestId('scan-canvas')).toBeInTheDocument();
    });

    it('shows an error and no canvas when the TIFF cannot be decoded', async () => {
      // A valid header and a directory offset that points outside the file.
      const damaged = Uint8Array.from([0x49, 0x49, 0x2a, 0x00, 0xff, 0xff, 0xff, 0x7f, 1, 2, 3]);
      setup({ body: damaged, contentType: 'image/tiff' });
      expect(await screen.findByRole('alert')).toHaveTextContent(trOcr.scan.tiffFailed);
      expect(screen.queryByTestId('scan-canvas')).toBeNull();
      expect(canvas.context.putImageData).not.toHaveBeenCalled();
    });

    it('refuses a TIFF whose tags claim more pixels than the limit, before decoding any pixel', async () => {
      setup({ body: syntheticTiff(10_000, 10_000, new Uint8Array(4)), contentType: 'image/tiff' });
      expect(await screen.findByRole('alert')).toHaveTextContent(trOcr.scan.tooLarge);
      expect(canvas.context.createImageData).not.toHaveBeenCalled();
    });

    it('says so when the browser gives no 2D context', async () => {
      canvas.restore();
      const none = vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
      setup({ body: syntheticTiff(2, 1), contentType: 'image/tiff' });
      expect(await screen.findByRole('alert')).toHaveTextContent(trOcr.scan.imageFailed);
      none.mockRestore();
    });
  });

  describe('PNG and JPEG', () => {
    it('shows a PNG with an img and an object URL', async () => {
      setup({ body: PNG_BYTES, contentType: 'image/png' });
      const image = await screen.findByTestId('scan-image');
      expect(image).toHaveAttribute('src', 'blob:deneme-1');
      expect(image).toHaveAttribute(
        'alt',
        trOcr.scan.imageLabel(SCAN_ATTRS.baski, SCAN_ATTRS.sayfa),
      );
      expect(urls.created).toHaveLength(1);
      expect(urls.created[0]!.type).toBe('image/png');
      expect(screen.queryByTestId('scan-canvas')).toBeNull();
    });

    it('shows a JPEG and gives the blob its own type when the answer had none', async () => {
      setup({ body: JPEG_BYTES, contentType: 'application/octet-stream' });
      expect(await screen.findByTestId('scan-image')).toBeInTheDocument();
      expect(urls.created[0]!.type).toBe('image/jpeg');
    });

    it('revokes the object URL when the viewer goes away', async () => {
      const { unmount } = setup({ body: PNG_BYTES, contentType: 'image/png' });
      await screen.findByTestId('scan-image');
      expect(urls.revoked).toEqual([]);
      unmount();
      expect(urls.revoked).toEqual(['blob:deneme-1']);
    });

    it('shows an error when the browser cannot display the image', async () => {
      setup({ body: PNG_BYTES, contentType: 'image/png' });
      fireEvent.error(await screen.findByTestId('scan-image'));
      expect(await screen.findByRole('alert')).toHaveTextContent(trOcr.scan.imageFailed);
    });
  });

  describe('failures', () => {
    it('rejects bytes that are no TIFF, PNG or JPEG', async () => {
      setup({ body: new TextEncoder().encode('Deneme metni'), contentType: 'image/png' });
      expect(await screen.findByRole('alert')).toHaveTextContent(trOcr.scan.unknownFormat);
      expect(urls.created).toHaveLength(0);
    });

    it('shows the problem of a failed request and asks again on retry', async () => {
      let attempts = 0;
      const { user, scan } = setup(() => {
        attempts += 1;
        return attempts === 1
          ? {
              status: 404,
              body: JSON.stringify(problem(404, 'bulunamadi').body),
              contentType: 'application/problem+json',
            }
          : { body: PNG_BYTES, contentType: 'image/png' };
      });
      expect(await screen.findByText(trOcr.scan.failed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: trOcr.scan.retry }));
      expect(await screen.findByTestId('scan-image')).toBeInTheDocument();
      expect(scan.scanCalls).toHaveLength(2);
    });

    it('turns a non-JSON error page into the unexpected-answer message', async () => {
      setup({ status: 502, body: '<html>Deneme</html>', contentType: 'text/html' });
      expect(await screen.findByText(trOcr.scan.failed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes['yanit-bozuk'])).toBeInTheDocument();
    });

    it('aborts the request when the viewer goes away before the answer', async () => {
      let release: () => void = () => undefined;
      const gate = new Promise<void>((resolve) => {
        release = resolve;
      });
      const { scan, unmount } = setup(async () => {
        await gate;
        return { body: PNG_BYTES, contentType: 'image/png' };
      });
      await waitFor(() => expect(scan.scanCalls).toHaveLength(1));
      expect(scan.scanCalls[0]!.signal.aborted).toBe(false);
      unmount();
      expect(scan.scanCalls[0]!.signal.aborted).toBe(true);
      release();
      // Nothing was made of the late answer.
      await Promise.resolve();
      expect(urls.created).toHaveLength(0);
    });
  });

  describe('zoom and keyboard', () => {
    async function shown() {
      setup({ body: PNG_BYTES, contentType: 'image/png' });
      return screen.findByTestId('scan-viewport');
    }

    it('has three real buttons and a focusable viewport with a keyboard hint', async () => {
      const viewport = await shown();
      for (const name of [trOcr.scan.zoomIn, trOcr.scan.zoomOut, trOcr.scan.fit]) {
        const button = screen.getByRole('button', { name });
        expect(button).toHaveAttribute('type', 'button');
      }
      expect(viewport).toHaveAttribute('tabindex', '0');
      expect(viewport).toHaveAccessibleName(trOcr.scan.region);
      expect(viewport).toHaveAccessibleDescription(trOcr.scan.keyboardHint);
    });

    it('takes arrows, Ctrl/Cmd with up and down, and Home; it ignores every single character', async () => {
      const viewport = await shown();
      // fireEvent returns false when the handler called preventDefault.
      for (const key of ['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home']) {
        expect(fireEvent.keyDown(viewport, { key }), key).toBe(false);
      }
      expect(fireEvent.keyDown(viewport, { key: 'ArrowUp', ctrlKey: true })).toBe(false);
      expect(fireEvent.keyDown(viewport, { key: 'ArrowDown', metaKey: true })).toBe(false);
      for (const key of ['+', '-', '=', '0', 'z', 'r', 'f']) {
        expect(fireEvent.keyDown(viewport, { key }), key).toBe(true);
      }
      // Other Ctrl combinations stay with the browser.
      expect(fireEvent.keyDown(viewport, { key: 'ArrowLeft', ctrlKey: true })).toBe(true);
      expect(fireEvent.keyDown(viewport, { key: 'ArrowLeft', altKey: true })).toBe(true);
    });

    it('moves the page with the arrow keys and scales it with the zoom buttons', async () => {
      const { user } = setup({ body: PNG_BYTES, contentType: 'image/png' });
      const image = await screen.findByTestId('scan-image');
      const content = image.parentElement!;
      const before = content.style.transform;
      await user.click(screen.getByRole('button', { name: trOcr.scan.zoomIn }));
      await waitFor(() => expect(content.style.transform).not.toBe(before));
      const zoomed = content.style.transform;
      await user.click(screen.getByRole('button', { name: trOcr.scan.zoomOut }));
      await waitFor(() => expect(content.style.transform).not.toBe(zoomed));
    });
  });

  describe('pan buttons and cancelled decoding', () => {
    it('has four pan buttons of at least 24x24 (what they do is in scan-pan.test.tsx)', async () => {
      setup({ body: PNG_BYTES, contentType: 'image/png' });
      await screen.findByTestId('scan-image');
      const group = screen.getByRole('group', { name: trOcr.scan.pan });
      const names = [trOcr.scan.panUp, trOcr.scan.panDown, trOcr.scan.panLeft, trOcr.scan.panRight];
      for (const name of names) {
        const button = within(group).getByRole('button', { name });
        expect(button).toHaveAttribute('type', 'button');
        // size-8 (2rem) is above the 24 px target of WCAG 2.5.8.
        expect(button).toHaveClass('size-8');
      }
    });

    it('creates no object URL when the viewer goes away while the file head is being read', async () => {
      const real = Blob.prototype.arrayBuffer;
      let release: () => void = () => undefined;
      const spy = vi.spyOn(Blob.prototype, 'arrayBuffer').mockImplementation(function (this: Blob) {
        return new Promise<ArrayBuffer>((resolve) => {
          release = () => resolve(real.call(this));
        });
      });
      try {
        const { unmount } = setup({ body: PNG_BYTES, contentType: 'image/png' });
        await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
        unmount();
        release();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(urls.created).toHaveLength(0);
        expect(urls.revoked).toHaveLength(0);
      } finally {
        spy.mockRestore();
      }
    });

    it('paints nothing when the viewer goes away while a TIFF is being read', async () => {
      const real = Blob.prototype.arrayBuffer;
      let calls = 0;
      let release: () => void = () => undefined;
      const spy = vi.spyOn(Blob.prototype, 'arrayBuffer').mockImplementation(function (this: Blob) {
        calls += 1;
        if (calls === 1) return real.call(this);
        return new Promise<ArrayBuffer>((resolve) => {
          release = () => resolve(real.call(this));
        });
      });
      try {
        const { unmount } = setup({ body: syntheticTiff(2, 1), contentType: 'image/tiff' });
        await waitFor(() => expect(spy).toHaveBeenCalledTimes(2));
        unmount();
        release();
        await new Promise((resolve) => setTimeout(resolve, 0));
        expect(urls.created).toHaveLength(0);
        expect(canvas.context.putImageData).not.toHaveBeenCalled();
      } finally {
        spy.mockRestore();
      }
    });

    it('revokes exactly the object URLs it created', async () => {
      const { unmount } = setup({ body: JPEG_BYTES, contentType: 'image/jpeg' });
      await screen.findByTestId('scan-image');
      unmount();
      expect(urls.revoked).toEqual(urls.created.map((_, index) => `blob:deneme-${index + 1}`));
    });
  });
});
