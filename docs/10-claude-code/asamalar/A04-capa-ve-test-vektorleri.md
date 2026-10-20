# A04 · Çapa grameri ve ortak test vektörleri (TS, C#, Python)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek)
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
- `arastirmaci` Tanzil üst veri dosyasının resmî adresini, biçimini ve kullanım şartını doğrular. Adres hafızadan yazılmaz; Doğrulanacak.
- `hat-gelistirici` dosyayı `.tmp/tanzil-ust-veri/` altına indirir ve SHA-256'sını hesaplar. `data/raw` altına yazılmaz; kalıcı alım A11'dedir.
- Üretici (öneri: `uv run mutalaa export ayet-sayilari --kaynak <dosya>`) sure başına âyet sayısını dosyadan okur ve `shared/data/ayet-sayilari.json` yazar (öneri biçim: `kaynak_url`, `alinma_tarihi`, `sha256`, 114 elemanlı `sayilar`). Aynı komut üç kopyayı üretir (adlar öneri): `packages/anchors/src/generated/ayet-sayilari.ts`, `pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py`, `server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs`. Üretilmiş dosyalar elle düzenlenmez.
- Her dilde test: 114 eleman, toplam 6.236, 2. sure 286 (Çapa şeması §2 ve §4); kopya JSON'la aynı.
- **Bitti sayılır:** JSON ve üç kopya depoda; üç dilin dizi testi yeşil.

### A04.2 · Vektörler
- Satır biçimi Proje yapısı §1.2'deki alanlarla: `id`, `input`, `expected`, isteğe bağlı `note` (öneri ayrıntı aşağıda). Dosyalar JSONL, UTF-8, BOM yok, LF; satırlar `id` sırasıyla.

| Dosya | `input` | `expected` | Dayanak |
|---|---|---|---|
| `anchors/valid.jsonl` | çapa dizgisi | `ref` (§11 TS nesnesi `{anchor, span?}`), `canonical`, `unit` (`unitOf`), `unit_span` (`toUnitSpan`), `ayahs` (`coveredAyahs`; yalnız `qa`, `tf`, `meal`) | §4 örnekler, §8 |
| `anchors/invalid.jsonl` | dizgi | hata kodu: `BICIM`, `SURE_ARALIGI`, `AYET_ARALIGI`, `TERS_ARALIK`, `KANONIK_DEGIL`, `UZUNLUK` | §4 geçersiz tablo, §2 kurallar 1–9 |
| `anchors/compare.jsonl` | `[a, b]` | `-1`, `0`, `1` | §11 `compare` |
| `anchors/contains.jsonl` | `[dis, ic]` | `true` ya da `false` | §11 `contains` |
| `anchors/route.jsonl` | çapa (+ isteğe bağlı `sema`) | `native`, `web` | §11 rota tablosu ve şemalar |
| `offsets/offsets.jsonl` | metin | `codepoints`, `utf16`, `cp_to_utf16` çiftleri, `snap` (`[s,e)` → hizalanmış aralık) | §8; Test stratejisi §2 `of-0001` |
| `content-hash/hash.jsonl` | metin ve `op` (`ham` ya da `kanonik`) | `sha256`; `kanonik`te ayrıca `text` | §7 |

- §4'teki her geçerli ve geçersiz girdi birebir yer alır. Sınır satırları diziden programla üretilir: her sure için son âyet geçerli, bir fazlası `AYET_ARALIGI`; slug 64, derinlik 8 ve toplam 256 karakter sınırının iki yanı (`UZUNLUK`).
- Metinler sentetiktir: Latin harf, `\u` kaçışıyla yazılmış birleşen işaretler (ör. U+0302, U+0651, U+064E), en az bir BMP dışı karakter (Proje yapısı §1.2). `hash.jsonl` en az bir NFC olmayan Arapça dizi taşır (ör. bir harf + U+0651 + U+064E); bir uygulamanın metni sessizce normalize etmesi böyle yakalanır. Kur'an, meal, hadis ya da Risale metni vektöre konmaz.
- Dokümanın açıkça belirlemediği durum (ör. `p4` ile `p4:s2` sırası) vektöre konmaz; açık soru olarak aşama kaydına yazılır ya da `/karar` ile çözülür.
- `uv run mutalaa export test-vectors` (İçerik hattı §4): hesaplanan alanları standart kitaplıkla üretir (SHA-256, UTF-16 uzunluğu ve ofsetleri), dosyaları `id` sırasıyla, LF ve BOM'suz yazar; `--check` kipi fark varsa 1 ile çıkar (öneri). Birleşen, biçim ve BMP dışı karakterler `\u` kaçışıyla, diğerleri düz yazılır (öneri; gözden geçirme ve `grep` için). Anlamsal beklentiler (geçerlilik, sıra, kapsama, rota) elle yazılır ve gözden geçirilir. Biçim denetleyicisi (`@mutalaa/test-vectors`) klasör başına zorunlu alanları da sınar (öneri).
- **Bitti sayılır:** yedi dosya var; `pnpm --filter @mutalaa/test-vectors build` ve `uv run mutalaa export test-vectors --check` geçiyor.

