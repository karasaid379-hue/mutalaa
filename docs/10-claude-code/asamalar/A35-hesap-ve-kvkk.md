# A35 · Hesap (Identity, Google + Apple ile giriş) ve KVKK

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç) · [K-20](../../00-ozet/02-karar-defteri.md#k-20--barındırma) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 4 · v1.x · **Önkoşul:** [A34](./A34-magaza-yayini.md) · **İnsan adımı:** İ-03 (avukat: hesaplar için KVKK) · İ-20 (barındırma seçimi)
> **Ajanlar:** `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `ef-goc` · `mobil-ekran` · **Tahmini oturum:** 4–6
> **Başlat:** `/asama A35`

## Amaç
Okur için isteğe bağlı hesap kurulur: ASP.NET Core Identity ile e-posta ve parola, Google ile giriş ve onunla birlikte Apple ile Giriş, uygulama içinden hesap silme ve veri dökümü. KVKK yükümlülüklerinin kod tarafı (en az veri, aydınlatma metni, günlük kuralları, silme akışı) ve belge tarafı (veri işleyenler, saklama süreleri, VERBİS değerlendirmesi) hazırlanır; uygulama hesapsız tam çalışmayı sürdürür. Aşama yerelde ve `dev` derlemesinde biter. Canlıya açılış barındırma seçimine (İ-20) ve avukat incelemesine (İ-03) bağlıdır ve senkronla birlikte A36'nın son adımında, bu aşamanın hazırladığı listeyle yapılır.

## Okunacak belgeler
- [Backend API](../../02-mimari/05-backend-api.md): §1 çalışma kipleri, §3 `Program.cs`, §5 v1.x uçları, §6 kimlik ve hata modeli, §7 EF Core, §8 günlük, §9 kültür
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §3 tamamı, §4 "Faz 4 öncesi" listesi, §5 açık sorular
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): §2 ortak sütunlar ve `device_id`, §6 yedek biçimi, §8 "Gizlilik" maddesi
- [Genel mimari](../../02-mimari/01-genel-mimari.md): §6.3, §7 ortamlar, §10, §11 soru 3
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §10 bayraklar, §12 Sentry · [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §2 rota ağacı, §6 ayarlar
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §7 `xref_vote` · [Riskler](../../08-yol-haritasi/03-riskler.md): R-13

## Kapsam
**Yapılır**
- Genel kipte (`Mutalaa:Features:Public=true`) Backend API §5'teki hesap uçları: kayıt, giriş, yenileme, çıkış, Google ve Apple ile giriş, hesap silme, veri dökümü.
- Okur kimlik verisinin editoryal veritabanından ayrı tutulması kararı ve şeması.
- Mobilde Hesabım ekranı, giriş akışları, aydınlatma metni, "Hesabımı sil"; `hesapVeSenkron` bayrağı yalnız `dev`.
- KVKK belgeleri, mağaza beyanı taslakları ve canlıya açılış listesi.

**Yapılmaz**
- Senkron uçları, `kullanici` şemasındaki senkron tabloları ve istemci senkronu (A36). Canlıya açılış (A36 son adımı).
- Bağlantı oyu (`PUT`, `DELETE /api/v1/xrefs/{id}/vote`): [A36](./A36-senkron.md) A36.6. Silme akışı oy tablosu varsa oyları da kapsar.
- Web'de hesap (A38'in dışında; Faz 5'te istenirse ayrı plan). Uçtan uca şifreli notlar (ertelenmiş seçenek, KVKK §3.5).

## Adımlar
### A35.1 · Doğrulamalar ve kararlar
- `arastirmaci` resmî kaynaktan, tarihli ve bağlantılı raporlar:
  - App Store yönergesinin Apple ile Giriş hakkındaki güncel metni (Backend API §5 "Doğrulanacak": Google ile giriş sunulursa Apple ile Giriş de sunulur) ve Android'de Apple ile Giriş'in gerekip gerekmediği.
  - App Store ve Google Play'in uygulama içi hesap silme kuralı ve Google Play'deki silme bağlantısı şartı (KVKK §3.6 "Doğrulanacak").
  - Google ve Apple `id_token` doğrulamasının resmî yolu (imza anahtarları, `aud`, `nonce`) ve .NET'teki karşılığı.
  - Expo için Apple ile giriş ve Google ile giriş modülleri, cihazda belirteç için güvenli depo modülü ve SDK uyumu. Sürümler kurulum günü kilit dosyasına yazılır; Expo'ya bağlı paketler `npx expo install` ile kurulur.
- `/karar` ile (proje sahibi onaylar): okur kimliği ve kullanıcı verisi için ayrı veritabanı (öneri; Genel mimari §11 soru 3) ve Identity tablolarının `kimlik` şemasında durması (öneri; Backend API §7); erişim ve yenileme belirteci süreleri (öneri); silme bekleme süresi ve güvenlik günlüğü saklama süresi (KVKK §5 soru 5; avukat görüşüyle); e-posta gönderim sağlayıcısı.
- **Bitti sayılır:** rapor ve kararlar kayıtlı; açık kalan her soru İ-03 ya da İ-20'ye bağlanmış.

### A35.2 · Sunucu: Identity ve hesap uçları
- `sunucu-gelistirici` + `ef-goc`: okur kullanıcı tipi (öneri ad `ReaderUser`; editörün `EditorUser` tipiyle karışmaz), A35.1 kararındaki `DbContext` ve göçleri; her değişiklik en çok bir göç.
- Uçlar Backend API §5'teki gibi: e-posta ve parolayla taşıyıcı ve yenileme belirteci; `external/google` ve `external/apple` gövdesi `{id_token, nonce}`, sunucu imzayı, `aud` ve `nonce` değerini doğrular. Hatalar RFC 9457 ProblemDetails ve §6 kodlarıyla (`dogrulama`, `oturum-acilamadi`, `yetki-yok`).
- Genel kipte editör uçları hiç eşlenmez; `AddRateLimiter` hesap ve IP başına; günlüğe parola, belirteç, çerez, not içeriği ve e-posta yazılmaz (Backend API §8).
- Toplanan veri yalnız KVKK §3.2 tablosundaki kadardır: e-posta ya da Apple/Google giriş kimliği, Identity parola özeti, güvenlik günlüğü (IP, zaman, olay). Ad, telefon, doğum tarihi istenmez.
- Testler (`WebApplicationFactory`, Testcontainers `postgres:18`): kayıt, giriş, yenileme, çıkış; yanlış imza, yanlış `aud`, yanlış `nonce` için 401; hız sınırında 429; genel kipte editör uçları 404; giriş sırasında yakalanan günlükte e-posta ve parola geçmiyor. Dış sağlayıcı testleri test anahtarıyla, ağsız çalışır.
- OpenAPI belgesi yeniden üretilir.
- **Bitti sayılır:** `dotnet test` yeşil, yukarıdaki testler raporda adıyla; `git diff --exit-code server/Mutalaa.Api/openapi` temiz.

### A35.3 · Hesap silme ve veri dökümü
- `DELETE /api/v1/account` kimliğin yeniden doğrulanmasını ister, hesabı silme işaretiyle kapatır, oturumları ve yenileme belirteçlerini düşürür; bekleme süresi yapılandırmadan okunur (A35.1). Süre dolunca kalıcı silme işi kullanıcının bütün satırlarını, yumuşak silinmiş satırları, değişiklik akışı kayıtlarını, oturumları ve varsa `xref_vote` oylarını (`account_hash` ile) siler; kullanıcıya onay e-postası gider ([KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md) §3.6).
- Silme testi şemadaki tabloları `information_schema.tables` ile listeler ve her tabloda kullanıcı satırı kalmadığını doğrular; A36'nın ekleyeceği tablolar böylece kendiliğinden kapsanır.
- `GET /api/v1/account/export` v1 yedek biçimini (`"format": "mutalaa-yedek"`, [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md) §6) sunucudaki hesap kayıtlarıyla döndürür; A36 senkron tablolarını aynı döküme ekler.
- **Bitti sayılır:** silme ve döküm testleri yeşil; döküm dosyası v1 içe aktarma koduyla açılıyor.

### A35.4 · Mobil: Hesabım, giriş, aydınlatma metni, silme
- `mobil-gelistirici` + `mobil-ekran`: `app/(tabs)/ayarlar/hesap.tsx` (öneri; Mobil ekranlar §2 ve §6'ya `/belge-esitle` ile eklenir): durum, giriş yöntemleri, "Verilerimi dışa aktar", "Hesabımı sil".
- Hesap açma akışı aydınlatma metnini hesap oluşmadan önce gösterir; Google ile giriş varsa Apple ile Giriş de vardır (A35.1 platform kuralıyla). Hesap hiçbir akışta zorunlu değildir; tanıtımdaki "Hesap gerekmez" sözü geçerli kalır.
- Belirteçler A35.1'de seçilen güvenli depoda durur; MMKV'ye, günlüğe ve Sentry olaylarına girmez.
- `src/lib/flags.ts`: `hesapVeSenkron` yalnız `dev` için açılır; `internal` ve `public` canlıya açılışa kadar kapalı.
- Görsel denetim: geliştirme derlemesi (`(cd apps/mobile && eas build --profile development --platform android --non-interactive --no-wait)`, kullanıcı onayıyla; izleme A21.7'deki gibi), `adb exec-out screencap -p > .tmp/hesap.png`; Kâğıt, Âhar, Gece ve %200 yazı boyutu; `arayuz-denetcisi` inceler.
- E2E: yerel API'ye karşı e-posta ve parolayla hesap aç, dışa aktar, hesabı sil (Maestro). Google ve Apple ile giriş test hesaplarıyla elle denenir.
- **Bitti sayılır:** mobil testler ve Maestro akışı yeşil; ekran görüntüleri incelendi.

### A35.5 · KVKK belgeleri ve canlıya açılış listesi
- Aydınlatma metni KVKK §3.8 iskeletinin yedi başlığıyla `docs/07-yayin/aydinlatma-metni.md` (öneri) dosyasına yazılır; uygulama içi metin i18n anahtarlarına, yayın sayfası alan adına (İ-18) bu dosyadan aktarılır.
- Veri işleyenler listesi (KVKK §3.4 tablosu) seçilen sağlayıcılarla güncellenir; her yurt dışı işleyen için standart sözleşme ve 5 gün içinde Kurum'a bildirim takvimi yazılır (insan; hukuki görüş değildir).
- Avukata giden sorular `/yazisma avukat` ile taslaklanır: özel nitelikli veri (§3.5), VERBİS, saklama süreleri, Apple ve Google'ın rolü, hukuki sebepler (§3.3). Cevaplar `/karar` ve `/belge-esitle` ile işlenir.
- Mağaza beyanlarının hesap verisiyle güncel hâli kayda yazılır; formları insan doldurur (İ-15).
- Canlıya açılış listesi (A36.7'de kullanılır): barındırma kararı (İ-20), yalnız HTTPS, göç paketi (`dotnet ef migrations bundle`), canlıda `Mutalaa:Features:Public=true` ve `Editor=false`, sırların barındırma sırlarında olması, `/health/ready`, bayrakların açılma sırası (`internal`, sonra yeni uygulama sürümüyle `public`; A34 yordamı).
- KVKK §4 "Faz 4 öncesi" listesi ve canlıya açılış listesi `docs/07-yayin/surum-kayitlari/v1x-kvkk.md` (öneri) dosyasında, her madde için kanıt alanıyla tutulur.
- **Bitti sayılır:** listedeki her madde kanıt ya da İ numarası taşıyor.

## Kabul ölçütleri
- [ ] `dotnet test --solution server/Mutalaa.slnx` yeşil; hesap testleri (giriş, yenileme, çıkış, dış sağlayıcı ret durumları, 429, genel kipte editör uçları 404, günlükte e-posta ve parola yok) raporda adıyla.
- [ ] Silme testi `information_schema` ile listelenen her tabloda kullanıcı satırının 0 olduğunu doğruluyor.
- [ ] `git diff --exit-code server/Mutalaa.Api/openapi` temiz.
- [ ] Döküm dosyası `"format": "mutalaa-yedek"` taşıyor ve v1 içe aktarma testinde açılıyor.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; bayrak testi `hesapVeSenkron` değerini `internal` ve `public` için `false` buluyor.
- [ ] Maestro hesap akışı yeşil; ekran görüntüleri `.tmp/` altında, `arayuz-denetcisi` bulguları kapalı.
- [ ] Aydınlatma metni KVKK §3.8'in yedi başlığını aynı sırayla taşıyor (`grep -n "^## "` çıktısıyla gözle).
- [ ] `arastirmaci` raporu Apple ile Giriş ve hesap silme kurallarını tarih ve bağlantıyla veriyor.
- [ ] KVKK §4 "Faz 4 öncesi" listesinde kanıtsız madde yalnız İ numaralı.

## Doğrulama
```bash
dotnet test --solution server/Mutalaa.slnx
dotnet ef migrations script --idempotent --project server/Mutalaa.Infrastructure --startup-project server/Mutalaa.Api > .tmp/goc.sql
git diff --exit-code server/Mutalaa.Api/openapi
pnpm turbo run lint typecheck && pnpm --filter @mutalaa/mobile test
adb exec-out screencap -p > .tmp/hesap.png
maestro test apps/mobile/e2e/hesap.yaml          # akış klasörü A33'teki konumdur
grep -n "^## " docs/07-yayin/aydinlatma-metni.md
grep -n -- "- \[ \]" docs/07-yayin/surum-kayitlari/v1x-kvkk.md | grep -v "İ-"   # boş
```
Çözümde birden çok `DbContext` varsa göç komutlarında bağlam seçimi `ef-goc` becerisindeki biçimle yapılır. `eas build` kullanıcı onayı ister.

## Dikkat
- Hesap isteğe bağlıdır (K-15); hesapsız okuma hiçbir ekranda engellenmez.
- Editör kimliği (çerez, yalnız `127.0.0.1`) ile okur kimliği (taşıyıcı belirteç, canlı sunucu) karışmaz; genel kipte editör uçları eşlenmez.
- `device_id` rastgele üretilir, donanım kimliği kullanılmaz (KVKK §3.2, öneri). Reklam kimliği, konum, kişiler toplanmaz.
- Kültürden bağımsızlık: e-posta ve kimlik karşılaştırmaları ordinal; testler `tr-TR` kültüründe de koşar (Backend API §9).
- Gizli değerler (bağlantı dizesi, istemci gizlileri, imza anahtarları) yalnız kullanıcı sırlarında; Claude Code `.env` okumaz.
- KVKK notları hukuki görüş değildir; avukat incelemesi olmadan canlıya çıkılmaz. Testcontainers Docker Desktop ister (İ-01).

## İnsan adımları
- İ-20 · Barındırma seçimi: KVKK §3.7 ölçütleriyle; canlıya açılıştan (A36.7) önce.
- İ-03 · Avukat incelemesi (hesaplar için KVKK, özel nitelikli veri, VERBİS, saklama süreleri): A35.5'te sorular hazırlanır; canlıya açılıştan önce cevap gerekir.
- İ-15 · Apple Developer ve Google hesaplarında giriş istemcilerinin oluşturulması ve mağaza beyanlarının güncellenmesi: A35.4 ve A35.5.
- Google ve Apple ile girişin gerçek test hesaplarıyla elle denenmesi: A35.4.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `server/Mutalaa.Infrastructure/Identity/` (okur kimliği), yeni `DbContext` ve göçleri; `server/Mutalaa.Api/Endpoints/` hesap uçları; `openapi/v1.json`; `server/tests/` hesap testleri
- `apps/mobile/app/(tabs)/ayarlar/hesap.tsx`, `apps/mobile/src/features/settings/` hesap bileşenleri, `src/lib/flags.ts`, Maestro akışı
- `docs/07-yayin/aydinlatma-metni.md` ve `docs/07-yayin/surum-kayitlari/v1x-kvkk.md` (öneri), `docs/yazismalar/` avukat taslağı, karar defteri girdileri
- `docs/07-yayin/02-kvkk-ve-gizlilik.md` ve `docs/01-urun/03-mobil-ekranlar.md` güncellemeleri (`/belge-esitle`)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A35-hesap-ve-kvkk.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A34](./A34-magaza-yayini.md) · Sonraki: [A36](./A36-senkron.md)
