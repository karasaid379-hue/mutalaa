# A04 · Çapa grameri ve ortak test vektörleri (TS, C#, Python)

> **Sürüm:** 1.1 · **Tarih:** 25 Ekim 2026 · **Durum:** Tamam (2026-10-25) · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-35](../../00-ozet/02-karar-defteri.md#k-35--çapa-api-ayrıntıları) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A02](./A02-tek-depo-iskeleti.md) · **İnsan adımı:** yok
> **Ajanlar:** `web-gelistirici` · `sunucu-gelistirici` · `hat-gelistirici` · `test-yazari` · `metin-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `capa-gramer` · `test-vektoru` · `metin-butunlugu` · **Tahmini oturum:** 3–4
> **Başlat:** `/asama A04`

## Amaç
Kalıcı adres grameri (K-26) üç dilde aynı davranışla yazılır ve ortak test vektörleriyle kilitlenir: `packages/anchors` (TypeScript), `Mutalaa.Domain/Anchors` (C#), `mutalaa_pipeline.anchor` (Python). Ofset dönüşümü, `snapSpan`, `content_hash` ve kendi metnimizin ilk kayıt kanonikleştirmesi de bu aşamadadır. Anlam denetiminin ihtiyaç duyduğu 114 elemanlı âyet sayısı dizisi hafızadan değil, Tanzil üst veri dosyasından üretilir. Vektörlerin CI'da koşması A08'dedir.

## Okunacak belgeler
- [Çapa şeması](../../03-veri/01-capa-semasi.md): tamamı (§2 gramer ve anlam kuralları, §3 desenler, §4 örnekler, §7 kanonik metin, §8 ofsetler, §11 API ve dil karşılıkları)
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1.2 vektör biçimi, §3 paylaşılan kodun yeri, §4.1 `shared/test-vectors` paketi
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §2 (örnekler ve tuzaklar; dosya adları eski, aşağıdaki düzen geçerli)
- [Backend API](../../02-mimari/05-backend-api.md): §2 (`Anchors/`, `Text/`), §9 kültürden bağımsızlık
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §10.2 (BOM, `Rune`, ofsetler)

## Kapsam
**Yapılır**
- Vektörler: `shared/test-vectors/anchors/{valid,invalid,compare,contains,route}.jsonl`, `offsets/offsets.jsonl`, `content-hash/hash.jsonl`.
- Âyet sayısı dizisi: `shared/data/ayet-sayilari.json` ve üç dilde üretilmiş kopyası.
- Çapa şeması §11'deki API'nin üç dildeki karşılıkları; C# ve Python'da `content_hash` ve ilk kayıt kanonikleştirmesi.
- `uv run mutalaa export test-vectors` (bu üç klasör için).

**Yapılmaz**
- Normalizasyon vektörleri ve normalleştiriciler (A05); `fts-query` (A12).
- Sure adları, `shared/data/sure-adlari.json` ve "Bakara 255" gibi insan yazımı ayrıştırıcı (A11, A12, A28).
- Tanzil üst verisinin kalıcı alımı ve dizinin Tanzil metniyle çapraz denetimi (A10, A11).
- EF Core değer dönüştürücüsü (A07). Hermes'te vektör koşumu ve öz test ekranı (A21, A32). Yeniden çapalama (A30).

## Adımlar
### A04.1 · Âyet sayısı dizisi (Tanzil üst verisi)
- `arastirmaci` Tanzil üst veri dosyasının resmî adresini, biçimini ve kullanım şartını doğrular. Adres hafızadan yazılmaz. **Çözüldü (2026-10-24):** belge sayfası [tanzil.net/docs/quran_metadata](https://tanzil.net/docs/quran_metadata); dosya [`quran-data.xml`](https://tanzil.net/res/text/metadata/quran-data.xml) (sürüm 1.0). Kullanım şartı belirsiz: dosyadaki lisans satırı CC BY 3.0, Tanzil SSS'si ise "non-commercial purposes" diyor. Kullanıcı kararı D1: devam edilir ve belirsizlik kayda geçer ([lisans defteri §3.1](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md); soru [Tanzil taslağı](../../yazismalar/tanzil-arama-metni.md) 2. soru, [İ-08](../06-insan-adimlari.md)). Hukuki görüş değildir.
- `hat-gelistirici` dosyayı `.tmp/tanzil-ust-veri/` altına indirir ve SHA-256'sını hesaplar. `data/raw` altına yazılmaz; kalıcı alım A11'dedir.
- Üretici `uv run mutalaa export ayet-sayilari --kaynak <xml> --url <adres> --tarih <YYYY-AA-GG> [--check]` sure başına âyet sayısını dosyadan okur (sure adlarını okumaz; DOCTYPE/ENTITY ve UTF-16/NUL girdiyi reddeder) ve `shared/data/ayet-sayilari.json` yazar: `kaynak_url`, `alinma_tarihi`, `sha256`, `lisans`, `telif`, `surum`, 114 elemanlı `sayilar`. Aynı komut üç kopyayı üretir: `packages/anchors/src/generated/ayet-sayilari.ts`, `pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py`, `server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs`. `--check` yazmadan diskle karşılaştırır; fark varsa 1 ile çıkar. Üretilmiş dosyalar elle düzenlenmez.
- Her dilde test: 114 eleman, toplam 6.236, 2. sure 286 (Çapa şeması §2 ve §4); kopya JSON'la aynı.
- **Bitti sayılır:** JSON ve üç kopya depoda; üç dilin dizi testi yeşil.

### A04.2 · Vektörler
- Satır biçimi Proje yapısı §1.2'deki alanlarla: `id`, `input`, `expected`, isteğe bağlı `note` (öneri ayrıntı aşağıda). Dosyalar JSONL, UTF-8, BOM yok, LF; satırlar `id` sırasıyla.

| Dosya | `input` | `expected` | Dayanak |
|---|---|---|---|
| `anchors/valid.jsonl` | çapa dizgisi | `ref` (§11 TS nesnesi `{anchor, span?}`), `canonical`, `unit` (`unitOf`), `unit_span` (`toUnitSpan`), `ayahs` (`coveredAyahs`; `q`, `qa`, `tf` ve `meal` için kapsanan âyetler, diğer türlerde boş liste; K-35 madde 5) | §4 örnekler, §8 |
| `anchors/invalid.jsonl` | dizgi | hata kodu: `BICIM`, `SURE_ARALIGI`, `AYET_ARALIGI`, `TERS_ARALIK`, `KANONIK_DEGIL`, `UZUNLUK` | §4 geçersiz tablo, §2 kurallar 1–9, hata önceliği (K-35 madde 1–2) |
| `anchors/compare.jsonl` | `[a, b]` | `-1`, `0`, `1` | §11 `compare` (Kur'an'da okuma sırası, K-35 madde 3) |
| `anchors/contains.jsonl` | `[dis, ic]` | `true` ya da `false` | §11 `contains` (K-35 madde 4) |
| `anchors/route.jsonl` | çapa (+ isteğe bağlı `sema`) | `native`, `web` | §11 rota tablosu ve şemalar (K-35 madde 6) |
| `offsets/offsets.jsonl` | metin | `codepoints`, `utf16`, `cp_to_utf16` çiftleri, `snap` (`[s,e)` → hizalanmış aralık) | §8; Test stratejisi §2 `of-0001` |
| `content-hash/hash.jsonl` | metin ve `op` (`ham` ya da `kanonik`) | `sha256`; `kanonik`te ayrıca `text` | §7 |

- §4'teki her geçerli ve geçersiz girdi birebir yer alır. Sınır satırları diziden programla üretilir: her sure için son âyet geçerli, bir fazlası `AYET_ARALIGI`; slug 64, derinlik 8 ve toplam 256 karakter sınırının iki yanı (`UZUNLUK`).
- Metinler sentetiktir: Latin harf, `\u` kaçışıyla yazılmış birleşen işaretler (ör. U+0302, U+0651, U+064E), en az bir BMP dışı karakter (Proje yapısı §1.2). `hash.jsonl` en az bir NFC olmayan Arapça dizi taşır (ör. bir harf + U+0651 + U+064E); bir uygulamanın metni sessizce normalize etmesi böyle yakalanır. Kur'an, meal, hadis ya da Risale metni vektöre konmaz.
- Dokümanın açıkça belirlemediği durum (ör. `p4` ile `p4:s2` sırası) vektöre konmaz; açık soru olarak aşama kaydına yazılır ya da `/karar` ile çözülür.
- **Kimlik düzeni.** `valid` ve `invalid` tek ortak `an-` dizisini paylaşır (bir kimlik iki dosyada birden bulunmaz); diğer dosyalar `cm-` (compare), `ct-` (contains), `ro-` (route), `of-` (offsets) ve `ch-` (content-hash) önekini taşır. Üretilen sınır satırları `an-s001…s114` (her surenin son âyeti ve bir fazlası) ve `an-u-*` (uzunluk ve sayı sınırları) kimliklidir. Hata önceliğini sınayan çok ihlalli satırlar `invalid` içinde `an-0092…an-0107` aralığındadır: bir dizgi birden çok kuralı bozar ve ilk bozulan denetimin kodu beklenir (K-35 madde 1).
- `uv run mutalaa export test-vectors [--check] [--kok <dizin>]` (İçerik hattı §4): hesaplanan alanları standart kitaplıkla üretir (`codepoints`, `utf16`, `cp_to_utf16`, `sha256`) ve `an-s…` ile `an-u-…` sınır satırlarını her çalıştırmada baştan kurar; dosyaları `id` sırasıyla, LF ve BOM'suz yazar. `--check` yazmadan diskle karşılaştırır, fark varsa 1 ile çıkar; `--kok` depo kökünü verir (verilmezse `pnpm-workspace.yaml` aranır; testler içindir). Ayrıştırıcıyı içe aktarmaz: beklenen değer ayrıştırıcıdan üretilirse vektör kendini doğrular. Görünmez ve birleşen karakterler (`Mn`, `Mc`, `Me`, `Cc`, `Cf`, `Zl`, `Zp`, `Zs`, `Co`, `Cs`, `Cn`), BMP dışı karakterler ve Arapça blokları `\u` kaçışıyla yazılır; ham U+FEFF, U+2028 gibi literal bulunmaz. Anlamsal beklentiler (`ref`, `canonical`, `unit`, `unit_span`, `ayahs`, hata kodları, sıra, kapsama, rota, `snap`, kanonik `text`) elle yazılır ve gözden geçirilir; üreteç bunlara dokunmaz, yalnız biçimini denetler. Biçim denetleyicisi (`@mutalaa/test-vectors`) klasör başına zorunlu alanları da sınar.
- **Bitti sayılır:** yedi dosya var; `pnpm --filter @mutalaa/test-vectors build` ve `uv run mutalaa export test-vectors --check` geçiyor.

### A04.3 · TypeScript: `packages/anchors` (`web-gelistirici`)
- §11'deki tipler ve işlevlerin tamamı: `parse`, `tryParse`, `format`, `compare`, `contains`, `toRoute`, `fromRoute`, `unitOf`, `coveredAyahs`, `toUnitSpan`, `cpToUtf16`, `utf16ToCp`, `snapSpan`, `AnchorError`. Belirsiz ayrıntılar K-35'e göredir: hata önceliği, `compare` okuma sırası, `contains` ekleri, ofset işlevlerinin hataları.
- Desenler §3'teki gibi: her tür için tek desen, `[0-9]` (asla `\d`), `q` deseninde ayrı grup adları. Desen önce gelir (sure, âyet, kelime en çok üç hane; aralık bitişi 0 olamaz). Anlam denetimi gömülü diziyle.
- Vitest koşucusu `anchors/*` ve `offsets/` dosyalarını `@mutalaa/test-vectors` paketinden okur. `content-hash` TS'de koşmaz: cihaz özeti hesaplamaz (Çapa şeması §7). Vitest kurulum dosyası koşu başında etkin yerel ayarı (`Intl.DateTimeFormat().resolvedOptions().locale`) yazar.
- **Bitti sayılır:** `pnpm --filter @mutalaa/anchors test` normal ve `LANG=tr_TR.UTF-8` ile yeşil; her geçerli vektörde `parse(format(r))` gidiş-dönüşü eşit.

### A04.4 · C#: `Mutalaa.Domain` (`sunucu-gelistirici`)
- `Mutalaa.Domain/Anchors`: `AnchorRef` (`sealed record`), `Parse`, `TryParse`, `ToString`, `IComparable<AnchorRef>`, `Contains`, `ToRoute` (isteğe bağlı şema alır), `UnitOf`, `ToUnitSpan`, `CoveredAyahs` (K-35 madde 5–6); desenler `[GeneratedRegex]` ve `RegexOptions.CultureInvariant` ile, `IgnoreCase` yok (Backend API §2, Çapa şeması §3).
- `Mutalaa.Domain/Text`: `ContentHash` (SHA-256, küçük harf onaltılık), kendi metnimizin ilk kayıt kanonikleştirmesi, kod noktası ofsetleri ve `snapSpan` karşılığı (Backend API §2); kod noktası işlemleri `Rune` ile. Kanonikleştirme sırası K-35 madde 7'dir: silinecek karakterler silinir; NFC; satır sonu (CRLF ve tek CR → U+000A), U+0020 ve U+0009 dizileri tek U+0020; baş ve son yalnız U+0020, U+0009, U+000A'dan kırpılır. `Trim` kullanılmaz, çünkü U+00A0'ı da keser; U+00A0 kenarda korunur, U+2028, U+2029 ve U+0085'e dokunulmaz.
- `Mutalaa.Domain.Tests` vektör koşucusu yedi dosyanın hepsini okur; vektörler ve `ayet-sayilari.json` test çıktısına bağlantılı dosya olarak kopyalanır (öneri). Koşucu kendi nesnesini `expected`'deki JSON biçimine çevirerek karşılaştırır. Rota dosyasında yalnız `ToRoute` sınanır; `fromRoute` yalnız TypeScript'tedir (§11 tablosu). Bütün vektör testleri `tr-TR` kültüründe ikinci kez koşar (Backend API §9).
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` yeşil; `tr-TR` koşumu ayrı test olarak görünüyor.

### A04.5 · Python: `mutalaa_pipeline.anchor` (`hat-gelistirici`)
- `pipeline/src/mutalaa_pipeline/anchor/capa.py`: `parse`, `try_parse`, `format` ve `str`, `sort_key`, `contains`, `to_route` (isteğe bağlı şema alır), `unit_of`, `to_unit_span`, `covered_ayahs` (K-35 madde 5–6); `dataclass(frozen=True)`; `re` ile `(?P<ad>…)` ve `[0-9]`.
- Aynı pakette `content_hash`, ilk kayıt kanonikleştirmesi ve `snap_span` (`anchor/metin.py`). Kanonikleştirme sırası K-35 madde 7'dir (silme, NFC, satır sonu ve boşluk); `strip()` kullanılmaz, çünkü U+00A0'ı da keser.
- `pipeline/tests/` koşucusu `@pytest.mark.parametrize` ile, kimlik olarak `id`; vektör klasörü depo kökünden bulunur (kök: `pnpm-workspace.yaml` dosyasının olduğu klasör; öneri). Python ofseti kod noktasıdır; `offsets/` dosyasından `codepoints` ve `snap` alanlarını, rota dosyasından yalnız `to_route` sonucunu sınar.
- **Bitti sayılır:** `uv run pytest` yeşil; `ruff` ve `mypy` temiz.

### A04.6 · Çapraz denetim
- `metin-denetcisi`: ofset ve `Mn` hizalaması, NFC olmayan dizinin korunması, kültür bağımsızlığı; vektörlerde gerçek dinî metin bulunmadığı.
- `test-yazari`: §2'deki dokuz anlam kuralının ve §4 tablolarının her satırının en az bir vektörde karşılığı var; eksik listesi boş.
- Bozma denemesi: bir vektörün beklenen değeri geçici olarak değiştirilir; üç koşucu da aynı `id`'yi kırmızı gösterir; değişiklik geri alınır.
- **Bitti sayılır:** iki rapor temiz ya da bulgular düzeltildi; bozma denemesi üç dilde yakalandı.

## Kabul ölçütleri
- [x] `shared/test-vectors/` altında yedi dosya var; `pnpm --filter @mutalaa/test-vectors build` geçiyor.
- [x] `shared/data/ayet-sayilari.json` kaynak adresi, alınma tarihi ve SHA-256 taşıyor; 114 eleman, toplam 6.236; üç kopya JSON'la aynı.
- [x] `pnpm --filter @mutalaa/anchors test` hem varsayılan hem `LANG=tr_TR.UTF-8` ile yeşil.
- [x] `dotnet test --solution server/Mutalaa.slnx` yeşil; vektörler `tr-TR` kültüründe de geçiyor.
- [x] `cd pipeline && uv run pytest` yeşil; `uv run mutalaa export test-vectors --check` 0 ile çıkıyor.
- [x] Çapa şeması §4 tablolarındaki her girdi vektörlerde birebir var (Doğrulama'daki döngü "EKSİK" yazmıyor).
- [x] Bozma denemesi üç dilde kırmızı; `metin-denetcisi` ve `test-yazari` raporları aşama kaydında.

## Doğrulama
```bash
pnpm --filter @mutalaa/test-vectors build
pnpm --filter @mutalaa/anchors test
LANG=tr_TR.UTF-8 pnpm --filter @mutalaa/anchors test
dotnet test --solution server/Mutalaa.slnx
(cd pipeline && uv run pytest && uv run ruff check . && uv run mypy src && uv run mutalaa export test-vectors --check)
for g in 'q:1:1' 'q:2:255:3-7' 'q:2:255-257' 'konu:tevhid' 'meal:elmalili:2:255@10-48' \
         'tf:elmalili:2-255-257:p3' 'tf:elmalili:2-255-255:p1' 'tf:elmalili:mukaddime:p4' \
         'tf:elmalili:sure-2-giris:p1' 'rn:sozler:soz-10:hakikat-3:p4:s2' 'rn:sozler:soz-10:hasiye-1:p1' \
         'h:tecrid:15' 'ht:naim:tecrid:15' 'k:kisas-i-enbiya:hz-ibrahim:p2' 'q:115:1' 'q:2:287' \
         'q:2:255:7-3' 'q:2:255:3-3' 'q:2:255-255' 'q:2:257-255' 'konu:tevhid@0-5' 'q:02:255' 'Q:2:255' \
         'q:2:255@0-10' 'rn:sozler:p4:p5' 'rn:sözler:p1' 'tf:elmalili:2-255:p3' 'meal:elmalili:2:255@48-10' \
         'h:muslim:2564a'; do
  grep -qF "\"$g\"" shared/test-vectors/anchors/*.jsonl || echo "EKSİK: $g"
done
git check-ignore -q shared/data/ayet-sayilari.json && echo "HATA: shared/data yok sayılıyor" || echo "shared/data izleniyor"
```

## Dikkat
- İçerik etiği: vektörlerde yalnız sentetik metin ve dokümandaki çapa dizgileri vardır. Âyet sayıları hafızadan yazılmaz ve elle düzeltilmez; üreteçle uyuşmazlıkta durulur ve kullanıcıya gösterilir.
- `\d` yasak, `[0-9]` kullanılır. .NET'te `RegexOptions.CultureInvariant`, Python'da `(?P<ad>…)`. `IgnoreCase` yok. Ayrıntı: `capa-gramer`.
- Ofset kanonik metnin kod noktasıdır, aralık yarı açıktır; UTF-16 dönüşümü yalnız `packages/anchors` API'siyle (§8). `@` Kur'an, konu ve cümle çapalarına eklenmez; `q:2:255:3-3` kanonik değildir.
- Vektör şartnamedir: kural değişecekse önce vektör eklenir ve üç dil aynı değişiklikte geçer. Ayrıntı: `test-vektoru`.
- BOM'lu JSONL Python'da ilk satırı bozar (Yerel geliştirme §10.2). `Mn` hizalaması üç dilin Unicode verisine dayanır ve üç çalışma zamanının Unicode sürümü farklıdır (aşama kaydı); vektörler yerleşik ve eski işaretlerle yazılır.
- Windows'ta `LANG=tr_TR.UTF-8` Node'un yerel ayarını değiştirmez; ICU yerel ayarı Windows kullanıcı ayarından alır. Türkçe Windows'ta iki koşu da `tr-TR`'dir; `LANG` karşıtlığı Linux CI'da (A08) görülür. Koşu başında yazılan iki yerel ayar aşama kaydına geçer. Ayrıntı: `windows-sorun`.
- `snapSpan` mobilde Hermes'te de çalışacak; düzenli ifade ya da Unicode özelliği desteği (`\p{Mn}`, adlı grup, ileri bakış) A21'deki öz testte ve A32 öz test ekranında sınanır. Hermes'te vektör koşumu bu aşamada yapılmadı.
- Vektör adları ve satır alanları Çapa şeması §11, Test stratejisi §2 ve Proje yapısı §1.2'de aynıdır (`id`, `input`, `expected`, `note`; geçerli çapada `expected.ref` ve `expected.canonical`). Python modülü `pipeline/src/mutalaa_pipeline/anchor/capa.py`.

## İnsan adımları
- Yok. Tanzil üst verisinin kullanım şartı belirsiz çıktı; kullanıcı kararı D1 (2026-10-24): devam ve kayda geçir. Tanzil'e gönderilecek soru [İ-08](../06-insan-adimlari.md) altındadır ve gönderim kullanıcıdadır.

## Çıktılar
- `shared/test-vectors/anchors/*.jsonl`, `offsets/offsets.jsonl`, `content-hash/hash.jsonl`; biçim denetleyicisinin alan denetimi
- `shared/data/ayet-sayilari.json`; `packages/anchors/src/generated/ayet-sayilari.ts`, `pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py`, `server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs`
- `packages/anchors/src/` ve testleri; `server/Mutalaa.Domain/Anchors/`, `server/Mutalaa.Domain/Text/ContentHash` ve kanonikleştirme; `server/tests/Mutalaa.Domain.Tests/` vektör koşucusu
- `pipeline/src/mutalaa_pipeline/anchor/` (`capa.py`, metin ve özet modülü), `export` altında `test-vectors` ve `ayet-sayilari` komutları, `pipeline/tests/` koşucusu

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A04-capa-ve-test-vektorleri.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## Aşama kaydı (kapanış 2026-10-25)

Plan kararları (2026-10-24): D1 Tanzil üst veri şartı belirsiz, devam ve kayda geçir; D2 belirsiz ayrıntılar [K-35](../../00-ozet/02-karar-defteri.md#k-35--çapa-api-ayrıntıları) ile kapatıldı; D3 Kur'an `compare` okuma sırasıyla; D4 `unitOf`, `toUnitSpan`, `coveredAyahs` üç dilde.

### Kabul ölçütleri ve kanıt

| Ölçüt | Kanıt |
|---|---|
| Yedi vektör dosyası | `shared/test-vectors/` altında 7 dosya, 560 satır: `anchors/valid` 151, `invalid` 192, `compare` 79, `contains` 78, `route` 21; `offsets` 11; `content-hash` 28. Biçim denetleyicisi: `pnpm --filter @mutalaa/test-vectors test` 180/180 |
| Âyet sayısı dizisi | `shared/data/ayet-sayilari.json` künyesi aşağıda; 114 eleman, toplam 6.236, 2. sure 286; üç kopya JSON'la aynı: `uv run mutalaa export ayet-sayilari --check` 0 |
| TypeScript | `pnpm --filter @mutalaa/anchors test` 568/568, hem normal hem `LANG=tr_TR.UTF-8` |
| C# | `dotnet test --solution server/Mutalaa.slnx` 1155/1155; her vektör `Invariant` ve `tr-TR` olarak ayrı test |
| Python | `cd pipeline && uv run pytest` 969 geçti; `ruff check`, `ruff format --check` ve `mypy` temiz; `uv run mutalaa export test-vectors --check` 0 |
| Bütün | `pnpm test`, `pnpm lint`, `pnpm typecheck` turbo ile sırasıyla 11, 7 ve 11 görev başarılı; `dotnet format server/Mutalaa.slnx --verify-no-changes` 0; kanca testleri (`node --test ".claude/hooks/test/*.test.mjs"`) 64/64 |
| Çapa şeması §4 kapsamı | Doğrulama bölümündeki 29 girdilik "EKSİK" döngüsü boş |
| Bozma denemesi ve raporlar | Aşağıda |

### Yerel ayar ve Unicode sürümleri

- Vitest kurulum dosyasının koşu başında yazdığı yerel ayar: normal koşuda `tr-TR`, `LANG=tr_TR.UTF-8` koşusunda da `tr-TR`. Windows'ta `LANG` Node'un yerel ayarını değiştirmedi (ICU Windows kullanıcı ayarını okur); karşıtlık Linux CI'da görülecek (A08).
- Unicode sürümleri: Node Unicode 17.0; Python 3.13 `unicodedata` 15.1.0; .NET 10.0.13 `Rune` kategori verisi en az Unicode 16 (kesin sürüm doğrulanamadı).
- Sürüm farkının sonucu: Node'da `Mn` olup Python'da `Mn` olmayan 75 kod noktası var (örn. U+0897), tersi 1. Vektörler bu yüzden eski ve yerleşik işaretlerle yazıldı (U+0302, U+0301, U+0307, U+0651, U+064E, U+1D167).

### Tanzil üst veri dosyası künyesi

| Alan | Değer |
|---|---|
| Kaynak | [`quran-data.xml`](https://tanzil.net/res/text/metadata/quran-data.xml); belge sayfası [Quran Metadata](https://tanzil.net/docs/quran_metadata) (sürüm 1.0); kaynak arastirmaci okuması 2026-10-24 |
| Alınma tarihi | 2026-10-24 |
| SHA-256 | `8867c1d88191472adec9db694b3cd9f135b1a2ef580574d32cf888dcb22c5c7a` |
| Lisans ve telif | dosyada `cc-by`; "(C) 2008-2009 Tanzil.info" |
| Boyut ve yer | 77.234 bayt; yalnız `.tmp/tanzil-ust-veri/` altında (git dışı); `data/raw` altında yok, kalıcı alım A11'de |
| Kullanım şartı | Belirsiz: dosyadaki CC BY 3.0 satırı ile SSS'deki "non-commercial purposes" cümlesi uzlaştırılamadı. Karar D1: devam ve kayıt; [lisans defteri §3.1](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md). Hukuki görüş değildir |

### Bozma denemesi (2026-10-25)

`anchors/compare.jsonl` içinde `cm-0001` beklenen değeri -1'den 1'e çevrildi. Dört koşu aynı kimliği kırmızı gösterdi: TypeScript `test/vectors.test.ts > cm-0001`, Python `test_compare[cm-0001]`, C# `Compare_Invariant(cm-0001)` ve `Compare_trTR(cm-0001)`. Dosya yedekten geri alındı (SHA-256 `f5bc6003…` aynı) ve dört takım yeniden yeşil oldu.

### Denetçi raporları (bulguların hepsi düzeltildi)

- `inceleyici`: engelleyici yok. Önemli bulgu: üretecin DOCTYPE reddi UTF-16 ya da NUL içeren girdiyle atlatılabiliyordu; üreteç bu girdileri de reddedecek biçimde düzeltildi.
- `metin-denetcisi`: engelleyici yok. Python `tfb` kolunda hata önceliği TypeScript ve C#'tan ayrışıyordu; düzeltildi, ortak öncelik vektörleri eklendi (`an-0092…an-0107`). Ham U+FEFF, U+2028 gibi literaller `\u` kaçışına çevrildi.
- `test-yazari` kapsam denetimi: §2 kuralları, §4 tabloları ve K-35 maddelerinin hepsi bir vektörde. Eklenenler: `contains` için sure, ad ve eser farkı; `compare` için eser farkı; `invalid` için öncelik satırları.
- `lisans-denetcisi`: engelleyici yok.
- Çapraz sınama: 2232 girdi üzerinde üç dilin kanonik biçimi, `unitOf`, `toUnitSpan`, `coveredAyahs`, rotalar, `compare` ve `contains` sonuçları eşit çıktı.

### Açık kalanlar ve devreden işler

- **A05 ve A21.** `snapSpan` yalnız hat ve sunucu tarafında hesaplanır, cihaz tablosu sabit kalır kararı A05/A21'de netleşmeli (açık not). Node ve Python `Mn` kümeleri farklıdır (yukarıda); normalizasyon vektörleri yerleşik, eski işaretlerle yazılmalıdır ([A05](./A05-arama-normalizasyonu.md) notu).
- **A08.** Turbo `test` görevine `LANG`/`LC_ALL` bildirilmeli (`"env": ["LANG","LC_ALL"]` ya da `passThroughEnv`); şu an `turbo run test` iki `LANG` için aynı özeti veriyor. NFC vektörleri Linux'ta yeniden koşmalı (.NET ICU/NLS ve Python Unicode sürümü farklı olabilir). `LANG` karşıtı koşu Linux CI'dadır.
- **A21 ve A32.** Hermes'te vektör koşumu; `\p{Mn}`, adlı grup ve ileri bakış desteğinin sınanması.
- **Hata türleri vektörle sabitlenmedi.** TypeScript `RangeError`; C# `InvalidOperationException`, `NotSupportedException`, `ArgumentException`, `ArgumentOutOfRangeException`; Python `ValueError`. Hata kodu (`AnchorError.code`) yalnız ayrıştırmada vardır. Vektörler yalnız "hata verir" sonucunu kilitler.
- **A11.** Tanzil üst veri kaynağı kartı ve kalıcı alım; kullanım şartı belirsiz ([lisans defteri §3.1](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md)).
- **A13 ve A34.** Tanzil atfı (CC BY 3.0) paketlenirken eklenir.
- **İ-08.** Mağaza yayını öncesi Tanzil'e 2. soru (üst veri dosyaları dahil); gönderim kullanıcıdadır ([taslak](../../yazismalar/tanzil-arama-metni.md)).

### Kullanıcıya bırakıldı

Emülatörde ya da cihazda doğrulama ve Hermes'te vektör koşumu bu aşamada yapılmadı (CLAUDE.md çalışma düzeni 3). Hermes sınaması A21 öz testi ve A32 öz test ekranındadır.

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A03](./A03-yerel-altyapi.md) · Sonraki: [A05](./A05-arama-normalizasyonu.md)
