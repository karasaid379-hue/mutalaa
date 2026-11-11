// Cache helpers of the review area and the label tables (A15.3).
import { QueryClient, type InfiniteData } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import type { components } from '@/api/schema';
import {
  actionLabel,
  fieldLabel,
  labelOf,
  originLabel,
  roleLabel,
  statusLabel,
  targetLabel,
} from '@/i18n/labels';
import { tr } from '@/i18n/tr';
import {
  QUEUE_PAGE_SIZE,
  SURE_ADI_PAGE_SIZE,
  patchReviewInLists,
  removeReviewsFromLists,
  reviewDetailInit,
  reviewListInit,
  reviewListOptions,
  toListItem,
} from '@/review/queries';
import { page, reviewDetail, reviewItem } from './fixtures';

type ListData = InfiniteData<components['schemas']['ReviewListResponse'], unknown>;

function seeded() {
  const client = new QueryClient();
  const key = [
    'get',
    '/api/v1/reviews',
    reviewListInit({ hedef_tablo: 'unit', alan: 'metin' }),
  ] as const;
  const data: ListData = {
    pages: [
      page([reviewItem({ id: 1 }), reviewItem({ id: 2 })], 'c'),
      page([reviewItem({ id: 3 })]),
    ],
    pageParams: [null, 'c'],
  };
  client.setQueryData(key, data);
  // A detail query and the stats must not be touched by list patches.
  client.setQueryData(
    ['get', '/api/v1/reviews/{id}', reviewDetailInit(1)],
    reviewDetail({ id: 1 }),
  );
  return { client, key };
}

describe('queue list init and options', () => {
  it('asks for open records of one target and field', () => {
    expect(reviewListInit({ hedef_tablo: 'xref', alan: 'status' })).toEqual({
      params: {
        query: { hedef_tablo: 'xref', alan: 'status', durum: 'acik', limit: QUEUE_PAGE_SIZE },
      },
    });
    expect(
      reviewListInit({ hedef_tablo: 'surah_alias', alan: 'status' }, SURE_ADI_PAGE_SIZE).params
        .query.limit,
    ).toBe(200);
  });

  it('starts without a cursor (null, not the library default 0) and follows next_cursor', () => {
    expect(reviewListOptions.initialPageParam).toBeNull();
    expect(reviewListOptions.getNextPageParam(page([], 'sonraki'))).toBe('sonraki');
    expect(reviewListOptions.getNextPageParam(page([], null))).toBeUndefined();
  });
});

describe('patchReviewInLists', () => {
  it('replaces the record in every page and leaves the others', () => {
    const { client, key } = seeded();
    patchReviewInLists(client, toListItem(reviewDetail({ id: 3, xmin: 777 })));
    const pages = client.getQueryData<ListData>(key)!.pages;
    expect(pages[1]!.items[0]!.xmin).toBe(777);
    expect(pages[0]!.items.map((item) => item.xmin)).toEqual([100, 100]);
    expect(pages[0]!.next_cursor).toBe('c');
  });

  it('removes a record that is no longer open', () => {
    const { client, key } = seeded();
    patchReviewInLists(client, reviewItem({ id: 2, durum: 'onaylandi' }));
    expect(client.getQueryData<ListData>(key)!.pages.map((p) => p.items.map((i) => i.id))).toEqual([
      [1],
      [3],
    ]);
  });

  it('keeps an open record whose second approval is pending in the list', () => {
    const { client, key } = seeded();
    patchReviewInLists(client, reviewItem({ id: 1, durum: 'acik', ikinci_onay_bekliyor: true }));
    expect(client.getQueryData<ListData>(key)!.pages[0]!.items[0]!.ikinci_onay_bekliyor).toBe(true);
  });

  it('does not touch the detail query', () => {
    const { client } = seeded();
    patchReviewInLists(client, reviewItem({ id: 1, xmin: 55 }));
    expect(
      client.getQueryData<components['schemas']['ReviewDetailDto']>([
        'get',
        '/api/v1/reviews/{id}',
        reviewDetailInit(1),
      ])!.xmin,
    ).toBe(100);
  });
});

describe('removeReviewsFromLists', () => {
  it('removes the given ids from every cached list', () => {
    const { client, key } = seeded();
    removeReviewsFromLists(client, [1, 3]);
    expect(client.getQueryData<ListData>(key)!.pages.map((p) => p.items.map((i) => i.id))).toEqual([
      [2],
      [],
    ]);
  });
});

describe('toListItem', () => {
  it('drops the detail-only fields', () => {
    const item = toListItem(reviewDetail({ gerekce: 'g', ikinci_gerekce: 'ig', sure_ms: 5 }));
    expect(Object.keys(item)).not.toContain('gerekce');
    expect(Object.keys(item)).not.toContain('hedef');
    expect(Object.keys(item)).not.toContain('dogrulanmis');
    expect(item.id).toBe(1);
  });
});

describe('label tables', () => {
  it('map the API values to Turkish and show an unknown value raw', () => {
    expect(statusLabel('geri_alindi')).toBe('Geri alındı');
    expect(actionLabel('duzenle_onayla')).toBe(tr.labels.action.duzenle_onayla);
    expect(fieldLabel('anlam_kisa')).toBe(tr.labels.field.anlam_kisa);
    expect(originLabel('kullanici_oyu')).toBe(tr.labels.origin.kullanici_oyu);
    expect(roleLabel('admin')).toBe('Yönetici');
    expect(targetLabel('surah_alias')).toBe('Sure adı');
    expect(statusLabel('yeni_durum')).toBe('yeni_durum');
    expect(targetLabel('yeni_tablo')).toBe('yeni_tablo');
    expect(labelOf(tr.labels.status, null)).toBe('');
    // Prototype names are not labels.
    expect(labelOf(tr.labels.status, 'constructor')).toBe('constructor');
    expect(labelOf(tr.labels.status, 'toString')).toBe('toString');
  });

  it('cover all 13 review target tables and the four statuses', () => {
    expect(Object.keys(tr.labels.target)).toHaveLength(13);
    expect(Object.keys(tr.labels.status)).toEqual([
      'acik',
      'onaylandi',
      'reddedildi',
      'geri_alindi',
    ]);
  });
});
