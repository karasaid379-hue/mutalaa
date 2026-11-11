import { tr } from '@/i18n/tr';
import { PROBLEM_TYPE_PREFIX, type Problem } from './problem';

/** The operation a problem belongs to; it selects the wording (Turkish messages differ per operation). */
export type ProblemContext = 'decision' | 'bulk' | 'correction' | 'release' | 'login';

type MessageTable = Readonly<Record<string, string>>;

const OFFSET_MARKER = 'Ofsetli';

/** `kod` of a problem; taken from `type` when the body has no `kod`; '' when neither is usable. */
export function kodOf(problem: Problem): string {
  if (typeof problem.kod === 'string' && problem.kod !== '') return problem.kod;
  if (typeof problem.type === 'string' && problem.type.startsWith(PROBLEM_TYPE_PREFIX)) {
    return problem.type.slice(PROBLEM_TYPE_PREFIX.length);
  }
  return '';
}

/** Whether the server's own message says the 422 is about offset-bearing fields (marks, sentences). */
function isOffsetUnsupported(problem: Problem): boolean {
  return (
    kodOf(problem) === 'inceleme-desteklenmiyor' && (problem.detail ?? '').includes(OFFSET_MARKER)
  );
}

/** The Turkish message of a problem for an operation; unknown codes are shown raw, never guessed. */
export function problemText(problem: Problem, context?: ProblemContext): string {
  const kod = kodOf(problem);
  if (isOffsetUnsupported(problem) && context !== 'bulk') return tr.problem.offsetUnsupported;
  if (context) {
    const overrides: MessageTable = tr.problem.contexts[context];
    if (Object.hasOwn(overrides, kod)) return overrides[kod] ?? '';
  }
  if (kod === '') return tr.problem.codes['yanit-bozuk'];
  const codes: MessageTable = tr.problem.codes;
  return Object.hasOwn(codes, kod) ? (codes[kod] ?? '') : tr.problem.unknownCode(kod);
}

/** Codes whose server message adds information the Turkish text does not carry. */
const DETAIL_CODES: readonly string[] = [
  'dogrulama',
  'capa-gecersiz',
  'degistirilemez-metin',
  'durum-gecisi-gecersiz',
  'cakisma',
  'inceleme-desteklenmiyor',
  'hata',
];

export function showsServerDetail(problem: Problem): boolean {
  return !!problem.detail && DETAIL_CODES.includes(kodOf(problem)) && !isOffsetUnsupported(problem);
}
