# A38 · Web (Next.js)

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-14](../../00-ozet/02-karar-defteri.md#k-14--web) · [K-08](../../00-ozet/02-karar-defteri.md#k-08--platform-sırası) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5)
> **Faz:** 5 · Web · **Önkoşul:** [A34](./A34-magaza-yayini.md) · **İnsan adımı:** İ-18
> **Ajanlar:** `web-gelistirici` · `arayuz-denetcisi` · `arastirmaci` · `test-yazari` · `metin-denetcisi` · `inceleyici` · **Beceriler:** `capa-gramer` · `test-vektoru` · `metin-butunlugu` · `paket-yayini` · `windows-sorun` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A38`

## Amaç
Next.js 16 ile her âyete (`/kuran/[sure]/[ayet]`, 6.236 sayfa) ve her mushaf sayfasına (`/mushaf/[sayfa]`, 604 sayfa) kalıcı adresli, statik üretilen ve arama motorunda görünen bir site kurulur. Site içeriği yalnız `public` kalite kapısından geçmiş, imzalı public manifestteki paketlerden okur (onaylı birimler; `test-` kaynak yok); paylaşılan paketleri (`anchors`, `search`, `reader-core`, `ui-tokens`) kullanır; `mutalaa://q/2/255` ile `/kuran/2/255` aynı çapaya gider. Aşama işe tedarikle başlar (A38.0): kitaplık ve araç sürümleri kayıttan doğrulanır; web rotaları, arama yolu ve barındırma A38.1'de kesinleşir.

## Okunacak belgeler
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 5
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §11 `toRoute` ve web rotaları tablosu, §12 sure adları, §13 ÇŞ-7
- [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §1 Web satırı, §2.6, §4.2 Next.js
- [Genel mimari](../../02-mimari/01-genel-mimari.md): §3, §8, §10, §11 soru 3 · [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1, §2, §3
- [Arama](../../03-veri/05-arama-fts5.md): §1 normalleştirme, §4 sonuç parçası, §5 web araması
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §5 manifest ve imza, §7 süzme ve `page_map` notu
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §3 derleme türleri ve görünürlük, §4 kalite kapısı kuralları, §6 Kaynaklar ekranı (atıf bilgisi)
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §3.1 Kur'an metni ve yazı tipleri
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.5, §9, §10 `packages/ui-tokens` · [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §7 kural 5
- [Belge çelişkileri](../07-belge-celiskileri.md): BÇ-10 (web aramasının veri kaynağı), BÇ-36 (web adresinin çapaya çözümü)

## Kapsam
**Yapılır**
- Tedarik doğrulaması (A38.0), web rotalarının kesinleşmesi (ÇŞ-7), `apps/web` iskeleti, public paketlerden içerik okuma betiği.
- `/kuran/[sure]/[ayet]`, `/mushaf/[sayfa]` ve karara göre meal, tefsir, hadis ve Risale rotalarının statik üretimi; atıf bilgisi (paketin `attribution` tablosundan).
- Web araması, ortak vektörlerin web test koşusu, `mutalaa://` ↔ `https://` eşlik testi, evrensel bağlantı dosyaları.
- Canlıya açılış (barındırma ve alan adı hazır olunca).

**Yapılmaz**
- Web'de hesap ve senkron: Fazlar Faz 5'e göre "hesap web'de istenirse" Faz 4'e bağlı; istenirse ayrı plan (`/karar`).
- Mushaf A (QPC sayfa yazı tipleri ve düzen verisi) web'de: kapsam dışı (öneri); `/mushaf/[sayfa]` Mod C mantığıyla Unicode metinden üretilir.
- Mobil uygulamada evrensel bağlantının yayımlanması: yeni uygulama sürümüyle (A34 yordamı).

## Tedarik
| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Web çatısı | `next` 16.4.3 ([npm](https://www.npmjs.com/package/next/v/16.4.3), 23 Ekim 2026; `vercel/next.js` etiketi `v16.4.3`, commit `29bbeab0`; 16.4 duyurusu 6 Ekim 2026), `react` ve `react-dom` 19.3.1 ([npm](https://www.npmjs.com/package/react/v/19.3.1), 14 Ekim 2026; `facebook/react` etiketi `v19.3.1`, commit `61aa00df`); npm paketi | `pnpm --filter @mutalaa/web add next react react-dom`; sürümler `pnpm-lock.yaml` içinde sabitlenir | npm `latest` etiketi 16.4.3 ve 19.3.1; `next` Node ≥ 20.9 ister (yerel Node 24.21.0); `react-dom` eş bağımlılığı `react@^19.3.1`. [16.4 duyurusu](https://nextjs.org/blog/next-16-4) açılıyor: `ensureStatic`, React 19.3, `next upgrade --agent`. [`ensureStatic` belgesi](https://nextjs.org/docs/app/api-reference/file-conventions/route-segment-config/ensureStatic): yalnız `cacheComponents` açıkken çalışır (aksi hâlde derleme düşer); dinamik rotada `generateStaticParams()` en az bir parametre nesnesi vermelidir. [Statik dışa aktarım rehberi](https://nextjs.org/docs/app/guides/static-exports) (güncelleme 9 Ağustos 2026): `output: 'export'`; `generateStaticParams()` olmayan ya da `dynamicParams: true` dinamik rota, çerez, rewrite, redirect, başlık, Proxy, Draft Mode ve Server Actions desteklenmez; çıktı `out/` altındadır ve `out/404.html` üretilir | `next` 16.3 hattının son kararlı yaması (A38.0'da kayıttan okunur) |
| Stil ve bileşenler | `tailwindcss` ve `@tailwindcss/postcss` 4.3.3 ([npm](https://www.npmjs.com/package/tailwindcss/v/4.3.3), 16 Temmuz 2026; `tailwindlabs/tailwindcss` etiketi `v4.3.3`, commit `c2b24dd1`); shadcn/ui: CLI `shadcn` 4.23.0 ([npm](https://www.npmjs.com/package/shadcn/v/4.23.0), 27 Ekim 2026; `shadcn-ui/ui` etiketi `shadcn@4.23.0`, commit `96da9cc7`; Node ≥ 20.18.1); bileşen kaynağı depoya kopyalanır | `pnpm --filter @mutalaa/web add tailwindcss @tailwindcss/postcss`; `pnpm dlx shadcn@4.23.0 init` (bayraklar A38.2'de Next.js şablonu için belgeden alınır) | npm `latest` etiketi üç pakette de bu sürümler; A15 tedarik tablosuyla aynı sürümler (editör paneli ve web aynı yığın). Next.js kurulum adımı A38.0'da Tailwind ve shadcn belgesiyle doğrulanır | Yok (editör paneliyle aynı yığın) |
| Yazı tipleri (web biçimi) | `@fontsource/amiri-quran` 5.3.0 ([npm](https://www.npmjs.com/package/@fontsource/amiri-quran/v/5.3.0), 19 Temmuz 2026; `arabic` altkümesi `amiri-quran-arabic-400-normal.woff2`, 45.680 bayt); Türkçe gövde ve arayüz için `@fontsource/literata` ve `@fontsource/ibm-plex-sans`, metin içi Arapça için `@fontsource/noto-naskh-arabic` (üçü de 5.3.0). A24'te Mod C yazı tipi olarak KFGQPC Hafs seçilirse A24'te alınan WOFF2 (`kfgqpc-hafs-font` kaydı) kullanılır | `pnpm --filter @mutalaa/web add`; CSS dosyası içe aktarılır (`@fontsource/amiri-quran/arabic-400.css`) | Ölçüldü (2 Kasım 2026): Tanzil `quran-uthmani.txt` 68, `quran-simple-clean.txt` 44 farklı Arapça blok kod noktası kullanıyor; Amiri Quran `arabic` altkümesinde (cmap 128 kod noktası) ikisinde de eksik 0; KFGQPC Hafs v22 TTF'sinde (297.688 bayt, cmap 608 kod noktası) Uthmani için eksik 0. Fontsource paketinde yalnız `arabic` ve `latin` WOFF2 dosyaları var | A24'te `data/gelen/` altına alınan yazı tipi dosyaları (`amiri-quran-font`, `kfgqpc-hafs-font`) `next/font/local` ile |
| Web araması (tarayıcı dizini) | `@orama/orama` 3.1.18 ([npm](https://www.npmjs.com/package/@orama/orama/v/3.1.18), 19 Aralık 2025; `oramasearch/orama` etiketi `v3.1.18`, commit `2fe41e16`; depoda son hareket 3 Temmuz 2026), Türkçe ve Arapça gövdeleyiciler için `@orama/stemmers` 3.1.18 (`tr.js` 15.435 bayt, `ar.js` 12.429 bayt), dizinin dosyaya yazılması için `@orama/plugin-data-persistence` 3.1.18 | `pnpm --filter @mutalaa/web add` | Orama dil tablosunda `arabic` ve `turkish` var (paket kaynağı `components/tokenizer/languages.js`); `@orama/stemmers` paketinde `ar` ve `tr` dosyaları var; Node ≥ 20. Dizin boyutu ve sorgu süresi (Arapça + Türkçe, 6.236 âyet) A38.1'de gerçek `core` paketiyle ölçülür | Pagefind 1.6.0 (npm, 1 Kasım 2026; `Pagefind/pagefind` etiketi `v1.6.0`, commit `860a4ea8`; parçalı dizin, `addCustomRecord` ile özel kayıt; her dilde çalışır, gövdeleme desteklenen dillerde); `@sqlite.org/sqlite-wasm` 3.54.1-build1 (npm, 19 Ekim 2026; Node ≥ 22; aynı FTS5 paketini tarayıcıda açar) |
| Derlemede paket SQLite dosyalarını salt okunur açma | `node:sqlite` (Node.js 24 LTS "Krypton", yerleşik; [belge](https://nodejs.org/docs/latest-v24.x/api/sqlite.html): kararlılık 1.2 "Release candidate"; `new DatabaseSync(yol, { readOnly: true })`) | Yok (yerleşik) | Ölçüldü (2 Kasım 2026, Node 24.21.0, sentetik tablo): SQLite 3.53.4, derleme seçeneklerinde `ENABLE_FTS5`; salt okunur açılan dosyada FTS5 `bm25` sorgusu çalışıyor, yazma "attempt to write a readonly database" ile reddediliyor. Gerçek `core` paketiyle sınama A38.0'da | `better-sqlite3` 13.0.3 (npm, 5 Ağustos 2026; Node ≥ 22; yerel eklenti) |
| Manifest imzası ve kanonik JSON (derleme betiği) | `node:crypto` Ed25519 (yerleşik) ve `canonicalize` 5.1.0 ([npm](https://www.npmjs.com/package/canonicalize/v/5.1.0), 18 Eylül 2026; A13'ün seçtiği kitaplık; Node ≥ 22) | `pnpm --filter @mutalaa/web add canonicalize` | Ölçüldü (2 Kasım 2026, Node 24.21.0, sentetik veri): 32 baytlık açık anahtar JWK ile içe aktarıldı, 64 baytlık imza doğrulandı, bir bayt bozulunca doğrulama reddetti. Yayınlayıcı imzası A13'te NSec ile üretilir (aynı boyutlar). Gerçek `public` manifestiyle doğrulama A38.2'de | `@noble/ed25519` 3.2.0 (npm, 27 Ağustos 2026; A23'te kullanılır) |
| Evrensel bağlantı ve uygulama bağlantısı dosyaları | Apple [Supporting associated domains](https://developer.apple.com/documentation/xcode/supporting-associated-domains) (`/.well-known/apple-app-site-association`) ve Android [Verify Android App Links](https://developer.android.com/training/app-links/verify-android-applinks) (`/.well-known/assetlinks.json`); dosyaları biz üretiriz | Belgeler okunur; dosyalar `apps/web/public/.well-known/` altında üretilir | Apple belgesi HTTP 200: dosya `https://<tam alan adı>/.well-known/apple-app-site-association` adresinde, geçerli sertifikayla ve yönlendirmesiz sunulur; içerik `applinks.details[].appIDs` ve `components` dizilerini taşır. Android belgesi HTTP 200: `https://<alan adı>/.well-known/assetlinks.json`; uygulama tarafında `android:autoVerify="true"`. Ekip kimliği ve imza parmak izi İ-15 hesaplarından gelir; içerik türü ve ayrıntılar A38.0'da belgeyle doğrulanır | Yok (resmî biçim) |
| Barındırma (statik çıktı) | Cloudflare Pages ([sınırlar](https://developers.cloudflare.com/pages/platform/limits/): ücretsiz planda siteye en çok 20.000 dosya) ya da Workers statik varlıkları ([sınırlar](https://developers.cloudflare.com/workers/static-assets/billing-and-limitations/)); K-21'in R2 önerisi ve İ-18 alan adıyla aynı hesap (hesap: altyapı). Seçim A38.1'de `/karar` ile | Hesap İ-18 ile açılır; dağıtım komutu A38.0'da belgeyle sabitlenir | Cloudflare Pages [yönlendirme belgesi](https://developers.cloudflare.com/pages/configuration/serving-pages/): üst düzeyde `404.html` varsa bulunmayan adrese en yakın `404.html` döner; yoksa Pages siteyi tek sayfa uygulaması sayıp `/` sunar. Next.js `out/404.html` ürettiği için `/kuran/2/300` 404 almalıdır (A38.6'da canlı adreste sınanır). Sayfa sayısı: 6.236 âyet + 604 mushaf sayfası (+ varsa sure ve meal sayfaları); sayfa başına çıktı dosyası sayısı A38.1 denemesinde ölçülür ve 20.000 sınırıyla karşılaştırılır | GitHub Pages ([sınırlar](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits): yayımlanan site en çok 1 GB, dağıtım 10 dakikayı aşarsa zaman aşımı) |
| Site içeriği (kendi yayınımız) | A13 Yayınlayıcının ürettiği imzalı `public/manifest.json` ve paketleri (`core`; varsa meal, `tefsir-elmalili`), canlı S3 uyumlu depoda (İ-18); sure adları `shared/data/sure-adlari.json` (A11) | `apps/web/scripts/fetch-packs.mjs` (`MANIFEST_URL`); paketler `apps/web/.content/` altına iner | 114 sure ve 6.236 âyet (`data/gelen/tanzil/2026-11-02/quran-simple-clean.txt`: 6.236 satır, bu aşamada yeniden sayıldı); 604 mushaf sayfası (Tanzil `quran-data.xml`, A11 ölçümü). Her paket sha256 ve manifest imzasıyla doğrulanır | Yok (`dev` ve `internal` manifestleri hiçbir yapılandırmada okunmaz) |
| Test ve lint araçları | Kök `vitest` 5.0.5, `typescript` ~6.0.3, `eslint` ^10.13.0 (A02); `eslint-config-next` 16.4.3 ([npm](https://www.npmjs.com/package/eslint-config-next/v/16.4.3), 23 Ekim 2026); bileşen testi için A15 tablosundaki sürümler (`@testing-library/react` 16.3.3, `jsdom` 30.1.3, `axe-core` 4.14.0) | `pnpm --filter @mutalaa/web add -D` | `eslint-config-next` eş bağımlılıkları `eslint >=9` ve `typescript >=3.3.1`: kökteki ESLint 10 ve TypeScript 6.0 ile uyumlu. A15 sürümleri bu aşamada yeniden okunmadı; A38.0'da kayıttan doğrulanır | Yok (A15 ile aynı araçlar) |

Kendimiz yapacağımız işler: `apps/web` rotaları ve sayfa bileşenleri; `scripts/fetch-packs.mjs` (manifest, imza, sha256 ve `pack_source` denetimi); web rota tablosu (`packages/anchors`) ve `route.jsonl` kesin biçimi; arama dizinini public paketlerden üreten derleme betiği; evrensel bağlantı dosyalarının üretimi; sitemap ve robots dosyaları; metin bütünlüğü, 404 ve eşlik testleri.

## Adımlar
### A38.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrular. Kitaplıkların son kararlı sürümü npm kayıt dizininden (`https://registry.npmjs.org/<paket>/latest`), yayım tarihi deps.dev'den (`https://api.deps.dev/v3/systems/npm/packages/<paket>/versions/<sürüm>`) okunur; GitHub etiketleri `git ls-remote` ile commit'e çözülür (`api.github.com` kullanılmaz; açıklamalı etiketlerde `^{}` satırı commit'tir). Belge adresleri (Next.js, Node.js, Apple, Android, Cloudflare, GitHub Pages) açılır, güncelleme tarihleri tablodakilerle karşılaştırılır. Açılmayan adresin ya da kayıtta bulunmayan sürümün yerine tablodaki yedek aday kullanılır ve tablo güncellenir.
- Bu aşama içerik kaynağı almaz: `data/gelen/` altına dosya inmez, `pipeline/sources/` altına kayıt açılmaz. Alınan yapılar npm kitaplıklarıdır (paket dosyalarını `pnpm install` indirir; yazı tipleri `@fontsource/*` paketlerinden gelir); site içeriği kendi `public` yayınımızdır (A38.2 betiği).
- Sürümü paket kaydından doğrula: `pnpm --filter @mutalaa/web list --depth 0` kurulu sürümü, `pnpm --filter @mutalaa/web outdated` kayıttaki son kararlı sürümü gösterir. Tablo, `pnpm-lock.yaml` ve komut çıktısı aynı sürümleri vermelidir.
- Tablodaki ölçümler (`node:sqlite` ile FTS5, `node:crypto` ile Ed25519, yazı tipi kod noktası kapsamı) CI'ın Node sürümünde de yinelenir; `ci-ts.yml` Node sürümü Teknoloji yığını §4.2 ile (Node.js 24 LTS) aynı olmalıdır. Yazı tipi kapsam denetimi `apps/web/scripts/` altında betik olarak tutulur (öneri); A24'te Mod C yazı tipi seçildiyse denetim o yazı tipiyle çalışır.
- **Bitti sayılır:** tablodaki her kitaplığın sürümü kayıtta doğrulanmış (ya da yedek adayla değiştirilip tablo güncellenmiş); belge adresleri açılıyor; ölçüm hücreleri CI'ın Node sürümünde yinelenmiş; sürümler A38.2'de `package.json` ve `pnpm-lock.yaml` içine bu değerlerle yazılmaya hazır.

### A38.1 · Doğrulamalar ve kararlar
- Aşamaya atanmış açık belge çelişkilerinin kararı bu adımın ilk maddesidir: BÇ-10 (web aramasının veri kaynağı) ve BÇ-36 (web adresinin çapaya çözümü); aşağıdaki kararlarla birlikte alınır.
- `arastirmaci` resmî kaynaktan doğrular: Faz 5 başındaki güncel kararlı Next.js sürümü (Tedarik: 16.4.3; yükseltme yolu `next upgrade --agent`); `ensureStatic` ile `output: 'export'` birlikte derleniyor mu (`ensureStatic` yalnız `cacheComponents` açıkken çalışır ve dinamik rotada en az bir parametre ister; birlikte derlenmezse statik çıktıyı `output: 'export'` ve `dynamicParams = false` garanti eder, `ensureStatic` kullanılmaz); 6.840 statik sayfanın derleme süresi, bellek etkisi ve sayfa başına çıktı dosyası sayısı (deneme projesi `.tmp/web-deneme/`, sentetik sayfalarla); Orama'nın Türkçe ve Arapça gövdeleyicileri ve dizin boyutu (gerçek `core` paketiyle); `node:sqlite`'ın paket dosyalarını salt okunur açması; Apple evrensel bağlantı ve Android uygulama bağlantısı dosyalarının biçimi. Sürümler kurulum günü kilit dosyasına yazılır.
- `/karar` (proje sahibi onaylar): web rotalarının kesin listesi, meal, tefsir, hadis ve Risale rotaları dahil (Çapa şeması §11 tablosu "Faz 5'te kesinleşir"; her biri ilgili paket `public` manifestte onaylı birimlerle yer alıyorsa); BÇ-36: `https://…/kuran/2/255` adresinin çapaya çevrilmesi (web adresini çapaya çeviren işlev, ör. `fromWebRoute`, eklenir ya da evrensel bağlantı uygulamada yerel şemaya yeniden yazılır); arama yolu (BÇ-10); web barındırma (Tedarik'teki adaylar; ölçüt sayfa başına dosya sayısı ve alan adı; ücretli plan gerekirse tahmini maliyet karar sırasında gösterilir).
- Arama kuralı: Arama §5 web aramasını editoryal veritabanındaki `tsvector` sütunlarına bağlıyor; oysa editoryal veritabanı onaysız taslakları ve editör kararlarını taşıdığı için dışarıya açılmaz (Genel mimari §10, §11 soru 3). Bu aşamada web araması editoryal veritabanını sorgulamaz. Seçenekler: (a) derlemede public paketlerden üretilen Orama dizini (Tedarik'teki seçim); (b) public paketlerden doldurulan ayrı bir arama veritabanı ve genel kipte bir uç; (c) Tedarik'teki yedek adaylar: parçalı dizinli Pagefind ya da aynı FTS5 paketini tarayıcıda açan `@sqlite.org/sqlite-wasm`. Her yolda sorgu `packages/search` ile normalleşir; seçim `/karar` ile yapılır (ölçütler: tarayıcıya inen dizin boyutu, Türkçe ve Arapça sorgu doğruluğu), Arama §5 `/belge-esitle` ile güncellenir.
- **Bitti sayılır:** rapor ve kararlar defterde; BÇ-10 ve BÇ-36 belge çelişkileri dosyasında `çözüldü` olarak işlenmiş; `shared/test-vectors/anchors/route.jsonl` kesinleşen web rotalarını taşıyor ve üç dilde yeşil.

### A38.2 · `apps/web` iskeleti ve içerik kaynağı
- `web-gelistirici`: `apps/web` (`@mutalaa/web`); Tailwind v4 ile `packages/ui-tokens` teması ve tema değişken blokları; shadcn/ui; ESLint ve Turborepo görevleri. `packages/*` içine `next` girmez (Proje yapısı §2 kural 2).
- İçerik betiği (öneri `apps/web/scripts/fetch-packs.mjs`): `MANIFEST_URL` ile public manifesti indirir, imzayı `public` açık anahtarıyla doğrular (Ed25519 için `node:crypto`, kanonik JSON için `canonicalize`; İçerik paketleri §5), her paketin sha256'sını denetler, paket dosyalarını `node:sqlite` ile salt okunur açıp manifestteki ve `pack_meta` içindeki `flavor` değerinin `public` olduğunu ve `pack_source` içinde `test-` önekli kaynak bulunmadığını kontrol eder; aksi hâlde sıfırdan farklı kodla durur. Paketler `apps/web/.content/` (git dışı, öneri) altına iner. `dev` ve `internal` manifestleri hiçbir yapılandırmada okunmaz.
- **Bitti sayılır:** bozuk imzalı, `public` dışı derleme türlü ve `test-` kaynaklı üç fikstür manifestiyle betik sıfırdan farklı kodla çıkıyor (test).

### A38.3 · Rotalar ve statik üretim
- `/kuran/[sure]/[ayet]`: âyet metni kanonik Tanzil metniyle, hiçbir dönüşüm uygulanmadan (NFC yok), `lang="ar"` ve `dir="rtl"` ile; Elmalılı meali; sure adı `shared/data/sure-adlari.json`'dan; atıflar paketin `attribution` tablosundan (Tanzil'in kendi bildirimi `notice_text` bayt bayt ve tanzil.net bağlantısı, Elmalılı künyesi).
- `/mushaf/[sayfa]`: Mod C mantığıyla Medine sayfa sınırları; sınırlar public `core` paketindeki `page_map`'ten gelir. `page_map` yoksa bu rotalar üretilmez ve kayda yazılır (İçerik paketleri §7).
- Meal, tefsir, hadis ve Risale rotaları A38.1 kararıyla; her biri yalnız ilgili paket (`tefsir-elmalili`, `hadis-*`, `risale-*`) public manifestte ise.
- Statik üretim: `generateStaticParams` ve `dynamicParams = false` ile `output: 'export'` (A38.1 denemesi `ensureStatic` ile `cacheComponents` birlikteliğini onaylarsa `ensureStatic` de eklenir); geçersiz adres (`/kuran/2/300`) en yakın âyete yuvarlanmaz, 404 döner (`out/404.html`).
- Erişilebilirlik [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md) §2.5 ve §9'a göre: metin kontrastı en az 4,5:1, dokunma hedefi, Arapça ve Türkçe ayrı boyut, %200 büyütme; `arayuz-denetcisi` ekran görüntüleriyle denetler.
- **Bitti sayılır:** statik parametre testleri 6.236 ve 604 değerini veriyor; 404 ve metin bütünlüğü testleri yeşil; `out/` dosya sayısı seçilen barındırıcının sınırının altında (A38.1 ölçümüyle karşılaştırılır).

### A38.4 · Arama
- A38.1'deki yol uygulanır. Sorgu normalleştiricisinin sürümü paketlerin `normalizer_version` değeriyle aynıdır; dizin ve sorgu metni `packages/search` ile normalleşir, seçilen kitaplığın kendi gövdeleyicisi bu normalleşmeyi bozmaz (test); sonuç parçası kanonik metinden `reader-core` ile üretilir, arama sütunu sayfada görünmez.
- `normalize/tr.jsonl`, `normalize/ar.jsonl` ve uygulanabilen `fts-query/query.jsonl` vektörleri web test koşusunda geçer (Faz 5 çıkış ölçütü).
- **Bitti sayılır:** arama testinde `Işık`, `ışık`, `IŞIK` ve `isik` sorguları aynı ilk sonucu getiriyor.

### A38.5 · Eşlik ve derin bağlantı
- `anchors/route.jsonl` her satırda yerel ve web rotasını taşır; `q:2:255` ↔ `mutalaa://q/2/255` ↔ `/kuran/2/255` satırı zorunludur. `toRoute` ve `fromRoute` gidiş-dönüş testi web test koşusunda da çalışır. BÇ-36 kararı uygulanır (web adresini çapaya çeviren işlev ya da uygulamada yerel şemaya yeniden yazma).
- Evrensel bağlantı ve uygulama bağlantısı dosyaları alan adında (İ-18) yayımlanmak üzere üretilir: `apple-app-site-association` (`applinks.details[].appIDs` ve `components`; geçerli sertifika, yönlendirme yok) ve `assetlinks.json` (Android `autoVerify`) `apps/web/public/.well-known/` altına yazılır; uygulama tarafı yeni sürümle gelir. `https://<alan-adı>/kuran/2/255` uygulamada aynı çözücüye bağlanır (Mobil ekranlar §7 kural 5).
- **Bitti sayılır:** gidiş-dönüş testi yeşil; dosyalar üretildi ve sürüm kaydında.

### A38.6 · Canlıya açılış
- Önkoşullar: barındırma kararı (A38.1) ve alan adı (İ-18). Alan adı hazır değilse A38.0–A38.5 yine tamamlanır; yalnız bu alt adım açık kalır, aşama `sürüyor` durumunda olur ve İ-18 ilerleme dosyasına yazılır.
- Canlıda yalnız public paketler kullanılır; CI'daki web derlemesi aynı içerik betiğiyle doğrulanır.
- **Bitti sayılır:** canlı adreste `/kuran/2/255` 200 ve `/kuran/2/300` 404 dönüyor.

## Kabul ölçütleri
- [ ] Tedarik tablosundaki her sürüm kayıtta doğrulanmış ve `pnpm-lock.yaml` ile aynı (A38.0).
- [ ] `pnpm --filter @mutalaa/web build` başarılı.
- [ ] Statik parametre testleri `/kuran` için 6.236, `/mushaf` için 604 değerini veriyor (ya da `page_map` yoksa `/mushaf` 0 ve gerekçe kayıtta).
- [ ] `anchors/route.jsonl` TypeScript, C#, Python ve web test koşusunda yeşil; `q:2:255` satırı iki rotayı taşıyor.
- [ ] Metin bütünlüğü testi: örnek âyetlerde sayfadaki Arapça metin `unit.text` ile bayt bayt aynı; `content-hash` vektöründeki NFC olmayan dizi bozulmuyor.
- [ ] İçerik betiğinin üç negatif testi sıfırdan farklı kodla duruyor.
- [ ] `/kuran/2/300` 404 testi ve arama testi yeşil.
- [ ] `apps/web` içinde PostgreSQL ya da editoryal veritabanı istemcisi yok (`grep` boş).
- [ ] Kontrast testi yeşil; `arayuz-denetcisi` bulguları kapalı.
- [ ] BÇ-10 ve BÇ-36 kararları defterde; belge çelişkileri dosyasında `çözüldü`.
- [ ] Canlıya açılış yapıldıysa canlı adres testleri geçti.

## Doğrulama
```bash
pnpm --filter @mutalaa/anchors test && pnpm --filter @mutalaa/search test && pnpm --filter @mutalaa/ui-tokens test
pnpm --filter @mutalaa/web test
dotnet test --solution server/Mutalaa.slnx && uv --directory pipeline run pytest
pnpm --filter @mutalaa/web list --depth 0   # sürümler Tedarik tablosuyla aynı
grep -n '"q:2:255"' shared/test-vectors/anchors/route.jsonl
grep -rniE "npgsql|postgres|ConnectionStrings" apps/web --include="*.ts" --include="*.tsx" --include="*.mjs"   # boş
MANIFEST_URL="https://<içerik-alanı>/public/manifest.json" pnpm --filter @mutalaa/web exec node scripts/fetch-packs.mjs
pnpm --filter @mutalaa/web build
# Canlıya açılıştan sonra (A38.6)
curl -s -o /dev/null -w "%{http_code}\n" "https://<alan-adı>/kuran/2/255"   # 200
curl -s -o /dev/null -w "%{http_code}\n" "https://<alan-adı>/kuran/2/300"   # 404
```
PowerShell'de: `$env:MANIFEST_URL = "https://<içerik-alanı>/public/manifest.json"` ve `curl.exe`.

## Dikkat
- Kanonik metin hiçbir katmanda dönüştürülmez: âyet metni React'e `normalize()` görmeden verilir; HTML kaçışı dışında değişiklik yoktur. Ayrıntı: `metin-butunlugu`.
- Web'e yalnız `public` içerik girer; `test-` kaynak hiçbir durumda girmez; editoryal veritabanı web'den sorgulanmaz. Onaysız birim `public` manifestte zaten yoktur (P-10); içerik betiği yine de `flavor` ve `pack_source` denetimini yapar.
- Statik çıktıyı `output: 'export'` garanti eder; `ensureStatic` yalnız `cacheComponents` açıkken çalışır, aksi hâlde derleme düşer. Sayfa başına çıktı dosyası sayısı barındırıcı sınırını (Cloudflare Pages ücretsiz planda 20.000 dosya) aşabilir; A38.1 denemesinde ölçülür.
- `node:sqlite` Node 24'te kararlılık 1.2 (aday sürüm) düzeyindedir; yalnız derleme betiğinde kullanılır, tarayıcıya girmez.
- Türkçe büyük-küçük harf `packages/search` açık eşlemesiyle; argümansız `toLocaleLowerCase` ve `localeCompare` ESLint'te yasak.
- Rotalar `packages/anchors` ile üretilir ve çözülür; elle dizgi birleştirilmez. Ayrıntı: `capa-gramer`.
- Windows: `.next/` ve `.content/` çok sayıda dosya üretir; OneDrive eşitlemesi ve uzun yol sorunları için `windows-sorun`.
- A08'den devir (CI): web iş akışı ya da `ci-ts.yml` içindeki web adımı eklenirken `NEXT_TELEMETRY_DISABLED=1` ortam değişkeni verilir; mevcut iş akışları `TURBO_TELEMETRY_DISABLED`, `TESTINGPLATFORM_TELEMETRY_OPTOUT` ve `DOTNET_CLI_TELEMETRY_OPTOUT` ile aynı ilkeyi izler ([Proje yapısı §7](../../02-mimari/03-proje-yapisi.md#7-ci-iş-akışları-github-actions)).

## İnsan adımları
- İ-18 · Canlı içerik deposu ve alan adı: depo A38.2'nin `MANIFEST_URL` değeri için (denemeler yerel depo ve fikstürle sürer); alan adı A38.5 (evrensel bağlantı dosyaları) ve A38.6 (canlıya açılış) için. Bekleyen İ-18 yalnız kendisine bağlı alt adımı bekletir.
- Web barındırma kararı (numarasız; proje sahibi, `/karar`): A38.1'de. Barındırma hesabı altyapıdır (Cloudflare Pages ya da Workers; İ-18 hesabıyla aynı olabilir).
- Apple ekip kimliği ve Android imza parmak izi (İ-15 hesaplarından): A38.5.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/web/` (Next.js uygulaması, rotalar, `scripts/fetch-packs.mjs` öneri, testler)
- `shared/test-vectors/anchors/route.jsonl` (kesin web rotaları); `packages/anchors` web rota tablosu
- Evrensel bağlantı ve uygulama bağlantısı dosyaları (alan adında yayımlanmak üzere)
- `pnpm-lock.yaml` içinde Tedarik tablosundaki sürümler; güncel `## Tedarik` tablosu
- Karar defteri: web rotaları, arama yolu, barındırma; Çapa şeması §11 ve Arama §5 güncellemeleri (`/belge-esitle`); BÇ-10 ve BÇ-36 `çözüldü`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A38-web.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A37](./A37-elmalili-tefsir-paketi.md) · Sonraki: [A39](./A39-devre-disi.md)
