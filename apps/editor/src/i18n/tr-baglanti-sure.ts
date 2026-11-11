// Visible text of the link candidates queue (kuyruk/baglanti) and the surah name queue (kuyruk/sure-adi), Turkish.
// Same rules as tr.ts: screens carry no literals. Label tables map the API's values to Turkish; an unknown
// value is shown raw (labelOf).

export const trBaglanti = {
  detailHeading: 'Bağlantı adayı',
  sourceParagraph: 'Paragraf',
  candidateAyah: 'Aday âyet',
  meal: 'Meal',
  noAnchors: 'Bu kayıt için kaynak ve hedef çapa bilgisi yok.',
  textLoading: 'Metin yükleniyor',
  textFailed: 'Metin alınamadı.',
  mealNotShown: 'Hedef bir âyet olmadığı için meal gösterilmez.',
  selectedCount: (count: number) => `${count} kayıt seçildi`,
  selectShort: 'Seç',
  selectRow: (anchor: string) => `Toplu onay için seç: ${anchor}`,
  bulkRegion: 'Toplu onay',
  missing: {
    highlighted: 'Vurgulu dizi',
    evidence: 'Kanıt özeti',
    alternatives: 'Alternatifler',
    ordering: 'Sıralama: tutarsız, toplu, gri bölge',
  },
  closed: {
    changeTarget: 'Hedefi değiştir',
    fixRange: 'Aralığı düzelt',
    changeType: 'Tür değiştir',
    ima: 'İma',
    patternList: 'Kalıp listesi',
    bulkSelect: 'Toplu seçim',
  },
  closedActions: 'Henüz çalışmayan işlemler',
} as const;

export const trSureAdi = {
  groupHeading: (no: number) => `Sure ${no}`,
  unknownGroup: 'Sure numarası okunamadı',
  groupCount: (count: number, selectable: number) =>
    `${count} aday, ${selectable} tanesi toplu seçilebilir`,
  noSelectable: 'Bu grupta toplu seçilebilir ad yok; riskli adlar tek tek onaylanır.',
  selectGroup: 'Grubu seç',
  clearGroup: 'Grup seçimini kaldır',
  selectGroupHint: (no: number) => `Sure ${no}: riskli adlar seçilmez.`,
  selectRow: (alias: string) => `Toplu onay için seç: ${alias}`,
  riskyOnlySingle: 'Riskli ad: yalnız tek tek karar verilir.',
  riskUnknownOnlySingle: 'Risk bilgisi okunamadı; yalnız tek tek karar verilir.',
  riskyBadge: 'Riskli ad',
  anlam: 'Anlam',
  yazimlar: 'Öteki yazımlar',
  kaynaklar: 'Kaynaklar',
  file: 'dosya',
  line: 'satır',
  noPayload: 'Önerilen değer okunamadı; kayıt ham haliyle gösteriliyor.',
  tanzilFarkTitle: 'Tanzil ile fark var',
  tanzilFarkHint:
    'Kaynak listesindeki değer Tanzil üst verisinden farklı; onaylamadan önce denetleyin.',
  tanzilField: 'Alan',
  tanzilWikipedia: 'Vikipedi',
  tanzilTanzil: 'Tanzil',
  selectedCount: (count: number) => `${count} ad seçildi`,
  rowMarked: 'Toplu onayda sorunlu; Toplu onay bölümüne bakın.',
  bulkRegion: 'Toplu onay',
  detailHeading: 'Sure adı adayı',
  singleOnlyNote: 'Ret ve riskli adlar yalnız tek tek, bu formdan verilir.',
  labels: {
    kind: {
      kanonik: 'Kanonik ad',
      yazim: 'Yazım',
      diger_ad: 'Diğer ad',
      arapca: 'Arapça',
    },
    tanzilField: {
      ayet: 'Âyet sayısı',
      yer: 'İniş yeri',
      inis_sirasi: 'İniş sırası',
    },
  },
} as const;
