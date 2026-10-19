# A18 · Bağlantılar (`xref`) ve altın setler

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A16](./A16-elmalili-meali.md) · [A17](./A17-kelime-katmani.md) · **İnsan adımı:** İ-12 (Türkçe → kök onayı) · İ-13
> **Ajanlar:** `hat-gelistirici` · `test-yazari` · `lisans-denetcisi` · `arastirmaci` · `sunucu-gelistirici` (yayın süzgeci) · `inceleyici` · **Beceriler:** `icerik-hatti` · `capa-gramer` · `lisans-kapisi` · `metin-butunlugu` · **Tahmini oturum:** 4–5 Claude Code oturumu; etiketleme ayrıca
> **Başlat:** `/asama A18`

## Amaç
v1 bağlantı türleri içerik hattında üretilir ve `xref` tablosuna aday olarak yazılır: Kur'an içi `kok` ve `lemma`, Tanzil üzerinde kendi n-gram indeksimizle `benzer_ayet`, onaylı meal için Türkçe kelime → Arapça kök indeksi. Açık atıf ve iktibas motoru kurulur ve sentetik örneklerle sınanır. Altın set araçları ve tür başına kapılar kurulur; etiketleme insan işidir (İ-13). Kapıyı geçemeyen türün aday bağlantıları pakete girmez.

