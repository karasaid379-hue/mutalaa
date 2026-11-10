import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { trBaglanti } from '@/i18n/tr-baglanti-sure';
import { BaglantiQueue } from '@/screens/baglanti/baglanti-queue';
import { BULK_ENABLED } from '@/screens/baglanti/config';
import { MEAL_ID, targetInfo } from '@/screens/baglanti/target';
import { ok, problem, useFakeApi } from './fake-api';
import {
  ARABIC_SAMPLE,
  unitFor,
  xrefDetail,
  xrefHandlers,
  xrefItem,
} from './fixtures-baglanti-sure';
import { page, session, signedIn } from './fixtures';
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

  describe('list', () => {
    it('sends the first request without a cursor and with the xref filter', async () => {
      setup();
      await screen.findAllByRole('link');
      const first = listCalls()[0]!;
      expect(first.search.has('cursor')).toBe(false);
      expect(first.search.get('hedef_tablo')).toBe('xref');
      expect(first.search.get('alan')).toBe('status');
      expect(first.search.get('durum')).toBe('acik');
      expect(first.search.get('limit')).toBe('50');
    });

    it('shows the empty state', async () => {
      fake.get('/api/v1/reviews', ok(page([])));
      renderInRouter(fake, <BaglantiQueue />);
      expect(await screen.findByTestId('queue-empty')).toHaveTextContent(tr.queue.empty);
    });

    it('shows the problem when the list fails', async () => {
      fake.get('/api/v1/reviews', problem(500, 'sunucu-hatasi'));
      renderInRouter(fake, <BaglantiQueue />);
      expect(await screen.findByText(tr.queue.loadFailed)).toBeInTheDocument();
      expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    });

    it('shows the unverified badge only from the API field', async () => {
      fake.get(
        '/api/v1/reviews',
        ok(page([xrefItem(1, { dogrulanmamis: true, yz_modeli: 'deneme-model' }), xrefItem(2)])),
      );
      renderInRouter(fake, <BaglantiQueue />);
      const list = await screen.findByRole('region', { name: tr.queue.listLabel });
      await within(list).findAllByRole('listitem');
      expect(within(list).getAllByText(tr.badge.unverified)).toHaveLength(1);
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
      fake.get('/api/v1/reviews', ok(page(items(1))));
      fake.get('/api/v1/reviews/{id}', ok(xrefDetail(1, 'rn:deneme:p1', 'h:deneme:1')));
      fake.get('/api/v1/units/{anchor}', (call) => ok(unitFor(call.params.anchor!)));
      fake.get('/api/v1/auth/me', ok(session()));
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByText(trBaglanti.mealNotShown)).toBeInTheDocument();
      expect(
        unitCalls()
          .map((call) => call.params.anchor)
          .sort(),
      ).toEqual(['h:deneme:1', 'rn:deneme:p1']);
    });

    it('says so when the record has no anchors and fetches no unit', async () => {
      fake.get('/api/v1/reviews', ok(page(items(1))));
      fake.get('/api/v1/reviews/{id}', ok(xrefDetail(1, '', '', { hedef: { tablo: 'xref' } })));
      fake.get('/api/v1/auth/me', ok(session()));
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByText(trBaglanti.noAnchors)).toBeInTheDocument();
      expect(unitCalls()).toHaveLength(0);
    });

    it('shows the problem of a text that cannot be loaded, the rest stays', async () => {
      fake.get('/api/v1/reviews', ok(page(items(1))));
      fake.get('/api/v1/reviews/{id}', ok(xrefDetail(1)));
      fake.get('/api/v1/auth/me', ok(session()));
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

    it('marks the four sections the API does not give yet (A18) and invents nothing', async () => {
      setup(items(1), '/?kayit=1');
      await screen.findByText('Deneme paragrafı 1');
      for (const title of Object.values(trBaglanti.missing)) {
        const heading = screen.getByRole('heading', { level: 3, name: title });
        expect(heading.parentElement).toHaveTextContent(tr.missing.section('A18'));
      }
    });

    it('shows the first and the second approval apart', async () => {
      fake.get('/api/v1/reviews', ok(page(items(1))));
      fake.get(
        '/api/v1/reviews/{id}',
        ok(
          xrefDetail(1, undefined, undefined, {
            ikinci_onay_bekliyor: true,
            inceleyen: 'baska@deneme.test',
          }),
        ),
      );
      fake.get('/api/v1/auth/me', ok(session()));
      fake.get('/api/v1/units/{anchor}', (call) => ok(unitFor(call.params.anchor!)));
      renderInRouter(fake, <BaglantiQueue />, '/?kayit=1');
      expect(await screen.findByTestId('approval-first')).toBeInTheDocument();
      expect(screen.getByTestId('approval-second')).toBeInTheDocument();
    });

    it('decides with the status approval (If-Match = xmin)', async () => {
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
    it('lists the six closed actions with the A18 label', async () => {
      setup(items(1), '/?kayit=1');
      await screen.findByText('Deneme paragrafı 1');
      const labels = Object.values(trBaglanti.closed);
      expect(labels).toHaveLength(6);
      for (const label of labels) {
        expect(
          screen.getByRole('button', { name: `${label} · ${tr.openQuestion('A18')}` }),
        ).toHaveAttribute('data-open-question', 'A18');
      }
      expect(openQuestions()).toHaveLength(6);
    });

    it('sends no request when a closed button is clicked', async () => {
      const { user } = setup(items(1), '/?kayit=1');
      await screen.findByText('Deneme paragrafı 1');
      await screen.findByText('Deneme meal metni 1');
      const before = fake.calls.length;
      for (const button of openQuestions()) await user.click(button);
      expect(fake.calls.length).toBe(before);
      expect(singleCalls()).toHaveLength(0);
      expect(bulkCalls()).toHaveLength(0);
    });
  });

  describe('bulk selection', () => {
    it('is closed by the constant flag (false in production)', () => {
      expect(BULK_ENABLED).toBe(false);
    });

    it('is closed on the real route: no checkbox, only the closed "Toplu seçim"', async () => {
      // The detail route would also match /reviews/stats, so the session handlers come last.
      xrefHandlers(fake);
      signedIn(fake);
      fake.get('/api/v1/reviews', ok(page(items(3))));
      renderApp(fake, '/kuyruk/baglanti');
      await screen.findAllByRole('link', { name: /00000000/ });
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
      expect(
        screen.getByRole('button', {
          name: `${trBaglanti.closed.bulkSelect} · ${tr.openQuestion('A18')}`,
        }),
      ).toBeInTheDocument();
      expect(screen.queryByTestId('baglanti-bulk')).not.toBeInTheDocument();
    });

    it('with the flag off by prop there is no checkbox and no bulk bar', async () => {
      setup(items(3), '/', false);
      await screen.findAllByRole('link');
      expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
      expect(
        openQuestions().some((button) =>
          button.textContent!.startsWith(trBaglanti.closed.bulkSelect),
        ),
      ).toBe(true);
    });

    describe('with the flag injected on', () => {
      async function selectFirst(user: ReturnType<typeof setup>['user'], count: number) {
        for (let id = 1; id <= count; id++) {
          await user.click(
            await screen.findByRole('checkbox', {
              name: trBaglanti.selectRow(items(count)[id - 1]!.hedef_anahtar),
            }),
          );
        }
      }

      it('gives every row a checkbox and no "Toplu seçim" closed button', async () => {
        setup(items(3), '/', true);
        await screen.findAllByRole('link');
        expect(screen.getAllByRole('checkbox')).toHaveLength(3);
        expect(
          openQuestions().some((button) =>
            button.textContent!.startsWith(trBaglanti.closed.bulkSelect),
          ),
        ).toBe(false);
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
          kararlar: { id: number; xmin: number; karar: string }[];
        };
        expect(body.kararlar.map((entry) => entry.id)).toEqual([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]);
        expect(body.kararlar.every((entry) => entry.karar === 'onaylandi')).toBe(true);
        expect(body.kararlar[0]!.xmin).toBe(501);
        await waitFor(() => expect(screen.queryByTestId('baglanti-bulk')).not.toBeInTheDocument());
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
    });
  });
});
