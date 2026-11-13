import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { BaglantiQueue } from '@/screens/baglanti/baglanti-queue';
import { BULK_ENABLED, linkFilter } from '@/screens/baglanti/config';
import { MEAL_ID, targetInfo } from '@/screens/baglanti/target';
import { ok, problem, useFakeApi } from './fake-api';
import {
  ARABIC_SAMPLE,
  ARABIC_SAMPLE_2,
  linkTarget,
  unitFor,
  xrefDetail,
  xrefHandlers,
  xrefItem,
} from './fixtures-baglanti-sure';
import { page, session, signedIn, stats } from './fixtures';
import { renderApp, renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];

const items = (count: number): Item[] =>
  Array.from({ length: count }, (_, index) => xrefItem(index + 1));

const openQuestions = () => [...document.querySelectorAll<HTMLElement>('[data-open-question]')];

describe('target info', () => {
  it('reads the target anchor with @mutalaa/anchors only', () => {
    expect(targetInfo('q:1:2')).toEqual({ ayah: true, mealAnchor: `meal:${MEAL_ID}:1:2` });
    expect(targetInfo('h:deneme:1')).toEqual({ ayah: false, mealAnchor: null });
    expect(targetInfo('rn:deneme:p1')).toEqual({ ayah: false, mealAnchor: null });
    expect(targetInfo('Q:1:2')).toEqual({ ayah: false, mealAnchor: null });
    expect(targetInfo('')).toEqual({ ayah: false, mealAnchor: null });
  });
});

describe('link filter', () => {
  it('is the xref status queue in class order, with the status and class the editor chose', () => {
    expect(linkFilter('acik', 'hepsi')).toEqual({
      hedef_tablo: 'xref',
      alan: 'status',
      sira: 'sinif',
    });
    expect(linkFilter('uzmanda', 'gri')).toEqual({
      hedef_tablo: 'xref',
      alan: 'status',
      sira: 'sinif',
      durum: 'uzmanda',
      sinif: 'gri',
    });
  });
});

