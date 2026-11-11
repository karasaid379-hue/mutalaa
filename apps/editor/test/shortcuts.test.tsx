// Keyboard rules (A15.3, WCAG 2.1.4): there is no single-character shortcut anywhere, and Ctrl+Enter or
// Meta+Enter sends a form from its text field. Plain Enter and Shift+Enter only break the line.
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { tr } from '@/i18n/tr';
import { trc } from '@/i18n/tr-catalog';
import { BulkDecision } from '@/review/bulk-decision';
import { DecisionForm } from '@/review/decision-form';
import { ok, useFakeApi } from './fake-api';
import { page, reviewDetail, reviewItem, session, signedIn, unitDetail } from './fixtures';
import {
  DECIDED,
  ocrDetail,
  ocrHandlers,
  ocrItem,
  stubCanvas,
  stubObjectUrls,
  syntheticTiff,
  withScanFetch,
  type CanvasStub,
  type ObjectUrlStub,
} from './fixtures-ocr';
import { renderApp, renderWithProviders } from './render-app';

// --- Ctrl/Meta+Enter sends ---

const MODIFIERS = [
  ['Ctrl', { ctrlKey: true }],
  ['Meta', { metaKey: true }],
] as const;

describe('Ctrl+Enter and Meta+Enter (decision form)', () => {
  const fake = useFakeApi();

  function setup() {
    fake.get('/api/v1/auth/me', ok(session()));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
    fake.post('/api/v1/reviews/{id}/decision', ok(DECIDED));
    return renderWithProviders(fake, <DecisionForm review={reviewDetail()} onDecided={vi.fn()} />);
  }
  const calls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  it.each(MODIFIERS)('%s+Enter sends from the reason field', async (_name, modifier) => {
    const { user } = setup();
    await user.click(screen.getByRole('radio', { name: tr.review.reject }));
    const reason = screen.getByLabelText(tr.review.reason);
    await user.type(reason, 'Deneme gerekçe');
    expect(fireEvent.keyDown(reason, { key: 'Enter', ...modifier })).toBe(false);
    await waitFor(() => expect(calls()).toHaveLength(1));
  });

  it('plain Enter and Shift+Enter do not send', async () => {
    const { user } = setup();
    await user.click(screen.getByRole('radio', { name: tr.review.reject }));
    const reason = screen.getByLabelText(tr.review.reason);
    await user.type(reason, 'Deneme gerekçe');
    expect(fireEvent.keyDown(reason, { key: 'Enter' })).toBe(true);
    expect(fireEvent.keyDown(reason, { key: 'Enter', shiftKey: true })).toBe(true);
    expect(fireEvent.keyDown(reason, { key: 'Enter', altKey: true })).toBe(true);
    expect(calls()).toHaveLength(0);
  });
});

describe('Ctrl+Enter and Meta+Enter (bulk decision)', () => {
  const fake = useFakeApi();

  it.each(MODIFIERS)('%s+Enter sends from the reason field', async (_name, modifier) => {
    fake.post('/api/v1/reviews/decisions', (call) => {
      const body = call.json as { kararlar: { id: number }[] };
      return ok({
        sonuclar: body.kararlar.map((entry) => ({
          id: entry.id,
          durum: 'onaylandi',
          eylem: 'onayla',
          xmin: 2000 + entry.id,
        })),
      });
    });
    const items = [1, 2, 3].map((id) =>
      reviewItem({ id, hedef_tablo: 'xref', alan: 'status', hedef_anahtar: `kayit-${id}` }),
    );
    renderWithProviders(
      fake,
      <BulkDecision items={items} sampling="none" onDone={vi.fn()} renderSample={() => null} />,
    );
    const reason = screen.getByLabelText(tr.bulk.reason);
    fireEvent.change(reason, { target: { value: 'Toplu deneme gerekçe' } });
    expect(fireEvent.keyDown(reason, { key: 'Enter', ...modifier })).toBe(false);
    await waitFor(() => expect(fake.callsTo('post', '/api/v1/reviews/decisions')).toHaveLength(1));
  });
});

