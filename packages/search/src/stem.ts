// Turkish stem key (`tr_stem`, K-36 item 6, device half K-44 item 1). Same result as the Python
// reference (mutalaa_pipeline.normalize.turkish.tr_stem); locked by normalize/tr-govde.jsonl.
//
// Per narrow word: only a-circumflex, i-circumflex and u-circumflex are folded (the Snowball
// vowel set is `a e i-dotless i o o-umlaut u u-umlaut` only), the Snowball Turkish stem is taken,
// then the wide fold is applied; an empty result or one without a letter or number falls back to
// the wide form of the word. Word count and order equal the wide key.
import TurkishStemmer from 'snowball-stemmers-js/lib/turkish-stemmer.js';
import { foldWide, hasLetterOrNumber, narrowWords } from './normalize.js';

/** Only these three are folded before stemming (explicit map, no locale involved). */
const CIRCUMFLEX: ReadonlyMap<string, string> = new Map([
  ['â', 'a'],
  ['î', 'i'],
  ['û', 'u'],
]);

let stemmer: TurkishStemmer | undefined;

function foldCircumflex(word: string): string {
  let out = '';
  for (const ch of word) out += CIRCUMFLEX.get(ch) ?? ch;
  return out;
}

/** Stem of one narrow word, wide folded; the wide form of the word when no usable stem remains. */
function stemWord(narrow: string): string {
  stemmer ??= new TurkishStemmer();
  const folded = foldWide(stemmer.stemWord(foldCircumflex(narrow)));
  if (folded === '' || !hasLetterOrNumber(folded)) return foldWide(narrow);
  return folded;
}

/**
 * Stem key of a text: the stems of its narrow Turkish words joined by one U+0020. Arabic-script
 * parts are not part of it (they go to `ar_norm`).
 */
export function stemTr(text: string): string {
  return narrowWords(text).map(stemWord).join(' ');
}
