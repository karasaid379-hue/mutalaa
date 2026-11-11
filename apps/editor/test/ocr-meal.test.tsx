// The two Elmalılı meals in the `kuyruk/ocr` route (A16.5, K-49): source tabs and the stage view, the source name and
// edition label, the pipeline warning and witness agreement, the covered range of a joined meal, its follower unit
// and the basmala meal. Texts are made up ("Deneme meal paragrafı 1"), never meal text.
import { screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trOcr } from '@/i18n/tr-ocr';
import { Component as QueueOcr } from '@/screens/queue-ocr';
import { ok, useFakeApi } from './fake-api';
import { page, session } from './fixtures';
import {
  ARABIC_AYAH,
  DECIDED,
  ocrDetail,
  ocrHandlers,
  ocrItem,
  ocrUnit,
  pipelineProposal,
  stubCanvas,
  stubObjectUrls,
  withScanFetch,
  type CanvasStub,
  type ObjectUrlStub,
} from './fixtures-ocr';
import { renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type Unit = components['schemas']['UnitDetail'];

const ORIGINAL = 'meal:elmalili:2:1';
const SIMPLIFIED = 'meal:elmalili-sade:2:1';
const FOLLOWER = 'meal:elmalili:2:2';

function mealItem(id: number, anchor: string, over: Partial<Item> = {}): Item {
  return ocrItem(id, {
    hedef_anahtar: anchor,
    onceki: null,
    onerilen: { metin: 'Deneme meal paragrafı 1', content_hash: 'hash-1' },
    oneren: 'hat',
    koken: 'hat',
    ...over,
  });
}

describe('kuyruk/ocr: meals', () => {
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

  interface SetupOptions {
    items?: Item[];
    detail?: (id: number) => components['schemas']['ReviewDetailDto'];
    unit?: (anchor: string) => Unit;
    route?: string;
    /** Answer of the list for the request's query (default: `items`). */
    list?: (search: URLSearchParams) => Item[];
  }

  function setup(options: SetupOptions = {}) {
    const items = options.items ?? [mealItem(1, ORIGINAL), mealItem(2, SIMPLIFIED)];
    ocrHandlers(fake, {
      ...(options.unit ? { unit: options.unit } : {}),
      detail: options.detail ?? ((id) => ocrDetail(id, items.find((item) => item.id === id) ?? {})),
    });
    fake.get(
      '/api/v1/reviews',
      options.list ? (call) => ok(page(options.list!(call.search))) : ok(page(items)),
    );
    fake.get('/api/v1/auth/me', ok(session(['editor'])));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({ ...DECIDED, id: Number(call.params.id) }),
    );
    const scan = withScanFetch(fake, () => ({ body: new Uint8Array(), contentType: 'image/tiff' }));
    return renderInRouter(scan, <QueueOcr />, options.route ?? '/');
  }

  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const lastList = () => listCalls().at(-1)!;
  /** The unit of a meal without a page mapping (the hat path): `attrs` as given. */
  const mealUnit =
    (attrs: Record<string, unknown>, over: Partial<Unit> = {}) =>
    (anchor: string): Unit =>
      ocrUnit(anchor, { attrs, ...over });

  describe('source tabs and stage view', () => {
    it('starts with every source and every open record: no kaynak and no asama', async () => {
      setup();
      await screen.findAllByRole('link');
      const first = listCalls()[0]!;
      expect(first.search.has('kaynak')).toBe(false);
      expect(first.search.has('asama')).toBe(false);
      expect(first.search.get('hedef_tablo')).toBe('unit');
      expect(first.search.get('alan')).toBe('metin');
      expect(screen.getByRole('tab', { name: trOcr.filters.sources.hepsi })).toHaveAttribute(
        'aria-selected',
        'true',
      );
    });

    it('names the two tab rows and lists the source tabs and the stage views', async () => {
      setup();
      const sources = await screen.findByRole('tablist', { name: trOcr.filters.sourceLabel });
      expect(
        within(sources)
          .getAllByRole('tab')
          .map((tab) => tab.textContent),
      ).toEqual([
        trOcr.filters.sources.hepsi,
        trOcr.filters.sources.orijinal,
        trOcr.filters.sources.sade,
      ]);
      const stages = screen.getByRole('tablist', { name: trOcr.filters.stageLabel });
      expect(
        within(stages)
          .getAllByRole('tab')
          .map((tab) => tab.textContent),
      ).toEqual([
        trOcr.filters.stages.hepsi,
        trOcr.filters.stages.ilk,
        trOcr.filters.stages.ikinci,
      ]);
    });

    it('asks for the original meal with kaynak=elmalili-meal and for the simplified one with kaynak=elmalili-sade-meal', async () => {
      const { user } = setup();
      await screen.findAllByRole('link');
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.orijinal }));
      await waitFor(() => expect(lastList().search.get('kaynak')).toBe('elmalili-meal'));
      expect(lastList().search.has('asama')).toBe(false);
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.sade }));
      await waitFor(() => expect(lastList().search.get('kaynak')).toBe('elmalili-sade-meal'));
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.hepsi }));
      await waitFor(() => expect(lastList().search.has('kaynak')).toBe(false));
    });

    it('shows the second approval view with asama=ikinci and keeps the source', async () => {
      const { user } = setup();
      await screen.findAllByRole('link');
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.sade }));
      await user.click(screen.getByRole('tab', { name: trOcr.filters.stages.ikinci }));
      await waitFor(() => expect(lastList().search.get('asama')).toBe('ikinci'));
      expect(lastList().search.get('kaynak')).toBe('elmalili-sade-meal');
      expect(lastList().search.get('hedef_tablo')).toBe('unit');
      expect(lastList().search.get('durum')).toBe('acik');
      expect(lastList().search.has('cursor')).toBe(false);
      await user.click(screen.getByRole('tab', { name: trOcr.filters.stages.ilk }));
      await waitFor(() => expect(lastList().search.get('asama')).toBe('ilk'));
      await user.click(screen.getByRole('tab', { name: trOcr.filters.stages.hepsi }));
      await waitFor(() => expect(lastList().search.has('asama')).toBe(false));
    });

    it('drops the selected record when a tab changes', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await screen.findByText(trOcr.detailHeading);
      await user.click(screen.getByRole('tab', { name: trOcr.filters.stages.ikinci }));
      expect(await screen.findByText(tr.queue.selectPrompt)).toBeInTheDocument();
      expect(screen.queryByText(trOcr.detailHeading)).toBeNull();
    });

    it('explains the selected tab as plain text tied to its row, with the source id as code', async () => {
      const { user } = setup();
      await screen.findAllByRole('link');
      const sources = screen.getByRole('tablist', { name: trOcr.filters.sourceLabel });
      expect(sources).toHaveAccessibleDescription(trOcr.filters.sourceHints.hepsi);
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.sade }));
      await waitFor(() =>
        expect(sources).toHaveAccessibleDescription(
          `${trOcr.filters.sourceHints.sade} ${trOcr.filters.sourceIdLabel} elmalili-sade-meal`,
        ),
      );
      expect(
        within(screen.getByTestId('ocr-filters')).getByText('elmalili-sade-meal').tagName,
      ).toBe('CODE');
      await user.click(screen.getByRole('tab', { name: trOcr.filters.stages.ikinci }));
      const stages = screen.getByRole('tablist', { name: trOcr.filters.stageLabel });
      await waitFor(() =>
        expect(stages).toHaveAccessibleDescription(trOcr.filters.stageHints.ikinci),
      );
    });
  });

  describe('tab rows: keyboard, URL and live region', () => {
    const selectedTabs = () =>
      screen.getAllByRole('tab', { selected: true }).map((tab) => tab.textContent);
    const urlParams = (router: { state: { location: { search: string } } }) =>
      new URLSearchParams(router.state.location.search);

    it('has no tab panel, so no empty focus stop and no dangling aria-controls', async () => {
      setup();
      await screen.findAllByRole('link');
      expect(screen.queryAllByRole('tabpanel')).toHaveLength(0);
      for (const tab of screen.getAllByRole('tab')) {
        expect(tab).not.toHaveAttribute('aria-controls');
      }
      // Tab order: the selected tab of each row, then the list links; nothing else takes focus.
      const focusable = screen
        .getByTestId('ocr-filters')
        .querySelectorAll('[tabindex]:not([tabindex="-1"])');
      expect([...focusable].map((el) => el.getAttribute('role'))).toEqual(['tab', 'tab']);
    });

    it('moves focus with the arrow keys and selects with Enter, dropping only ?kayit=', async () => {
      const { user, router } = setup({ route: '/?kayit=1&asama=ilk' });
      await screen.findByText(trOcr.detailHeading);
      await user.tab();
      const all = screen.getByRole('tab', { name: trOcr.filters.sources.hepsi });
      expect(all).toHaveFocus();
      await user.keyboard('{ArrowRight}');
      const original = screen.getByRole('tab', { name: trOcr.filters.sources.orijinal });
      expect(original).toHaveFocus();
      expect(original).toHaveAttribute('aria-selected', 'false');
      await user.keyboard('{ArrowRight}');
      expect(screen.getByRole('tab', { name: trOcr.filters.sources.sade })).toHaveFocus();
      await user.keyboard('{ArrowLeft}');
      expect(original).toHaveFocus();
      await user.keyboard('{Enter}');
      await waitFor(() => expect(original).toHaveAttribute('aria-selected', 'true'));
      await waitFor(() => expect(lastList().search.get('kaynak')).toBe('elmalili-meal'));
      const params = urlParams(router);
      expect(params.get('kaynak')).toBe('orijinal');
      expect(params.get('asama')).toBe('ilk');
      expect(params.has('kayit')).toBe(false);
      expect(await screen.findByText(tr.queue.selectPrompt)).toBeInTheDocument();
    });

    it('selects with Space as well', async () => {
      const { user } = setup();
      await screen.findAllByRole('link');
      await user.tab();
      await user.keyboard('{ArrowRight}{ArrowRight}');
      const simplified = screen.getByRole('tab', { name: trOcr.filters.sources.sade });
      expect(simplified).toHaveFocus();
      await user.keyboard(' ');
      await waitFor(() => expect(simplified).toHaveAttribute('aria-selected', 'true'));
      await waitFor(() => expect(lastList().search.get('kaynak')).toBe('elmalili-sade-meal'));
    });

    it('reads both tabs from the URL, keeps them in the row links and writes them back', async () => {
      const { user, router } = setup({ route: '/?kaynak=sade&asama=ikinci&kayit=1' });
      await screen.findAllByRole('link');
      expect(selectedTabs()).toEqual([trOcr.filters.sources.sade, trOcr.filters.stages.ikinci]);
      const first = listCalls()[0]!;
      expect(first.search.get('kaynak')).toBe('elmalili-sade-meal');
      expect(first.search.get('asama')).toBe('ikinci');
      const list = screen.getByRole('region', { name: tr.queue.listLabel });
      for (const link of within(list).getAllByRole('link')) {
        const href = new URLSearchParams(link.getAttribute('href')!.split('?')[1]);
        expect(href.get('kaynak')).toBe('sade');
        expect(href.get('asama')).toBe('ikinci');
        expect(href.has('kayit')).toBe(true);
      }
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.hepsi }));
      await waitFor(() => expect(urlParams(router).has('kaynak')).toBe(false));
      expect(urlParams(router).get('asama')).toBe('ikinci');
      expect(urlParams(router).has('kayit')).toBe(false);
    });

    it('treats an unknown tab value in the URL as the default tab', async () => {
      setup({ route: '/?kaynak=baska&asama=bozuk' });
      await screen.findAllByRole('link');
      expect(selectedTabs()).toEqual([trOcr.filters.sources.hepsi, trOcr.filters.stages.hepsi]);
      expect(listCalls()[0]!.search.has('kaynak')).toBe(false);
      expect(listCalls()[0]!.search.has('asama')).toBe(false);
    });

    it('keeps the tabs in the URL after a decision opens the next record', async () => {
      const { user, router } = setup({
        items: [mealItem(1, SIMPLIFIED), mealItem(2, SIMPLIFIED)],
        route: '/?kaynak=sade&asama=ilk&kayit=1',
        unit: mealUnit({}),
      });
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      await user.type(screen.getByLabelText(tr.review.reason), 'Deneme gerekçe');
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(urlParams(router).get('kayit')).toBe('2'));
      expect(urlParams(router).get('kaynak')).toBe('sade');
      expect(urlParams(router).get('asama')).toBe('ilk');
    });

    it('has one live region and says how many records loaded, after the load and after a filter change', async () => {
      const items = [mealItem(1, ORIGINAL), mealItem(2, SIMPLIFIED), mealItem(3, SIMPLIFIED)];
      const { user } = setup({
        items,
        list: (search) => (search.get('kaynak') === 'elmalili-sade-meal' ? items.slice(1) : items),
      });
      await screen.findAllByRole('link');
      expect(screen.getAllByRole('status')).toHaveLength(1);
      const live = screen.getByRole('status');
      await waitFor(() => expect(live).toHaveTextContent(tr.queue.loadedCount(3)));
      await user.click(screen.getByRole('tab', { name: trOcr.filters.sources.sade }));
      await waitFor(() => expect(live).toHaveTextContent(tr.queue.loadedCount(2)));
      expect(screen.getAllByRole('status')).toHaveLength(1);
    });

    it('does not replace the decision message with the count', async () => {
      const { user } = setup({
        items: [mealItem(1, SIMPLIFIED), mealItem(2, SIMPLIFIED)],
        route: '/?kayit=1',
        unit: mealUnit({}),
      });
      await screen.findAllByRole('link');
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      await user.type(screen.getByLabelText(tr.review.reason), 'Deneme gerekçe');
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() =>
        expect(screen.getByRole('status')).toHaveTextContent(tr.review.decided('reddedildi')),
      );
      expect(screen.getByRole('status')).not.toHaveTextContent(tr.queue.loadedCount(1));
    });
  });

  describe('source name and edition label', () => {
    it('shows the source and its edition label on every list row of a meal', async () => {
      setup({ items: [mealItem(1, ORIGINAL), mealItem(2, SIMPLIFIED)] });
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      const rows = await within(list).findAllByRole('listitem');
      expect(within(rows[0]!).getByTestId('ocr-source')).toHaveTextContent(
        `${trOcr.source.label}${trOcr.source.names.orijinal}${trOcr.source.editions.orijinal}`,
      );
      expect(within(rows[1]!).getByTestId('ocr-source')).toHaveTextContent(
        `${trOcr.source.label}${trOcr.source.names.sade}${trOcr.source.editions.sade}`,
      );
      expect(within(rows[0]!).queryByText(trOcr.source.editions.sade)).toBeNull();
    });

    it('draws nothing for a unit that is not one of the two meals', async () => {
      setup({ items: [ocrItem(1)] });
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      await within(list).findAllByRole('listitem');
      expect(screen.queryByTestId('ocr-source')).toBeNull();
    });

    it('shows the source and the label in the detail of the simplified meal, without an unverified badge', async () => {
      setup({
        items: [mealItem(1, SIMPLIFIED)],
        route: '/?kayit=1',
        unit: mealUnit({}),
      });
      const detail = await screen.findByRole('region', { name: tr.queue.detailLabel });
      const source = await within(detail).findByTestId('ocr-source');
      expect(source).toHaveTextContent(trOcr.source.editions.sade);
      // "Doğrulanmamış" comes from the API field only; the edition label never produces it.
      expect(within(detail).queryByText(tr.badge.unverified)).toBeNull();
    });

    it('shows the unverified badge of the meal only from dogrulanmamis', async () => {
      setup({
        items: [mealItem(1, SIMPLIFIED, { dogrulanmamis: true }), mealItem(2, ORIGINAL)],
      });
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      const rows = await within(list).findAllByRole('listitem');
      expect(within(rows[0]!).getByText(tr.badge.unverified)).toBeInTheDocument();
      expect(within(rows[1]!).queryByText(tr.badge.unverified)).toBeNull();
    });
  });

  describe('pipeline notes', () => {
    const pipelineItem = (over: Record<string, unknown> = {}) =>
      mealItem(1, ORIGINAL, { onerilen: pipelineProposal(over) });
    const open = (items: Item[]) => setup({ items, route: '/?kayit=1', unit: mealUnit({}) });

    it('explains each warning code in Turkish, in the order given', async () => {
      const codes = Object.keys(trOcr.hat.warnings);
      expect(codes).toEqual([
        'birlesik_meal',
        'ortak_metin',
        'numarasiz_parca',
        'yinelenen_numara',
        'sira_disi',
        'besmele_meali',
      ]);
      open([pipelineItem({ uyari: codes })]);
      const warning = await screen.findByTestId('ocr-hat-warning');
      expect(warning).toHaveTextContent(trOcr.hat.warningHeading);
      expect(warning).toHaveAttribute('role', 'note');
      const items = within(warning).getAllByRole('listitem');
      expect(items.map((item) => item.textContent)).toEqual(Object.values(trOcr.hat.warnings));
      // The code strings themselves are never shown.
      expect(warning).not.toHaveTextContent('numarasiz_parca');
    });

    it('names an unknown warning code with the raw code in a code element', async () => {
      open([pipelineItem({ uyari: ['kod_bilinmiyor', 'constructor', 'birlesik_meal'] })]);
      const warning = await screen.findByTestId('ocr-hat-warning');
      const items = within(warning).getAllByRole('listitem');
      expect(items.map((item) => item.textContent)).toEqual([
        `${trOcr.hat.unknownWarning} kod_bilinmiyor`,
        `${trOcr.hat.unknownWarning} constructor`,
        trOcr.hat.warnings.birlesik_meal,
      ]);
      expect(within(items[0]!).getByText('kod_bilinmiyor').tagName).toBe('CODE');
      expect(within(items[1]!).getByText('constructor').tagName).toBe('CODE');
    });

    it('cuts a very long unknown code', async () => {
      open([pipelineItem({ uyari: ['x'.repeat(200)] })]);
      const warning = await screen.findByTestId('ocr-hat-warning');
      expect(within(warning).getByText(`${'x'.repeat(64)}…`)).toBeInTheDocument();
    });

    it('shows the witness agreement and its range, and never calls it "Güven"', async () => {
      open([pipelineItem()]);
      const witness = await screen.findByTestId('ocr-witness');
      expect(
        within(witness).getByRole('heading', { name: trOcr.hat.witnessHeading }),
      ).toBeInTheDocument();
      expect(witness).toHaveTextContent('Tanık uyumu %97');
      expect(witness).toHaveTextContent('Tanık kapsamı: 1–2');
      expect(witness).toHaveTextContent(`${trOcr.hat.witnessSourceLabel} elmalili-meal-epub`);
      expect(witness).toHaveTextContent(
        `${trOcr.hat.witnessMethodLabel} rapidfuzz.fuzz.ratio/tr_narrow`,
      );
      // The raw identifiers are drawn as code.
      expect(within(witness).getByText('elmalili-meal-epub').tagName).toBe('CODE');
      expect(within(witness).getByText('rapidfuzz.fuzz.ratio/tr_narrow').tagName).toBe('CODE');
      expect(witness).toHaveTextContent(trOcr.hat.witnessHint);
      expect(screen.queryByText(/Güven/)).toBeNull();
    });

    it('leaves the range out when kapsam is null', async () => {
      open([
        pipelineItem({
          tanik: {
            skor: 80,
            kapsam: null,
            yontem: 'deneme-1',
            yontem_surumu: '1',
            kaynak: 'deneme',
          },
        }),
      ]);
      const witness = await screen.findByTestId('ocr-witness');
      expect(witness).toHaveTextContent('Tanık uyumu %80');
      expect(witness).not.toHaveTextContent('Tanık kapsamı');
    });

    it('shows the witness box without a warning box when there is no warning', async () => {
      open([pipelineItem({ uyari: [] })]);
      await screen.findByTestId('ocr-witness');
      expect(screen.queryByTestId('ocr-hat-warning')).toBeNull();
    });

    it('shows neither box when the proposal carries no warning and no witness agreement', async () => {
      open([mealItem(1, ORIGINAL)]);
      await screen.findByText(trOcr.detailHeading);
      await screen.findByTestId('ocr-unit-text');
      expect(screen.queryByTestId('ocr-hat-warning')).toBeNull();
      expect(screen.queryByTestId('ocr-witness')).toBeNull();
    });

    it('ignores an unreadable tanik and a uyari that is not a list', async () => {
      open([pipelineItem({ tanik: 'bozuk', uyari: 'numarasiz_parca' })]);
      await screen.findByTestId('ocr-unit-text');
      expect(screen.queryByTestId('ocr-witness')).toBeNull();
      expect(screen.queryByTestId('ocr-hat-warning')).toBeNull();
    });
  });

  describe('joined meal', () => {
    it('shows the ayahs of attrs.kapsam on the head unit', async () => {
      setup({
        items: [mealItem(1, ORIGINAL)],
        route: '/?kayit=1',
        unit: mealUnit({ kapsam: 'q:2:1-2' }),
      });
      const section = await screen.findByTestId('ocr-ayah');
      expect(await within(section).findByTestId('ocr-ayah-scope')).toHaveTextContent(
        trOcr.merged.scope('q:2:1-2'),
      );
      await waitFor(() => expect(within(section).getAllByText(ARABIC_AYAH)).toHaveLength(2));
      const asked = fake.callsTo('get', '/api/v1/units/{anchor}').map((call) => call.params.anchor);
      expect(asked).toContain('q:2:1');
      expect(asked).toContain('q:2:2');
    });

    it('falls back to the ayah of the unit when kapsam cannot be read', async () => {
      setup({
        items: [mealItem(1, ORIGINAL)],
        route: '/?kayit=1',
        unit: mealUnit({ kapsam: 'bozuk' }),
      });
      const section = await screen.findByTestId('ocr-ayah');
      expect(within(section).queryByTestId('ocr-ayah-scope')).toBeNull();
      await waitFor(() => expect(within(section).getAllByText(ARABIC_AYAH)).toHaveLength(1));
    });

    describe('the follower unit', () => {
      function setupFollower(over: Partial<Item> = {}) {
        return setup({
          items: [mealItem(1, FOLLOWER, { onerilen: null, ...over })],
          route: '/?kayit=1',
          unit: mealUnit({ birlesik_ile: ORIGINAL }, { metin: '' }),
        });
      }

      it('links to the head unit and says the text is there', async () => {
        setupFollower();
        const section = await screen.findByTestId('ocr-follower');
        expect(section).toHaveTextContent(trOcr.merged.followerBody);
        const link = within(section).getByTestId('ocr-follower-head');
        expect(link).toHaveTextContent(ORIGINAL);
        expect(link).toHaveAttribute('href', '/birimler?birim=meal%3Aelmalili%3A2%3A1');
        // The empty text is not announced as a gap: only the follower section speaks.
        expect(screen.queryByTestId('ocr-unit-text')).toBeNull();
        expect(screen.queryByText(trOcr.text.empty)).toBeNull();
      });

      it('shows a closed Düzelt with its reason, no edit field, and sends nothing when it is pressed', async () => {
        const { user } = setupFollower();
        const fix = await screen.findByTestId('ocr-follower-fix');
        expect(fix).toHaveAttribute('aria-disabled', 'true');
        expect(fix).toHaveAccessibleDescription(trOcr.merged.fixClosedHint);
        expect(fix).not.toHaveAttribute('data-open-question');
        const before = fake.calls.length;
        await user.click(fix);
        expect(fake.calls).toHaveLength(before);
        await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
        expect(screen.queryByLabelText(tr.review.editedText)).toBeNull();
        expect(screen.getByTestId('ocr-correct')).not.toHaveTextContent(trOcr.correct.openHint);
      });

      it('says there is no proposal and approves the status with duzenlenen null', async () => {
        const { user } = setupFollower();
        expect(await screen.findByText(trOcr.diff.noProposal)).toBeInTheDocument();
        await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
        await user.type(screen.getByLabelText(tr.review.reason), 'Durum onayı');
        await user.click(screen.getByRole('button', { name: tr.review.submit }));
        await waitFor(() =>
          expect(fake.callsTo('post', '/api/v1/reviews/{id}/decision')).toHaveLength(1),
        );
        expect(fake.callsTo('post', '/api/v1/reviews/{id}/decision')[0]!.json).toEqual({
          karar: 'onaylandi',
          duzenlenen: null,
          gerekce: 'Durum onayı',
        });
      });

      it('names the head unit as unreadable when birlesik_ile is not an anchor', async () => {
        setup({
          items: [mealItem(1, FOLLOWER, { onerilen: null })],
          route: '/?kayit=1',
          unit: mealUnit({ birlesik_ile: 'bozuk' }, { metin: '' }),
        });
        const section = await screen.findByTestId('ocr-follower');
        expect(section).toHaveTextContent(trOcr.merged.headMissing);
        expect(within(section).queryByRole('link')).toBeNull();
      });
    });

    it('keeps the edit field open on the head unit', async () => {
      const { user } = setup({
        items: [mealItem(1, ORIGINAL)],
        route: '/?kayit=1',
        unit: mealUnit({ kapsam: 'q:2:1-2' }),
      });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      expect(await screen.findByLabelText(tr.review.editedText)).toBeInTheDocument();
      expect(screen.queryByTestId('ocr-follower')).toBeNull();
    });
  });

  describe('basmala meal', () => {
    it('shows attrs.besmele_meali apart from the unit text', async () => {
      setup({
        items: [mealItem(1, ORIGINAL)],
        route: '/?kayit=1',
        unit: mealUnit({
          besmele_meali: { metin: 'Deneme besmele meali', content_hash: 'hash-b' },
        }),
      });
      const section = await screen.findByTestId('ocr-besmele');
      expect(
        within(section).getByRole('heading', { name: trOcr.besmele.heading }),
      ).toBeInTheDocument();
      expect(within(section).getByText('Deneme besmele meali')).toBeInTheDocument();
      expect(
        within(screen.getByTestId('ocr-unit-text')).queryByText('Deneme besmele meali'),
      ).toBeNull();
    });

    it('shows nothing without besmele_meali', async () => {
      setup({ items: [mealItem(1, ORIGINAL)], route: '/?kayit=1', unit: mealUnit({}) });
      await screen.findByTestId('ocr-unit-text');
      expect(screen.queryByTestId('ocr-besmele')).toBeNull();
    });
  });

  describe('closed actions', () => {
    it('labels the OCR actions S-15 and the correction of an offset unit A20', async () => {
      setup({
        items: [mealItem(1, ORIGINAL)],
        route: '/?kayit=1',
        unit: mealUnit({}, { marks: [{ start: 0, end: 3, tur: 'deneme' }] }),
      });
      const closed = await screen.findByTestId('ocr-closed-actions');
      for (const button of within(closed).getAllByRole('button')) {
        expect(button).toHaveAttribute('data-open-question', 'S-15');
      }
      const correct = await screen.findByTestId('ocr-correct');
      await waitFor(() =>
        expect(within(correct).getByRole('button')).toHaveAttribute('data-open-question', 'A20'),
      );
      expect(correct).toHaveTextContent(trOcr.correct.offsetBlocked);
    });

    it('says in the scan notice that scanning is left to S-15', async () => {
      setup({ items: [mealItem(1, ORIGINAL)], route: '/?kayit=1', unit: mealUnit({}) });
      expect(await screen.findByTestId('scan-not-mapped')).toHaveTextContent(trOcr.scan.notMapped);
      expect(trOcr.scan.notMapped).toContain('S-15');
    });
  });
});
