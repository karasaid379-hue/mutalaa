# Karar Defteri

> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Onaylı
> **Kapsam:** 16–18 Ekim 2026 beyin fırtınası oturumunda verilen bütün kararlar ve sonraki eklemeler (K-31, 19 Ekim 2026).
> **Kural:** Bir karar değişirse eski satır silinmez; "Geçersiz" olarak işaretlenir ve yeni karara bağlantı verilir.

Bu dosya projenin tek doğruluk kaynağıdır. Diğer dosyalar bir kararı ayrıntılandırır ama değiştiremez. Çelişki görülürse bu dosya geçerlidir.

---

## Özet tablo

| No | Konu | Karar | Ayrıntı |
|---|---|---|---|
| K-01 | Ad | **Mütâlaa** | [Ürün özeti](./01-urun-ozeti.md) |
| K-02 | İlk içerik seti | Kur'an-ı Kerîm (Elmalılı meali ile), hadis, Risale-i Nur; kitaplar sonra | [Kapsam](../01-urun/01-kapsam-ve-fazlar.md) |
| K-03 | Tefsir | Şimdilik yalnız Elmalılı; önce meal, tefsir metni sonra | [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) |
| K-04 | Hadis | Tecrîd-i Sarîh (Arapça + Ahmed Naim Türkçesi) ve Kütüb-i Sitte Arapça metni birlikte | [Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md) |
| K-05 | Risale-i Nur ve lisanslı içerik | Altyapı şimdi hazırlanır; telif görüşmeleri zamanı gelince | [Risale hazırlığı](../04-icerik/05-risale-hazirligi.md) |
| K-06 | Yayın kapısı | Her kaynak lisans durumu ve Kurul onay sürümü taşır | [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) |
| K-07 | Mushaf görünümü | A, B ve C üçü de seçenek; kullanıcı seçer | [Okuma deneyimi](../01-urun/02-okuma-deneyimi.md) |
| K-08 | Platform sırası | Önce mobil, web mobilden sonra | [Fazlar](../08-yol-haritasi/01-fazlar.md) |
| K-09 | Mobil | React Native + TypeScript, Expo SDK 57 (58'e geçiş), Expo Router | [Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md) |
| K-10 | Arka uç | ASP.NET Core 10 (LTS), Minimal API, EF Core 10 | [Backend API](../02-mimari/05-backend-api.md) |
| K-11 | Veritabanı | PostgreSQL 18 | [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) |
| K-12 | İçerik hattı | Python 3.13 (uv) | [İçerik hattı](../04-icerik/02-icerik-hatti.md) |
| K-13 | Editör paneli | React + TypeScript + Vite + shadcn/ui | [Proje yapısı](../02-mimari/03-proje-yapisi.md) |
| K-14 | Web | Next.js 16 (React + TypeScript), mobilden sonra | [Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md) |
| K-15 | Hesap ve senkron | v1.x'te; ilk sürüm hesapsız | [Kullanıcı verisi ve senkron](../03-veri/04-kullanici-verisi-ve-senkron.md) |
| K-16 | Çakışma çözümü | HLC + veri türüne göre birleştirme | [Kullanıcı verisi ve senkron](../03-veri/04-kullanici-verisi-ve-senkron.md) |
| K-17 | Arama | Cihazda SQLite FTS5, normalize arama metni | [Arama](../03-veri/05-arama-fts5.md) |
| K-18 | Depolama yöneticisi | v1'de | [Depolama yöneticisi](../06-mobil/03-depolama-yoneticisi.md) |
| K-19 | Kelime anlamları | Kendimiz yazarız: yapay zekâ taslağı + insan onayı | [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md) |
| K-20 | Barındırma | Geliştirme kendi bilgisayarda; canlıda düşük maliyetli yöntem sonra seçilecek | [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) |
| K-21 | İçerik dağıtımı | Sürümlü SQLite paketleri; yerelde S3 uyumlu depo (SeaweedFS), canlıda S3 uyumlu depo (öneri: Cloudflare R2) | [İçerik paketleri](../03-veri/03-icerik-paketleri.md) |
| K-22 | Gelir modeli | Şimdilik yok; fiyatlandırma sonra | [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) |
| K-23 | Dokümanlar | `mutalaa-docs`; `quran-app-docs` arşiv ve referans | [README](../README.md) |
| K-24 | Tasarım dili | "Sade Osmanlı": İznik paleti, Kâğıt / Âhar / Gece | [Tasarım sistemi](../01-urun/04-tasarim-sistemi.md) |
| K-25 | İlkeler | Tarafsızlık, kelimesi kelimesine metin, reklamsızlık, riyâsız tasarım | [Ürün özeti](./01-urun-ozeti.md) |
| K-26 | Kalıcı adresler | Tek çapa grameri, yeniden numaralama yok | [Çapa şeması](../03-veri/01-capa-semasi.md) |
| K-27 | Bağlantılar | Tek `xref` tablosu; tür, güven, kanıt, durum, lisans | [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md) |
| K-28 | Ses | expo-audio + XState | [Ses sistemi](../06-mobil/02-ses-sistemi.md) |
| K-29 | Mobil arayüz | NativeWind v4 + React Native Reusables + @gorhom/bottom-sheet + Reanimated 4 | [Mobil mimari](../06-mobil/01-mobil-mimari.md) |
| K-30 | Eski plandan çıkarılanlar | .NET 9 monolit, Azure yığını, Expo SDK 51 ve kapsam dışı modüller | [Bu dosya, K-30](#k-30--eski-plandan-çıkarılanlar) |
| K-31 | Geliştirme aracı | Yalnız Claude Code ile, proje klasörünün içinde, aşama aşama (A00–A40) | [Claude Code rehberi](../10-claude-code/README.md) |

---

## Kararlar

### K-01 · Ad: Mütâlaa
- **Karar:** Uygulamanın adı *Mütâlaa*.
- **Gerekçe:** "Dikkatle okuma, üzerinde düşünerek çalışma" anlamına gelir ve Risale-i Nur'un kendi dağarcığında geçer. Ürünün işini doğrudan anlatır.
- **Not:** Mağaza adı ve alan adı uygunluğu canlıya geçmeden önce kontrol edilecek ([Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md)).

### K-02 · İlk içerik seti
- **Karar:** İlk içerik seti Kur'an-ı Kerîm (Elmalılı meali ile), hadis ve Risale-i Nur. Kitaplar (Kısas-ı Enbiyâ, Mevlid vb.) sonraki fazda.
- **Gerekçe:** Ürünün ayırt edici işi bu üç külliyat arasındaki bağlantılar.
- **Yayın:** Üçünün de altyapısı şimdi hazırlanır. Her biri lisans durumuna göre yayına açılır ([K-06](#k-06--yayın-kapısı)).

### K-03 · Tefsir: önce Elmalılı meali
- **Karar:** Şimdilik tek tefsir Elmalılı Hamdi Yazır'ın *Hak Dini Kur'an Dili*. Önce âyet meali hazırlanır, tefsir metni ikinci aşamada.
- **Kaynak:** Özgün 1935–39 baskısı (yazar 1942'de vefat etti; eser 1 Ocak 2013'ten beri serbest). Sadeleştirilmiş baskılar kullanılmaz, çünkü sadeleştirenin hakkı sürer.
- **Düzeltme (18 Ekim 2026):** Oturumda bu baskının Osmanlıca harflerle basıldığı söylenmişti. Bu doğru görünmüyor: baskı 1928 harf devriminden sonra yapıldı ve Princeton kataloğu eseri "Osmanlı Türkçesi" değil "Turkish" olarak kaydediyor (İstanbul: Matbaai Ebüzziya, 1935–1938, 6.442 sayfa). Türkçe metin büyük olasılıkla Latin harfli, âyetler Arapça harflidir. Bu yüzden iş, harf çevirisi değil, 1930'ların dizgisine ve imlasına uygun OCR ve düzeltmedir. Bir tarama nüshası üzerinde doğrulanacak. Kaynak: [Princeton SCSB-3946972](https://catalog.princeton.edu/catalog/SCSB-3946972).
- **Değerlendirilen alternatifler:** Mevcut bir dijital metni temel almak (sadeleştirme hakkı riski); Elmalılı'ya ek olarak Arapça klasik tefsir (sonraya bırakıldı).

### K-04 · Hadis kaynakları
- **Karar:** Tecrîd-i Sarîh (Arapça + Babanzâde Ahmed Naim'in Türkçesi) ile Kütüb-i Sitte'nin Arapça metni birlikte işlenir.
- **Gerekçe:** Ahmed Naim (ö. 1934) bölümü bugün serbest; Kâmil Miras'ın (ö. 1957) ciltleri 1 Ocak 2028'de serbest kalır. Yasal Türkçe hadis metni sunan tek yol bu. Arapça metinler serbest.
- **Açık nokta:** Açık hadis veri setlerinin kaynak belgeleri zayıf; kaynak seçimi [Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md) dosyasında.

### K-05 · Risale-i Nur ve lisansı bekleyen içerik
- **Karar:** Risale-i Nur'un içerik hattı, adresleri, âyet atıf dizini ve baskı sayfa eşlemesi şimdi hazırlanır. Telif görüşmeleri zamanı gelince yapılır. Aynı yaklaşım hadis çevirileri, diğer tefsirler ve Türk hattı mushaf için de geçerli.
- **Hukuki durum:** Risale-i Nur 31 Aralık 2030'a kadar korunuyor, 1 Ocak 2031'de serbest kalıyor. Hakları bugün kimin kullandığı belirsiz.
- **Sonuç:** Risale metni yalnız ekip içi `dev` derlemelerinde görünür. Dış test kullanıcılarına giden `internal` derlemelere ve mağaza paketine girmez. Ekip içi işlemenin (dizin üretimi dahil) hukuken uygunluğu hukukçuya danışılır.

### K-06 · Yayın kapısı
- **Karar:** Her içerik kaynağı bir lisans durumu taşır: `serbest`, `bekliyor`, `ic_kullanim`, `kapali`. Kur'an metni, meal ve ses kaynakları ayrıca Kurul onaylı sürüm bilgisi taşır.
- **Kural (derleme türüne göre görünürlük):**
  - `public` (mağaza): yalnız `serbest` ve gerekiyorsa Kurul onaylı içerik.
  - `internal` (davetli test kullanıcıları): yalnız `serbest` içerik. Kurul onayı bekleyen Kur'an metni, meal ve sesin kapalı testte gösterilip gösterilemeyeceği Kurul'la ön görüşmede sorulur (Açık soru); cevap gelene kadar dış test kullanıcısı alınmaz.
  - `dev` (yalnız ekip): `serbest`, `bekliyor` ve `ic_kullanim` içerik. `kapali` içerik hiçbir derlemeye girmez.
- **Durumların anlamı:**
  - `serbest`: kamu malı, açık lisanslı ya da yazılı izni olan içerik.
  - `bekliyor`: izin ya da açıklama istendi, cevap bekleniyor (örnek: Kur'an Corpus verisi).
  - `ic_kullanim`: hukukçu görüşüyle yalnız ekip içinde işlenebilen içerik.
  - `kapali`: hiçbir derlemede kullanılmaz ve işlenmez.
- **Başlangıç durumları:** Risale-i Nur metni hukukçu görüşü gelene kadar `kapali`, görüş olumluysa `ic_kullanim`; izinle ya da 1 Ocak 2031'de `serbest`. Tecrîd-i Sarîh'in Kâmil Miras ciltleri 1 Ocak 2028'e kadar `kapali`, sonra `serbest`.
  - Güncelleme (18 Ekim 2026): İlk taslakta `internal` derlemenin `ic_kullanim` içeriği gösterebileceği yazılıydı; dış test kullanıcılarına dağıtım çoğaltma ve yayma sayılabileceği için bu kural sıkılaştırıldı.
- **Dayanak:** 633 sayılı Kanun m. 6 (4 Haziran 2025'ten beri): Kurul onayı olmayan elektronik ve sesli Kur'an ile mealli mushaf yayımlanamaz.
- **Uygulama notu (18 Ekim 2026):** Kapı yalnız metinlere değil veri setlerine de uygulanır. Kur'an Corpus (QAC) kaynaklı kök ve lemma verisinin lisansı belirsiz olduğu için bu veri `core` paketinden ayrı bir pakette, kendi lisans durumuyla tutulur; QAC'den yazılı açıklık gelene kadar `bekliyor` durumundadır. Manifest, paket başına `kurul_gerekli` bilgisi ve manifest imzası taşır.

### K-07 · Mushaf görünümü: üç seçenek
- **Karar:** Üç çizim yolu da uygulamada seçenek olarak bulunur; kullanıcı ayarlardan seçer.
  - **A · Medine düzeni:** QPC sayfa fontları, satırlar basılı mushafla birebir. Kelime seçimi, koyu tema, tecvid renkleri.
  - **B · Türk hattı:** Lisanslı sayfa görselleri + sayfa başına âyet koordinat verisi. Âyet vurgusu var, kelime seçimi yok. Lisans gelince açılır.
  - **C · Akan Unicode metin:** Tek açık lisanslı font, büyütünce yeniden akar, en erişilebilir yol.
- **Gerekçe:** Kullanıcı tercihi. Kalıcı adres şeması üçünü aynı anda destekler; mod değişse de not ve vurgular kopmaz.

### K-08 · Platform sırası
- **Karar:** Önce mobil (iOS ve Android), web mobilden sonra.

### K-09 · Mobil teknoloji
- **Karar:** React Native + TypeScript, Expo SDK 57 (SDK 58 kararlı çıkınca geçiş), Expo Router, geliştirme derlemeleri (Expo Go değil).
- **Gerekçe:** Eski plandaki SDK 51 altı sürüm geride. React Native 0.82'den beri yalnız Yeni Mimari'de çalışıyor.
- **Not:** SDK 56'dan itibaren asgari iOS sürümü 16.4; iPhone 7, 6s ve ilk SE desteklenmiyor.

### K-10 · Arka uç
- **Karar:** ASP.NET Core 10 (LTS, 14 Kasım 2028'e kadar destek), Minimal API, EF Core 10 + Npgsql.
- **Görev:** v1'de editör paneli uçları ve içerik yayını. v1.x'te hesap (ASP.NET Core Identity) ve senkron.
- **Değerlendirilen alternatifler:** Supabase (en az operasyon), Cloudflare Workers + D1 (en ucuz), güncellenmiş Azure planı (en pahalı). Proje sahibi ASP.NET'i seçti.

### K-11 · Veritabanı: PostgreSQL 18
- **Karar:** PostgreSQL 18 (MSSQL yerine).
- **Gerekçe:** Ücretsiz ve açık kaynak; Türkçe ve Arapça tam metin arama yapılandırmaları hazır; anlamsal katman için pgvector; Linux konteynerde hafif; EF Core sağlayıcısı (Npgsql) olgun. MSSQL'in ücretsiz sürümü sınırlı, tam sürümü lisans istiyor.

### K-12 · İçerik hattı: Python
- **Karar:** Python 3.13, paket yönetimi `uv`.
- **Gerekçe:** Elmalılı'nın 6.442 sayfalık özgün baskısı OCR ve düzeltme gerektiriyor (Latin harfli Türkçe ve Arapça âyetler; bkz. K-03 düzeltmesi). OCR, Arapça NLP, gömme modelleri ve toplu yapay zekâ etiketlemede en olgun ekosistem Python. Hat yalnız geliştirme makinesinde çalışır, üretim sunucusunda çalışmaz.
- **Değerlendirilen alternatifler:** .NET 10 (ZemberekDotNet ile Türkçe lemmatizasyon), TypeScript (uygulamalarla tek dil).

### K-13 · Editör paneli
- **Karar:** React + TypeScript + Vite + shadcn/ui; iç araç.
- **Görev:** Otomatik bulunan iktibasları, kök etiketlerini ve kelime anlamlarını onaylamak; metin düzeltmek; lisans durumunu yönetmek.

### K-14 · Web
- **Karar:** Next.js 16 (React + TypeScript), mobilden sonra.
- **Gerekçe:** Next.js zaten React + TypeScript; aynı bileşenlerle aynı şıklıkta görünür. Farkı her âyete ve sayfaya ayrı adres, arama motorunda görünme ve hızlı ilk açılış. Düz React (Vite) iç araçlarda kullanılır.

### K-15 · Hesap ve senkron v1.x'te
- **Karar:** İlk sürüm hesapsız ve çevrimdışı tam çalışır. Notlar, vurgular ve ilerleme cihazda kalır. Hesap ve cihazlar arası senkron v1.x'te gelir.
- **Kural:** Yerel kullanıcı veritabanı v1'den itibaren senkrona hazır şemayla kurulur; v1.x'te göç gerekmez.

### K-16 · Senkron çakışma çözümü
- **Karar:** Her kayıt UUIDv7 kimlik, HLC zaman damgası, silme işareti ve temel sürüm taşır. Birleştirme veri türüne göre:
  - Yer imi, vurgu, ayar: kayıt bazında son yazan kazanır (HLC sırasıyla).
  - Hatim ve okunan sayfalar: küme birleşimi.
  - Kaldığın yer: cihaz başına tutulur, çakışma oluşmaz.
  - Notlar: iki cihazda değişmişse iki sürüm korunur, kullanıcı seçer.
- **Kaynak:** Proje sahibinin önerisi (18 Ekim 2026).

### K-17 · Arama: SQLite FTS5
- **Karar:** Arama cihazda SQLite FTS5 ile yapılır. Arama metni içerik hattında normalize edilir; önek indeksi, Arapça için trigram tablosu, bm25 sıralaması. Hedef: orta seviye Android'de 50 ms altı.
- **Kaynak:** Proje sahibinin önerisi (18 Ekim 2026) ve araştırma raporu.

### K-18 · Depolama yöneticisi v1'de
- **Karar:** Ayarlar › Depolama ekranı v1'de: paket listesi, boyut, sürüm, tek dokunuşla silme, hafız başına ses silme, yalnız Wi-Fi ile indirme, duraklatılabilir indirme kuyruğu.
- **Kaynak:** Proje sahibinin önerisi (18 Ekim 2026).

### K-19 · Kur'an kelime anlamları
- **Karar:** Türkçe kelime anlamları kendimiz yazılır. Yapay zekâ lemma başına taslak çıkarır, insan onaylar.
- **Gerekçe:** Yeniden kullanılabilir açık lisanslı Türkçe kelime meali bulunamadı. İş yükü 77.429 kelimeye değil, farklı lemma sayısına bağlı.

### K-20 · Barındırma
- **Karar:** Geliştirme şimdilik kendi bilgisayarda (Docker Compose). Canlıya geçerken düşük maliyetli bir yöntem seçilecek.
- **Not:** Hesaplar v1.x'te geldiğinde KVKK nedeniyle veri konumu kararı yeniden ele alınacak.

### K-21 · İçerik dağıtımı
- **Karar:** İçerik sürümlü SQLite paketleri olarak dağıtılır. Yerelde S3 uyumlu bir depo, canlıda S3 uyumlu bir depo.
- **Güncelleme (18 Ekim 2026):** Oturumda yerel depo için MinIO önerilmişti. MinIO, Ekim 2025'ten beri topluluk Docker imajı yayımlamıyor ve Aralık 2025'ten beri bakım modunda. Yerel geliştirmede SeaweedFS'in S3 arayüzü kullanılır (Doğrulanacak; bkz. [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md)).
- **Öneri:** Canlıda Cloudflare R2 (veri çıkışı ücretsiz; ses trafiği için belirleyici). Kesin seçim canlıya geçişte.

### K-22 · Gelir modeli
- **Karar:** Şimdilik bir gelir modeli yok; önce projenin çalıştığı doğrulanacak. Fiyatlandırma "Sonra yapılacaklar" listesinde.

### K-23 · Doküman yeri
- **Karar:** Yeni klasör `mutalaa-docs`. Eski `quran-app-docs` dokunulmadan arşiv ve referans olarak kalır.
- **Güncelleme (19 Ekim 2026):** Masaüstündeki `mutalaa-docs` klasörü proje kökü oldu; belgeler bu klasörün `docs/` alt klasörüne taşındı ([K-31](#k-31--geliştirme-aracı-claude-code)).

### K-24 · Tasarım dili
- **Karar:** "Sade Osmanlı": kâğıt yüzeyler, İznik çinisi paletinden çini mavisi, turkuaz ve lâl; altın yalnız süs çizgilerinde. Kâğıt, Âhar ve Gece temaları.
- **Referans:** "Mütâlaa Okuma Uygulaması" vitrin sayfası (okuma masası örneği ve mushaf seçenekleri).

### K-25 · İlkeler
Eski plandan aynen devralınır:
- Hiçbir cemaate ve yayınevine bağlı olmamak.
- Said Nursî metnini kelimesi kelimesine, kısaltmadan ve sadeleştirmeden yayımlamak.
- Reklam göstermemek.
- Riyâya teşvik eden sıralama ve liderlik tablosu koymamak.
- Fetva vermemek.
- Yapay zekâ ürettiği her metne "doğrulanmamış" rozeti koymak.

### K-26 · Kalıcı adresler (çapa şeması)
- **Karar:** Her metin birimi tek bir gramere göre kalıcı bir adres alır: `q:2:255`, `q:2:255-257` (âyet aralığı), `q:2:255:3-7` (kelime aralığı), `meal:elmalili:2:255`, `tf:elmalili:…`, `rn:sozler:…`, `h:{koleksiyon}:{no}`, `ht:{ceviri}:{koleksiyon}:{no}`, `konu:{slug}`, `…@120-184`.
- **Kural:** Adresler hiçbir sürümde yeniden numaralanmaz; her birim metin özeti (hash) taşır. Karakter aralığı `@başlangıç-bitiş` yarı açıktır: başlangıç dahil, bitiş hariç.
- **Kanonik metin:** Kaynaktan alınan metin, kaynağın dağıttığı hâliyle saklanır; Tanzil metni bayt bayt değiştirilmez (NFC bile uygulanmaz, çünkü NFC şedde ile harekenin sırasını değiştirir ve Tanzil "değiştirmek yasak" şartı koyar). NFC yalnız kendi ürettiğimiz metinlere (transkripsiyonlar, kelime anlamları) ilk kayıtta uygulanır. Ofsetler kanonik metindeki Unicode kod noktalarıdır; arama için normalize edilmiş metin ayrı sütunda tutulur.

### K-27 · Tek bağlantı tablosu
- **Karar:** Bütün bağlantılar `xref` tablosunda: kaynak ve hedef adres + aralık, tür, puan, güven, kanıt, durum (aday / onaylı / red), lisans.
- **İstisna:** Âyet ↔ meal ve âyet ↔ tefsir aralığı ilişkileri adreslerin kendisinden türetilir (`meal:elmalili:2:255` ↔ `q:2:255`, `tf:elmalili:2-255-257:…` ↔ `q:2:255-257`); `xref`'e ayrıca yazılmaz. Kullanıcı oyları (v1.x) ayrı bir `xref_vote` tablosunda tutulur.

### K-28 · Ses
- **Karar:** expo-audio + XState durum makinesi (tekrar, aralık, âyetler arası bekleme, Kur'an + meal dönüşümü).
- **Gerekçe:** react-native-track-player v5 ticari kullanım için lisans istiyor; v4 donduruldu.

### K-29 · Mobil arayüz kitaplıkları
- **Karar:** NativeWind v4 (kararlı sürüm) + React Native Reusables + @gorhom/bottom-sheet + Reanimated 4 + Gesture Handler; durum için Zustand + TanStack Query + MMKV.

### K-30 · Eski plandan çıkarılanlar
`quran-app-docs` (Mayıs 2026) şu kararlar için geçersizdir:
- ASP.NET Core 9 modüler monolit (12 modül) → ASP.NET Core 10, ince API ([K-10](#k-10--arka-uç)).
- Azure yığını (Container Apps, AI Search, Azure AD B2C, Redis, Front Door, SignalR) → yerel geliştirme + düşük maliyetli barındırma ([K-20](#k-20--barındırma)).
- Expo SDK 51, expo-av, WatermelonDB, react-native-track-player → [K-09](#k-09--mobil-teknoloji), [K-28](#k-28--ses).
- Bu ürün için kapsam dışı: zekât hesaplayıcı, çocuk modu, aile hesabı, LMS, mukabele, ortak hatim, kıraat-i seb'a, hac/umre rehberi, AR, akıllı saat, botlar, açık API.
- Risale için yapay zekâ özetleri ve gönüllü liderlik tablosu: ilkelerle çeliştiği için çıkarıldı ([K-25](#k-25--i̇lkeler)).

Eski planın okuyucu tasarımları, "okuma simetrisi" çekirdeği (son okunan yer, yer imi klasörleri, beş renkli vurgu, bağlantılı notlar) ve içerik etiği korunur.

### K-31 · Geliştirme aracı: Claude Code
- **Karar:** Proje yalnız Claude Code ile ve proje klasörünün içinde geliştirilir. Proje kökü masaüstündeki `mutalaa-docs` klasörüdür; belgeler `docs/` altındadır. Kit kökteki `CLAUDE.md`, `.claude/` klasörü (ajanlar, beceriler, kurallar, hook'lar, `settings.json`) ve `docs/10-claude-code/` bölümüdür (rehber, A00–A40 aşamaları, ilerleme, insan adımları).
- **Kurallar:**
  - Claude Code proje klasörünün dışına yazmaz ve dışından dosya okumaz. Dosya araçlarını `permissions.blockReadsOutsideWorkingDirectories` ve `klasor-bekcisi` hook'u kesin olarak sınırlar; kabuk komutlarında hook görünen yolları denetler; çalıştırılan programlar Windows'ta işletim sistemi düzeyinde sınırlanmaz, bu yüzden kural Claude için bağlayıcı bir talimattır ([Kurulum](../10-claude-code/01-kurulum.md) §7). Geçici dosyalar `.tmp/`, plan dosyaları `.tmp/planlar` altındadır; Claude Code'un proje dışındaki karalama klasörü kapalıdır (`enableArtifact: false`). Araçların kendi önbellek ve geçici dosyaları ile Claude Code'un oturum kayıtları bu kuralın dışındadır.
  - Claude Code proje kökünde başlatılır; komutlar Git Bash'te çalışır (PowerShell aracı kapalı).
  - Otomatik hafıza kapalıdır (`autoMemoryEnabled: false`); proje bilgisi yalnız depodaki dosyalarda tutulur.
  - İş birimi aşamadır. Her aşama `/asama` ile yürütülür; kabul ölçütleri komut çıktısıyla kanıtlanmadan ve inceleme yapılmadan bitmiş sayılmaz. Durum [İlerleme](../10-claude-code/05-ilerleme.md) dosyasındadır.
  - Claude Code Kur'an, meal, tefsir, hadis ve Risale metnini hafızadan yazmaz; bu metinler yalnız kaynak dosyalardan, içerik hattıyla gelir.
  - Commit kapsam listesine kit değişiklikleri için `kit` eklendi ([Proje yapısı](../02-mimari/03-proje-yapisi.md) §6).
- **Not:** Proje yolu boşluk, Türkçe karakter ve OneDrive içerdiği için Android geliştirme derlemesi varsayılan olarak EAS bulutunda yapılır; yol ve OneDrive kararı A00 aşamasında verilir ([Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §2).
- **Kaynak:** Proje sahibinin talebi (19 Ekim 2026).

---

## İlgili dosyalar
- [README](../README.md) · [Ürün özeti](./01-urun-ozeti.md) · [Sözlük](./03-sozluk.md)
- [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md)