### A04.3 · TypeScript: `packages/anchors` (`web-gelistirici`)
- §11'deki tipler ve işlevlerin tamamı: `parse`, `tryParse`, `format`, `compare`, `contains`, `toRoute`, `fromRoute`, `unitOf`, `coveredAyahs`, `toUnitSpan`, `cpToUtf16`, `utf16ToCp`, `snapSpan`, `AnchorError`.
- Desenler §3'teki gibi: her tür için tek desen, `[0-9]` (asla `\d`), `q` deseninde ayrı grup adları. Anlam denetimi gömülü diziyle.
- Vitest koşucusu `anchors/*` ve `offsets/` dosyalarını `@mutalaa/test-vectors` paketinden okur. `content-hash` TS'de koşmaz: cihaz özeti hesaplamaz (Çapa şeması §7). Vitest kurulum dosyası koşu başında etkin yerel ayarı (`Intl.DateTimeFormat().resolvedOptions().locale`) yazar.
- **Bitti sayılır:** `pnpm --filter @mutalaa/anchors test` normal ve `LANG=tr_TR.UTF-8` ile yeşil; her geçerli vektörde `parse(format(r))` gidiş-dönüşü eşit.

### A04.4 · C#: `Mutalaa.Domain` (`sunucu-gelistirici`)
- `Mutalaa.Domain/Anchors`: `AnchorRef` (`sealed record`), `Parse`, `TryParse`, `ToString`, `IComparable<AnchorRef>`, `Contains`, `ToRoute`; desenler `[GeneratedRegex]` ve `RegexOptions.CultureInvariant` ile, `IgnoreCase` yok (Backend API §2, Çapa şeması §3).
- `Mutalaa.Domain/Text`: `ContentHash` (SHA-256, küçük harf onaltılık), kendi metnimizin ilk kayıt kanonikleştirmesi (§7 adım 1–3), kod noktası ofsetleri ve `snapSpan` karşılığı (Backend API §2); kod noktası işlemleri `Rune` ile.
- `Mutalaa.Domain.Tests` vektör koşucusu yedi dosyanın hepsini okur; vektörler ve `ayet-sayilari.json` test çıktısına bağlantılı dosya olarak kopyalanır (öneri). Koşucu kendi nesnesini `expected`'deki JSON biçimine çevirerek karşılaştırır. Rota dosyasında yalnız `ToRoute` sınanır; `fromRoute` yalnız TypeScript'tedir (§11 tablosu). Bütün vektör testleri `tr-TR` kültüründe ikinci kez koşar (Backend API §9).
- **Bitti sayılır:** `dotnet test --solution server/Mutalaa.slnx` yeşil; `tr-TR` koşumu ayrı test olarak görünüyor.

### A04.5 · Python: `mutalaa_pipeline.anchor` (`hat-gelistirici`)
- `pipeline/src/mutalaa_pipeline/anchor/capa.py`: `parse`, `try_parse`, `format` ve `str`, `sort_key`, `contains`, `to_route`; `dataclass(frozen=True)`; `re` ile `(?P<ad>…)` ve `[0-9]`.
- Aynı pakette `content_hash`, ilk kayıt kanonikleştirmesi ve `snap_span` (dosya adı öneri: `anchor/metin.py`).
- `pipeline/tests/` koşucusu `@pytest.mark.parametrize` ile, kimlik olarak `id`; vektör klasörü depo kökünden bulunur (kök: `pnpm-workspace.yaml` dosyasının olduğu klasör; öneri). Python ofseti kod noktasıdır; `offsets/` dosyasından `codepoints` ve `snap` alanlarını, rota dosyasından yalnız `to_route` sonucunu sınar.
- **Bitti sayılır:** `uv run pytest` yeşil; `ruff` ve `mypy` temiz.

