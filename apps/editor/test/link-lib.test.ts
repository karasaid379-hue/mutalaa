// A18.4 pure parts: the link edit rules, the snapshot readers, the queue filter, the roles and the list cache.
import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { canDecideStatus, canSendToExpert } from '@/lib/roles';
import { kodOf, problemText, showsServerDetail } from '@/lib/problem-text';
import {
  REVIEWS_PATH,
  patchReviewInLists,
  reviewListInit,
  type QueueFilter,
} from '@/review/queries';
import { approveBlockReason } from '@/review/rules';
import { LINK_CLASSES, isLinkClass, isLinkStatusView, linkFilter } from '@/screens/baglanti/config';
import {
  EMPTY_LINK_EDIT,
  isEditableType,
  resolveLinkEdit,
  type LinkEditContext,
  type LinkEditInput,
} from '@/screens/baglanti/link-edit';
import {
  classCount,
  hasSummaryFacts,
  readEvidence,
  readHighlight,
  readLinkClass,
  readSpan,
} from '@/screens/baglanti/link-snapshot';
import { stats } from './fixtures';
import { xrefItem } from './fixtures-baglanti-sure';

const CTX: LinkEditContext = { currentType: 'iktibas', currentDst: 'q:1:2' };
const edit = (over: Partial<LinkEditInput>, ctx: LinkEditContext = CTX) =>
  resolveLinkEdit({ ...EMPTY_LINK_EDIT, ...over }, ctx);

describe('resolveLinkEdit', () => {
  it('has nothing to send when nothing is typed', () => {
    expect(edit({})).toEqual({ value: null, problems: [], anchorCarriesSpan: false });
  });

  it('sends the target, the span and the type that differ from the current ones', () => {
    expect(edit({ dstAnchor: 'q:2:255' }).value).toEqual({ dst_anchor: 'q:2:255' });
    expect(edit({ spanStart: '2', spanEnd: '6' }).value).toEqual({ dst_span: [2, 6] });
    expect(edit({ type: 'atif' }).value).toEqual({ type: 'atif' });
    expect(
      edit(
        { dstAnchor: 'h:buhari:52', spanStart: '0', spanEnd: '9', type: 'ima' },
        {
          currentType: 'atif',
          currentDst: 'h:muslim:1',
        },
      ).value,
    ).toEqual({ dst_anchor: 'h:buhari:52', dst_span: [0, 9], type: 'ima' });
  });

  it('drops what equals the current value (the server would take it as a plain approval)', () => {
    expect(edit({ dstAnchor: 'q:1:2' }).value).toBeNull();
    expect(edit({ dstAnchor: '  q:1:2  ', type: 'iktibas' }).value).toBeNull();
    expect(edit({ dstAnchor: 'q:3:4', type: 'iktibas' }).value).toEqual({ dst_anchor: 'q:3:4' });
  });

  it('never sends dst_span with an anchor that carries its own span (word range, one word)', () => {
    for (const anchor of ['q:2:255:3-7', 'q:2:255:3']) {
      const result = edit({ dstAnchor: anchor });
      expect(result.anchorCarriesSpan).toBe(true);
      expect(result.value).toEqual({ dst_anchor: anchor });
      expect(Object.keys(result.value!)).not.toContain('dst_span');
    }
    const conflict = edit({ dstAnchor: 'q:2:255:3-7', spanStart: '1', spanEnd: '4' });
    expect(conflict.value).toBeNull();
    expect(conflict.problems).toEqual([{ field: 'span', code: 'spanConflict' }]);
  });

  it.each([
    ['q:2:287x', 'anchorInvalid'],
    ['Q:2:255', 'anchorInvalid'],
    ['q:2:255-257', 'anchorRange'],
    ['rn:deneme:p1:s2', 'anchorSentence'],
    ['rn:deneme:p1', 'anchorKind'],
    ['meal:elmalili:2:255', 'anchorKind'],
    ['konu:tevhid', 'anchorKind'],
  ])('refuses the target %j (%s)', (anchor, code) => {
    const result = edit({ dstAnchor: anchor });
    expect(result.value).toBeNull();
    expect(result.problems).toEqual([{ field: 'dstAnchor', code }]);
  });

  it('lets a type that is not editable keep any target kind (the server asks only for the editable ones)', () => {
    expect(
      edit({ dstAnchor: 'konu:tevhid' }, { currentType: 'benzer_ayet', currentDst: 'q:1:2' })
        .problems,
    ).toEqual([]);
  });

  it('asks the editable-type target rule for the type the editor chose', () => {
    const result = edit(
      { dstAnchor: 'konu:tevhid', type: 'ima' },
      { currentType: 'benzer_ayet', currentDst: 'q:1:2' },
    );
    expect(result.problems).toEqual([{ field: 'dstAnchor', code: 'anchorKind' }]);
  });

  it.each([
    [{ spanStart: '3' }, 'spanBoth'],
    [{ spanEnd: '3' }, 'spanBoth'],
    [{ spanStart: '5', spanEnd: '5' }, 'spanOrder'],
    [{ spanStart: '6', spanEnd: '5' }, 'spanOrder'],
    [{ spanStart: '-1', spanEnd: '5' }, 'spanInt'],
    [{ spanStart: '1.5', spanEnd: '5' }, 'spanInt'],
    [{ spanStart: '01', spanEnd: '5' }, 'spanInt'],
    [{ spanStart: '1', spanEnd: '2147483648' }, 'spanInt'],
    [{ spanStart: '٣', spanEnd: '9' }, 'spanInt'],
    [{ spanStart: '0', spanEnd: '5' }, 'spanWordStart'],
  ] as const)('refuses the span %j (%s) on an ayah target', (input, code) => {
    const result = edit({ ...input });
    expect(result.value).toBeNull();
    expect(result.problems).toEqual([{ field: 'span', code }]);
  });

  it('accepts a start of 0 for a text target (code points)', () => {
    expect(
      edit({ spanStart: '0', spanEnd: '4' }, { currentType: 'atif', currentDst: 'h:buhari:52' })
        .value,
    ).toEqual({ dst_span: [0, 4] });
    expect(edit({ dstAnchor: 'h:buhari:52', spanStart: '0', spanEnd: '4' }).value).toEqual({
      dst_anchor: 'h:buhari:52',
      dst_span: [0, 4],
    });
  });

  it('reports the editable types', () => {
    expect(['atif', 'iktibas', 'ima'].every(isEditableType)).toBe(true);
    for (const type of ['kok', 'lemma', 'benzer_ayet', 'anlamsal', '', null]) {
      expect(isEditableType(type)).toBe(false);
    }
  });
});

