# A34 · Mağaza v1 yayın hazırlığı

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-21](../../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 3 · Mağaza v1 · **Önkoşul:** [A33](./A33-uctan-uca-test-ve-ic-dagitim.md) · **İnsan adımı:** İ-03 (KVKK dosyasının avukat incelemesi) · İ-15 (hesaplar, gönderim) · İ-18 (canlı depo, alan adı) · İ-19 (Kurul başvurusu ve onayı) · İ-27 (Sentry ayarları)
> **Ajanlar:** `lisans-denetcisi` · `inceleyici` · `arastirmaci` · `belge-bekcisi` · **Beceriler:** `lisans-kapisi` · `paket-yayini` · **Tahmini oturum:** 3–4 (Kurul beklemesi hariç)
> **Başlat:** `/asama A34`

## Amaç
Kurul onaylı içerikle `public` (mağaza) derlemesini yayına hazır hâle getirmek. [Test stratejisi](../../07-yayin/03-test-stratejisi.md) §13 sürüm kontrol listesinin her maddesi kanıtıyla kapanır: public yapıt taraması yeşil, public manifest imzalı, Kurul kapsamındaki içerik özetleri onaylı özetlerle aynı, atıflar ve `THIRD_PARTY_NOTICES` eksiksiz, gizlilik metni ve mağaza beyanları uygulamanın gerçek davranışıyla uyumlu, geri alma yolları yazılı. Aşama `mobile-vX.Y.Z` etiketiyle biter. Mağazaya gönderim (`eas submit`) ve Kurul başvurusu insan işidir; Claude Code mağazaya hiçbir şey göndermez.

## Okunacak belgeler
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): tamamı; özellikle §3, §4.2 imza, §5 yapıt taraması, §6 ekranlar, §7.2–§7.3 Kurul adımları ve değişiklik yönetimi, §7.6
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §2 (v1), §4 "Faz 3 öncesi" listesi, §5
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §5 test 6 ve 8, §7, §12, §13
- [Backend API](../../02-mimari/05-backend-api.md): §10.1 komutlar ve çıkış kodları, §10.3 P-01…P-14, §10.5, §10.6 terfi ve geri alma
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §6 etiketler, §7 `eas-build.yml` ve gömülü `core` denetimi
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §5 manifest ve imza, §6 sürümleme ve geri çekme
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §2.2, §4 etiketler, §8 B-05, B-06, B-07, B-12
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 3, §6 soru 1 · [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md): §3 lisans notları, §4.2
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §6 "Şart takibi" · [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §10, §12

## Kapsam
**Yapılır**
- Sürüm kaydı ve §13 kontrol listesinin kanıtlarla kapatılması; lisans defteri §6 şart takibi.
- İçerik dondurma, Kurul başvuru dosyası, onayın kaydı, `public` terfisi, imza ve yapıt taraması.
- Atıf denetimi, `THIRD_PARTY_NOTICES`, gizlilik metni, mağaza beyanları ve mağaza metninin hazırlanması.
- Sürüm numarası, `mobile-vX.Y.Z` etiketi, geri alma yollarının yazılması ve `dev` türünde provası.

**Yapılmaz**
- Maestro akışlarının, performans ve erişilebilirlik ölçümünün kurulması (A33); burada yalnız sürüm adayındaki sonuçlar kayda bağlanır.
- Kaynaklar ve lisanslar ile Kurul onay bilgisi ekranlarının kodu (A32); burada yalnız içerikleri denetlenir.
- Hesaplı sürümün gizlilik beyanları (A35, A36). Lisans ya da takvim olayıyla içerik açmak (A39).
- Mağaza konsollarında form doldurma ve `eas submit` (insan).

## Adımlar
### A34.1 · Önkoşullar, şart takibi ve sürüm kaydı
- `/durum` ile A33'ün bittiğini, sürüm adayı commit'ini ve İ-15, İ-18, İ-19 durumunu göster. A33'ün Maestro, performans, erişilebilirlik ve duman testi kanıtları bu aşamanın girdisidir.
- Sürüm kaydını aç: `docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z.md` (öneri). İçine §13 maddelerini, KVKK §4 "Faz 3 öncesi" listesini ve her madde için "kanıt" alanını yaz; insan gerektiren maddeye İ numarası yazılır.
- `lisans-denetcisi`: lisans defteri §6 şart takibi: QF şartları (her public sürümden önce), tanzil.net güncellemeler sayfası, QAC metinleri yeniden okunur; tarih ve sonuç kayda girer. Şart değiştiyse aşama durur ve [A39](./A39-takvim-ve-lisans-olaylari.md) yordamı açılır.
- `arastirmaci` resmî kaynaktan doğrular (KVKK §2.2, §2.5, §2.6'da "Doğrulanacak"): mağazaların gizlilik politikası bağlantısı kuralı; App Privacy ve Veri güvenliği formlarının güncel alan adları; hata raporlama servisinin "hizmet sağlayıcı" sayılması; Sentry'de IP saklamayı kapatan ayarın adı ve servis veri bölgesi; Expo eklentisiyle sürüm ve kaynak eşlemesi yükleme yolu; EAS Update ile `production` kanalına düzeltme gönderme komutu.
- Proje sahibi kararları kayda ve `/karar` ile deftere: ses izni ya da onayı yoksa Mağaza v1'in sessiz çıkıp çıkmayacağı (Fazlar §6 soru 1); hata raporu anahtarının varsayılanı (KVKK §5 soru 2); veri sorumlusu ve iletişim adresi (S-11).
- **Bitti sayılır:** sürüm kaydı var; her madde ya kanıt ya da İ numarası taşıyor; `arastirmaci` raporu bağlantılı ve tarihli.

### A34.2 · İçerik dondurma ve Kurul başvuru dosyası
- Mealin iki düzeltme turu kapalıdır; `elmalili-meal` birimlerinden `onayli` olmayan kalmaz (SQL aşağıda). Kapanmamışsa başvuru yapılmaz: onaydan sonraki düzeltme yeniden onay ister.
- Dondurma yayını: `dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal`. Yayın sürümü (`S`, CalVer) ve `release.ozetler` içindeki Kurul içerik özetleri, Tanzil dosya özeti, Elmalılı metin sürümü, ses giriyorsa hafız başına âyet-dosya listesi kayda yazılır ([Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md) §7.2 madde 2).
- Başvuru dosyası `data/kurul/<S>/` altında (git dışı): Tanzil'le bayt bayt eşitlik raporu (A10 değişmezlik testleri), test raporları (A33), üç mushaf modunun ekran görüntüleri, izin belgeleri, Kurul'un istediği biçimde döküm (biçim Açık soru; İ-02 cevabına göre). Ön yazı `/yazisma kurul` ile `docs/yazismalar/` altına taslak olur.
- **Bitti sayılır:** `data/kurul/<S>/` §7.2 madde 3'teki her belgeyi içeriyor; teslim listesi İ-19 için kullanıcıya gösterildi.

### A34.3 · Kurul onayını sabitleme (İ-19 cevabından sonra)
- Kurul düzeltme isterse düzeltme elle yapılmaz: içerik hattından geçer, testler koşar, yeni özet üretilir ve A34.2'ye dönülür (onay treni).
- Onay gelince her Kurul kaynağı için editör panelinden `PUT /api/v1/sources/{slug}/kurul-onay` (onay no, onaylı sürüm, tarih, özet) açılır; değeri farklı bir editörün ikinci onayı uygular. Claude Code onay vermez.
- `publish --flavor public --dry-run`: kapı raporunda P-04 reddi yoksa devam; ret varsa çıkış kodu `2` ve gerekçe raporda.
- Onaylı içerik commit'i `kurul/<onay-no>` etiketiyle işaretlenir (öneri).
- **Bitti sayılır:** her Kurul kaynağında üç Kurul alanı ve `ikinci_inceleyen` dolu; kuru çalıştırmada P-04 reddi yok.

### A34.4 · Public yayın, imza ve yapıt taraması
- Canlı depo (İ-18) ayarları A33'teki `internal` kanalıyla aynı yoldan verilir; gizli değerler yalnız kullanıcı sırlarında. Yol tanımlı değilse `/karar` ile seçilir.
- `public` imza anahtarı yoksa `keys generate --flavor public`: açık anahtar `apps/mobile/src/packs/keys.ts` içindeki `public` listesine girer; özel anahtar depoya ve CI günlüğüne girmez; `public` ve `internal` anahtarları ayrıdır. Sıradaki anahtar (öneri) ve özel anahtarın çevrimdışı yedeği insan işidir.
- Terfi: `promote --surum <S> --to public` (P-14: içerik özetleri iç kanalda test edilenle aynı).
- Gömülü `core`: `MANIFEST_URL=https://<içerik-alanı>/public/manifest.json pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs` imzayı ve sha256'yı doğrular.
- Yapıt taraması: `verify --flavor public --embedded-core apps/mobile/assets/db/core.db` (dosya adı BÇ-25 kararıdır) ve `verify --flavor internal`. Tarama her `pack_source` kaydının `serbest`, Kurul özetlerinin `kurul_onay_ozeti` ile aynı ve public önekte manifest dışı nesne olmadığını denetler; P-12 gereği `test-` kaynak yoktur.
- **Bitti sayılır:** iki `verify` 0 ile çıkıyor; gömülü `core` sha256'sı public manifestte geçiyor; manifestte fikstür paketi yok.

### A34.5 · Atıflar, açık kaynak lisansları, gizlilik ve mağaza metni
- Atıf (B-07): public paketlerin `attribution` satırları lisans defteriyle karşılaştırılır: Tanzil bildiriminin tam metni ve tanzil.net bağlantısı, Elmalılı künyesi, font lisansları, varsa QF atfı ve hafız adları. Eksik atıf `source.atif_metni` alanında düzeltilir; paket sürümü artar.
- `THIRD_PARTY_NOTICES` mobil ikiliye giren bağımlılıkların lisans listesinden üretilir (`pnpm --filter @mutalaa/mobile licenses list`; yalnız üretim bağımlılığı ve JSON çıktı seçenekleri `arastirmaci` ile doğrulanır). Dosya yeri A32'deki ekranın okuduğu yerdir; yoksa öneri `apps/mobile/assets/THIRD_PARTY_NOTICES.txt`. İzin listesi dışı lisans ya da reklam ve izleme SDK'sı varsa aşama durur. Sunucu tarafı (A07, [Teknoloji yığını](../../02-mimari/02-teknoloji-yigini.md) §2.2) bildirim listesine yazılır: Npgsql (PostgreSQL License telif bildirimi), EFCore.NamingConventions (Apache-2.0), EF Core ve Identity (MIT). Sunucu mobil ikiliye girmediği için bildirimin hangi dosyada duracağı bu aşamada kararlaştırılır (hukuki görüş değildir).
- Gizlilik metni KVKK §2.5 taslağından yazılır; veri sorumlusu A34.1 kararıyla dolar. Metindeki menü yolları uygulamadaki gerçek adlarla aynı olmalıdır; taslak [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md) §6 ağacındaki adlara ("İlerleme ve gizlilik", "Verilerimi sil") uyduruldu (19 Ekim 2026). Uygulamadaki adlar değişirse metin de değişir. Metin uygulamada ve alan adındaki sayfada yayımlanır (İ-18).
- Davranış denetimi: `beforeSend` ayıklama testi (fikstür not metni olaydan düşer), `sendDefaultPii: false`, analitik ve izleme SDK'sı yok, App Tracking Transparency istenmiyor, "Hata raporlarını gönder" anahtarı ve "Verilerimi sil" çalışıyor.
- Mağaza beyanları KVKK §2.6 tablosundan, A34.1'deki güncel alan adlarıyla kayda yazılır; formları insan doldurur (İ-15).
- Mağaza metni `docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z-magaza-metni.md` (öneri): yalnız public manifestteki paketlerin özelliklerini anlatır. Kapsam ve fazlar §4'te `v1.x`, `Web`, `Takvime bağlı`, `Faz atanmadı` etiketli özellikler ve public'te olmayan paketler (ör. `bekliyor` `kelime-kok`, Mushaf A, izinsiz ses) vaat edilmez; resmî kurum çağrışımı ve kurum logosu yoktur (R-12). `inceleyici` metni bu listeye göre okur.
- **Bitti sayılır:** atıf karşılaştırması farksız; `THIRD_PARTY_NOTICES` yeniden üretildiğinde `git diff` boş; mağaza metni incelemesi bulgusuz.

### A34.6 · Sürüm, etiket, üretim derlemesi ve geri alma
- Uygulama sürümü `app.config.ts` içinde `X.Y.Z`; `eas.json` `production` profili `MANIFEST_URL` (public manifest) ve `SENTRY_DSN` taşır (gizli değer değildir). Mağaza yayınından önceki iki haftada SDK değişmez (öneri).
- Geri alma yolları sürüm kaydına yazılır: JS hatası → EAS Update, `production` kanalı (içerik taşımaz); içerik → `rollback --flavor public --to <önceki>`; `core` → yeni uygulama sürümü. Prova `dev` türünde: `rollback --flavor dev --to <önceki>` ve `verify --flavor dev`, ardından `publish --flavor dev` ile eski hâline dönülür.
- `/inceleme`, `/commit`, yerel etiket: `git tag -a mobile-vX.Y.Z -m "mobile vX.Y.Z"`. Etiketin gönderilmesi `eas-build` iş akışını tetikler; yalnız kullanıcının açık onayıyla yapılır ya da kullanıcı yapar. İş akışındaki `fetch-core.mjs` imzayı ve `core` için `kurul_onay` değerini denetler; boşsa derleme durur.
- Test kanalı (TestFlight, Google Play iç test), iOS 16.4 ve düşük seviye Android duman testi, Kurul onay bilgisi ekranının görüntüsü, Sentry sürümü ve kaynak eşlemeleri, ikili boyutu: insan yapar ya da paylaşır, sonuç kayda yazılır.
- **Bitti sayılır:** etiket sürüm commit'ini gösteriyor; prova `rollback` ve `verify` 0 ile çıktı; kayıtta kanıtsız madde yalnız İ numaralı maddeler.

## Kabul ölçütleri
- [ ] `verify --flavor public --embedded-core …` ve `verify --flavor internal` 0 ile çıkıyor.
- [ ] `fetch-core.mjs` public manifest imzasını `keys.ts` içindeki `public` anahtarıyla doğruluyor; gömülü `core` sha256'sı public manifestte bir kez geçiyor.
- [ ] Public manifestte `test-` önekli ya da `ses-test` paketi yok.
- [ ] `elmalili-meal` birimlerinde `onayli` olmayan satır sayısı 0.
- [ ] Her Kurul kaynağında `kurul_onay`, `kurul_onay_tarihi`, `kurul_onay_ozeti` dolu; ilgili `review` satırlarında `inceleyen` ile `ikinci_inceleyen` dolu ve farklı.
- [ ] Public kapı raporunda `core` "girdi"; "girmedi" olan her paket gerekçesiyle sürüm kaydında (gözle).
- [ ] `THIRD_PARTY_NOTICES` yeniden üretildiğinde fark yok; lisans listesinde izin dışı lisans ve reklam ya da izleme SDK'sı yok.
- [ ] Atıf karşılaştırması farksız; `core` paketinde Tanzil bildiriminin tam metni var (değişmezlik testi 6).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil ve `beforeSend` ayıklama testi içinde.
- [ ] Gizlilik sayfası 200 döndürüyor; metindeki menü yolları uygulamadaki adlarla aynı (gözle).
- [ ] Mağaza metni incelemesinde ertelenmiş özellik ya da public'te olmayan paket yok (`inceleyici` raporu).
- [ ] `dev` geri alma provası 0 ile çıktı; sürüm kaydında üç geri alma yolu yazılı.
- [ ] `mobile-vX.Y.Z` etiketi sürüm commit'inde; kayıtta boş kanıt yalnız İ numaralı maddelerde.

## Doğrulama
```bash
pnpm turbo run lint typecheck test && dotnet test --solution server/Mutalaa.slnx && (cd pipeline && uv run pytest)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'elmalili-meal' AND metin_durumu <> 'onayli';"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT slug, kurul_onay, kurul_onay_tarihi, left(kurul_onay_ozeti, 12) FROM icerik.source WHERE kurul_gerekli AND license_status = 'serbest';"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT hedef_anahtar, inceleyen, ikinci_inceleyen FROM icerik.review WHERE hedef_tablo = 'source' AND alan = 'kurul_onay' AND durum = 'onaylandi';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run; echo "çıkış: $?"
MANIFEST_URL="https://<içerik-alanı>/public/manifest.json" pnpm --filter @mutalaa/mobile exec node scripts/fetch-core.mjs
dotnet run --project server/Mutalaa.Publisher -- verify --flavor public --embedded-core apps/mobile/assets/db/core.db; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor internal; echo "çıkış: $?"
curl -sS "https://<içerik-alanı>/public/manifest.json" -o .tmp/public-manifest.json
grep -c "$(sha256sum apps/mobile/assets/db/core.db | cut -d' ' -f1)" .tmp/public-manifest.json   # 1
grep -cE '"pack_id": *"(test-|ses-test)' .tmp/public-manifest.json                                       # 0
pnpm --filter @mutalaa/mobile licenses list
pnpm --filter @mutalaa/mobile test && grep -rl --include="*.test.*" "beforeSend" apps/mobile
curl -sSf -o /dev/null "https://<alan-adı>/<gizlilik-sayfası>" && echo "gizlilik sayfası açık"
dotnet run --project server/Mutalaa.Publisher -- rollback --flavor dev --to "<önceki-sürüm>"; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
git rev-parse "mobile-vX.Y.Z^{commit}" HEAD
grep -n -- "- \[ \]" docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z.md | grep -v "İ-"                       # boş
```
Gömülü `core` dosyasının adı A23'teki BÇ-25 kararıdır (öneri `core.db`); karar başka ad seçtiyse komutlar ona göre yazılır. `-U` ve `-d` değerleri `.env.example` varsayılanlarıdır. Kullanıcı PowerShell'de çalıştırırsa: `$env:MANIFEST_URL = "https://<içerik-alanı>/public/manifest.json"` ve `curl.exe`.

## Dikkat
- `eas submit` hiç çalıştırılmaz; etiket gönderimi ve EAS derlemesi kullanıcının açık onayı ister (CLAUDE.md kural 11).
- `public` yalnız `serbest` ve gerekiyorsa Kurul onaylı içerik alır; `test-` kaynak hiçbir durumda girmez. Ayrıntı: `lisans-kapisi`.
- Onaydan sonra Kurul kaynağında tek bayt değişirse içerik özeti değişir ve public derleme durur (P-04); düzeltmeler onay treninde toplanır.
- EAS Update içerik taşımaz; gömülü `core` yalnız yeni ikiliyle değişir.
- Özel imza anahtarı yalnız kullanıcı sırlarında durur; Claude Code `.env` dosyalarını okumaz.
- Kurul onay bilgisinin gösterim biçimi (numara, QR, mühür) Açık soru; Kurul'un cevabına göre A32 ekranı güncellenir.
- Yurt dışı vitrinler aynı kapıdan geçer; onay beklerken yalnız yurt dışında yayın yapılmaz (§7.6). Hukuki görüş değildir.

## İnsan adımları
- İ-19 · Kurul başvurusu ve onayı: A34.2'deki dosya hazır olunca; A34.3'ten önce gerekir.
- İ-18 · Canlı içerik deposu ve alan adı: A34.4 ve gizlilik sayfasından önce.
- İ-15 · Expo, Apple Developer ve Google Play hesapları: mağaza adı kontrolü (S-08), beyan formları, test kanalı, `eas submit` ve yayına alma; A34.6'da.
- İ-03 · KVKK dosyasının avukat incelemesi: [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md) başlık notu gereği v1 mağazaya çıkmadan önce.
- İ-27 · Sentry proje ayarında IP saklamanın kapatılması ve kaynak eşlemesi yükleme sırrı.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `docs/07-yayin/surum-kayitlari/mobile-vX.Y.Z.md` ve `mobile-vX.Y.Z-magaza-metni.md` (öneri)
- `data/kurul/<S>/` başvuru dosyası (git dışı); `docs/yazismalar/` altında Kurul ön yazısı taslağı
- `release` tablosunda `internal` ve `public` yayınları; canlı depoda public manifest, imzası ve paketler
- `apps/mobile/src/packs/keys.ts` (`public` açık anahtarı), `apps/mobile/eas.json`, `app.config.ts` sürümü, `THIRD_PARTY_NOTICES`
- Gizlilik metni (uygulama içi ve alan adında); karar defteri girdileri; git etiketleri `mobile-vX.Y.Z` ve `kurul/<onay-no>` (öneri)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A34-magaza-yayini.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A33](./A33-uctan-uca-test-ve-ic-dagitim.md) · Sonraki: [A35](./A35-hesap-ve-kvkk.md)
