// Decision pre-checks and the stale-record description (A15.3). Pure functions.
import { describe, expect, it } from 'vitest';
import { tr } from '@/i18n/tr';
import { labelOf } from '@/i18n/labels';
import {
  approveBlockReason,
  canEditValue,
  hasOffsetData,
  isGlossEditable,
  proposedGloss,
  proposedText,
} from '@/review/rules';
import { describeChanges } from '@/review/stale';
import { QUEUES, openCount } from '@/review/queues';
import { reviewDetail, reviewItem, stats, unitDetail } from './fixtures';

describe('canEditValue', () => {
  const open = reviewItem();
  const unit = unitDetail();

  it('is true for an open first-stage unit text with an editable, offset-free unit', () => {
    expect(canEditValue(open, unit)).toBe(true);
  });

  it('is false without unit information', () => {
    expect(canEditValue(open, null)).toBe(false);
    expect(canEditValue(open, undefined)).toBe(false);
  });

  it.each([
    ['another target table', reviewItem({ hedef_tablo: 'xref' })],
    ['another field', reviewItem({ alan: 'status' })],
    ['a closed review', reviewItem({ durum: 'onaylandi' })],
    ['the second approval stage', reviewItem({ ikinci_onay_bekliyor: true })],
  ])('is false for %s', (_, review) => {
    expect(canEditValue(review, unit)).toBe(false);
  });

  it.each([
    ['a unit the API says is not correctable', unitDetail({ duzeltilebilir: false })],
    ['an ayet (Tanzil) unit', unitDetail({ kind: 'ayet', duzeltilebilir: true })],
    ['a Quran text source', unitDetail({ kaynak_tur: 'kuran_metni', duzeltilebilir: true })],
    ['a unit with marks', unitDetail({ marks: [[0, 3, 'x']] })],
    ['a unit with sentences', unitDetail({ sentences: [[0, 5]] })],
    ['a unit with unreadable marks', unitDetail({ marks: 'bozuk' })],
  ])('is false for %s', (_, info) => {
    expect(canEditValue(open, info)).toBe(false);
  });

  it('treats empty marks and null sentences as no offset data', () => {
    expect(hasOffsetData({ marks: [], sentences: null })).toBe(false);
    expect(hasOffsetData({ marks: null, sentences: [] })).toBe(false);
    expect(hasOffsetData({ marks: undefined, sentences: undefined })).toBe(false);
    expect(hasOffsetData({ marks: [], sentences: [[0, 1]] })).toBe(true);
  });
});

describe('approveBlockReason', () => {
  const me = 'editor@deneme.test';

  it('is null for an open record of someone else', () => {
    expect(approveBlockReason(reviewItem({ koken: 'hat', oneren: 'hat' }), me)).toBeNull();
    expect(
      approveBlockReason(reviewItem({ koken: 'editor', oneren: 'baska@deneme.test' }), me),
    ).toBeNull();
  });

  it('closes a decided record', () => {
    expect(approveBlockReason(reviewItem({ durum: 'reddedildi' }), me)).toBe('closed');
  });

  it('closes "Onayla" for the editor\'s own proposal (case-insensitive), not for a pipeline proposal', () => {
    expect(
      approveBlockReason(reviewItem({ koken: 'editor', oneren: 'EDITOR@Deneme.test' }), me),
    ).toBe('own-proposal');
    expect(approveBlockReason(reviewItem({ koken: 'hat', oneren: me }), me)).toBeNull();
  });

  it('closes the second approval for the first approver', () => {
    expect(
      approveBlockReason(
        reviewItem({ ikinci_onay_bekliyor: true, inceleyen: me, oneren: 'hat' }),
        me,
      ),
    ).toBe('same-first-approver');
    expect(
      approveBlockReason(
        reviewItem({ ikinci_onay_bekliyor: true, inceleyen: 'baska@deneme.test' }),
        me,
      ),
    ).toBeNull();
  });

  it('closes nothing while the user is unknown', () => {
    expect(approveBlockReason(reviewItem({ koken: 'editor', oneren: me }), undefined)).toBeNull();
  });
});

describe('proposedText', () => {
  it('prefers the edited value over the original proposal', () => {
    expect(
      proposedText(
        reviewItem({ duzenlenen: { metin: 'Düzenlenmiş' }, onerilen: { metin: 'Önerilen' } }),
      ),
    ).toBe('Düzenlenmiş');
    expect(proposedText(reviewItem({ duzenlenen: null, onerilen: { metin: 'Önerilen' } }))).toBe(
      'Önerilen',
    );
    expect(proposedText(reviewItem({ duzenlenen: null, onerilen: null }))).toBeNull();
    expect(
      proposedText(reviewItem({ onerilen: { alias: 'Deneme-sure-1' }, duzenlenen: null })),
    ).toBeNull();
  });
});

