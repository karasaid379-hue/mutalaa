# A15 · Editör paneli

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-13](../../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A14](./A14-api-editor-uclari.md) · **İnsan adımı:** yok
> **Ajanlar:** `web-gelistirici` · `arayuz-denetcisi` · `test-yazari` · `arastirmaci` · `inceleyici` · **Beceriler:** `windows-sorun` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A15`

## Amaç
`apps/editor` kurulur: editörlerin kaynakların lisans durumunu yönettiği, birimleri incelediği, OCR satırlarını düzelttiği, kelime anlamı ve bağlantı adaylarını onayladığı ve yayın başlattığı iç web aracı. API tipleri OpenAPI belgesinden üretilir; elle tip yazılmaz. A16–A19'un insan turları bu panelde yürür.

## Okunacak belgeler
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1 (`apps/editor`), §2 bağımlılık kuralları, §4.1, §5 ESLint, §7 `ci-ts.yml`
- [Backend API](../../02-mimari/05-backend-api.md): §4 uçlar, §4.1 kuyruklar, §4.2 uç kuralları, §6 kimlik, OpenAPI ve hata modeli
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §8 `review` ve inceleme akışı
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §7 OCR inceleme ekranı · [Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md): §6 lemma kuyruğu
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §12 bağlantı kuyruğu ve toplu onay · [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §5 madde 7
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §4 kapı raporu · [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §2.5
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §4 `editor` servisi ve Dockerfile notu, §6 adım 5

## Kapsam
**Yapılır**
- Vite, React, TypeScript, Tailwind CSS v4 ve shadcn/ui iskeleti; `gen:api` (openapi-typescript ve openapi-fetch).
- Rotalar: `giris`, `kuyruk/baglanti`, `kuyruk/lemma`, `kuyruk/ocr`, `kaynaklar`, `birimler`, `yayinlar`.
- Ortak inceleme bileşenleri: karar, `If-Match`, toplu karar, ikinci onay gösterimi, "doğrulanmamış" rozeti.
- `apps/editor/Dockerfile` (`app` profili).

**Yapılmaz**
- API uçları (A14). Kuyruklara veri yazan hat işleri (A16–A19).
- `surah_alias` ve `quran_word_fix` için ayrı rota (Proje yapısı §1: yok, Açık soru). `surah_alias` onayı API karar uçlarıyla (A11); `quran_word_fix` `kuyruk/lemma` ya da API ile (A17).
- `ui-tokens` teması (A22'den sonra bağlanır; bu aşamada shadcn/ui varsayılan teması). Web sitesi (A38).

## Adımlar
### A15.1 · Doğrulamalar
- `arastirmaci` resmî kaynaktan doğrular: `react-router` güncel ana sürümü ve Vite ile kurulumu (Teknoloji yığını §2.5'te "sürüm Doğrulanacak"); shadcn/ui'nin Vite ve Tailwind CSS v4 kurulum adımları; `openapi-typescript` ve `openapi-fetch` güncel kullanımı; Vite vekil yapılandırması.
- Sürümler dokümanda yazmıyorsa kurulum günü kilit dosyasına yazılır; uydurulmaz.
- **Bitti sayılır:** kurulum komutları kaynak bağlantısıyla raporlu.

### A15.2 · İskelet ve API istemcisi
- `apps/editor` (`@mutalaa/editor`): Vite, React, TypeScript, Tailwind CSS v4, shadcn/ui (bileşenler `src/components/` altına kopyalanır), `react-router`, `@tanstack/react-query`.
- `vite.config.ts`: `/api` vekili `http://localhost:5080`; geliştirme sunucusu 5173.
- `gen:api` betiği: `server/Mutalaa.Api/openapi/v1.json` → `src/api/` altında üretilmiş tipler ve `openapi-fetch` istemcisi. CI'daki "Editör API istemcisi güncel mi" denetimi yerelde de koşar.
- İç bağımlılıklar yalnız `@mutalaa/anchors` ve `@mutalaa/search`; `toLocale*` ve `localeCompare` ESLint kuralları geçerli.
- Dockerfile: `node:24-alpine` ile derleme, `nginx:stable-alpine` ile sunum; nginx `/api/` isteklerini `http://api:8080` adresine aktarır; port 5174.
- **Bitti sayılır:** `build` ve `typecheck` yeşil; `gen:api` sonrası `git diff` boş.

