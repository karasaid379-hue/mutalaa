import { isRecord, readArray, readNumber, readString } from './record';

// Run-time readers of the meal fields the content pipeline writes (K-49 madde 8 and 9). Nothing is trusted: a
// value of an unexpected shape reads as absent.

/**
 * `onerilen.tanik` of a pipeline record (export/pg_meal.py `onerilen_kur`): the agreement with a second copy of the
 * text. `skor` is an integer from 0 to 100; `kapsam` is `[ilk, son]` or null; `yontem` and `yontem_surumu` name the
 * measure; `kaynak` is the witness source.
 */
export interface WitnessScore {
  skor: number | null;
  kapsam: readonly [number, number] | null;
  yontem: string | null;
  yontemSurumu: string | null;
  kaynak: string | null;
}

/** What the pipeline adds next to `{metin, content_hash}` in `onerilen`: warning codes and the witness agreement. */
export interface PipelineExtras {
  /** `uyari`: code strings (`birlesik_meal`, `ortak_metin`, ...); the screen maps each to a Turkish sentence. */
  uyarilar: string[];
  tanik: WitnessScore | null;
}

/** `kapsam` as a pair of finite numbers; anything else reads as absent. */
function readRange(value: unknown): readonly [number, number] | null {
  if (!isRecord(value)) return null;
  const range = readArray(value, 'kapsam');
  if (range === null || range.length !== 2) return null;
  const [first, last] = range;
  return typeof first === 'number' &&
    Number.isFinite(first) &&
    typeof last === 'number' &&
    Number.isFinite(last)
    ? [first, last]
    : null;
}

/** Reads `uyari` (an array of code strings) and `tanik` of a review payload (`onerilen`). */
export function readPipelineExtras(value: unknown): PipelineExtras {
  const codes = readArray(value, 'uyari') ?? [];
  const witness = isRecord(value) ? value['tanik'] : undefined;
  const skor = readNumber(witness, 'skor');
  const kapsam = readRange(witness);
  const yontem = readString(witness, 'yontem');
  const yontemSurumu = readString(witness, 'yontem_surumu');
  const kaynak = readString(witness, 'kaynak');
  const hasWitness = skor !== null || kapsam !== null || yontem !== null || kaynak !== null;
  return {
    uyarilar: codes.filter((code): code is string => typeof code === 'string' && code !== ''),
    tanik: hasWitness ? { skor, kapsam, yontem, yontemSurumu, kaynak } : null,
  };
}

/** `attrs.besmele_meali`: the separately taken basmala meal of a surah (canonical text and its hash). */
export interface BasmalaMeal {
  metin: string;
  contentHash: string | null;
}

/** Meal facts kept in the `attrs` of a unit. */
export interface MealAttrs {
  /** `attrs.kapsam`: the ayah range a joined meal covers (`q:{sure}:{ilk}-{son}`); on the head unit. */
  kapsam: string | null;
  /** True when `attrs.birlesik_ile` is filled: the unit follows a joined meal and has no text of its own. */
  follower: boolean;
  /** `attrs.birlesik_ile` as an anchor (the head unit); null when it is not a string. */
  headAnchor: string | null;
  besmele: BasmalaMeal | null;
}

/** Reads the meal fields of `attrs`. `birlesik_ile` counts like on the server: any non-null, non-empty value. */
export function readMealAttrs(attrs: unknown): MealAttrs {
  const raw = isRecord(attrs) ? attrs['birlesik_ile'] : undefined;
  const follower = raw !== undefined && raw !== null && raw !== '';
  const besmeleRaw = isRecord(attrs) ? attrs['besmele_meali'] : undefined;
  const besmeleText = readString(besmeleRaw, 'metin');
  return {
    kapsam: readString(attrs, 'kapsam'),
    follower,
    headAnchor: typeof raw === 'string' && raw !== '' ? raw : null,
    besmele:
      besmeleText === null
        ? null
        : { metin: besmeleText, contentHash: readString(besmeleRaw, 'content_hash') },
  };
}
