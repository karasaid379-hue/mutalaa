/** `If-Match` value of a review: `"{xmin}"` (strong, single tag; never `*` or `W/`). */
export function formatIfMatch(xmin: number): string {
  return `"${xmin}"`;
}
