# A05 · Arama normalizasyonu (TS, C#, Python)

> **Sürüm:** 1.2 · **Tarih:** 26 Ekim 2026 · **Durum:** Tamam (26 Ekim 2026) · **Bağlı kararlar:** [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A04](./A04-capa-ve-test-vektorleri.md) · **İnsan adımı:** yok
> **Ajanlar:** `web-gelistirici` · `sunucu-gelistirici` · `hat-gelistirici` · `test-yazari` · `metin-denetcisi` · `arastirmaci` · `inceleyici` · **Beceriler:** `test-vektoru` · `metin-butunlugu` · `windows-sorun` · **Tahmini oturum:** 2–3
> **Başlat:** `/asama A05`

## Amaç
Arama metninin normalizasyonu ([Arama](../../03-veri/05-arama-fts5.md) §1, `normalizer_version = 1.0`) üç dilde aynı sonucu verir ve `normalize/tr.jsonl`, `normalize/ar.jsonl` vektörleriyle kilitlenir. Türkçe dar ve geniş anahtar, Arapça `ar_norm`; Python'da ayrıca Türkçe gövde (`tr_stem`). Normalizasyon yalnız arama sütunları ve sorgu içindir; kanonik metin hiçbir adımda değişmez (K-26). Türkçe yerel ayar tuzakları (İ/ı) testle kapatılır.

## Okunacak belgeler
- [Arama (FTS5)](../../03-veri/05-arama-fts5.md): §1 normalleştirme belirtimi (tamamı), §7 AR-1, AR-2, AR-8
- [Yerel geliştirme](../../02-mimari/04-yerel-gelistirme.md): §10.1 Türkçe yerel ayar, §10.2 Unicode ve dosya biçimi
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §2 (örnek satırlar ve tuzak tablosu)
- [Proje yapısı](../../02-mimari/03-proje-yapisi.md): §1.2 vektör biçimi, §3 kodun yeri, §5 ESLint yerel ayar kuralı
- [Backend API](../../02-mimari/05-backend-api.md): §2 (`Text/`), §9 (`LowerTurkish` örneği)

## Kapsam
**Yapılır**
- Vektörler: `shared/test-vectors/normalize/tr.jsonl` (86 satır) ve `normalize/ar.jsonl` (62 satır); `export test-vectors` bu iki dosyanın yalnız biçimini, kaçışını ve kimlik düzenini denetler.
- `packages/search/src/normalize.ts`; `server/Mutalaa.Domain/Text/SearchNormalizer.cs`; `pipeline/src/mutalaa_pipeline/normalize/` (`turkish.py`, `arabic.py`, `unicode.py`). Üçünde de `normalizer_version` sabiti `1.0`.
- İç kesme listesi: `shared/data/ic-kesme.txt` ve `uv run mutalaa export ic-kesme [--check]` (TypeScript ve C# kopyaları: `packages/search/src/generated/ic-kesme.ts`, `server/Mutalaa.Domain/Text/IcKesme.g.cs`).
- Python'da `tr_stem` (`snowballstemmer` 3.1.1, K-36 madde 6) ve mypy taslakları `pipeline/stubs/`.

**Yapılmaz**
- FTS5 tabloları, `tr_stem_lex`, sorgu ayrıştırma ve `fts-query/query.jsonl` (A12). Ölçüm sorgu kümesi (A12, A28). TypeScript gövdeleyicisi (A12).
- Hat komutu `uv run mutalaa normalize --source …` ve G-NOR kapısının `qa run` içine bağlanması (A10).
- Arama §1.3 madde 4'teki kurallar (Farsça harfler, Arapça-Hint rakamlar, U+0610–U+061A ve U+08D3–U+08FF işaretleri; AR-8): 1.0'da değişmezler; kaynakta görülünce A10'da yeni küçük sürümle ele alınır.
- Arama §1.5 Arapça tablosundaki girdilerin Tanzil baytlarıyla vektör satırları (A10.7).
- Hermes'te `toLocaleLowerCase('tr')` ve `normalize` davranışı, öz test ekranı (A21, A32).

## Adımlar
### A05.1 · Doğrulanacaklar
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar (Arama §1.2 madde 7, AR-2):
  - Python için Türkçe Snowball gövdeleyicisi: paket adı, lisansı, son sürümü, Python 3.13 uyumu; PostgreSQL `turkish_stem` ile aynı Snowball algoritmasını kullanıp kullanmadığı.
  - TypeScript'te Türkçe Snowball uygulaması var mı (yalnız bilgi; `tr_stem_lex` kararı A12'de).