describe('link snapshot readers', () => {
  it('reads the class: the four known values only', () => {
    for (const value of LINK_CLASSES) expect(readLinkClass(value)).toBe(value);
    expect(readLinkClass('baska')).toBeNull();
    expect(readLinkClass(null)).toBeNull();
    expect(readLinkClass(undefined)).toBeNull();
    expect(isLinkClass('gri')).toBe(true);
    expect(isLinkClass('Gri')).toBe(false);
    expect(isLinkStatusView('uzmanda')).toBe(true);
    expect(isLinkStatusView('onaylandi')).toBe(false);
  });

  it('reads the evidence and trusts no shape', () => {
    expect(readEvidence(null)).toBeNull();
    expect(readEvidence('metin')).toBeNull();
    expect(readEvidence([1])).toBeNull();
    const none = readEvidence({})!;
    expect(hasSummaryFacts(none)).toBe(false);
    expect(none.alternatives).toEqual([]);
    const facts = readEvidence({
      matched_words: '7',
      coverage: 0.5,
      consistent_quote: 'evet',
      phrase_freq: 2,
      group: { a: 1 },
      alternatives: 'yok',
    })!;
    expect(facts.matchedWords).toBeNull();
    expect(facts.coverage).toBe(0.5);
    expect(facts.consistentQuote).toBeNull();
    expect(facts.phraseFreq).toBe(2);
    expect(facts.group).toBeNull();
    expect(facts.alternatives).toEqual([]);
    expect(hasSummaryFacts(facts)).toBe(true);
  });

  it('reads alternatives: scalar entries of an object, plain scalars, nothing else', () => {
    const facts = readEvidence({
      alternatives: [
        { dst: 'q:1:3', n: 5, ok: true, nested: { a: 1 }, none: null },
        'q:1:4',
        7,
        null,
        [1],
        {},
      ],
    })!;
    expect(facts.alternatives).toEqual([
      {
        entries: [
          { key: 'dst', value: 'q:1:3' },
          { key: 'n', value: '5' },
          { key: 'ok', value: 'true' },
        ],
      },
      { entries: [{ key: null, value: 'q:1:4' }] },
      { entries: [{ key: null, value: '7' }] },
    ]);
  });

  it('reads the highlight: all three null, or no sequence, is "no highlight"', () => {
    expect(readHighlight(null)).toBeNull();
    expect(readHighlight(undefined)).toBeNull();
    expect(readHighlight({ sol: null, dizi: null, sag: null })).toBeNull();
    expect(readHighlight({ sol: 'a', dizi: null, sag: 'b' })).toBeNull();
    expect(readHighlight({ sol: 'a', dizi: '', sag: 'b' })).toBeNull();
    expect(readHighlight({ sol: null, dizi: 'd', sag: null })).toEqual({
      before: null,
      sequence: 'd',
      after: null,
    });
  });

  it('reads a span only when it is two integers', () => {
    expect(readSpan([1, 5])).toEqual([1, 5]);
    expect(readSpan([1])).toBeNull();
    expect(readSpan([1, 5, 9])).toBeNull();
    expect(readSpan([1.5, 5])).toBeNull();
    expect(readSpan(null)).toBeNull();
  });

  it('counts a class from the stats (0 when it is not listed, undefined while unknown)', () => {
    const data = stats(
      [['xref', 'status', 3]],
      [
        ['tutarsiz', 1],
        ['toplu', 2],
      ],
      4,
    );
    expect(classCount(data, 'tutarsiz')).toBe(1);
    expect(classCount(data, 'toplu')).toBe(2);
    expect(classCount(data, 'gri')).toBe(0);
    expect(classCount(undefined, 'gri')).toBeUndefined();
    expect(data.toplam_uzmanda).toBe(4);
  });
});

