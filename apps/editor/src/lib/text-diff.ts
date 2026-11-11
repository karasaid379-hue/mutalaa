import { diffArrays } from 'diff';

// Word level text difference for the "record changed" view after a 412. Words come from Intl.Segmenter
// (UAX 29), the comparison from jsdiff `diffArrays`. A combining mark (Arabic harakat, Turkish accents)
// never becomes a segment of its own: it stays glued to the letter before it, so a changed mark shows
// the whole word as changed instead of splitting a letter from its mark. The texts are compared as they
// are: no normalization (K-26).

const MARK_START = /^\p{M}/u;

const segmenter = new Intl.Segmenter('tr', { granularity: 'word' });

/** Word, space and punctuation segments of `text`; marks stay with their base letter. Joining the result gives `text` back. */
export function segmentWords(text: string): string[] {
  const out: string[] = [];
  for (const part of segmenter.segment(text)) {
    const segment = part.segment;
    if (out.length > 0 && MARK_START.test(segment)) {
      out[out.length - 1] += segment;
    } else {
      out.push(segment);
    }
  }
  return out;
}

export type DiffKind = 'same' | 'added' | 'removed';

export interface DiffPart {
  kind: DiffKind;
  text: string;
}

/** Word level difference between two texts; adjacent parts of one kind are merged. */
export function diffText(before: string, after: string): DiffPart[] {
  const changes = diffArrays(segmentWords(before), segmentWords(after));
  const parts: DiffPart[] = [];
  for (const change of changes) {
    const kind: DiffKind = change.added ? 'added' : change.removed ? 'removed' : 'same';
    const text = change.value.join('');
    if (text === '') continue;
    const last = parts[parts.length - 1];
    if (last && last.kind === kind) last.text += text;
    else parts.push({ kind, text });
  }
  return parts;
}
