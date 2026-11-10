import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import type { InfiniteData } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { BulkDecision } from '@/review/bulk-decision';
import { reviewListInit } from '@/review/queries';
import { ok, problem, useFakeApi } from './fake-api';
import { page, reviewDetail, reviewItem } from './fixtures';
import { renderWithProviders } from './render-app';

type Item = components['schemas']['ReviewItemDto'];
type ListData = InfiniteData<components['schemas']['ReviewListResponse'], unknown>;

const FILTER = { hedef_tablo: 'xref', alan: 'status' };

function makeItems(count: number): Item[] {
  return Array.from({ length: count }, (_, index) => {
    const id = index + 1;
    return reviewItem({
      id,
      hedef_tablo: 'xref',
      hedef_anahtar: `kayit-${id}`,
      alan: 'status',
      xmin: 1000 + id,
      onceki: null,
      onerilen: null,
    });
  });
}

const sampleRows = () => screen.queryAllByTestId('bulk-sample-row');
const confirm = () => screen.getByRole('button', { name: tr.bulk.confirm });
const reason = () => screen.getByLabelText(tr.bulk.reason);

describe('BulkDecision', () => {
  const fake = useFakeApi();
  const decisionsCalls = () => fake.callsTo('post', '/api/v1/reviews/decisions');
  const OUTCOME = (id: number) => ({ id, durum: 'onaylandi', eylem: 'onayla', xmin: 2000 + id });

  function setup(items: Item[], sampling: 'tenth' | 'none' = 'tenth', random?: () => number) {
    fake.post('/api/v1/reviews/decisions', (call) => {
      const body = call.json as { kararlar: { id: number }[] };
      return ok({ sonuclar: body.kararlar.map((entry) => OUTCOME(entry.id)) });
    });
    const onDone = vi.fn();
    const view = renderWithProviders(
      fake,
      <BulkDecision
        items={items}
        sampling={sampling}
        random={random}
        onDone={onDone}
        renderSample={(item) => <p>{`Deneme içerik ${item.id}`}</p>}
      />,
    );
    return { ...view, onDone };
  }

  async function judgeAll(user: ReturnType<typeof setup>['user'], verdict: string) {
    for (const row of sampleRows()) {
      await user.click(within(row).getByRole('radio', { name: verdict }));
    }
  }

  describe('sample', () => {
    it.each([
      [1, 1],
      [9, 1],
      [10, 1],
      [11, 2],
      [25, 3],
      [100, 10],
    ])('has ceil(n/10) rows for %i selected records (%i)', (count, expected) => {
      setup(makeItems(count));
      expect(sampleRows()).toHaveLength(expected);
      expect(screen.getByTestId('bulk-count')).toHaveTextContent(tr.bulk.count(count));
    });

    it('draws distinct records of the selection with the real random source', () => {
      setup(makeItems(40), 'tenth');
      const rows = sampleRows();
      expect(rows).toHaveLength(4);
      const anchors = rows.map((row) => row.textContent);
      expect(new Set(anchors).size).toBe(4);
    });

    it('draws the sample from the random source (deterministic seam)', () => {
      setup(makeItems(25), 'tenth', () => 0);
      expect(sampleRows().map((row) => within(row).getByText(/Deneme içerik/).textContent)).toEqual(
        ['Deneme içerik 1', 'Deneme içerik 2', 'Deneme içerik 3'],
      );
    });

    it('asks every sampled record to be judged before the batch is sent', async () => {
      const { user } = setup(makeItems(25));
      fireEvent.change(reason(), { target: { value: 'Örneklem temiz' } });
      await user.click(confirm());
      expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(
        tr.bulk.verdictPending(0, 3),
      );
      expect(decisionsCalls()).toHaveLength(0);

      await judgeAll(user, tr.bulk.correct);
      await user.click(confirm());
      await waitFor(() => expect(decisionsCalls()).toHaveLength(1));
    });

    it('is cancelled by a single "Hatalı" and stays cancelled even if the verdict is changed back', async () => {
      const { user } = setup(makeItems(25));
      fireEvent.change(reason(), { target: { value: 'Gerekçe' } });
      const rows = sampleRows();
      await user.click(within(rows[0]!).getByRole('radio', { name: tr.bulk.correct }));
      await user.click(within(rows[1]!).getByRole('radio', { name: tr.bulk.wrong }));
      await user.click(within(rows[2]!).getByRole('radio', { name: tr.bulk.correct }));
      expect(await screen.findByTestId('bulk-cancelled')).toHaveTextContent(tr.bulk.cancelledBody);
      expect(confirm()).toBeDisabled();
      await user.click(within(rows[1]!).getByRole('radio', { name: tr.bulk.correct }));
      expect(confirm()).toBeDisabled();
      expect(decisionsCalls()).toHaveLength(0);
    });
  });

  describe('request', () => {
    it('sends every selected record with its own xmin, approval only, and no If-Match', async () => {
      const items = makeItems(25);
      const { user, onDone } = setup(items);
      await judgeAll(user, tr.bulk.correct);
      fireEvent.change(reason(), { target: { value: 'Toplu gerekçe' } });
      await user.click(confirm());
      await waitFor(() => expect(decisionsCalls()).toHaveLength(1));
      const call = decisionsCalls()[0]!;
      expect(call.headers.has('If-Match')).toBe(false);
      const body = call.json as { kararlar: Record<string, unknown>[] };
      expect(Object.keys(body)).toEqual(['kararlar']);
      expect(body.kararlar).toHaveLength(25);
      expect(body.kararlar[0]).toEqual({
        id: 1,
        xmin: 1001,
        karar: 'onaylandi',
        duzenlenen: null,
        gerekce: 'Toplu gerekçe',
      });
      expect(body.kararlar.map((entry) => entry.xmin)).toEqual(items.map((item) => item.xmin));
      expect(body.kararlar.every((entry) => entry.karar === 'onaylandi')).toBe(true);
      await waitFor(() => expect(onDone).toHaveBeenCalledTimes(1));
      expect(onDone.mock.calls[0]![0]).toHaveLength(25);
      expect(screen.getByRole('status')).toHaveTextContent(tr.bulk.done(25));
    });

    it('takes 100 records and refuses 101 and 0', async () => {
      const { user, unmount } = setup(makeItems(100), 'none');
      fireEvent.change(reason(), { target: { value: 'Yüz kayıt' } });
      await user.click(confirm());
      await waitFor(() => expect(decisionsCalls()).toHaveLength(1));
      expect((decisionsCalls()[0]!.json as { kararlar: unknown[] }).kararlar).toHaveLength(100);
      unmount();

      const second = setup(makeItems(101), 'none');
      fireEvent.change(reason(), { target: { value: 'Çok fazla' } });
      await second.user.click(confirm());
      expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(tr.bulk.limit);
      expect(decisionsCalls()).toHaveLength(1);
      second.unmount();

      const third = setup([], 'none');
      expect(screen.getByTestId('bulk-count')).toHaveTextContent(tr.bulk.count(0));
      fireEvent.change(reason(), { target: { value: 'Boş' } });
      await third.user.click(confirm());
      expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(tr.bulk.limit);
    });

    it('needs no sample without sampling (sure adı) but still a reason', async () => {
      const { user } = setup(makeItems(30), 'none');
      expect(screen.queryByTestId('bulk-sample')).not.toBeInTheDocument();
      expect(screen.getByText(tr.bulk.noSampling)).toBeInTheDocument();
      await user.click(confirm());
      expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(tr.review.reasonRequired);
      expect(decisionsCalls()).toHaveLength(0);
      fireEvent.change(reason(), { target: { value: 'Hepsi doğru' } });
      await user.click(confirm());
      await waitFor(() => expect(decisionsCalls()).toHaveLength(1));
    });

    it('limits the reason to 2000 code points and rejects NUL', async () => {
      const { user } = setup(makeItems(3), 'none');
      fireEvent.change(reason(), { target: { value: 'a'.repeat(2001) } });
      await user.click(confirm());
      expect(await screen.findByTestId('bulk-summary')).toHaveTextContent(
        tr.review.reasonTooLong(2001, 2000),
      );
      fireEvent.change(reason(), { target: { value: 'x\u0000y' } });
      expect(screen.getByTestId('unwritable-warning')).toBeInTheDocument();
      await user.click(confirm());
      expect(decisionsCalls()).toHaveLength(0);
      await user.click(screen.getByRole('button', { name: tr.review.unwritableAction }));
      expect((reason() as HTMLTextAreaElement).value).toBe('xy');
    });
  });

  describe('errors', () => {
    it('412: fetches only the changed records, patches the cache and marks them', async () => {
      const items = makeItems(25);
      const { user, queryClient, api } = setup(items, 'none');
      const key = api.$api.queryOptions('get', '/api/v1/reviews', reviewListInit(FILTER)).queryKey;
      queryClient.setQueryData<ListData>(key, { pages: [page(items)], pageParams: [null] });
      fake.post(
        '/api/v1/reviews/decisions',
        problem(412, 'surum-uyusmazligi', { kimlikler: [2, 3] }),
      );
      fake.get('/api/v1/reviews/{id}', (call) => {
        const id = Number(call.params.id);
        return ok(
          reviewDetail({ ...makeItems(25)[id - 1]!, xmin: 5000 + id, hedef: { tablo: 'xref' } }),
        );
      });

      fireEvent.change(reason(), { target: { value: 'Toplu' } });
      await user.click(confirm());

      expect(
        await screen.findByText(tr.problem.contexts.bulk['surum-uyusmazligi']),
      ).toBeInTheDocument();
      await waitFor(() => expect(fake.callsTo('get', '/api/v1/reviews/{id}')).toHaveLength(2));
      expect(
        fake
          .callsTo('get', '/api/v1/reviews/{id}')
          .map((call) => call.params.id)
          .sort(),
      ).toEqual(['2', '3']);
      expect(decisionsCalls()).toHaveLength(1);

      const rows = await screen.findByTestId('bulk-problem-rows');
      expect(rows).toHaveTextContent(`kayit-2: ${tr.bulk.rowStale}`);
      expect(rows).toHaveTextContent(`kayit-3: ${tr.bulk.rowStale}`);
      expect(rows).not.toHaveTextContent('kayit-1:');

      // The cache holds the fresh versions of exactly those two records.
      const cached = queryClient.getQueryData<ListData>(key)!.pages[0]!.items;
      expect(cached.find((item) => item.id === 2)?.xmin).toBe(5002);
      expect(cached.find((item) => item.id === 3)?.xmin).toBe(5003);
      expect(cached.find((item) => item.id === 1)?.xmin).toBe(1001);
      expect(cached).toHaveLength(25);
    });

    it('412: a record that is no longer open leaves the cached lists', async () => {
      const items = makeItems(5);
      const { user, queryClient, api } = setup(items, 'none');
      const key = api.$api.queryOptions('get', '/api/v1/reviews', reviewListInit(FILTER)).queryKey;
      queryClient.setQueryData<ListData>(key, { pages: [page(items)], pageParams: [null] });
      fake.post('/api/v1/reviews/decisions', problem(412, 'surum-uyusmazligi', { kimlikler: [4] }));
      fake.get(
        '/api/v1/reviews/{id}',
        ok(reviewDetail({ ...items[3]!, durum: 'onaylandi', xmin: 7000 })),
      );
      fireEvent.change(reason(), { target: { value: 'Toplu' } });
      await user.click(confirm());
      await screen.findByTestId('bulk-problem-rows');
      expect(
        queryClient.getQueryData<ListData>(key)!.pages[0]!.items.map((item) => item.id),
      ).toEqual([1, 2, 3, 5]);
    });

    it('412: the verdict of a changed sampled record is dropped', async () => {
      const items = makeItems(25);
      const { user } = setup(items, 'tenth', () => 0);
      fake.post('/api/v1/reviews/decisions', problem(412, 'surum-uyusmazligi', { kimlikler: [1] }));
      fake.get('/api/v1/reviews/{id}', ok(reviewDetail({ ...items[0]!, xmin: 9000 })));
      await judgeAll(user, tr.bulk.correct);
      fireEvent.change(reason(), { target: { value: 'Toplu' } });
      await user.click(confirm());
      await screen.findByTestId('bulk-problem-rows');
      const first = sampleRows()[0]!;
      expect(within(first).getByRole('radio', { name: tr.bulk.correct })).not.toBeChecked();
      expect(within(sampleRows()[1]!).getByRole('radio', { name: tr.bulk.correct })).toBeChecked();
      expect(screen.getByText(tr.bulk.verdictPending(2, 3))).toBeInTheDocument();
    });

    it('404 kimlikler: marks the missing records and leaves them out of the next attempt', async () => {
      const { user } = setup(makeItems(6), 'none');
      fake.post('/api/v1/reviews/decisions', (call) => {
        const ids = (call.json as { kararlar: { id: number }[] }).kararlar.map((entry) => entry.id);
        return ids.includes(4)
          ? problem(404, 'bulunamadi', { kimlikler: [4] })
          : ok({ sonuclar: ids.map(OUTCOME) });
      });
      fireEvent.change(reason(), { target: { value: 'Toplu' } });
      await user.click(confirm());
      const rows = await screen.findByTestId('bulk-problem-rows');
      expect(rows).toHaveTextContent(`kayit-4: ${tr.bulk.rowMissing}`);
      expect(screen.getByText(tr.problem.contexts.bulk.bulunamadi)).toBeInTheDocument();
      expect(screen.getByTestId('bulk-count')).toHaveTextContent(tr.bulk.count(5));

      await user.click(confirm());
      await waitFor(() => expect(decisionsCalls()).toHaveLength(2));
      const ids = (decisionsCalls()[1]!.json as { kararlar: { id: number }[] }).kararlar.map(
        (e) => e.id,
      );
      expect(ids).toEqual([1, 2, 3, 5, 6]);
    });

    it('rule violation (kimlik): marks the row with the reason and leaves it out of the next attempt', async () => {
      const { user } = setup(makeItems(4), 'none');
      fake.post('/api/v1/reviews/decisions', (call) => {
        const ids = (call.json as { kararlar: { id: number }[] }).kararlar.map((entry) => entry.id);
        return ids.includes(2)
          ? problem(409, 'durum-gecisi-gecersiz', {
              kimlik: 2,
              detail: 'Editor kendi onerisini onaylayamaz.',
            })
          : ok({ sonuclar: ids.map(OUTCOME) });
      });
      fireEvent.change(reason(), { target: { value: 'Toplu' } });
      await user.click(confirm());
      const rows = await screen.findByTestId('bulk-problem-rows');
      expect(rows).toHaveTextContent(`kayit-2: ${tr.bulk.rowViolation}`);
      expect(rows).toHaveTextContent(tr.problem.contexts.bulk['durum-gecisi-gecersiz']);
      await user.click(confirm());
      await waitFor(() => expect(decisionsCalls()).toHaveLength(2));
      expect(
        (decisionsCalls()[1]!.json as { kararlar: { id: number }[] }).kararlar.map((e) => e.id),
      ).toEqual([1, 3, 4]);
    });

    it('shows other problems as a summary without marking rows', async () => {
      const { user } = setup(makeItems(3), 'none');
      fake.post('/api/v1/reviews/decisions', problem(500, 'sunucu-hatasi'));
      fireEvent.change(reason(), { target: { value: 'Toplu' } });
      await user.click(confirm());
      expect(await screen.findByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
      expect(screen.queryByTestId('bulk-problem-rows')).not.toBeInTheDocument();
    });
  });
});
