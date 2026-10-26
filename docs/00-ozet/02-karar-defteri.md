# Karar Defteri

> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Onaylı
> **Kapsam:** 16–18 Ekim 2026 beyin fırtınası oturumunda verilen bütün kararlar ve sonraki eklemeler (K-31, 19 Ekim 2026; K-32, K-33 ve K-34, 21 Ekim 2026; K-35, 24 Ekim 2026; K-36, 25 Ekim 2026; K-37, 26 Ekim 2026).
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
| K-32 | pnpm kurulumu ve düzeni | npm ile kurulur (Corepack yok); sürüm yalnız `devEngines.packageManager` ile sabitlenir; `node_modules` düzeni izole (varsayılan) | [Proje yapısı](../02-mimari/03-proje-yapisi.md) |
| K-33 | .NET test çalıştırıcısı | xunit.v3 4.x + Microsoft.Testing.Platform; komut `dotnet test --solution server/Mutalaa.slnx`; çözüm biçimi `.slnx` | [Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md) |
| K-34 | TypeScript sürümü | Tek sürüm TypeScript 6.0.x; TS 7 (native) kullanılmaz, geçiş araçlar desteklenince | [Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md) |
| K-35 | Çapa API ayrıntıları | Hata önceliği, §3 desenlerinin önceliği, Kur'an'da okuma sırası, birim ve rota işlevleri üç dilde, ilk kayıt adım sırası | [Çapa şeması](../03-veri/01-capa-semasi.md) |
| K-36 | Arama normalizasyonu ayrıntıları | Adım sırası, kesme ve sözcük kuralları, biçim karakterleri, Arapça noktalama, küçük harf kod noktası başına; Python gövdeleyicisi `snowballstemmer` 3.1.1 ve `â î û` ön katlaması | [Arama](../03-veri/05-arama-fts5.md) |
| K-37 | Editoryal şema ayrıntıları | G-YZ kaydı `review.yz_kaydi`; ortak enum JSON'u 11 tür; Identity `kimlik` şemasında, parola yalnız uzunluk ≥ 12; PostgreSQL ad politikası; belgede olmayan dizin yok | [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) |

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
- **Güncelleme (19 Ekim 2026, A00):** Proje kökünün gerçek adı `mutalaa-kit`tir (`C:\Users\MEHMET SAİD\OneDrive\Masaüstü\mutalaa-kit`); `mutalaa-docs` adı proje kökü olarak kullanılmaz. Ayrıntı: [K-31](#k-31--geliştirme-aracı-claude-code).

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
- **Güncelleme (2026-10-24):** Uygulama ayrıntıları (hata önceliği, sıralama, birim ve rota işlevleri, ilk kayıt adım sırası) [K-35](#k-35--çapa-api-ayrıntıları) ile belirlendi; bu karar değişmedi.
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
- **Güncelleme (19 Ekim 2026, A00):**
  - Proje kökü `mutalaa-kit` klasörüdür; yol kararı "yerinde kal"dır (OneDrive altında; yoğun işlerde eşitleme duraklatılır, Android derlemesi EAS bulutunda). Metindeki `mutalaa-docs` ifadesi bu karara göre okunur.
  - Uzak depo özel (private) GitHub deposu `karasaid379-hue/mutalaa`'dır. A08'e kadar her aşama sonunda commit'ler `main` dalına itilir (`git push origin main`, her seferinde onay sorar). A08'den sonra [Proje yapısı](../02-mimari/03-proje-yapisi.md) §6'daki akış (aşama dalı, PR, squash) geçerlidir. Zorla push yasaktır.
- **Kaynak:** Proje sahibinin talebi (19 Ekim 2026).

### K-32 · pnpm kurulumu, sürüm sabitleme ve düzen
- **Karar:**
  - pnpm npm yoluyla kurulur (`npx get-pnpm` ya da `npm install -g pnpm`); Corepack kullanılmaz.
  - Sürüm kök `package.json` içinde yalnız `devEngines.packageManager` alanıyla, tam sürüm olarak sabitlenir (kurulum günü kurulu sürüm; A02'de 12.14.0). `packageManager` alanı yazılmaz.
  - `node_modules` düzeni pnpm'in izole varsayılanıdır. Metro ile sembolik bağ sorunu çıkarsa yedek `pnpm-workspace.yaml` içine `nodeLinker: hoisted` yazmaktır; bu değişiklik `/karar` ister. `nodeLinker` ayarı `.npmrc` dosyasından okunmadığı için `.npmrc` yalnız kimlik doğrulama, kayıt defteri ya da sertifika gerekirse açılır.
- **Gerekçe:**
  - pnpm'in kurulum belgesi Windows'ta npm yolunu öneriyor ([pnpm.io/installation](https://pnpm.io/installation), okuma 2026-10-21). pnpm bakımcısı Corepack ile pnpm kurulmamasını öneriyor ([pnpm/discussions #9044](https://github.com/orgs/pnpm/discussions/9044)). Corepack Node 24'te deneysel, Node 25'ten itibaren dağıtılmıyor ([Node.js belgesi](https://nodejs.org/docs/latest-v24.x/api/corepack.html)); Corepack ile pnpm 12 uyumuna dair resmî ifade bulunamadı.
  - `devEngines.packageManager` pnpm belgesinde yeni yol, `packageManager` "legacy" ([pnpm.io/package_json](https://pnpm.io/package_json)). `pnpm/action-setup` iki alanı da okur, bu yüzden CI'da `version` girdisi gerekmez ([README](https://github.com/pnpm/action-setup#readme)).
  - Expo, SDK 54'ten beri pnpm'in izole kurulumunu resmî destekler; `hoisted` yalnız sorun çıkarsa önerilir ([docs.expo.dev/guides/monorepos](https://docs.expo.dev/guides/monorepos/), okuma 2026-10-21). İzole düzen, sürüm sabitleme ve bağımlılık sınırları ([Proje yapısı](../02-mimari/03-proje-yapisi.md) §2) için de daha sıkıdır.
- **Değerlendirilen alternatifler:** Corepack ile kurulum ve `packageManager` alanı (yukarıdaki gerekçelerle elendi); `node-linker=hoisted` (SDK 54+ için resmî destek varken gerekmiyor).
- **Not:** Expo SDK 58'e özel bir uyumluluk tablosu yok, kanıt SDK 54+ için genel destek beyanıdır; mobil iskelet gelince (A21) yeniden sınanır. `devEngines.packageManager` ile `packageManager` birlikte verilince pnpm 12'nin davranışı belgelenmemiş; bu yüzden yalnız biri kullanılır.
- **Kaynak:** Proje sahibinin kararı (21 Ekim 2026, A02; [BÇ-28](../10-claude-code/07-belge-celiskileri.md)).

### K-33 · .NET test çalıştırıcısı: xunit.v3 + Microsoft.Testing.Platform
- **Karar:**
  - Test projeleri `xunit.v3` 4.x (MTP v2) kullanır; kökteki `global.json` içinde `"test": { "runner": "Microsoft.Testing.Platform" }` yazılıdır.
  - Test komutu `dotnet test --solution server/Mutalaa.slnx` (CI'da `-c Release --no-build` ile). Çözüm biçimi `.slnx` kalır; `.sln`'e geçilmez.
  - `Microsoft.NET.Test.Sdk` ve `xunit.runner.visualstudio` eklenmez.
- **Gerekçe:**
  - `xunit.v3` 4.0, VSTest hedefini .NET 10 SDK'da desteklemiyor ([xunit.net/releases/v3/4.0.0](https://xunit.net/releases/v3/4.0.0)). .NET 10 SDK'da MTP kipi `global.json` ile açılır ve çözüm yolu `--solution` ile verilir ([dotnet test belgesi](https://learn.microsoft.com/en-us/dotnet/core/testing/unit-testing-with-dotnet-test), okuma 2026-10-21).
  - Yerel kanıt (A02.4, SDK 10.0.402, 21 Ekim 2026): `dotnet test --solution server/Mutalaa.slnx --no-build` 5 testi geçti; `dotnet format server/Mutalaa.slnx --verify-no-changes` çıkış 0 verdi (bilerek bozulan dosyada 2); `dotnet restore server/Mutalaa.slnx --locked-mode` hatasız. `.slnx` için `.sln` yedeği gerekmedi.
- **Değerlendirilen alternatifler:** `xunit.v3.mtp-off` + `xunit.runner.visualstudio` + `Microsoft.NET.Test.Sdk` (VSTest; komut değişmezdi, ama xunit'in varsayılan ve geleceğe dönük yolu MTP).
- **Not:** Pozisyonel `dotnet test server/Mutalaa.slnx` biçimi 10.0.402'de çalışıyor, ama MTP belgesinde yoktur; kullanılmaz. `global.json` `rollForward: latestFeature` ile kilit dosyaları birlikte kullanılıyor (kilitler 10.0.402 ile üretildi); SDK kayması `restore --locked-mode` içinde NU1004 verirse `rollForward` için yeni karar açılır.
- **Kaynak:** Proje sahibinin kararı (21 Ekim 2026, A02).

### K-34 · TypeScript: tek sürüm 6.0.x
- **Karar:** Kök `package.json` içinde `typescript` gerçek pakettir ve `~6.0` aralığındadır; takma ad ya da ikinci derleyici yoktur. TypeScript 7 (native) kullanılmaz. `tsc`, typescript-eslint ve editörün tsserver'ı aynı sürümü görür.
- **Gerekçe:** typescript-eslint 8.72.0 `typescript` eş bağımlılığını `<6.1` ile sınırlıyor; A02'de TypeScript 7.0.2 ile `typescript-eslint does not support TS 7.0` hatası alındı (21 Ekim 2026). TS 6 ve 7'yi takma adlarla yan yana kurmak çalıştı, ama bağımsız incelemede kırılgan bulundu: `tsc` bin'i 7.0.2, `typescript` paketi 6.0.x verir; Expo (`expo install --check`) ve Next.js `typescript` paketinin adını ve sürümünü bekler; ikinci bir `typescript` bağımlılığı gelince `tsc` bin'i sessizce başka sürüme geçebilir. TS 7 duyurusu: [devblogs.microsoft.com](https://devblogs.microsoft.com/typescript/announcing-typescript-7-0/).
- **Değerlendirilen alternatifler:** İki derleyici (`typescript` adına `@typescript/typescript6`, `tsc` için `@typescript/native` = TS 7.0.2). Hız kazancı yedi boş pakette önemsiz, bakım yükü ve kırılganlık fazla.
- **Not:** TS 7'ye geçiş typescript-eslint, Expo ve Next desteği belgelenince tek satırlık yükseltmedir; o zaman bu karar `/karar` ile güncellenir.
- **Kaynak:** Proje sahibinin kararı (21 Ekim 2026, A02).

### K-35 · Çapa API ayrıntıları
- **Karar:** [K-26](#k-26--kalıcı-adresler-çapa-şeması)'nın uygulama ayrıntıları TypeScript, C# ve Python'da aynıdır ve ortak test vektörleriyle kilitlenir:
  1. **Hata önceliği.** `[a-z0-9:@-]` dışı karakter → `BICIM`; toplam uzunluk 256'yı aşarsa → `UZUNLUK`; Çapa şeması §3 desenine uymayan → `BICIM`; slug 64 karakteri, derinlik 8'i (yol uzunluğu, kitap dahil), bir sayı alanı 2.147.483.647'yi aşarsa → `UZUNLUK`; sonra sırayla `SURE_ARALIGI`, `AYET_ARALIGI`, `TERS_ARALIK`, `KANONIK_DEGIL`.
  2. **Desen önce gelir.** §3 desenleri §2 EBNF'den dardır ve bağlayıcıdır: sure, âyet ve kelime en çok üç hanedir (`q:1000:1`, `q:2:255:1000` → `BICIM`); aralık bitişi 0 olamaz (`…@0-0`, `…@5-0` → `BICIM`).
  3. **`compare`.** Kur'an çapaları okuma sırasıyla dizilir: önce sure ve başlangıç âyeti; eşitlikte âyet, sonra kelimeler ve kelime aralıkları başlangıç kelimesine göre (aynı başlangıçta tek kelime önce, sonra bitişe göre), en sonda âyet aralıkları bitişe göre. Örnek: `q:2:255 < q:2:255:2 < q:2:255:2-3 < q:2:255:9 < q:2:255-256 < q:2:255-257 < q:2:256`. Diğer türlerde alanlar kanonik dizgideki soldan sağa sırayla karşılaştırılır; yol öğe öğe ASCII olarak, kısa önek önce; olmayan isteğe bağlı alan olandan önce; aralık önce başlangıç, sonra bitişle. Örnek: `rn:…:p4 < rn:…:p4@0-5 < rn:…:p4:s1`.
  4. **`contains`.** §11'e ek olarak: kelime aralığı kendi alt aralıklarını, âyet aralığı içindeki kelime aralıklarını da kapsar; aralıklı paragraf cümle çapasını kapsamaz; cümle çapası yalnız kendini kapsar.
  5. **Birim işlevleri.** `unitOf`: kelime ve kelime aralığı → âyet; `@` aralığı atılır; cümle → paragraf; âyet aralığı ve konu aynen kalır. `toUnitSpan`: kelime ya da kelime aralığı → âyet + `[ilk, son + 1)`; `@a-b` → taban çapa + `[a, b)`; aralıksız birim → yalnız `unit`; âyet aralığı ve cümle çapası → hata (âyet aralığı `coveredAyahs` ile âyetlere bölünür; cümle sınırı içerik verisi ister). `coveredAyahs`: `q`, `qa`, `tf` ve `meal` için kapsanan âyetler; diğer türlerde boş liste. Üç işlev Python (`unit_of`, `to_unit_span`, `covered_ayahs`) ve C#'ta (`UnitOf`, `ToUnitSpan`, `CoveredAyahs`) da yazılır.
  6. **Rotalar.** Yerel rota her türde mekaniktir; şema `mutalaa`, `mutalaa-internal` ya da `mutalaa-dev` olur; Python ve C# da isteğe bağlı şema alır. Web rotası yalnız §11 tablosundaki biçimler için üretilir (Kur'an âyeti, kelime aralığı ve âyet aralığı; konu; aralıksız meal; aralıksız âyetli tefsir; Risale paragrafı, aralığı atılarak; aralıksız hadis). Diğer biçimler hata verir; web rotaları ÇŞ-7 ile Faz 5'te kesinleşir. `fromRoute` yalnız üç yerel şemayı çözer.
  7. **İlk kayıt kanonikleştirmesi (§7).** Adımlar şu sırayla uygulanır: silinecek karakterler silinir; NFC; satır sonları (CRLF ve tek CR) U+000A olur, U+0020 ve U+0009 dizileri tek U+0020'ye iner, metnin başı ve sonu yalnız U+0020, U+0009 ve U+000A'dan kırpılır. U+00A0 kenarda da korunur; U+2028, U+2029 ve U+0085'e dokunulmaz.
  8. **Ofset işlevleri.** `snapSpan` `0 ≤ başlangıç ≤ bitiş ≤ uzunluk` dışında; `cpToUtf16` `[0, kod noktası sayısı]` dışında; `utf16ToCp` `[0, UTF-16 uzunluğu]` dışında ya da bir vekil çiftin ortasında hata verir.
- **Gerekçe:** Çapa şeması bu durumları açık bırakıyordu ya da kendi içinde ayrışıyordu. §2 EBNF sayıyı sınırsız ve aralık bitişini 0 olabilir yazarken §3 desenleri bunları dışlıyor. §11'deki "eşitlikte âyet, kelime, kelime aralığı, âyet aralığı" ile "okuma sırasıyla aynıdır" ifadeleri `q:2:255:9` ve `q:2:255:2-3` için farklı sonuç veriyor. §7 adımları yazılı sırayla uygulanınca silmeden sonra NFC olmayan dizi, kırpmadan sonra baştaki boşluk kalabiliyor. Sayı sınırı JavaScript'in tam sayı kesinliğini ve C# `int`'ini korur; uzunluk karakter kümesi denetiminden sonra ölçüldüğü için üç dilde aynı sayılır. Kaynak: A04 tasarım incelemesi (24 Ekim 2026).
- **Değerlendirilen alternatifler:** Kur'an'da belgenin harfi (önce tür: bütün tek kelimeler, sonra bütün kelime aralıkları; okuma sırasından sapar). Belirsiz durumları açık soru bırakıp vektöre koymamak (diller arasında fark kalabilirdi). `unitOf`, `toUnitSpan`, `coveredAyahs` yalnız TypeScript'te (hat ve sunucu `xref` yazacak).
- **Kaynak:** Proje sahibinin kararı (24 Ekim 2026, A04).

### K-36 · Arama normalizasyonu ayrıntıları
- **Karar:** [Arama](../03-veri/05-arama-fts5.md) §1'in (`normalizer_version = 1.0`) açık bıraktığı durumlar TypeScript, C# ve Python'da aynıdır ve `normalize/tr.jsonl` ile `normalize/ar.jsonl` vektörleriyle kilitlenir:
  1. **Ortak ön adım, bu sırayla.** (a) Eşsiz vekil kod birimi U+0020 olur. (b) U+200B U+0020 olur; diğer biçim karakterleri (Cf: U+00AD, U+200C–U+200F, U+2060, U+2066–U+2069, U+FEFF, U+061C, U+0600–U+0605, U+06DD, BMP dışı U+E0001 …) silinir. (c) NFC. (d) Yazı sistemine göre bölme: Arapça bloklarındaki her kod noktası Arapça parçaya, diğerleri Türkçe parçaya gider; öbür parçada o konum U+0020 olur. Silme NFC'den önce gelir, çünkü hiçbir kanonik ayrışım Cf üretmez. Atanmamış ve gizli kullanım kod noktaları (Cn, Co; değişmez karakterler ve U+FFFE dahil) silinmez, NFC onları değiştirmeden geçirir ve sözcük ayırıcıdır; .NET `Normalize` U+FFFE'yi reddettiği için C# NFC'yi U+FFFE sınırlarında parçalayarak uygular (A05 çapraz sınama bulgusu).
  2. **Türkçe parça, bu sırayla.** `I → ı`, `İ → i`, sonra kod noktası başına basit küçük harf eşlemesi; yedi kesme biçimi (U+2019, U+2018, U+02BC, U+02BE, U+02BF, U+00B4, U+0060) U+0027 olur (sözcük ayırmadan önce, çünkü bu karakterler noktalama ve simge kategorisindedir); sözcük, `Lu Ll Lt Lm Lo Mn Mc Me Nd Nl No` kategorilerindeki kod noktalarıyla U+0027'nin en uzun dizisidir (`isalnum`, `IsLetterOrDigit`, `\w` kullanılmaz); her sözcükte baş ve sondaki kesme dizileri atılır, iç kesme uygulanır, kalan ilk kesmeden sonrası ek olarak atılır, sözcük NFC'ye çevrilir, harf ya da rakam (L, N) taşımayan sözcük atılır. "Baş" ve "son" sözcüğün küçük harfli, kesmeleri U+0027 olmuş hâlinin ilk ve son kod noktasıdır (birleşen işaret önde ise kesme baş sayılmaz); "L, N" `Lu Ll Lt Lm Lo Nd Nl No` kategorileridir. Dar anahtar sözcükleri tek U+0020 ile birleştirir; geniş anahtar her sözcüğe ayrı `ı → i`, NFD, U+0300–U+036F silme, NFC uygular ve sözcük sayısı ile sırası dar anahtarla aynıdır.
  3. **İç kesme eşleşmesi.** Sözcüğün geniş biçimi (kesmeler korunarak) `shared/data/ic-kesme.txt` girdilerinden biriyle başlıyorsa en uzun girdi seçilir ve sözcüğün ilk k kesmesi silinir (k = girdideki kesme sayısı). Girdiler `^[a-z]+('[a-z]+)+$` desenine uyar, benzersiz ve sıralıdır. Liste TypeScript ve C# koduna `uv run mutalaa export ic-kesme` ile kopyalanır; Python dosyayı doğrudan okur.
  4. **Arapça parça.** Silme (U+064B–U+065F, U+0670, U+06D6–U+06ED, U+0640), birleştirme, sonra L, M, N dışı her kod noktası ayırıcıdır (`، ؛ ؟ ﴾ ﴿` bunun içindedir); L ya da N taşımayan sözcük atılır. Silme aralığı dışındaki işaretler (U+0610–U+061A, U+08D3–U+08FF), Farsça harfler, Arapça-Hint rakamlar, sunum biçimleri (NFKC uygulanmaz) ve U+06C0 1.0'da değişmez; AR-8 ve QA raporu A10'dadır.
  5. **Küçük harf kod noktası başınadır.** JavaScript `toLowerCase()` ve Python `str.lower()` dizede son sigma bağlamı uygular, .NET `Rune.ToLowerInvariant` uygulamaz; kod noktası başına çağrı üçünü eşitler. Sonucu `ΟΔΟΣ → οδοσ`'tur ve bilinen sınır olarak kayıtlıdır (Yunanca hedef yazı sistemi değildir).
  6. **Gövde (`tr_stem`, Python).** Her dar sözcükte yalnız `â → a`, `î → i`, `û → u` katlanır (ç ğ ı ö ş ü korunur), Snowball Türkçe gövdesi alınır ve geniş katlamadan geçirilir; sonuç boşsa ya da L/N taşımıyorsa sözcüğün geniş biçimi kullanılır. Sebep: Snowball Türkçe algoritmasının sesli harf tanımı yalnız `a e ı i o ö u ü`'dür, `â î û` sesli sayılmaz. `tr_wide` ve `tr_stem` aynı sayıda sözcük taşır ve sırası aynıdır. Gövdeleyici `snowballstemmer` 3.1.1'dir (BSD-3-Clause, saf Python), tam sürümle sabitlenir ve `snowballstemmer.turkish_stemmer.TurkishStemmer` doğrudan içe aktarılır.
  7. **Sürüm.** İç kesme listesi ve gövdeleyici sürümü normalleştiricinin parçasıdır; liste eklemesi ya da gövdeleyici sürüm değişikliği küçük sürümü artırır ([Arama](../03-veri/05-arama-fts5.md) §1 kuralı).
  8. **Unicode verisi.** Kategoriler, küçük harf eşlemesi ve NFC çalışma zamanının verisinden gelir (Python 15.1, Node 17.0, .NET: kategori çalışma zamanı tablosundan, `Normalize` işletim sisteminin ICU/NLS kitaplığından); sabit tablo tutulmaz ve vektörler yalnız eski, yerleşik kod noktalarını kullanır ([A04 aşama kaydı](../10-claude-code/asamalar/A04-capa-ve-test-vektorleri.md#aşama-kaydı-kapanış-2026-10-25)).
- **Gerekçe:** Arama §1 bu durumları açık bırakıyordu; üç dilin ayrışması sessiz arama kaybı demektir. Tasarım bağımsız bir incelemede Arama §1.5 Türkçe tablosunun 14 girdisi ve `IŞIK` üzerinden adım adım yürütüldü; hepsi tablodaki çıktıyı veriyor. Gövdeleyici seçimi `arastirmaci` raporuna dayanır (25 Ekim 2026; kaynaklar: [PyPI snowballstemmer](https://pypi.org/pypi/snowballstemmer/json), [Snowball Türkçe algoritması](https://snowballstem.org/algorithms/turkish/stemmer.html), [turkish.sbl](https://github.com/snowballstem/snowball/blob/master/algorithms/turkish.sbl), [PostgreSQL 18 Snowball README](https://github.com/postgres/postgres/blob/REL_18_STABLE/src/backend/snowball/README)). PostgreSQL 18 `turkish_stem`, Snowball'un 2025-02-19 anlık görüntüsünden alınmıştır; sonraki tek Türkçe davranış farkı kesmeli özel isim ekidir ve dar anahtarda kesme kalmadığı için etkisi beklenmez (çıkarım, çalıştırılarak doğrulanmadı).
- **Değerlendirilen alternatifler:** `PyStemmer` 3.1.0 (C uzantısı, aynı ortamda kuruluysa `snowballstemmer` sessizce ona geçerdi). `tr_stem`'i A12'ye bırakmak. `â î û` ön katlaması olmadan belgenin harfiyle gövdeleme (düzeltme işaretli sözcüklerin bir kısmı gövdelenmezdi). Bütün biçim karakterlerini boşluk yapmak (yumuşak tireli ve ZWNJ'li sözcükler ikiye bölünürdü). TypeScript gövdeleyicisi A12'de değerlendirilir.
- **Kaynak:** Proje sahibinin kararı (25 Ekim 2026, A05); gövdeleyici lisansı BSD-3-Clause, hukuki görüş değildir.

### K-37 · Editoryal şema ayrıntıları
- **Karar:** [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) v1 şeması EF Core 10 göçüyle şu ayrıntılarla kurulur:
  1. **Yapay zekâ kaydı (G-YZ, BÇ-05).** `review` tablosuna `yz_kaydi jsonb` sütunu eklenir; `prompt_id`, `prompt_sha256` ve `input_sha256` bu sütunda durur. Öteki alanlar var olan sütunlardan gelir: `ai_model` → `yz_modeli`, `review_id` → `review.id`, `created_at` → `review.created_at`. `dogrulanmis` ayrı saklanmaz; hedef satırın onaylı durumundan türetilir. Kısıt `review_yz_kaydi_check`: `yz_modeli` ile `yz_kaydi` ya ikisi birden boştur ya ikisi birden doludur; doluysa `yz_kaydi` bir JSON nesnesidir, üç anahtarı da taşır ve iki özet `^[0-9a-f]{64}$` biçimindedir.
  2. **Ortak enum dosyası 11 tür taşır.** `packages/content-schema/enums.json` artık §2'deki bütün türleri içerir; yeni eklenenler `unit_kind`, `unit_status`, `metin_durumu`, `inceleme_durumu`, `surum_durumu`. TypeScript, C#, Python ve PostgreSQL bu dosyaya karşı testlenir; PostgreSQL'deki etiket sırası JSON'daki sıradır. Npgsql 10'un `MapEnum` yöntemi etiketleri alfabetik sıraya dizdiği için türler `HasPostgresEnum` ile tanımlanır ve sıra açıkça verilir.
  3. **Editör kimliği.** Identity tabloları `kimlik` şemasında durur: `users`, `roles`, `user_roles`, `user_claims`, `user_logins`, `user_tokens`, `role_claims`. Identity şema sürümü varsayılan kalır, passkey tablosu kurulmaz. Parola en az 12 karakter olur; büyük harf, rakam ya da simge şartı yoktur. 5 hatalı denemede hesap 15 dakika kilitlenir. Kullanıcı adı e-posta adresidir ve her e-posta yalnız bir hesapta kullanılabilir.
  4. **Ad politikası.** `icerik` şemasındaki kısıt ve dizin adları, PostgreSQL'in adsız nesnelere verdiği adlardır: `{tablo}_pkey`, `{tablo}_{sütun}_fkey`, `{tablo}_{sütunlar}_key`, `{tablo}_{sütun}_check`; birden çok sütuna bakan CHECK `{tablo}_check` olur. Belgede adı geçen dizin ve kısıtlar o adı taşır. Belgede tekil kısıt (UNIQUE) diye yazılanlar EF'de aynı adlı tekil dizin olarak kurulur. Tek istisna `xref_natural_key`: hat bu kısıtı `ON CONFLICT ON CONSTRAINT` ile hedeflediği için gerçek bir kısıt olarak göçe ham SQL ile eklenir.
  5. **Belgede olmayan dizin açılmaz.** EF'nin yabancı anahtar sütunlarına kendiliğinden dizin açması kapatılır; `icerik` şemasında yalnız belgedeki dizinler bulunur. Identity'nin dört yabancı anahtar dizini açıkça tanımlanır.
- **Gerekçe:** G-YZ alanları için tabloda yer yoktu; A16 ve A17 bu kaydın karar defterinde olmasını bekliyor ([belge çelişkileri](../10-claude-code/07-belge-celiskileri.md), BÇ-05). Tek bir enum dosyası dört uygulamayı birbirine bağlar. `license_status` sırası lisans kapısının davranışını belirler; Npgsql'in alfabetik sıralaması bilinçli bir tasarımdır ([efcore.pg #3667](https://github.com/npgsql/efcore.pg/issues/3667), [#3390](https://github.com/npgsql/efcore.pg/issues/3390); A07.1 okuması, 26 Ekim 2026). [Backend API](../02-mimari/05-backend-api.md) §6 parola için yalnız uzunluk şartı koyuyor; Identity'nin varsayılan kuralları [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §6'daki örnek parolayı reddederdi. EFCore.NamingConventions kısıt ve dizinlere `pk_`, `fk_` ve `ix_` öneklerini verir; ad politikasıyla belgedeki DDL, `pg_dump` çıktısı ve hattın SQL'i aynı adları kullanır. Yabancı anahtar dizini kuralı açık kalsaydı belgede olmayan 10 dizin açılırdı.
- **Değerlendirilen alternatifler:** G-YZ için `review` tablosuna ayrı sütunlar (her yeni alan bir göç ister) ya da kararı A16'ya ertelemek. Enum'ları yalnız C# ve PostgreSQL'de tutmak (iki doğruluk kaynağı olurdu). Identity'nin varsayılan parola kuralları. EF'nin ad önekleri ve yabancı anahtar dizinleri.
- **Kaynak:** Proje sahibinin kararı (26 Ekim 2026, A07): 1–3. maddeler soru-cevapla, 4–5. maddeler plan onayıyla.

---

## İlgili dosyalar
- [README](../README.md) · [Ürün özeti](./01-urun-ozeti.md) · [Sözlük](./03-sozluk.md)
- [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md)
