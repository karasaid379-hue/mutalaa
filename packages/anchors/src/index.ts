export const packageName = '@mutalaa/anchors' as const;

export type { Anchor, AnchorRef, Span } from './types.js';
export { AnchorError } from './errors.js';
export type { AnchorErrorCode } from './errors.js';
export { parse, tryParse } from './parse.js';
export { format } from './format.js';
export { compare } from './compare.js';
export { contains } from './contains.js';
export { toRoute, fromRoute } from './route.js';
export { unitOf, toUnitSpan, coveredAyahs } from './unit.js';
export { cpToUtf16, utf16ToCp, snapSpan } from './offsets.js';
