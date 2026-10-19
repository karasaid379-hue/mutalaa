# A17 · Kelime katmanı: `quran_word`, `kelime-kok` (QAC), Türkçe anlam taslakları

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-19](../../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-12](../../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · [A11](./A11-kuran-yapisi-ve-sayfa-eslemesi.md) (A11.2 yeterli) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-04 · İ-12 · İ-17
> **Ajanlar:** `hat-gelistirici` · `lisans-denetcisi` · `arastirmaci` · `sunucu-gelistirici` (paket tanımı gerekirse) · `test-yazari` · `inceleyici` · **Beceriler:** `icerik-hatti` · `lisans-kapisi` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan dalgaları ayrıca
> **Başlat:** `/asama A17`

## Amaç
Kur'an'ın kelime katmanı tamamlanır: A11'in yazdığı Tanzil kelime bölmesine (`quran_word`) QAC v0.4'ten kök, lemma ve morfoloji eklenir. QAC düzeltme katmanı ve K-19 gereği lemma başına Türkçe anlam taslakları da bu aşamada kurulur. QAC kaynaklı veri `core` dışında, `kelime-kok` paketinde ve QAC'den yazılı açıklık gelene kadar `bekliyor` durumundadır; yalnız `dev` derlemede görünür. Yapay zekâ taslak üretir, insan dalga dalga onaylar (İ-12).

## Okunacak belgeler
- [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §1–§4, §7 IDF, §8 cihaz verisi (§5 Türkçe → kök hattı A18'dedir)
- [Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md): tamamı
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.2 QAC ve QUL, §8 yazışma 4
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §5 `root`, `lemma`, `lemma_gloss`, `quran_word`, `quran_word_fix`; §8 `review`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.2 `core.quran_word`, §3.3 `kelime-kok`, §7
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §9 G-BUT ve G-YZ, §10 yapay zekâ politikası, §11 maliyet
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §6 kelime numaraları ve ÇŞ-1 · [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 `lemma` eşiği

## Kapsam
**Yapılır**
- `quran_word`: A11'in yazdığı Tanzil satırlarının denetimi ve QAC alanlarının doldurulması.
- QAC alımı (`qac-morfoloji`), segmentlerin kelimeye toplanması, `root`, `lemma`, morfoloji alanları, sayılar ve IDF.
- `quran_word_fix` katmanı; lemma envanteri ve sıklık dalgaları; QUL ile iç çapraz sayım.
- Kelime anlamı taslakları, JSON şeması, `lemma_gloss` adayları ve QA araçları; `kelime-kok` paketinin `dev` yayını.

**Yapılmaz**
- Türkçe kelime → Arapça kök hattı (`tr_root_index`, `tr_form`) ve `kok`/`lemma` bağlantıları (A18; meal gerektirir).
- Kelime kartı arayüzü (A25). QAC olumsuz cevap verirse yedek yol (Kelime anlamları §2.1) ayrı karar ve iş olarak planlanır.

## Adımlar
### A17.1 · Doğrulamalar ve QAC durumu
- `arastirmaci` resmî kaynaktan doğrular: QAC v0.4 morfoloji dosyasının indirme yolu, biçimi (segment satırları, lemma ve kök alanları) ve iki lisans metni; QAC'de aynı yazılışlı lemmaların ayrımı; QUL lemma kaynağının numarası ve dosya biçimi; Claude Haiku 5.5 model kimliği ve Batch API kullanımı ([İçerik hattı](../../04-icerik/02-icerik-hatti.md) §13 madde 5).
- İ-04: A01'de gönderilen QAC e-postasına cevap geldiyse `lisans-denetcisi` lisans defterine ve `source` kaydına işler. Gelmediyse `qac-morfoloji` `bekliyor` kalır ve aşama sürer.
- İndirme bir form ya da onay istiyorsa dosyayı kullanıcı indirir ve proje klasörüne koyar.
- **Bitti sayılır:** A06'da açılan `pipeline/sources/qac-morfoloji.toml` doğrulanmış adres ve tarihli lisans kopyasıyla güncel; `uv run mutalaa sources check` 0.

### A17.2 · `quran_word` denetimi (A11'in satırları)
- Tanzil kelime bölmesi A11.2'de yazıldı ve `core`'a girdi. Bu adım satırları yeniden üretmez: satır sayısını, 6.236 âyetin kapsandığını ve A11'in dilim eşitliği testinin yeşil olduğunu denetler; QAC birleştirmesine (A17.3) hazırlar. Satırlar yoksa (A11.2 bitmemiş) aşama durur ve `/asama A11` önerilir.
- **Bitti sayılır:** satır sayısı ve âyet kapsamı raporda; A11'in testleri yeşil.

### A17.3 · QAC alımı, morfoloji ve sayılar
- `uv run mutalaa ingest qac`: dosya `data/raw/qac-morfoloji/{tarih}/` altına SHA-256 ile yazılır ve hiç değiştirilmez.
- `uv run mutalaa enrich morphology`: segmentler kelime düzeyine toplanır; kök ve lemma gövde segmentinden gelir. Âyet başına kelime sayısı Tanzil bölmesiyle karşılaştırılır (durak işaretleri hariç); farklar editöre liste olarak gider (G-BUT raporlar; ÇŞ-1). Kelime numarası QAC konumudur; Tanzil bölmesi ayrışırsa eşleme önerisi planda sunulur ve `/karar` ile yazılır.
- `root`, `lemma` (`lang = 'ar'`, `qac_ref`), `quran_word.root_id`, `lemma_id`, `pos`, `features`, `morph_source = 'qac-morfoloji'`; `occurrences`, `ayah_count` ve `idf_q = ln(6236 / ayah_count)`.
- `root.id` ve `lemma.id` kalıcıdır; ikinci çalıştırma QAC dizgisine göre aynı kimlikleri verir.
- `quran_word` satırlarında yalnız QAC sütunları güncellenir; Tanzil sütunları ve satırların kendisi A11'indir (A11.2 sütun sahipliği).
- `uv run mutalaa export pg --source qac-morfoloji`.
- **Bitti sayılır:** her `quran_word.lemma_id` QAC dosyasındaki lemmayla eşleşiyor (Test stratejisi §4: QAC'den türetme %100 tutarlı).

### A17.4 · Düzeltme katmanı
- `quran_word_fix` önerileri `aday` girer ve `review` (`hedef_tablo = 'quran_word_fix'`) açar. Yayınlayıcı yalnız `onayli` düzeltmeleri uygular (P-09); künye "QAC v0.4 + Mütâlaa düzeltmeleri (N adet)".
- Panelde ayrı rota yoktur; kayıtlar `kuyruk/lemma` ekranında ya da API karar uçlarıyla işlenir (Açık soru; planda karar).
- **Bitti sayılır:** onaylı düzeltmenin uygulandığı, adayın uygulanmadığı test yeşil.

### A17.5 · Lemma envanteri ve dalgalar
- Kelime anlamları §2'deki sorgular lemma, kök ve kelime sayılarını ve kümülatif kapsamayı verir. Dalgalar §3'tedir: 0 harf ve zamirler, 1 ilk %50, 2 %80'e, 3 %95'e, 4 kalanlar. Dalga içinde lemmalar köke göre gruplanır.
- QUL çapraz sayımı yalnız iç denetimdir (`uv run mutalaa ingest qul --resource 75`); QUL verisi pakete girmez. QUL verisi ileride pakete alınacaksa Tarteel yazışması `/yazisma qul` ile hazırlanır (İ-26; A01 bu işi buraya bıraktı).
- Fâtiha ve 30. cüz lemmalarının öne alınıp alınmayacağı planda proje sahibine sorulur.
- **Bitti sayılır:** dalga tablosu sorgudan üretilmiş ve `data/reports/` altında.

### A17.6 · Anlam taslakları ve QA araçları
- İstem `pipeline/prompts/kelime-anlami/v1.md` (Kelime anlamları §5). Çıktı JSON şemasıyla doğrulanır; kökü QAC kökünden farklı taslak reddedilir; geçersiz çıktı bir kez yeniden denenir, sonra kuyruğa düşer.
- Girdi: lemma, QAC kökü ve türü, sıklık, en çok 8 örnek âyet (Tanzil Arapçası; Elmalılı meali onaylıysa meal, değilse yalnız Arapça) ve aynı kökün onaylı anlamları. Korumalı mealler, QF içeriği ve kişisel veri girmez; çağrıdan önce `require_embed_ok` çalışır.
- Pilot: `uv run mutalaa llm estimate --task glosses --sample 50`. Maliyet ve madde başı süre kullanıcıya sunulur; İ-17 bütçesiyle onaylanır.
- `uv run mutalaa enrich glosses --wave 1`: Batch API, sıcaklık 0. `lemma_gloss` satırları `status = 'aday'` ve `origin = 'yz:{model}'` ile girer; G-YZ alanları A16.4'teki kararla tutulur (`dogrulanmis = false`; A16'dan önce çalışıyorsa karar burada verilir). Her taslağa `review` (`hedef_tablo = 'lemma_gloss'`, `alan = 'anlam_kisa'`).
- QA araçları (Kelime anlamları §7): 30 maddelik kalibrasyon seti, 300 lemmalık çift değerlendirme ve Cohen κ (hedef ≥ 0,60), onay sonrası ikinci okuma (en az 300 ya da %10) ve Wilson üst sınırı (öneri ≤ %2), taslak kalite ölçüleri. Kod `pipeline/src/mutalaa_pipeline/qa/` altında.
- **Bitti sayılır:** dalga 1 taslakları kuyrukta; QA araçlarının birim testleri yeşil.

### A17.7 · İnsan dalgaları ve yayın
- Bekleme noktası (İ-12): her dalgada kalibrasyon, çift değerlendirme, onay ve ikinci okuma insan işidir. `/asama` aşamayı ilerleme dosyasında `engelli` durumuna alır ve Not sütununa dalga numarasını ve bekleyen işi yazar (ör. "İ-12 dalga 1 onayı"). Sonraki dalga `uv run mutalaa enrich glosses --wave N` ile açılır.
- Yayın: `kelime-kok` (`word_morph`, `root`, `lemma`, `lemma_gloss`) `publish --flavor dev` ile; `core.quran_word` A11'den beri pakettedir ve QAC alanlarını taşımaz. `dev`'de taslaklar "doğrulanmamış" rozetiyle görünür. `kelime-kok` `bekliyor` olduğu için `internal` ve `public`'e girmez (P-03, P-05). Paket tanımı A13'te yoksa `sunucu-gelistirici` ekler.
- **Bitti sayılır:** `dev` manifestinde `kelime-kok` var; `internal` kuru çalıştırmasında yok.

## Kabul ölçütleri
- [ ] A11'in `quran_word` satırları var ve dilim eşitliği testi yeşil; QAC ile kelime sayısı farkları raporda.
- [ ] QAC dosyasının SHA-256'sı kayıtlı ve yeniden hesapla aynı; `qac-morfoloji` `bekliyor` (ya da İ-04 cevabına göre güncel).
- [ ] Lemma türetme tutarlılığı %100; `root.id` ve `lemma.id` ikinci çalıştırmada değişmiyor (testler).
- [ ] Onaylı `quran_word_fix` uygulanıyor, aday uygulanmıyor (test).
- [ ] Dalga tablosu sorgudan üretilmiş; pilot maliyet tahmini kullanıcı onaylı.
- [ ] Dalga 1 taslakları `aday` ve `dogrulanmis = false`; G-YZ "geçti"; şema dışı çıktı 0.
- [ ] κ, ikinci okuma ve Wilson hesaplarının birim testleri yeşil.
- [ ] `kelime-kok` yalnız `dev` manifestinde; `internal` kuru çalıştırma raporunda P kodlarıyla dışarıda.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check)
(cd pipeline && uv run mutalaa ingest qac && uv run mutalaa enrich morphology)
(cd pipeline && uv run mutalaa qa run --source qac-morfoloji && uv run mutalaa export pg --source qac-morfoloji)
(cd pipeline && uv run mutalaa llm estimate --task glosses --sample 50)
(cd pipeline && uv run pytest && uv run ruff check .)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*), count(DISTINCT lemma_id), count(DISTINCT root_id) FROM icerik.quran_word;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT status, count(*) FROM icerik.lemma_gloss GROUP BY 1;"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
```

## Dikkat
- QAC dosyası değiştirilmez; düzeltmeler ayrı katmandadır. QAC verisi `core` paketine girmez (K-06 uygulama notu, P-05); `core.quran_word` yalnız Tanzil bölmesidir.
- Taslak yalnız sözlük anlamıdır: tefsir, mezhep tercihi, fıkhî hüküm ve öğüt yazılmaz; emin olunmayan maddede `emin_degil` işaretlenir. Onaysız taslak `public`'e girmez (P-08).
- Kelime anlamı kendi ürettiğimiz metindir; ilk kayıtta NFC uygulanır.
- Sayılar elle yazılmaz; 77.429 gibi değerler yalnız karşılaştırma bilgisidir. Kur'an kelimeleri hafızadan yazılmaz.
- QUL ve QF verisi pakete girmez; QF içeriği istemlere de girmez (`embed_ok = false`).
- Günlüklere metin yazılmaz; yapay zekâ çağrıları model, istem özeti, token ve maliyetle kaydedilir.

## İnsan adımları
- İ-04 · QAC cevabı: cevap gelmezse aşama `bekliyor` durumuyla sürer; olumsuz cevapta yedek yol `/karar` ile planlanır.
- İ-17 · Anthropic API anahtarı ve bütçe: A17.6 pilotundan önce gerekir.
- İ-12 · Kelime anlamı taslaklarının onayı: her dalgada bekleme noktası; ilerleme dosyasına yazılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/ingest/qac.py`, `enrich/morphology.py`, `enrich/glosses.py`, `qa/` uyum ve örneklem hesapları, testler
- `pipeline/sources/qac-morfoloji.toml` ve lisans kopyası; `pipeline/prompts/kelime-anlami/v1.md`
- PostgreSQL'de `quran_word` QAC alanları, `root`, `lemma`, `lemma_gloss`, `review` kayıtları
- `dev` kanalında `kelime-kok` paketi; karar defterinde ÇŞ-1 eşlemesi ve G-YZ kayıtları

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A17-kelime-katmani.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A16](./A16-elmalili-meali.md) · Sonraki: [A18](./A18-baglantilar-ve-altin-setler.md)
