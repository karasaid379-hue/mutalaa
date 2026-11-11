// Pan buttons of the scan viewer (WCAG 2.5.7: moving the page needs no dragging). jsdom has no layout, so the
// library's bounds would swallow every move; the handle's `panBy` is replaced by a spy and the calls are checked.
import { fireEvent, screen } from '@testing-library/react';
import { forwardRef, useImperativeHandle, useRef } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { trOcr } from '@/i18n/tr-ocr';
import { ScanViewer } from '@/screens/ocr/scan-viewer';
import { useFakeApi } from './fake-api';
import {
  PNG_BYTES,
  SCAN_ATTRS,
  stubCanvas,
  stubObjectUrls,
  withScanFetch,
  type CanvasStub,
  type ObjectUrlStub,
} from './fixtures-ocr';
import { renderWithProviders } from './render-app';

const panBy = vi.hoisted(() => vi.fn());

vi.mock('react-zoom-pan-pinch', async (importOriginal) => {
  const real = await importOriginal<typeof import('react-zoom-pan-pinch')>();
  const Wrapper = forwardRef<unknown, Record<string, unknown>>(function Wrapper(props, ref) {
    const inner = useRef<Record<string, unknown> | null>(null);
    useImperativeHandle(
      ref,
      () =>
        new Proxy(
          {},
          { get: (_target, key) => (key === 'panBy' ? panBy : inner.current?.[key as string]) },
        ),
    );
    const Real = real.TransformWrapper as unknown as React.ComponentType<Record<string, unknown>>;
    return <Real {...props} ref={inner} />;
  });
  return { ...real, TransformWrapper: Wrapper };
});

describe('ScanViewer pan buttons', () => {
  const fake = useFakeApi();
  let canvas: CanvasStub;
  let urls: ObjectUrlStub;

  beforeEach(() => {
    panBy.mockClear();
    canvas = stubCanvas();
    urls = stubObjectUrls();
  });
  afterEach(() => {
    canvas.restore();
    urls.restore();
  });

  async function shown() {
    const scan = withScanFetch(fake, () => ({ body: PNG_BYTES, contentType: 'image/png' }));
    const view = renderWithProviders(scan, <ScanViewer {...SCAN_ATTRS} />);
    await screen.findByTestId('scan-image');
    return view;
  }

  it('each direction button pans by one step the same way its arrow key does', async () => {
    const { user } = await shown();
    const viewport = screen.getByTestId('scan-viewport');
    const pairs = [
      [trOcr.scan.panUp, 'ArrowUp'],
      [trOcr.scan.panDown, 'ArrowDown'],
      [trOcr.scan.panLeft, 'ArrowLeft'],
      [trOcr.scan.panRight, 'ArrowRight'],
    ] as const;
    for (const [name, key] of pairs) {
      panBy.mockClear();
      await user.click(screen.getByRole('button', { name }));
      expect(panBy).toHaveBeenCalledTimes(1);
      const byButton = panBy.mock.calls[0];
      panBy.mockClear();
      fireEvent.keyDown(viewport, { key });
      expect(panBy).toHaveBeenCalledTimes(1);
      expect(panBy.mock.calls[0], name).toEqual(byButton);
    }
    // Up and down move the page along y, left and right along x.
    panBy.mockClear();
    await user.click(screen.getByRole('button', { name: trOcr.scan.panUp }));
    expect(panBy).toHaveBeenCalledWith(0, 60, 0);
    await user.click(screen.getByRole('button', { name: trOcr.scan.panRight }));
    expect(panBy).toHaveBeenLastCalledWith(-60, 0, 0);
  });
});
