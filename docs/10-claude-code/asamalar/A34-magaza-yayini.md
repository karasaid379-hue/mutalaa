# A34 · Mağaza v1 yayın hazırlığı

> **Sürüm:** 1.1 · **Tarih:** 1 Kasım 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-41](../../00-ozet/02-karar-defteri.md#k-41--ses-sistemi-hazır-kayıtlar-ayna-ve-çevrimiçi-öncelikli-dinleme) · [K-42](../../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi)
> **Faz:** 3 · Mağaza v1 · **Önkoşul:** [A33](./A33-uctan-uca-test-ve-ic-dagitim.md) · **İnsan adımı:** İ-11 (meal turları) · İ-15, İ-18, İ-27
> **Ajanlar:** `arastirmaci` (A34.0 tedarik) · `mobil-gelistirici` · `sunucu-gelistirici` · `arayuz-denetcisi` · `inceleyici` · `belge-bekcisi` · **Beceriler:** `paket-yayini` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A34`

## Amaç
`public` (mağaza) derlemesini yayına hazır hâle getirmek: iç testte kalite kapısından geçen yayın `promote` ile `public` için üretilir, imzalanır ve taranır. [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §13 sürüm kontrol listesinin her maddesi kanıtıyla kapanır: `public` kuru çalıştırması 0 ile biter, public yapıt taraması yeşil, public manifest imzalı, terfide içerik özetleri iç kanalda test edilen yayınla aynı (P-14), atıflar ve Kaynaklar ekranı eksiksiz, gizlilik metni ve mağaza beyanları uygulamanın gerçek davranışıyla uyumlu, geri alma yolları yazılı. Aşama `mobile-vX.Y.Z` etiketiyle biter. Mağaza hesapları, mağaza konsollarındaki form girişi ve mağazaya gönderim (`eas submit`) kullanıcı işidir; Claude Code mağazaya hiçbir şey göndermez ve `promote` yalnız kullanıcı kararıyla çalışır.

## Okunacak belgeler
- [Yayın süreci](../../07-yayin/01-yayin-sureci.md): tamamı; özellikle §3 derleme türleri, §4 kalite kapısı kuralları ve §4.2 imza, §5 yapıt taraması, §6 Kaynaklar ekranı, §7 Yayın adımları (§7.1 adımlar, §7.2 mağaza formları, §7.3 değişiklik yönetimi, §7.4 geri alma)
- [Gizlilik](../../07-yayin/02-gizlilik.md): §2 (v1), §4 "Faz 3 öncesi" listesi, §5
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 test 6 ve 8, §7, §12, §13
- [Backend API](../../02-mimari/05-backend-api.md): §10.1 komutlar ve çıkış kodları, §10.3 kapı kontrolleri (P-01, P-07…P-14), §10.5, §10.6 terfi ve geri alma
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §6 Git kuralları ve etiketler, §7 `eas-build.yml` ve gömülü `core` denetimi
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §5 manifest ve imza, §6 sürümleme ve geri çekme
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §2.1 derleme türleri, §4 modül özellikleri ve etiketleri, §5 faz atanmamış işler, §8 başarı ölçütleri (B-07, B-12)
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 3 · [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §3 kitaplık notları ve bağımlılık listesi, §4.2 yükseltme politikası
- [Kaynaklar](../../04-icerik/01-kaynaklar.md): §1 kaynak kaydı ve atıf · [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §10, §12

## Kapsam
**Yapılır**
- Sürüm kaydı ve §13 kontrol listesinin kanıtlarla kapatılması; mağaza ve Sentry şartlarının güncel hâlinin resmî kaynaktan doğrulanması.
- İçerik dondurma, kalite kapısı kuru çalıştırması, `public` terfisi, imza ve yapıt taraması.
- Atıf denetimi, Ayarlar › Kaynaklar ekranının son hâlinin denetimi (atıf satırları ve açık kaynak bölümü), gizlilik metni, mağaza beyanları ve mağaza metninin hazırlanması.
- Sürüm numarası, `mobile-vX.Y.Z` etiketi, geri alma yollarının yazılması ve `dev` türünde provası.

**Yapılmaz**
- Maestro akışlarının, performans ve erişilebilirlik ölçümünün kurulması (A33); burada yalnız sürüm adayındaki sonuçlar kayda bağlanır.
- Ayarlar › Kaynaklar ekranının kodu (A32); burada yalnız içerikleri denetlenir.
- Hesaplı sürümün gizlilik beyanları (A35, A36).
- Mağaza konsollarında hesap işlemleri ve form girişi, `eas submit` (kullanıcı).

## Tedarik
Okuma tarihi 3 Kasım 2026; A34.0'da yenilenir. Bu aşama içerik kaynağı almaz: kaynak kaydı (`pipeline/sources/*.toml`) açılmaz, `data/gelen/` kullanılmaz. Mağaza hazırlığının araçlarını, resmî teknik şartlarını ve kitaplıklarını alır; Expo, Apple Developer, Google Play ve Sentry hesapları altyapıdır (İ-15, İ-27). Adresler `curl` ile açıldı; `support.google.com` yardım sayfaları HEAD isteğine 404 döner, GET ile ve `?hl=en` ekiyle açılır.

| Gerekli yapı | Seçilen kaynak (ad, adres, sürüm ya da commit, biçim) | Alma yolu | Eksiksizlik kanıtı | Yedek aday |
|---|---|---|---|---|
| Derleme, gönderim ve güncelleme aracı | npm `eas-cli` 27.3.0 (3 Kasım 2026 02:58 UTC; Node 20.18.3 ya da 22 ve üstü); GitHub `expo/eas-cli` etiketi `v27.3.0` = commit `bc25602d655eb5d5e3f3174836e13b567cae919d`. Belgeler: [iOS gönderimi](https://docs.expo.dev/submit/ios/), [Android gönderimi](https://docs.expo.dev/submit/android/) | `pnpm dlx eas-cli@<sürüm>`; iş akışında `expo/expo-github-action` `eas-version`. `eas submit` yalnız kullanıcı çalıştırır. Gönderim ön koşulları (hesap: altyapı, İ-15): iOS için `bundleIdentifier`, App Store Connect uygulama kaydı (`ascAppId`) ve API anahtarı (`ascApiKeyPath`, `ascApiKeyIssuerId`, `ascApiKeyId`) ya da Apple kimliği; Android için Play Console'da uygulama kaydı ve Expo hesabına yüklenen Google service account anahtarı | Komut yüzeyi eas-cli README'sinde: `eas submit`, `eas update`, `eas update:rollback`, `eas update:republish`, `eas metadata:push`, `eas metadata:pull`, `eas build:version:set`, `eas channel:rollout`. Aynı aracın öteki sabitlemeleri: A21 ve A33 notlarında 27.2.0 (commit `92e1b01bd703c124ceda5e4ebfb149257d19f6e3`), `eas-build.yml` içinde 26.0.0; A34.0 üçünü tek sürüme eşitler. İlk Android gönderimi varsayılan olarak dahili test kanalında ilk sürümü açar (`releaseStatus: draft` seçeneği vardır). Derleme numarası: `cli.appVersionSource: remote` ve `production` profilinde `autoIncrement`. Ücret: Free plan sınırlı düşük öncelikli derleme verir, Starter plan 19 ABD doları/ay (45 dolar derleme kredisi); tahmini maliyet derlemeden önce kullanıcıya gösterilir (kural 11) | Fastlane `deliver` ve `supply` (`fastlane/fastlane` etiketi `2.241.2` = commit `a540df301c4ada0621cdb50358049734712f7ee7`); mağaza konsoluna elle yükleme |
| JavaScript güncellemesi ve geri alma | `expo-updates` 58.0.20 (npm, 31 Ekim 2026; Expo SDK 58 `bundledNativeModules.json` dosyasında `~58.0.20`) ve EAS Update `production` kanalı; belgeler: [Getting started](https://docs.expo.dev/eas-update/getting-started/), [Rollbacks](https://docs.expo.dev/eas-update/rollbacks/) | `expo install expo-updates` (A21); güncelleme: `eas update --channel production --message "<ileti>" --environment <ortam>`; geri alma: `eas update:rollback` (etkileşimli; önceki güncellemeye ya da ikiliye gömülü güncellemeye döner) | İki belge sayfası 200; komutlar README'de var; JavaScript güncellemesi içerik taşımaz, gömülü `core` yalnız yeni ikiliyle değişir | Yok (içerik hatası için `rollback --flavor public`; `core` hatası için yeni uygulama sürümü) |
| Mağaza ekran görüntüsü araçları | Maestro CLI `cli-2.12.1` (`mobile-dev-inc/Maestro` etiketi = commit `67d8a677029261fa424a45a10d08eacd6aa0deed`); [takeScreenshot](https://docs.maestro.dev/api-reference/commands/takescreenshot) komutu `- takeScreenshot: <ad>` ile PNG yazar. A33 aynı aracı kurar; akış dosyasını Claude Code yazar, koşumu ve ekran görüntüsü almayı kullanıcı yapar | Yok (A33'te kurulu) | Belge sayfası 200; sürüm sayfası (`github.com/mobile-dev-inc/Maestro/releases/tag/cli-2.12.1`) 200 | Android: `adb exec-out screencap -p` (Android SDK Platform-Tools 37.0.1, Temmuz 2026; [sürüm notları](https://developer.android.com/tools/releases/platform-tools)); iOS: TestFlight derlemesinde gerçek iPhone (Windows'ta iOS simülatörü yoktur) |
| Mağaza varlık ölçüleri | Apple: [Screenshot specifications](https://developer.apple.com/help/app-store-connect/reference/app-information/screenshot-specifications/); Google Play: [Preview assets](https://support.google.com/googleplay/android-developer/answer/9866151?hl=en) | Yok (resmî sayfalar; ölçüler sürüm kaydına yazılır) | Apple: iPhone için en az bir, en çok 10 görüntü (JPEG ya da PNG, alfa kanalı yok); orta ekran sınıfı 1179 × 2556 ya da 1206 × 2622, büyük ekran sınıfı 1260 × 2736, 1290 × 2796 ya da 1320 × 2868 (dikey); arayüz boyutlar arasında tutarlıysa en yüksek gerekli çözünürlük yeterlidir ve App Store Connect küçültür; iPad 13 inç yalnız iPad desteği varsa gerekir (Expo `ios.supportsTablet` varsayılanı `false`). Google: simge 512 × 512 PNG (alfalı, en çok 1024 KB); öne çıkan görsel 1024 × 500 JPEG ya da 24-bit PNG (alfasız), zorunlu; ekran görüntüsü cihaz türü başına en çok 8, kenarlar 1.080–7.680 px, 16:9 ya da 9:16; yayın için farklı cihaz türleri arasında en az iki görüntü | Yok |
| App Privacy ve Veri güvenliği formları, gizlilik manifestosu | Apple: [App privacy details](https://developer.apple.com/app-store/app-privacy-details/), [Manage app privacy](https://developer.apple.com/help/app-store-connect/manage-app-information/manage-app-privacy/). Google Play: [Data safety](https://support.google.com/googleplay/android-developer/answer/10787469?hl=en), [Prepare your app for review](https://support.google.com/googleplay/android-developer/answer/9859455?hl=en). Expo: [Apple privacy manifests](https://docs.expo.dev/guides/apple-privacy/) (`ios.privacyManifests`) ve `ios.config.usesNonExemptEncryption` (`ITSAppUsesNonExemptEncryption`) | Çevrimiçi formlar; değer tablosunu Claude Code hazırlar, formu kullanıcı doldurur (İ-15) | Apple: "collect" veriyi cihazdan çıkarıp gerçek zamanlı isteğin gerektirdiğinden uzun erişilebilir tutmaktır; üçüncü taraf ortaklar SDK'ları da kapsar; iOS için gizlilik politikası adresi zorunludur. Google: form kapalı, açık ve üretim test kanallarındaki uygulamalar için de doldurulur; veri toplamasa da form ve politika bağlantısı gerekir; "Crash logs" ve "Diagnostics" veri türleri vardır; "service provider" geliştirici adına veri işleyen kuruluştur. Expo: Apple statik CocoaPods bağımlılıklarındaki `PrivacyInfo` dosyalarını her zaman ayrıştırmaz; eksik gerekçeler yüklemeden sonra Apple e-postasıyla bildirilir | Yok |
| Gizlilik politikası sayfası | Kendi metnimiz ([Gizlilik](../../07-yayin/02-gizlilik.md) §2.5), statik HTML | İçerik deposu ya da alan adı (İ-18; S-08) | Şartlar (3 Kasım 2026 okuması): Apple iOS için adres ister; Google: etkin, herkese açık http ya da https adresi, geçerli SSL, oturumsuz ve coğrafi kısıtsız erişim, düzenlenemez standart web sayfası (PDF değil), uygulamaya özgü; bağlantı mağaza sayfasında ve uygulama içinde bulunur. Sayfa adresi 200 döndürür (A34.5) | GitHub Pages ([belge](https://docs.github.com/en/pages)); Cloudflare Pages ([belge](https://developers.cloudflare.com/pages/)) |
| Hata raporlama kitaplığı, Expo eklentisi ve servis ayarları | npm `@sentry/react-native` `~8.28.0` (Expo SDK 58 paketi, 24 Eylül 2026; `getsentry/sentry-react-native` etiketi `8.28.0` = commit `e6f7b497f23cf35d85fda696066ba2cd9ae72206`; npm `latest` 8.33.0); Expo eklentisi `@sentry/react-native/expo`, Metro için `@sentry/react-native/metro`; [Expo kılavuzu](https://docs.sentry.io/platforms/react-native/guides/expo/). `@sentry/wizard` 9.1.0 isteğe bağlı | `expo install @sentry/react-native` (A21 kurar); kaynak eşlemesi derlemede `SENTRY_AUTH_TOKEN` ortam değişkeniyle yüklenir (İ-27) | Sentry belgeleri (200): IP adresi varsayılan olarak Sentry sunucusunca isteğin kaynağından çıkarılır; Project Settings › Security & Privacy altında IP adresi saklamayı önleme ayarı vardır ve coğrafi bilgi bu ayar açıkken de IP'den çıkarılır; `sendDefaultPii: true` olmadıkça kullanıcı bilgisi, başlık, çerez ve cihaz adı gönderilmez; `beforeSend` yalnız JavaScript katmanı olaylarını süzer, yerel (native) olaylar süzülmez; veri bölgesi ABD (Iowa) ya da AB (Frankfurt) olarak organizasyon açılırken seçilir ve sonradan değişmez (yeni organizasyon gerekir). Ayarın ekrandaki tam adı A34.0'da ölçülür | GlitchTip ([glitchtip.com](https://glitchtip.com/); Sentry istemci SDK'larıyla uyumlu olduğunu belirtir, kendi sunucumuzda çalışır) |
| Mağaza metni alanları | EAS Metadata ([belge](https://docs.expo.dev/eas/metadata/)): `store.config.json`, `eas metadata:push` ve `eas metadata:pull`; beta; yalnız App Store | `eas-cli` (ilk satır); Claude Code `store.config.json` dosyasını yazar, `eas metadata:push` ve Google Play konsol girişi kullanıcı işidir (İ-15) | Belge sayfası 200; belge, Google Play listelerinin ve ekran görüntüsü yüklemenin kapsam dışı olduğunu gösterir | Konsollara elle giriş |
| Açık kaynak bağımlılık listesi (Ayarlar › Kaynaklar) | Depodaki `scripts/ci/list-licenses.mjs` (A08) ve `pnpm licenses list` ([belge](https://pnpm.io/cli/licenses): `--prod`, `--json`, `--filter`, `--recursive`) | Yok (depoda hazır); `pnpm --filter @mutalaa/mobile licenses list --prod --json` çıktısı betiğe `pnpm` kipinde ve `--json <dosya>` ile verilir | pnpm belgesi 200; betik `pnpm` ya da `nuget` kipinde çalışır ve CI'da `ci-ts` ile `ci-dotnet` içinde koşar | Yok |
| Yayın kontrol listeleri ve platform şartları | Repo içi: [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §13 ve [Gizlilik](../../07-yayin/02-gizlilik.md) §4. Apple: [App Review Guidelines](https://developer.apple.com/app-store/review/guidelines/). Google Play: [Prepare your app for review](https://support.google.com/googleplay/android-developer/answer/9859455?hl=en) (App content: gizlilik politikası, reklam bildirimi, hedef kitle ve içerik, içerik derecelendirmesi, veri güvenliği), [Prepare and roll out a release](https://support.google.com/googleplay/android-developer/answer/9859348?hl=en), [Target API level](https://support.google.com/googleplay/android-developer/answer/11926878?hl=en), [kişisel hesap test koşulu](https://support.google.com/googleplay/android-developer/answer/14151465?hl=en) | Repo içi; resmî sayfalar | 14 + 7 madde (§13: 14; Gizlilik §4 Faz 3 öncesi: 7). 31 Ağustos 2026'dan beri yeni uygulamalar ve güncellemeler Android 16 (API 36) ya da üstünü hedefler; React Native 0.88.1 (Expo SDK 58) `targetSdk = 36`. Google Play kişisel hesabı 13 Kasım 2023'ten sonra açıldıysa üretim erişimi için kapalı test gerekir (en az 12 test kullanıcısı, kesintisiz 14 gün); kapalı test kanalı A33'teki iç dağıtımla birlikte açılır, üretim erişimi başvurusu mağaza hesabı işidir (İ-15) ve aşamanın kalanını durdurmaz. Android Developers "launch checklist" adresi 404 döner; yerine Play Console Help sayfaları kullanılır | Expo [App stores best practices](https://docs.expo.dev/distribution/app-stores/) (200) |

Kendimiz yapacağımız işler: sürüm kaydı ve kanıt tablosu, mağaza metni (Apple için `store.config.json`), gizlilik sayfası (statik HTML), Apple ve Google beyan değer tabloları (App Privacy, Veri güvenliği, yaş ve içerik derecelendirmesi cevapları, şifreleme beyanı), `ios.privacyManifests` girdileri, Maestro ekran görüntüsü akışı, `eas.json` `production` profili ve sürüm numaraları, geri alma provası.

## Adımlar
### A34.0 · Tedarik doğrulaması ve indirme
- `arastirmaci` ile `## Tedarik` tablosundaki adreslerin açıldığını ve sürümlerin güncel olduğunu doğrula: `eas-cli`, `expo-updates` ve `@sentry/react-native` npm kaydından, GitHub etiketleri `git ls-remote --tags` ile okunur; kurulu sürümler `pnpm --filter @mutalaa/mobile list expo-updates @sentry/react-native --depth 0` ile karşılaştırılır. Apple, Expo, Sentry ve pnpm sayfaları `curl -sIL` ile, Google yardım sayfaları `curl -sL "<adres>?hl=en"` ile açılır. Açılmayan adresin yerine yedek adayı kullan.
- Bu aşama dosya indirmez: kaynak kaydı (`pipeline/sources/*.toml`) açılmaz, `data/gelen/` kullanılmaz ve doldurulacak indirme formu yoktur. Araç ve kitaplık sürümleri paket kaydından doğrulanır; okuma tarihleriyle sürüm kaydına yazılır.
- `eas-cli` sürümünü üç yerde tek değere eşitle: A21'in sabitlediği sürüm, `.github/workflows/eas-build.yml` içindeki `eas-version` ve `eas.json` içindeki `cli.version` aralığı. Sürüm kayıt tarihi ve Node sürüm aralığı karşılaştırılır.
- Mağaza sayfalarının ölçülerini (ekran görüntüsü boyutları, simge ve öne çıkan görsel) ve şartlarını (gizlilik politikası adresi, hedef API düzeyi) tablodaki değerlerle karşılaştır; değişen değer sürüm kaydına yazılır ve sonraki adımlar ona göre yürür. Sentry'de IP saklamayı önleme ayarının ekrandaki tam adı bu adımda ölçülür.
- **Bitti sayılır:** tablodaki her adres açılıyor (HTTP 200); `eas-cli` sürümü A21, `eas-build.yml` ve `eas.json` içinde aynı; kitaplık sürümleri paket kaydıyla ve kurulu sürümle aynı; "A34.0'da ölçülür" yazan hücre kalmadı; okuma tarihleri sürüm kaydında.

### A34.1 · Önkoşullar, platform şartları ve sürüm kaydı
- `/durum` ile A33'ün bittiğini, sürüm adayı commit'ini ve İ-15, İ-18, İ-27 durumunu göster. A33'ün Maestro, performans, erişilebilirlik ve duman testi kanıtları bu aşamanın girdisidir.
- Sürüm kaydını aç: `docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z.md` (öneri). İçine §13 maddelerini, Gizlilik §4 "Faz 3 öncesi" listesini ve her madde için "kanıt" alanını yaz; insan gerektiren maddeye İ numarası yazılır.
- `arastirmaci` resmî kaynaktan doğrular (Gizlilik §2.2, §2.5, §2.6'daki "Doğrulanacak" maddeleri) ve değerleri bağlantı ve okuma tarihiyle sürüm kaydına yazar: mağazaların gizlilik politikası bağlantısı kuralı; App Privacy ve Veri güvenliği formlarının güncel alan adları; hata raporlama servisinin "hizmet sağlayıcı" sayılması; Sentry'de IP saklamayı kapatan ayarın adı ve servis veri bölgesi; Expo eklentisiyle sürüm ve kaynak eşlemesi yükleme yolu; EAS Update ile `production` kanalına düzeltme gönderme komutu; yerel (native) çökme olaylarının `beforeSend` dışında kalması; Android hedef API düzeyi; Apple gizlilik manifestosu (`ios.privacyManifests`) ve şifreleme beyanı (`ios.config.usesNonExemptEncryption`). Doğrulanan değerler Gizlilik dosyasına işlenir (`/belge-esitle`).
- Proje sahibi kararları kayda ve `/karar` ile deftere: hata raporu anahtarının varsayılanı (Gizlilik §5 madde 1); yayıncı adı ve iletişim adresi (mağaza hesabı açılırken belli olur, İ-15). Mağaza hesaplarının türü (kişisel ya da kurumsal) kayda yazılır.
- **Bitti sayılır:** sürüm kaydı var; her madde ya kanıt ya da İ numarası taşıyor; `arastirmaci` raporu bağlantılı ve tarihli.

### A34.2 · İçerik dondurma ve kanıt dosyaları
- **`public` yayının önkoşulu: İ-11 meal turları** (K-49 madde 12; A16, A18, A19 ve A37'yi bekletmediler, `public` yayını bekletirler). İki meal için ayrı ayrı: tur 1 tam (bütün birimler `onayli`), tur 2 en az 600 âyet ve G-INC geçti; `elmalili-meal` ve `elmalili-sade-meal` birimlerinden `onayli` olmayan kalmaz (SQL aşağıda). Birimler bu ana kadar `taslak` kalır. G-INC geçmeden `public`'e meal kaynağı çıkmaz ([K-49](../../00-ozet/02-karar-defteri.md#k-49--elmalılı-mealleri-hazır-metin-yolu-ve-ocrın-proje-sonuna-ertelenmesi) madde 5): bir meal kaynağının bütün âyetleri onaylanıp G-INC geçmedikçe `public` derleme o kaynağı dışarıda bırakır; bu kural kodda bu aşamada yazılır ve her meal kaynağı (`elmalili-meal`, `elmalili-sade-meal`) için ayrı denetlenir. A34'e kadar bu kural yoktur: `PackCatalog.cs` açıklamasındaki not gereği kısmi (kısmen onaylı) meal `public` derlemeye girebilir; yalnız onaylı birimler girer (P-10). Kapanmamışsa terfi yapılmaz: onaylı birimde sonradan yapılan her düzeltme birimi yeniden inceleme ve ikinci onaydan geçirir ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §7.3).
- Dondurma yayını: `dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal`. Yayın sürümü (`S`, CalVer) ve `release.ozetler` içindeki içerik özetleri, Tanzil dosya özeti (`source.dosya_sha256`), Elmalılı metin sürümü (`elmalili-meal` anlamsal sürümü; ilk onaylı sürüm 1.0.0), ses giriyorsa kayıt başına sure-dosya listesi (bayt, sha256, dosya sürümü) sürüm kaydına yazılır ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §7.1 madde 1–2).
- Kanıt dosyaları sürüm kaydında bağlantı ya da özetle durur: Tanzil'le bayt bayt eşitlik raporu (A10 değişmezlik testleri), test raporları (A33), kapı raporu (`release` kaydına bağlı JSON). Büyük dosyalar `data/reports/` altında tutulur (git dışı).
- Mağaza ekran görüntüleri: Maestro `takeScreenshot` akışını Claude Code yazar (`apps/mobile/e2e/magaza-ekran-goruntuleri.yaml`); akışı koşmak ve ekran görüntüsü almak kullanıcıdadır (Android emülatör ya da cihaz; iOS için TestFlight derlemesinde gerçek iPhone). Ölçüler Tedarik tablosundadır; dosyalar `data/reports/magaza/` altına konur (git dışı). Sürüm kaydında "kullanıcıya bırakıldı" diye yazılır.
- **Bitti sayılır:** `elmalili-meal` sorgusu 0 döndürüyor; dondurma yayını `internal` manifestinde; sürüm kaydında içerik özetleri, Tanzil eşitlik raporu, A33 test raporları ve kapı raporu bağlantısı var.

### A34.3 · Kalite kapısı kuru çalıştırması ve düzeltme
- `dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run`: 0 ile bitmelidir. Kapı bir yayını reddederse çıkış kodu `2` olur, manifest yayımlanmaz ve kapı raporu nedeni kural koduyla yazar ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §4; [Backend API](../../02-mimari/05-backend-api.md) §10.1, §10.3).
- Ret varsa düzeltme elle yapılmaz: içerik hattından ya da editör panelinden geçer, testler koşar, yeni içerik özeti üretilir ve A34.2'ye dönülür ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §7.1 madde 3). Düzeltmeler biriktirilip tek yayın olarak terfi edebilir.
- Kapı raporu okunur: `core` "girdi"; "girmedi" olan her paket kural koduyla birlikte sürüm kaydına yazılır. Mağaza metni (A34.5) bu listeye göre yazılır.
- **Bitti sayılır:** kuru çalıştırma 0 ile çıkıyor; kapı raporunda `core` "girdi"; "girmedi" olan paketler gerekçesiyle kayıtta.

### A34.4 · Public yayın, imza ve yapıt taraması
- Canlı depo (İ-18) ayarları A33'teki `internal` kanalıyla aynı yoldan verilir; gizli değerler yalnız kullanıcı sırlarında. Yol tanımlı değilse `/karar` ile seçilir.
- `public` imza anahtarı yoksa `keys generate --flavor public`: açık anahtar `apps/mobile/src/packs/keys.ts` içindeki `public` listesine girer; özel anahtar depoya ve CI günlüğüne girmez; `public` ve `internal` anahtarları ayrıdır. Sıradaki anahtar (öneri) ve özel anahtarın çevrimdışı yedeği kullanıcı işidir.
- Terfi: `promote --surum <S> --to public`; yalnız kullanıcı kararıyla çalışır. P-14: içerik özetleri iç kanalda test edilenle aynı olmalıdır.
- Gömülü `core`: `MANIFEST_URL=https://<içerik-alanı>/public/manifest.json pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs` imzayı ve sha256'yı doğrular.
- Yapıt taraması: `verify --flavor public --embedded-core apps/mobile/assets/db/core.db` (dosya adı BÇ-25 kararıdır) ve `verify --flavor internal`. Tarama ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §5 madde 3) her paketin `pack_meta.flavor` değerinin `public` olduğunu, her `pack_source` kaydının bir kaynak kaydına denk geldiğini ve `test-` ile başlamadığını (P-12), terfide içerik özetlerinin iç kanalda test edilenle aynı olduğunu (P-14) ve public önekte manifest dışı nesne bulunmadığını denetler.
- **Bitti sayılır:** iki `verify` 0 ile çıkıyor; gömülü `core` sha256'sı public manifestte geçiyor; manifestte fikstür paketi yok.

### A34.5 · Atıflar, Kaynaklar ekranı, gizlilik ve mağaza metni
- Atıf (B-07): public paketlerin `attribution` satırları kaynak kayıtlarındaki `atif_metni`, `atif_url` ve `notice_text` alanlarıyla karşılaştırılır ([Kaynaklar](../../04-icerik/01-kaynaklar.md) §1; [Yayın süreci](../../07-yayin/01-yayin-sureci.md) §6): Tanzil'in kendi bildirimi (bayt bayt) ve tanzil.net bağlantısı, Elmalılı künyesi, QPC yazı tipi ve mushaf düzeni atıfları, ses kaynakları (okuyucu adları, MP3Quran, Tarteel, QUD). Kaynak kartlarındaki taslak atıf metinleri bu adımda kesinleşir. Eksik ya da hatalı atıf kaynak kaydındaki `atif_metni` alanında (`pipeline/sources/<kimlik>.toml`) düzeltilir; paket sürümü artar.
- Açık kaynak bölümü: Ayarlar › Kaynaklar ekranının açık kaynak bölümü (A32) `scripts/ci/list-licenses.mjs --json` çıktısıyla beslenir ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §6; [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) §3). Sürüm adayında liste yeniden üretilir (komut Doğrulama bölümündedir) ve ekrandaki bölümle aynı olduğu görülür. Listede reklam ya da izleme SDK'sı varsa aşama durur ([Gizlilik](../../07-yayin/02-gizlilik.md) §2.3, K-25).
- Gizlilik metni [Gizlilik](../../07-yayin/02-gizlilik.md) §2.5 taslağından yazılır; yayıncı adı ve iletişim adresi mağaza hesabı açılırken belli olur (İ-15). Metindeki menü yolları uygulamadaki gerçek adlarla aynı olmalıdır; taslaktaki adlar [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md) §6 ağacından alınmıştır ("İlerleme ve gizlilik", "Verilerimi sil"); uygulamadaki adlar değişirse metin de değişir. Metin uygulamada ve alan adındaki sayfada yayımlanır (İ-18); sayfa mağaza şartlarına uyar (Tedarik): etkin ve herkese açık https adresi, oturumsuz ve coğrafi kısıtsız, düzenlenemez web sayfası (PDF değil), uygulamaya özgü.
- Davranış denetimi: `beforeSend` ayıklama testi (fikstür not metni olaydan düşer), `sendDefaultPii: false`, analitik ve izleme SDK'sı yok, App Tracking Transparency istenmiyor, "Hata raporları" anahtarı ve "Verilerimi sil" çalışıyor. `beforeSend` yalnız JavaScript olaylarını süzer; yerel (native) çökme olaylarında kullanıcı ve IP alanlarının boş olduğu Sentry panelinde bir örnek olayla görülür ve kayda yazılır (İ-27).
- Mağaza beyanları [Gizlilik](../../07-yayin/02-gizlilik.md) §2.6 tablosundan, A34.1'deki güncel alan adlarıyla kayda yazılır: Apple App Privacy (Tanılama › Çökme verisi; izleme yok), yaş derecelendirmesi, şifreleme beyanı ve `ios.privacyManifests` girdileri; Google Veri güvenliği (kilitlenme günlükleri ve tanılama), içerik derecelendirmesi, hedef kitle ve reklam bildirimi (reklam yok). Formları kullanıcı doldurur (İ-15).
- Mağaza metni `docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z-magaza-metni.md` (öneri): yalnız public manifestteki paketlerin özelliklerini anlatır. Kapsam ve fazlar §4'te `v1.x`, `Web` ve `Ek içerik` etiketli özellikler, §5'teki faz atanmamış işler ve kapı raporunda "girmedi" olan paketlerin özellikleri vaat edilmez; resmî kurum çağrışımı ve kurum logosu yoktur (R-12). `inceleyici` metni bu listeye göre okur. Apple için metin `store.config.json` olarak da yazılır (EAS Metadata, beta); gönderimi kullanıcı yapar (İ-15).
- **Bitti sayılır:** atıf karşılaştırması farksız; açık kaynak listesi yeniden üretildiğinde ekrandaki bölümle aynı ve listede reklam ya da izleme SDK'sı yok; mağaza metni incelemesi bulgusuz.

### A34.6 · Sürüm, etiket, üretim derlemesi ve geri alma
- Uygulama sürümü `app.config.ts` içinde `X.Y.Z`; `eas.json` `production` profili `MANIFEST_URL` (public manifest) ve `SENTRY_DSN` taşır (gizli değer değildir). Derleme numarası elle artırılmaz: `cli.appVersionSource` `remote` ve `production` profilinde `autoIncrement` ([Mobil mimari](../../06-mobil/01-mobil-mimari.md) §10). Mağaza yayınından önceki iki haftada SDK değişmez (öneri).
- Geri alma yolları sürüm kaydına yazılır: JS hatası → EAS Update, `production` kanalı (`eas update:rollback`; içerik taşımaz); içerik → `rollback --flavor public --to <önceki>`; `core` → yeni uygulama sürümü. Prova `dev` türünde: `rollback --flavor dev --to <önceki>` ve `verify --flavor dev`, ardından `publish --flavor dev` ile eski hâline dönülür.
- `/inceleme`, `/commit`, yerel etiket: `git tag -a mobile-vX.Y.Z -m "mobile vX.Y.Z"`. Etiketin gönderilmesi `eas-build` iş akışını tetikler; yalnız kullanıcının açık onayıyla yapılır ya da kullanıcı yapar. EAS derleme kancasında (`eas-build-post-install`) çalışan `fetch-core.mjs` imzayı ve `core` sha256'sını denetler; tutmazsa derleme durur ([Proje yapısı](../../02-mimari/03-proje-yapisi.md) §7).
- Test kanalı (TestFlight, Google Play iç test), iOS 16.4 ve düşük seviye Android duman testi, Sentry sürümü ve kaynak eşlemeleri, ikili boyutu, mağaza ekran görüntüleri: kullanıcı yapar ya da paylaşır, sonuç kayda yazılır.
- **Bitti sayılır:** etiket sürüm commit'ini gösteriyor; prova `rollback` ve `verify` 0 ile çıktı; kayıtta kanıtsız madde yalnız İ numaralı maddeler.

## Kabul ölçütleri
- [ ] Tedarik tablosundaki her adres açılıyor; `eas-cli` sürümü A21, `eas-build.yml` ve `eas.json` içinde aynı; "A34.0'da ölçülür" hücresi kalmadı.
- [ ] `publish --flavor public --dry-run` 0 ile çıkıyor; kapı raporunda `core` "girdi"; "girmedi" olan her paket gerekçesiyle sürüm kaydında (gözle).
- [ ] `verify --flavor public --embedded-core …` ve `verify --flavor internal` 0 ile çıkıyor.
- [ ] Terfide içerik özetleri iç kanalda test edilen yayınla aynı (P-14).
- [ ] `fetch-core.mjs` public manifest imzasını `keys.ts` içindeki `public` anahtarıyla doğruluyor; gömülü `core` sha256'sı public manifestte bir kez geçiyor.
- [ ] Public manifestte `test-` önekli ya da `ses-test` paketi yok.
- [ ] `elmalili-meal` ve `elmalili-sade-meal` birimlerinde `onayli` olmayan satır sayısı 0 (İ-11 tur 1) ve her iki meal için tur 2 (en az 600 âyet) ile G-INC geçti.
- [ ] `uv --directory pipeline run mutalaa sources check` 0 hata ve 0 uyarıyla bitiyor; atıf karşılaştırması farksız; `core` paketinde Tanzil'in kendi bildirimi bayt bayt var ve SHA-256'sı kilitteki `bildirim_sha256` değerine eşit (değişmezlik testi 6).
- [ ] Açık kaynak bağımlılık listesi yeniden üretildiğinde Ayarlar › Kaynaklar ekranındaki bölümle aynı; listede reklam ya da izleme SDK'sı yok.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil ve `beforeSend` ayıklama testi içinde.
- [ ] Gizlilik sayfası 200 döndürüyor; metindeki menü yolları uygulamadaki adlarla aynı (gözle).
- [ ] Mağaza metni incelemesinde ertelenmiş özellik ya da public'te olmayan paket yok (`inceleyici` raporu).
- [ ] `dev` geri alma provası 0 ile çıktı; sürüm kaydında üç geri alma yolu yazılı.
- [ ] `mobile-vX.Y.Z` etiketi sürüm commit'inde; kayıtta boş kanıt yalnız İ numaralı maddelerde.

## Doğrulama
```bash
pnpm turbo run lint typecheck test && dotnet test --solution server/Mutalaa.slnx && uv --directory pipeline run pytest
uv --directory pipeline run pytest -m degismezlik
uv --directory pipeline run mutalaa sources check; echo "çıkış: $?"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id IN ('elmalili-meal', 'elmalili-sade-meal') AND metin_durumu <> 'onayli';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run; echo "çıkış: $?"
MANIFEST_URL="https://<içerik-alanı>/public/manifest.json" pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs
dotnet run --project server/Mutalaa.Publisher -- verify --flavor public --embedded-core apps/mobile/assets/db/core.db; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor internal; echo "çıkış: $?"
curl -sS "https://<içerik-alanı>/public/manifest.json" -o .tmp/public-manifest.json
grep -c "$(sha256sum apps/mobile/assets/db/core.db | cut -d' ' -f1)" .tmp/public-manifest.json   # 1
grep -cE '"pack_id": *"(test-|ses-test)' .tmp/public-manifest.json                                       # 0
pnpm --filter @mutalaa/mobile licenses list --prod --json | node scripts/ci/list-licenses.mjs pnpm --json .tmp/acik-kaynak.json
grep -i -E "analytics|amplitude|mixpanel|segment|appsflyer|adjust|admob|mobile-ads|onesignal|posthog" .tmp/acik-kaynak.json   # boş (eşleşen paket tek tek okunur)
pnpm --filter @mutalaa/mobile test && grep -rl --include="*.test.*" "beforeSend" apps/mobile
curl -sSf -o /dev/null "https://<alan-adı>/<gizlilik-sayfası>" && echo "gizlilik sayfası açık"
grep -n "eas-version" .github/workflows/eas-build.yml
pnpm --filter @mutalaa/mobile list expo-updates @sentry/react-native --depth 0
dotnet run --project server/Mutalaa.Publisher -- rollback --flavor dev --to "<önceki-sürüm>"; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
git rev-parse "mobile-vX.Y.Z^{commit}" HEAD
grep -n -- "- \[ \]" docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z.md | grep -v "İ-"                       # boş
```
Gömülü `core` dosyasının adı A23'teki BÇ-25 kararıdır (öneri `core.db`); karar başka ad seçtiyse komutlar ona göre yazılır. `-U` ve `-d` değerleri `.env.example` varsayılanlarıdır. Kullanıcı PowerShell'de çalıştırırsa: `$env:MANIFEST_URL = "https://<içerik-alanı>/public/manifest.json"` ve `curl.exe`.

## Dikkat
- `eas submit` hiç çalıştırılmaz; etiket gönderimi ve EAS derlemesi (ücretli iş) kullanıcının açık onayını ister (CLAUDE.md kural 11); tahmini maliyet derlemeden önce söylenir.
- `public` yalnız onaylı birim alır; `test-` kaynak hiçbir durumda girmez. Ayrıntı: `paket-yayini` becerisi (Derleme görünürlüğü, Kalite kapısı kuralları).
- Terfiden sonra içerikte tek bayt değişirse içerik özeti değişir ve P-14 terfiyi durdurur; düzeltmeler hattan geçer ve yeni sürümde toplanır.
- EAS Update içerik taşımaz; gömülü `core` yalnız yeni ikiliyle değişir.
- Özel imza anahtarı yalnız kullanıcı sırlarında durur; Claude Code `.env` dosyalarını okumaz.
- `public` derleme bütün ülkelerde ve vitrinlerde aynı kapıdan geçer; ülkeye göre ayrı paket ya da manifest yoktur ([Yayın süreci](../../07-yayin/01-yayin-sureci.md) §7.1).
- Sentry `beforeSend` yalnız JavaScript olaylarını süzer; yerel olaylar için A34.5 denetimi geçerlidir.
- Maestro akışını koşmak ve ekran görüntüsü almak kullanıcıdadır ([çalışma düzeni](../../../CLAUDE.md)); ilerleme notunda ve kapanış raporunda "kullanıcıya bırakıldı" yazılır.

## İnsan adımları
- İ-11 · Elmalılı meal turları (iki meal için ayrı ayrı: tur 1 tam, tur 2 en az 600 âyet, G-INC): `public` yayının önkoşuludur (A34.2); `public` dışındaki işleri bekletmez.
- İ-15 · Expo, Apple Developer ve Google Play hesapları: mağaza adı kontrolü (S-08), beyan formları, test kanalı (kişisel Google Play hesabında kapalı test kullanıcıları dahil), `eas submit` ve yayına alma; A34.6'da.
- İ-18 · Canlı içerik deposu ve alan adı: A34.4 ve gizlilik sayfasından önce.
- İ-27 · Sentry projesi ve DSN; proje ayarında IP saklamanın kapatılması ve kaynak eşlemesi yükleme sırrı (`SENTRY_AUTH_TOKEN`).
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z.md` ve `mobile-vX.Y.Z-magaza-metni.md` (öneri); araç sürümleri ve okuma tarihleri sürüm kaydında
- `release` tablosunda `internal` ve `public` yayınları; canlı depoda public manifest, imzası ve paketler
- `apps/mobile/src/packs/keys.ts` (`public` açık anahtarı), `apps/mobile/eas.json`, `app.config.ts` sürümü ve `ios.privacyManifests`, `apps/mobile/e2e/magaza-ekran-goruntuleri.yaml`
- Gizlilik metni (uygulama içi ve alan adında), beyan değer tabloları, Apple için `store.config.json`; karar defteri girdileri; git etiketi `mobile-vX.Y.Z`

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A34-magaza-yayini.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A33](./A33-uctan-uca-test-ve-ic-dagitim.md) · Sonraki: [A35](./A35-hesap-ve-gizlilik.md)
