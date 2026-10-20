# A05 · Arama normalizasyonu (TS, C#, Python)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-17](../../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
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
- Vektörler: `shared/test-vectors/normalize/tr.jsonl` ve `normalize/ar.jsonl`.
- `packages/search/src/normalize.ts`; `server/Mutalaa.Domain/Text/SearchNormalizer`; `pipeline/src/mutalaa_pipeline/normalize/` (`turkish.py`, `arabic.py`, `unicode.py`). Üçünde de `normalizer_version` sabiti `1.0`.
- İç kesme listesinin başlangıcı: `shared/data/ic-kesme.txt`.
- Python'da `tr_stem` (gövdeleyici doğrulanırsa).

**Yapılmaz**
- FTS5 tabloları, `tr_stem_lex`, sorgu ayrıştırma ve `fts-query/query.jsonl` (A12). Ölçüm sorgu kümesi (A12, A28).
- Hat komutu `uv run mutalaa normalize --source …` ve G-NOR kapısının `qa run` içine bağlanması (A10).
- Arama §1.3 madde 4'teki öneri kuralları (Farsça harfler, Arapça-Hint rakamlar; AR-8): kaynakta görülünce A10'da.
- Arama §1.5 Arapça tablosundaki girdilerin Tanzil baytlarıyla vektör satırları (A10.7).
- Hermes'te `toLocaleLowerCase('tr')` ve `normalize` davranışı, öz test ekranı (A21, A32).

## Adımlar
### A05.1 · Doğrulanacaklar
- `arastirmaci` resmî kaynaktan bağlantısıyla raporlar (Arama §1.2 madde 7, AR-2):
  - Python için Türkçe Snowball gövdeleyicisi: paket adı, lisansı, son sürümü, Python 3.13 uyumu; PostgreSQL `turkish_stem` ile aynı Snowball algoritmasını kullanıp kullanmadığı.
  - TypeScript'te Türkçe Snowball uygulaması var mı (yalnız bilgi; `tr_stem_lex` kararı A12'de).
- Python kitaplığı seçilirse `/karar` ile yazılır; bağımlılık `uv add` ile eklenir.
- **Bitti sayılır:** iki cevap kaynaklı aşama kaydında; seçim yapıldıysa karar defterinde.