### A04.6 · Çapraz denetim
- `metin-denetcisi`: ofset ve `Mn` hizalaması, NFC olmayan dizinin korunması, kültür bağımsızlığı; vektörlerde gerçek dinî metin bulunmadığı.
- `test-yazari`: §2'deki dokuz anlam kuralının ve §4 tablolarının her satırının en az bir vektörde karşılığı var; eksik listesi boş.
- Bozma denemesi: bir vektörün beklenen değeri geçici olarak değiştirilir; üç koşucu da aynı `id`'yi kırmızı gösterir; değişiklik geri alınır.
- **Bitti sayılır:** iki rapor temiz ya da bulgular düzeltildi; bozma denemesi üç dilde yakalandı.

## Kabul ölçütleri
- [ ] `shared/test-vectors/` altında yedi dosya var; `pnpm --filter @mutalaa/test-vectors build` geçiyor.
- [ ] `shared/data/ayet-sayilari.json` kaynak adresi, alınma tarihi ve SHA-256 taşıyor; 114 eleman, toplam 6.236; üç kopya JSON'la aynı.
- [ ] `pnpm --filter @mutalaa/anchors test` hem varsayılan hem `LANG=tr_TR.UTF-8` ile yeşil.
- [ ] `dotnet test --solution server/Mutalaa.slnx` yeşil; vektörler `tr-TR` kültüründe de geçiyor.
- [ ] `cd pipeline && uv run pytest` yeşil; `uv run mutalaa export test-vectors --check` 0 ile çıkıyor.
- [ ] Çapa şeması §4 tablolarındaki her girdi vektörlerde birebir var (Doğrulama'daki döngü "EKSİK" yazmıyor).
- [ ] Bozma denemesi üç dilde kırmızı; `metin-denetcisi` ve `test-yazari` raporları aşama kaydında.

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
- BOM'lu JSONL Python'da ilk satırı bozar (Yerel geliştirme §10.2). `Mn` hizalaması üç dilin Unicode verisine dayanır; vektörler yerleşik ve eski işaretlerle yazılır.
- Windows'ta `LANG=tr_TR.UTF-8` Node'un yerel ayarını değiştirmez; ICU yerel ayarı Windows kullanıcı ayarından alır. Türkçe Windows'ta iki koşu da `tr-TR`'dir; `LANG` karşıtlığı Linux CI'da (A08) görülür. Koşu başında yazılan iki yerel ayar aşama kaydına geçer. Ayrıntı: `windows-sorun`.
- `snapSpan` mobilde Hermes'te de çalışacak; düzenli ifade ya da Unicode özelliği desteği A21'deki öz testte sınanır.
- Vektör adları ve satır alanları Çapa şeması §11, Test stratejisi §2 ve Proje yapısı §1.2'de aynıdır (`id`, `input`, `expected`, `note`; geçerli çapada `expected.ref` ve `expected.canonical`). Python modülü `pipeline/src/mutalaa_pipeline/anchor/capa.py`.

## İnsan adımları
- Yok. Tanzil üst verisinin kullanım şartı belirsiz çıkarsa kullanıcı karar verir.

## Çıktılar
- `shared/test-vectors/anchors/*.jsonl`, `offsets/offsets.jsonl`, `content-hash/hash.jsonl`; biçim denetleyicisinin alan denetimi
- `shared/data/ayet-sayilari.json`; `packages/anchors/src/generated/ayet-sayilari.ts`, `pipeline/src/mutalaa_pipeline/anchor/ayet_sayilari.py`, `server/Mutalaa.Domain/Anchors/AyetSayilari.g.cs`
- `packages/anchors/src/` ve testleri; `server/Mutalaa.Domain/Anchors/`, `server/Mutalaa.Domain/Text/ContentHash` ve kanonikleştirme; `server/tests/Mutalaa.Domain.Tests/` vektör koşucusu
- `pipeline/src/mutalaa_pipeline/anchor/` (`capa.py`, metin ve özet modülü), `export` altında `test-vectors` ve `ayet-sayilari` komutları, `pipeline/tests/` koşucusu

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A04-capa-ve-test-vektorleri.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A03](./A03-yerel-altyapi.md) · Sonraki: [A05](./A05-arama-normalizasyonu.md)
