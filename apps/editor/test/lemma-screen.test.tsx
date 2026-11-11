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
  LEMMA_ARABIC,
  SHA_A,
  SHA_B,
  YZ_KAYDI,
  glossDetail,
  glossItem,
  lemmaHandlers,
  lemmaItem,
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
    opts: { glosses?: Item[]; lemmas?: Item[]; route?: string; detail?: Detail } = {},
  ) {
    const glosses = opts.glosses ?? [glossItem(1), glossItem(2)];
    const lemmas = opts.lemmas ?? [lemmaItem(101), lemmaItem(102)];
    fake.get('/api/v1/reviews', (call) =>
      ok(page(call.search.get('hedef_tablo') === 'lemma' ? lemmas : glosses)),
    );
    if (opts.detail) fake.get('/api/v1/reviews/{id}', ok(opts.detail));
    else lemmaHandlers(fake);
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
      expect(screen.getByRole('tab', { name: trLemma.tabs.anlam })).toHaveAttribute(
        'aria-selected',
        'true',
      );
      expect(screen.getByRole('tab', { name: trLemma.tabs.durum })).toHaveAttribute(
        'aria-selected',
        'false',
      );
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
      expect(origin).toHaveTextContent(`${trLemma.origin.confidence}0,87`);
      expect(origin).toHaveTextContent(trLemma.origin.unverifiedNote);
      // The confidence is present, so its section is not marked as missing.
      expect(
        within(root).queryByRole('heading', { level: 3, name: trLemma.missing.confidence }),
      ).not.toBeInTheDocument();
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

    it('marks the confidence as missing when neither the API nor the payload carries one', async () => {
      setup({ route: '/?kayit=1', detail: glossDetail(1, { guven: null }) });
      const root = await card();
      const heading = within(root).getByRole('heading', {
        level: 3,
        name: trLemma.missing.confidence,
      });
      expect(heading.parentElement).toHaveTextContent(tr.missing.section('A17'));
      expect(within(root).getByTestId('lemma-origin')).not.toHaveTextContent(
        trLemma.origin.confidence + '0',
      );
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
      expect(origin).toHaveTextContent(`${trLemma.origin.confidence}0,25`);
      expect(
        screen.queryByRole('heading', { level: 3, name: trLemma.missing.confidence }),
      ).not.toBeInTheDocument();
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

    it('marks the four sections the API does not give yet (A17) and invents nothing', async () => {
      setup({ route: '/?kayit=1' });
      const root = await card();
      for (const title of [
        trLemma.missing.rootPosFrequency,
        trLemma.missing.kwic,
        trLemma.missing.sameRoot,
        trLemma.missing.waveOrder,
      ]) {
        const heading = within(root).getByRole('heading', { level: 3, name: title });
        expect(heading.parentElement).toHaveTextContent(tr.missing.section('A17'));
      }
      expect(trLemma.missing.rootPosFrequency).toBe('Kök, tür ve sıklık');
      expect(trLemma.missing.sameRoot).toBe('Aynı kökün onaylı anlamları');
      expect(trLemma.missing.waveOrder).toBe('Dalga ve kök sırası');
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
    it('lists the four closed actions: three A17 and one A18', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      const expected: [string, string][] = [
        [trLemma.closed.editApprove, 'A17'],
        [trLemma.closed.sendExpert, 'A17'],
        [trLemma.closed.redraft, 'A17'],
        [trLemma.closed.etymologicalOnly, 'A18'],
      ];
      for (const [label, phase] of expected) {
        expect(
          screen.getByRole('button', { name: `${label} · ${tr.openQuestion(phase)}` }),
        ).toHaveAttribute('data-open-question', phase);
      }
      expect(openQuestions()).toHaveLength(4);
      expect(trLemma.closed.editApprove).toBe('Düzenle ve onayla');
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

    it('has no edited-text field: the decision is approval or rejection only, and no unit is requested', async () => {
      setup({ route: '/?kayit=1' });
      await card();
      expect(screen.queryByLabelText(tr.review.editedText)).not.toBeInTheDocument();
      expect(fake.callsTo('get', '/api/v1/units/{anchor}')).toHaveLength(0);
      expect(screen.getByText(trLemma.decisionNote)).toBeInTheDocument();
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
    });

    it('has no axe violations (list, tabs and the card with the decision form)', async () => {
      // The detail handler comes before signedIn: its /reviews/stats answer must win over /reviews/{id}.
      fake.get(
        '/api/v1/reviews/{id}',
        ok(glossDetail(1, { yz_kaydi: YZ_KAYDI, yz_modeli: 'deneme-model', dogrulanmamis: true })),
      );
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
