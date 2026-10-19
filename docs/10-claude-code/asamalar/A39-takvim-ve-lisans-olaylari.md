# A39 · Takvim ve lisans olayları (2028, 2031, yeni lisanslar) — tekrar kullanılabilir yordam

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-04](../../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Faz:** 6 · Takvime bağlı · **Önkoşul:** [A13](./A13-yayinlayici-ve-yayin-kapisi.md) · **İnsan adımı:** olaya göre: İ-03 (avukat) · İ-19 (Kurul onay treni) · hak sahibiyle yazışma · ikinci onayı veren editör
> **Ajanlar:** `lisans-denetcisi` · `arastirmaci` · `hat-gelistirici` · `sunucu-gelistirici` · `belge-bekcisi` · `inceleyici` · **Beceriler:** `lisans-kapisi` · `paket-yayini` · `icerik-hatti` · **Tahmini oturum:** olay başına 1–3 (içerik sayısallaştırma işi hariç)
> **Başlat:** `/asama A39`

## Amaç
Bu aşama bir kez bitmez; her takvim ya da lisans olayında aynı yordamla yeniden yürütülür. Yordam lisans defterini günceller, `license_status` değerini inceleme akışıyla (ikinci onay) değiştirir, içerik Kurul kapsamındaysa onay trenini başlatır, yeni paket sürümlerini yayımlar ve Kaynaklar ve lisanslar ekranını günceller. Her olay `docs/04-icerik/olaylar/` (öneri) altında bir olay kaydı bırakır. Hiçbir durum tarih geldi diye kendiliğinden değişmez.

## Okunacak belgeler
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 6 tablosu ve ortak yol
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §1 iç kullanım kuralı, §2, ilgili kaynak kartı (§3), §4, §6 takvim ve şart takibi, §7 yeni kaynak kontrol listesi
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §2, §4, §6, §7.2–§7.3
- [Backend API](../../02-mimari/05-backend-api.md): §4 `/sources` uçları, §4.1 ikinci onay, §10.1, §10.6 · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `source` ve `kamu_mali_tarihi`, §8 `review`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §3.1 `attribution`, §6 sürümleme ve geri çekme
- Olaya göre: [Hadis hazırlığı](../../04-icerik/04-hadis-hazirligi.md) §1–§3 (2028), [Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md) §1, §4–§5 (2031), [Sonra yapılacaklar](../../08-yol-haritasi/02-sonra-yapilacaklar.md) S-04, S-05, S-06, S-07, S-09

## Kapsam
**Yapılır**

| Olay | Tarih | Kaynak | Geçiş | Kurul | Olaya özgü kural |
|---|---|---|---|---|---|
| Tecrîd, Kâmil Miras ciltleri | 1 Ocak 2028 | `tecrid-miras` | `kapali` → `serbest` | Gerekmez (çıkarım); hadisteki âyet çevirileri Açık soru | Tarih gelmeden indirme, tarama, OCR yok; III. cilt doğrulanana kadar Miras sayılır; çeviri çapası `ht:miras:tecrid:{no}`; okuyucudaki 2028 notu kalkar |
| Risale-i Nur | 1 Ocak 2031 | `risale-1956-1960` | `kapali` ya da `ic_kullanim` → `serbest` | Gerekmez (çıkarım; teyit) | Risale hazırlığı §5 listesi; Ekim–Aralık 2030 son hukuki kontrol; kelimesi kelimesine (K-25); başka yazar ve mütercim kısımları kendi tarihleriyle; `risale-asil-nusha` yalnız karşılaştırma |
| Çantay meali | 1 Ocak 2035 | yeni kaynak | yeni kayıt, `serbest` | Gerekir (mealli gösterim) | K-02 ve K-03 şimdilik yalnız Elmalılı'yı seçer; ek meal yeni karar ister (`/karar`, S-09); yalnız özgün baskı |
| Bilmen meal-tefsiri, *Hikmet Goncaları* | 1 Ocak 2042 | yeni kaynak | yeni kayıt, `serbest` | Meal için gerekir | Çantay ile aynı |
| Yeni lisans ya da izin | Tarihsiz | ör. Türk hattı ([A40](./A40-mushaf-b.md)), Diyanet meali, ek hafız, Risale lisansı, QAC cevabı, KFGQPC izni | iznin kapsamına göre `serbest` ya da `ic_kullanim` | Kaynağa göre | Lisans defteri §7 kontrol listesi; tarihli lisans kopyası |
| Geri çekme | Tarihsiz | kaldırma talebi, lisans iptali, Kurul onayının geri çekilmesi | `kapali` ya da önceki onaylı sürüm | — | Paket manifestten çıkar; cihazda paket lisans nedeniyle devre dışı kalır, notlar ve vurgular kalır |

**Yapılmaz**
- Büyük sayısallaştırma işinin kendisi (Miras ciltleri, Risale temel baskıları, yeni mealler): ilgili hat araçlarıyla (A16, A19, A20) ayrı plan olarak yürür; bu yordam yalnız kapı ve yayın yolunu yönetir.
- Mağaza sürümü (`core` değişirse A34 yordamı). Mushaf B'nin uygulaması (A40).

## Adımlar
### A39.1 · Olayı aç ve doğrula
- Olay kaydı `docs/04-icerik/olaylar/{YYYY-MM-DD}-{kimlik}.md` (öneri) şu şablonla açılır:
  ```markdown
  # Olay · {YYYY-MM-DD} · {kimlik}
  - Tür: takvim | yeni lisans | geri çekme
  - Kaynaklar: `{slug}` …   · Önceki → yeni durum: `kapali` → `serbest`
  - Dayanak: FSEK m. 26–27 hesabı ya da izin belgesi ya da avukat görüşü (bağlantılarla)
  - Kişiler ve tarihler: yazar, mütercim, sadeleştiren, derleyici; ölüm tarihleri ve kaynakları
  - Lisans kopyası: `pipeline/sources/licenses/{kimlik}-{YYYY-MM-DD}.txt` · SHA-256: …
  - Kurul: gerekli mi (evet, hayır, Açık soru); onay treni: başvuru tarihi, onay no
  - İnceleme kayıtları: `review` kimlikleri, `inceleyen`, `ikinci_inceleyen`
  - Paketler ve sürümler: `{pack_id}@{sürüm}` · Yayınlar: dev, internal, public (`release` kimlikleri)
  - Kullanıcıya görünen değişiklik: …   · Güncellenen belgeler: …
  - Kapanış: tarih, doğrulama çıktılarının özeti
  ```
- `lisans-denetcisi` + `arastirmaci`: FSEK m. 26–27 hesabı birincil kaynakla yapılır (lisans defteri §6: eser ölüm yılı + 71'inci yılın 1 Ocak'ında serbest kalır; kural mütercim ve sadeleştiren için ayrıca işler); lisans metni canlı sayfadan ve dosyadan okunur.
- Tarihli olayda olay gününden önce yalnız hazırlık yapılır (lisans defteri §6 "Hazırlık": 2027'nin son çeyreğinde Miras tarama planı ve araçlar, 2030'un son çeyreğinde son hukuki kontrol). Avukat gereken olayda İ-03, Kurul gereken olayda İ-19 takvime yazılır; hak sahibine taslak `docs/yazismalar/` biçimiyle hazırlanır.
- **Bitti sayılır:** kayıtta dayanak ve doğrulama alanları kaynak bağlantılarıyla dolu.

### A39.2 · Lisans defteri ve `source` güncellemesi
- Aynı değişiklikte: lisans defteri (özet tablo, kaynak kartı, §6 takvim), `pipeline/sources/{kimlik}.toml` (`license_status`, `lisans_kopyasi`, `lisans_sha256`, `atif_metni`, `embed_ok`, `yeniden_kontrol`) ve tarihli lisans kopyası. `uv run mutalaa sources check` (G-LIS) yeşil.
- Editoryal veritabanında değişiklik yalnız inceleme akışıyla: yönetici `PUT /api/v1/sources/{slug}/license-status` (gerekirse `/embed-ok`, `/kurul-onay`) ile `review` açar; ilk onay `inceleyen` alanını doldurur, farklı bir editörün onayı değeri uygular ve `ikinci_inceleyen` alanını doldurur. Claude Code isteği hazırlar, onay vermez. Tarihli olayda ikinci onay olay gününden önce verilmez.
- **Bitti sayılır:** API yeni durumu döndürüyor; `review` satırında iki farklı ad var; TOML, defter ve veritabanı aynı değeri taşıyor.

### A39.3 · İçerik hattı ve Kurul treni
- Yeni metin gerekiyorsa ilgili hat aracıyla işlenir (Tecrîd: A19; Risale: A20 altyapısı ve Risale hazırlığı §5; yeni meal: A16 araçları). `kapali` iken ham veri hatta alınmaz; komut 3 çıkış koduyla durur.
- Kaynak `kurul_gerekli` ise onay treni: içerik dondurma, başvuru dosyası, başvuru (İ-19), onayın ikinci onayla kaydı; A34.2 ve A34.3 aynen uygulanır. Onay gelene kadar kaynak `public`'e girmez (P-04).
- **Bitti sayılır:** QA kapıları geçti; Kurul gerekiyorsa onay alanları dolu ya da kayıt "Kurul bekleniyor" diyor.

### A39.4 · Paket yayını
- `publish --flavor dev` → testler → `publish --flavor internal` → kapı ve Kurul uygunsa `promote --surum <S> --to public`; her türde `verify`. İçeriği değişmeyen paket önceki sürümünü korur; atıf değişirse paket sürümü artar.
- `core` etkilenirse yeni uygulama sürümü gerekir (A34 yordamı); EAS Update içerik taşımaz.
- Geri çekmede kaynak `kapali` olur ya da `rollback --flavor <f> --to <önceki>` ile önceki onaylı sürüme dönülür.
- **Bitti sayılır:** bütün `verify` komutları 0; kapı raporunda kaynak doğru derleme türlerinde "girdi" ya da gerekçesiyle "girmedi".

### A39.5 · Ekranlar, belgeler ve kapanış
- Kaynaklar ve lisanslar ekranı paketlerin `attribution` tablosundan beslenir; yeni paket sürümünde satırın ve atıf metninin varlığı denetlenir. Olaya bağlı arayüz metinleri (Hadis okuyucudaki 2028 notu, Risale bilgi şeridi) güncellenir ya da kaldırılır.
- `/karar` ile karar defterine tarihli güncelleme satırı (eski satır silinmez). `/belge-esitle`: Fazlar Faz 6, Kapsam ve fazlar §3, ilgili hazırlık dosyası.
- Olay kaydı kapatılır.
- **Bitti sayılır:** kayıtta boş alan yok; `belge-bekcisi` çelişki bildirmiyor.

## Kabul ölçütleri
Her olayda:
- [ ] Olay kaydı var ve şablondaki her alan dolu.
- [ ] `uv run mutalaa sources check` 0; `sources list` ve `GET /api/v1/sources/{slug}` aynı yeni durumu gösteriyor.
- [ ] Durum değişikliğinin `review` satırında `inceleyen` ve `ikinci_inceleyen` dolu ve farklı; tarihli olayda `incelendi_at` olay gününden önce değil.
- [ ] Tarihi geçmiş ama hâlâ `kapali` kaynak sorgusu boş ya da her satır kayıtta gerekçeli.
- [ ] `verify --flavor dev`, `internal` ve yayımlandıysa `public` 0 ile çıkıyor.
- [ ] Yeni paketin `attribution` satırı güncel atıf metnini taşıyor (P-11; Kaynaklar ve lisanslar ekranında gözle).
- [ ] Kurul gerekiyorsa public kapı raporunda P-04 geçti ya da paket gerekçesiyle dışarıda.
- [ ] Karar defterinde tarihli güncelleme satırı var; `belge-bekcisi` raporu temiz.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check); echo "çıkış: $?"
(cd pipeline && uv run mutalaa sources list)
curl -sS "http://localhost:5080/api/v1/sources/<slug>"       # Development'ta DevAutoLogin ile
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT hedef_anahtar, inceleyen, ikinci_inceleyen, incelendi_at FROM icerik.review WHERE hedef_tablo = 'source' AND alan = 'license_status' ORDER BY id DESC LIMIT 5;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT slug, kamu_mali_tarihi, license_status FROM icerik.source WHERE kamu_mali_tarihi <= current_date AND license_status = 'kapali';"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor internal; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor public; echo "çıkış: $?"
```
`-U` ve `-d` değerleri `.env.example` varsayılanlarıdır. PowerShell'de `curl` yerine `curl.exe` yazılır.

## Dikkat
- Durum tarihe göre kendiliğinden değişmez; her geçiş inceleme akışı ve ikinci onaydır.
- Yordam tekrar kullanılır: ilerleme tablosunda aşama her olaydan sonra `tamam` olur, yeni olayda `/asama A39` ile yeniden `sürüyor` yapılır ve oturum günlüğüne olay adıyla yazılır. Tarihi gelmiş olayları `kamu_mali_tarihi` sorgusu gösterir (öneri: her yıl başında çalıştırılır).
- `kapali` kaynağın ham verisi indirilmez, hatta alınmaz, yapay zekâ servisine gönderilmez (`embed_ok = false`): 2028'den önce Miras ciltleri, avukat görüşünden ya da 2031'den önce Risale metni. Ayrıntı: `lisans-kapisi`.
- Serbest kalan eserde sonraki baskıların sadeleştirme, dipnot ve editoryal ekleri kullanılmaz; yalnız özgün baskı.
- Risale 2031'den sonra da kelimesi kelimesine, kısaltmadan ve sadeleştirmeden yayımlanır; yapay zekâ özeti yok (K-25, K-30). Tek yayınevine münhasır anlaşma yapılmaz.
- Çapalar yeniden numaralanmaz: Tecrîd numarası (`h:tecrid:{no}`) aynı kalır, Miras çevirisi `ht:miras:tecrid:{no}` olarak eklenir.
- Kurul kapsamındaki içerik onaysız `public`'e girmez; düzeltmeler onay treninde toplanır.
- Hukuki görüş değildir; FSEK hesabı ve iznin kapsamı avukatla teyit edilir.

## İnsan adımları
- Olaya göre: İ-03 (avukat: Risale 2031 son kontrolü, yeni iznin kapsamı), İ-19 (Kurul onay treni), hak sahibiyle yazışma ve izin belgesi, ikinci onayı verecek editör.
- Tarama işleri (Miras ciltleri, Risale temel baskıları) İ-09'a benzer biçimde ve olay gününden sonra.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `docs/04-icerik/olaylar/{YYYY-MM-DD}-{kimlik}.md` (öneri)
- `docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md`, `pipeline/sources/{kimlik}.toml`, `pipeline/sources/licenses/…`
- `source` ve `review` satırları; yeni `release` kayıtları ve paket sürümleri
- Karar defteri güncelleme satırı ve ilgili belge güncellemeleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A39-takvim-ve-lisans-olaylari.md dosyasındaki yordamı şu olay için yürüt: <olay, ör. "tecrid-miras, 1 Ocak 2028">. Önce olay kaydını, önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A38](./A38-web.md) · Sonraki: [A40](./A40-mushaf-b.md)
