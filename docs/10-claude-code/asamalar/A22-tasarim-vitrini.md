# A22 · Tasarım vitrini ve `ui-tokens`

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-24](../../00-ozet/02-karar-defteri.md#k-24--tasarım-dili) · [K-29](../../00-ozet/02-karar-defteri.md#k-29--mobil-arayüz-kitaplıkları) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-14](../../00-ozet/02-karar-defteri.md#k-14--web)
> **Faz:** 2 · Mobil v1 (iç test) · **Önkoşul:** [A21](./A21-mobil-iskelet.md) · **İnsan adımı:** İ-22 (durdurmaz; onay gelene kadar belgedeki değerler)
> **Ajanlar:** `mobil-gelistirici` · `arayuz-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `mobil-ekran` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A22`

## Amaç
"Sade Osmanlı" tasarım dilinin jetonları tek JSON kaynakta toplanır ve hem mobil (NativeWind v4) hem web ve editör (Tailwind v4) için derlenir. Kontrast eşiğinin altında kalan her jeton çifti derlemeyi durdurur. Ekranlar yazılmadan önce, yalnız geliştirici derlemelerinde görünen Tasarım vitrini kurulur; görsel kararlar üç tema ve üç yazı boyutunda gözden geçirilir.

## Okunacak belgeler
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): tamamı
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §11 Erişilebilirlik kontrolleri, §12 CI düzeni
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §10 (`tasarimVitrini`), §13 Erişilebilirlik uygulaması
- [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §3.2 (Tasarım vitrini satırı), §6 yazı boyutu kademeleri
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §2 bağımlılık kuralları, §4.1 Turborepo görevleri

## Kapsam
**Yapılır**
- `packages/ui-tokens`: `tokens.json`, `schema.json`, `build.ts`, kontrast testi ve `dist/` çıktıları.
- A21'deki tema sağlayıcısının ve React Native Reusables tema değişkenlerinin bu jetonlara bağlanması.
- Yazı rolleri ve kademeleri, hareket jetonları ve Hareketi Azalt bağı.
- Simge takımı kararı (TS-3) ve onaltılık renk ESLint kuralı (öneri).
- Tasarım vitrini rotası, ilk bölümleri ve üç tema × üç boyut ekran görüntüleri.

**Yapılmaz**
- Okuyucu parçalarının kendisi: `PageView` ve `AyahMarker` (A24), `WordCard`, `LinkResult`, `ChipSlot` (A25), `MiniPlayer` ve `PlayerSheet` (A27). Her aşama kendi bileşenini vitrine ekler.
- Ayarlar › Görünüm ekranı (A32). Editörün ve webin `tailwind.css`'e geçişi `web-gelistirici`nin ayrı işidir. Tecvid renkleri (v1.x).

## Adımlar
### A22.1 · Doğrulamalar ve kararlar (`arastirmaci`)
- A21'de seçilen SDK `apps/mobile/package.json`'dan okunur. Şunlar resmî belgeden doğrulanır ve sonuç `/belge-esitle` ile işlenir:
  - NativeWind v4 ön ayarında CSS değişkenli renk tanımı ve `vars()` ile tema geçişi (TS-8); React Native Reusables'ın beklediği tema değişkeni adları.
  - Tailwind v4 `@theme` sözdizimi ve `[data-theme="gece"]` değişken blokları (editör Tailwind v4.3 kullanır).
  - Simge takımı: Expo SDK 56'dan beri `@react-native-vector-icons/*` paketleri; React Native Reusables'ın kullandığı takım ve lisansı (TS-3). Seçim `/karar` ile yazılır.
  - IBM Plex Sans'ın lisans dosyası ve Türkçe kapsamı (â, î, û, ğ, ş, İ, ı); Apple'ın varsayılan Dynamic Type tablosu (Tasarım sistemi §3.2).
- TS-1 (IBM Plex Sans ya da Inter) ve TS-4 (öneri jetonların onayı) proje sahibine sorulur; cevap gelene kadar dokümandaki değerler kullanılır.
- **Bitti sayılır:** maddelerin sonucu dokümanda; simge takımı kararı karar defterinde.

### A22.2 · `packages/ui-tokens`
- Klasör düzeni Tasarım sistemi §10'daki gibidir. `tokens.json` değerleri dokümandan aynen taşır:
  - §2.1 temel jetonlar; §2.2 ek rol jetonları (öneri, TS-4); §2.3 beş vurgu rengi (zemin ve işaret); §2.4 bölüm vurgusu; `sus` için `yalnizSus: true`.
  - §3.2 yazı rolleri ve kademe dizileri (`turkce`, `arapca`, varsayılan 5); §4 boşluk ve köşe; §5 hareket.
  - `kontrast` listesi: metin ↔ yüzey 4,5; `cizgi-guclu` ↔ yüzey 3,0; metin ↔ `vurgu.*.zemin` 4,5. Bütün metin jetonları sınandığı için (§2.5, §9) öteki metin rolleri de listeye girer.
- `schema.json` biçimi derlemede doğrular (doğrulayıcı kitaplık öneri olarak seçilir). `build.ts` dört dosya üretir: `dist/tokens.ts`, `dist/nativewind-preset.js`, `dist/tailwind.css`, `dist/kontrast.md`.
- Paket `react-native`, `expo-*` ve DOM API'si kullanmaz. Betikler: `build`, `test` (Vitest), `typecheck`. Turborepo `build` çıktısı `dist/**`.
- **Bitti sayılır:** `pnpm --filter @mutalaa/ui-tokens build` dört dosyayı üretir.

### A22.3 · Kontrast testi
- `test/contrast.test.ts` WCAG göreli parlaklık formülüyle hesaplar. `kontrast` listesindeki her çift üç temada sınanır; joker (`vurgu.*.zemin`) bütün vurgulara açılır.
- Hesaplanan oranlar Test stratejisi §11 tablosuyla ve Tasarım sistemi §2'deki değerlerle bir ondalık hassasiyetle aynıdır (ör. metin Kâğıt 16,3, çini mavisi Âhar 6,8, altın süs Kâğıt 2,96).
- `yalnizSus` jetonu hiçbir metin rolünde kullanılamaz; kullanılırsa test kırılır.
- Eşik altı çift derlemeyi durdurur: bozuk bir bellek içi jeton kümesiyle `build` işlevinin hata verdiği ayrıca sınanır. Sonuç tablosu `kontrast.md`'ye yazılır.
- **Bitti sayılır:** `pnpm --filter @mutalaa/ui-tokens test` yeşil; kırılma testi geçer.

### A22.4 · Mobil bağlama
- `apps/mobile` pakete `workspace:*` ile bağlanır. NativeWind yapılandırması ön ayarı kullanır; A21'in tema sağlayıcısı etkin temanın değişkenlerini `vars()` ile uygular. Sınıflar `bg-yuzey text-metin` biçimindedir. React Native Reusables'ın tema değişkenleri aynı jetonlara eşlenir; kitaplığın kendi renk değerleri kullanılmaz.
- `useThemeTokens()` ham renk isteyen yerler (SVG, Reanimated, alt sayfa) için `dist/tokens.ts`'den okur.
- Yazı: okuma rolleri kademe × sistem ölçeğiyle, arayüz rolleri sistem ölçeğiyle `maxFontSizeMultiplier` sınırına kadar büyür (sınır değeri öneri olarak yazılır). Okuma metni en az %200'e çıkar; Arapça ve Türkçe ölçek ayrıdır (`arabicScale`, `turkishScale`).
- Hareket: Hareketi Azalt açıkken süreler `anlik` olur (`AccessibilityInfo.isReduceMotionEnabled`).
- ESLint kuralı `#` ile başlayan renk dizgesini `packages/ui-tokens` dışında yakalar (öneri, Tasarım sistemi §10).
- Simge takımı A22.1 kararıyla kurulur; sekme simgeleri yazılı etiketle birlikte görünür. Yalnız simgeden oluşan düğme erişilebilirlik etiketi taşır.
- **Bitti sayılır:** tema testi üç temada `yuzey` ve `metin` değişkenlerinin jetonlardaki değerleri aldığını gösterir; `apps/mobile` içinde onaltılık renk yok; mobil `lint`, `typecheck` ve `test` yeşil.

### A22.5 · Tasarım vitrini
- Rota `app/(tabs)/ayarlar/gelistirici/vitrin.tsx`; içerik `src/features/settings/vitrin/`. `tasarimVitrini` `dev` ve `internal`'da açık, `public`'te kapalıdır; orada rota Ayarlar'a yönlenir.
- Denetimler: tema, yazı boyutu (varsayılan, kademe 8, %200), Hareketi Azalt, sayfa çevirme yönü, dokunma alanlarını gösteren katman. Ekran görüntüsünü betikle almak için aynı değerler sorgu parametresiyle de verilir: `?tema=gece&boyut=8` (öneri).
- Bölümler (Tasarım sistemi §11):
  - Renkler: değer ve çalışma anında hesaplanan kontrast; eşik altı çift `isaret` çerçevesiyle. Hesap `ui-tokens`'taki aynı işlevle yapılır.
  - Tipografi: bütün roller. Türkçe örnek açıkça sentetiktir ("Deneme paragrafı 1 · âlem, îman, ûlâ, İı, ğş"). Arapça rollerin örneği (Fâtiha'nın ilk âyeti) ve meal örneği yalnız `core` paketinden okunur; o bağlantı A24'te kurulur, o zamana kadar alan "Örnek metin `core` bağlanınca görünür" der.
  - Okuyucu parçaları: yer tutucu liste; A24, A25 ve A27 kendi bileşenlerini buraya ekler.
  - Genel bileşenler: React Native Reusables'tan düğme, iletişim kutusu, sekmeler, geçiş grubu, seçim kutusu, anahtar, ilerleme, açılır pencere; `EmptyState`, `Skeleton`, `Snackbar`.
  - Motifler ve rozetler: `TezhipFrame`, `SectionDivider` (`currentColor`), `UnverifiedBadge` ("doğrulanmamış"), `LicenseBadge`.
- **Bitti sayılır:** vitrin `dev` derlemede açılır; `public` yönlendirme testi yeşil.

### A22.6 · Görsel denetim
- Geliştirme derlemesi emülatörde açılır. Yeni yerel modül eklendiyse (ör. simge takımı) önce kullanıcının onayıyla yeni EAS geliştirme derlemesi alınır.
- `mobil-ekran` yöntemiyle 9 görüntü alınır: Kâğıt, Âhar, Gece × varsayılan, kademe 8, %200 → `.tmp/vitrin/<tema>-<boyut>.png`.
- `arayuz-denetcisi` görüntüleri Tasarım sistemi §9 kontrol listesiyle okur: kontrast listesinde eşik altı çift yok, %200'de kesilen metin yok, dokunma katmanında 44×44 pt altında hedef yok, Türkçe harfler doğru, renk tek başına anlam taşımıyor.
- Referans görüntülerin saklanacağı yer öneridir (`apps/mobile/test/vitrin-referans/`); her jeton ya da bileşen değişikliğinde yeniden alınır.
- **Bitti sayılır:** 9 görüntü ve `arayuz-denetcisi` raporu; engelleyici bulgu yok.

## Kabul ölçütleri
- [ ] `pnpm --filter @mutalaa/ui-tokens build` `dist/tokens.ts`, `dist/nativewind-preset.js`, `dist/tailwind.css` ve `dist/kontrast.md` üretir.
- [ ] `pnpm --filter @mutalaa/ui-tokens test` yeşil: her çift eşikte; oranlar Test stratejisi §11 ile aynı; bozuk küme derlemeyi durdurur; `sus` metin rolünde yok.
- [ ] `kontrast.md` üç temanın bütün çiftlerini oranlarıyla listeler (gözle kontrol).
- [ ] `apps/mobile/src` ve `apps/mobile/app` içinde onaltılık renk dizgesi yok; ESLint renk kuralı örnek ihlali yakalar (test).
- [ ] `pnpm --filter @mutalaa/mobile lint`, `typecheck` ve `test` yeşil; vitrin `public` bayrağıyla Ayarlar'a yönlenir (test).
- [ ] Kontrast testi CI'daki `turbo run test` içinde koşar (`ci-ts.yml`; Test stratejisi §12).
- [ ] Simge takımı kararı ve TS-8 sonucu karar defterinde ya da dokümanda.
- [ ] 9 ekran görüntüsü `.tmp/vitrin/` altında; `arayuz-denetcisi` raporunda engelleyici bulgu yok.

## Doğrulama
```bash
pnpm --filter @mutalaa/ui-tokens build
ls packages/ui-tokens/dist
pnpm --filter @mutalaa/ui-tokens test
pnpm --filter @mutalaa/ui-tokens typecheck
grep -rnE "['\"]#[0-9A-Fa-f]{3,8}['\"]" apps/mobile/src apps/mobile/app || echo "onaltılık renk yok"
pnpm --filter @mutalaa/mobile lint && pnpm --filter @mutalaa/mobile typecheck && pnpm --filter @mutalaa/mobile test
mkdir -p .tmp/vitrin
adb shell "am start -W -a android.intent.action.VIEW -d 'mutalaa-dev://ayarlar/gelistirici/vitrin?tema=gece&boyut=8'"
adb exec-out screencap -p > .tmp/vitrin/gece-8.png
```
Son iki komut dokuz tema ve boyut birleşimi için tekrarlanır. `adb shell` içinde `&` tırnak içinde kalmalıdır.

## Dikkat
- Değerler dokümandan aynen alınır; yeni değer "öneri" diye işaretlenir. Jeton değişikliği paket sürümünü artırır ve vitrin görüntüleri yeniden alınır.
- `sus` açık temalarda metin olarak kullanılmaz (2,96:1 ve 3,33:1). Altın yalnız süs çizgisidir.
- Renk tek başına anlam taşımaz: vurgu zemin, alt çizgi ve simgeyle; güven etiketi yazıyla.
- İçerik etiği: vitrinde Risale metni yer almaz; Kur'an ve meal örneği elle yazılmaz, yalnız `core`'dan okunur. Sentetik Türkçe örnek "Deneme" diye başlar.
- Türkçe metinde `textTransform: 'uppercase'` kullanılmaz (öneri); büyük harf `trUpper` ile.
- Klişe motif yok: cami silueti, hilal, ay-yıldız, yeşil-altın gradyan, süs amaçlı sahte Arapça (Tasarım sistemi §7, §8).
- `packages/ui-tokens` platformdan bağımsızdır; NativeWind ve Tailwind çıktıları üretilir, paket onları içe aktarmaz.
- Git Bash'te `adb` yol dönüşümü ve tırnak sorunlarında `windows-sorun`.
- Commit kapsamları `ui-tokens` ve `mobile`.

## İnsan adımları
- İ-22 · Öneri işaretli değerlerin onayı: TS-4 (ek rol jetonları, vurgu renkleri, `bolum-risale`) ve TS-1 (arayüz yazı tipi) proje sahibine sorulur. Aşamayı durdurmaz; onay gelene kadar dokümandaki değerler kullanılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/ui-tokens/`: `package.json`, `src/tokens.json`, `src/schema.json`, `src/build.ts`, `test/contrast.test.ts`; üretilen `dist/`
- `apps/mobile/`: tema sağlayıcısı, `useThemeTokens`, NativeWind ön ayar bağlantısı, ESLint renk kuralı, simge takımı
- `apps/mobile/app/(tabs)/ayarlar/gelistirici/vitrin.tsx`, `apps/mobile/src/features/settings/vitrin/`
- Karar defterinde simge takımı; `/belge-esitle` ile işlenen TS-8 ve yazı tipi doğrulamaları; `.tmp/vitrin/` (git dışı)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A22-tasarim-vitrini.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A21](./A21-mobil-iskelet.md) · Sonraki: [A23](./A23-cihaz-veri-katmani.md)