describe('queue filter and list request', () => {
  it('asks for class order, one class and the expert status as the server names them', () => {
    expect(reviewListInit(linkFilter('acik', 'hepsi')).params.query).toEqual({
      hedef_tablo: 'xref',
      alan: 'status',
      durum: 'acik',
      sira: 'sinif',
      limit: 50,
    });
    expect(reviewListInit(linkFilter('uzmanda', 'toplu')).params.query).toEqual({
      hedef_tablo: 'xref',
      alan: 'status',
      durum: 'uzmanda',
      sira: 'sinif',
      sinif: 'toplu',
      limit: 50,
    });
    const filter: QueueFilter = { hedef_tablo: 'lemma', onay_yolu: 'editor' };
    expect(reviewListInit(filter).params.query).toMatchObject({ onay_yolu: 'editor' });
  });
});

describe('roles for the expert flow', () => {
  it('lets editor and admin decide an open record and only the expert decide one at the expert', () => {
    for (const roles of [['editor'], ['admin'], ['editor', 'admin']]) {
      expect(canDecideStatus(roles, 'acik')).toBe(true);
      expect(canDecideStatus(roles, 'uzmanda')).toBe(false);
      expect(canSendToExpert(roles)).toBe(true);
    }
    expect(canDecideStatus(['uzman'], 'uzmanda')).toBe(true);
    expect(canDecideStatus(['uzman'], 'acik')).toBe(false);
    expect(canSendToExpert(['uzman'])).toBe(false);
    expect(canDecideStatus([], 'uzmanda')).toBe(false);
    expect(canDecideStatus(undefined, 'acik')).toBe(false);
  });

  it('does not call a record at the expert closed', () => {
    const base = xrefItem(1);
    expect(approveBlockReason({ ...base, durum: 'acik' }, 'a@b.test')).toBeNull();
    expect(approveBlockReason({ ...base, durum: 'uzmanda' }, 'a@b.test')).toBeNull();
    expect(approveBlockReason({ ...base, durum: 'onaylandi' }, 'a@b.test')).toBe('closed');
  });
});

