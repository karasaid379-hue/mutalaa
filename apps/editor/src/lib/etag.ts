/** `If-Match` value of a review: `"{xmin}"` (strong, single tag; never `*` or `W/`). */
export function formatIfMatch(xmin: number): string {
  return `"${xmin}"`;
}

/**
 * `If-Match` value of a Risale book approval: `"{ozet}"`, the 64 lowercase hex digits of `GET /risale/books/{kitap}`
 * (`ozet`; the same text is its `ETag`). Strong, single tag (K-51 madde 11).
 */
export function formatBookIfMatch(digest: string): string {
  return `"${digest}"`;
}
