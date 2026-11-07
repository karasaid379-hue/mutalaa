# Ürün Özeti

> **Sürüm:** 1.3 · **Tarih:** 1 Kasım 2026 · **Durum:** Onaylı
> **Bağlı kararlar:** [K-01, K-02, K-07, K-08, K-25](./02-karar-defteri.md) · [K-41](./02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-42](./02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)

## Tek cümlede

**Mütâlaa**, Kur'an-ı Kerîm'i mushaf sayfasında, karşısında meali ve yanında âyeti izleyen tefsiriyle okutan, seçilen hafızla dinleten ve bir kelimeye ya da kelime grubuna dokununca Kur'an'da, tefsirde, hadiste ve Risale-i Nur'da nerede geçtiğini gösterip okunan yere geri döndüren, çevrimdışı çalışan bir okuma ve öğrenme uygulamasıdır.

Ad, "dikkatle okuma, üzerinde düşünerek çalışma" anlamına gelir ve Risale-i Nur'un kendi dağarcığında geçer.

## Çekirdek akış

1. **Oku.** Üç mushaf görünümünden birini seç: A · Medine düzeni, B · Türk hattı, C · akan metin. Mushaf + Meal ya da âyet âyet okuma modlarına geç. Ayrıntı: [Okuma deneyimi](../01-urun/02-okuma-deneyimi.md).
2. **Dinle.** Hafızı seç; âyet vurgulanarak ilerlesin; âyeti ya da aralığı tekrarla, hızı ayarla. Ayrıntı: [Ses sistemi](../06-mobil/02-ses-sistemi.md).
3. **Bağla.** Bir kelimeye ya da kelime grubuna dokun. Bağlantılar paneli sonuçları esere göre gruplar ve her sonucun neden geldiğini söyler. Bir sonuca git, sonra "Okuduğun yere dön" ile geri gel. Ayrıntı: [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md).
4. **Biriktir.** Vurgu, not, yer imi ve hatim ilerlemesi cihazda kalır; hesap ve senkron v1.x'te gelir. Ayrıntı: [Kullanıcı verisi ve senkron](../03-veri/04-kullanici-verisi-ve-senkron.md).

## Kimin için

| Okur | İhtiyacı | Mütâlaa'nın cevabı |
|---|---|---|
| Genel okur | Mushafı ve meali yan yana, sade bir arayüzle okumak | Mushaf + Meal modu, Kâğıt / Âhar / Gece temaları |
| Risale ders halkası okuyucusu | Risale'de geçen âyete hızla ulaşmak, farklı baskıların sayfa numaralarını eşlemek | Âyet ↔ Risale atıf dizini, baskı sayfa eşlemesi, lügat yoğunluğu ayarı |
| İlahiyat öğrencisi | Kök, lemma ve kaynak gösteren bağlantılar | Kelime kartı, kök gezgini, gerekçeli ve güven düzeyli bağlantılar |
| Yaşlı okur | Büyük yazı, net kontrast, kaybolmayan okuma yeri | Ayrı Arapça/Türkçe yazı boyutu, %200 büyütme, akan metin modu, cihaz başına kaldığın yer |

## Neden farklı

Diyanet, vavtv, Hayrat, Açık Kuran, Quran.com ve Risale uygulamaları incelendi. Her biri bir parçayı iyi yapıyor; bu parçaları tek akışta birleştiren yok ([araştırma raporu](../09-kaynakca.md)).