describe('list cache by status', () => {
  function seed(client: QueryClient, durum: 'acik' | 'uzmanda', ids: number[]) {
    const key = [
      'get',
      REVIEWS_PATH,
      reviewListInit({ hedef_tablo: 'xref', alan: 'status', durum }),
    ];
    client.setQueryData(key, {
      pages: [{ items: ids.map((id) => xrefItem(id)), next_cursor: null }],
      pageParams: [null],
    });
    return key;
  }
  const idsOf = (client: QueryClient, key: unknown[]) =>
    (client.getQueryData(key) as { pages: { items: { id: number }[] }[] }).pages[0]!.items.map(
      (item) => item.id,
    );

  it('keeps a record that moved to the expert in the expert list and takes it out of the open list', () => {
    const client = new QueryClient();
    const open = seed(client, 'acik', [1, 2]);
    const expert = seed(client, 'uzmanda', [1]);
    patchReviewInLists(client, { ...xrefItem(1), durum: 'uzmanda', xmin: 999 });
    expect(idsOf(client, open)).toEqual([2]);
    expect(idsOf(client, expert)).toEqual([1]);
    expect(
      (client.getQueryData(expert) as { pages: { items: { xmin: number }[] }[] }).pages[0]!
        .items[0]!.xmin,
    ).toBe(999);
  });

  it('keeps an open record in the open list and out of the expert list', () => {
    const client = new QueryClient();
    const open = seed(client, 'acik', [1, 2]);
    const expert = seed(client, 'uzmanda', [3]);
    patchReviewInLists(client, { ...xrefItem(1), durum: 'acik', xmin: 777 });
    expect(idsOf(client, open)).toEqual([1, 2]);
    expect(idsOf(client, expert)).toEqual([3]);
  });

  it('takes a decided record out of every list', () => {
    const client = new QueryClient();
    const open = seed(client, 'acik', [1, 2]);
    const expert = seed(client, 'uzmanda', [1]);
    patchReviewInLists(client, { ...xrefItem(1), durum: 'onaylandi' });
    expect(idsOf(client, open)).toEqual([2]);
    expect(idsOf(client, expert)).toEqual([]);
  });
});

describe('problem wording of A18.4', () => {
  it('words toplu-uygun-degil and shows the server detail', () => {
    expect(problemText({ kod: 'toplu-uygun-degil' })).toBe(tr.problem.codes['toplu-uygun-degil']);
    expect(problemText({ kod: 'toplu-uygun-degil' }, 'bulk')).toBe(
      tr.problem.contexts.bulk['toplu-uygun-degil'],
    );
    expect(kodOf({ type: 'urn:mutalaa:problem:toplu-uygun-degil' })).toBe('toplu-uygun-degil');
    expect(showsServerDetail({ kod: 'toplu-uygun-degil', detail: "bu aday: 'gri'" })).toBe(true);
  });

  it('words a 403 for a decision and for a bulk decision (a record at the expert)', () => {
    expect(problemText({ kod: 'yetki-yok' }, 'decision')).toBe(
      tr.problem.contexts.decision['yetki-yok'],
    );
    expect(problemText({ kod: 'yetki-yok' }, 'bulk')).toBe(tr.problem.contexts.bulk['yetki-yok']);
    expect(problemText({ kod: 'yetki-yok' })).toBe(tr.problem.codes['yetki-yok']);
  });

  it('words the link action and word fix contexts, and falls back to the generic text', () => {
    for (const kod of ['surum-uyusmazligi', 'yetki-yok', 'bulunamadi', 'cakisma'] as const) {
      expect(problemText({ kod }, 'link')).toBe(tr.problem.contexts.link[kod]);
    }
    expect(problemText({ kod: 'dogrulama' }, 'wordFix')).toBe(
      tr.problem.contexts.wordFix.dogrulama,
    );
    expect(problemText({ kod: 'sunucu-hatasi' }, 'wordFix')).toBe(
      tr.problem.codes['sunucu-hatasi'],
    );
  });
});