### A15.3 · Oturum ve ortak inceleme bileşenleri
- `giris`: `POST /api/v1/auth/login`, `GET /auth/me` ile rol, `logout`. 401 `giris` rotasına, 403 yetki mesajına götürür. Geliştirmede A14'ün `DevAutoLogin` ayarı açıksa giriş atlanır.
- Kuyruk listesi: `GET /reviews` süzgeçleri (`hedef_tablo`, `alan`, `durum`), imleçli sayfalama, `GET /reviews/stats` sayıları.
- Karar bileşeni: `POST /reviews/{id}/decision` her zaman `If-Match` taşır; 412'de kayıt yeniden yüklenir ve fark gösterilir. Toplu karar en çok 100 kayıttır.
- İkinci onay gereken alanlarda (meal ve tefsir metni, `license_status`, `kurul_onay`, `embed_ok`) ilk onay ve bekleyen ikinci onay ayrı gösterilir. `yz_modeli` dolu kayıt "doğrulanmamış" rozeti taşır (K-25).
- ProblemDetails `type` kodları (`degistirilemez-metin`, `surum-uyusmazligi`, `yayin-suruyor`, `lisans-kapisi` …) Türkçe iletiye çevrilir.
- Arapça metin `lang="ar"` ve `dir="rtl"` ile çizilir. Kanonik metin olduğu gibi gösterilir; istemci normalize etmez.
- **Bitti sayılır:** bileşen testleri yeşil.

### A15.4 · Kuyruk ekranları
- `kuyruk/ocr` (Elmalılı hazırlığı §7): solda sayfa görseli ve bölge kutuları, sağda aktarılmış metin, üstte Tanzil âyet metni ve ilgili meal birimi. Eylemler: Onayla, Düzelt, Böl, Birleştir, Belirsiz işaretle, Not ekle. Dört göz: düzelten ve onaylayan farklı kişidir. Görsel A14.4'teki karara bağlıdır; uç yoksa alan "görsel ucu tanımlı değil" uyarısı gösterir.
- `kuyruk/lemma` (Kelime anlamları §6): dalga ve kök sırası; kartta lemma, kök, tür, sıklık, KWIC (Arapça ve Elmalılı meali), taslak alanları, aynı kökün onaylı anlamları ve kılavuz uyarıları. Eylemler: Onayla, Düzenle ve onayla, Reddet ve yeniden taslak iste, Uzmana gönder, "yalnızca etimolojik" işaretle. Türkçe kelime → kök kartı da bu rotadadır (Kök ve lemma §5 madde 7).
- `kuyruk/baglanti` (İktibas tespiti §12): sıra önce tutarsız atıflar, sonra toplu onaya uygun gruplar, en son gri bölge. Kartta paragraf ve vurgulu dizi, aday âyet (Arapça ve meal), kanıt özeti ve alternatifler. Eylemler: Onayla, Reddet, Hedefi değiştir, Aralığı düzelt, İma olarak işaretle, Kalıp listesine ekle. Toplu onayda rastgele %10 örneklem incelenir; tek hata toplu onayı iptal eder.
- Karar ucunda karşılığı belirsiz eylemler (Böl, Birleştir, Kalıp listesine ekle) `onerilen` alanıyla gönderilir. Karşılık kurulamıyorsa düğme devre dışı kalır, "Açık soru" etiketi taşır ve A16 ya da A18'de karara bağlanır.
- **Bitti sayılır:** üç kuyruk boş, dolu ve hata durumunda doğru çiziliyor (fikstür yanıtlarıyla testler).