- Python kitaplığı seçilirse `/karar` ile yazılır; bağımlılık `uv add` ile eklenir.
- **Çözüldü (25 Ekim 2026):** Python gövdeleyicisi `snowballstemmer` 3.1.1 (BSD-3-Clause, saf Python) seçildi ve [K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 6'ya yazıldı; kaynaklar [PyPI](https://pypi.org/pypi/snowballstemmer/json) ve [Snowball Türkçe algoritması](https://snowballstem.org/algorithms/turkish/stemmer.html). TypeScript Snowball uygulaması kararı A12'dedir.
- **Bitti sayılır:** iki cevap kaynaklı aşama kaydında; seçim yapıldıysa karar defterinde.

### A05.2 · Vektörler
- Satır biçimi (Proje yapısı §1.2 alanlarıyla; Arama §1.5): Türkçe `{"id":"tr-0001","input":"Işık","expected":{"dar":"ışık","genis":"isik"},"note":"I → ı"}`; Arapça `{"id":"ar-0001","input":"…","expected":"…","note":"…"}`.
- Türkçe satırlar Arama §1.5'teki Türkçe tablodan birebir, Test stratejisi §2'deki örneklerden ve Proje yapısı §1.2'deki `IŞIK → isik` örneğinden gelir. §1.2 madde 1–6'nın her kuralı en az bir satırda; `a` + U+0302 + `lem` gibi NFC durumları `\u` kaçışıyla yazılır.
- Arapça satırlar `\u` kaçışıyla kurulan sentetik harf ve işaret dizileridir: her dizi bir kuralı sınamak için seçilmiş harf ve işaretlerden oluşur (ör. `\u0628\u0651\u064E`: harf, şedde, fetha; NFC olmayan sıra) ve âyet, Kur'an kelimesi ya da başka bir metinden alıntı değildir. §1.3 madde 1–3'ün ve §1.5 Arapça tablosunun "Sınanan kural" sütunundaki her kural en az bir sentetik satırla sınanır; işaretler hem NFC sırasında hem NFC olmayan sırada denenir. Beklenen değer kuralın kendisinden türetilir; `note` kuralı adlandırır.
- Arama §1.5 Arapça tablosundaki girdiler vektöre kopyalanmaz: Kur'an metnidir ve belgedeki yazım Tanzil'in baytlarıyla aynı değildir. Aynı girdilerin Tanzil baytlarıyla satırları A10.7'de betikle eklenir. Claude Code Arapça kelime ya da âyet yazmaz.
- İç kesme listesi `shared/data/ic-kesme.txt` (UTF-8, LF, satır başına bir girdi, geniş anahtarla): Arama §1.2 madde 3'teki örneklerle başlar: `kur'an`, `mu'min`, `ma'na`, `san'at`, `lem'a`, `i'caz`, `te'sir`. Külliyattan genişletme ve editör onayı sonraki hatlardadır (AR-1).
- **Bitti sayılır:** iki dosya biçim denetiminden geçiyor; Türkçe tablonun her girdisi birebir bir satırda (Doğrulama'daki döngü "EKSİK" yazmıyor); Arapça kuralların her biri en az bir sentetik satırda.

### A05.3 · TypeScript: `packages/search` (`web-gelistirici`)
- `src/normalize.ts`: Türkçe (dar, geniş), Arapça ve yazı sistemine göre bölme (§1.1): `normalizeTr`, `normalizeAr`, `searchKeys`, `splitScripts`; `NORMALIZER_VERSION = '1.0'`.
- Küçük harf: önce `I → ı`, `İ → i`, sonra kod noktası başına `toLowerCase()` (dize düzeyinde değil; K-36 madde 5). `toLocaleLowerCase`, `toLocaleUpperCase` ve tek argümanlı `localeCompare` kullanılmaz (ESLint kuralı, Proje yapısı §5).
- Geniş anahtar dar anahtardan, her sözcüğe ayrı türetilir: `ı → i`, NFD, yalnız U+0300–U+036F silinir, NFC (§1.2 madde 6).
- Vitest koşucusu iki dosyayı `@mutalaa/test-vectors` paketinden okur. Kurulum dosyası koşu başında etkin yerel ayarı (`Intl.DateTimeFormat().resolvedOptions().locale`) yazar.
- **Bitti sayılır:** `pnpm --filter @mutalaa/search test` varsayılan ve `LANG=tr_TR.UTF-8` ile yeşil; `pnpm lint` temiz.

### A05.4 · C#: `Mutalaa.Domain/Text` (`sunucu-gelistirici`)
- `SearchNormalizer` (Backend API §2): `LowerTurkish`, `SplitScripts`, `TurkishNarrow`, `TurkishWide`, `Arabic`, `Keys`; Türkçe küçük harf `LowerTurkish` örneğindeki açık eşlemeyle, `Rune` ile kod noktası başına (§9). Kültüre duyarlı çağrı CA1304…CA1311 ile derlemede durur.
- Klasör `Mutalaa.Domain/Text/` (Backend API §2, Proje yapısı §3, Arama §1).
- xUnit vektör testleri `Mutalaa.Domain.Tests` içinde; varsayılan ve `tr-TR` kültüründe.
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` yeşil; `tr-TR` koşumu görünür.

### A05.5 · Python: `mutalaa_pipeline.normalize` (`hat-gelistirici`)
- `unicode.py` (NFC, yazı sistemine göre bölme), `turkish.py` (dar ve geniş anahtar; kesme ve ek kuralları; iç kesme listesi `shared/data/ic-kesme.txt` dosyasından `encoding="utf-8"` ile okunur), `arabic.py`. `str.lower()` İ'yi iki kod noktasına çevirir; önce açık eşleme (Test stratejisi §2 tuzak tablosu).
- `tr_stem`: A05.1'de seçilen gövdeleyici (`snowballstemmer` 3.1.1) dar anahtarın her sözcüğünü `â î û` ön katlamasından sonra işler, sonuç geniş anahtara katlanır (K-36 madde 6). Değişmez kural: `tr_wide` ile `tr_stem` aynı sayıda sözcük taşır ve sıraları aynıdır (§1.2 madde 7); kural testle sınanır. Gövdeleyici doğrulanamazsa `tr_stem` A12'ye bırakılır ve aşama kaydına yazılır.
- pytest vektör koşucusu; `PYTHONUTF8=0` ile de koşar (Türkçe Windows'ta cp1254 hatalarını görmek için; Yerel geliştirme §10.1).
- **Bitti sayılır:** `uv run pytest` iki kipte yeşil; değişmez kural testi var.

### A05.6 · Çapraz denetim
- `metin-denetcisi`: işlevler girdiyi değiştirmez, yeni dize döndürür; İ ve ı eşlemesi her dilde ilk adım; NFC sırası; Arapça silme ve birleştirme sırası §1.3 ile aynı.
- Bozma denemesi: bir vektörün beklenen değeri geçici olarak değiştirilir; üç dil de aynı `id`'yi kırmızı gösterir; değişiklik geri alınır.
- **Bitti sayılır:** rapor temiz ya da bulgular düzeltildi; bozma denemesi üç dilde yakalandı.

## Kabul ölçütleri
- [x] `normalize/tr.jsonl` ve `normalize/ar.jsonl` var; biçim denetimi geçiyor; Arama §1.5 Türkçe tablosunun her girdisi birebir bir satırda (döngü "EKSİK" yazmıyor); Arapça kurallar (§1.3 madde 1–3, §1.5 "Sınanan kural" sütunu) sentetik dizilerle sınanıyor.
- [x] `pnpm --filter @mutalaa/search test` varsayılan ve `LANG=tr_TR.UTF-8` ile yeşil; `pnpm lint` yeşil.
- [x] `dotnet test --solution server/Mutalaa.slnx` yeşil; normalizasyon testleri `tr-TR` kültüründe de geçiyor.
- [x] `uv run pytest` hem varsayılan hem `PYTHONUTF8=0` ile yeşil.
- [x] Üç uygulamada `normalizer_version` `1.0`.
- [x] `tr_stem` ya Python'da uygulandı ve değişmez kural testi yeşil, ya da A12'ye devri aşama kaydında.
- [x] `shared/data/ic-kesme.txt` var ve UTF-8, BOM'suz, LF.
- [x] Bozma denemesi üç dilde kırmızı; `metin-denetcisi` raporu aşama kaydında.

## Doğrulama
```bash
pnpm --filter @mutalaa/test-vectors build
pnpm --filter @mutalaa/search test
LANG=tr_TR.UTF-8 pnpm --filter @mutalaa/search test
pnpm lint
dotnet test --solution server/Mutalaa.slnx
(cd pipeline && uv run pytest && PYTHONUTF8=0 uv run pytest && uv run ruff check . && uv run mypy src \
  && uv run mutalaa export ic-kesme --check && uv run mutalaa export test-vectors --check)
grep -c . shared/test-vectors/normalize/tr.jsonl shared/test-vectors/normalize/ar.jsonl
grep -rn "normalizer_version\|NORMALIZER_VERSION\|NormalizerVersion" packages/search/src server/Mutalaa.Domain/Text pipeline/src/mutalaa_pipeline/normalize
for g in 'Işık' 'İMAN' 'ışığın' "Kur'ân'ın" 'Kur’an’dan' "mü'min" "Lem'alar" "Sözler'de" 'âlem' 'alem' \
         'hâlâ' 'hala' 'Âl-i İmrân' 'a\u0302lem'; do
  grep -qF -e "\"input\":\"$g\"" -e "\"input\": \"$g\"" shared/test-vectors/normalize/tr.jsonl || echo "EKSİK: $g"
done
```
Döngü Arama §1.5 Türkçe tablosunun girdilerini arar; birleşen işaret dosyada `\u` kaçışıyla yazıldığı için son girdi kaçışlı biçimdedir.

## Dikkat
- Normalizasyon yalnız arama sütunları ve sorgu içindir; kanonik metin değişmez. Tanzil metnine NFC uygulanmaz (K-26). Ayrıntı: `metin-butunlugu`.
- Çıktıyı değiştiren her kural yeni bir küçük sürümdür ve bütün metin paketlerini yeniden ürettirir (Arama §1). Kural değişmeden önce o kuralı gösteren vektör eklenir; üç dil aynı değişiklikte geçer. Ayrıntı: `test-vektoru`.
- Türkçe küçük harf asla cihazın ya da işletim sisteminin yerel ayarına bırakılmaz. .NET'te `StringComparison.Ordinal` ve `CultureInfo.InvariantCulture`; düzenli ifadede `[0-9]`.
- Arapça kural sırası: önce silme (U+064B–U+065F, U+0670, U+06D6–U+06ED, U+0640), sonra harf birleştirme, sonra ayırıcılar (L, M, N dışı her kod noktası); yalın hemze korunur (§1.3 ve §1.5 tablosu; K-36 madde 4).
- Vektör biçimi: Arama §1.5 ve Test stratejisi §2 Türkçe satırı tek nesnede iki anahtarla verir (`expected: {dar, genis}`); dosyalar JSONL'dir (Proje yapısı §1.2).
- Unicode sürüm farkı (A04'ten, 2026-10-25): Python 3.13 `unicodedata` 15.1.0, Node Unicode 17.0, .NET ≥ 16. Node'da `Mn` olup Python'da `Mn` olmayan 75 kod noktası var (örn. U+0897), tersi 1. Normalizasyon vektörlerinde ve `Mn` temelli kurallarda (Arapça işaret silme, geniş anahtarda U+0300–U+036F) yalnız eski, yerleşik işaretler kullanılır (U+0302, U+0301, U+0307, U+0651, U+064E); yeni eklenen işaretler vektöre girmez. Bu fark artık karardır: kategori, küçük harf ve NFC çalışma zamanının verisinden gelir, sabit tablo tutulmaz ([K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 8). `snapSpan` normalizasyonla aynı `Mn` verisine dayanır: hat ve sunucu tarafında hesaplanır; cihaz tablosunun sabit kalıp kalmayacağı kararı A21'dedir. Ayrıntı: [A04 aşama kaydı](./A04-capa-ve-test-vektorleri.md#aşama-kaydı-kapanış-2026-10-25).
- Windows: Claude Code oturumunda `PYTHONUTF8=1` ayarlıdır; bu yüzden ikinci pytest koşusu `PYTHONUTF8=0` ile yapılır. `LANG=tr_TR.UTF-8` ise Windows'ta Node'un yerel ayarını değiştirmez (ICU Windows kullanıcı ayarını okur); Türkçe Windows'ta iki Vitest koşusu da `tr-TR`'dir ve karşıtlık Linux CI'da (A08) görülür. Koşu başında yazılan yerel ayarlar aşama kaydına geçer. Ayrıntı: `windows-sorun`.

## İnsan adımları
- Yok.

## Çıktılar
- `shared/test-vectors/normalize/tr.jsonl`, `normalize/ar.jsonl`; `shared/data/ic-kesme.txt`
- `packages/search/src/normalize.ts`, `src/generated/ic-kesme.ts` ve testleri (`test/normalize.test.ts`, `test/vectors.ts`, kurulum dosyası)
- `server/Mutalaa.Domain/Text/SearchNormalizer.cs`, `Text/IcKesme.g.cs` ve `server/tests/Mutalaa.Domain.Tests/NormalizeVectorTests.cs`
- `pipeline/src/mutalaa_pipeline/normalize/{unicode,turkish,arabic}.py`, `export/ic_kesme.py`, `pipeline/tests/` vektör, birim ve değişmez kural testleri; gövdeleyici bağımlılığı `snowballstemmer==3.1.1` (`pyproject.toml`, `uv.lock`) ve `pipeline/stubs/` mypy taslakları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A05-arama-normalizasyonu.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## Aşama kaydı (kapanış 2026-10-26)

Plan kararları (2026-10-25): D1 Arama §1'in açık bıraktığı ayrıntılar [K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) ile kapatıldı (adım sırası, kesme ve sözcük kuralları, biçim karakterleri, Arapça noktalama, küçük harf kod noktası başına); D2 Python gövdeleyicisi `snowballstemmer` 3.1.1 ve `â î û` ön katlaması; üç kullanıcı seçimi vardı. Reddedilen seçenekler K-36 "Değerlendirilen alternatifler" bölümünde kayıtlıdır: C uzantılı `PyStemmer`, `tr_stem`'i A12'ye bırakmak ve ön katlamasız gövdeleme. Sonuç: `tr_stem` bu aşamada Python'da uygulandı.

### Kabul ölçütleri ve kanıt

| Ölçüt | Kanıt |
|---|---|
| Vektör dosyaları | `shared/test-vectors/normalize/tr.jsonl` 86 satır, `ar.jsonl` 62 satır (`grep -c .`). Biçim denetleyicisi: `pnpm --filter @mutalaa/test-vectors test` 260/260; `uv run mutalaa export test-vectors --check` 0 |
| Türkçe tablo ve Arapça kurallar | Doğrulama bölümündeki "EKSİK" döngüsü boş. Arapça satırlar sentetik `\u` dizileridir; kural başına en az bir satır |
| TypeScript | `pnpm --filter @mutalaa/search test` 174/174, hem normal hem `LANG=tr_TR.UTF-8`; `pnpm lint` ve `pnpm typecheck` yeşil |
| C# | `dotnet test --solution server/Mutalaa.slnx` 1493/1493 (tr-TR ve Invariant testleri ayrı görünür); `dotnet format server/Mutalaa.slnx --verify-no-changes` 0 |
| Python | `cd pipeline && uv run pytest` 1344 geçti; `PYTHONUTF8=0 uv run pytest` 1344 geçti; `ruff check`, `ruff format --check` ve `mypy src` temiz |
| İç kesme listesi | `shared/data/ic-kesme.txt` var (UTF-8, BOM'suz, LF, 7 girdi); `uv run mutalaa export ic-kesme --check` 0 |
| Sürüm sabiti | TypeScript `NORMALIZER_VERSION`, C# `SearchNormalizer.NormalizerVersion`, Python `NORMALIZER_VERSION`: üçünde `1.0` |
| `tr_stem` | Python'da uygulandı (`snowballstemmer==3.1.1`); `tr_wide` ve `tr_stem` aynı sayıda sözcük ve aynı sıra: `pipeline/tests/test_tr_stem.py` |
| Bozma denemesi ve raporlar | Aşağıda |

### Yerel ayar ve Unicode sürümleri

- Vitest kurulum dosyasının koşu başında yazdığı yerel ayar: iki koşuda da `[search] locale=tr-TR unicode=17.0`. Windows'ta `LANG` Node'un yerel ayarını değiştirmedi (ICU Windows kullanıcı ayarını okur); karşıtlık Linux CI'da görülecek (A08).
- .NET ortamı: Windows, .NET 10.0.13, ICU kipi, `CurrentCulture` tr-TR.
- Unicode sürümleri: Python 3.13 `unicodedata` 15.1.0; Node 17.0; .NET çalışma zamanı kategori tablosu (kesin sürüm doğrulanmadı). Kural: [K-36](../../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) madde 8.

### Çapraz sınama

23.438 girdi (tohum 20261025) üzerinde üç dilin anahtarları karşılaştırıldı; sonunda fark yok. Bulunan tek fark: .NET `string.Normalize` U+FFFE'yi reddediyordu, TypeScript ve Python reddetmiyordu. Karar K-36 madde 1'e yazıldı (Cn ve Co silinmez, ayırıcıdır; C# NFC'yi U+FFFE sınırlarında parçalar), vektörler `tr-0080`, `tr-0081` ve `ar-0061` ile kilitlendi ve C# düzeltildi.

### Bozma denemesi ve denetçi raporları

**Bozma denemesi (2026-10-26).** `normalize/tr.jsonl` içinde `tr-0001` beklenen geniş anahtarı `isik` iken `isix` yapıldı. Dört koşu aynı kimliği kırmızı gösterdi: TypeScript `test/normalize.test.ts > normalize/tr.jsonl > tr-0001` (1 başarısız, 173 geçti), Python `test_turkce_vektoru[tr-0001]` (1 başarısız, 151 geçti), C# `Turkish_Invariant(tr-0001)` ve `Turkish_trTR(tr-0001)` (2 başarısız, 1491 geçti). Vektör denetleyicisi ve `export test-vectors --check` değer bozmayı yakalamaz (yalnız biçim, kaçış ve kimlik denetler; değerler elle yazılır); yakalayan üç dilin uygulama testleridir. Dosya yedekten geri alındı (SHA-256 `667f3fb3…` aynı) ve üç takım yeniden yeşil oldu: 174, 1344 ve 1493.

**Denetçi raporları (bulguların hepsi işlendi ya da aşağıda devredildi).**
- `metin-denetcisi`: engelleyici yok. Önemli iki bulgu: (1) C# `string.Normalize` U+FFFE'de `ArgumentException` atıyordu (çapraz sınama aynı hatayı bağımsız buldu; 0..U+10FFFF taramasında vekil olmayan kod noktalarından yalnız U+FFFE patlıyor); NFC U+FFFE sınırlarında parçalanarak düzeltildi, K-36 madde 1'e yazıldı, vektörler `tr-0080`, `tr-0081`, `ar-0061` ve diğer Cn/Co/Lt/Lm satırları (`tr-0082…0086`, `ar-0062`) eklendi. (2) `shared/test-vectors/scripts/check-lib.mjs` kaynağında ham U+0300 ve U+036F vardı; `\u` kaçışına çevrildi ve betik klasörü ham birleşen işaret için tarandı. Öneriler: C# `char` yinelemeleri `Rune`'a çevrildi, TypeScript `replaceAll` düzenli ifadeye çevrildi, belge farkları `belge-bekcisi` ile işlendi. Elle türetme: 65 riskli satır K-36'dan yürütüldü, çelişki yok. Arapça vektörlerde âyet ya da kaynak metin yok; yalnız sentetik harf-işaret dizileri (iki üç harfli diziler rastlantıyla gerçek sözcüğe benzeyebilir, kaynak metin değildir).
- `lisans-denetcisi`: engelleyici yok. `snowballstemmer` 3.1.1 BSD-3-Clause, saf Python, yalnız hatta çalışır, ürüne girmez; tekerlekte örnek veri yok; `uv.lock` yalnız bu paketi ekliyor; PyStemmer kurulu değil. Eksik: Teknoloji yığını §2.4 satırı (eklendi). Hukuki görüş değildir.
- `inceleyici`: engelleyici ve önemli bulgu yok. Kendi 30.000 girdilik sınamasında üç dil aynı özeti verdi. Uygulanan öneriler: TypeScript'te geçersiz anahtarda `RangeError`, `searchKeys` içinde tek ön adım, C#'ta U+FFFF, U+1FFFE, U+10FFFF, U+FDD0, U+FFFD ve U+E0001 testleri, `Environment_is_recorded` testinin gerçek bir şeyi doğrulaması. Devredilenler aşağıda.

### Açık kalanlar ve devreden işler

- **A12.** Snowball bazı sözcükleri agresif keser (`kuran` → `kura`, `mümin` → `mum`, `iman` → `ima`); `tr_stem` etkisi arama ölçümüyle gözden geçirilir. TypeScript gövdeleyicisi ve `tr_stem_lex` kararı da A12'dedir (AR-2).
- **A08 ve A21.** Python Unicode 15.1 ile Node ve .NET'in daha yeni harfleri (U+A7CB–U+A7CD, U+A7DA–U+A7DC, U+1C89 …) paket üretimi ile cihaz sorgusu arasında ayrışabilir; Linux CI (A08) ve Hermes (A21) gözler. Hermes `normalize` ve `\p{…}` desteği A21 öz testindedir.
- **Eşsiz vekil.** JSONL'de yazılamaz; üç dilin birim testleriyle kilitlidir.
- **AR-1.** En uzun iç kesme eşleşmesi birim testlerindedir; liste büyüyünce vektöre taşınır. Liste külliyattan genişletilir, editör onayı sonraki hatlardadır.
- **A21.** `snapSpan` ve `Mn` kararı (cihaz tablosu).
- **A10.** AR-8 (Farsça harfler, Arapça-Hint rakamlar, silme aralığı dışındaki işaretler); `normalize` hat komutu ve G-NOR.
- **A10.7.** Arama §1.5 Arapça tablosunun Tanzil baytlarıyla vektör satırları.
- **A12 ve A14.** Normalleştiriciler girdi uzunluğunu sınırlamaz (6 MB'lık girdi TypeScript'te yaklaşık 3,7 sn, doğrusal maliyet). Sorgu girişi kabul eden uç nokta ve arama ekranı uzunluğu sınırlar (öneri 1–4 KB) ve bunu bir testle kilitler.
- **A08.** Linux CI'da .NET'in ICU/NLS durumu ve U+FFFE gibi değişmez karakterlerin davranışı yeniden doğrulanır; dağıtım imajında ICU bulunmalı (`InvariantGlobalization` bilerek kapalı). `Environment_is_recorded` testi .NET'in iç `GlobalizationMode` tipine yansımayla bakar; bir çalışma zamanı sürümünde yanlış kırmızı verirse tanı çıktısına indirilir.
- **Küçük işler (öneri, engelleyici değil).** Python `govde_sozcuk` önbelleği uzun sözcükleri de tutar (65536 giriş; > 64 karakterlik sözcük önbelleğe alınmayabilir); `ic_kesme_coz` ile `export/ic_kesme.py` aynı liste kuralının iki ayrı uygulamasıdır (biri BOM, yineleme ve sıra denetler, öbürü yalnız CR ve desen), `--check` ile korunur; `turkish.py` kök bulucusunun `FileNotFoundError` dalı testsizdir.
- **A34.** `THIRD_PARTY_NOTICES` mağaza öncesi (`snowballstemmer` BSD bildirimi dahil; hukuki görüş değildir).

### Kullanıcıya bırakıldı

Hermes'te vektör koşumu bu aşamada yapılmadı (CLAUDE.md çalışma düzeni 3); A21 öz testi ve A32 öz test ekranındadır.

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A04](./A04-capa-ve-test-vektorleri.md) · Sonraki: [A06](./A06-lisans-defteri-ve-enumlar.md)
