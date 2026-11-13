import { tryParse } from '@mutalaa/anchors';
import type { DecisionEdit } from '@/review/types';

// The edit of a link candidate that goes with "Onayla" (K-48 madde 2, `duzenlenen`): a new target anchor, a corrected
// target span and a changed type. The checks only save a round trip: the API checks again and has the last word.
// Anchors are read with `@mutalaa/anchors` only. The body follows the server's rules: nothing that equals the
// current value is sent, and a target anchor that carries its own span (a word range, `@a-b`) never goes with
// `dst_span`.

/** The types an editor may change between (K-48 madde 2); every other type is fixed. */
export const EDITABLE_TYPES = ['atif', 'iktibas', 'ima'] as const;
export type EditableType = (typeof EDITABLE_TYPES)[number];

export function isEditableType(value: unknown): value is EditableType {
  return EDITABLE_TYPES.some((type) => type === value);
}

/** What the editor typed: empty strings mean "do not change". */
export interface LinkEditInput {
  dstAnchor: string;
  spanStart: string;
  spanEnd: string;
  type: '' | EditableType;
}

export const EMPTY_LINK_EDIT: LinkEditInput = {
  dstAnchor: '',
  spanStart: '',
  spanEnd: '',
  type: '',
};

/** The values the record has now (`hedef`). */
export interface LinkEditContext {
  currentType: string | null;
  currentDst: string | null;
}

export type LinkEditProblemCode =
  | 'anchorInvalid'
  | 'anchorRange'
  | 'anchorSentence'
  | 'anchorKind'
  | 'spanBoth'
  | 'spanInt'
  | 'spanOrder'
  | 'spanWordStart'
  | 'spanConflict';

export interface LinkEditProblem {
  field: 'dstAnchor' | 'span';
  code: LinkEditProblemCode;
}

export interface LinkEditResult {
  /** The `duzenlenen` body; null when nothing changes or while there are problems. */
  value: DecisionEdit | null;
  problems: readonly LinkEditProblem[];
  /** The typed anchor carries its own span (a word range or `@a-b`): the span fields are closed. */
  anchorCarriesSpan: boolean;
}

interface ParsedTarget {
  kind: string;
  carriesSpan: boolean;
}

function parseTarget(text: string): { target: ParsedTarget } | { problem: LinkEditProblemCode } {
  const ref = tryParse(text);
  if (ref === null) return { problem: 'anchorInvalid' };
  const anchor = ref.anchor;
  if (anchor.t === 'qa') return { problem: 'anchorRange' };
  if (anchor.t === 'rn' && anchor.s !== undefined) return { problem: 'anchorSentence' };
  const carriesSpan = ref.span !== undefined || (anchor.t === 'q' && anchor.ilk !== undefined);
  return { target: { kind: anchor.t, carriesSpan } };
}

/** Largest integer the API reads (a 32 bit integer). */
const MAX_BOUND = 2_147_483_647;

/** A span bound typed into a field: plain digits (no sign, no leading zero), at most a 32 bit integer; else null. */
function parseBound(text: string): number | null {
  if (!/^(0|[1-9][0-9]*)$/.test(text)) return null;
  const value = Number(text);
  return Number.isSafeInteger(value) && value <= MAX_BOUND ? value : null;
}

/** Applies the checks and builds the `duzenlenen` body of the approval. */
export function resolveLinkEdit(input: LinkEditInput, context: LinkEditContext): LinkEditResult {
  const problems: LinkEditProblem[] = [];
  const anchorText = input.dstAnchor.trim();
  const effectiveType = input.type !== '' ? input.type : context.currentType;

  let target: ParsedTarget | null = null;
  if (anchorText !== '') {
    const parsed = parseTarget(anchorText);
    if ('problem' in parsed) {
      problems.push({ field: 'dstAnchor', code: parsed.problem });
    } else {
      target = parsed.target;
      // A human-approved type needs an ayah or a hadith as its target (server rule).
      if (isEditableType(effectiveType) && target.kind !== 'q' && target.kind !== 'h') {
        problems.push({ field: 'dstAnchor', code: 'anchorKind' });
      }
    }
  }
  const anchorCarriesSpan = target?.carriesSpan === true;

  let span: [number, number] | null = null;
  const startText = input.spanStart.trim();
  const endText = input.spanEnd.trim();
  if (startText !== '' || endText !== '') {
    if (startText === '' || endText === '') {
      problems.push({ field: 'span', code: 'spanBoth' });
    } else {
      const start = parseBound(startText);
      const end = parseBound(endText);
      if (start === null || end === null) {
        problems.push({ field: 'span', code: 'spanInt' });
      } else if (start >= end) {
        problems.push({ field: 'span', code: 'spanOrder' });
      } else if (anchorCarriesSpan) {
        problems.push({ field: 'span', code: 'spanConflict' });
      } else {
        const targetKind = target?.kind ?? kindOf(context.currentDst);
        if (targetKind === 'q' && start < 1) {
          problems.push({ field: 'span', code: 'spanWordStart' });
        } else {
          span = [start, end];
        }
      }
    }
  }

  if (problems.length > 0) return { value: null, problems, anchorCarriesSpan };

  const value: DecisionEdit = {};
  if (anchorText !== '' && anchorText !== context.currentDst) value.dst_anchor = anchorText;
  if (span !== null) value.dst_span = span;
  if (input.type !== '' && input.type !== context.currentType) value.type = input.type;
  return { value: Object.keys(value).length === 0 ? null : value, problems, anchorCarriesSpan };
}

function kindOf(anchor: string | null): string | null {
  if (anchor === null) return null;
  const ref = tryParse(anchor);
  return ref === null ? null : ref.anchor.t;
}
