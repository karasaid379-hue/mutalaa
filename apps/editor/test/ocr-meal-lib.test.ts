// Pure helpers of the meal queue (A16.5, K-49): the filter of a tab, the edition of an anchor, the readers of the
// pipeline fields and the edit rule for a joined meal follower. Texts are made up.
import { describe, expect, it } from 'vitest';
import { readMealAttrs, readPipelineExtras } from '@/lib/payload';
import { reviewListInit } from '@/review/queries';
import { canEditValue } from '@/review/rules';
import {
  OCR_SOURCE_TABS,
  OCR_STAGE_VIEWS,
  isOcrSourceTab,
  isOcrStageView,
  ocrFilter,
} from '@/screens/ocr/config';
import { MEAL_SOURCE_SLUG, mealEditionOf } from '@/screens/ocr/meal-source';
import { reviewItem, unitDetail } from './fixtures';

describe('reviewListInit', () => {
  it('adds kaynak and asama only when they are given', () => {
    const plain = reviewListInit({ hedef_tablo: 'unit', alan: 'metin' }).params.query;
    expect(Object.keys(plain)).toEqual(['hedef_tablo', 'alan', 'durum', 'limit']);
    const full = reviewListInit({
      hedef_tablo: 'unit',
      alan: 'metin',
      kaynak: 'elmalili-meal',
      asama: 'ikinci',
    }).params.query;
    expect(full).toMatchObject({ kaynak: 'elmalili-meal', asama: 'ikinci', durum: 'acik' });
  });
});

describe('ocrFilter', () => {
  it('maps the source tabs to the source slugs and the stage views to asama', () => {
    expect(ocrFilter('hepsi', 'hepsi')).toEqual({ hedef_tablo: 'unit', alan: 'metin' });
    expect(ocrFilter('orijinal', 'hepsi')).toMatchObject({ kaynak: 'elmalili-meal' });
    expect(ocrFilter('sade', 'hepsi')).toMatchObject({ kaynak: 'elmalili-sade-meal' });
    expect(ocrFilter('sade', 'ikinci')).toEqual({
      hedef_tablo: 'unit',
      alan: 'metin',
      kaynak: 'elmalili-sade-meal',
      asama: 'ikinci',
    });
    expect(ocrFilter('hepsi', 'ilk')).toEqual({ hedef_tablo: 'unit', alan: 'metin', asama: 'ilk' });
  });

  it('recognizes only its own tab and view ids', () => {
    expect(OCR_SOURCE_TABS.every(isOcrSourceTab)).toBe(true);
    expect(OCR_STAGE_VIEWS.every(isOcrStageView)).toBe(true);
    expect(isOcrSourceTab('baska')).toBe(false);
    expect(isOcrStageView(null)).toBe(false);
  });
});

describe('mealEditionOf', () => {
  it('tells the two Elmalılı meals apart by the meal id of the anchor', () => {
    expect(mealEditionOf('meal:elmalili:2:255')).toBe('orijinal');
    expect(mealEditionOf('meal:elmalili-sade:2:255')).toBe('sade');
  });

  it('is null for another meal, another anchor kind or text that is not an anchor', () => {
    expect(mealEditionOf('meal:deneme:2:255')).toBeNull();
    expect(mealEditionOf('q:2:255')).toBeNull();
    expect(mealEditionOf('rn:deneme:p1')).toBeNull();
    expect(mealEditionOf('bozuk')).toBeNull();
    expect(mealEditionOf('meal:Elmalili:2:255')).toBeNull();
  });

  it('keeps the source slugs of K-49', () => {
    expect(MEAL_SOURCE_SLUG).toEqual({ orijinal: 'elmalili-meal', sade: 'elmalili-sade-meal' });
  });
});

describe('readPipelineExtras', () => {
  const witness = {
    skor: 97,
    kapsam: [1, 2],
    yontem: 'rapidfuzz.fuzz.ratio/tr_narrow',
    yontem_surumu: '1',
    kaynak: 'elmalili-meal-epub',
  };

  it('reads the warning codes and the whole witness agreement', () => {
    expect(readPipelineExtras({ uyari: ['birlesik_meal', '', 'sira_disi', 3] }).uyarilar).toEqual([
      'birlesik_meal',
      'sira_disi',
    ]);
    expect(readPipelineExtras({ tanik: witness }).tanik).toEqual({
      skor: 97,
      kapsam: [1, 2],
      yontem: 'rapidfuzz.fuzz.ratio/tr_narrow',
      yontemSurumu: '1',
      kaynak: 'elmalili-meal-epub',
    });
  });

  it('reads a null or malformed kapsam as absent', () => {
    for (const kapsam of [null, [1], [1, 2, 3], ['1', '2'], [1, Number.NaN], 'q:2:1']) {
      expect(readPipelineExtras({ tanik: { ...witness, kapsam } }).tanik?.kapsam).toBeNull();
    }
  });

  it('does not read a single string as a warning list', () => {
    expect(readPipelineExtras({ uyari: 'numarasiz_parca' }).uyarilar).toEqual([]);
  });

  it('reads anything else as absent and never throws', () => {
    for (const value of [
      null,
      undefined,
      'metin',
      7,
      [],
      { uyari: 5, tanik: 'x' },
      { uyari: [] },
    ]) {
      expect(readPipelineExtras(value)).toEqual({ uyarilar: [], tanik: null });
    }
    expect(readPipelineExtras({ tanik: { skor: Number.NaN } }).tanik).toBeNull();
    expect(readPipelineExtras({ tanik: {} }).tanik).toBeNull();
  });
});

describe('readMealAttrs', () => {
  it('reads kapsam, the follower link and the basmala meal', () => {
    const attrs = readMealAttrs({
      kapsam: 'q:2:1-2',
      besmele_meali: { metin: 'Deneme besmele meali', content_hash: 'h' },
    });
    expect(attrs).toEqual({
      kapsam: 'q:2:1-2',
      follower: false,
      headAnchor: null,
      besmele: { metin: 'Deneme besmele meali', contentHash: 'h' },
    });
    expect(readMealAttrs({ birlesik_ile: 'meal:elmalili:2:1' })).toMatchObject({
      follower: true,
      headAnchor: 'meal:elmalili:2:1',
    });
  });

  it('counts a follower like the server: any non-null, non-empty birlesik_ile', () => {
    expect(readMealAttrs({ birlesik_ile: ['meal:elmalili:2:1'] })).toMatchObject({
      follower: true,
      headAnchor: null,
    });
    for (const attrs of [{ birlesik_ile: null }, { birlesik_ile: '' }, {}, null, undefined, 'x']) {
      expect(readMealAttrs(attrs).follower).toBe(false);
    }
  });

  it('ignores a basmala meal without text', () => {
    expect(readMealAttrs({ besmele_meali: { content_hash: 'h' } }).besmele).toBeNull();
    expect(readMealAttrs({ besmele_meali: 'x' }).besmele).toBeNull();
  });
});

describe('canEditValue and a joined meal follower', () => {
  const review = reviewItem({ hedef_anahtar: 'meal:elmalili:2:2' });
  const unit = (attrs: unknown) =>
    unitDetail({ kind: 'meal', kaynak_tur: 'meal', duzeltilebilir: true, attrs });

  it('closes the edit field of the follower and keeps it open for the head unit', () => {
    expect(canEditValue(review, unit({ birlesik_ile: 'meal:elmalili:2:1' }))).toBe(false);
    expect(canEditValue(review, unit({ kapsam: 'q:2:1-2' }))).toBe(true);
    expect(canEditValue(review, unit({}))).toBe(true);
  });
});
