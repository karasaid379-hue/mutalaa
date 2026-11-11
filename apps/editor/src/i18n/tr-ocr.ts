// Visible text of the OCR correction queue (kuyruk/ocr), Turkish. Same rules as tr.ts: screens carry no literals.

export const trOcr = {
  detailHeading: 'OCR satırı',
  filters: {
    sourceLabel: 'Kaynak',
    stageLabel: 'Onay aşaması',
    sources: {
      hepsi: 'Tüm kaynaklar',
      orijinal: 'Orijinal meal',
      sade: 'Sadeleştirilmiş meal',
    },
    sourceHints: {
      hepsi: 'Her kaynaktan açık birim metni kayıtları.',
      orijinal: 'Elmalılı meali, orijinal metin.',
      sade: 'Elmalılı meali, sadeleştirilmiş metin; ayrı adlı baskıdır ve orijinal meali değiştirmez.',
    },
    /** Said before the source id, which the screen draws in a `code` element. */
    sourceIdLabel: 'Kaynak kimliği:',
    stages: {
      hepsi: 'Tüm açık kayıtlar',
      ilk: 'İlk onay bekleyenler',
      ikinci: 'İkinci onay bekleyenler',
    },
    stageHints: {
      hepsi: 'Açık kayıtların hepsi.',
      ilk: 'Henüz kimsenin onaylamadığı kayıtlar.',
      ikinci:
        'İlk onayı verilmiş, ikinci onayı bekleyen kayıtlar; ikinci onay başka bir editörden gelmelidir.',
    },
  },
  source: {
    label: 'Kaynak',
    names: {
      orijinal: 'Elmalılı meali',
      sade: 'Elmalılı meali',
    },
    editions: {
      orijinal: 'orijinal',
      sade: 'sadeleştirilmiş',
    },
  },
  hat: {
    warningHeading: 'İçerik hattı uyarısı',
    warningHint: 'Hat bu metni alırken bir durumu işaretledi; karar vermeden önce denetleyin.',
    /** One sentence per warning code of the pipeline (`onerilen.uyari`). */
    warnings: {
      birlesik_meal:
        'Bu âyetin meali komşu âyetlerle birleşik verilmiş; metin başlangıç birimde durur ve kapsam gösterilir.',
      ortak_metin:
        'Kaynakta aynı metin birden çok ardışık olmayan âyete verilmiş; her birim aynı metni taşır. Bölünüp bölünmeyeceği editörün kararıdır.',
      numarasiz_parca: 'Kaynakta numarasız bir parça önceki âyete eklendi.',
      yinelenen_numara:
        'Kaynakta aynı numara birden çok kez geçiyor; parçalar sırayla birleştirildi.',
      sira_disi: 'Kaynakta âyet sırası bozuk.',
      besmele_meali: 'Besmele meali ayrıca alındı.',
    },
    /** Said before the raw code, which the screen draws in a `code` element. */
    unknownWarning: 'Bilinmeyen uyarı kodu:',
    witnessHeading: 'Tanık uyumu',
    witnessScore: (score: string) => `Tanık uyumu %${score}`,
    witnessRange: (first: string, last: string) => `Tanık kapsamı: ${first}–${last}`,
    /** Said before the method and the witness source, which the screen draws in `code` elements. */
    witnessMethodLabel: 'Yöntem:',
    witnessSourceLabel: 'Tanık kaynağı:',
    witnessHint:
      'İkinci bir nüshadan alınan metinle benzerlik oranıdır. Özgün baskıya sadakat ölçüsü değildir; ortak kökenli nüshalar da yüksek çıkabilir.',
  },
  merged: {
    scope: (range: string) =>
      `Birleşik meal: bu birim ${range} aralığındaki âyetlerin mealini birlikte taşır.`,
    followerHeading: 'Birleşik mealin izleyen birimi',
    followerBody:
      'Bu birim kendi metnini taşımaz; metin başlangıç birimdedir. Burada yalnız durum onayı ya da ret verilebilir.',
    headLead: 'Başlangıç birim:',
    headMissing: 'Başlangıç birimin çapası okunamadı.',
    fixClosed: 'Kapalı',
    fixClosedHint:
      'Düzelt kapalı: birleşik mealin metni başlangıç birimde durur; düzeltmeyi oradan önerin.',
  },
  besmele: {
    heading: 'Besmele meali',
    hint: 'Kaynakta açık bir işaretle ayrıca alınmış besmele meali; birimin metnine dahil değildir.',
  },
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
      "Bu birimin ofsetli alanları (işaretler, cümleler) var; metin değişince ofsetler kayar. Metin düzeltmesi A20'de desteklenecek; o zamana kadar düzeltme kapalıdır.",
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
    notMapped: 'Sayfa görseli yok: tarama ve OCR proje sonuna bırakıldı (S-15)',
    notMappedHint:
      'Hazır metin yolunda birimler baskı ve sayfa bilgisi taşımaz; bu yüzden görsel istenmedi.',
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
    pan: 'Kaydır',
    panUp: 'Yukarı kaydır',
    panDown: 'Aşağı kaydır',
    panLeft: 'Sola kaydır',
    panRight: 'Sağa kaydır',
    zoomIn: 'Yakınlaştır',
    zoomOut: 'Uzaklaştır',
    fit: 'Sığdır',
    keyboardHint:
      'Kaydırma düğmeleri ya da, görsel odaktayken, ok tuşları görseli kaydırır; Ctrl ya da Cmd ile yukarı ve aşağı ok yakınlaştırır; Home sığdırır.',
    canvasLabel: (baski: string, sayfa: string) => `Tarama sayfası: ${baski} ${sayfa}`,
    imageLabel: (baski: string, sayfa: string) => `Tarama sayfası: ${baski} ${sayfa}`,
  },
} as const;