### A05.2 · Vektörler
- Satır biçimi (Proje yapısı §1.2 alanlarıyla; Arama §1.5): Türkçe `{"id":"tr-0001","input":"Işık","expected":{"dar":"ışık","genis":"isik"},"note":"I → ı"}`; Arapça `{"id":"ar-0001","input":"…","expected":"…","note":"…"}`.
- Türkçe satırlar Arama §1.5'teki Türkçe tablodan birebir, Test stratejisi §2'deki örneklerden ve Proje yapısı §1.2'deki `IŞIK → isik` örneğinden gelir. §1.2 madde 1–6'nın her kuralı en az bir satırda; `a` + U+0302 + `lem` gibi NFC durumları `\u` kaçışıyla yazılır.
- Arapça satırlar `\u` kaçışıyla kurulan sentetik harf ve işaret dizileridir: her dizi bir kuralı sınamak için seçilmiş harf ve işaretlerden oluşur (ör. `\u0628\u0651\u064E`: harf, şedde, fetha; NFC olmayan sıra) ve âyet, Kur'an kelimesi ya da başka bir metinden alıntı değildir. §1.3 madde 1–3'ün ve §1.5 Arapça tablosunun "Sınanan kural" sütunundaki her kural en az bir sentetik satırla sınanır; işaretler hem NFC sırasında hem NFC olmayan sırada denenir. Beklenen değer kuralın kendisinden türetilir; `note` kuralı adlandırır.
- Arama §1.5 Arapça tablosundaki girdiler vektöre kopyalanmaz: Kur'an metnidir ve belgedeki yazım Tanzil'in baytlarıyla aynı değildir. Aynı girdilerin Tanzil baytlarıyla satırları A10.7'de betikle eklenir. Claude Code Arapça kelime ya da âyet yazmaz.
- İç kesme listesi `shared/data/ic-kesme.txt` (UTF-8, LF, satır başına bir girdi, geniş anahtarla): Arama §1.2 madde 3'teki örneklerle başlar: `kur'an`, `mu'min`, `ma'na`, `san'at`, `lem'a`, `i'caz`, `te'sir`. Külliyattan genişletme ve editör onayı sonraki hatlardadır (AR-1).
- **Bitti sayılır:** iki dosya biçim denetiminden geçiyor; Türkçe tablonun her girdisi birebir bir satırda (Doğrulama'daki döngü "EKSİK" yazmıyor); Arapça kuralların her biri en az bir sentetik satırda.

### A05.3 · TypeScript: `packages/search` (`web-gelistirici`)
- `src/normalize.ts`: Türkçe (dar, geniş), Arapça ve yazı sistemine göre bölme (§1.1); `NORMALIZER_VERSION = '1.0'`.
- Küçük harf: önce `I → ı`, `İ → i`, sonra `toLowerCase()`. `toLocaleLowerCase`, `toLocaleUpperCase` ve tek argümanlı `localeCompare` kullanılmaz (ESLint kuralı, Proje yapısı §5).
- Geniş anahtar dar anahtardan türetilir: `ı → i`, NFD, U+0300–U+036F silinir, NFC (§1.2 madde 6).
- Vitest koşucusu iki dosyayı `@mutalaa/test-vectors` paketinden okur. Kurulum dosyası koşu başında etkin yerel ayarı (`Intl.DateTimeFormat().resolvedOptions().locale`) yazar.
- **Bitti sayılır:** `pnpm --filter @mutalaa/search test` varsayılan ve `LANG=tr_TR.UTF-8` ile yeşil; `pnpm lint` temiz.

### A05.4 · C#: `Mutalaa.Domain/Text` (`sunucu-gelistirici`)
- `SearchNormalizer` (Backend API §2); Türkçe küçük harf `LowerTurkish` örneğindeki açık eşlemeyle (§9). Kültüre duyarlı çağrı CA1304…CA1311 ile derlemede durur.
- Klasör `Mutalaa.Domain/Text/` (Backend API §2, Proje yapısı §3, Arama §1).
- xUnit vektör testleri `Mutalaa.Domain.Tests` içinde; varsayılan ve `tr-TR` kültüründe.
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` yeşil; `tr-TR` koşumu görünür.