| Boşluk | Bugün en yakın örnek | Mütâlaa'nın cevabı |
|---|---|---|
| Mushaf, sayfaya hizalı meal ve âyeti izleyen tefsir aynı anda | Diyanet iki bölme, vavtv sekmeler, Hayrat ayrı sayfa | Tablette açık kitap, telefonda sekmeler ve tek dokunuşla tefsir |
| Seçilen kelimeden eserler arası geçiş ve geri dönüş | Quran.com Çalışma Modu (Risale ve Türkçe tefsir yok) | Esere göre gruplu Bağlantılar paneli ve geri dönüş yığını |
| Âyet ↔ Risale iki yönlü atıf dizini | Yok | İnsan onaylı atıf tablosu |
| Risale'de Arapça ibarelerin satır içi meali | Yalnız eski bir Android uygulaması | İktibas tespiti ve meal kartı |
| Baskılar arası sayfa eşleme | Yok | `page_map` tablosu |
| Âyet vurgulu, Kur'an + meal dönüşümlü dinleme ve Türk hafızlar | Diyanet dönüşümü, vavtv Türk hafızları sunuyor | Âyet vurgulu dinleme v1'de, Kur'an + meal dönüşümlü dinleme v1.x'te; Türk hafızlar için faz atanmadı ([Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md)) |
| Bağımsızlık | Güçlü rakiplerin hepsi bir kuruma bağlı | Hiçbir cemaate ve yayınevine bağlı olmayan ürün |

## İlkeler

[K-25](./02-karar-defteri.md#k-25--i̇lkeler):
- Hiçbir cemaate ve yayınevine bağlı olmamak.
- Said Nursî metnini kelimesi kelimesine, kısaltmadan ve sadeleştirmeden yayımlamak.
- Reklam göstermemek.
- Riyâya teşvik eden sıralama ve liderlik tablosu koymamak; ilerleme varsayılan olarak kişisel ve gizli.
- Fetva vermemek.
- Yapay zekânın ürettiği her metne "doğrulanmamış" rozeti koymak; insan onayı olmadan doğrulanmış göstermemek.

## İlk sürüm (v1) bir bakışta

- **Platform:** iOS ve Android (Expo). Web mobilden sonra (Next.js 16).
- **İçerik:** Kur'an-ı Kerîm metni ve Elmalılı meali; hadis (Tecrîd-i Sarîh Arapça + Ahmed Naim ve Kâmil Miras Türkçesi, Kütüb-i Sitte Arapça); Risale-i Nur (metin, adresler, âyet atıf dizini, baskı sayfa eşlemesi, lügat). Elmalılı tefsir metni v1.x'te. Kitaplar sonra.
- **Yayın:** Her içerik editör onayından ve Yayınlayıcının kalite kapısından geçtikçe mağaza sürümüne girer ([K-42](./02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük)). Her kaynağın atıf satırı Ayarlar › Kaynaklar ekranında görünür.
- **Ses:** Popüler okuyucuların hazır dijital kayıtları kullanılır, hafız sesi alınmaz; dosyalar kendi içerik deposundan sunulur ([K-40](./02-karar-defteri.md#k-40--ses-kaynağı-hazır-dijital-tilavet-kaynakları), [K-41](./02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme)).
- **Hesap:** Yok. Uygulama hesapsız ve çevrimdışı tam çalışır.
- **Arama:** Cihazda, SQLite FTS5.
- **Depolama yöneticisi:** Var.

Tam liste: [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md).

## Referans malzeme

- **Vitrin sayfası:** "Mütâlaa Okuma Uygulaması". Tıklanabilir okuma masası örneği, mushaf seçenekleri karşılaştırması, özellik haritası, tasarım dili.
- **Araştırma raporu:** `Kuran Risale okuma uygulaması araştırması.md` (16 Ekim 2026). Kaynak listesi: [Kaynakça](../09-kaynakca.md).
- **Claude Code rehberi:** [Claude Code ile geliştirme](../10-claude-code/README.md). Proje yalnız Claude Code ile, aşama aşama geliştirilir ([K-31](./02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)).
- **Eski plan:** `quran-app-docs` (Mayıs 2026). Okuyucu tasarımları ve ilkeler için referans; teknoloji kararları [K-30](./02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) ile geçersiz.

## İlgili dosyalar
- [README](../README.md) · [Karar defteri](./02-karar-defteri.md) · [Sözlük](./03-sozluk.md)
- [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md) · [Fazlar](../08-yol-haritasi/01-fazlar.md)
