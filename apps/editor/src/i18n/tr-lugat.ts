// Visible text of the Risale lügat tab (kuyruk/lemma, fourth tab; K-51 madde 9, 10 and 14), Turkish. Same rules as
// tr.ts: screens carry no literals. The reference meanings are unapproved reference data: they are shown with
// that label and are never offered as the definition.

export const trLugat = {
  heading: 'Lügat maddesi',
  decisionNote:
    'Lügat kaynağından gelen tanım varsa değiştirmeden onaylayabilir ya da düzenleyip onaylayabilirsiniz; tanımsız maddede tanımı kendiniz yazın. Anlam başvurusu tanım olarak onaylanmaz. Reddederseniz madde pakete girmez.',
  /** Readable names of the lügat sources, by `source_id`; the attribution is the source's own name. An unknown id is shown as is. */
  sources: {
    'lugat-rnk': 'RNK lügatı',
    'lugat-sozluk-rganeyev': 'rganeyev/Sozluk',
    'risale-kelime-frekans': 'Risale başlık söz listesi',
  } as Readonly<Record<string, string>>,
  meaning: (no: number) => `Anlam ${no}`,
  list: {
    line: (frequency: string) => `Sıklık ${frequency}`,
    noFrequency: 'Sıklık bilgisi yok',
    meaningSource: (source: string, no: number) => `${source} · Anlam ${no}`,
  },
  snapshot: {
    heading: 'Madde',
    missing: 'Maddenin anlık görünümü yok (kayıt silinmiş ya da okunamıyor).',
    headword: 'Başlık söz',
    source: 'Kaynak',
    meaning: 'Anlam sırası',
    ottoman: 'Osmanlıca yazım',
    etymology: 'Köken dili',
    level: 'Düzey',
    definition: 'Tanım',
    sourceDefinition: 'Tanım (kaynaktan, onaysız)',
    noDefinition: 'Henüz tanım yazılmadı.',
    origin: 'Maddenin kaynağı',
    version: 'Sürüm',
    status: 'Madde durumu',
    originNames: {
      hat: 'İçerik hattı',
      kaynak: 'Lügat kaynağı',
      editor: 'Editör',
    },
  },
  reference: {
    heading: 'Başvuru (onaysız)',
    note: 'Yalnızca bilgi içindir: tanım olarak onaylanmaz, maddeye ve pakete yazılmaz.',
    frequency: 'Toplam sıklık',
    books: 'Geçtiği kitap',
    booksCount: (count: number) => `${count} kitap`,
    meanings: 'Sözlük anlamları',
    meaningEntry: (count: number) => `${count} kayıt`,
    none: 'Bu kayıtta anlam başvurusu yok.',
    unreadable: 'Önerilen değer okunamadı; ham hali aşağıda.',
    raw: 'Ham değer',
  },
  origin: {
    heading: 'Köken',
    origin: 'Köken',
    proposer: 'Öneren',
    noAi: 'Bu madde yapay zekâ taslağı değildir; ham girdi onaya kadar "Aday" durumundadır.',
  },
  edit: {
    editAndApprove: 'Düzenle ve onayla',
    cancelEdit: 'Düzenlemeden vazgeç',
    unchangedNote:
      'Kaynak tanımı olduğu gibi onaylanır; köken "Lügat kaynağı" kalır. Değiştirmek için "Düzenle ve onayla"yı seçin.',
    label: 'Tanım (düzenle ve onayla)',
    hint: 'Onaylamak için gereklidir; yazdığınız tanım kaydedilir ve köken "Editör" olur. Metin kendi ürettiğimiz metindir; sunucu kaydederken Unicode NFC biçimine çevirir.',
    count: (count: number, max: number) => `${count} / ${max} karakter`,
    empty: 'Tanım boş olamaz; onay için tanımı yazın.',
    tooLong: (count: number, max: number) =>
      `Tanım en çok ${max} karakter olabilir (şimdi ${count}).`,
    unwritable: 'Tanım geçersiz karakter içeriyor (NUL ya da eşleşmemiş vekil karakter).',
    serverInvalid:
      'Sunucu bu tanımı kabul etmedi: boş, en çok 2000 karakteri aşan ya da geçersiz karakter içeriyor olabilir.',
    notCandidate:
      'Onay kabul edilmedi: madde aday değil, kayıt kapalı ya da karar kuralı ihlal edildi.',
    required: 'Lügat maddesi tanım yazılmadan onaylanamaz; tanımı yazın.',
  },
} as const;