### A05.5 · Python: `mutalaa_pipeline.normalize` (`hat-gelistirici`)
- `unicode.py` (NFC, yazı sistemine göre bölme), `turkish.py` (dar ve geniş anahtar; kesme ve ek kuralları; iç kesme listesi `shared/data/ic-kesme.txt` dosyasından `encoding="utf-8"` ile okunur), `arabic.py`. `str.lower()` İ'yi iki kod noktasına çevirir; önce açık eşleme (Test stratejisi §2 tuzak tablosu).
- `tr_stem`: A05.1'de seçilen gövdeleyici dar anahtarın her sözcüğünü işler, sonuç geniş anahtara katlanır. Değişmez kural: `tr_wide` ile `tr_stem` aynı sayıda sözcük taşır ve sıraları aynıdır (§1.2 madde 7); kural testle sınanır. Gövdeleyici doğrulanamazsa `tr_stem` A12'ye bırakılır ve aşama kaydına yazılır.
- pytest vektör koşucusu; `PYTHONUTF8=0` ile de koşar (Türkçe Windows'ta cp1254 hatalarını görmek için; Yerel geliştirme §10.1).
- **Bitti sayılır:** `uv run pytest` iki kipte yeşil; değişmez kural testi var.

### A05.6 · Çapraz denetim
- `metin-denetcisi`: işlevler girdiyi değiştirmez, yeni dize döndürür; İ ve ı eşlemesi her dilde ilk adım; NFC sırası; Arapça silme ve birleştirme sırası §1.3 ile aynı.
- Bozma denemesi: bir vektörün beklenen değeri geçici olarak değiştirilir; üç dil de aynı `id`'yi kırmızı gösterir; değişiklik geri alınır.
- **Bitti sayılır:** rapor temiz ya da bulgular düzeltildi; bozma denemesi üç dilde yakalandı.

## Kabul ölçütleri
- [ ] `normalize/tr.jsonl` ve `normalize/ar.jsonl` var; biçim denetimi geçiyor; Arama §1.5 Türkçe tablosunun her girdisi birebir bir satırda (döngü "EKSİK" yazmıyor); Arapça kurallar (§1.3 madde 1–3, §1.5 "Sınanan kural" sütunu) sentetik dizilerle sınanıyor.
- [ ] `pnpm --filter @mutalaa/search test` varsayılan ve `LANG=tr_TR.UTF-8` ile yeşil; `pnpm lint` yeşil.
- [ ] `dotnet test --solution server/Mutalaa.slnx` yeşil; normalizasyon testleri `tr-TR` kültüründe de geçiyor.
- [ ] `uv run pytest` hem varsayılan hem `PYTHONUTF8=0` ile yeşil.
- [ ] Üç uygulamada `normalizer_version` `1.0`.
- [ ] `tr_stem` ya Python'da uygulandı ve değişmez kural testi yeşil, ya da A12'ye devri aşama kaydında.
- [ ] `shared/data/ic-kesme.txt` var ve UTF-8, BOM'suz, LF.
- [ ] Bozma denemesi üç dilde kırmızı; `metin-denetcisi` raporu aşama kaydında.

## Doğrulama
```bash
pnpm --filter @mutalaa/test-vectors build
pnpm --filter @mutalaa/search test
LANG=tr_TR.UTF-8 pnpm --filter @mutalaa/search test
pnpm lint
dotnet test --solution server/Mutalaa.slnx
(cd pipeline && uv run pytest && PYTHONUTF8=0 uv run pytest && uv run ruff check . && uv run mypy src)
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
- Arapça kural sırası: önce silme (U+064B–U+065F, U+0670, U+06D6–U+06ED, U+0640), sonra harf birleştirme, sonra noktalama; yalın hemze korunur (§1.3 ve §1.5 tablosu).
- Vektör biçimi: Arama §1.5 ve Test stratejisi §2 Türkçe satırı tek nesnede iki anahtarla verir (`expected: {dar, genis}`); dosyalar JSONL'dir (Proje yapısı §1.2).
- Windows: Claude Code oturumunda `PYTHONUTF8=1` ayarlıdır; bu yüzden ikinci pytest koşusu `PYTHONUTF8=0` ile yapılır. `LANG=tr_TR.UTF-8` ise Windows'ta Node'un yerel ayarını değiştirmez (ICU Windows kullanıcı ayarını okur); Türkçe Windows'ta iki Vitest koşusu da `tr-TR`'dir ve karşıtlık Linux CI'da (A08) görülür. Koşu başında yazılan yerel ayarlar aşama kaydına geçer. Ayrıntı: `windows-sorun`.

## İnsan adımları
- Yok.

## Çıktılar
- `shared/test-vectors/normalize/tr.jsonl`, `normalize/ar.jsonl`; `shared/data/ic-kesme.txt`
- `packages/search/src/normalize.ts` ve testleri
- `server/Mutalaa.Domain/Text/SearchNormalizer` ve `Mutalaa.Domain.Tests` içindeki vektör testleri
- `pipeline/src/mutalaa_pipeline/normalize/{unicode,turkish,arabic}.py`, `pipeline/tests/` vektör ve değişmez kural testleri; seçildiyse gövdeleyici bağımlılığı (`pyproject.toml`, `uv.lock`)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A05-arama-normalizasyonu.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A04](./A04-capa-ve-test-vektorleri.md) · Sonraki: [A06](./A06-lisans-defteri-ve-enumlar.md)