## Okunacak belgeler
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §2 katmanlar, §4 `xref` ve upsert, §5 türler, §6 puanlama, §8 yayın kuralı, §13 paketleme
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): tamamı
- [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §5 Türkçe kelime → Arapça kök hattı, §6 "yalnızca etimolojik", §7 kalite ve IDF
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 altın set değerlendirmesi ve eşikler
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5–§7 (`lemma` Türkçe satırı, `tr_root_index`, `tr_form`, `xref`), §8 `review`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §4 bağlantıların dağılımı, §7 süzme · [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §6 madde 4, §9, §10

## Kapsam
**Yapılır**
- Türkçe kelime → Arapça kök hattı onaylı meal üzerinde; `lemma` (`lang = 'tr'`), `tr_root_index`, `tr_form`.
- Kur'an içi `kok` ve `lemma` bağlantıları; `benzer_ayet` (sözlüksel, kendi indeksimiz).
- Açık atıf grameri ve iktibas motoru (n-gram, Smith-Waterman, kalıp ve bağlam kuralları, gri bölgede isteğe bağlı dil modeli doğrulaması); hazır araç karşılaştırması.
- Altın set biçimi, etiketleme kuyruğu, ölçüm ve kapı raporları; tür bazında yayın süzgeci kararı.

**Yapılmaz**
- Risale metni üzerinde çalıştırma ve Risale altın seti: metin `kapali` (İ-03). Elmalılı tefsir paragrafları (A37).
- Hadis atıfları ve Tecrîd–Buhârî eşlemesi (A19). `anlamsal` ve `konu` (v1.x). Bağlantılar paneli ve "Önerilen" sırası (cihazda; A25).

## Adımlar
### A18.1 · Doğrulamalar ve kararlar
- `arastirmaci` doğrular: zeyrek'in Python 3.13 ile çalışması (Kök ve lemma §10 madde 3); kaikki/wiktextract JSONL alan adları ve lisans durumu; Tanzil Uthmani ve Simple Clean âyet başı kelime sayısı eşitliği ve imlâî → Uthmani konum eşlemesi (İktibas tespiti §5, §14 madde 3); ijaza, quran-search-in-text ve passim lisans ve sürümleri (§11).
- zeyrek uyumsuzsa yedek yol (ZemberekDotNet) `/karar` ile seçilir. Birim başına bağlantı sayısı N ve `idf_n < 0,2` eşiği (öneri) planda sorulur.
- Eşikler: hedefler Kapsam ve fazlar §8 B-03 ve B-04'tür (İ-22 onayına kadar öneri); tür başına kapı eşikleri Test stratejisi §4 tablosundadır ve B-03 ile uyumludur. İktibas tespiti §10 bu ikisine bağlanır.
- **Bitti sayılır:** kararlar karar defterinde; doğrulama raporu kaynak bağlantılı.

### A18.2 · Türkçe kelime → Arapça kök (meal)
- Kök ve lemma §5 adımları `pipeline/src/mutalaa_pipeline/enrich/` altında (komut öneri: `uv run mutalaa enrich tr-roots --source elmalili-meal`): belirteç ve iki anahtar (A05), izafet, harf-i tarif ve kesme ön bölmesi, zeyrek lemmatizasyonu, kaikki etimolojisi (yalnız eşleme ve madde bağlantısı saklanır), QAC kök envanterine eşleme, çözülmeyenler için dil modeli toplu işi (yalnız QAC envanterindeki en çok 20 aday; liste dışı çıktı atılır; üç istem çeşitlemesi ayrışırsa kuyruğun başı).
- Türkçe lemmalar `lemma` tablosunda `lang = 'tr'` satırıdır (`ar_lemma_id`, `etymological_only`, `origin`, `status = 'aday'`, `freq`). Her eşleme `review` açar; kart A15'in `kuyruk/lemma` rotasındadır. Onaylı eşlemelerden `tr_root_index` (ofset kanonik metinde kod noktası) ve `tr_form` üretilir.
- "Yalnızca etimolojik" işareti `(tr_lemma, kök)` çiftindedir (§6); örnekleri editör doğrular.
- **Bitti sayılır:** onaylı eşlemelerden `tr_root_index` ve `tr_form` dolu; her `span` meal metni uzunluğu içinde (G-CAP).

### A18.3 · Kur'an içi `kok`, `lemma` ve `benzer_ayet`
- `kok` ve `lemma`: âyetten âyete, Bağlantı modeli §6 formülüyle (`idf_n`, birim-birim skor); birim başına ilk N satır. `license` QAC nedeniyle `bekliyor` olur (§4 madde 5: en kısıtlayıcı değer). `lemma` bağlantıları QAC lemmalarıyla %100 tutarlı olmalıdır (Test stratejisi §4).
- `benzer_ayet`: Tanzil üzerinde kendi n-gram indeksimiz; skor `min(1, ortak/7)·(0,5 + 0,5·kapsama)`, `evidence.subtype = 'sozluksel'`. QUL ve QurSim kaynaklı satırlar kullanılırsa `license = 'bekliyor'` ile girer ve yalnız `dev`'de kalır (Bağlantı modeli §5; K-06); `internal` ve `public` için sözlüksel satırlar kendi indeksimizden gelir.
- Yükleme doğal anahtarla upsert yapar (Bağlantı modeli §4 madde 3); yeni çalışmada üretilmeyen `aday` satır silinir, `onayli` satır "yeniden doğrula" kaydıyla kuyruğa düşer. Her satır `evidence.src_hash`, `dst_hash`, `source_id` taşır.
- **Bitti sayılır:** üç tür `xref` içinde `aday`; lemma tutarlılık testi yeşil; ikinci çalıştırma `onayli` satırlara dokunmuyor (test).

### A18.4 · Açık atıf ve iktibas motoru
- Açık atıf grameri İktibas tespiti §2'yi izler; `SURE_ADI` alternatifleri A11'in onaylı `surah_alias` satırlarından uzunluk sırasıyla derlenir; riskli adlar yalnız güçlü ipucuyla kabul edilir; sure ve âyet sınırı A04 dizisiyle denetlenir. A11'in onayı henüz yoksa gramer yalnız sayısal biçimleri (`(2:255)`, `[2/255]`) tanır; ad tabanlı biçimler onaydan sonra açılır.
- İktibas: Arapça dizilerin çıkarılması (§3), eşleştirme normalizasyonu (§4; A05 kuralları ve iki ek adım), 3–4 gram indeksi Uthmani ve Simple Clean üzerinde (§5), Smith-Waterman genişletme ve âyet sınırında bölme (§6), kısa ve kalıp ifade kuralları (§7; kalıp listesi editör onaylı dosya), bağlam sinyalleri (§8). Dil modeli doğrulaması yalnız `0,40 ≤ confidence < 0,80` aralığında ve yalnız `embed_ok = true` metinlerde çalışır (§9); sonuç `evidence.llm` alanına yazılır, durum `aday` kalır.
- Hazır araçlar (§11): ijaza ve quran-search-in-text geliştirme bölümünde aynı dizilerle koşulur; karar kuralı §11'dedir ve `/karar` ile yazılır.
- Testler sentetik Türkçe paragraflarla yazılır; Arapça diziler dokümandaki örneklerden ya da Tanzil dosyasından betikle alınır, hafızadan yazılmaz. Motor bugün onaylı meal üzerinde koşar (komut: `uv run mutalaa enrich citations --target elmalili-meal`; hedef adı öneri); tefsir A37'de, Risale İ-03'ten sonra eklenir.
- **Bitti sayılır:** motorun birim testleri yeşil; meal koşusu rapor üretiyor.

### A18.5 · Altın setler ve kapılar
- Setler `data/gold/` altında tutulur (git dışı, yedeklenir). Biçim, etiket sınıfları ve iki kişilik bağımsız etiketleme İktibas tespiti §10'u izler; ayrışmayı üçüncü kişi çözer; Cohen κ raporlanır; %40 geliştirme, %60 dondurulmuş test.
- Bu aşamada kurulan setler: kök (300–500 Türkçe lemma → kök çifti; şimdilik meal bandı, sıklık bandına göre tabakalı) ve `benzer_ayet` örneklemi. Atıf ve iktibas setinin biçimi ve etiketleme kuyruğu hazırlanır; içerik A37 (Elmalılı tefsir) ve İ-03 (Risale) sonrasında dolar.
- Ölçüm (komut öneri: `uv run mutalaa qa gold --type kok`): `prf`, açıklık eşleşmesi (aynı hedef ve örtüşme ≥ 0,5), κ. Eşikler Test stratejisi §4 tablosundadır; önceki kabul edilmiş koşuya göre 0,02'den fazla düşüş koşuyu kırar (öneri). Rapor `data/reports/{data_version}.json`.
- Yayın süzgeci: eşik tutmazsa o türün `aday` satırları pakete girmez. Raporun Yayınlayıcı'ya nasıl ulaşacağı dokümanda yoktur; öneri `/karar` ile yazılır ve `sunucu-gelistirici` Yayınlayıcı'ya ekler.
- Bekleme noktası (İ-13): kök ve `benzer_ayet` setlerinin etiketlenmesi. `/asama` aşamayı ilerleme dosyasında `engelli` durumuna alır ve Not sütununa "İ-13 etiketleme bekleniyor" yazar; etiketleme bitince ölçüm koşar.
- **Bitti sayılır:** ölçüm araçlarının testleri yeşil; setler etiketlendiyse kapı raporu üretilmiş.

### A18.6 · Yayın
- `publish --flavor dev`: `xref_idx` satırları İçerik paketleri §4 kurallarıyla pakete dağılır; `approved` ve `folded` Bağlantı modeli §6 etiket tablosundan; `red` hiç girmez, `aday` yalnız `dev` ve `internal`'a (P-07); `license` izin vermeyen satır düşer. `tr_root_index` ve `tr_form` `kelime-kok` paketine girer.
- **Bitti sayılır:** `dev` manifestinde yeni sürümler; `internal` kuru çalıştırmasında `bekliyor` lisanslı bağlantılar yok.

## Kabul ölçütleri
- [ ] zeyrek, kaikki, N, araç seçimi ve yayın süzgeci kararları karar defterinde.
- [ ] `tr_root_index` satırlarının tamamı onaylı eşlemeden; her açıklık metin uzunluğu içinde ve yarı açık (test).
- [ ] `kok`, `lemma`, `benzer_ayet` satırları `xref` içinde; `lemma` tutarlılığı %100; ikinci çalıştırma `onayli` satırları değiştirmiyor, üretilmeyen `aday` satırları siliyor (testler).
- [ ] QAC'ye dayanan bağlantıların `license` değeri `bekliyor`; QUL ve QurSim kaynaklı satırlardan `internal` ve `public` derlemeye giren 0 (SQL ve kapı raporu).
- [ ] Atıf ve iktibas motorunun birim testleri yeşil; gri bölge dışında dil modeli çağrısı yok; `embed_ok = false` kaynağa gönderim yok.
- [ ] Ölçüm araçları (`prf`, açıklık örtüşmesi, κ, gerileme kuralı) testli; etiketleme bittiyse kök ve `benzer_ayet` kapı raporları `data/reports/` altında.
- [ ] `dev` yayını `xref_idx` taşıyor; `internal` kuru çalıştırmasında `bekliyor` lisanslı satır yok.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check)
(cd pipeline && uv run mutalaa enrich citations --target elmalili-meal --dry-run)
(cd pipeline && uv run mutalaa qa run --source elmalili-meal --gate G-CAP)
(cd pipeline && uv run pytest && uv run ruff check .)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT type, status, license, count(*) FROM icerik.xref GROUP BY 1, 2, 3 ORDER BY 1, 2, 3;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.tr_root_index;"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
```

## Dikkat
- Âyet ↔ meal ve âyet ↔ tefsir ilişkisi çapadan türetilir; `xref`'e yazılmaz (K-27). Âyet aralığı çapası `xref` ucu olmaz; âyet başına satır ve `evidence.group` kullanılır.
- Uçlar birim düzeyindedir; Kur'an ucunda aralık kelime konumu, metin biriminde kod noktasıdır (`toUnitSpan`).
- Risale metni işlenmez, Risale parçası teste konmaz; sentetik paragraflar "Deneme paragrafı" biçimindedir.
- Dil modeli yalnız aday puanlar; kararı editör verir. `ima` ve `konu` otomatik yayımlanmaz.
- Reddedilen bağlantı başka yoldan yeniden önerilmez: doğal anahtar `origin` içermez.
- Günlüklere metin yazılmaz.

## İnsan adımları
- İ-13 · Altın set etiketleme: A18.5'te kök ve `benzer_ayet` setleri; atıf ve iktibas seti A37 ve İ-03'ten sonra. Bekleme noktaları ilerleme dosyasına yazılır.
- İ-12 · Türkçe kelime → kök eşlemelerinin editör onayı: A18.2'de; kelime anlamı onayıyla aynı editör işidir ([İnsan adımları](../06-insan-adimlari.md)).
- İ-17 (API anahtarı) A16 ve A17'de tamamlanmış olmalıdır.

## Çıktılar
- `pipeline/src/mutalaa_pipeline/enrich/` kök hattı, bağlantı üreteçleri, atıf ve iktibas motoru, kalıp listesi; `qa/` altın set ölçümleri; testler
- PostgreSQL'de `lemma` (`tr`), `tr_root_index`, `tr_form`, `xref` ve `review` kayıtları
- `data/gold/` setleri (git dışı); `data/reports/{data_version}.json`
- Yayınlayıcıda tür bazında süzgeç (karara göre); `dev` kanalında yeni paket sürümleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A18-baglantilar-ve-altin-setler.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A17](./A17-kelime-katmani.md) · Sonraki: [A19](./A19-hadis-hatlari.md)
