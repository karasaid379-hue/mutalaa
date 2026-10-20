# A06 · Lisans defteri v1 (kaynak kayıtları) ve ortak enum şeması

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · **İnsan adımı:** yok
> **Ajanlar:** `hat-gelistirici` · `lisans-denetcisi` · `arastirmaci` · `web-gelistirici` · `sunucu-gelistirici` · `inceleyici` · **Beceriler:** `lisans-kapisi` · `icerik-hatti` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A06`

## Amaç
Lisans defterindeki her somut kaynak, `pipeline/sources/{kimlik}.toml` kaydı ve tarihli lisans kopyasıyla depoya girer; `uv run mutalaa sources list` ve `sources check` çalışır. Bundan sonra kaydı olmayan kaynak içerik hattına alınamaz (G-LIS). Paylaşılan enum değerleri `packages/content-schema` içindeki tek bir JSON dosyasında durur; Python, TypeScript ve C# karşılıkları bu dosyaya karşı test edilir, PostgreSQL tarafı A07'dedir. Faz 0 çıkış ölçütü "Lisans defterinde v1 kaynaklarının durumu dolu" bu aşamayla sağlanır.

## Okunacak belgeler
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): tamamı (§1 durumlar ve iç kullanım kuralı, §2 özet tablo, §3 kaynak kartları, §6 şart takibi, §7 kontrol listesi ve TOML örneği)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar ve çıkış kodları, §8 yeni kaynak ekleme, §9 G-LIS
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §2 türler, §3 `source` sütunları (TOML alanları aynı adları taşır)
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 enum tutarlılığı
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §2.1, §2.3 durum sırası, §3 derleme görünürlüğü
- [Backend API](../../02-mimari/05-backend-api.md): §2 (`Content/`, `Links/`, `Licensing/`), §7 (enum etiket testi), §10.3 P-02

## Kapsam
**Yapılır**
- `pipeline/sources/{kimlik}.toml` kayıtları; `pipeline/sources/licenses/` altında lisans kopyaları ve dayanak notları.
- `uv run mutalaa sources list` ve `sources check`, fikstürlü testleriyle.
- `packages/content-schema/enums.json` (öneri ad) ve TypeScript, Python, C# karşılıkları ile testleri.

**Yapılmaz**
- `source` tablosu ve PostgreSQL enum türleri (A07); `source` satırlarının veritabanına yüklenmesi (`ingest`, A10).
- `test-` önekli sentetik kaynak kayıtları (A13).
- Kalıp kimlikler (`qul-*`, `ses-turk-hafiz-*`, `mushaf-b-*`): somut kaynak seçilince ilgili aşamada (A17, A27, A40).
- Yayın kapısı mantığı (A13). Yazışma cevaplarının işlenmesi (A01'den sonra `/karar`).
- `kapali` kaynakların dosyalarını indirmek (iç kullanım kuralı; lisans defteri §1).

## Adımlar
### A06.1 · Kayıt şeması ve `sources` komutları (`hat-gelistirici`)
- TOML alanları `source` sütunlarıyla aynı adı taşır (Editoryal veritabanı §3; lisans defteri §7 örneği). Zorunlu: `slug`, `tur`, `baslik`, `license_name`, `license_status`, `atif_metni`, `kurul_gerekli`, `embed_ok`, `yeniden_kontrol`. İsteğe bağlı: `yazar`, `yazar_vefat_yili`, `surum`, `provider`, `kaynak_url`, `license_url`, `kisitlar`, `notice_text`, `atif_url`, `kamu_mali_tarihi`, `baski_bilgisi`, `notlar`, `lisans_kopyasi`, `lisans_sha256`.
- `surum` veritabanında zorunludur; TOML'da boşsa alım sırasında doldurulur (A10 ve sonrası; öneri).
- `uv run mutalaa sources list [--format json]`: kimlik, `tur`, `license_status`, `kurul_gerekli`, `embed_ok`, `yeniden_kontrol`; tarihi geçmiş yeniden kontrol işaretlenir (`--format json` öneri).
- `uv run mutalaa sources check`: her TOML ayrıştırılır; dosya adı `slug` ile aynı ve ASCII; `tur` ve `license_status` `enums.json` değerlerinden; `kapali` dışındaki kaynakta lisans kopyası var ve SHA-256'sı tutuyor (G-LIS); `atif_metni` dolu; `kisitlar` anahtarları bilinen listeden (`degistirme_yasak`, `hazir_vt_yasak`, `onbellek_gun`, `yalniz_eslesen_ses`; bilinmeyen anahtar uyarı, öneri). Çıkış kodları İçerik hattı §4: `0` geçti, `2` kayıt ya da dosya hatası.
- Testler `pipeline/tests/fixtures/sources/` altındaki `test-` önekli sentetik kayıtlarla: geçerli kayıt, bozuk TOML, eksik lisans kopyası, yanlış özet, bilinmeyen durum, dosya adı ile `slug` farkı.
- **Bitti sayılır:** komut testleri yeşil; `0` ve `2` çıkış kodları sınandı.

### A06.2 · Enum JSON'u ve dil karşılıkları
- `packages/content-schema/enums.json`: Test stratejisi §6'daki dört tür (`license_status` 4, `xref_type` 8, `xref_status` 3, `xref_origin` 3) Editoryal veritabanı §2'deki sırayla. Ek olarak `source_kind` (TOML `tur` denetimi için) ve `derleme_turu` (öneri). Sıra anlamlıdır: `serbest` < `bekliyor` < `ic_kullanim` < `kapali`; kapı en kısıtlayıcıyı seçer (Yayın kapısı §2.3).
- TypeScript (`web-gelistirici`): `packages/content-schema/src/enums.ts` içinde `as const` dizileri ve birleşim tipleri; Vitest dizileri JSON'la sırasıyla karşılaştırır.
- Python (`hat-gelistirici`): `pipeline/src/mutalaa_pipeline/enums.py` (öneri) `StrEnum` sınıfları; pytest JSON'la karşılaştırır; `sources check` bu sınıfları kullanır.
- C# (`sunucu-gelistirici`): `Mutalaa.Domain/Licensing` (`LicenseStatus`, `BuildFlavor`), `Mutalaa.Domain/Content` (`SourceKind`) ve `Mutalaa.Domain/Links` (`XrefType`, `XrefStatus`, `XrefOrigin`) (Backend API §2). C# adı ile veritabanı etiketi arasındaki eşleme Domain'de saf bir işlevdir (`IcKullanim` → `ic_kullanim`); xUnit testi her değerin etiketini ve sırasını JSON'la sınar (Backend API §7). Domain Npgsql'e bağlanmaz.
- **Bitti sayılır:** üç dilin testi yeşil; JSON'dan bir değer geçici olarak silinince üçü de kırmızı.

### A06.3 · Lisans kopyaları (`arastirmaci`, `hat-gelistirici`)
- `arastirmaci` her kaynağın lisans ya da şart sayfasını defterdeki bağlantıdan canlı okur ve defterdeki özetle uyuşup uymadığını raporlar. Fark çıkarsa durum değiştirilmez; kullanıcıya gösterilir ve `/karar` önerilir.
- `hat-gelistirici` metni `pipeline/sources/licenses/{kimlik}-{YYYY-MM-DD}.txt` olarak saklar ve SHA-256'yı TOML'a yazar (lisans defteri §7). Yalnız lisans ya da şart metni kopyalanır; makale ya da ansiklopedi metni kopyalanmaz.
- Koruma süresi dolduğu için serbest olan eserlerde (ör. `elmalili-meal`, `tecrid-naim`, `lugat-redhouse-1890`) lisans metni yoktur. Dosya bizim yazdığımız kısa bir dayanak notudur: ölüm tarihi, FSEK m. 26–27 hesabı, defterdeki kaynak bağlantıları (öneri).
- Canlı sayfası okunamayan kaynakta (ör. tanzil.net, KFGQPC resmî sayfası) defterin dayandığı kopya kullanılır ve `notlar` alanına "Doğrulanacak" yazılır. Tanzil için bu, defterin bağlantı verdiği OpenITI kopyasındaki Tanzil bildirim satırlarıdır; OpenITI'nin kendi içeriği alınmaz (lisans defteri §4). Canlı doğrulama ilgili aşamadadır (Tanzil için A10).
- **Bitti sayılır:** `kapali` dışındaki her kaynakta lisans kopyası ya da dayanak notu ve doğru SHA-256 var.

### A06.4 · Kayıtlar (`hat-gelistirici`, `lisans-denetcisi`)
- Lisans defteri §2'deki her somut kimlik için bir TOML. Değerler tablodan ve §3 kartlarından aynen alınır: `license_status`, `embed_ok`, Kurul sütunu, atıf metni, kaynak ve lisans bağlantıları.
- Eşleme kuralları: `embed_ok` "Uygulanmaz" (font) → `false`; "Evet (çıkarım)" → `true` ve `notlar`'da "çıkarım". Kurul "Evet", "Dolaylı", "Ses paketiyle" → `kurul_gerekli = true` (Editoryal veritabanı §3 tür varsayılanı); "Gerekmez" → `false`; "Açık soru" → tür varsayılanı ve `notlar`'da "Açık soru".
- `tur` `source_kind` değerlerinden seçilir; belirsiz eşleşme (ör. `risale-kelime-frekans`) kullanıcıya sorulur.
- `kisitlar`: değiştirme yasağı taşıyan kaynaklarda `degistirme_yasak = true` (Tanzil, QAC, KFGQPC Hafs fontu; lisans defteri §3.1–§3.2); `ses-qf-api` için `hazir_vt_yasak = true` ve `onbellek_gun = 7` (§3.1, Backend API P-02); `quran-align` için `yalniz_eslesen_ses = true` (§7 örneği).
- Defterin kaynak başına "Doğrulanacak" ve "Açık soru" notları TOML'un `notlar` alanına taşınır; çözümü sahibi olan aşamadadır (ör. Tanzil sürüm numarası A10, Naim'in çevirdiği ciltler A19, Amiri Quran alt kümeleme koşulu A24).
- `yeniden_kontrol`: QF kaynaklarında üç ay sonrası (§6 şart takibi), diğerlerinde altı ay sonrası (öneri; §7 örneği).
- `lisans-denetcisi` `sources list --format json` çıktısını §2 tablosuyla satır satır karşılaştırır; kimlik ve `license_status` farkı sıfır olmalı.
- Kullanıcı durumları onaylar (lisans defteri §7 son madde). Defter §1'deki editoryal veritabanı farkı çözüldü (19 Ekim 2026): Editoryal veritabanı §3 ve §11 defterle aynı değerleri verir.
- **Bitti sayılır:** `sources check` 0 ile çıkıyor; karşılaştırma farkı sıfır; kullanıcı onayı aşama kaydında.

## Kabul ölçütleri
- [ ] Lisans defteri §2'deki her somut kimlik için `pipeline/sources/{kimlik}.toml` var; kalıp kimlikler için dosya yok.
- [ ] `uv run mutalaa sources check` 0 ile çıkıyor; bozuk fikstürlerde 2 ile çıktığı pytest'te sınanıyor.
- [ ] `sources list` çıktısında `kapali` kayıtlar defterdeki gibi: `tecrid-miras`, `risale-1956-1960`, `risale-asil-nusha`, `risale-atif-dizini`, `ses-everyayah`, `ses-quranicaudio`.
- [ ] `kapali` dışındaki her kaynakta lisans kopyası ya da dayanak notu ve tutan SHA-256 var.
- [ ] `enums.json` dört zorunlu türü Editoryal veritabanı §2'deki sırayla taşıyor; TypeScript, Python ve C# testleri yeşil.
- [ ] `lisans-denetcisi` karşılaştırma raporu: kimlik ve durum farkı sıfır.
- [ ] Hiçbir lisans dosyası korunan bir eserin metnini içermiyor (gözle).

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check; echo "sources check çıkış: $?")
(cd pipeline && uv run mutalaa sources list)
(cd pipeline && uv run mutalaa sources list --format json) > .tmp/kaynaklar.json
(cd pipeline && uv run pytest && uv run ruff check . && uv run mypy src)
ls pipeline/sources/*.toml | wc -l
ls pipeline/sources/licenses/
pnpm --filter @mutalaa/content-schema test
dotnet test --solution server/Mutalaa.slnx
```

