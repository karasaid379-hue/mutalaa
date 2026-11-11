import { screen, waitFor, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import { tr } from '@/i18n/tr';
import { DecisionForm } from '@/review/decision-form';
import { QueueLayout } from '@/review/queue-layout';
import { ok, problem, useFakeApi } from './fake-api';
import { page, reviewDetail, reviewItem, session, unitDetail } from './fixtures';
import { renderInRouter } from './render-app';

type Item = components['schemas']['ReviewItemDto'];

const FILTER = { hedef_tablo: 'unit', alan: 'metin' };

function items(ids: number[]): Item[] {
  return ids.map((id) => reviewItem({ id, hedef_anahtar: `rn:deneme:p${id}`, xmin: 100 + id }));
}

function Harness({ loadAll = false }: { loadAll?: boolean }) {
  return (
    <QueueLayout
      title="Deneme kuyruğu"
      filter={FILTER}
      loadAll={loadAll}
      renderDetail={({ review, onDecided }) => (
        <>
          <h2>{`Kayıt ${review.hedef_anahtar}`}</h2>
          <DecisionForm review={review} onDecided={onDecided} />
        </>
      )}
    />
  );
}

describe('QueueLayout', () => {
  const fake = useFakeApi();
  const listCalls = () => fake.callsTo('get', '/api/v1/reviews');

  function detailHandlers() {
    fake.get('/api/v1/reviews/{id}', (call) => {
      const id = Number(call.params.id);
      return ok(reviewDetail({ id, hedef_anahtar: `rn:deneme:p${id}`, xmin: 100 + id }));
    });
    fake.get('/api/v1/auth/me', ok(session()));
    fake.get('/api/v1/units/{anchor}', ok(unitDetail()));
  }

  it('sends the first request without a cursor and with the queue filter', async () => {
    fake.get('/api/v1/reviews', ok(page(items([1, 2]))));
    renderInRouter(fake, <Harness />);
    await screen.findByText('rn:deneme:p1');
    const first = listCalls()[0]!;
    expect(first.search.has('cursor')).toBe(false);
    expect(first.search.get('hedef_tablo')).toBe('unit');
    expect(first.search.get('alan')).toBe('metin');
    expect(first.search.get('durum')).toBe('acik');
    expect(first.search.get('limit')).toBe('50');
  });

  it('lists the records with their badges and the title as h1', async () => {
    fake.get(
      '/api/v1/reviews',
      ok(
        page([
          reviewItem({ id: 1, dogrulanmamis: true, yz_modeli: 'deneme-model' }),
          ...items([2]),
        ]),
      ),
    );
    renderInRouter(fake, <Harness />);
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Deneme kuyruğu' }),
    ).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('heading', { level: 1 })).toHaveFocus());
    const list = screen.getByRole('region', { name: tr.queue.listLabel });
    expect(await within(list).findAllByRole('listitem')).toHaveLength(2);
    expect(within(list).getAllByText(tr.badge.unverified)).toHaveLength(1);
    expect(within(list).getByText(tr.queue.loadedCount(2))).toBeInTheDocument();
    expect(screen.getByText(tr.queue.selectPrompt)).toBeInTheDocument();
  });

  it('opens the record named by ?kayit= and keeps the id in the address when selecting', async () => {
    fake.get('/api/v1/reviews', ok(page(items([1, 2, 3]))));
    detailHandlers();
    const { router, user } = renderInRouter(fake, <Harness />, '/?kayit=2');
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Kayıt rn:deneme:p2' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /rn:deneme:p2/ })).toHaveAttribute(
      'aria-current',
      'true',
    );

    await user.click(screen.getByRole('link', { name: /rn:deneme:p3/ }));
    expect(
      await screen.findByRole('heading', { level: 2, name: 'Kayıt rn:deneme:p3' }),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe('?kayit=3');
    expect(fake.callsTo('get', '/api/v1/reviews/{id}').map((call) => call.params.id)).toEqual([
      '2',
      '3',
    ]);
  });

  it('ignores a bad ?kayit= value', async () => {
    fake.get('/api/v1/reviews', ok(page(items([1]))));
    renderInRouter(fake, <Harness />, '/?kayit=abc');
    await screen.findByText('rn:deneme:p1');
    expect(screen.getByText(tr.queue.selectPrompt)).toBeInTheDocument();
    expect(fake.callsTo('get', '/api/v1/reviews/{id}')).toHaveLength(0);
  });

  it('shows the problem when the record cannot be loaded', async () => {
    fake.get('/api/v1/reviews', ok(page(items([1]))));
    fake.get('/api/v1/reviews/{id}', problem(404, 'bulunamadi'));
    renderInRouter(fake, <Harness />, '/?kayit=9');
    expect(await screen.findByText(tr.queue.detailFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes.bulunamadi)).toBeInTheDocument();
  });

  it('loads more with the cursor of the previous page and hides the button at the end', async () => {
    fake.get('/api/v1/reviews', (call) =>
      call.search.get('cursor') === 'imlec-1'
        ? ok(page(items([3, 4]), null))
        : ok(page(items([1, 2]), 'imlec-1')),
    );
    const { user } = renderInRouter(fake, <Harness />);
    await screen.findByText('rn:deneme:p1');
    await user.click(screen.getByRole('button', { name: tr.ui.loadMore }));
    await screen.findByText('rn:deneme:p4');
    expect(listCalls()).toHaveLength(2);
    expect(listCalls()[1]!.search.get('cursor')).toBe('imlec-1');
    expect(screen.getAllByRole('link')).toHaveLength(4);
    expect(screen.queryByRole('button', { name: tr.ui.loadMore })).not.toBeInTheDocument();
  });

  it('loads every page without a button when asked (loadAll, 200 per page)', async () => {
    fake.get('/api/v1/reviews', (call) => {
      const cursor = call.search.get('cursor');
      if (cursor === 'b') return ok(page(items([5, 6]), null));
      if (cursor === 'a') return ok(page(items([3, 4]), 'b'));
      return ok(page(items([1, 2]), 'a'));
    });
    renderInRouter(fake, <Harness loadAll />);
    await screen.findByText('rn:deneme:p6');
    expect(listCalls()).toHaveLength(3);
    expect(listCalls().every((call) => call.search.get('limit') === '200')).toBe(true);
    expect(screen.queryByRole('button', { name: tr.ui.loadMore })).not.toBeInTheDocument();
  });

  it('shows the empty state', async () => {
    fake.get('/api/v1/reviews', ok(page([])));
    renderInRouter(fake, <Harness />);
    expect(await screen.findByTestId('queue-empty')).toHaveTextContent(tr.queue.empty);
  });

  it('shows the problem of a failed list and retries', async () => {
    let fail = true;
    fake.get('/api/v1/reviews', () =>
      fail ? problem(500, 'sunucu-hatasi') : ok(page(items([1]))),
    );
    const { user } = renderInRouter(fake, <Harness />);
    expect(await screen.findByText(tr.queue.loadFailed)).toBeInTheDocument();
    expect(screen.getByText(tr.problem.codes['sunucu-hatasi'])).toBeInTheDocument();
    fail = false;
    await user.click(screen.getByRole('button', { name: tr.ui.retry }));
    expect(await screen.findByText('rn:deneme:p1')).toBeInTheDocument();
  });

  it('opens the next record after a decision, moves focus to it and drops the decided one from the list', async () => {
    const decided = new Set<number>();
    fake.get('/api/v1/reviews', () =>
      ok(page(items([1, 2, 3]).filter((item) => !decided.has(item.id)))),
    );
    detailHandlers();
    fake.post('/api/v1/reviews/{id}/decision', (call) => {
      decided.add(Number(call.params.id));
      return ok({
        id: Number(call.params.id),
        durum: 'onaylandi',
        eylem: 'onayla',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'onayli',
        xmin: 500,
      });
    });
    const { router, user } = renderInRouter(fake, <Harness />, '/?kayit=1');
    await screen.findByRole('heading', { level: 2, name: 'Kayıt rn:deneme:p1' });
    await user.click(await screen.findByRole('radio', { name: tr.review.approve }));
    await user.type(screen.getByLabelText(tr.review.reason), 'Tamam');
    await user.click(screen.getByRole('button', { name: tr.review.submit }));

    expect(
      await screen.findByRole('heading', { level: 2, name: 'Kayıt rn:deneme:p2' }),
    ).toBeInTheDocument();
    expect(router.state.location.search).toBe('?kayit=2');
    expect(screen.getByRole('region', { name: tr.queue.detailLabel })).toHaveFocus();
    await waitFor(() =>
      expect(screen.queryByRole('link', { name: /rn:deneme:p1/ })).not.toBeInTheDocument(),
    );
    expect(fake.callsTo('post', '/api/v1/reviews/{id}/decision')[0]?.headers.get('If-Match')).toBe(
      '"101"',
    );
  });

  it('moves focus to the list when the last record is decided', async () => {
    const decided = new Set<number>();
    fake.get('/api/v1/reviews', () => ok(page(items([1]).filter((item) => !decided.has(item.id)))));
    detailHandlers();
    fake.post('/api/v1/reviews/{id}/decision', (call) => {
      decided.add(Number(call.params.id));
      return ok({
        id: 1,
        durum: 'reddedildi',
        eylem: 'reddet',
        ikinci_onay_bekliyor: false,
        hedef_durumu: 'red',
        xmin: 500,
      });
    });
    const { router, user } = renderInRouter(fake, <Harness />, '/?kayit=1');
    await screen.findByRole('heading', { level: 2, name: 'Kayıt rn:deneme:p1' });
    await user.click(await screen.findByRole('radio', { name: tr.review.reject }));
    await user.type(screen.getByLabelText(tr.review.reason), 'Ret');
    await user.click(screen.getByRole('button', { name: tr.review.submit }));

    expect(await screen.findByTestId('queue-empty')).toBeInTheDocument();
    expect(router.state.location.search).toBe('');
    expect(screen.getByRole('region', { name: tr.queue.listLabel })).toHaveFocus();
  });
});
