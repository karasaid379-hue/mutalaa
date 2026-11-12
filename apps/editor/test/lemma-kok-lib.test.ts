import { describe, expect, it } from 'vitest';
import { isObjectionPayload, readObjectionReason, readRootMapping } from '@/lib/payload';
import {
  isObjectionReview,
  isRootMappingEditable,
  isRootMappingReview,
  parseIdInput,
  proposedMapping,
} from '@/review/rules';
import {
  APPROVAL_FILTERS,
  isApprovalFilter,
  itemApproval,
  matchesApprovalFilter,
  readApprovalPath,
} from '@/screens/lemma/approval';
import { kokDetail, kokItem, objectionItem, trTarget } from './fixtures-lemma';

describe('readRootMapping', () => {
  it('reads the three fields and drops anything that is not a positive integer or a boolean', () => {
    expect(readRootMapping({ root_id: 7, ar_lemma_id: 1001, etymological_only: true })).toEqual({
      rootId: 7,
      arLemmaId: 1001,
      etymologicalOnly: true,
    });
    expect(readRootMapping({ root_id: 7 })).toEqual({
      rootId: 7,
      arLemmaId: null,
      etymologicalOnly: null,
    });
    expect(readRootMapping({ root_id: '7', ar_lemma_id: 0, etymological_only: 'evet' })).toBeNull();
    expect(readRootMapping({ root_id: 1.5 })).toBeNull();
    expect(readRootMapping(null)).toBeNull();
    expect(readRootMapping('metin')).toBeNull();
    expect(readRootMapping([1, 2])).toBeNull();
  });
});

describe('objection payload', () => {
  it('is an objection only when itiraz is exactly true', () => {
    expect(isObjectionPayload({ itiraz: true, gerekce: 'Neden' })).toBe(true);
    expect(isObjectionPayload({ itiraz: 'true' })).toBe(false);
    expect(isObjectionPayload({ root_id: 7 })).toBe(false);
    expect(isObjectionPayload(null)).toBe(false);
    expect(readObjectionReason({ itiraz: true, gerekce: 'Neden' })).toBe('Neden');
    expect(readObjectionReason({ itiraz: false, gerekce: 'Neden' })).toBeNull();
  });
});

describe('root mapping rules', () => {
  it('knows the review: lemma + kok_eslemesi, and a candidate is editable, an objection or a closed one is not', () => {
    expect(isRootMappingReview(kokItem(1))).toBe(true);
    expect(isRootMappingReview({ hedef_tablo: 'lemma', alan: 'status' })).toBe(false);
    expect(isRootMappingReview({ hedef_tablo: 'lemma_gloss', alan: 'kok_eslemesi' })).toBe(false);
    expect(isRootMappingEditable(kokItem(1))).toBe(true);
    expect(isRootMappingEditable(kokItem(1, { durum: 'onaylandi' }))).toBe(false);
    expect(isObjectionReview(objectionItem(2))).toBe(true);
    expect(isRootMappingEditable(objectionItem(2))).toBe(false);
  });

  it('proposes the edited value, else the proposal, else the lemma row', () => {
    expect(
      proposedMapping(
        kokDetail(1, { duzenlenen: { root_id: 9, ar_lemma_id: null, etymological_only: true } }),
      ),
    ).toEqual({ rootId: 9, arLemmaId: null, etymologicalOnly: true });
    expect(proposedMapping(kokDetail(1))).toEqual({
      rootId: 7,
      arLemmaId: 1001,
      etymologicalOnly: false,
    });
    expect(
      proposedMapping(
        kokDetail(1, { onerilen: null, hedef: trTarget(1, { root_id: 5, ar_lemma_id: null }) }),
      ),
    ).toEqual({ rootId: 5, arLemmaId: null, etymologicalOnly: false });
    expect(proposedMapping(kokDetail(1, { onerilen: null, hedef: null }))).toEqual({
      rootId: null,
      arLemmaId: null,
      etymologicalOnly: null,
    });
  });

  it('parses a typed id: empty is none, plain positive digits within 32 bits are a number, the rest invalid', () => {
    expect(parseIdInput('')).toBeNull();
    expect(parseIdInput('7')).toBe(7);
    expect(parseIdInput('2147483647')).toBe(2147483647);
    for (const bad of ['0', '-3', '1.5', ' 7', '7 ', '12x', '2147483648', '٣', '1e3']) {
      expect(parseIdInput(bad)).toBe('invalid');
    }
  });
});

describe('approval path', () => {
  it('reads otomatik and editor only', () => {
    expect(readApprovalPath('otomatik')).toBe('otomatik');
    expect(readApprovalPath('editor')).toBe('editor');
    expect(readApprovalPath('Otomatik')).toBeNull();
    expect(readApprovalPath(null)).toBeNull();
    expect(readApprovalPath(undefined)).toBeNull();
  });

  it('classifies a listed review: a candidate, or an objection by the path in onceki; unreadable is null', () => {
    expect(itemApproval(kokItem(1))).toBe('aday');
    expect(itemApproval(objectionItem(2, 'otomatik'))).toBe('otomatik');
    expect(itemApproval(objectionItem(3, 'editor'))).toBe('editor');
    expect(itemApproval(objectionItem(4, null))).toBeNull();
  });

  it('filters: "hepsi" passes everything, the others exactly their class', () => {
    expect(APPROVAL_FILTERS).toEqual(['hepsi', 'otomatik', 'editor', 'aday']);
    expect(isApprovalFilter('aday')).toBe(true);
    expect(isApprovalFilter('baska')).toBe(false);
    const unreadable = objectionItem(4, null);
    expect(matchesApprovalFilter(unreadable, 'hepsi')).toBe(true);
    for (const filter of ['otomatik', 'editor', 'aday'] as const) {
      expect(matchesApprovalFilter(unreadable, filter)).toBe(false);
    }
    expect(matchesApprovalFilter(kokItem(1), 'aday')).toBe(true);
    expect(matchesApprovalFilter(kokItem(1), 'otomatik')).toBe(false);
  });
});