describe('describeChanges (the 412 view)', () => {
  it('lists the fields that differ, with Turkish labels for known values', () => {
    const before = reviewDetail({ durum: 'acik', inceleyen: null, ikinci_onay_bekliyor: false });
    const after = reviewDetail({
      durum: 'acik',
      inceleyen: 'birinci@deneme.test',
      ikinci_onay_bekliyor: true,
      xmin: 101,
    });
    expect(describeChanges(before, after)).toEqual([
      { field: 'inceleyen', before: '—', after: 'birinci@deneme.test' },
      { field: 'ikinci_onay_bekliyor', before: tr.ui.no, after: tr.ui.yes },
    ]);
  });

  it('maps status and action values and keeps unknown ones raw', () => {
    const before = reviewDetail({ durum: 'acik', eylem: 'oner' });
    const after = reviewDetail({ durum: 'onaylandi', eylem: 'yeni_eylem' });
    expect(describeChanges(before, after)).toEqual([
      {
        field: 'durum',
        before: labelOf(tr.labels.status, 'acik'),
        after: tr.labels.status.onaylandi,
      },
      { field: 'eylem', before: tr.labels.action.oner, after: 'yeni_eylem' },
    ]);
  });

  it('carries both texts of a changed text payload for the diff', () => {
    const before = reviewDetail({ onerilen: { metin: 'Deneme paragrafı 1' } });
    const after = reviewDetail({ onerilen: { metin: 'Deneme paragrafı 2' } });
    expect(describeChanges(before, after)).toEqual([
      {
        field: 'onerilen',
        before: 'Deneme paragrafı 1',
        after: 'Deneme paragrafı 2',
        text: { before: 'Deneme paragrafı 1', after: 'Deneme paragrafı 2' },
      },
    ]);
  });

  it('shows a non-text payload as JSON without a text diff', () => {
    const before = reviewDetail({ onerilen: { alias: 'Deneme-sure-1' } });
    const after = reviewDetail({ onerilen: { alias: 'Deneme-sure-2' } });
    const [change] = describeChanges(before, after);
    expect(change).toEqual({
      field: 'onerilen',
      before: '{"alias":"Deneme-sure-1"}',
      after: '{"alias":"Deneme-sure-2"}',
    });
  });

  it('is empty when only xmin moved', () => {
    expect(describeChanges(reviewDetail({ xmin: 1 }), reviewDetail({ xmin: 2 }))).toEqual([]);
  });
});

describe('queue counts', () => {
  it('sums the stats entries of a screen (lemma has three tabs; quran_word_fix counts every field)', () => {
    const data = stats([
      ['unit', 'metin', 4],
      ['lemma_gloss', 'anlam_kisa', 2],
      ['lemma', 'status', 3],
      ['quran_word_fix', 'lemma_id', 4],
      ['quran_word_fix', 'pos', 1],
      ['quran_word_fix', 'root_id', 2],
      ['quran_word_fix', 'features', 3],
      ['xref', 'status', 9],
    ]);
    const byId = Object.fromEntries(QUEUES.map((queue) => [queue.id, openCount(data, queue)]));
    expect(byId).toEqual({ ocr: 4, lemma: 15, baglanti: 9, 'sure-adi': 0 });
    expect(openCount(undefined, QUEUES[0]!)).toBeUndefined();
  });
});

describe('isGlossEditable and proposedGloss', () => {
  it('is true only for an open lemma_gloss + anlam_kisa review', () => {
    const gloss = reviewItem({ hedef_tablo: 'lemma_gloss', alan: 'anlam_kisa' });
    expect(isGlossEditable(gloss)).toBe(true);
    expect(isGlossEditable({ ...gloss, durum: 'onaylandi' })).toBe(false);
    expect(isGlossEditable({ ...gloss, hedef_tablo: 'lemma', alan: 'status' })).toBe(false);
    expect(isGlossEditable({ ...gloss, hedef_tablo: 'quran_word_fix', alan: 'lemma_id' })).toBe(
      false,
    );
    expect(isGlossEditable(reviewItem())).toBe(false);
  });

  it('proposes the editor value first, then the candidate, else null', () => {
    expect(
      proposedGloss(
        reviewItem({
          onerilen: { anlam_kisa: 'Deneme öneri' },
          duzenlenen: { anlam_kisa: 'Deneme editör' },
        }),
      ),
    ).toBe('Deneme editör');
    expect(proposedGloss(reviewItem({ onerilen: { anlam_kisa: 'Deneme öneri' } }))).toBe(
      'Deneme öneri',
    );
    expect(proposedGloss(reviewItem({ onerilen: { baska: 1 }, duzenlenen: null }))).toBeNull();
  });
});