describe('BaglantiQueue', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const unitCalls = () => fake.callsTo('get', '/api/v1/units/{anchor}');
  const singleCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');
  const bulkCalls = () => fake.callsTo('post', '/api/v1/reviews/decisions');

  function setup(list: Item[] = items(2), route = '/', bulkEnabled?: boolean) {
    let store = list;
    fake.get('/api/v1/reviews', () => ok(page(store)));
    xrefHandlers(fake);
    fake.get('/api/v1/auth/me', ok(session()));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 700,
      }),
    );
    fake.post('/api/v1/reviews/decisions', (call) => {
      const kararlar = (call.json as { kararlar: { id: number }[] }).kararlar;
      store = store.filter((item) => !kararlar.some((entry) => entry.id === item.id));
      return ok({
        sonuclar: kararlar.map((entry) => ({
          id: entry.id,
          durum: 'onaylandi',
          eylem: 'onayla',
          xmin: 800 + entry.id,
        })),
      });
    });
    return renderInRouter(fake, <BaglantiQueue bulkEnabled={bulkEnabled} />, route);
  }

  /** Detail handler for one record, registered after the defaults so it wins (stats stay answered). */
  function withDetail(detail: components['schemas']['ReviewDetailDto']) {
    fake.get('/api/v1/reviews', ok(page(items(1))));
    xrefHandlers(fake);
    fake.get('/api/v1/reviews/{id}', ok(detail));
    fake.get('/api/v1/reviews/stats', ok(stats([['xref', 'status', 1]])));
    fake.get('/api/v1/auth/me', ok(session()));
  }

  describe('list', () => {
    it('sends the first request without a cursor, with the xref filter and in class order', async () => {
      setup();
      await screen.findAllByRole('link');
      const first = listCalls()[0]!;
      expect(first.search.has('cursor')).toBe(false);
      expect(first.search.get('hedef_tablo')).toBe('xref');
      expect(first.search.get('alan')).toBe('status');
      expect(first.search.get('durum')).toBe('acik');
      expect(first.search.get('sira')).toBe('sinif');
      expect(first.search.has('sinif')).toBe(false);
      expect(first.search.get('limit')).toBe('50');
    });

    it('shows the empty state', async () => {
      fake.get('/api/v1/reviews', ok(page([])));
      fake.get('/api/v1/reviews/stats', ok(stats([])));
      renderInRouter(fake, <BaglantiQueue />);
      expect(await screen.findByTestId('queue-empty')).toHaveTextContent(tr.queue.empty);
    });

    it('shows the problem when the list fails', async () => {
      fake.get('/api/v1/reviews', problem(500, 'sunucu-hatasi'));
      fake.get('/api/v1/reviews/stats', ok(stats([])));
      renderInRouter(fake, <BaglantiQueue />);
      expect(await screen.findByText(tr.queue.loadFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    });

    it('shows the unverified badge only from the API field', async () => {
      fake.get(
        '/api/v1/reviews',
        ok(page([xrefItem(1, { dogrulanmamis: true, yz_modeli: 'deneme-model' }), xrefItem(2)])),
      );
      fake.get('/api/v1/reviews/stats', ok(stats([])));
      renderInRouter(fake, <BaglantiQueue />);
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      await within(list).findAllByRole('listitem');
      expect(within(list).getAllByText(tr.badge.unverified)).toHaveLength(1);
    });

    it('gives every row its class as a badge with text, in the order the API sent', async () => {
      const list = [
        xrefItem(1, { sinif: 'tutarsiz' }),
        xrefItem(2, { sinif: 'toplu' }),
        xrefItem(3, { sinif: 'gri' }),
        xrefItem(4, { sinif: 'diger' }),
      ];
      setup(list);
      const region = await screen.findByRole('region', { name: tr.queue.listLabel });
      const rows = await within(region).findAllByRole('listitem');
      expect(rows).toHaveLength(4);
      const texts = rows.map((row) => within(row).getByTestId('class-badge').textContent);
      expect(texts).toEqual([
        trBaglanti.classes.tutarsiz,
        trBaglanti.classes.toplu,
        trBaglanti.classes.gri,
        trBaglanti.classes.diger,
      ]);
      // The meaning is in text, not colour alone: every badge has a hidden explanation tied to it.
      for (const [index, cls] of (['tutarsiz', 'toplu', 'gri', 'diger'] as const).entries()) {
        const badge = within(rows[index]!).getByTestId('class-badge');
        expect(badge).toHaveAttribute('data-link-class', cls);
        expect(badge).toHaveAccessibleDescription(trBaglanti.classHints[cls]);
      }
    });

    it('draws no class badge for a record without a known class', async () => {
      setup([xrefItem(1, { sinif: null }), xrefItem(2, { sinif: 'yeni-sinif' })]);
      await screen.findAllByRole('link');
      expect(screen.queryByTestId('class-badge')).not.toBeInTheDocument();
    });

    it('filters by class on the server: a new query with sinif, the cursor starts over', async () => {
      const { user } = setup(items(2));
      await screen.findAllByRole('link');
      await user.click(screen.getByRole('radio', { name: /^Gri bölge/ }));
      await waitFor(() =>
        expect(listCalls().some((call) => call.search.get('sinif') === 'gri')).toBe(true),
      );
      const call = listCalls().find((entry) => entry.search.get('sinif') === 'gri')!;
      expect(call.search.has('cursor')).toBe(false);
      expect(call.search.get('sira')).toBe('sinif');
      expect(call.search.get('hedef_tablo')).toBe('xref');
    });

    it('takes the class counts of the filter from the stats (baglanti_siniflari)', async () => {
      setup();
      const group = await screen.findByRole('radiogroup', { name: trBaglanti.classFilter.label });
      await waitFor(() =>
        expect(
          within(group).getByRole('radio', {
            name: trBaglanti.classFilter.count(trBaglanti.classes.tutarsiz, 1),
          }),
        ).toBeInTheDocument(),
      );
      expect(
        within(group).getByRole('radio', {
          name: trBaglanti.classFilter.count(trBaglanti.classes.toplu, 2),
        }),
      ).toBeInTheDocument();
      // A class the stats do not list has count 0.
      expect(
        within(group).getByRole('radio', {
          name: trBaglanti.classFilter.count(trBaglanti.classes.gri, 0),
        }),
      ).toBeInTheDocument();
    });

    it('shows the records sent to an expert in a view of its own (durum=uzmanda) with a note', async () => {
      const { user } = setup(items(2));
      await screen.findAllByRole('link');
      const uzmanda = await screen.findByRole('radio', {
        name: trBaglanti.statusView.uzmandaCount(trBaglanti.statusView.uzmanda, 1),
      });
      await user.click(uzmanda);
      await waitFor(() =>
        expect(listCalls().some((call) => call.search.get('durum') === 'uzmanda')).toBe(true),
      );
      expect(await screen.findByText(trBaglanti.statusView.uzmandaNote)).toBeInTheDocument();
      // No bulk checkbox in this view.
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    });
  });

  describe('detail', () => {
    it('shows the paragraph, the candidate ayah (Arabic, as stored) and the meal from the units endpoint', async () => {
      setup(items(2), '/?kayit=1');
      expect(await screen.findByText('Deneme paragrafı 1')).toBeInTheDocument();
      expect(await screen.findByText('Deneme meal metni 1')).toBeInTheDocument();
      const ayah = await screen.findByText(ARABIC_SAMPLE);
      expect(ayah).toHaveAttribute('lang', 'ar');
      expect(ayah).toHaveAttribute('dir', 'rtl');
      expect(ayah.textContent).toBe(ARABIC_SAMPLE);
      expect(
        screen.getByRole('heading', { level: 3, name: trBaglanti.sourceParagraph }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('heading', { level: 3, name: trBaglanti.candidateAyah }),
      ).toBeInTheDocument();
      expect(screen.getByRole('heading', { level: 3, name: trBaglanti.meal })).toBeInTheDocument();
      expect(
        unitCalls()
          .map((call) => call.params.anchor)
          .sort(),
      ).toEqual(['meal:elmalili:1:2', 'q:1:2', 'rn:deneme:p1']);
    });

    it('shows no meal and no Arabic styling when the target is not an ayah', async () => {
      withDetail(xrefDetail(1, 'rn:deneme:p1', 'h:deneme:1'));
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByText(trBaglanti.mealNotShown)).toBeInTheDocument();
      expect(
        unitCalls()
          .map((call) => call.params.anchor)
          .sort(),
      ).toEqual(['h:deneme:1', 'rn:deneme:p1']);
    });

    it('says so when the record has no anchors and fetches no unit', async () => {
      withDetail(xrefDetail(1, '', '', { hedef: { tablo: 'xref' } }));
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByText(trBaglanti.noAnchors)).toBeInTheDocument();
      expect(unitCalls()).toHaveLength(0);
    });

    it('shows the problem of a text that cannot be loaded, the rest stays', async () => {
      withDetail(xrefDetail(1));
      fake.get('/api/v1/units/{anchor}', (call) =>
        call.params.anchor!.startsWith('meal:')
          ? problem(404, 'bulunamadi')
          : ok(unitFor(call.params.anchor!)),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByText(trBaglanti.textFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
      expect(await screen.findByText('Deneme paragrafı 1')).toBeInTheDocument();
    });

    it('shows the first and the second approval apart', async () => {
      withDetail(
        xrefDetail(1, undefined, undefined, {
          ikinci_onay_bekliyor: true,
          inceleyen: 'baska@deneme.test',
        }),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByTestId('approval-first')).toBeInTheDocument();
      expect(screen.getByTestId('approval-second')).toBeInTheDocument();
    });

    it('draws the highlighted sequence: before, the sequence in a mark (Arabic as Arabic), after', async () => {
      setup(items(1), '/?kayit=1');
      const text = await screen.findByTestId('link-highlight-text');
      expect(text).toHaveTextContent(`Deneme önce ${ARABIC_SAMPLE_2} deneme sonra`);
      const mark = text.querySelector('mark')!;
      expect(mark).toHaveTextContent(ARABIC_SAMPLE_2);
      expect(mark).toHaveAttribute('lang', 'ar');
      expect(mark).toHaveAttribute('dir', 'rtl');
      expect(screen.queryByTestId('link-highlight-stale')).not.toBeInTheDocument();
      expect(screen.getByRole('group', { name: trBaglanti.highlight.heading })).toBeInTheDocument();
    });

    it('draws a Turkish sequence as a plain mark', async () => {
      withDetail(
        xrefDetail(1, undefined, undefined, {
          hedef: linkTarget('rn:deneme:p1', 'q:1:2', {
            vurgulu_dizi: { sol: null, dizi: 'deneme dizisi', sag: null },
          }),
        }),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      const text = await screen.findByTestId('link-highlight-text');
      const mark = text.querySelector('mark')!;
      expect(mark).toHaveAttribute('lang', 'tr');
      expect(mark).not.toHaveAttribute('dir');
    });

    it.each([
      ['the whole object is null', null],
      ['all three parts are null', { sol: null, dizi: null, sag: null }],
      ['only the sequence is null', { sol: 'a', dizi: null, sag: 'b' }],
    ])('says "Metin güncel değil" when %s', async (_name, dizi) => {
      withDetail(
        xrefDetail(1, undefined, undefined, {
          hedef: linkTarget('rn:deneme:p1', 'q:1:2', { vurgulu_dizi: dizi }),
        }),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByTestId('link-highlight-stale')).toHaveTextContent(
        trBaglanti.highlight.stale,
      );
      expect(screen.queryByTestId('link-highlight-text')).not.toBeInTheDocument();
    });

    it('draws the evidence summary as one line plus the facts of the candidate', async () => {
      setup(items(1), '/?kayit=1');
      const line = await screen.findByTestId('link-evidence-line');
      expect(line.textContent).toBe(
        [
          'Kapsama %40',
          '7 eşleşen kelime',
          'Âyette 9 kelime',
          "Kur'an'da 1 âyette",
          'açık atıf yok',
          'Konum: govde',
          'Alt tür: deneme-alt-tur',
          'Grup: g1',
        ].join(' · '),
      );
      const facts = screen.getByTestId('link-facts');
      expect(within(facts).getByText(trBaglanti.evidence.type).nextSibling).toHaveTextContent(
        trBaglanti.types.iktibas,
      );
      expect(within(facts).getByText(trBaglanti.evidence.srcSpan).nextSibling).toHaveTextContent(
        '[12, 16)',
      );
      expect(within(facts).getByText(trBaglanti.evidence.dstSpan).nextSibling).toHaveTextContent(
        '[1, 5)',
      );
      expect(within(facts).getByText(trBaglanti.evidence.score).nextSibling).toHaveTextContent(
        '0,91',
      );
      expect(within(facts).getByText(trBaglanti.evidence.confidence).nextSibling).toHaveTextContent(
        '0,97',
      );
    });

    it('says "açık atıf var" for a consistent quotation and says nothing for a missing fact', async () => {
      withDetail(
        xrefDetail(1, undefined, undefined, {
          hedef: linkTarget('rn:deneme:p1', 'q:1:2', {
            evidence_ozeti: { consistent_quote: true, matched_words: 8, editor_duzeltmesi: true },
          }),
        }),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      const line = await screen.findByTestId('link-evidence-line');
      expect(line.textContent).toBe(
        ['8 eşleşen kelime', 'açık atıf var', trBaglanti.evidence.editorFix].join(' · '),
      );
    });

    it.each([
      ['no evidence', null],
      ['an empty summary', {}],
    ])('says there is no evidence summary for %s', async (_name, evidence) => {
      withDetail(
        xrefDetail(1, undefined, undefined, {
          hedef: linkTarget('rn:deneme:p1', 'q:1:2', { evidence_ozeti: evidence }),
        }),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      await screen.findByTestId('link-evidence-summary');
      expect(screen.getByText(trBaglanti.evidence.none)).toBeInTheDocument();
      expect(screen.queryByTestId('link-evidence-line')).not.toBeInTheDocument();
      expect(screen.getByText(trBaglanti.alternatives.none)).toBeInTheDocument();
    });

    it('lists the alternatives as the API gave them (keys as technical names, plain values too)', async () => {
      setup(items(1), '/?kayit=1');
      const rows = await screen.findAllByTestId('link-alternative');
      expect(rows).toHaveLength(2);
      expect(rows[0]).toHaveTextContent(trBaglanti.alternatives.item(1));
      expect(rows[0]).toHaveTextContent('dst: q:1:3');
      expect(rows[0]).toHaveTextContent('matched_words: 5');
      expect(rows[1]).toHaveTextContent(trBaglanti.alternatives.item(2));
      expect(rows[1]).toHaveTextContent('q:1:4');
    });

    it('shows the class badge on the card and leaves no "not in the API yet" placeholder', async () => {
      withDetail(
        xrefDetail(1, undefined, undefined, {
          sinif: 'gri',
        }),
      );
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      await screen.findByTestId('link-card');
      const card = screen.getByTestId('link-card');
      expect(within(card).getByTestId('class-badge')).toHaveTextContent(trBaglanti.classes.gri);
      expect(screen.queryByText(tr.missing.section('A18'))).not.toBeInTheDocument();
    });

    it('decides with the status approval (If-Match = xmin) and sends no edit when nothing was changed', async () => {
      const { user } = setup(items(2), '/?kayit=2');
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(singleCalls()).toHaveLength(1));
      const call = singleCalls()[0]!;
      expect(call.params.id).toBe('2');
      expect(call.headers.get('If-Match')).toBe('"502"');
      expect(call.json).toEqual({ karar: 'onaylandi', duzenlenen: null, gerekce: 'Uygun' });
    });

    it('starts with an empty form for the next record', async () => {
      const { user, router } = setup(items(3), '/?kayit=1');
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Alakasız' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(router.state.location.search).toBe('?kayit=2'));
      await waitFor(() =>
        expect(screen.getByRole('radio', { name: tr.review.reject })).not.toBeChecked(),
      );
      expect(screen.getByLabelText(tr.review.reason)).toHaveValue('');
    });
  });

  describe('closed controls', () => {
    it('has no closed "Açık soru" button left on the card or in the list', async () => {
      setup(items(1), '/?kayit=1');
      await screen.findByText('Deneme paragrafı 1');
      await screen.findByText('Deneme meal metni 1');
      expect(openQuestions()).toHaveLength(0);
    });
  });

  describe('bulk selection', () => {
    it('is open by the constant flag (true since A18.4)', () => {
      expect(BULK_ENABLED).toBe(true);
    });

    it('is open on the real route: a checkbox only on the rows of the "toplu" class, a note says so', async () => {
      // The detail route would also match /reviews/stats, so the session handlers come last.
      xrefHandlers(fake);
      signedIn(fake);
      fake.get(
        '/api/v1/reviews',
        ok(
          page([
            xrefItem(1, { sinif: 'tutarsiz' }),
            xrefItem(2, { sinif: 'toplu' }),
            xrefItem(3, { sinif: 'gri' }),
            xrefItem(4, { sinif: 'toplu' }),
          ]),
        ),
      );
      renderApp(fake, '/kuyruk/baglanti');
      await screen.findAllByRole('link', { name: /00000000/ });
      expect(screen.getAllByRole('checkbox')).toHaveLength(2);
      expect(
        screen.getByRole('checkbox', { name: trBaglanti.selectRow(xrefItem(2).hedef_anahtar) }),
      ).toBeInTheDocument();
      expect(
        screen.queryByRole('checkbox', { name: trBaglanti.selectRow(xrefItem(1).hedef_anahtar) }),
      ).not.toBeInTheDocument();
      expect(screen.getByText(trBaglanti.bulkNote)).toBeInTheDocument();
      expect(openQuestions()).toHaveLength(0);
      expect(screen.queryByTestId('baglanti-bulk')).not.toBeInTheDocument();
    });

    it('shows the class counts and the expert count of the stats in the sidebar, as text', async () => {
      xrefHandlers(fake);
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page(items(1))));
      fake.get(
        '/api/v1/reviews/stats',
        ok(
          stats(
            [['xref', 'status', 8]],
            [
              ['tutarsiz', 3],
              ['toplu', 4],
              ['gri', 0],
              ['diger', 1],
            ],
            2,
          ),
        ),
      );
      renderApp(fake, '/kuyruk/baglanti');
      const line = await screen.findByTestId('sidebar-link-counts');
      expect(line).toHaveTextContent(
        `${trBaglanti.sidebarClasses('Tutarsız 3, Toplu uygun 4, Diğer 1')} · ${trBaglanti.sidebarExpert(2)}`,
      );
    });

    it('shows no count line in the sidebar while every count is zero', async () => {
      xrefHandlers(fake);
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page(items(1))));
      renderApp(fake, '/kuyruk/baglanti');
      await screen.findAllByRole('link', { name: /00000000/ });
      expect(screen.queryByTestId('sidebar-link-counts')).not.toBeInTheDocument();
    });

    it('with the flag off by prop there is no checkbox, no note and no bulk bar', async () => {
      setup(items(3), '/', false);
      await screen.findAllByRole('link');
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
      expect(screen.queryByText(trBaglanti.bulkNote)).not.toBeInTheDocument();
      expect(openQuestions()).toHaveLength(0);
    });

    describe('with the flag on', () => {
      async function selectFirst(user: ReturnType<typeof setup>['user'], count: number) {
        for (let id = 1; id <= count; id++) {
          await user.click(
            await screen.findByRole('checkbox', {
              name: trBaglanti.selectRow(items(count)[id - 1]!.hedef_anahtar),
            }),
          );
        }
      }

      it('gives every "toplu" row a checkbox', async () => {
        setup(items(3), '/', true);
        await screen.findAllByRole('link');
        expect(screen.getAllByRole('checkbox')).toHaveLength(3);
      });

      it('asks for a 10 percent sample: ceil(n/10) rows with the evidence of each', async () => {
        const { user } = setup(items(12), '/', true);
        await selectFirst(user, 11);
        expect(screen.getByTestId('baglanti-bulk')).toHaveTextContent(trBaglanti.selectedCount(11));
        expect(screen.getByTestId('bulk-sample')).toBeInTheDocument();
        const rows = screen.getAllByTestId('bulk-sample-row');
        expect(rows).toHaveLength(2);
        for (const row of rows) {
          expect(await within(row).findByText('Deneme paragrafı 1')).toBeInTheDocument();
          expect(await within(row).findByText(ARABIC_SAMPLE)).toHaveAttribute('lang', 'ar');
          // The sample shows the evidence summary of the record too.
          expect(await within(row).findByTestId('link-evidence-line')).toBeInTheDocument();
        }
      });

      it('sends nothing before the whole sample is judged, then sends the selection once', async () => {
        const { user } = setup(items(12), '/', true);
        await selectFirst(user, 11);
        fireEvent.change(screen.getByLabelText(tr.bulk.reason), {
          target: { value: 'Örneklem temiz' },
        });
        await user.click(screen.getByRole('button', { name: tr.bulk.confirm }));
        expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(
          tr.bulk.verdictPending(0, 2),
        );
        expect(bulkCalls()).toHaveLength(0);
        for (const row of screen.getAllByTestId('bulk-sample-row')) {
          await user.click(within(row).getByRole('radio', { name: tr.bulk.correct }));
        }
        await user.click(screen.getByRole('button', { name: tr.bulk.confirm }));
        await waitFor(() => expect(bulkCalls()).toHaveLength(1));
        const body = bulkCalls()[0]!.json as {
          kararlar: { id: number; xmin: number; karar: string; duzenlenen: unknown }[];
        };
        expect(body.kararlar.map((entry) => entry.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
        expect(body.kararlar.every((entry) => entry.karar === 'onaylandi')).toBe(true);
        expect(body.kararlar.every((entry) => entry.duzenlenen === null)).toBe(true);
        expect(body.kararlar[0]!.xmin).toBe(501);
        await waitFor(() => expect(screen.queryByTestId('baglanti-bulk')).not.toBeInTheDocument());
      });

      it('moves focus to the list region after the bulk approval', async () => {
        const { user } = setup(items(12), '/', true);
        await selectFirst(user, 11);
        fireEvent.change(screen.getByLabelText(tr.bulk.reason), {
          target: { value: 'Örneklem temiz' },
        });
        for (const row of screen.getAllByTestId('bulk-sample-row')) {
          await user.click(within(row).getByRole('radio', { name: tr.bulk.correct }));
        }
        await user.click(screen.getByRole('button', { name: tr.bulk.confirm }));
        await waitFor(() => expect(screen.queryByTestId('baglanti-bulk')).not.toBeInTheDocument());
        expect(screen.getByRole('region', { name: tr.queue.listLabel })).toHaveFocus();
      });

      it('is cancelled by a single "Hatalı"', async () => {
        const { user } = setup(items(12), '/', true);
        await selectFirst(user, 11);
        const rows = screen.getAllByTestId('bulk-sample-row');
        await user.click(within(rows[0]!).getByRole('radio', { name: tr.bulk.correct }));
        await user.click(within(rows[1]!).getByRole('radio', { name: tr.bulk.wrong }));
        expect(await screen.findByTestId('bulk-cancelled')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: tr.bulk.confirm })).toBeDisabled();
        expect(bulkCalls()).toHaveLength(0);
      });

      async function approveSelection(user: ReturnType<typeof setup>['user'], count: number) {
        await selectFirst(user, count);
        fireEvent.change(screen.getByLabelText(tr.bulk.reason), {
          target: { value: 'Örneklem temiz' },
        });
        for (const row of screen.queryAllByTestId('bulk-sample-row')) {
          await user.click(within(row).getByRole('radio', { name: tr.bulk.correct }));
        }
        await user.click(screen.getByRole('button', { name: tr.bulk.confirm }));
      }

      it('shows the 422 toplu-uygun-degil with the record it names, keeps the selection and marks the row', async () => {
        const { user } = setup(items(3), '/', true);
        fake.post(
          '/api/v1/reviews/decisions',
          problem(422, 'toplu-uygun-degil', {
            kimlik: 2,
            detail: "Toplu onay yalniz 'toplu' sinifindaki baglanti adaylarina uygulanir.",
          }),
        );
        await approveSelection(user, 3);
        const summary = await screen.findByText(tr.problem.contexts.bulk['toplu-uygun-degil']);
        expect(summary).toBeInTheDocument();
        expect(screen.getByText(tr.bulk.recordLabel(2))).toBeInTheDocument();
        expect(
          screen.getByText(/Sunucu iletisi: Toplu onay yalniz 'toplu' sinifindaki/),
        ).toBeInTheDocument();
        // The selection is kept: the bulk panel is still there and the three rows stay checked.
        expect(screen.getByTestId('baglanti-bulk')).toBeInTheDocument();
        expect(
          screen.getAllByRole('checkbox').filter((box) => box.hasAttribute('data-checked')),
        ).toHaveLength(3);
        // The named record is marked and left out of the next attempt.
        const marked = screen.getByTestId('bulk-problem-rows');
        expect(marked).toHaveTextContent(xrefItem(2).hedef_anahtar);
        expect(marked).toHaveTextContent(tr.bulk.rowViolation);
        expect(screen.getByTestId('bulk-count')).toHaveTextContent(tr.bulk.count(2));
      });

      it('shows the 403 yetki-yok (a record at the expert) in Turkish and keeps the selection', async () => {
        const { user } = setup(items(3), '/', true);
        fake.post('/api/v1/reviews/decisions', problem(403, 'yetki-yok', { kimlik: 3 }));
        await approveSelection(user, 3);
        expect(await screen.findByText(tr.problem.contexts.bulk['yetki-yok'])).toBeInTheDocument();
        expect(screen.getByText(tr.bulk.recordLabel(3))).toBeInTheDocument();
        expect(screen.getByTestId('baglanti-bulk')).toHaveTextContent(trBaglanti.selectedCount(3));
        expect(bulkCalls()).toHaveLength(1);
      });

      it('keeps the selection when the request fails without naming a record (403)', async () => {
        const { user } = setup(items(3), '/', true);
        fake.post('/api/v1/reviews/decisions', problem(403, 'yetki-yok'));
        await approveSelection(user, 3);
        expect(await screen.findByText(tr.problem.contexts.bulk['yetki-yok'])).toBeInTheDocument();
        expect(screen.getByTestId('baglanti-bulk')).toHaveTextContent(trBaglanti.selectedCount(3));
        expect(screen.getByTestId('bulk-count')).toHaveTextContent(tr.bulk.count(3));
      });
    });
  });
});
