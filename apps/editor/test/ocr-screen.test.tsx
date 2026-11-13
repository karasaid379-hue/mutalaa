import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trOcr } from '@/i18n/tr-ocr';
import { Component as QueueOcr } from '@/screens/queue-ocr';
import { ok, problem, useFakeApi } from './fake-api';
import { OTHER_EMAIL, page, session, signedIn, stats } from './fixtures';
import {
  ARABIC_AYAH,
  AYAH_ANCHOR,
  DECIDED,
  MEAL_ANCHOR,
  PNG_BYTES,
  SCAN_URL_PATH,
  ocrDetail,
  ocrHandlers,
  ocrItem,
  ocrUnit,
  stubCanvas,
  stubObjectUrls,
  syntheticTiff,
  withScanFetch,
  type CanvasStub,
  type ObjectUrlStub,
} from './fixtures-ocr';
import { renderApp, renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type Unit = components['schemas']['UnitDetail'];

describe('kuyruk/ocr', () => {
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

  const scanBytes = () => ({ body: syntheticTiff(2, 1), contentType: 'image/tiff' });

  interface SetupOptions {
    items?: Item[];
    unit?: (anchor: string) => Unit;
    route?: string;
    email?: string;
    scan?: () => { status?: number; body?: Uint8Array | string; contentType?: string };
  }

  function setup(options: SetupOptions = {}) {
    const items = options.items ?? [ocrItem(1), ocrItem(2)];
    ocrHandlers(fake, {
      ...(options.unit ? { unit: options.unit } : {}),
      detail: (id) => ocrDetail(id, items.find((item) => item.id === id) ?? {}),
    });
    fake.get('/api/v1/reviews', ok(page(items)));
    fake.get('/api/v1/auth/me', ok(session(['editor'], options.email)));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({ ...DECIDED, id: Number(call.params.id) }),
    );
    const scan = withScanFetch(fake, options.scan ?? scanBytes);
    const view = renderInRouter(scan, <QueueOcr />, options.route ?? '/?kayit=1');
    return { scan, ...view };
  }

  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  describe('list', () => {
    it('asks for the open unit texts without a cursor', async () => {
      setup({ route: '/' });
      await screen.findAllByRole('link');
      const first = listCalls()[0]!;
      expect(first.search.has('cursor')).toBe(false);
      expect(first.search.get('hedef_tablo')).toBe('unit');
      expect(first.search.get('alan')).toBe('metin');
      expect(first.search.get('durum')).toBe('acik');
      expect(first.search.get('limit')).toBe('50');
      expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent(tr.nav.queueOcr);
    });

    it('shows the empty state', async () => {
      setup({ items: [], route: '/' });
      expect(await screen.findByTestId('queue-empty')).toHaveTextContent(tr.queue.empty);
    });

    it('shows the problem when the list fails', async () => {
      ocrHandlers(fake);
      fake.get('/api/v1/auth/me', ok(session()));
      fake.get('/api/v1/reviews', problem(500, 'sunucu-hatasi'));
      renderInRouter(fake, <QueueOcr />, '/');
      expect(await screen.findByText(tr.queue.loadFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    });

    it('shows the unverified badge only from the API field', async () => {
      setup({
        items: [ocrItem(1, { dogrulanmamis: true, yz_modeli: 'deneme-model' }), ocrItem(2)],
        route: '/',
      });
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      await within(list).findAllByRole('listitem');
      expect(within(list).getAllByText(tr.badge.unverified)).toHaveLength(1);
    });
  });

  describe('detail', () => {
    it('shows the Tanzil ayah as stored and the meal text', async () => {
      setup();
      const ayah = await screen.findByText(ARABIC_AYAH);
      expect(ayah).toHaveAttribute('lang', 'ar');
      expect(ayah).toHaveAttribute('dir', 'rtl');
      expect(ayah.textContent).toBe(ARABIC_AYAH);
      const meal = await screen.findByTestId('ocr-unit-text');
      expect(within(meal).getByRole('heading', { name: trOcr.text.meal })).toBeInTheDocument();
      expect(within(meal).getByText('Deneme meal metni eski')).toBeInTheDocument();
      // The ayah was asked for by its own anchor, derived with @mutalaa/anchors from the meal anchor.
      const units = fake.callsTo('get', '/api/v1/units/{anchor}').map((call) => call.params.anchor);
      expect(units).toContain(AYAH_ANCHOR);
      expect(units).toContain(MEAL_ANCHOR.replace(':1:2', ':1:2'));
    });

    it('shows the word level difference from the previous to the proposed text', async () => {
      setup();
      const diff = await screen.findByTestId('text-diff');
      expect(diff.querySelector('del')).toHaveTextContent('eski');
      expect(diff.querySelector('ins')).toHaveTextContent('yeni');
    });

    it('shows only the proposal when the previous text is not recorded, and says so when there is none', async () => {
      setup({ items: [ocrItem(1, { onceki: null })] });
      expect(await screen.findByText(trOcr.diff.proposedOnly)).toBeInTheDocument();
      expect(screen.queryByTestId('text-diff')).toBeNull();
    });

    it('says there is no proposal when onerilen cannot be read', async () => {
      ocrHandlers(fake, { detail: (id) => ocrDetail(id, { onerilen: 'bozuk' }) });
      fake.get('/api/v1/reviews', ok(page([ocrItem(1)])));
      fake.get('/api/v1/auth/me', ok(session()));
      renderInRouter(withScanFetch(fake, scanBytes), <QueueOcr />, '/?kayit=1');
      expect(await screen.findByText(trOcr.diff.noProposal)).toBeInTheDocument();
    });

    it('shows the edit of the first approval as a second difference', async () => {
      ocrHandlers(fake, {
        detail: (id) =>
          ocrDetail(id, {
            duzenlenen: { metin: 'Deneme meal metni yeni düzeltme', content_hash: 'hash-2' },
          }),
      });
      fake.get('/api/v1/reviews', ok(page([ocrItem(1)])));
      fake.get('/api/v1/auth/me', ok(session()));
      renderInRouter(withScanFetch(fake, scanBytes), <QueueOcr />, '/?kayit=1');
      expect(await screen.findByText(trOcr.diff.editedHeading)).toBeInTheDocument();
      expect(screen.getAllByTestId('text-diff')).toHaveLength(2);
    });

    it('shows the problem and asks for no page image when the unit cannot be read', async () => {
      ocrHandlers(fake);
      fake.get('/api/v1/units/{anchor}', (call) =>
        call.params.anchor === MEAL_ANCHOR || call.params.anchor!.startsWith('meal:')
          ? problem(500, 'sunucu-hatasi')
          : ok(ocrUnit(call.params.anchor!)),
      );
      fake.get('/api/v1/reviews', ok(page([ocrItem(1)])));
      fake.get('/api/v1/auth/me', ok(session()));
      const scan = withScanFetch(fake, scanBytes);
      renderInRouter(scan, <QueueOcr />, '/?kayit=1');
      expect(await screen.findByText(trOcr.unitFailed)).toBeInTheDocument();
      expect(scan.scanCalls).toHaveLength(0);
      // The edit field stays closed without unit facts.
      fireEvent.click(await screen.findByRole('radio', { name: tr.review.approve }));
      expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
    });
  });

  describe('page image', () => {
    it('asks for the scan by the baski and sayfa of the unit attrs and shows it', async () => {
      const { scan } = setup();
      expect(await screen.findByTestId('scan-canvas')).toBeInTheDocument();
      expect(scan.scanCalls.map((call) => call.path)).toEqual([SCAN_URL_PATH]);
      expect(screen.queryByTestId('scan-not-mapped')).toBeNull();
    });

    it('shows a PNG scan with an img', async () => {
      setup({ scan: () => ({ body: PNG_BYTES, contentType: 'image/png' }) });
      expect(await screen.findByTestId('scan-image')).toBeInTheDocument();
    });

    it.each([
      ['no attrs', {}],
      ['baski only', { baski: 'deneme-baski' }],
      ['an invalid page id', { baski: 'deneme-baski', sayfa: 'sayfa-1' }],
      ['an invalid edition id', { baski: '../deneme', sayfa: 'c01-s0001' }],
      ['other field names', { cilt: 1, sayfa_no: 3 }],
    ])('says the mapping is not defined yet and sends no request for %s', async (_name, attrs) => {
      const { scan } = setup({ unit: (anchor) => ocrUnit(anchor, { attrs }) });
      const notice = await screen.findByTestId('scan-not-mapped');
      expect(notice).toHaveTextContent(trOcr.scan.notMapped);
      // The rest of the card is there.
      expect(await screen.findByText(ARABIC_AYAH)).toBeInTheDocument();
      expect(scan.scanCalls).toHaveLength(0);
      expect(screen.queryByTestId('scan-viewer')).toBeNull();
    });

    it('shows the problem of a missing scan and the rest of the card stays usable', async () => {
      setup({
        scan: () => ({
          status: 404,
          body: JSON.stringify(problem(404, 'bulunamadi').body),
          contentType: 'application/problem+json',
        }),
      });
      expect(await screen.findByText(trOcr.scan.failed)).toBeInTheDocument();
      expect(screen.getByRole('radio', { name: tr.review.approve })).toBeInTheDocument();
    });

    it('shows the decode error of a damaged TIFF', async () => {
      setup({
        scan: () => ({
          body: Uint8Array.from([0x49, 0x49, 0x2a, 0x00, 0xff, 0xff, 0xff, 0x7f]),
          contentType: 'image/tiff',
        }),
      });
      expect(await screen.findByText(trOcr.scan.tiffFailed)).toBeInTheDocument();
    });
  });

  describe('actions without an API counterpart', () => {
    it('shows Böl, Birleştir, Belirsiz işaretle and Not ekle closed with the S-15 label, and sends nothing', async () => {
      const { user, scan } = setup();
      const closed = await screen.findByTestId('ocr-closed-actions');
      const buttons = within(closed).getAllByRole('button');
      expect(buttons.map((button) => button.textContent)).toEqual(
        [trOcr.actions.split, trOcr.actions.merge, trOcr.actions.uncertain, trOcr.actions.note].map(
          (label) => `${label} · ${tr.openQuestion('S-15')}`,
        ),
      );
      for (const button of buttons) {
        expect(button).toHaveAttribute('aria-disabled', 'true');
        expect(button).toHaveAttribute('data-open-question', 'S-15');
      }
      await screen.findByTestId('scan-canvas');
      const before = fake.calls.length;
      const scansBefore = scan.scanCalls.length;
      for (const button of buttons) await user.click(button);
      expect(fake.calls).toHaveLength(before);
      expect(scan.scanCalls).toHaveLength(scansBefore);
      expect(decisionCalls()).toHaveLength(0);
    });
  });

  describe('correction (approval with an edited text)', () => {
    const approve = () => screen.findByRole('radio', { name: tr.review.approve });
    const reason = () => screen.getByLabelText(tr.review.reason);

    it('opens the edit field on Onayla for an editable unit and sends If-Match and the edited text', async () => {
      const { user } = setup();
      await user.click(await approve());
      const edit = await screen.findByLabelText(tr.review.editedText);
      // The field starts with the proposed text.
      expect(edit).toHaveValue('Deneme meal metni yeni');
      expect(screen.getByTestId('ocr-correct')).toHaveTextContent(trOcr.correct.openHint);
      fireEvent.change(edit, { target: { value: 'Deneme meal metni düzeltilmiş' } });
      await user.type(reason(), 'Sayfa görseliyle karşılaştırıldı');
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.params.id).toBe('1');
      expect(call.headers.get('If-Match')).toBe('"101"');
      expect(call.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { metin: 'Deneme meal metni düzeltilmiş' },
        gerekce: 'Sayfa görseliyle karşılaştırıldı',
      });
    });

    it('sends duzenlenen null when the text is left as proposed', async () => {
      const { user } = setup();
      await user.click(await approve());
      await screen.findByLabelText(tr.review.editedText);
      await user.type(reason(), 'Doğru');
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect((decisionCalls()[0]!.json as { duzenlenen: unknown }).duzenlenen).toBeNull();
    });

    it('rejects with If-Match and no edit field', async () => {
      const { user } = setup();
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
      await user.type(reason(), 'Okuma hatası');
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.headers.get('If-Match')).toBe('"101"');
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Okuma hatası',
      });
    });

    it('closes the edit field for a unit with marks and shows the A20 question instead', async () => {
      const { user } = setup({
        unit: (anchor) => ocrUnit(anchor, { marks: [{ start: 0, end: 3, tur: 'deneme' }] }),
      });
      const section = await screen.findByTestId('ocr-correct');
      await waitFor(() =>
        expect(within(section).getByText(trOcr.correct.offsetBlocked)).toBeInTheDocument(),
      );
      const button = within(section).getByRole('button');
      expect(button).toHaveTextContent(`${trOcr.actions.fix} · ${tr.openQuestion('A20')}`);
      expect(button).toHaveAttribute('data-open-question', 'A20');
      await user.click(await approve());
      expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
      const before = fake.calls.length;
      await user.click(button);
      expect(fake.calls).toHaveLength(before);
    });

    it('closes the edit field for a unit with sentence ranges', async () => {
      const { user } = setup({ unit: (anchor) => ocrUnit(anchor, { sentences: [[0, 5]] }) });
      await user.click(await approve());
      expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
      expect(within(screen.getByTestId('ocr-correct')).getByRole('button')).toHaveAttribute(
        'data-open-question',
        'A20',
      );
    });

    it('closes the edit field in the second approval stage and gives the reason', async () => {
      const { user } = setup({
        items: [ocrItem(1, { ikinci_onay_bekliyor: true, inceleyen: OTHER_EMAIL })],
      });
      await user.click(await approve());
      expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
      expect(screen.getByTestId('ocr-correct')).toHaveTextContent(trOcr.correct.notAvailable);
      expect(within(screen.getByTestId('ocr-correct')).queryByRole('button')).toBeNull();
    });

    it('shows no correction control for a Tanzil ayah', async () => {
      const { user } = setup({
        items: [ocrItem(1, { hedef_anahtar: AYAH_ANCHOR })],
        unit: (anchor) => ocrUnit(anchor),
      });
      const section = await screen.findByTestId('ocr-correct');
      expect(section).toHaveTextContent(trOcr.correct.immutable);
      expect(within(section).queryByRole('button')).toBeNull();
      await user.click(await approve());
      expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
      // The ayah is shown once, as the Tanzil text; there is no second "unit text" copy and no Düzelt question.
      expect(await screen.findAllByText(ARABIC_AYAH)).toHaveLength(1);
      expect(screen.queryByTestId('ocr-unit-text')).toBeNull();
      expect(screen.queryByText(new RegExp(`^${trOcr.actions.fix} `))).toBeNull();
    });

    it('closes Onayla for the editor`s own proposal', async () => {
      setup({ items: [ocrItem(1, { koken: 'editor', oneren: 'editor@deneme.test' })] });
      expect(await screen.findByTestId('approve-closed-reason')).toHaveTextContent(
        tr.review.blockedOwnProposal,
      );
      expect(screen.getByRole('radio', { name: tr.review.approve })).toHaveAttribute(
        'aria-disabled',
        'true',
      );
    });
  });

  describe('route', () => {
    it('is the lazy route kuyruk/ocr of the panel, with a focused heading', async () => {
      signedIn(fake);
      ocrHandlers(fake);
      fake.get('/api/v1/reviews/stats', ok(stats([])));
      fake.get('/api/v1/reviews', ok(page([ocrItem(1)])));
      const scan = withScanFetch(fake, scanBytes);
      renderApp(scan, '/kuyruk/ocr?kayit=1');
      const heading = await screen.findByRole('heading', { level: 1, name: tr.nav.queueOcr });
      expect(heading).toBeInTheDocument();
      expect(await screen.findByTestId('scan-canvas')).toBeInTheDocument();
    });
  });
});
