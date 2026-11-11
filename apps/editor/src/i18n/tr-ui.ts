// Visible and screen-reader text of the shared UI parts added in the A15 review fixes (part 2). Same rules as
// tr.ts: components carry no literals.

export const trUi = {
  /** Name of the toast region (the toast component is kept but no toast is raised yet). */
  toastRegion: 'Bildirimler',
  /** Hidden text around the marked words of a text difference, so that the meaning is not carried by colour. */
  diff: {
    removedStart: 'Silinen metin başı. ',
    removedEnd: ' Silinen metin sonu. ',
    addedStart: 'Eklenen metin başı. ',
    addedEnd: ' Eklenen metin sonu. ',
  },
} as const;