describe('Ctrl+Enter and Meta+Enter (unit correction)', () => {
  const fake = useFakeApi();

  it.each(MODIFIERS)('%s+Enter sends from the reason field', async (_name, modifier) => {
    signedIn(fake);
    fake.get('/api/v1/units/{anchor}', ok(unitDetail({ duzeltilebilir: true })));
    fake.post('/api/v1/units/{anchor}/corrections', ok({ id: 5, durum: 'acik' }, 201));
    const { user } = renderApp(fake, '/birimler?birim=rn%3Adeneme%3Ap1');
    await user.click(await screen.findByRole('button', { name: trc.units.correct }));
    fireEvent.change(screen.getByRole('textbox', { name: trc.units.correctionText }), {
      target: { value: 'Deneme paragrafı 1 b' },
    });
    const reason = screen.getByRole('textbox', { name: trc.units.correctionReason });
    fireEvent.change(reason, { target: { value: 'Deneme gerekçe' } });
    expect(fireEvent.keyDown(reason, { key: 'Enter' })).toBe(true);
    expect(fake.callsTo('post', '/api/v1/units/{anchor}/corrections')).toHaveLength(0);
    expect(fireEvent.keyDown(reason, { key: 'Enter', ...modifier })).toBe(false);
    await waitFor(() =>
      expect(fake.callsTo('post', '/api/v1/units/{anchor}/corrections')).toHaveLength(1),
    );
  });
});

// --- the running panel: typing characters outside a text field does nothing ---

const PRINTABLE = [
  ...'abcdefghijklmnopqrstuvwxyz',
  ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
  ...'0123456789',
  ...'?/.,;:+-=[]{}\\|!@#$%^&*()_~`\'"<>',
  // Turkish letters: the dotted and dotless I are the usual trap.
  'İ',
  'ı',
  'ş',
  'ğ',
];

describe('no single-character shortcut (the running panel)', () => {
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

  it('ignores every printable character on the page, the navigation, the lists and the heading', async () => {
    ocrHandlers(fake, { detail: (id) => ocrDetail(id) });
    signedIn(fake);
    fake.get('/api/v1/reviews', ok(page([ocrItem(1), ocrItem(2)])));
    const scan = withScanFetch(fake, () => ({
      body: syntheticTiff(2, 1),
      contentType: 'image/tiff',
    }));
    const { router } = renderApp(scan, '/kuyruk/ocr?kayit=1');
    await screen.findByTestId('scan-canvas');
    await screen.findByRole('radio', { name: tr.review.approve });
    await waitFor(() =>
      expect(fake.callsTo('get', '/api/v1/reviews/stats').length).toBeGreaterThan(0),
    );

    const before = fake.calls.length;
    const location = `${router.state.location.pathname}${router.state.location.search}`;
    const targets: HTMLElement[] = [
      document.body,
      screen.getByRole('navigation', { name: tr.nav.label }),
      screen.getByRole('region', { name: tr.queue.listLabel }),
      screen.getByRole('region', { name: tr.queue.detailLabel }),
      screen.getByRole('heading', { level: 1 }),
    ];
    const focused = document.activeElement;
    for (const target of targets) {
      for (const key of PRINTABLE) {
        // `true` means nobody called preventDefault: no handler took the key.
        expect(fireEvent.keyDown(target, { key }), `${key} on ${target.tagName}`).toBe(true);
        fireEvent.keyUp(target, { key });
      }
    }
    expect(`${router.state.location.pathname}${router.state.location.search}`).toBe(location);
    expect(document.activeElement).toBe(focused);
    expect(fake.calls.length).toBe(before);
    expect(fake.callsTo('post', '/api/v1/reviews/{id}/decision')).toHaveLength(0);
  });
});
