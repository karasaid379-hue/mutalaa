// All user-visible text of the editor panel lives here (Turkish). Components never carry literals:
// the ESLint rules in eslint.config.mjs reject JSX text and literal aria-label/title/placeholder/alt.
export const tr = {
  app: {
    title: 'Mütâlaa Editör',
  },
  ui: {
    close: 'Kapat',
    closeToast: 'Bildirimi kapat',
    previous: 'Önceki',
    next: 'Sonraki',
    more: 'Daha fazla',
    loading: 'Yükleniyor',
    toggleSidebar: 'Kenar çubuğunu aç/kapat',
  },
} as const;
