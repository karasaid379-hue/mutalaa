import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import axe from 'axe-core';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trLemma } from '@/i18n/tr-lemma';
import { LemmaQueue } from '@/screens/lemma/lemma-queue';
import { ok, problem, useFakeApi } from './fake-api';
import { page, session, signedIn } from './fixtures';
import {
  KWIC_LEFT,
  KWIC_RIGHT,
  KWIC_WORD,
  LEMMA_ARABIC,
  ROOT_ARABIC,
  SHA_A,
  SHA_B,
  YZ_KAYDI,
  fixDetail,
  fixItem,
  glossDetail,
  glossItem,
  lemmaHandlers,
  lemmaInfo,
  lemmaItem,
  readyGlossDetail,
  readyGlossItem,
} from './fixtures-lemma';
import { renderApp, renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type Detail = components['schemas']['ReviewDetailDto'];

const openQuestions = () => [...document.querySelectorAll<HTMLElement>('[data-open-question]')];

describe('LemmaQueue', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');
  const detailCalls = () => fake.callsTo('get', '/api/v1/reviews/{id}');
  const decisionCalls = () => fake.callsTo('post', '/api/v1/reviews/{id}/decision');

  /** The list answers by the `hedef_tablo` filter; the detail answers by id (below 100 gloss, from 100 lemma). */
  function setup(
    opts: {
      glosses?: Item[];
      lemmas?: Item[];
      fixes?: Item[];
      route?: string;
      detail?: Detail;
      info?: ReturnType<typeof lemmaInfo>;
    } = {},
  ) {
    const glosses = opts.glosses ?? [glossItem(1), glossItem(2)];
    const lemmas = opts.lemmas ?? [lemmaItem(101), lemmaItem(102)];
    const fixes = opts.fixes ?? [fixItem(201), fixItem(202)];
    fake.get('/api/v1/reviews', (call) => {
      const table = call.search.get('hedef_tablo');
      return ok(page(table === 'lemma' ? lemmas : table === 'quran_word_fix' ? fixes : glosses));
    });
    lemmaHandlers(fake, opts.info);
    if (opts.detail) fake.get('/api/v1/reviews/{id}', ok(opts.detail));
    fake.get('/api/v1/auth/me', ok(session()));
    fake.post('/api/v1/reviews/{id}/decision', (call) =>
      ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 900,
      }),
    );
    return renderInRouter(fake, <LemmaQueue />, opts.route ?? '/');
  }

  const card = () => screen.findByTestId('lemma-card');

  describe('list and tabs', () => {
    it('opens on the word meaning drafts: lemma_gloss + anlam_kisa, no cursor, 50 per page', async () => {
      setup();
      await screen.findByRole('link', { name: /^1001/ });
      const first = listCalls()[0]!;
      expect(first.search.has('cursor')).toBe(false);
      expect(first.search.get('hedef_tablo')).toBe('lemma_gloss');
      expect(first.search.get('alan')).toBe('anlam_kisa');
      expect(first.search.get('durum')).toBe('acik');
      expect(first.search.get('limit')).toBe('50');
      // The wave and root order is the default (K-50 madde 7).
      expect(first.search.get('sira')).toBe('dalga');
      expect(screen.getByRole('tab', { name: trLemma.tabs.anlam })).toHaveAttribute(
        'aria-selected',
        'true',
      );
      expect(screen.getByRole('tab', { name: trLemma.tabs.durum })).toHaveAttribute(
        'aria-selected',
        'false',
      );
    });

    it('has three tabs in this order and opens the correction queue without alan and sira', async () => {
      const { user, router } = setup({ route: '/?kayit=201' });
      await screen.findByTestId('fix-card');
      expect(screen.getAllByRole('tab').map((tab) => tab.textContent)).toEqual([
        trLemma.tabs.anlam,
        trLemma.tabs.durum,
        trLemma.tabs.duzeltme,
      ]);
      await user.click(screen.getByRole('tab', { name: trLemma.tabs.duzeltme }));
      await screen.findByRole('link', { name: new RegExp(`^${fixItem(201).hedef_anahtar}`) });
      const last = listCalls().at(-1)!;
      expect(last.search.get('hedef_tablo')).toBe('quran_word_fix');
      expect(last.search.has('alan')).toBe(false);
      expect(last.search.has('sira')).toBe(false);
      expect(last.search.has('cursor')).toBe(false);
      expect(router.state.location.search).toBe('');
      // The order control belongs to the two other tabs only.
      expect(
        screen.queryByRole('radiogroup', { name: trLemma.order.label }),
      ).not.toBeInTheDocument();
      expect(screen.getAllByText(trLemma.list.fix(tr.labels.field.lemma_id))).toHaveLength(2);
    });

    it('offers the order wave | creation; the wave order is selected first', async () => {
      const { user } = setup();
      await screen.findByRole('link', { name: /^1001/ });
      const group = screen.getByRole('radiogroup', { name: trLemma.order.label });
      expect(within(group).getByRole('radio', { name: trLemma.order.dalga })).toBeChecked();
      expect(within(group).getByRole('radio', { name: trLemma.order.olusturma })).not.toBeChecked();
      await user.click(within(group).getByRole('radio', { name: trLemma.order.olusturma }));
      await waitFor(() => expect(listCalls().at(-1)!.search.get('sira')).toBe('olusturma'));
      expect(within(group).getByRole('radio', { name: trLemma.order.olusturma })).toBeChecked();
      // The order stays when the tab changes; the status queue asks in the same order.
      await user.click(screen.getByRole('tab', { name: trLemma.tabs.durum }));
      await screen.findByRole('link', { name: /^2101/ });
      expect(listCalls().at(-1)!.search.get('sira')).toBe('olusturma');
      expect(listCalls().at(-1)!.search.get('hedef_tablo')).toBe('lemma');
    });

    it('starts the cursor over when the order changes (the API cursors are typed by order)', async () => {
      fake.get('/api/v1/reviews', (call) =>
        ok(
          call.search.get('cursor') === null
            ? page([glossItem(1)], `imlec-${call.search.get('sira')}`)
            : page([glossItem(2)]),
        ),
      );
      lemmaHandlers(fake);
      fake.get('/api/v1/auth/me', ok(session()));
      const { user } = renderInRouter(fake, <LemmaQueue />);
      await screen.findByRole('link', { name: /^1001/ });
      await user.click(screen.getByRole('button', { name: tr.ui.loadMore }));
      await screen.findByRole('link', { name: /^1002/ });
      const more = listCalls().at(-1)!;
      expect(more.search.get('cursor')).toBe('imlec-dalga');
      expect(more.search.get('sira')).toBe('dalga');
      await user.click(screen.getByRole('radio', { name: trLemma.order.olusturma }));
      await waitFor(() => expect(listCalls().at(-1)!.search.get('sira')).toBe('olusturma'));
      const reset = listCalls().at(-1)!;
      expect(reset.search.has('cursor')).toBe(false);
      await screen.findByRole('link', { name: /^1001/ });
      expect(screen.queryByRole('link', { name: /^1002/ })).not.toBeInTheDocument();
    });

    it('marks the consistency of a ready candidate in the list (threshold 0,8)', async () => {
      setup({
        glosses: [
          readyGlossItem(1, 0.85),
          readyGlossItem(2, 0.5),
          glossItem(3),
          // An AI draft has a confidence, not a dominant share: no mark in the list.
          glossItem(4, {
            guven: 0.9,
            yz_modeli: 'deneme-model',
            onerilen: { anlam_kisa: 'Deneme' },
          }),
        ],
      });
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      await within(list).findAllByRole('listitem');
      const marks = within(list).getAllByTestId('lemma-item-consistency');
      expect(marks.map((mark) => mark.textContent)).toEqual([
        trLemma.list.line(trLemma.list.consistent, '%85'),
        trLemma.list.line(trLemma.list.inconsistent, '%50'),
      ]);
    });

    it('switches the filter to lemma + status and drops the selected record', async () => {
      const { user, router } = setup({ route: '/?kayit=1' });
      await card();
      await user.click(screen.getByRole('tab', { name: trLemma.tabs.durum }));
      await screen.findByRole('link', { name: /^2101/ });
      const last = listCalls().at(-1)!;
      expect(last.search.get('hedef_tablo')).toBe('lemma');
      expect(last.search.get('alan')).toBe('status');
      expect(last.search.has('cursor')).toBe(false);
      expect(router.state.location.search).toBe('');
      expect(screen.queryByTestId('lemma-card')).not.toBeInTheDocument();
      expect(screen.getByText(tr.queue.selectPrompt)).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: trLemma.tabs.durum })).toHaveAttribute(
        'aria-selected',
        'true',
      );
      // Back to the first tab: the first filter is requested again.
      await user.click(screen.getByRole('tab', { name: trLemma.tabs.anlam }));
      await screen.findByRole('link', { name: /^1001/ });
    });

    it('moves focus with the arrow keys and activates the tab with Enter', async () => {
      const { user } = setup();
      await screen.findByRole('link', { name: /^1001/ });
      screen.getByRole('tab', { name: trLemma.tabs.anlam }).focus();
      await user.keyboard('{ArrowRight}');
      expect(screen.getByRole('tab', { name: trLemma.tabs.durum })).toHaveFocus();
      await user.keyboard('{Enter}');
      await screen.findByRole('link', { name: /^2101/ });
      expect(listCalls().at(-1)!.search.get('hedef_tablo')).toBe('lemma');
    });

    it('shows the empty state', async () => {
      fake.get('/api/v1/reviews', ok(page([])));
      renderInRouter(fake, <LemmaQueue />);
      expect(await screen.findByTestId('queue-empty')).toHaveTextContent(tr.queue.empty);
      expect(screen.getByRole('tab', { name: trLemma.tabs.anlam })).toBeInTheDocument();
    });

    it('shows the problem when the list fails and keeps the tabs', async () => {
      fake.get('/api/v1/reviews', problem(500, 'sunucu-hatasi'));
      renderInRouter(fake, <LemmaQueue />);
      expect(await screen.findByText(tr.queue.loadFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: trLemma.tabs.durum })).toBeInTheDocument();
    });

    it('draws the unverified badge from the API field only', async () => {
      setup({
        glosses: [
          glossItem(1, { dogrulanmamis: true, yz_modeli: 'deneme-model', yz_kaydi: YZ_KAYDI }),
          glossItem(2, { yz_modeli: 'deneme-model', yz_kaydi: YZ_KAYDI, dogrulanmamis: false }),
        ],
      });
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      await within(list).findAllByRole('listitem');
      expect(within(list).getAllByText(tr.badge.unverified)).toHaveLength(1);
    });
  });

  describe('the card of a word meaning draft', () => {
    it('shows the snapshot, the proposed value, the origin and the unverified badge (K-25)', async () => {
      setup({
        route: '/?kayit=1',
        detail: glossDetail(1, {
          dogrulanmamis: true,
          yz_modeli: 'deneme-model',
          yz_kaydi: YZ_KAYDI,
          guven: 0.87,
          onerilen: {
            anlam_kisa: 'Deneme anlam 1',
            kuran_anlamlari: ['Deneme madde 1', 'Deneme madde 2'],
            turkce_es_kelime: 'Deneme-kelime',
            emin_degil: true,
            yalnizca_etimolojik_adayi: true,
            dayanak_ayetler: ['q:1:2', 'bozuk'],
            gerekce: 'Deneme gerekçe',
          },
        }),
      });
      const root = await card();
      expect(
        within(root).getByRole('heading', { level: 2, name: trLemma.heading.anlam }),
      ).toBeInTheDocument();
      expect(within(root).getByText(tr.badge.unverified)).toBeInTheDocument();

      const snapshot = within(root).getByTestId('lemma-snapshot');
      expect(snapshot).toHaveTextContent(`${trLemma.snapshot.lemmaId}1001`);
      expect(snapshot).toHaveTextContent('Deneme anlam 1');
      expect(snapshot).toHaveTextContent(`${trLemma.snapshot.status}Aday`);

      const values = within(root).getByTestId('lemma-values');
      expect(
        within(values).getByRole('heading', { name: trLemma.values.onerilen }),
      ).toBeInTheDocument();
      expect(
        within(values).queryByRole('heading', { name: trLemma.values.onceki }),
      ).not.toBeInTheDocument();
      expect(
        within(values).queryByRole('heading', { name: trLemma.values.duzenlenen }),
      ).not.toBeInTheDocument();
      expect(values).toHaveTextContent('Deneme madde 2');
      expect(values).toHaveTextContent('Deneme-kelime');
      expect(values).toHaveTextContent('Deneme gerekçe');
      expect(within(values).getByText(trLemma.values.eminDegil)).toBeInTheDocument();
      expect(within(values).getByText(trLemma.values.etimolojikAday)).toBeInTheDocument();
      expect(values).toHaveTextContent(`q:1:2`);
      expect(values).toHaveTextContent(`bozuk (${trLemma.values.notAnchor})`);
      expect(values.textContent).not.toContain('q:1:2 (');

      const origin = within(root).getByTestId('lemma-origin');
      expect(origin).toHaveTextContent(`${trLemma.origin.origin}İçerik hattı`);
      expect(origin).toHaveTextContent('deneme-model');
      expect(origin).toHaveTextContent('deneme-istem-v1');
      expect(origin).toHaveTextContent(SHA_A);
      expect(origin).toHaveTextContent(SHA_B);
      // An AI draft carries a plain "Güven": no dominant share label and no consistency mark.
      expect(origin).toHaveTextContent(`${trLemma.origin.confidence}%87`);
      expect(origin).not.toHaveTextContent(trLemma.origin.dominantShare);
      expect(within(root).queryByTestId('lemma-consistency')).not.toBeInTheDocument();
      expect(origin).toHaveTextContent(trLemma.origin.unverifiedNote);
      // The confidence is present, so no "no confidence" note.
      expect(within(root).queryByTestId('lemma-confidence-none')).not.toBeInTheDocument();
    });

    it('shows the previous value and the word difference when the meaning changes', async () => {
      setup({
        route: '/?kayit=1',
        detail: glossDetail(1, {
          eylem: 'oner',
          onceki: { anlam_kisa: 'Deneme eski anlam' },
          onerilen: { anlam_kisa: 'Deneme yeni anlam' },
          duzenlenen: { anlam_kisa: 'Deneme düzenlenen anlam' },
        }),
      });
      const values = await screen.findByTestId('lemma-values');
      for (const name of [
        trLemma.values.onceki,
        trLemma.values.onerilen,
        trLemma.values.duzenlenen,
      ]) {
        expect(within(values).getByRole('heading', { name })).toBeInTheDocument();
      }
      const diff = within(values).getByTestId('text-diff');
      expect(diff.querySelector('del')?.textContent).toMatch(/eski/);
      expect(diff.querySelector('ins')?.textContent).toMatch(/yeni/);
    });

    it('says so when neither the API nor the payload carries a confidence (no "not in the API" note)', async () => {
      setup({ route: '/?kayit=1', detail: glossDetail(1, { guven: null }) });
      const root = await card();
      expect(within(root).getByTestId('lemma-confidence-none')).toHaveTextContent(
        trLemma.origin.confidenceNone,
      );
      expect(within(root).getByTestId('lemma-origin')).not.toHaveTextContent(
        trLemma.origin.confidence,
      );
      expect(root.textContent).not.toContain("API'de henüz yok");
      expect(within(root).queryByTestId('lemma-consistency')).not.toBeInTheDocument();
    });

    it('says the confidence is unreadable when it is not between 0 and 1, with no consistency mark', async () => {
      setup({ route: '/?kayit=1', detail: readyGlossDetail(1, {}, 1.5) });
      const root = await card();
      expect(within(root).getByTestId('lemma-confidence-unreadable')).toHaveTextContent(
        trLemma.origin.shareUnreadable,
      );
      expect(within(root).queryByTestId('lemma-consistency')).not.toBeInTheDocument();
      expect(within(root).getByTestId('lemma-origin')).not.toHaveTextContent('%150');
    });

    it('reads the confidence from the G-YZ record or the payload when the field is empty', async () => {
      setup({
        route: '/?kayit=1',
        detail: glossDetail(1, {
          guven: null,
          yz_modeli: 'deneme-model',
          yz_kaydi: { ...YZ_KAYDI, guven: 0.25 },
        }),
      });
      const origin = await screen.findByTestId('lemma-origin');
      expect(origin).toHaveTextContent(`${trLemma.origin.confidence}%25`);
      expect(screen.queryByTestId('lemma-confidence-none')).not.toBeInTheDocument();
    });

    it('shows a value with no known field as raw JSON and says so', async () => {
      setup({ route: '/?kayit=1', detail: glossDetail(1, { onerilen: { baska_alan: 'Deneme' } }) });
      const values = await screen.findByTestId('lemma-values');
      expect(values).toHaveTextContent(trLemma.values.unreadable);
      expect(within(values).getByText(trLemma.values.raw)).toBeInTheDocument();
      expect(values).toHaveTextContent('"baska_alan": "Deneme"');
    });

    it('shows a plain string value as it is', async () => {
      setup({ route: '/?kayit=1', detail: glossDetail(1, { onerilen: 'Deneme düz anlam' }) });
      const values = await screen.findByTestId('lemma-values');
      expect(values).toHaveTextContent('Deneme düz anlam');
      expect(values).not.toHaveTextContent(trLemma.values.unreadable);
    });

    it('says so when the record has no values and no snapshot', async () => {
      setup({
        route: '/?kayit=1',
        detail: glossDetail(1, { onceki: null, onerilen: null, duzenlenen: null, hedef: null }),
      });
      const root = await card();
      expect(within(root).getByText(trLemma.values.none)).toBeInTheDocument();
      expect(within(root).getByText(trLemma.snapshot.missing)).toBeInTheDocument();
    });

    it('shows a ready-source candidate: origin row, dominant share, consistent mark and the distribution', async () => {
      setup({ route: '/?kayit=1', detail: readyGlossDetail(1) });
      const root = await card();
      // A ready source has no AI model: no unverified badge, the origin row tells where it comes from.
      expect(within(root).queryByText(tr.badge.unverified)).not.toBeInTheDocument();
      expect(within(root).getByTestId('lemma-snapshot')).toHaveTextContent(
        `${trLemma.snapshot.origin}${trLemma.snapshot.readySource('deneme-kaynak')}`,
      );
      expect(within(root).getByTestId('lemma-snapshot')).toHaveTextContent(
        `${trLemma.snapshot.version}1`,
      );
      const origin = within(root).getByTestId('lemma-origin');
      expect(origin).toHaveTextContent(`${trLemma.origin.dominantShare}%85`);
      const mark = within(root).getByTestId('lemma-consistency');
      expect(mark).toHaveTextContent(trLemma.origin.consistent);
      expect(mark).toHaveTextContent('%80 ve üstü tutarlı sayılır');
      const distribution = within(root).getByTestId('lemma-distribution');
      expect(
        within(distribution).getByRole('heading', { name: trLemma.origin.distribution }),
      ).toBeInTheDocument();
      expect(distribution).toHaveTextContent(trLemma.origin.distributionNote);
      expect(distribution).toHaveTextContent(
        `Deneme anlam 1${trLemma.origin.distributionEntry(17)}`,
      );
      expect(distribution).toHaveTextContent(
        `Deneme öteki anlam${trLemma.origin.distributionEntry(3)}`,
      );
    });

    it('marks a share under the threshold as an inconsistent ready meaning', async () => {
      setup({ route: '/?kayit=1', detail: readyGlossDetail(1, {}, 0.5) });
      const mark = await screen.findByTestId('lemma-consistency');
      expect(mark).toHaveTextContent(trLemma.origin.inconsistent);
      expect(mark).not.toHaveTextContent(`${trLemma.origin.consistent}`);
    });

    it('names an editor value in the origin row of the snapshot', async () => {
      setup({
        route: '/?kayit=1',
        detail: readyGlossDetail(1, {
          hedef: {
            tablo: 'lemma_gloss',
            lemma_id: 1001,
            origin: 'editor',
            version: '2',
            status: 'onayli',
          },
        }),
      });
      const root = await card();
      expect(within(root).getByTestId('lemma-snapshot')).toHaveTextContent(
        `${trLemma.snapshot.origin}${trLemma.snapshot.originNames.editor}`,
      );
    });
  });

  describe('the lemma card sections (GET /lemmas/{id})', () => {
    it('requests the lemma of the target and shows root, type, frequency, wave, same root and KWIC', async () => {
      setup({ route: '/?kayit=1' });
      const info = await screen.findByTestId('lemma-info');
      await screen.findByTestId('lemma-root');
      expect(fake.callsTo('get', '/api/v1/lemmas/{id}')[0]!.params.id).toBe('1001');

      const rootSection = within(info).getByTestId('lemma-root');
      const letters = within(rootSection).getByText(ROOT_ARABIC);
      expect(letters).toHaveAttribute('lang', 'ar');
      expect(letters).toHaveAttribute('dir', 'rtl');
      // The Buckwalter spelling is a technical, secondary, left to right value.
      const bw = within(rootSection).getByText('xyz');
      expect(bw).toHaveAttribute('dir', 'ltr');
      expect(rootSection).toHaveTextContent(`${trLemma.info.root.occurrences}120`);
      expect(rootSection).toHaveTextContent(`${trLemma.info.root.ayahs}80`);
      expect(rootSection).toHaveTextContent(`${trLemma.info.root.idf}1,23`);
      expect(rootSection).toHaveTextContent('Deneme kök anlamı');

      const pos = within(info).getByTestId('lemma-pos');
      expect(pos).toHaveTextContent(`N${trLemma.info.pos.count(30)}`);
      expect(pos).toHaveTextContent(`${trLemma.info.pos.unknown}${trLemma.info.pos.count(2)}`);

      const frequency = within(info).getByTestId('lemma-frequency');
      expect(frequency).toHaveTextContent(`${trLemma.info.frequency.words}42`);
      expect(frequency).toHaveTextContent(`${trLemma.info.frequency.ayahs}35`);

      expect(within(info).getByTestId('lemma-wave')).toHaveTextContent(
        trLemma.info.wave.value(1, 3),
      );

      const sameRoot = within(info).getByTestId('lemma-same-root');
      expect(sameRoot).toHaveTextContent('Deneme kardeş anlam');
      expect(sameRoot).toHaveTextContent(trLemma.info.sameRoot.count(9));
      expect(within(sameRoot).getByText(LEMMA_ARABIC)).toHaveAttribute('dir', 'rtl');
    });

    it('draws the KWIC context in Arabic as stored, with the meal status (draft = unverified)', async () => {
      setup({ route: '/?kayit=1' });
      const kwic = await screen.findByTestId('lemma-kwic');
      const item = within(kwic).getByTestId('lemma-kwic-item');
      const line = item.querySelector('p[lang="ar"]')!;
      expect(line).toHaveAttribute('dir', 'rtl');
      expect(line.textContent).toBe(`${KWIC_LEFT}${KWIC_WORD}${KWIC_RIGHT}`);
      expect(line.querySelector('mark')?.textContent).toBe(KWIC_WORD);
      expect(item).toHaveTextContent('q:1:1:1');
      const meal = within(item).getByTestId('lemma-kwic-meal');
      expect(meal).toHaveTextContent(trLemma.info.kwic.mealStatus.taslak);
      expect(meal).toHaveTextContent('Deneme meal metni 1');
      expect(meal.querySelector('p')).toHaveAttribute('lang', 'tr');
    });

    it('shows an approved meal as approved and marks an unknown status raw and unverified', async () => {
      const base = lemmaInfo().kwic[0]!;
      setup({
        route: '/?kayit=1',
        info: lemmaInfo({
          kwic: [
            { ...base, kelime_capa: 'q:1:1:1', meal: { ...base.meal!, metin_durumu: 'onayli' } },
            {
              ...base,
              kelime_capa: 'q:1:1:2',
              meal: { ...base.meal!, metin_durumu: 'yeni-durum' },
            },
          ],
        }),
      });
      const kwic = await screen.findByTestId('lemma-kwic');
      const [approved, unknown] = within(kwic).getAllByTestId('lemma-kwic-meal');
      expect(approved).toHaveTextContent(trLemma.info.kwic.mealStatus.onayli);
      expect(approved).not.toHaveTextContent(trLemma.info.kwic.mealUnverified);
      expect(unknown).toHaveTextContent('yeni-durum');
      expect(unknown).toHaveTextContent(trLemma.info.kwic.mealUnverified);
    });

    it('omits the meal when it is null and says the text is unreadable when the three parts are null', async () => {
      const base = lemmaInfo().kwic[0]!;
      setup({
        route: '/?kayit=1',
        info: lemmaInfo({ kwic: [{ ...base, sol: null, kelime: null, sag: null, meal: null }] }),
      });
      const item = await screen.findByTestId('lemma-kwic-item');
      expect(within(item).queryByTestId('lemma-kwic-meal')).not.toBeInTheDocument();
      expect(within(item).getByTestId('lemma-kwic-no-meal')).toHaveTextContent(
        trLemma.info.kwic.noMeal,
      );
      expect(item.querySelector('[lang="ar"]')).toBeNull();
      expect(item).toHaveTextContent(trLemma.info.kwic.textMissing);
    });

    it('says "Veri yok" for null and empty data, not an error', async () => {
      setup({
        route: '/?kayit=1',
        info: lemmaInfo({
          kok: null,
          tur_dagilimi: [],
          dalga: null,
          ayni_kok_anlamlari: [],
          kwic: [],
        }),
      });
      const info = await screen.findByTestId('lemma-info');
      await screen.findByTestId('lemma-kwic');
      expect(within(info).getByTestId('lemma-root')).toHaveTextContent(trLemma.info.root.none);
      for (const id of ['lemma-pos', 'lemma-wave', 'lemma-same-root', 'lemma-kwic']) {
        expect(within(info).getByTestId(id)).toHaveTextContent(trLemma.info.noData);
      }
      // The frequency is always real numbers.
      expect(within(info).getByTestId('lemma-frequency')).toBeInTheDocument();
      expect(within(info).queryByRole('alert')).not.toBeInTheDocument();
    });

    it('shows the problem when the lemma card cannot be loaded; the rest of the card stays', async () => {
      setup({ route: '/?kayit=1' });
      fake.get('/api/v1/lemmas/{id}', problem(404, 'bulunamadi'));
      const root = await card();
      expect(await within(root).findByText(trLemma.info.failed)).toBeInTheDocument();
      expect(within(root).getByTestId('lemma-snapshot')).toBeInTheDocument();
      expect(within(root).getByRole('button', { name: tr.review.submit })).toBeInTheDocument();
    });

    it('asks no lemma card when the review has no lemma id', async () => {
      setup({
        route: '/?kayit=1',
        detail: glossDetail(1, { hedef: null, hedef_anahtar: 'bozuk' }),
      });
      const root = await card();
      expect(within(root).getByTestId('lemma-info')).toHaveTextContent(trLemma.info.noId);
      expect(fake.callsTo('get', '/api/v1/lemmas/{id}')).toHaveLength(0);
    });

    it('offers a retry on a failed lemma card and loads it again', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      fake.get('/api/v1/lemmas/{id}', problem(500, 'sunucu-hatasi'));
      const root = await card();
      await within(root).findByText(trLemma.info.failed);
      fake.get('/api/v1/lemmas/{id}', ok(lemmaInfo()));
      await user.click(within(root).getByRole('button', { name: tr.ui.retry }));
      await within(root).findByTestId('lemma-root');
      expect(within(root).queryByText(trLemma.info.failed)).not.toBeInTheDocument();
    });

    it('marks the loading card busy without a second live region', async () => {
      let release: () => void = () => {};
      const gate = new Promise<void>((resolve) => {
        release = resolve;
      });
      setup({ route: '/?kayit=1' });
      fake.get('/api/v1/lemmas/{id}', async () => {
        await gate;
        return ok(lemmaInfo());
      });
      const info = await screen.findByTestId('lemma-info');
      expect(info).toHaveAttribute('aria-busy', 'true');
      expect(within(info).getByTestId('lemma-info-loading').querySelector('[role]')).toBeNull();
      release();
      await within(info).findByTestId('lemma-root');
      expect(info).toHaveAttribute('aria-busy', 'false');
    });

    it('has no placeholder left on the card', async () => {
      setup({ route: '/?kayit=1' });
      const root = await card();
      await screen.findByTestId('lemma-kwic');
      expect(root.textContent).not.toContain("API'de henüz yok");
    });
  });

  describe('edit and approve (lemma_gloss)', () => {
    const field = () => screen.getByLabelText(trLemma.edit.label);
    const approve = async (user: ReturnType<typeof setup>['user']) => {
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
    };
    const reason = (value = 'Uygun') =>
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value } });
    const submit = (user: ReturnType<typeof setup>['user']) =>
      user.click(screen.getByRole('button', { name: tr.review.submit }));

    it('shows the field only on approval of a word meaning, filled with the proposal and a counter', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await card();
      expect(screen.queryByLabelText(trLemma.edit.label)).not.toBeInTheDocument();
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      expect(screen.queryByLabelText(trLemma.edit.label)).not.toBeInTheDocument();
      await approve(user);
      expect(field()).toHaveValue('Deneme anlam 1');
      expect(field()).toHaveAttribute('lang', 'tr');
      expect(screen.getByText(new RegExp(trLemma.edit.count(14, 200)))).toBeInTheDocument();
      // It does not replace the meal-text field of the unit review.
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      expect(fake.callsTo('get', '/api/v1/units/{anchor}')).toHaveLength(0);
    });

    it('sends the edited meaning as duzenlenen.anlam_kisa', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme yeni anlam' } });
      reason('Daha doğru');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { anlam_kisa: 'Deneme yeni anlam' },
        gerekce: 'Daha doğru',
      });
    });

    it('sends a plain approval when the text equals the proposal (also with spaces around it)', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: '  Deneme anlam 2 ' } });
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Uygun',
      });
    });

    it('does not send an edit with a rejection even after the field was changed', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme yeni anlam' } });
      await user.click(screen.getByRole('radio', { name: tr.review.reject }));
      reason('Uygun değil');
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'reddedildi',
        duzenlenen: null,
        gerekce: 'Uygun değil',
      });
    });

    it('refuses an empty meaning next to the field and sends nothing', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: '   ' } });
      reason();
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(field()).toHaveAttribute('aria-invalid', 'true');
      expect(screen.getAllByText(trLemma.edit.empty).length).toBeGreaterThanOrEqual(2);
      expect(screen.getByTestId('gloss-edit')).toHaveTextContent(trLemma.edit.empty);
      await waitFor(() =>
        expect(screen.getByTestId('decision-summary').parentElement).toHaveFocus(),
      );
    });

    it('counts code points, not UTF-16 units: 200 astral letters pass, 201 do not', async () => {
      const astral = String.fromCodePoint(0x1d7d8);
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: astral.repeat(201) } });
      reason();
      expect(screen.getByText(new RegExp(trLemma.edit.count(201, 200)))).toBeInTheDocument();
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(screen.getByTestId('gloss-edit')).toHaveTextContent(trLemma.edit.tooLong(201, 200));

      fireEvent.change(field(), { target: { value: astral.repeat(200) } });
      expect(screen.getByText(new RegExp(trLemma.edit.count(200, 200)))).toBeInTheDocument();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toEqual({
        karar: 'onaylandi',
        duzenlenen: { anlam_kisa: astral.repeat(200) },
        gerekce: 'Uygun',
      });
    });

    it('warns about NUL in the meaning and sends nothing', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme\u0000anlam' } });
      reason();
      expect(screen.getByTestId('unwritable-warning')).toBeInTheDocument();
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(screen.getByTestId('gloss-edit')).toHaveTextContent(trLemma.edit.unwritable);
    });

    it('shows a 400 dogrulama on the meaning field in Turkish and keeps the input', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme yeni anlam' } });
      reason();
      fake.post(
        '/api/v1/reviews/{id}/decision',
        problem(400, 'dogrulama', { errors: { 'duzenlenen.anlam_kisa': ['sunucu iletisi'] } }),
      );
      await submit(user);
      await waitFor(() =>
        expect(screen.getByTestId('gloss-edit')).toHaveTextContent(trLemma.edit.serverInvalid),
      );
      expect(field()).toHaveAttribute('aria-invalid', 'true');
      expect(field()).toHaveValue('Deneme yeni anlam');
      expect(screen.getByLabelText(tr.review.reason)).toHaveValue('Uygun');
    });

    it('shows a 409 next to the field (the target is not a candidate)', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'Deneme yeni anlam' } });
      reason();
      fake.post('/api/v1/reviews/{id}/decision', problem(409, 'durum-gecisi-gecersiz'));
      await submit(user);
      await waitFor(() =>
        expect(screen.getByTestId('gloss-edit')).toHaveTextContent(trLemma.edit.notCandidate),
      );
      expect(field()).toHaveValue('Deneme yeni anlam');
    });

    it('shows a 409 of a plain approval as the usual decision problem, not on the field', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      reason();
      fake.post('/api/v1/reviews/{id}/decision', problem(409, 'durum-gecisi-gecersiz'));
      await submit(user);
      await screen.findByText(tr.problem.contexts.decision['durum-gecisi-gecersiz']);
      expect(screen.getByTestId('gloss-edit')).not.toHaveTextContent(trLemma.edit.notCandidate);
    });

    it('has no meaning field on a lemma status review', async () => {
      const { user } = setup({ route: '/?kayit=101' });
      await card();
      await approve(user);
      expect(screen.queryByLabelText(trLemma.edit.label)).not.toBeInTheDocument();
      expect(screen.getByText(trLemma.decisionNote.durum)).toBeInTheDocument();
    });

    it('measures the meaning as the server does: trailing space ignored, NFC counted, the sent text unchanged', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      // 200 letters and a trailing space: 200 after the trim, so it passes; it is sent as typed.
      const padded = 'a'.repeat(200) + ' ';
      fireEvent.change(field(), { target: { value: padded } });
      reason();
      expect(screen.getByText(new RegExp(trLemma.edit.count(200, 200)))).toBeInTheDocument();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toMatchObject({ duzenlenen: { anlam_kisa: padded } });
    });

    it('counts a decomposed (NFD) meaning in NFC: 150 letter + combining mark pairs are 150, not 300', async () => {
      const decomposed = (String.fromCodePoint(0x65) + String.fromCodePoint(0x301)).repeat(150);
      expect(decomposed.length).toBe(300);
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: decomposed } });
      reason();
      expect(screen.getByText(new RegExp(trLemma.edit.count(150, 200)))).toBeInTheDocument();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      // No client normalization: the value goes out in the form it was typed.
      expect(decisionCalls()[0]!.json).toMatchObject({ duzenlenen: { anlam_kisa: decomposed } });
    });

    it('refuses 201 NFC code points even when a trailing space is added', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: 'a'.repeat(201) + ' ' } });
      reason();
      await submit(user);
      expect(decisionCalls()).toHaveLength(0);
      expect(screen.getByTestId('gloss-edit')).toHaveTextContent(trLemma.edit.tooLong(201, 200));
    });

    it('treats a text that differs from the proposal only by tab or line feed at the ends as unchanged', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      const edited = String.fromCodePoint(9) + 'Deneme anlam 2' + String.fromCodePoint(10);
      fireEvent.change(field(), { target: { value: edited } });
      reason();
      await submit(user);
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      expect(decisionCalls()[0]!.json).toMatchObject({ duzenlenen: null });
    });

    it('ties the inline error to the field (aria-describedby) once, and keeps the summary link', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      fireEvent.change(field(), { target: { value: '   ' } });
      reason();
      await submit(user);
      const inline = screen.getByTestId('gloss-edit').querySelector('div[id]')!;
      expect(inline).toHaveTextContent(trLemma.edit.empty);
      const described = field().getAttribute('aria-describedby')!.split(' ');
      expect(described).toContain(inline.id);
      // The summary ids are not repeated on the field; the summary still links to it.
      const summary = screen.getByTestId('decision-summary');
      for (const li of summary.querySelectorAll('li[id]')) expect(described).not.toContain(li.id);
      await user.click(within(summary).getByRole('link', { name: trLemma.edit.empty }));
      expect(field()).toHaveFocus();
    });

    it('sends the keyboard shortcut from the meaning field too', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await approve(user);
      reason();
      field().focus();
      await user.keyboard('{Control>}{Enter}{/Control}');
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
    });
  });

  describe('the card of a correction (quran_word_fix)', () => {
    it('shows anchor, field, QAC value, new value, reason and editor; technical values read left to right', async () => {
      setup({ route: '/?kayit=201' });
      const root = await screen.findByTestId('fix-card');
      expect(
        within(root).getByRole('heading', { level: 2, name: trLemma.heading.duzeltme }),
      ).toBeInTheDocument();
      const snap = within(root).getByTestId('fix-snapshot');
      expect(within(snap).getByText('q:1:1:1')).toHaveAttribute('dir', 'ltr');
      expect(snap).toHaveTextContent(`${trLemma.fix.field}${tr.labels.field.lemma_id}`);
      // A technical value (an id) reads left to right; Arabic letters are Arabic text in the Quran font.
      const qac = within(snap).getByTestId('fix-qac-value');
      expect(qac).toHaveTextContent('1001');
      expect(qac).toHaveAttribute('dir', 'ltr');
      expect(qac).not.toHaveAttribute('lang', 'ar');
      const newValue = within(snap).getByTestId('fix-new-value');
      expect(newValue).toHaveAttribute('lang', 'ar');
      expect(newValue).toHaveAttribute('dir', 'rtl');
      expect(newValue).toHaveClass('font-quran');
      expect(newValue.textContent).toBe(LEMMA_ARABIC);
      expect(within(snap).getByText('Deneme düzeltme gerekçesi')).toHaveAttribute('lang', 'tr');
      expect(snap).toHaveTextContent(`${trLemma.fix.editor}editor@deneme.test`);
      expect(snap).toHaveTextContent(`${trLemma.fix.status}Aday`);
      expect(within(snap).queryByTestId('fix-mismatch')).not.toBeInTheDocument();
    });

    it('has approval and rejection only: no edit fields, no closed actions, no lemma card request', async () => {
      const { user } = setup({ route: '/?kayit=201' });
      const root = await screen.findByTestId('fix-card');
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      expect(screen.queryByLabelText(trLemma.edit.label)).not.toBeInTheDocument();
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      expect(openQuestions()).toHaveLength(0);
      expect(within(root).getByText(trLemma.fix.note)).toBeInTheDocument();
      expect(fake.callsTo('get', '/api/v1/lemmas/{id}')).toHaveLength(0);
      expect(fake.callsTo('get', '/api/v1/units/{anchor}')).toHaveLength(0);
    });

    it('decides with If-Match = xmin and an empty edit', async () => {
      const { user } = setup({ route: '/?kayit=201' });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Doğru' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.headers.get('If-Match')).toBe('"701"');
      expect(call.json).toEqual({ karar: 'onaylandi', duzenlenen: null, gerekce: 'Doğru' });
    });

    it('warns when the review field differs from the correction field', async () => {
      setup({ route: '/?kayit=201', detail: fixDetail(201, { alan: 'pos' }) });
      const snap = await screen.findByTestId('fix-snapshot');
      expect(within(snap).getByTestId('fix-mismatch')).toHaveTextContent(trLemma.fix.mismatch);
    });

    it('says so when the snapshot is missing', async () => {
      setup({ route: '/?kayit=201', detail: fixDetail(201, { hedef: null }) });
      expect(await screen.findByText(trLemma.fix.missing)).toBeInTheDocument();
    });
  });

  describe('the card of a lemma status review', () => {
    it('shows the Arabic lemma as stored (lang, dir) and the target status label', async () => {
      setup({ route: '/?kayit=101' });
      const root = await card();
      expect(
        within(root).getByRole('heading', { level: 2, name: trLemma.heading.durum }),
      ).toBeInTheDocument();
      const arabic = within(within(root).getByTestId('lemma-snapshot')).getByText(LEMMA_ARABIC);
      expect(arabic).toHaveAttribute('lang', 'ar');
      expect(arabic).toHaveAttribute('dir', 'rtl');
      expect(arabic.textContent).toBe(LEMMA_ARABIC);
      const values = within(root).getByTestId('lemma-values');
      expect(values).toHaveTextContent(`${trLemma.values.status}Onaylı`);
      expect(within(root).getByTestId('lemma-snapshot')).toHaveTextContent(
        `${trLemma.snapshot.status}Aday`,
      );
    });
  });

  describe('closed actions', () => {
    it('lists the three closed actions: expert and etymological A18, redraft S-16 (edit and approve is a working form now)', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      const expected: [string, string][] = [
        [trLemma.closed.sendExpert, 'A18'],
        [trLemma.closed.redraft, 'S-16'],
        [trLemma.closed.etymologicalOnly, 'A18'],
      ];
      for (const [label, phase] of expected) {
        expect(
          screen.getByRole('button', { name: `${label} · ${tr.openQuestion(phase)}` }),
        ).toHaveAttribute('data-open-question', phase);
      }
      expect(openQuestions()).toHaveLength(3);
      expect(
        screen.getByRole('button', { name: 'Yeniden taslak iste · Açık soru: S-16' }),
      ).toBeInTheDocument();
      expect(screen.getByText(trLemma.closedNote)).toHaveTextContent('BÇ-61');
      expect(screen.getByText(trLemma.closedNote)).toHaveTextContent('S-16');
      expect(trLemma.closed.sendExpert).toBe('Uzmana gönder');
      expect(trLemma.closed.redraft).toBe('Yeniden taslak iste');
      expect(trLemma.closed.etymologicalOnly).toBe('Yalnızca etimolojik');
    });

    it('sends no request when a closed button is clicked', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await card();
      const before = fake.calls.length;
      for (const button of openQuestions()) await user.click(button);
      expect(fake.calls.length).toBe(before);
      expect(decisionCalls()).toHaveLength(0);
    });

    it('has no unit text field, and no unit is requested; the note names the meaning edit', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      expect(fake.callsTo('get', '/api/v1/units/{anchor}')).toHaveLength(0);
      expect(screen.getByText(trLemma.decisionNote.anlam)).toBeInTheDocument();
    });

    it('keeps no phase A17 button anywhere on the cards', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      expect(document.querySelector('[data-open-question="A17"]')).toBeNull();
    });
  });

  describe('decision', () => {
    it('approves with If-Match = xmin and the body {karar, duzenlenen, gerekce}', async () => {
      const { user } = setup({ route: '/?kayit=2' });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.params.id).toBe('2');
      expect(call.headers.get('If-Match')).toBe('"302"');
      expect(call.json).toEqual({ karar: 'onaylandi', duzenlenen: null, gerekce: 'Uygun' });
    });

    it('rejects a lemma status review and opens the next record', async () => {
      const { user, router } = setup({ route: '/?kayit=101' });
      await user.click(await screen.findByRole('tab', { name: trLemma.tabs.durum }));
      await screen.findByRole('link', { name: /^2101/ });
      // The tab dropped the selection: pick the record again.
      await user.click(screen.getByRole('link', { name: /^2101/ }));
      await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), {
        target: { value: 'Uygun değil' },
      });
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await waitFor(() => expect(decisionCalls()).toHaveLength(1));
      const call = decisionCalls()[0]!;
      expect(call.headers.get('If-Match')).toBe('"501"');
      expect(call.json).toEqual({ karar: 'reddedildi', duzenlenen: null, gerekce: 'Uygun değil' });
      await waitFor(() => expect(router.state.location.search).toBe('?kayit=102'));
    });

    it('needs a reason: nothing is sent without it', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      expect(decisionCalls()).toHaveLength(0);
    });

    it('after a 412 shows the fresh record on the card and keeps the input', async () => {
      const { user } = setup({ route: '/?kayit=1' });
      await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
      fireEvent.change(screen.getByLabelText(tr.review.reason), { target: { value: 'Uygun' } });
      fake.post('/api/v1/reviews/{id}/decision', problem(412, 'surum-uyusmazligi'));
      fake.get(
        '/api/v1/reviews/{id}',
        ok(
          glossDetail(1, {
            xmin: 999,
            onerilen: { anlam_kisa: 'Deneme değişen anlam' },
          }),
        ),
      );
      await user.click(screen.getByRole('button', { name: tr.review.submit }));
      await screen.findByTestId('stale-record');
      const values = screen.getByTestId('lemma-values');
      await waitFor(() => expect(values).toHaveTextContent('Deneme değişen anlam'));
      expect(decisionCalls()).toHaveLength(1);
      expect(screen.getByLabelText(tr.review.reason)).toHaveValue('Uygun');
    });
  });

  describe('detail errors', () => {
    it('shows the problem when the record cannot be loaded; the list stays', async () => {
      fake.get('/api/v1/reviews', ok(page([glossItem(1)])));
      fake.get('/api/v1/reviews/{id}', problem(404, 'bulunamadi'));
      fake.get('/api/v1/auth/me', ok(session()));
      renderInRouter(fake, <LemmaQueue />, '/?kayit=1');
      expect(await screen.findByText(tr.queue.detailFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
      expect(screen.getByRole('link', { name: /^1001/ })).toBeInTheDocument();
      expect(detailCalls()).toHaveLength(1);
    });
  });

  describe('route', () => {
    it('opens at /kuyruk/lemma with the screen title as the only h1 and both tabs', async () => {
      lemmaHandlers(fake);
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page([glossItem(1)])));
      renderApp(fake, '/kuyruk/lemma');
      expect(
        await screen.findByRole('heading', { level: 1, name: tr.nav.queueLemma }),
      ).toBeInTheDocument();
      expect(await screen.findByRole('link', { name: /^1001/ })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: trLemma.tabs.anlam })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: trLemma.tabs.durum })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: trLemma.tabs.duzeltme })).toBeInTheDocument();
    });

    it('has no axe violations (list, tabs and the card with the decision form)', async () => {
      // The detail handler comes before signedIn: its /reviews/stats answer must win over /reviews/{id}.
      fake.get(
        '/api/v1/reviews/{id}',
        ok(glossDetail(1, { yz_kaydi: YZ_KAYDI, yz_modeli: 'deneme-model', dogrulanmamis: true })),
      );
      fake.get('/api/v1/lemmas/{id}', ok(lemmaInfo()));
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page([glossItem(1)])));
      const { container } = renderApp(fake, '/kuyruk/lemma?kayit=1');
      await card();
      const result = await axe.run(container, {
        rules: { 'color-contrast': { enabled: false }, 'target-size': { enabled: false } },
      });
      expect(
        result.violations.map(
          (violation) =>
            `${violation.id}: ${violation.nodes.map((node) => node.target.join(' ')).join(' | ')}`,
        ),
      ).toEqual([]);
    });
  });
});

describe('trLemma', () => {
  it('has no empty text', () => {
    const walk = (value: unknown, path: string): string[] => {
      if (typeof value === 'string') return value.trim() === '' ? [path] : [];
      if (typeof value === 'function') return [];
      if (typeof value === 'object' && value !== null) {
        return Object.entries(value).flatMap(([key, entry]) => walk(entry, `${path}.${key}`));
      }
      return [];
    };
    expect(walk(trLemma, 'trLemma')).toEqual([]);
  });
});
