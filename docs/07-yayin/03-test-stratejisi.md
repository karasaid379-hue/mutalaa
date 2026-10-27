# Test stratejisi

> **Sürüm:** 1.7 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-37](../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-17](../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-18](../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-35](../00-ozet/02-karar-defteri.md#k-35--çapa-api-ayrıntıları) · [K-36](../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları) · [K-27](../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform)

Bu dosya neyin, hangi araçla, ne zaman test edildiğini tanımlar. Eşik değerlerinin çoğu bu dosyanın önerisidir; ilk ölçümden sonra kalibre edilir ve öyle işaretlidir.

## 1. Katmanlar

| Katman | Araç | Nerede |
|---|---|---|
| Ortak test vektörleri | pytest, Vitest, xUnit | `shared/test-vectors/` |
| Birim | pytest (`pipeline/`), Vitest (`packages/`, `apps/editor`), Jest + jest-expo (`apps/mobile`), xUnit (`server/`) | Her PR |
| İçerik kalitesi | Altın set değerlendirmesi, değişmezlik testleri | Gece ve sürüm |
| Veritabanı | Göç testleri (Testcontainers, `postgres:18`) | Her PR |
| Yayın kapısı | Publisher birim, bütünleşik ve yapıt taraması | Her PR ve sürüm |
| Mobil | React Native Testing Library, Maestro | PR ve gece |
| Performans, erişilebilirlik | Kıyas ekranı, `gfxinfo`, Instruments, tarayıcılar, elle kontrol | Sürüm |

## 2. Ortak test vektörleri

Normalizasyon ve çapa kuralları tek yerde tanımlıdır ve Python, TypeScript ve C# uygulamaları aynı dosyalarla kilitlenir. Vektör dosyası şartnamedir: bir dosya değişirse üç uygulama aynı PR'da geçmek zorundadır.

```text
shared/test-vectors/
  normalize/tr.jsonl        # Türkçe geniş ve dar anahtar
  normalize/ar.jsonl        # Arapça hareke ve harf birleştirme
  anchors/valid.jsonl       # çapa ayrıştırma; ayrıca invalid, compare, contains, route
  offsets/offsets.jsonl     # kod noktası ofsetleri ve snapSpan
  content-hash/hash.jsonl   # kanonik metin özeti
  fts-query/query.jsonl     # sorgu → FTS5 MATCH ifadesi (doğruluk; Arama §3)
  arama/olcum.jsonl         # arama ölçüm kümesi (bölüm 10); vektör değildir, koşucular okumaz
```

Düzenin tamamı [Proje yapısı](../02-mimari/03-proje-yapisi.md) §1'dedir. Her satır `id`, `input`, `expected` ve isteğe bağlı `note` alanlarını taşır (aynı dosya §1.2).

Çapa vektörleri [K-35](../00-ozet/02-karar-defteri.md#k-35--çapa-api-ayrıntıları)'teki ayrıntıları da kilitler: hata kodlarının önceliği, Kur'an'da okuma sırasına göre `compare`, `contains` ekleri, birim işlevleri (`unitOf`, `toUnitSpan`, `coveredAyahs`), rota kuralları, ofset işlevlerinin hataları ve kendi metnimizin ilk kayıt adım sırası ([Çapa şeması](../03-veri/01-capa-semasi.md) §2, §7, §11). Bir işlevi uygulayan her dil aynı vektörde aynı sonucu verir; `content-hash/` TypeScript'te koşmaz, çünkü cihaz özet hesaplamaz.

Örnekler (çıktılar yerel Python denemesiyle doğrulandı; kesin kurallar [Arama](../03-veri/05-arama-fts5.md) ve [Çapa şeması](../03-veri/01-capa-semasi.md) dosyalarındadır). Satırlar farklı dosyalardandır: `tr-` ve `ar-` `normalize/`, `an-0001` ve `an-0004` `anchors/valid.jsonl`, `an-0002`, `an-0003`, `an-0005` ve `an-0006` `anchors/invalid.jsonl`, `of-` `offsets/offsets.jsonl`. Kimlik önekleri: `valid` ve `invalid` tek ortak `an-` dizisini paylaşır; `cm-` `compare`, `ct-` `contains`, `ro-` `route`, `of-` `offsets`, `ch-` `content-hash` dosyasındadır. Üretilen sınır satırları `an-s…` ve `an-u-…` kimliklidir; birden çok kuralı bozan öncelik satırları `invalid` içindedir (A04, K-35 madde 1). Aşağıdaki satırlar biçimi gösterir; gerçek vektörlerde `expected` ayrıca `unit`, `unit_span` ve `ayahs` taşır ve not alanı dayanak gösterir. `tr-` ve `ar-` satırları gerçek vektörlerden aynen alınmıştır (A05, [K-36](../00-ozet/02-karar-defteri.md#k-36--arama-normalizasyonu-ayrıntıları)): `tr.jsonl` 86, `ar.jsonl` 62 satırdır; `expected` değerleri elle yazılır ve `uv run mutalaa export test-vectors` yalnız biçimi, kaçışı ve kimlik düzenini denetler. Arapça satırlar `\u` kaçışlı sentetik harf ve işaret dizileridir, Kur'an metni değildir; Arama §1.5'teki Kur'an kelimeli Arapça tablonun Tanzil baytlarıyla satırları A10.7'de eklenir.

```jsonl
{"id":"tr-0001","input":"Işık","expected":{"dar":"ışık","genis":"isik"},"note":"I → ı"}
{"id":"tr-0002","input":"İMAN","expected":{"dar":"iman","genis":"iman"},"note":"İ → i"}
{"id":"tr-0003","input":"ışığın","expected":{"dar":"ışığın","genis":"isigin"},"note":"Türkçe harf katlama"}
{"id":"tr-0011","input":"hâlâ","expected":{"dar":"hâlâ","genis":"hala"},"note":"dar anahtar ayırır"}
{"id":"tr-0015","input":"IŞIK","expected":{"dar":"ışık","genis":"isik"},"note":"büyük harf I → ı (Test stratejisi 2)"}
{"id":"ar-0001","input":"بًب","expected":"بب","note":"U+064B (silme aralığının başı) silinir, harfler birleşir"}
{"id":"ar-0002","input":"بٟب","expected":"بب","note":"U+065F (silme aralığının sonu) silinir"}
{"id":"ar-0003","input":"بٰب","expected":"بب","note":"U+0670 (üstteki elif) silinir"}
{"id":"an-0001","input":"q:2:255:3-7","expected":{"ref":{"anchor":{"t":"q","sure":2,"ayet":255,"ilk":3,"son":7}},"canonical":"q:2:255:3-7"}}
{"id":"an-0002","input":"q:2:255:7-3","expected":"TERS_ARALIK","note":"ilk > son"}
{"id":"an-0003","input":"q:2:287","expected":"AYET_ARALIGI","note":"Bakara 286 âyet"}
{"id":"an-0004","input":"tf:elmalili:2-255-257:p3","expected":{"ref":{"anchor":{"t":"tf","eser":"elmalili","sure":2,"ilk":255,"son":257,"p":3}},"canonical":"tf:elmalili:2-255-257:p3"}}
{"id":"an-0005","input":"rn:sözler:soz-10:p4","expected":"BICIM","note":"slug küçük harf ASCII"}
{"id":"an-0006","input":"rn:sozler:soz-10:hakikat-3:p4@184-120","expected":"TERS_ARALIK","note":"başlangıç > bitiş"}
{"id":"of-0001","input":"âlem 𝐀","expected":{"codepoints":6,"utf16":7},"note":"girdi NFC biçiminde; U+1D400 BMP dışı"}
```

```python
# pipeline/tests/test_normalize_vectors.py
@pytest.mark.parametrize("vektor", TR, ids=[v["id"] for v in TR])
def test_turkce_vektoru(vektor):
    assert normalize_tr(vektor["input"], "dar") == vektor["expected"]["dar"]
    assert normalize_tr(vektor["input"], "genis") == vektor["expected"]["genis"]
```

```ts
// packages/search/test/normalize.test.ts
test.each(rows)('$id', ({ input, expected }) => {
  expect(normalizeTr(input, 'dar')).toBe(expected.dar);
  expect(normalizeTr(input, 'genis')).toBe(expected.genis);
});
```

```csharp
// server/tests/Mutalaa.Domain.Tests/NormalizeVectorTests.cs: her vektör Invariant ve tr-TR olarak ayrı koşar
[Theory]
[MemberData(nameof(TrIds))]
public void Turkish_trTR(string id) => CultureScope.Turkish(() => CheckTurkish(id));
// CheckTurkish: SearchNormalizer.TurkishNarrow(input) == dar, SearchNormalizer.TurkishWide(input) == genis
```

| Tuzak | Örnek | Önlem |
|---|---|---|
| Python küçük harf | `"İ".lower()` iki kod noktası verir (`i` + U+0307); `"I".lower()` `i` verir | Önce `I→ı`, `İ→i` açık eşlemesi, sonra kod noktası başına küçük harf |
| .NET küçük harf | `ToLower()` geçerli kültüre bağlıdır | Kültüre bırakılmaz; açık eşleme ve `Rune.ToLowerInvariant` (`SearchNormalizer.LowerTurkish`) |
| JS küçük harf | `toLowerCase()` Türkçe kurala uymaz; `toLocaleLowerCase('tr')` kullanılmaz (Hermes davranışı: [Mobil mimari](../06-mobil/01-mobil-mimari.md) MM-11) | Açık eşleme; cihazda öz test |
| Son sigma | Dize düzeyinde `lower()` ve `toLowerCase()` son sigma bağlamı uygular, .NET uygulamaz (`ΟΔΟΣ`) | Kod noktası başına küçük harf; `tr-0025` bilinen sınırı kilitler |
| Unicode sürümü | Python 15.1, Node 17.0, .NET kendi tablosu: yeni harf ve işaretler ayrışabilir | Vektörler yalnız eski, yerleşik kod noktalarını kullanır; Linux CI (A08) ve Hermes (A21) gözler |
| Ofset | Python kod noktası sayar, JS ve C# UTF-16 birimi sayar (`of-0001`: 6 ve 7) | Ofset kod noktasıdır; dönüştürücü vektörle sınanır |
| FTS5 varsayılanı | unicode61, "Işık"ı `ışık`, `IŞIK`, `isik` sorgularıyla bulamadı; harekeli besmele parçalandı ([SQLite FTS5](https://sqlite.org/fts5.html), rapordaki yerel deneme) | İndeks normalize `search_text` üzerinde |

Jest Node üzerinde çalışır ve Hermes'i sınamaz. Bu yüzden `dev` derlemede bir "Öz test" ekranı vektörleri Hermes'te çalıştırır ve bir Maestro akışı "Geçti" metnini doğrular. Vektör dosyaları yalnız `dev` derlemeye gömülür.

## 3. Birim testleri

- **Python (pytest):** `ingest`, `normalize`, `anchor`, `enrich`, `qa` modülleri; ağ ve model çağrısı fikstürle değiştirilir; yavaş testler işaretlenir.
- **TypeScript (Vitest):** `anchors`, `content-schema`, `search`, `reader-core`, `player`, `ui-tokens` ve editör paneli. Ses durum makinesi (XState) geçiş testleriyle sınanır.
- **C# (xUnit):** `Mutalaa.Domain`, `Mutalaa.Publisher`, `Mutalaa.Api`.

```ts
// Olay ve bağlam adları: Ses sistemi §5 (sahte motor ve kuyruk çözücüyle)
test('âyet ×3 tekrardan sonra sonraki âyete geçer', async () => {
  const actor = createActor(createPlayerMachine(fakeEngine, resolveQueue, { repeatEach: 3 })).start();
  actor.send({ type: 'LOAD', reciterId: 'test', range: { scope: 'aralik', from: 'q:1:1', to: 'q:1:7' }, autoplay: true });
  await waitFor(actor, (s) => s.matches({ active: 'playing' }));
  for (let i = 0; i < 3; i++) actor.send({ type: 'ENGINE.ITEM_END', index: 0, durationMs: 5000 });
  const { queue, index } = actor.getSnapshot().context;
  expect(queue[index].anchor).toBe('q:1:2');
});
```

## 4. İçerik hattı: altın set değerlendirmesi

| Altın set | Büyüklük | Tabakalama |
|---|---|---|
| Atıf ve iktibas | 300–500 paragraf | Sözler, Mektubat, Lem'alar, Şuâlar, Mesnevî-i Nuriye, İşârâtü'l-İ'câz ve Elmalılı tefsir örneklemi |
| Kök (Türkçe lemma → Arapça kök) | 300–500 çift | Sıklık bandı ve kaynak (meal, tefsir, Risale) |
| Benzer âyet | Örneklem | QUL kaydı, lisansı teyit edilirse |
| Anlamsal (v1.x) | Alan içi sorgu seti | Türkçe sorgu → paragraf; Arapça ve Türkçe → âyet |

Büyüklük ve tabakalar rapordan gelir. Risale metni hukukçu görüşü gelene kadar `kapali` olduğu için Risale altın seti de bu görüşten sonra kurulur; görüş olumluysa set `data/` altında (git dışı) tutulur ve hiçbir pakete girmez ([K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik), [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı)). Harici bir dil modeli API'sine gönderim ayrıca Açık soru; hukuki görüş değildir ([Yayın kapısı ve Kurul](./01-yayin-kapisi-ve-kurul.md#24-telif-ve-işleme-açık-soruları)). Elmalılı ve serbest metinlerdeki iktibas setleri bu görüşü beklemez. Basılı fihristler başlangıç noktasıdır; bir fihrist kaydının Kur'an'da karşılığı bulunmadığı not edilmiştir ([RİNAP](https://rinap.uskudar.edu.tr/uploads/site/6/content/files/risale-i-nurun-tefsirdeki-yeri-compressed.pdf)).

Ölçüler âyet düzeyinde ve açıklık (span) düzeyinde kesinlik, duyarlılık ve F1'dir; uzun ve kısa iktibas ayrı raporlanır. Açıklık eşleşmesi aynı hedef çapa ve en az 0,5 örtüşme oranı ister (öneri).

Başarı hedefleri [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md#8-v1-başarı-ölçütleri) §8'deki B-03 ve B-04'tür; İ-22 onayına kadar öneridir (AS-09). Aşağıdaki tablo bu hedefleri tür başına kapıya çevirir; B-03 ve B-04'te olmayan değerler bu dosyanın önerisidir. B-03 ayrıca görünür (orta ve üstü güvenli) bağlantılarda âyet düzeyi kesinliği ≥ 0,95, "kesin" etiketlilerde ≥ 0,99 ister.

| `xref.type` | Başlangıç eşiği (öneri) | Eşik tutmazsa |
|---|---|---|
| `atif` | Kesinlik ≥ 0,98; duyarlılık ≥ 0,90 (B-03) | O türün `aday` bağlantıları pakete girmez |
| `iktibas`, 4 kelime ve üstü | Kesinlik ≥ 0,95 (B-03), duyarlılık ≥ 0,85 | Aynı |
| `iktibas`, 4 kelimeden kısa | Kesinlik ≥ 0,85 (B-03) | Yalnız `onayli` bağlantılar girer |
| `kok` | Kesinlik ≥ 0,95 (B-04), duyarlılık ≥ 0,80, dil modeli–insan κ ≥ 0,6 | Toplu etiketleme denetimsiz çalışmaz |
| `lemma` | QAC'den türetme %100 tutarlı | Derleme durur |
| `benzer_ayet` | Örneklem kesinliği ≥ 0,90 | Yalnız `onayli` |
| `anlamsal` (v1.x) | Kesinlik@10 ≥ 0,70 ve "makine önerisi" rozeti | Yayımlanmaz |
| `ima`, `konu` | Otomatik yayın yok | Yalnız editör onayı |

κ eşiği rapordaki protokolden gelir: insanlar arası uyum 0,60, üç dil modelinin çoğunluk oyu ile insan arası uyum 0,57 ([protocols.io](https://www.protocols.io/view/llm-assisted-expert-annotation-for-systematic-lite-4r3l2dw5jg1y/v1.pdf)). Bir koşuda herhangi bir ölçü önceki kabul edilmiş koşuya göre 0,02'den fazla düşerse koşu eşiği geçse de kırılır (öneri). Her koşu `data/reports/{data_version}.json` dosyasına (git dışı; [İçerik hattı](../04-icerik/02-icerik-hatti.md) §7) tür, set sürümü, örnek sayısı, ölçüler, eşik ve sonuç yazar.

```python
def prf(pred: set, gold: set) -> tuple[float, float, float]:
    tp = len(pred & gold)
    p = tp / len(pred) if pred else 1.0
    r = tp / len(gold) if gold else 1.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)
```

## 5. Kur'an metni değişmezlik testleri

Tanzil metni aynen dağıtılabilir, değiştirilemez ([Tanzil metni, OpenITI kopyası](https://raw.githubusercontent.com/OpenITI/0025AH/master/data/0001Quran/0001Quran.Mushaf/0001Quran.Mushaf.Tanzil001-ara1.mARkdown)). Kurul onayı da sürüme bağlıdır. Bu testler her gece ve her sürümde koşar:

1. İndirilen Uthmani ve Simple Clean dosyalarının SHA-256'sı `pipeline/src/mutalaa_pipeline/ingest/tanzil.lock.json` içindeki sabit değere eşittir.
2. 114 sure ve 6.236 âyet vardır.
3. Her `q:{sure}:{ayet}` biriminin kanonik metni Tanzil satırıyla bayt bayt aynıdır. Birimlerden Tanzil dosyası yeniden üretilir ve kaynakla karşılaştırılır (bildirim satırları hariç).
4. Her birimin `content_hash` değeri o metnin SHA-256'sıdır.
5. Okuyucunun metin seçicisi yalnız kanonik metni okur; `search_text` hiçbir ekranda görünmez (`reader-core` testi).
6. `core` paketinde Tanzil telif bildiriminin tam metni bulunur.
7. Sayfa eşlemesi: 1. sayfa Fâtiha 1–7'dir, 604. sayfa Nâs 6 ile biter, 0 ve 605 geçersizdir (`quran-app-docs/04-okuma/01-quran-okuyucu.md` testleri).
8. Kurul kapsamındaki paketlerde hesaplanan içerik özeti onaylı özete eşittir ([Yayın kapısı](./01-yayin-kapisi-ve-kurul.md)).

**Çözüldü (NFC, K-26).** Karar defteri kanonik metni kaynağın dağıttığı hâli olarak tanımladı: Tanzil metnine NFC uygulanmaz, NFC yalnız kendi ürettiğimiz metinlerde ilk kayıtta yapılır, ofsetler kanonik metnin kod noktalarıdır. Aşağıdaki not bu kararın gerekçesi olarak kalır. İlk brif kesin karakter aralıklarını NFC kanonik metinde tanımlıyordu. NFC Arapça harekelerin sırasını değiştirebilir: şedde + fetha (U+0651 U+064E) NFC'de fetha + şedde (U+064E U+0651) olur (yerel Python denemesi, 18 Ekim 2026). Tanzil metni NFC değilse NFC'ye çevirmek bayt değiştirir ve "değiştirmek yasak" şartıyla çatışır. Test 3 Kur'an birimlerinde Tanzil baytlarını korur, ayrıca metnin NFC olup olmadığını raporlar. Ofset tanımının Kur'an birimlerine nasıl uygulanacağı [Çapa şeması](../03-veri/01-capa-semasi.md) dosyasında karara bağlanır.

## 6. Veritabanı göç testleri

**Editoryal veritabanı (PostgreSQL 18, EF Core 10).** Bütün göçler boş bir `postgres:18.6-trixie` kabına uygulanır, bekleyen göç kalmaz. Şema dökümü (`pg_dump --schema-only`) depodaki anlık görüntüyle karşılaştırılır. Python hattının bütünleşik testleri aynı şemaya karşı koşar.

```csharp
public sealed class MigrationTests : IAsyncLifetime
{
    // Parametresiz new PostgreSqlBuilder() [Obsolete] (CS0618); uyarılar hata olduğu için imaj adı verilir.
    readonly PostgreSqlContainer _pg = new PostgreSqlBuilder("postgres:18.6-trixie")
        .WithEnvironment("POSTGRES_INITDB_ARGS", "--encoding=UTF8 --locale=C.UTF-8")
        .WithEnvironment("TZ", "UTC")
        .Build();
    public async ValueTask InitializeAsync() => await _pg.StartAsync();   // xunit.v3 imzası (doğrulandı, 21 Ekim 2026)
    public ValueTask DisposeAsync() => _pg.DisposeAsync();

    [Fact]
    public async Task Bos_veritabanina_butun_gocler_uygulanir()
    {
        await using var db = TestDb.Create(_pg.GetConnectionString());
        await db.Database.MigrateAsync();
        Assert.Empty(await db.Database.GetPendingMigrationsAsync());
    }
}
```

Yığın `xunit.v3` kullanır ([Teknoloji yığını](../02-mimari/02-teknoloji-yigini.md)); `IAsyncLifetime` yöntemleri `ValueTask` döndürür. Çözüldü (21 Ekim 2026): imza xunit.v3 kaynağında ve göç kılavuzunda doğrulandı ([IAsyncLifetime.cs](https://raw.githubusercontent.com/xunit/xunit/main/src/xunit.v3.core/IAsyncLifetime.cs), [xunit.v3 göç kılavuzu](https://xunit.net/docs/getting-started/v3/migration), okuma 21 Ekim 2026). Testler Microsoft.Testing.Platform üzerinde koşar; komut `dotnet test --solution server/Mutalaa.slnx` ([K-33](../00-ozet/02-karar-defteri.md#k-33--net-test-çalıştırıcısı-xunitv3--microsofttestingplatform), [Proje yapısı](../02-mimari/03-proje-yapisi.md) §4.2).

**Uygulandı (A07, 27 Ekim 2026).** Yukarıdaki örnek sadeleştirilmiş biçimdir; gerçek testler `server/tests/Mutalaa.Api.Tests/` altındadır.

- **Kap ve fikstür.** İmaj `postgres:18.6-trixie`'dir. İmajın varsayılan yerel ayarı `en_US.utf8` olduğu için kapta `POSTGRES_INITDB_ARGS=--encoding=UTF8 --locale=C.UTF-8` ve `TZ=UTC` verilir. Fikstür `AssemblyFixture`'dır ve kabı tembel açar: kurucu ve `InitializeAsync` Docker'a dokunmaz, `Build()` ilk veritabanı isteğinde çalışır. Böylece Docker kapalıyken yalnız Docker'lı sınıflar düşer (bir `AssemblyFixture` hatası bütün derlemeyi düşürür).
- **Enum testi.** Tek JSON `packages/content-schema/enums.json` dosyasıdır. TypeScript birleşim tipi (`packages/content-schema/test/enums.test.ts`, Vitest), Python enum'u (`pipeline/tests/test_enums.py`, pytest) ve C# enum'u (`EnumLabelTests`, xUnit v3; etiket ve sıra) bu JSON'la karşılaştırılır (A06). JSON on bir tür taşır: `license_status` (4 değer), `xref_type` (8), `xref_status` (3), `xref_origin` (3), `source_kind`, `derleme_turu`, `unit_kind`, `unit_status`, `metin_durumu`, `inceleme_durumu`, `surum_durumu` ([K-37](../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)). Sıra anlamlıdır (ör. `serbest` < `bekliyor` < `ic_kullanim` < `kapali`). `PostgresEnumTests` PostgreSQL'deki etiketleri `enumsortorder` sırasıyla JSON'la karşılaştırır.
- **Anlık görüntü.** Dosya `server/tests/Mutalaa.Api.Tests/Snapshots/editoryal-sema.sql`'dir (`SchemaSnapshotTests`). Dökümden her koşuda değişen satırlar atılır: `-- Dumped from database version …`, `-- Dumped by pg_dump version …`, `\restrict …`, `\unrestrict …`. Bilinçli değişiklikte güncelleme `MUTALAA_UPDATE_SNAPSHOTS=1 dotnet test --project server/tests/Mutalaa.Api.Tests --filter-class Mutalaa.Api.Tests.SchemaSnapshotTests` ile yapılır. Test dosyayı yeniden yazar ve bilerek kırmızı biter; `CI` ortam değişkeni doluysa güncelleme reddedilir. Fark commit'te gözden geçirilir.

**Kullanıcı veritabanı (cihazda, expo-sqlite + Drizzle).** Yayımlanmış her şema sürümünden bir fikstür veritabanı saklanır. Göç dosyaları Node'da SQLite üzerinde çalıştırılır ve veri kaybı olmadığı doğrulanır. Her kullanıcı tablosunda `id`, `hlc`, `updated_at`, `deleted_at`, `base_version`, `device_id` sütunlarının bulunduğu test edilir ([K-15](../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte)). Bir Maestro akışı eski sürümden güncellemeyi cihazda sınar.

**İçerik paketi.** `min_app_version` değeri uygulamadan yüksek olan paket açılmaz; eski paket yeni uygulamada açılır.

## 7. Yayın kapısı testleri

Ayrıntı [Yayın kapısı ve Kurul](./01-yayin-kapisi-ve-kurul.md#5-public-derleme-hiçbir-zaman-ic_kullanim-bekliyor-kapali-içermez-testi) dosyasındadır. Kapsam: durum × derleme türü matrisi (`internal` ve `public` yalnız `serbest`, `dev` `kapali` dışındaki her durum; [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı)); onaysız, onaylı ve onaydan sonra değişmiş Kurul kaynağı; kaynak kaydı olmayan paket; `kurul_gerekli` değerinin kaynaklardan türetilmesi; imzasız ya da bozuk imzalı manifestin public derlemede reddi; `xref` süzgeci (public derlemede `rn:` hedefli bağlantı yalnız ayrı lisanslı dizin kaydıyla girer); manifest ile önek içeriğinin tutarlılığı; public manifestin, public önekteki bütün nesnelerin ve gömülü `core` paketinin yapıt taraması. Bu son test her public sürümde zorunludur.

## 8. Mobil bileşen testleri

Jest (jest-expo) ve React Native Testing Library ile:

- **Kelime kartı:** Arapça kelime, Türkçe anlam, kök, "Bu kök Kur'an'da N yerde geçer" satırı, eylemler.
- **Bağlantılar alt sayfası:** esere göre gruplama, gerekçe etiketi, güven düzeyi, düşük güvenli ve denetlenmemiş bağlantıların "Daha fazla (otomatik)" altında katlanması.
- **Geri dönüş yığını:** atlama, kırıntı izi, "Okuduğun yere dön" çipi.
- **Mini oynatıcı ve Depolama listesi.**
- **Lisans görünürlüğü:** `internal` ve `public` bayrağıyla `bekliyor` paket Kütüphane'de görünmez; `kelime-kok` paketi `bekliyor` iken kelime kartında kök, lemma ve anlam satırları kapalıdır.

## 9. Uçtan uca testler (Maestro)

`dev` ve `internal` derlemeler iki fikstür paketi taşır: küçük bir metin paketi (`test-kucuk`) ve üretilmiş tonlarla sahte zamanlama içeren ses paketi `ses-test`. Ses paketinin kimliği `ses-{hafiz}` kalıbını izler; kaynağının slug'ı `test-ses`'tir. Böylece testler gerçek hafız kaydına ihtiyaç duymaz. Fikstürler kendi ürettiğimiz içeriktir ve `serbest` durumundadır; bu yüzden `internal` derlemeye de girer. Kaynak slug'ları `test-` ile başladığı için `public` derlemeye hiç girmez ([Backend API](../02-mimari/05-backend-api.md#103-kapı-kontrolleri) P-12; [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md#8-örnek-veri) §8). `testID` adları çapa gramerini kullanır. Akışlar derleme türünün uygulama kimliğini ve derin bağlantı şemasını değişkenden alır: `${APP_ID}` ve `${SCHEME}` `dev`'de `app.mutalaa.dev` ile `mutalaa-dev`, `internal`'da `app.mutalaa.internal` ile `mutalaa-internal`'dır ([Mobil mimari](../06-mobil/01-mobil-mimari.md#10-derleme-türleri-ve-özellik-bayrakları) §10). Değişkenler koşuda verilir; `maestro test` bayrağı Doğrulanacak (A33).

```yaml
appId: ${APP_ID}
name: Sayfa aç, kelimeye dokun, bağlantıya git, geri dön
---
- launchApp: { clearState: true }
- openLink: ${SCHEME}://q/2/255
- assertVisible: { id: "ayet-q:2:255" }
- tapOn: { id: "kelime-q:2:255:3" }
- assertVisible: { id: "kelime-karti" }
- tapOn: "Bağlantılar"
- tapOn: { id: "baglanti-0" }
- assertVisible: { id: "geri-don-cipi" }
- tapOn: { id: "geri-don-cipi" }
- assertVisible: { id: "ayet-q:2:255" }
```

| Akış | Adımlar ve doğrulama |
|---|---|
| Ses çal | `${SCHEME}://q/1/1` aç, mini oynatıcıda Oynat; Duraklat düğmesi görünür; `etkin-ayet-q:1:2` 20 saniye içinde görünür; Duraklat |
| Arama | Ara sekmesi, `isik` yaz; ilk sonuç "Işık" içerir; sonuca dokununca okuyucu açılır |
| Depolama'da paket sil | Ayarlar › Depolama, `test-kucuk` satırında Sil; onay penceresi yoktur ([K-18](../00-ozet/02-karar-defteri.md#k-18--depolama-yöneticisi-v1de), [Depolama yöneticisi](../06-mobil/03-depolama-yoneticisi.md) §1.1). Satır "Silindi · Geri al" olur; ekrandan çıkınca Kütüphane'de "İndir" görünür |

Android'de ASCII dışı karakter girişi Doğrulanacak; arama akışı bu yüzden `isik` sorgusuyla geniş anahtarı sınar, Arapça sorgu öz test ekranında sınanır. Akışlar iOS simülatöründe, Android emülatöründe ve sürümde bir gerçek orta seviye Android cihazda koşar. iOS simülatörü Mac ister, geliştirme Windows'tadır ([Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §1); iOS akışlarının nerede koşacağı Açık soru'dur (bölüm 14 madde 7).

## 10. Performans testleri

| Ölçü | Hedef | Ölçüm |
|---|---|---|
| Arama | 50 ms altı (p95 < 50 ms), orta seviye Android ([K-17](../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5)) | `dev` ve `internal` derlemedeki "Arama ölçümü" ekranı, `shared/test-vectors/arama/olcum.jsonl` ([Arama](../03-veri/05-arama-fts5.md) §6) |
| Sayfa çevirme | 60 fps; takılan kare oranı ≤ %5 (öneri) | Android `gfxinfo`, iOS Instruments |
| Kelime kartı, Bağlantılar ilk sonuç | ≤ 100 ms (öneri) | Kıyas ekranı |
| Soğuk açılış | Açık soru: eski plan iki değer veriyor (TTI < 3 s; iPhone 12'de < 1,5 s, düşük seviye Android'de < 2,5 s) | Sürüm ölçümü |
| Bellek | < 200 MB (eski plan; öneri) | Sürüm ölçümü |
| Uygulama boyutu | Açık soru: eski plandaki < 30 MB bütçesi gömülü `core` paketiyle uyuşmayabilir | Her sürümde kaydedilir |

Sorgu seti Türkçe tek kelime, önek, ekli biçim ("ışığın"), harekeli ve harekesiz Arapça ve birden çok paketi `ATTACH` ile arayan sorgular içerir. Referans cihazlar Açık soru: bir orta seviye Android ve iOS 16.4 çalıştıran en eski cihaz sınıfı.

```bash
adb shell dumpsys gfxinfo <paket-adi> reset
maestro test apps/mobile/e2e/perf-sayfa-cevir.yaml   # 50 sayfa kaydırma
adb shell dumpsys gfxinfo <paket-adi> | grep -i "janky"
```

## 11. Erişilebilirlik kontrolleri

**Otomatik.** `ui-tokens` içindeki her metin ve yüzey çifti için WCAG kontrast oranı hesaplanır; 4,5:1 altı kırılır. Altın süs rengi metin jetonu olarak kullanılamaz. Değerler rapordaki hesapla aynıdır; Âhar sütunundaki çini mavisi ve altın bu dosyada hesaplandı.

| Jeton | Kâğıt | Âhar | Gece |
|---|---|---|---|
| Metin | 16,3:1 | 13,2:1 | 13,8:1 |
| Çini mavisi | 7,7:1 | 6,8:1 | 8,4:1 |
| Turkuaz | 5,7:1 | 5,9:1 | 8,6:1 |
| Lâl | 6,6:1 | 6,3:1 | 6,1:1 |
| Altın | süs 2,96:1, metin rengi 4,7:1 | süs 3,3:1 | 9,0:1 |

Ekranlar her sürümde Android Erişilebilirlik Tarayıcısı ve Xcode Accessibility Inspector ile taranır.

**Elle** ([Apple HIG Erişilebilirlik](https://developer.apple.com/design/human-interface-guidelines/accessibility)):

- [ ] VoiceOver ve TalkBack ile dört E2E akışı tamamlanır.
- [ ] Mushaf A'da glif kelimeler ekran okuyucudan gizlidir; her âyet Arapça dil özelliği taşıyan Unicode metin ([Mobil mimari](../06-mobil/01-mobil-mimari.md#13-erişilebilirlik-uygulaması) §13) ve "Bakara Sûresi, 255. âyet" etiketiyle tek öğedir; ekran okuyucu açıkken "Erişilebilir metin modu" önerilir.
- [ ] Metin %200 büyür; Arapça ve Türkçe boyutu ayrı ayarlanır.
- [ ] Dokunma hedefleri 44×44 pt (en az 28×28).
- [ ] Hareketi Azalt açıkken kayan geçiş yerine solma, otomatik kaydırma yerine atlama kullanılır.
- [ ] Her kaydırma jestinin görünür düğme karşılığı vardır; alt sayfada görünür Kapat düğmesi bulunur.
- [ ] Renk tek başına anlam taşımaz: ses vurgusunda âyette zemin, kelimede alt çizgi.

VoiceOver ve TalkBack'in harekeli Kur'an Arapçasıyla davranışı hakkında kaynak bulunamadı. Bu davranış gerçek kullanıcılarla sınanır (Açık soru).

## 12. CI düzeni

| Tetik | Koşanlar |
|---|---|
| Her PR | Vektörler (3 dil), birim testleri, tip denetimi, lint, bağımlılık lisans denetimi, Publisher kapı testleri, göç ve enum testleri, kontrast testi |
| Gece | İçerik hattı tam koşu, altın set değerlendirmesi, değişmezlik testleri, `internal` paket üretimi, emülatörde Maestro. Gece iş akışı henüz yoktur: A08 gece işi kurmaz; iskeleti ilk gece işiyle A10'da açılır ([BÇ-42](../10-claude-code/07-belge-celiskileri.md#1-karar-bekleyenler)) |

**Her PR satırının bugünkü karşılığı (A08, 27 Ekim 2026).** Beş iş akışı koşar ([Proje yapısı §7](../02-mimari/03-proje-yapisi.md#7-ci-iş-akışları-github-actions)): `ci-ts` (TypeScript vektörleri ve birim testleri, lint, tip denetimi, `tr_TR.UTF-8` ve `C.UTF-8` ayakları), `ci-dotnet` (C# vektörleri ve birim testleri, Testcontainers ile veritabanı ve göç testleri, `dotnet format`), `ci-pipeline` (Python vektörleri ve testleri, ruff, mypy; Ubuntu ve Windows), `pr-title` (PR başlığı biçimi) ve `ci-workflows` (iş akışı dosyalarının actionlint denetimi). İki kapı vardır: bağımlılık lisans kapısı (yalnız dağıtılan ve sunulan kodda durdurur; [Teknoloji yığını §3](../02-mimari/02-teknoloji-yigini.md#3-lisans-notları)) ve PR başlığı kapısı. Publisher kapı testleri ve kontrast testi ilgili aşamalar geldikçe bu iş akışlarına eklenir (A13 ve mobil aşamalar); bugünkü koşular yalnız var olan testleri çalıştırır.
| Sürüm | Hepsi, public yapıt taraması, referans cihazda performans, elle erişilebilirlik, aşağıdaki kontrol listesi |

## 13. Sürüm kontrol listesi

- [ ] CI'nın bütün işleri yeşil; sürüm numarası ve değişiklik notu hazır.
- [ ] Altın set kapıları geçti; değerlendirme raporu `release` kaydına bağlı.
- [ ] Değişmezlik testleri yeşil.
- [ ] Kapı raporu okundu; public yapıt taraması yeşil; public manifest imzalı ve imza uygulamadaki açık anahtarla doğrulanıyor.
- [ ] Kurul kapsamındaki içerik özetleri onaylı özetlerle aynı; Kurul onay bilgisi ekranı doğru.
- [ ] Kaynaklar ve lisanslar ekranı yeni kaynakları ve fontları içeriyor.
- [ ] Gizlilik metni ve mağaza beyanları uygulamanın davranışıyla aynı ([KVKK ve gizlilik](./02-kvkk-ve-gizlilik.md)).
- [ ] Maestro akışları iOS ve Android'de yeşil (iOS koşusunun yeri: bölüm 14 madde 7); Öz test ekranı "Geçti".
- [ ] Performans bütçeleri referans cihazlarda tutuyor; uygulama boyutu kaydedildi.
- [ ] Erişilebilirlik elle kontrol listesi tamam.
- [ ] Hata raporlama sürümü ve kaynak eşlemeleri yüklendi; olaylarda kişisel veri yok.
- [ ] Mağaza metni ertelenmiş özellikleri vaat etmiyor.
- [ ] iOS 16.4 cihazında ve düşük seviye Android'de duman testi yapıldı.
- [ ] Geri alma yolu yazılı: JS hatası için EAS Update, içerik için önceki paket sürümü, `core` için yeni uygulama sürümü.

## 14. Açık sorular

1. ~~Tanzil metni NFC mi; ofset tanımı Kur'an birimlerine nasıl uygulanır?~~ Çözüldü: K-26 (Tanzil dağıtıldığı hâliyle; ofsetler kanonik metnin kod noktaları). Testin raporladığı NFC durumu yalnız bilgi amaçlıdır.
2. Referans cihazlar hangileri?
3. Soğuk açılış ve uygulama boyutu bütçeleri.
4. Android'de Maestro ile ASCII dışı karakter girişi (Doğrulanacak).
5. Hermes'te `toLocaleLowerCase('tr')` davranışı (Doğrulanacak).
6. Ekran okuyucuların harekeli Kur'an Arapçasıyla davranışı.
7. iOS'ta Maestro nerede koşar (bölüm 9, 13)? Öneri: bulutta, EAS Workflows'un Maestro desteği ya da Maestro Cloud ile (Doğrulanacak); o zamana kadar iOS için TestFlight'ta elle duman testi. Karar A33'te.

## İlgili dosyalar

- [Yayın kapısı ve Kurul](./01-yayin-kapisi-ve-kurul.md) · [KVKK ve gizlilik](./02-kvkk-ve-gizlilik.md)
- [Çapa şeması](../03-veri/01-capa-semasi.md) · [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md) · [Arama](../03-veri/05-arama-fts5.md)
- [İçerik hattı](../04-icerik/02-icerik-hatti.md) · [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) · [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)
- [Mobil mimari](../06-mobil/01-mobil-mimari.md) · [Ses sistemi](../06-mobil/02-ses-sistemi.md) · [Tasarım sistemi](../01-urun/04-tasarim-sistemi.md) · [Proje yapısı](../02-mimari/03-proje-yapisi.md)
- [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Riskler](../08-yol-haritasi/03-riskler.md) · [Kaynakça](../09-kaynakca.md)
