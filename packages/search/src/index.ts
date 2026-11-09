export const packageName = '@mutalaa/search' as const;

export {
  NORMALIZER_VERSION,
  normalizeAr,
  normalizeTr,
  searchKeys,
  splitScripts,
} from './normalize.js';
export type { SearchKeys, TrKey } from './normalize.js';
export { stemTr } from './stem.js';
export { MAX_QUERY_CODE_POINTS, buildFtsQuery } from './fts-query.js';
export type { BuildFtsQueryOptions, FtsAddress, FtsQuery, FtsSource } from './fts-query.js';
