export const packageName = '@mutalaa/search' as const;

export {
  NORMALIZER_VERSION,
  normalizeAr,
  normalizeTr,
  searchKeys,
  splitScripts,
} from './normalize.js';
export type { SearchKeys, TrKey } from './normalize.js';
