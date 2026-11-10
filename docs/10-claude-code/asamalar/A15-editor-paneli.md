# A15 · Editör paneli

> **Sürüm:** 1.3 · **Tarih:** 10 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-48](../../00-ozet/02-karar-defteri.md#k-48--editör-api-kuralları-inceleme-kararı-ikinci-onay-eşzamanlılık-yayın-talebi-ve-sayfa-görseli) · [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A14](./A14-api-editor-uclari.md) · **İnsan adımı:** —
> **Ajanlar:** `web-gelistirici` · `arayuz-denetcisi` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `windows-sorun` · `icerik-hatti` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A15`

## Amaç
`apps/editor` kurulur: editörlerin kaynak kayıtlarını gördüğü, birimleri incelediği, OCR satırlarını düzelttiği, kelime anlamı ve bağlantı adaylarını onayladığı ve yayın başlattığı iç web aracı. Kitaplıklar internetteki hazır paketlerden alınır ve sürümleri sabitlenir (`## Tedarik`). API tipleri OpenAPI belgesinden üretilir; elle tip yazılmaz. A16–A19'un insan turları bu panelde yürür.

## Okunacak belgeler
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`apps/editor`), §2 bağımlılık kuralları, §4.1, §5 ESLint, §7 `ci-ts.yml`
- [Backend API](../../02-mimari/05-backend-api.md): §4 uçlar, §4.1 kuyruklar, §4.2 uç kuralları, §6 kimlik, OpenAPI ve hata modeli
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §8 `review` ve inceleme akışı
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §7 OCR inceleme ekranı · [Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md): §6 lemma kuyruğu
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §12 bağlantı kuyruğu ve toplu onay · [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §5 madde 7
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): §4 kalite kapısı raporu · [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.5
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §4 `editor` servisi ve Dockerfile notu, §6 adım 5
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 kaynak kaydı ve atıf, §3.1 (Amiri Quran), §5 yeni kaynak ekleme

## Kapsam
**Yapılır**
- Tedarik doğrulaması (A15.0): kitaplık sürümleri, Amiri Quran yazı tipi dosyası, Docker imajı etiketleri.
- Vite, React, TypeScript, Tailwind CSS v4 ve shadcn/ui iskeleti; `gen:api` (openapi-typescript, openapi-fetch ve openapi-react-query).
- Rotalar: `giris`, `kuyruk/baglanti`, `kuyruk/lemma`, `kuyruk/ocr`, `kaynaklar`, `birimler`, `yayinlar`.
- Ortak inceleme bileşenleri: karar, `If-Match`, toplu karar, ikinci onay gösterimi, "doğrulanmamış" rozeti.
- `apps/editor/Dockerfile` (`app` profili).

**Yapılmaz**
- API uçları (A14). Kuyruklara veri yazan hat işleri (A16–A19).
- `surah_alias` ve `quran_word_fix` için ayrı rota (Proje yapısı §1: yok, Açık soru). `surah_alias` onayı API karar uçlarıyla (A11); `quran_word_fix` `kuyruk/lemma` ya da API ile (A17).
- `ui-tokens` teması (A22'den sonra bağlanır; bu aşamada shadcn/ui varsayılan teması). Web sitesi (A38).

## Tedarik
Araştırma tarihi: 1 Kasım 2026. Sürümler npm kaydından (`dist-tags.latest`), yayım tarihleri deps.dev'den, etiketler `git ls-remote` ile okundu. Panel kitaplık, araç ve bir yazı tipi alır; içerik metni, hesap ya da anahtar gerekmez.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Derleme aracı ve çatı | `vite` 8.3.5 (21 Ekim 2026; etiket `v8.3.5`) ve `@vitejs/plugin-react` 6.1.2 (5 Ekim 2026); `react` ve `react-dom` 19.3.1 (14 Ekim 2026; etiket `v19.3.1`); `@types/react` ve `@types/react-dom` 19.3.0 (9 Eylül 2026); npm. TypeScript, ESLint ve Vitest kök sürümleridir (`~6.0.3`, `^10.13.0`, `^5.0.5`; A02): npm'de `latest` TypeScript 7.0.2 olsa da `typescript-eslint` 8.72.1 `<6.1.0` ister | `pnpm --filter @mutalaa/editor add react react-dom`; `add -D vite @vitejs/plugin-react @types/react @types/react-dom`; kesin sürümler `pnpm-lock.yaml` içine yazılır | `vite.dev/guide/` açılıyor; Vite ve eklentisi Node 20.19+ ya da 22.12+ ister, eklenti `vite ^8` ister; aynı sürümlerle oluşturulan deneme iskeletinde `build` geçti (1 Kasım 2026) | `vite` 6.4.5 (npm `previous` etiketi; eklenti sürümü A15.0'da doğrulanır) |
| Stil | `tailwindcss` ve `@tailwindcss/vite` 4.3.3 (16 Temmuz 2026; etiket `v4.3.3`); npm. `src/index.css` içinde `@import "tailwindcss";`, Vite eklentisi `vite.config.ts` içinde | `pnpm --filter @mutalaa/editor add tailwindcss @tailwindcss/vite` | `tailwindcss.com/docs/installation/using-vite` ve shadcn/ui'nin Vite sayfası aynı iki paketi ve `@import` satırını veriyor; `@tailwindcss/vite` Vite 5.2 ile 8 arasını destekliyor; denemede derleme geçti | `@tailwindcss/postcss` 4.3.3 |
| Bileşen kitaplığı | shadcn/ui; CLI `shadcn` 4.23.0 (27 Ekim 2026; etiket `shadcn@4.23.0`; Node 20.18.1+); npm. Bileşenler depoya kopyalanır (`src/components/ui/`); CLI'nin eklediği yardımcı paketler (ör. `lucide-react` 1.66.0, `clsx`, `tailwind-merge`, taban kitaplık) A15.0'da `package.json` içinden yazılır | `pnpm dlx shadcn@4.23.0 init --cwd apps/editor --template vite --no-monorepo --no-rtl`; sonra `add <bileşen>` (aynı `--cwd`) | `ui.shadcn.com/docs/installation/vite` açılıyor: Tailwind kurulumu, `tsconfig` içinde `@/*` takma adı, `vite.config.ts` içinde `resolve.alias` (`@types/node`), `init`, `add`; `init --help` (CLI 4.23.0) `--template`, `--base`, `--no-monorepo`, `--rtl` seçeneklerini veriyor; `ui.shadcn.com/docs/components` listesinde button, input, textarea, label, field, select, checkbox, badge, card, table, tabs, dialog, alert-dialog, dropdown-menu, tooltip, toast, skeleton, spinner, empty, alert, separator, scroll-area ve kbd var | Radix UI ilkelleriyle (`radix-ui` 1.8.1) elle bileşen |
| Yönlendirme | `react-router` 8.5.1 (27 Ekim 2026; etiket `react-router@8.5.1`); npm. Tek paket (`react-router-dom` yok). Data Mode: `createBrowserRouter` `react-router` içinden, `RouterProvider` `react-router/dom` içinden | `pnpm --filter @mutalaa/editor add react-router` | `reactrouter.com/start/data/installation` açılıyor ve bu içe aktarma yollarını veriyor; paket Node 22.22+ ve React 19.2.7+ ister (React 19.3.1 ve Node 24 karşılar) | `react-router` 7 hattı (sürüm notlarındaki son 7.x girdisi 7.18.0; A15.0'da doğrulanır) |
| Sunucu durumu | `@tanstack/react-query` 5.105.0 (26 Ekim 2026; etiket `@tanstack/react-query@5.105.0`); npm | `pnpm --filter @mutalaa/editor add @tanstack/react-query` | `tanstack.com/query/latest/docs/framework/react/overview` açılıyor; React 18 ya da 19 ister | SWR 2.5.1 (12 Ağustos 2026) |
| API tipi, istemci ve sorgu kancaları | `openapi-typescript` 7.13.0 (etiket `openapi-typescript@7.13.0`) ve `openapi-fetch` 0.17.0 (etiket `openapi-fetch@0.17.0`), ikisi 11 Şubat 2026; `openapi-react-query` 0.5.4 (11 Şubat 2026; etiket `openapi-react-query@0.5.4`; `useQuery`, `useMutation`, `useInfiniteQuery`); npm. Girdi: A14'ün ürettiği `server/Mutalaa.Api/openapi/v1.json` (OpenAPI 3.1) | `pnpm --filter @mutalaa/editor add openapi-fetch openapi-react-query`; `add -D openapi-typescript`; `gen:api`: `openapi-typescript ../../server/Mutalaa.Api/openapi/v1.json -o src/api/schema.d.ts` | `openapi-ts.dev/openapi-fetch/` ve `openapi-ts.dev/openapi-react-query/` açılıyor (`createFetchClient<paths>({ baseUrl })`, `createClient(fetchClient)`); `openapi-react-query` `openapi-fetch ^0.17.0` ve `@tanstack/react-query ^5.80.0` ister, tipleri pakette; `openapi-typescript` `typescript ^5.x` ister (kökte 6.0.3: uyarı çıkar); denemede OpenAPI 3.1.1 örnek belgesinden tip üretildi ve `build` geçti | `@hey-api/openapi-ts` 0.99.0 (22 Haziran 2026); Orval 8.46.0 (30 Ekim 2026) |
| Test araçları | `vitest` 5.0.5 (kök); `@testing-library/react` 16.3.3 (27 Ağustos 2026), `@testing-library/dom` 10.4.2 (eş bağımlılık), `@testing-library/user-event` 14.6.8, `@testing-library/jest-dom` 7.0.1; `jsdom` 30.1.3 (15 Ekim 2026); npm | `pnpm --filter @mutalaa/editor add -D` ile | Vitest 5 Node 22.12+, 24 ya da 26+ ister; `jsdom` 30 Node 22.22.2+, 24.15.0+ ya da 26+ ister (yerel Node 24.21.0; Node 24 hattının son sürümü 24.22.2, 27 Ekim 2026); jest-dom 7 `@testing-library/dom >=10 <11` ister; aynı sürümlerle 3 bileşen testi geçti (1 Kasım 2026) | `happy-dom` 21.0.4 (Node 20+) |
| Erişilebilirlik denetimi | `eslint-plugin-jsx-a11y` 6.10.2 (statik denetim; eş bağımlılığı ESLint 9 ve altı, kökte 10: uyarı) ve `axe-core` 4.14.0 (5 Ekim 2026; bileşen testinde `axe.run`, tipleri pakette); npm | `pnpm --filter @mutalaa/editor add -D eslint-plugin-jsx-a11y axe-core` | Kayıt sürümleri doğrulandı; denemede lint kuralları ve axe testi çalıştı; `color-contrast` kuralı jsdom'da ölçülemez, kontrasta `arayuz-denetcisi` bakar | `jest-axe` 11.0.0 (elle tip bildirimiyle denemede çalıştı); `@chialab/vitest-axe` 0.19.2 Vitest 5'i eş bağımlılık aralığına almıyor |
| Metin farkı (412 sonrası "kayıt değişmiş" gösterimi) | `diff` (jsdiff) 9.0.0 (13 Nisan 2026); npm; tipleri pakette, ESM ve CJS | `pnpm --filter @mutalaa/editor add diff` | Kayıt doğrulandı; Arapça birleşik işaretli sentetik örnekte A15.0'da sınanır | Alan düzeyinde elle karşılaştırma |
| Sayfa görseli yakınlaştırma (OCR ekranı) | `react-zoom-pan-pinch` 4.2.0 (3 Eylül 2026); npm; tipleri pakette | `pnpm --filter @mutalaa/editor add react-zoom-pan-pinch` | Kayıt doğrulandı (React eş bağımlılığı `*`); bölge kutusu katmanıyla A15.4'te sınanır | CSS dönüşümüyle elle yakınlaştırma |
| Sayfa görseli TIFF gösterimi (OCR ekranı) | TIFF çözücü gerekli; kitaplık A15.0'da seçilir ([K-48](../../00-ozet/02-karar-defteri.md#k-48--editör-api-kuralları-inceleme-kararı-ikinci-onay-eşzamanlılık-yayın-talebi-ve-sayfa-görseli) madde 8: `GET /api/v1/scans/{baski}/{sayfa}` ham sayfa dosyasını olduğu gibi `image/tiff`, `image/png` ya da `image/jpeg` olarak verir, API baytları dönüştürmez; TIFF gösterimi panelin işidir) | A15.0'da `arastirmaci` aday kitaplıkları npm kaydından ve resmî belgeden doğrular; sürüm tabloya yazılır | A15.0'da sentetik bir TIFF ile sınanır (gerçek Elmalılı taraması panele alınmaz); sürüm kilit dosyasından yazılır | Sunucuda PNG'ye çevirme (API'nin ham dosyayı olduğu gibi verme kararını değiştirir; `/karar` ister) |
| Arapça yazı tipi (kanonik metnin gösterimi) | Amiri Quran, `AmiriQuran-Regular.ttf`; `github.com/google/fonts` commit `6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec`, yol `ofl/amiriquran/`; kaynak kaydı `amiri-quran-font` (A06) | A15.0'da `curl -L` ile `https://raw.githubusercontent.com/google/fonts/6c1dbe27dcf7d817d4b62cec033ba77fa8e2a5ec/ofl/amiriquran/AmiriQuran-Regular.ttf` adresinden `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` altında yeni boş klasöre iner; panel kopyasını `public/fonts/` altından `@font-face` ile yükler | Adres açılıyor (HTTP 200, 1 Kasım 2026); dosya TrueType, 136.920 bayt, SHA-256 `e2a47644762d16bdfb6d33e0d8db8c6ff30beae84150ef5a705316bbd829455c`; ad "Amiri Quran Regular", sürüm 1.003, 1.446 glif; Tanzil Uthmani metnindeki 69 ayırt edici kod noktasının 69'u fontta var; Türkçe Latin harfleri yok | `@fontsource/amiri-quran` 5.3.0 (19 Temmuz 2026; npm) |
| Çalışma ortamı ve imajlar | Node 24 (kök `.nvmrc`: `24`); Docker Hub `node:24-alpine` (28 Ekim 2026 güncel; özet `sha256:8a32c8cf…`; amd64, arm64, s390x) ve `nginx:stable-alpine` (29 Ekim 2026 güncel; özet `sha256:0e52bd05…`; amd64 ve arm64 dahil sekiz mimari) | `docker pull` (herkese açık imajlar); Dockerfile A15.2'de | İki etiketin Docker Hub kaydı açılıyor (HTTP 200) | `node:24-slim`; `nginx:alpine` (A15.0'da etiket varlığı doğrulanır) |

Kendimiz yapacağımız işler: yedi rota ve ortak inceleme bileşenleri (karar, `If-Match`, toplu karar, ikinci onay gösterimi, rozet); ProblemDetails kodlarının Türkçe ileti tablosu; role göre düğme gizleme; OCR bölge kutusu katmanı; `gen:api` betiği ve CI denetimi; Dockerfile ve nginx yapılandırması; bileşen testleri ve fikstür yanıtları (sentetik metin).

## Adımlar
### A15.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: npm kaydı (`dist-tags.latest`), belge sayfaları, GitHub etiketleri (`git ls-remote`; `api.github.com` kullanılmaz), ham dosya adresi (`curl -sIL`) ve Docker Hub etiketleri. Açılmayan adresin yerine yedek adayı kullan; değişen sürümü tabloya yaz.
- Kitaplıkları `pnpm --filter @mutalaa/editor add` ile ekle. Yüklü sürümleri `pnpm-lock.yaml` içinden oku ve tabloyla karşılaştır; fark varsa tabloya yaz. Eş bağımlılık uyarılarını (`openapi-typescript` için `typescript ^5.x`, `eslint-plugin-jsx-a11y` için ESLint 9 ve altı) gerekçesiyle kayda geçir; pnpm'in `peerDependencyRules` ayarıyla kapat.
- Yerel Node'un `jsdom` aralığını (24.15 ve üstü) karşıladığını denetle (`node --version`). Karşılamıyorsa `happy-dom` yedeğini kullan; [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md) belgesindeki Node alt sınırı `belge-esitle` ile eşitlenir.
- Amiri Quran dosyasını Claude Code indirir: dosya `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` altında yeni boş klasöre iner. Sabit commit'teki ham dosya değişmez; boyutu (136.920 bayt) ve SHA-256'sı `## Tedarik` tablosundaki değerle aynı olmalıdır. `pipeline/sources/amiri-quran-font.toml` kaydında `surum` commit SHA'sı, `kaynak_url` sabit adres olur; dosya adı ve boyut `notlar` alanına yazılır, SHA-256 klasördeki `SHA256SUMS` dosyasındadır. Kapsam notu (Tanzil Uthmani'deki 69 kod noktasının 69'u) A10'un indirdiği Tanzil dosyasıyla yeniden ölçülerek `notlar` alanında güncellenir. `uv --directory pipeline run mutalaa sources check` çıktısı `<N> kayit, 0 hata, 0 uyari` olur (N, o güne dek açılan kayıt sayısıdır).
- `node:24-alpine` ve `nginx:stable-alpine` etiketlerinin Docker Hub'da bulunduğunu doğrula (A15.2'deki Dockerfile bunları kullanır).
- OCR ekranı için bir TIFF çözücü seç (A14 görsel ucu ham TIFF verir, K-48 madde 8): `arastirmaci` aday kitaplıkları npm kaydından doğrular, seçilen sürüm `## Tedarik` tablosundaki satıra yazılır ve sentetik bir TIFF ile sınanır.
- **Bitti sayılır:** tablodaki her adres açılıyor; kilit dosyasındaki sürümler tabloyla aynı (fark tabloda yazılı); eş bağımlılık uyarıları gerekçesiyle kayıtlı; yazı tipi dosyası `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` altında ve SHA-256'sı `SHA256SUMS` dosyasında; `sources check` 0 hata.

### A15.1 · Doğrulamalar
- `arastirmaci` resmî kaynaktan doğrular: `react-router` Data Mode kurulumu (A15.0'da 8.5.1 olarak doğrulandı; Teknoloji yığını §2.5'teki "sürüm Doğrulanacak" notu bu sürümle kapanır); shadcn/ui'nin Vite ve Tailwind CSS v4 kurulum adımları; `openapi-typescript`, `openapi-fetch` ve `openapi-react-query` güncel kullanımı; Vite vekil yapılandırması.
- Sürümler kurulum günü kilit dosyasından yazılır; uydurulmaz. Teknoloji yığını §2.5 `belge-esitle` ile güncellenir.
- **Bitti sayılır:** kurulum komutları kaynak bağlantısıyla raporlu.

### A15.2 · İskelet ve API istemcisi
- `apps/editor` (`@mutalaa/editor`): Vite, React, TypeScript, Tailwind CSS v4, shadcn/ui (`init` komutu `## Tedarik` tablosundadır; bileşenler `src/components/ui/` altına kopyalanır; gerekenler `add` ile eklenir), `react-router` (Data Mode), `@tanstack/react-query`.
- `vite.config.ts`: `/api` vekili `http://localhost:5080`; geliştirme sunucusu 5173; `@` takma adı `src/` klasörüne (`tsconfig` içinde de).
- `gen:api` betiği: `server/Mutalaa.Api/openapi/v1.json` → `src/api/` altında üretilmiş tipler; istemci `openapi-fetch`, kancalar `openapi-react-query` ile kurulur (`$api.useQuery`, `$api.useMutation`, `$api.useInfiniteQuery`); sarmalayıcı kancalar elle yazılmaz. CI'daki "Editör API istemcisi güncel mi" denetimi yerelde de koşar.
- İç bağımlılıklar yalnız `@mutalaa/anchors` ve `@mutalaa/search`; `toLocale*` ve `localeCompare` ESLint kuralları geçerli.
- Dockerfile: `node:24-alpine` ile derleme, `nginx:stable-alpine` ile sunum; nginx `/api/` isteklerini `http://api:8080` adresine aktarır; port 5174.
- **Bitti sayılır:** `build` ve `typecheck` yeşil; `gen:api` sonrası `git diff` boş.

### A15.3 · Oturum ve ortak inceleme bileşenleri
- `giris`: `POST /api/v1/auth/login`, `GET /auth/me` ile rol, `logout`. 401 `giris` rotasına, 403 yetki mesajına götürür. Geliştirmede A14'ün `DevAutoLogin` ayarı açıksa giriş atlanır.
- Kuyruk listesi: `GET /reviews` süzgeçleri (`hedef_tablo`, `alan`, `durum`), imleçli sayfalama (`useInfiniteQuery`), `GET /reviews/stats` sayıları.
- Karar bileşeni: `POST /reviews/{id:long}/decision` gövdesi `{karar: onaylandi|reddedildi, duzenlenen?: {metin}, gerekce}` ve **her zaman `If-Match`** taşır (değer, kayıt okunurken gelen `ETag` ya da `xmin`; biçim `"{xmin}"`, `*` ve `W/` gönderilmez). Başlık eksikse API 428 `surum-gerekli` verir (istemci hatasıdır); 412 `surum-uyusmazligi` alınca kayıt yeniden yüklenir ve fark `diff` ile gösterilir. 412 yalnız `If-Match` uyuşmazlığı değildir: Domain kuralı hata verecekken (409, 422, 400) incelemenin `xmin` değeri araya giren başka bir kararla değişmişse API Domain hatasının yerine 412 döner (K-48 madde 6). Panel bu durumda kuralın hata mesajını değil "kayıt değişti, yenilendi" akışını gösterir; yenilenen kayıtta kural gene ihlal ediliyorsa asıl hata ikinci denemede kendi koduyla görünür. Toplu kararda aynı kural geçerlidir ve `kimlikler` değişen kayıtlardır. `gerekce` zorunludur (en çok 2.000 karakter); `gerekce` ve `duzenlenen.metin` NUL ya da eşleşmemiş vekil karakter içeremez (API 400 `dogrulama` verir; panel bu girdiyi göndermeden önce temizler ya da uyarır).
- Toplu karar: `POST /reviews/decisions` gövdesi `{kararlar: [{id, xmin, karar, duzenlenen?, gerekce}]}`, 1 ile 100 öğe, ya hepsi ya hiçbiri. **`If-Match` yalnız tekil karardadır;** toplu kararda sürüm her öğenin `xmin` alanındadır (liste öğesinden alınır). 412 yanıtı `kimlikler` uzantısında tutmayan kayıtların tam listesini verir (panel yalnız bunları yeniler); bulunamayan kayıt 404 ve `kimlikler`; kural ihlali ilgili durumu ve `kimlik` uzantısını verir. Aynı kimlik ya da aynı hedef için ikinci karar 400'dür.
- İkinci onay gereken alanlarda (meal ve tefsir metni) ilk onay ve bekleyen ikinci onay ayrı gösterilir: liste ve ayrıntı `ikinci_onay_bekliyor` alanını, ayrıntı `inceleyen`, `ikinci_inceleyen`, `ikinci_incelendi_at`, `ikinci_gerekce` ve `duzenlenen` alanlarını verir. İkinci onaylayan değeri değiştiremez (düzenleme alanı kapalı; değiştirmek isteyen reddeder); aynı kişi iki kez onaylayamaz ve öneren kendi önerisini onaylayamaz (409). "Doğrulanmamış" rozeti `dogrulanmamis` alanından çizilir (K-25): `yz_modeli` dolu VE NOT (review `onaylandi` ve hedef onaylı); kural liste ve ayrıntıda aynıdır, panel kuralı yeniden hesaplamaz. Açık ya da reddedilmiş yapay zekâ taslağı da rozet taşır. `dogrulanmis` yalnız ayrıntıdadır.
- **Ofsetli birimde metin düzeltmesi.** Birimin `marks` alanı boş dizi değilse ya da `sentences` doluysa metni değiştiren düzeltme önerisi ve metni değiştiren onay (ilk onay dahil, `duzenlenen` ile ya da öneriyle) API'de 422 `inceleme-desteklenmiyor` alır (K-48 madde 2, [BÇ-53](../07-belge-celiskileri.md)); durum onayı, ret ve metni değiştirmeyen onay serbesttir. Panel bu 422'yi "Bu birimin ofsetli alanları (işaretler, cümleler) var; metin düzeltmesi A16'da desteklenecek" iletisiyle gösterir, düzeltme düğmesini o birim için devre dışı bırakır ve "Açık soru: A16" etiketi koyar. Panel ofsetli olup olmadığını birim ayrıntısındaki `marks` ve `sentences` alanlarından öngörebilir; son söz API'nindir. İkinci onayda `duzenlenen` gönderilmez (API 422 verir).
- ProblemDetails `kod` ve `type` değerleri (`dogrulama`, `capa-gecersiz`, `degistirilemez-metin`, `inceleme-desteklenmiyor`, `durum-gecisi-gecersiz`, `cakisma`, `surum-uyusmazligi`, `surum-gerekli`, `yontem-desteklenmiyor`, `yayin-suruyor`, `kalite-kapisi`, `onceki-yayin-bozuk`, `depo-erisilemiyor`, `sunucu-hatasi` …; tablo: [Backend API](../../02-mimari/05-backend-api.md) §6) Türkçe iletiye çevrilir. `kalite-kapisi` yanıtı `kapi_raporu`, `yayin-suruyor` yanıtı `yayin`, `capa-gecersiz` yanıtı `capa_hata_kodu`, toplu 412 yanıtı `kimlikler` uzantısını taşır. Rota kısıtları: inceleme kimliği `{id:long}`, yayın kimliği `{id:int}`; kimlik biçimi yanlışsa uç eşleşmez (404).
- Arapça metin `lang="ar"` ve `dir="rtl"` ile çizilir; yazı tipi Amiri Quran'dır (A15.0). Kanonik metin olduğu gibi gösterilir; istemci normalize etmez.
- **Bitti sayılır:** bileşen testleri yeşil.

### A15.4 · Kuyruk ekranları
- `kuyruk/ocr` (Elmalılı hazırlığı §7): solda sayfa görseli (`react-zoom-pan-pinch` ile yakınlaştırılır) ve üstünde bölge kutuları, sağda aktarılmış metin, üstte Tanzil âyet metni ve ilgili meal birimi. Görsel `GET /api/v1/scans/{baski}/{sayfa}` ucundan gelir ([K-48](../../00-ozet/02-karar-defteri.md#k-48--editör-api-kuralları-inceleme-kararı-ikinci-onay-eşzamanlılık-yayın-talebi-ve-sayfa-görseli) madde 8): `baski` `^[a-z0-9-]{1,64}$`, `sayfa` `^c[0-9]{2}-s[0-9]{4}$` desenine uyar; yanıt ham dosyadır (`image/tiff`, `image/png` ya da `image/jpeg`, `Cache-Control: private, no-store`); bulunamazsa 404 `bulunamadi`. API TIFF'i dönüştürmez: gösterim panelin işidir (A15.0'da seçilen TIFF çözücü, `## Tedarik`). Birimden görsele eşleme (`attrs` alan adları) A16'da kesinleşir; o zamana kadar panel `baski` ve `sayfa` değerini birimin `attrs` alanından alamıyorsa görsel alanı "görsel eşlemesi henüz tanımlı değil" uyarısı gösterir. Eylemler: Onayla, Düzelt, Böl, Birleştir, Belirsiz işaretle, Not ekle. API karşılığı olanlar: Onayla (metin onayı), Düzelt (`duzenlenen: {metin}` ile onay ya da `POST /units/{anchor}/corrections` ile yeni öneri) ve Reddet. **Böl ve Birleştir** için karşılık kurulmadı; K-48 "Belirsiz işaretle" ve "Not ekle" için de karşılık tanımlamaz. Karşılığı olmayan düğmeler devre dışıdır, "Açık soru" etiketi taşır ve A16'da karara bağlanır. Dört göz: düzelten ve onaylayan farklı kişidir (öneren kendi önerisini onaylayamaz, 409).
- `kuyruk/lemma` (Kelime anlamları §6): dalga ve kök sırası; kartta lemma, kök, tür, sıklık, KWIC (Arapça ve Elmalılı meali), taslak alanları, aynı kökün onaylı anlamları ve kılavuz uyarıları. A14'te çalışan eylemler: Onayla ve Reddet (`lemma_gloss` + `anlam_kisa`, `lemma` + `status`; hedef `aday` olmalıdır). **Ertelenen eylemler (A17 ve A18):** "Düzenle ve onayla" (anlam düzenleme), "Uzmana gönder" ve "yalnızca etimolojik" işaretle (ayrıca "Reddet ve yeniden taslak iste" içindeki yeniden taslak isteği için karşılık kurulmadı); API ilk üçüne 422 `inceleme-desteklenmiyor` verir, düğmeler devre dışıdır ve "Açık soru" etiketi taşır. Türkçe kelime → kök kartı (`tr_root_index`, `tr_form`) da A18'dedir: API bu hedeflerin `hedef_anahtar` değerini ayrıştırmaz (Kök ve lemma §5 madde 7).
- `kuyruk/baglanti` (İktibas tespiti §12): sıra önce tutarsız atıflar, sonra toplu onaya uygun gruplar, en son gri bölge. Kartta paragraf ve vurgulu dizi, aday âyet (Arapça ve meal), kanıt özeti ve alternatifler. A14'te çalışan eylemler: Onayla ve Reddet (`xref` + `status`; hedef `aday` olmalıdır). **Ertelenen eylemler (A18):** Hedefi değiştir, Aralığı düzelt, tür değiştir, İma olarak işaretle (tür değişimi) ve Kalıp listesine ekle; API 422 `inceleme-desteklenmiyor` verir, düğmeler devre dışıdır ve "Açık soru" etiketi taşır. Toplu onayda rastgele %10 örneklem incelenir; tek hata toplu onayı iptal eder.
- Karar ucunda karşılığı belirsiz ya da ertelenen eylemler (Böl, Birleştir, Kalıp listesine ekle, anlam düzenleme, bağlantıda hedef ve aralık değişimi, uzmana gönder, etimolojik işaret) için düğme devre dışı kalır, "Açık soru" etiketi taşır ve A16, A17 ya da A18'de karara bağlanır (K-48 madde 2).
- **Bitti sayılır:** üç kuyruk boş, dolu ve hata durumunda doğru çiziliyor (fikstür yanıtlarıyla testler).

### A15.5 · Kaynaklar, birimler, yayınlar
- `kaynaklar`: liste ve ayrıntı (`GET /sources`, `/sources/{slug}`: ad, tür, sürüm, adres, atıf satırı, dosya özeti, birim sayısı). Salt okunur: kaynak kaydı `pipeline/sources/` dosyasında yaşar, panel yalnız gösterir (K-13).
- `birimler`: kaynak, önek ve arama süzgeci (`GET /units`); ayrıntıda kanonik metin, `metin_durumu`, `content_hash`, `marks`. Düzeltme formu yalnız kendi ürettiğimiz metinde görünür; API'nin `duzeltilebilir` alanı buna göre kullanılır, değişmez metinde (`unit.kind = 'ayet'` ya da `source.tur = 'kuran_metni'`, K-48 madde 5) düzeltme düğmesi yoktur. Düzeltme `POST /units/{anchor}/corrections` ile `{metin, gerekce}` gönderir; çapa yol parçası olarak `encodeURIComponent` ile kodlanır; geçersiz çapa 400 `capa-gecersiz` (`capa_hata_kodu`) alır.
- `yayinlar`: liste (`GET /releases?derleme=&cursor=`) ve ayrıntı (`/releases/{id:int}`: `kapi_raporu`, `ozetler`, `manifest`, `ETag`); kalite kapısı raporu tablosu (paket ve kaynak başına girdi ya da girmedi, kural kodu, gerekçe). Admin eylemleri: yeni yayın talebi `POST /releases` `{derleme, paketler?, notlar?}` (202; `dev`, `internal`, `public`), önizleme `POST /releases/preview` `{derleme, paketler?}` (200 `{derleme, kapi_raporu, uyarilar}` ya da 422 `kalite-kapisi` ve `kapi_raporu`; 422 `onceki-yayin-bozuk`, 503 `depo-erisilemiyor` ve 409 `cakisma` ayrı iletiyle gösterilir), terfi `POST /releases/{id}/promote` ve geri alma `POST /releases/{id}/rollback` `{notlar?}` (202; terfi kaynağı `yayinlandi` durumundaki `internal` yayındır, geri alma güncel yayına yapılamaz, ikisinde de 409 `durum-gecisi-gecersiz`). Üç talep de açık satır varken 409 `yayin-suruyor` alır ve yanıtın `yayin` uzantısındaki satır (`{id, surum, derleme, durum, talep}`) gösterilir. Talep yalnız `release` satırı açar; işi Yayınlayıcı `watch` yapar; durum ayrıntıdan (`durum`) okunur.
- **Bitti sayılır:** üç rotanın testleri yeşil.

### A15.6 · Test ve arayüz denetimi
- Vitest ve Testing Library: oturum yönlendirmesi, role göre düğme gizleme, 412 akışı, toplu karar sınırı, Tanzil biriminde düzeltme düğmesinin yokluğu, "doğrulanmamış" rozeti, ikinci onay gösterimi. Her rotanın bileşen testinde `axe-core` ihlal bildirmez (`color-contrast` kuralı jsdom'da kapalıdır).
- `arayuz-denetcisi`: etiketler, odak sırası, klavyeyle karar verme, `lang` ve `dir`, kontrast. Kullanıcı ekran görüntüsü alıp `.tmp/` altına koyarsa denetçi onu da okur.
- **Bitti sayılır:** `lint`, `typecheck`, `test`, `build` yeşil; denetçi raporunda engelleyici bulgu yok.

## Kabul ölçütleri
- [ ] `## Tedarik` tablosundaki her adres açılıyor ve kilit dosyasındaki sürümler tabloyla aynı (fark varsa tabloda yazılı).
- [ ] Amiri Quran dosyası `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` altında; SHA-256'sı `SHA256SUMS` dosyasında; `uv --directory pipeline run mutalaa sources check` `<N> kayit, 0 hata, 0 uyari` veriyor (N, o güne dek açılan kayıt sayısıdır).
- [ ] Yedi rota var; `giris` dışındaki rotalar oturumsuz erişimde `giris` rotasına yönlendiriyor (test).
- [ ] `src/api/` yalnız üretilmiş tipleri ve istemciyi içeriyor; `gen:api` sonrası `git diff --exit-code apps/editor/src/api` 0.
- [ ] Karar istekleri `If-Match` taşıyor; 412'de kayıt yeniden yükleniyor (test).
- [ ] İkinci onay gereken alanlarda ilk ve ikinci onay ayrı gösteriliyor; `yz_modeli` dolu kayıtta rozet var (test).
- [ ] Tanzil biriminde düzeltme düğmesi yok (test).
- [ ] `pnpm --filter @mutalaa/editor lint`, `typecheck`, `test` ve `build` yeşil.
- [ ] `arayuz-denetcisi` raporunda engelleyici bulgu yok.
- Yerelde A14 API'siyle giriş yapılıp yedi rotanın açılması kullanıcıya bırakılır; aşamayı bekletmez, kapanış raporunda "kullanıcıya bırakıldı" diye yazılır.

## Doğrulama
```bash
pnpm install
pnpm --filter @mutalaa/editor gen:api && git diff --exit-code apps/editor/src/api
pnpm --filter @mutalaa/editor lint
pnpm --filter @mutalaa/editor typecheck
pnpm --filter @mutalaa/editor test
pnpm --filter @mutalaa/editor build
uv --directory pipeline run mutalaa sources check
```
Gözle kontrol kullanıcıya bırakılır: API (`dotnet watch --project server/Mutalaa.Api`) ve panel (`pnpm dev:editor`) ayrı terminallerde açılır; panel `http://localhost:5173` adresindedir.

## Dikkat
- API tipleri elle yazılmaz; uç değişirse önce A14'te OpenAPI belgesi güncellenir, sonra `gen:api`.
- Hazır kaynak metni düzenlenemez; arayüz düzeltme düğmesini göstermez. Kanonik metin istemcide normalize edilmez.
- Kültür: `toLocaleLowerCase()` argümansız kullanılmaz; Türkçe sıralama `Intl.Collator('tr')` ile yapılır.
- Panel yalnız yerelde çalışır (`127.0.0.1`); dışarı açılmaz.
- Yapay zekâ taslakları onaylanana kadar "doğrulanmamış" rozetiyle görünür; panel taslağı onaylı gibi göstermez.
- Arayüz metni Türkçedir; kod tanımlayıcıları İngilizcedir.
- Test fikstürlerinde Kur'an, meal ya da hadis metni hafızadan yazılmaz; açıkça sentetik metin ("Deneme paragrafı 1 …") ya da kaynak dosyasından alınmış küçük parça kullanılır.
- Amiri Quran Türkçe Latin harflerini içermez: yalnız `lang="ar"` metinde kullanılır, Türkçe arayüz ve meal metni varsayılan yazı tipiyle çizilir. Yazı tipinde bulunmayan bir işaret yedek yazı tipiyle çizilir; metin değiştirilmez.
- Kitaplık sürümleri `pnpm-lock.yaml` içindedir; sürüm yükseltmesi tabloya ve kilit dosyasına birlikte yazılır.

## İnsan adımları
- Yok. Gözle kontrol kullanıcıya bırakılır ve aşamayı bekletmez. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/editor/` (`package.json`, `vite.config.ts`, `src/routes/*`, `src/api/*`, `src/components/*`, testler, `Dockerfile`)
- `pnpm-lock.yaml` güncellemesi
- `data/gelen/amiri-quran-font/<YYYY-AA-GG>/` (yazı tipi dosyası) ve güncellenmiş `pipeline/sources/amiri-quran-font.toml`
- Gerekirse karar defterinde OCR ve bağlantı eylemleri için açık soru notları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A15-editor-paneli.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A14](./A14-api-editor-uclari.md) · Sonraki: [A16](./A16-elmalili-meali.md)
