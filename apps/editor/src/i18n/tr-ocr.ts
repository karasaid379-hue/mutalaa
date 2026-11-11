// Visible text of the OCR correction queue (kuyruk/ocr), Turkish. Same rules as tr.ts: screens carry no literals.

export const trOcr = {
  detailHeading: 'OCR satırı',
  unitLoading: 'Birim yükleniyor',
  unitFailed: 'Birim alınamadı; sayfa görseli ve düzeltme kapalı.',
  ayah: {
    heading: 'Tanzil âyeti',
    loading: 'Âyet yükleniyor',
    failed: 'Âyet alınamadı.',
    none: 'Bu birim için bir âyet çapası okunamadı.',
    more: (count: number) => `ve ${count} âyet daha (gösterilmedi)`,
  },
  text: {
    meal: 'Meal',
    unit: 'Birim metni',
    empty: 'Birimin metni boş.',
  },
  diff: {
    heading: 'Önceki ve öneri',
    beforeAfter: 'Önceki metin ile önerilen metin arasındaki fark',
    same: 'Önerilen metin öncekiyle aynı.',
    proposedOnly: 'Önerilen metin (öncesi kayıtlı değil)',
    noProposal: 'Bu kayıtta önerilen metin yok.',
    editedHeading: 'İlk onayda düzenlenen metin',
    editedDiff: 'Önerilen metin ile düzenlenen metin arasındaki fark',
  },
  correct: {
    heading: 'Düzelt',
    openHint:
      'Düzeltmek için karar formunda Onayla’yı seçin; Düzenlenen metin alanı açılır ve metin düzenlenmiş haliyle onaylanır.',
    offsetBlocked:
      'Bu birimin işaret ya da cümle aralıkları var; metin değişince ofsetler kayar. A16’da karara bağlanana kadar düzeltme kapalıdır.',
    notAvailable: 'Bu kayıtta metin düzeltmesi yapılamaz (ikinci onay aşaması ya da kapalı kayıt).',
    immutable: 'Âyet metni düzenlenemez.',
  },
  actions: {
    heading: 'Henüz çalışmayan işlemler',
    fix: 'Düzelt',
    split: 'Böl',
    merge: 'Birleştir',
    uncertain: 'Belirsiz işaretle',
    note: 'Not ekle',
  },
  scan: {
    heading: 'Sayfa görseli',
    notMapped: 'Görsel eşlemesi henüz tanımlı değil (A16)',
    notMappedHint: 'Birimin öznitelikleri baskı ve sayfa bilgisi taşımadığı için görsel istenmedi.',
    loading: 'Sayfa görseli yükleniyor',
    decoding: 'Sayfa görseli çözülüyor',
    failed: 'Sayfa görseli alınamadı.',
    tiffFailed:
      'TIFF görseli çözülemedi; dosya bozuk ya da desteklenmeyen bir sıkıştırma kullanıyor.',
    tooLarge: 'Görsel çok büyük; güvenli bellek sınırını aşıyor, gösterilmedi.',
    unknownFormat: 'Görsel biçimi tanınmadı (TIFF, PNG ya da JPEG bekleniyor).',
    imageFailed: 'Görsel gösterilemedi.',
    retry: 'Görseli yeniden dene',
    downscaled: (width: number, height: number, shownWidth: number, shownHeight: number) =>
      `Görsel büyük olduğu için ${width}×${height} yerine ${shownWidth}×${shownHeight} olarak gösteriliyor.`,
    region: 'Sayfa görseli bölgesi',
    controls: 'Görsel denetimleri',
    zoomIn: 'Yakınlaştır',
    zoomOut: 'Uzaklaştır',
    fit: 'Sığdır',
    keyboardHint:
      'Görsel odaktayken oklarla kaydırın, Ctrl ya da Cmd ile yukarı ve aşağı ok ile yakınlaştırın, Home ile sığdırın.',
    canvasLabel: (baski: string, sayfa: string) => `Tarama sayfası: ${baski} ${sayfa}`,
    imageLabel: (baski: string, sayfa: string) => `Tarama sayfası: ${baski} ${sayfa}`,
  },
} as const;