### A15.5 · Kaynaklar, birimler, yayınlar
- `kaynaklar`: liste ve ayrıntı (lisans, Kurul alanları, `embed_ok`, `kisitlar`, birim sayısı). Admin durum değişikliği talep eder; talep ikinci onaya kadar "bekliyor" görünür.
- `birimler`: kaynak, önek ve arama süzgeci (`GET /units`); ayrıntıda kanonik metin, `metin_durumu`, `content_hash`, `marks`. Düzeltme formu yalnız kendi ürettiğimiz metinde görünür; Tanzil biriminde düzeltme düğmesi yoktur.
- `yayinlar`: liste ve ayrıntı; kapı raporu tablosu (paket ve kaynak başına girdi ya da girmedi, kural kodu, gerekçe); yeni yayın talebi (derleme türü), önizleme, terfi ve geri alma (admin). 409'da süren yayın gösterilir.
- **Bitti sayılır:** üç rotanın testleri yeşil.

### A15.6 · Test ve arayüz denetimi
- Vitest ve Testing Library: oturum yönlendirmesi, role göre düğme gizleme, 412 akışı, toplu karar sınırı, Tanzil biriminde düzeltme düğmesinin yokluğu, "doğrulanmamış" rozeti, ikinci onay gösterimi.
- `arayuz-denetcisi`: etiketler, odak sırası, klavyeyle karar verme, `lang` ve `dir`, kontrast. Kullanıcı ekran görüntüsü alıp `.tmp/` altına koyarsa denetçi onu da okur.
- **Bitti sayılır:** `lint`, `typecheck`, `test`, `build` yeşil; denetçi raporunda engelleyici bulgu yok.

## Kabul ölçütleri
- [ ] Yedi rota var; `giris` dışındaki rotalar oturumsuz erişimde `giris` rotasına yönlendiriyor (test).
- [ ] `src/api/` yalnız üretilmiş tipleri ve istemciyi içeriyor; `gen:api` sonrası `git diff --exit-code apps/editor/src/api` 0.
- [ ] Karar istekleri `If-Match` taşıyor; 412'de kayıt yeniden yükleniyor (test).
- [ ] İkinci onay gereken alanlarda ilk ve ikinci onay ayrı gösteriliyor; `yz_modeli` dolu kayıtta rozet var (test).
- [ ] Tanzil biriminde düzeltme düğmesi yok (test).
- [ ] `pnpm --filter @mutalaa/editor lint`, `typecheck`, `test` ve `build` yeşil.
- [ ] Yerelde A14 API'siyle giriş yapılıyor ve yedi rota açılıyor (kullanıcıyla gözle kontrol).
- [ ] `arayuz-denetcisi` raporunda engelleyici bulgu yok.

## Doğrulama
```bash
pnpm install
pnpm --filter @mutalaa/editor gen:api && git diff --exit-code apps/editor/src/api
pnpm --filter @mutalaa/editor lint
pnpm --filter @mutalaa/editor typecheck
pnpm --filter @mutalaa/editor test
pnpm --filter @mutalaa/editor build
```
Gözle kontrol için API (`dotnet watch --project server/Mutalaa.Api`) ve panel (`pnpm dev:editor`) ayrı terminallerde açılır; panel `http://localhost:5173` adresindedir.

## Dikkat
- API tipleri elle yazılmaz; uç değişirse önce A14'te OpenAPI belgesi güncellenir, sonra `gen:api`.
- Hazır kaynak metni düzenlenemez; arayüz düzeltme düğmesini göstermez. Kanonik metin istemcide normalize edilmez.
- Kültür: `toLocaleLowerCase()` argümansız kullanılmaz; Türkçe sıralama `Intl.Collator('tr')` ile yapılır.
- Panel yalnız yerelde çalışır (`127.0.0.1`); dışarı açılmaz.
- Yapay zekâ taslakları onaylanana kadar "doğrulanmamış" rozetiyle görünür; panel taslağı onaylı gibi göstermez.
- Arayüz metni Türkçedir; kod tanımlayıcıları İngilizcedir.

## İnsan adımları
- Yok. Son gözle kontrol kullanıcıyla yapılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `apps/editor/` (`package.json`, `vite.config.ts`, `src/routes/*`, `src/api/*`, `src/components/*`, testler, `Dockerfile`)
- `pnpm-lock.yaml` güncellemesi
- Gerekirse karar defterinde OCR ve bağlantı eylemleri için açık soru notları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A15-editor-paneli.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A14](./A14-api-editor-uclari.md) · Sonraki: [A16](./A16-elmalili-meali.md)