## Dikkat
- Hukuki görüş değildir. Claude Code durum değerlerini kendisi belirlemez ve değiştirmez; defterdeki değeri aynen yazar, farkı kullanıcıya gösterir. Ayrıntı: `lisans-kapisi`.
- `kapali` kaynağın kaydı yalnız üst veridir; dosyası indirilmez, hatta işlenmez, yapay zekâ servisine gönderilmez (lisans defteri §1). Risale metni avukat görüşüne kadar `kapali`dır.
- `embed_ok` varsayılanı `false`'tur; Quran Foundation içeriği `false` kalır (lisans defteri §1).
- Lisans defteri (`04-icerik/01`) ile TOML kayıtları aynı değişiklikte güncellenir; biri değişip öteki kalmaz (§7).
- Enum sırası anlamlıdır; değer eklemek ya da sırayı değiştirmek `/karar` ister. Yeni değer önce JSON'a, sonra dört dile aynı değişiklikte girer.
- Dosya adları ASCII; TOML ve lisans kopyaları UTF-8, BOM'suz, LF.
- Canlı sayfa okumak için web erişimi gerekir; izin listesinde olmayan alan adı kullanıcı onayı ister.

## İnsan adımları
- Yok. Kullanıcı A06.4'te durumları onaylar ve belirsiz `tur` eşleşmelerini seçer.

## Çıktılar
- `pipeline/sources/*.toml`, `pipeline/sources/licenses/*.txt`
- `pipeline/src/mutalaa_pipeline/` altında `sources` komutları ve `enums.py`; `pipeline/tests/` testleri ve `fixtures/sources/`
- `packages/content-schema/enums.json`, `packages/content-schema/src/enums.ts` ve testi
- `server/Mutalaa.Domain/Licensing/`, `Content/` ve `Links/` altındaki enum'lar ve etiket eşlemesi; `Mutalaa.Domain.Tests` içindeki enum testi
- `/belge-esitle` ile lisans defterindeki eski açık soru notunun güncellenmesi

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A06-lisans-defteri-ve-enumlar.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A05](./A05-arama-normalizasyonu.md) · Sonraki: [A07](./A07-editoryal-veritabani.md)
