# Kelime Anlamları
> **Sürüm:** 1.0 · **Tarih:** 18 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-19](../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-13](../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-12](../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python)

K-19 gereği Kur'an kelimelerinin Türkçe anlamlarını kendimiz yazarız: yapay zekâ lemma başına taslak çıkarır, insan onaylar. Yeniden kullanılabilir açık lisanslı bir Türkçe kelime meali yok: QuranWBW "copying them is not allowed" diyor, hablullah/data-quran CC BY-NC-ND lisanslı ([QuranWBW](https://legacy.quranwbw.com/2); [data-quran](https://github.com/hablullah/data-quran)). İş yükü farklı lemma sayısına bağlıdır; 77.429 kelimenin her biri ayrı yazılmaz. K-06 uygulama notu gereği QAC kaynaklı kök ve lemma verisi `core` paketinden ayrı bir pakette tutulur (önerilen ad `kelime-kok`); onaylı Türkçe anlamlar da bu paketle kelime kartına gider ([İçerik paketleri](../03-veri/03-icerik-paketleri.md)).

## 1. Kapsam

- **İş birimi lemmadır.** Lemma ve kök kimlikleri Quranic Arabic Corpus (QAC) v0.4'ten gelir. Kökün temel anlamı `root` tablosunda kök başına bir kez yazılır; lemmanın Kur'an'daki anlamları `lemma` tablosunda tutulur.
- **Kelime kartında görünen.** Arapça kelime (Tanzil), Türkçe kısa anlam, kök ve "Bu kök Kur'an'da N yerde geçer" bilgisi, kısa morfoloji satırı. Kartın tasarımı [Okuma deneyimi](../01-urun/02-okuma-deneyimi.md) dosyasındadır.
- **v1 dışı.** Âyet içindeki her geçiş için ayrı bağlam anlamı (Açık soru).
- **Bağımlılıklar.** `kelime-kok` paketi QAC'den yazılı açıklık gelene kadar `bekliyor` durumundadır; bu sürede yalnız ekip içi `dev` derlemelerinde görünür, `internal` ve `public` derlemelere giremez (K-06; [Kaynaklar ve lisans defteri](./01-kaynaklar-ve-lisans-defteri.md)). Türkçe anlamlar bizim yazımımızdır; ama bir kelimenin anlamını göstermek için QAC'nin kelime → lemma eşlemesine bağlıdır. Bağımlılık ve yedek yol bölüm 2.1'dedir. Kelime anlamlarının Kurul açısından meal sayılıp sayılmadığı Açık soru; cevap paket manifestindeki `kurul_gerekli` değerini belirler.

## 2. Lemma envanteri

Sayılar hatta ölçülür, elle yazılmaz. Kaynaklardaki kelime sayıları bile farklıdır: QAC 77.429 kelime diyor ([QAC SSS](https://corpus.quran.com/faq.jsp)), QUL'un morfoloji kategorisi 77.432 öğe listeliyor ([QUL kaynaklar](https://qul.tarteel.ai/resources)). Fark büyük olasılıkla kelime bölme farkından gelir; G-BUT kapısı farkı raporlar ve çözer ([İçerik hattı](./02-icerik-hatti.md)). Farklı lemma ve kök sayıları araştırmada bulunamadı; aşağıdaki sorgularla çıkarılır.

- **Girdi.** QAC v0.4 morfoloji dosyası. Dosya biçimi (satır başına kelime parçası, özellik alanında lemma ve kök) indirilen dosyada Doğrulanacak.
- **Çapraz kontrol.** QUL lemma SQLite dosyası: `lemmas(id, text, text_clean, words_count, uniq_words_count)` ve `word_lemmas(lemma_id, word_location)`, konumlar `2:3:5` biçiminde ([QUL lemma](https://qul.tarteel.ai/resources/morphology/75)). QUL kaynağının lisansı `bekliyor` olduğu için yalnız iç sayım için kullanılır.
- **Kimlik.** `lemma.id` bizim verdiğimiz kalıcı tamsayıdır ve yeniden numaralanmaz. QAC lemma dizgisi ayrı alanda tutulur. Aynı yazılışlı farklı lemmaların QAC'de nasıl ayrıldığı Doğrulanacak.

```bash
uv run mutalaa ingest qac
uv run mutalaa enrich morphology                 # quran_word ↔ lemma ↔ root
uv run mutalaa export pg --source qac-morfoloji
```

```sql
-- Sütun adları örnektir; kesin şema Editoryal veritabanı dosyasında
SELECT count(DISTINCT lemma_id) AS lemma_sayisi,
       count(DISTINCT root_id)  AS kok_sayisi,
       count(*)                 AS kelime_sayisi
FROM quran_word;

-- Sıklık sırası ve kümülatif kapsama (dalgaları bu tablo belirler)
WITH f AS (
  SELECT lemma_id, count(*) AS n
  FROM quran_word
  WHERE lemma_id IS NOT NULL
  GROUP BY lemma_id
)
SELECT lemma_id, n,
       row_number() OVER (ORDER BY n DESC, lemma_id) AS sira,
       round(100.0 * sum(n) OVER (ORDER BY n DESC, lemma_id) / sum(n) OVER (), 2) AS kumulatif_kapsama
FROM f
ORDER BY sira;
```

```python
# QUL ile çapraz sayım (dosya adı indirilen pakette doğrulanır)
import sqlite3
con = sqlite3.connect("data/raw/qul-lemma-75/2026-10-18/lemmas.sqlite")
qul = con.execute("""
    SELECT l.id, l.text, COUNT(*) AS n
    FROM lemmas l JOIN word_lemmas w ON w.lemma_id = l.id
    GROUP BY l.id ORDER BY n DESC
""").fetchall()
```

### 2.1 QAC bağımlılığı ve yedek yol

Anlam metni ile QAC verisi ayrı tutulur. Anlamlar bizim kalıcı `lemma.id` kimliğimize bağlanır; QAC'nin lemma dizgisi ve kelime → lemma ataması ayrı tablolarda durur. Böylece lemma kaynağı değişse de anlamlar yeniden yazılmaz.

```sql
-- Öneri; kesin şema Editoryal veritabanı dosyasında
CREATE TABLE lemma_kaynak (
  lemma_id       int  NOT NULL REFERENCES lemma(id),
  kaynak         text NOT NULL,      -- 'qac-0.4'; yedek yolda 'mutalaa-morfoloji'
  kaynak_anahtar text NOT NULL,      -- QAC lemma dizgisi (gerekirse sözcük türüyle)
  PRIMARY KEY (kaynak, kaynak_anahtar)
);
-- quran_word satırı lemma atamasının kaynağını da taşır (ör. lemma_kaynak = 'qac-0.4').
```

| QAC'nin cevabı | Sonuç |
|---|---|
| Yazılı izin | `kelime-kok` `serbest` olur. Atıf ve GPL bildirimi eklenir; dosya değiştirilmez, düzeltmeler ayrı katmanda tutulur |
| Yalnız ticari olmayan kullanım | Gelir modeli olmayan bugünkü durumun (K-22) bu şarta uyup uymadığı avukata ve proje sahibine sorulur; fiyatlandırma kararında yeniden değerlendirilir. O zamana kadar `bekliyor` |
| Ret ya da cevap yok | Kelime → lemma ve kök ataması kendimiz üretilir: Tanzil metni üzerinde CAMeL Tools (MIT) çözümlemesi ve sıklık dalgalarıyla insan doğrulaması. `lemma.id` ve anlamlar korunur; yalnız `lemma_kaynak` eşlemesi değişir. Ayrılan ya da birleşen lemmalar `kullanim_disi` ve yönlendirmeyle çözülür |

- Araştırma notu Kur'an kelimeleri için çözümleyici yerine insan doğrulamalı QAC verisini öneriyor. Yedek yol bu yüzden pahalıdır ve insan doğrulaması zorunludur.
- QUL'un ve Quranpedia'nın morfoloji verisi QAC'den türediği için bağımsız yedek sayılmaz. Quranpedia lisansı morfolojinin QAC'den (GNU GPL, atıf zorunlu) geldiğini söylüyor ([Quranpedia LICENSE](https://quranpedia.net/dumps/LICENSE.md); [QUL krediler](https://qul.tarteel.ai/credits)).
- QAC'nin 2. sürümü geliştiriliyor; standart veri setleri henüz yayımlanmadı ([kaisdukes/quranic-corpus](https://github.com/kaisdukes/quranic-corpus)). Lisansı netleşirse yedek olabilir (Doğrulanacak).
- Taslak istemleri QAC etiketlerini kullanır (`embed_ok`, lisans defteri). QAC'nin cevabı bunu kısıtlarsa istem yalnız Tanzil metni, Elmalılı meali ve bizim lemma biçimimizle çalışır.

## 3. Önceliklendirme

| Dalga | Kapsam | Not |
|---|---|---|
| 0 | Harf ve zamirler | Çok sık geçer; dil bilgisi işleviyle anlamlandırılır |
| 1 | Kelime geçişlerinin ilk %50'sini kapsayan lemmalar | |
| 2 | %80'e kadar | |
| 3 | %95'e kadar | |
| 4 | Kalanlar (az geçenler) | |

Dalgadaki lemma sayısı bölüm 2'deki sorgudan okunur. Zipf dağılımı nedeniyle ilk dalgaların az sayıda lemmayla büyük kapsama vermesi beklenir (araştırma notu çıkarımı). Dalga içinde lemmalar köke göre gruplanır; aynı kökün lemmaları aynı oturumda incelenir ve anlamlar tutarlı kalır. Proje sahibi isterse Fâtiha ve 30. cüz lemmaları öne alınabilir.

## 4. Anlam yazım kılavuzu

| Alan | İçerik | Kural |
|---|---|---|
| `anlam_kisa` | Kelime kartında görünen karşılık | 1–4 kelime; en fazla 3 karşılık, noktalı virgülle ayrılır |
| `kok_anlami` | Kökün temel anlamı (`root` tablosunda) | Bir cümleyi geçmez |
| `kuran_anlamlari` | Lemmanın Kur'an'daki kullanımları | En fazla 3 madde; sözlük anlamı |
| `tur` | Sözcük türü | QAC etiketinden gelir; elle yazılmaz |
| `turkce_es_kelime` | Türkçede yaşayan aynı kökenli kelime | Varsa |
| `yalnizca_etimolojik` | Türkçe eş kelimenin anlamı Kur'an'daki anlamdan kaymış | Bayrak |
| `editor_notu` | İç not | Uygulamada görünmez |

1. Sözlük anlamı yazılır. Tefsir, mezhep tercihi, fıkhî hüküm, öğüt ve âyete özel yorum yazılmaz.
2. Fiiller mastarla (-mak/-mek), isimler yalın tekil, sıfatlar sıfat olarak yazılır.
3. Harf ve edatlarda önce işlev parantez içinde, sonra karşılık yazılır: "(edat) içinde".
4. Günümüz Türkçesi kullanılır. Arapça kökenli terim Türkçede yerleşikse kullanılır (rahmet, sabır). Arapça kökenli terimlerin düzeltme işareti kullanımı proje kılavuzuyla tutarlıdır ([Elmalılı hazırlığı](./03-elmalili-hazirligi.md)).
5. Terim anlamı ile sözlük anlamı ayrı maddeye yazılır.
6. Korumalı meallerden ve kelime meallerinden ifade alınmaz; editör yazarken bunlara bakmaz. Elmalılı meali serbest olduğu için bağlam örneği olarak kullanılabilir.
7. Emin olunmayan durumda karşılık uydurulmaz; madde "emin değil" diye işaretlenir ve uzmana gider.

Örnekler (editör doğrular):

| Lemma | `anlam_kisa` | `kuran_anlamlari` |
|---|---|---|
| أَرْض | yer; yeryüzü | yer, yeryüzü; toprak, ülke |
| سَمَاء | gök | gök, sema |
| صَبَرَ | sabretmek | sabretmek, katlanmak; direnmek |
| فِي | (edat) içinde | içinde; hakkında |

**"Yalnızca etimolojik" bayrağı.** Türkçedeki anlamı Kur'an'daki anlamından kaymış kelimeler ayrıca etiketlenir (rapor). Örnek aday: "millet" Türkçede "ulus" anlamında yaygındır; Kur'an'daki kullanımı "din, yol" yönündedir (editör doğrular). Bayrak iki yerde kullanılır:
- Kelime kartında `turkce_es_kelime` gösterilirken "Türkçedeki anlamından farklı" uyarısı çıkar.
- Türkçe metindeki bir kelimeden Arapça köke giden `xref` bağlantısında (`type = 'kok'` ya da `'lemma'`) `evidence.yalnizca_etimolojik = true` yazılır; bağlantı panelinde gerekçe etiketi buna göre değişir ve sıralamada aşağı iner ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)).

## 5. Yapay zekâ taslak istemi

- **Girdi.** Lemma (harekeli Arapça), QAC kökü ve türü, sıklık, en fazla 8 örnek âyet (Tanzil Arapçası ve âyetin Elmalılı meali; meal hazır değilse yalnız Arapça), aynı kökün onaylı anlamları, kılavuz özeti.
- **Girmeyenler.** Korumalı mealler ve kelime mealleri; Quran Foundation içeriği; kişisel veri. Genel kural: girdi birimlerinin her kaynağı `embed_ok = true` olmalıdır; hat bunu çağrıdan önce denetler ([İçerik hattı](./02-icerik-hatti.md)).
- **Ayarlar.** Claude Haiku 5.5, Batch API, sıcaklık 0. İstem `pipeline/prompts/kelime-anlami/v1.md` dosyasında sürümlüdür. Çıktı JSON şemasıyla doğrulanır; taslağın kökü QAC kökünden farklıysa çıktı reddedilir.
- **Çoklu taslak (isteğe bağlı).** İki farklı istem sürümüyle iki taslak alınır; ayrışan maddeler incelemede öne çıkar. Yayımlanmış bir protokol üç dil modelinin çoğunluk oyunu kullanıyor ve üç modelin ayrıştığı maddeleri insana yönlendiriyor ([protocols.io](https://www.protocols.io/view/llm-assisted-expert-annotation-for-systematic-lite-4r3l2dw5jg1y/v1.pdf)).

```text
SİSTEM
Kur'an Arapçası için Türkçe lemma anlamı TASLAĞI yazıyorsun. Taslağı bir editör onaylayacak.
Kurallar:
- Yalnız sözlük anlamı yaz. Tefsir, mezhep tercihi, fıkhî hüküm ve öğüt yazma.
- anlam_kisa 1–4 kelime; en fazla 3 karşılık; noktalı virgülle ayır.
- Fiilleri mastarla (-mak/-mek), isimleri yalın tekil yaz. Harf ve edatlarda önce işlevi parantezle yaz.
- Verilen QAC kökünü kullan; kök önerme.
- Emin değilsen "emin_degil": true yaz; karşılık uydurma.
- Yalnız verilen JSON şemasıyla cevap ver.

KULLANICI
lemma: {lemma_ar}   QAC: {qac_lemma}   tür: {pos}   kök: {kok_ar}   sıklık: {n}
aynı kökün onaylı anlamları: {kardes_anlamlar}
örnek âyetler (Arapça | Elmalılı meali):
{ornekler}
```

```json
{
  "lemma_id": 1234,
  "anlam_kisa": "sabretmek",
  "kuran_anlamlari": ["sabretmek, katlanmak", "direnmek"],
  "kok_anlami_onerisi": "tutmak, katlanmak",
  "turkce_es_kelime": "sabır",
  "yalnizca_etimolojik_adayi": false,
  "emin_degil": false,
  "dayanak_ayetler": ["q:2:153", "q:3:200"],
  "gerekce": "Editör için kısa gerekçe"
}
```

Taslaklar veritabanına `status = 'aday'`, `dogrulanmis = false`, model, istem sürümü ve girdi hash'iyle girer ([İçerik hattı, yapay zekâ politikası](./02-icerik-hatti.md)).

## 6. Editör panelinde inceleme

- **Kuyruk.** Dalga sırasına, dalga içinde köke göre dizilir.
- **Kart.** Lemma, kök, tür, sıklık; KWIC dizini (az geçen lemmada bütün geçişler, sık geçende örneklem) Arapça ve Elmalılı mealiyle; taslak alanları; aynı kökün onaylı anlamları; kılavuz uyarıları (uzunluk, tefsir dili, eksik alan).
- **Eylemler.** Onayla; Düzenle ve onayla; Reddet ve yeniden taslak iste; Uzmana gönder; "yalnızca etimolojik" işaretle.
- **Kayıt.** Her eylem `review` tablosuna yazılır: inceleyen, eylem, önceki ve sonraki değer, süre, not. Madde başına harcanan süre maliyet tahminini besler.
- **Durum.** `aday` → `onayli` ya da `red`. `dev` derlemelerinde taslaklar "doğrulanmamış" rozetiyle görünür (K-25). Paket `serbest` olunca `public` derlemeye yalnız `onayli` anlamlar girer; `internal` derlemede onaysız taslakların gösterilip gösterilmeyeceği Açık soru ([İçerik paketleri](../03-veri/03-icerik-paketleri.md)).
- **İnceleyen.** Arapça ve Türkçe yetkinliği olan kişi. Rol ve yetkiler [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) dosyasında.

## 7. QA: iki gözden geçirenli örneklem ve uyum ölçüsü

1. **Kalibrasyon.** Dalga 1'den önce inceleyenler 30 maddeyi birlikte işler ve kılavuzu örneklerle netleştirir. Protokolde insanlar 11 maddeyle kalibre olup 20 maddeyle altın veri kurmuş, 66 maddeyle doğrulama yapmıştır ([protocols.io](https://www.protocols.io/view/llm-assisted-expert-annotation-for-systematic-lite-4r3l2dw5jg1y/v1.pdf)).
2. **Çift değerlendirme seti.** Dalga ve sözcük türüne göre tabakalı 300 lemma seçilir. İki inceleyen aynı taslağı birbirinden habersiz `kabul`, `duzelt`, `red` diye değerlendirir. Uyum Cohen kappa ile ölçülür: `κ = (p_o − p_e) / (1 − p_e)`; `p_o` gözlenen uyum, `p_e` şans uyumu. Protokolde insanlar arası κ 0,60 ± 0,24, üç modelin çoğunluk oyu ile insan arası κ 0,57 ± 0,08 bulunmuş. Hedef: inceleyenler arası κ ≥ 0,60. Altında kalırsa kılavuz netleştirilir ve kalibrasyon tekrarlanır.
3. **Onay sonrası ikinci okuma.** Her dalgada onaylı maddelerden rastgele örneklem (en az 300 ya da %10) ikinci bir inceleyene gider: `dogru`, `kucuk_hata`, `yanlis`. `yanlis` oranı %95 Wilson aralığıyla raporlanır. Öneri eşiği: üst sınır ≤ %2; aşılırsa dalga yeniden incelenir.
4. **Taslak kalitesi.** Değiştirilmeden kabul oranı, düzenleme mesafesi ve ret oranı sözcük türüne göre izlenir; istem bu verilere göre sürüm atlar.
5. **Hakemlik.** İki inceleyen ayrışırsa üçüncü kişi karar verir; karar kılavuza örnek olarak eklenir.

## 8. Sürümleme

- Veri seti `kelime-anlam-tr` adıyla anlamsal sürüm taşır. Her madde `surum` ve `content_hash` taşır; değişiklik `review` kaydıyla izlenir; iki sürüm arasında fark raporu üretilir.
- Anlam metni bizim ürettiğimiz metindir; ilk kayıtta NFC'ye çevrilir ve `content_hash` bu metinden hesaplanır (K-26).
- `lemma.id` yeniden numaralanmaz. QAC düzeltmesiyle bir lemma kalkarsa madde `kullanim_disi` olur ve yeni lemmaya yönlendirilir.
- `kelime-kok` paketi `data_version` taşır. Kelime anlamları Kurul kapsamına girerse (`kurul_gerekli`) her değişiklik yeniden onay gerektirebilir; bu yüzden düzeltmeler planlı sürümlerde toplu yayımlanır.

## 9. Kelime anlamlarının lisansı (Açık soru)

| Seçenek | Artı | Eksi |
|---|---|---|
| CC BY-SA 4.0 | Eski plan kendi üretimimiz için bunu öneriyordu (`quran-app-docs/11-icerik-edinim/01-veri-kaynaklari.md`); türevler açık kalır | Paylaşım koşulu bazı kullanıcıları uzaklaştırır |
| CC BY 4.0 | Yaygın yeniden kullanım | Türevler kapatılabilir |
| CC0 | En geniş kullanım | Atıf zorunluluğu kalkar |
| Tüm hakları saklı | Tam denetim | Topluluk katkısı ve yeniden kullanım kapanır |

Dikkat edilecek iki nokta: saf makine çıktısında insan "hususiyeti" olmadığı için büyük olasılıkla FSEK koruması doğmaz (araştırma notu); korunacak değer insanın düzenlediği anlamlardır. Anlam tablosu kendi `lemma.id` kimliğimize bağlıdır ve QAC eşlemesi ayrı tablodadır (bölüm 2.1); bu ayrımın GPL açısından yeterli olup olmadığı avukata sorulur. Karar proje sahibinindir.

## 10. Maliyet tahmini

| Kalem | Formül | Örnek (varsayım) |
|---|---|---|
| Yapay zekâ taslağı | `N × k × (T_girdi × p_girdi + T_cikti × p_cikti) / 10⁶` | Haiku 5.5 Batch fiyatıyla (girdi 0,05 $, çıktı 0,25 $ / milyon token) `T_girdi = 1.500`, `T_cikti = 250`, `k = 1`: 1.000 lemma ≈ 0,14 $; `k = 2` ile ≈ 0,28 $ |
| İnceleme | `N × t_madde` | `t_madde = 2 dk` ise 1.000 lemma ≈ 33 saat |
| QA | `300 × 2 × t_değerlendirme` + ikinci okuma örneklemi | Pilotta ölçülür |

Fiyatlar [Claude fiyatlandırma](https://platform.claude.com/docs/en/about-claude/pricing) sayfasından alındı (18 Ekim 2026). Token sayıları 50 lemmalık pilotta token sayma uç noktasıyla ölçülür (`uv run mutalaa llm estimate --task glosses --sample 50`); `t_madde` aynı pilotta kronometreyle ölçülür. Bu ölçekte asıl maliyet insan zamanıdır.

## 11. Açık sorular

1. QAC lisansı: yazılı açıklama gelmeden `kelime-kok` paketi (kök, lemma ve anlamlar) `internal` ve `public` derlemelere giremez; yedek yol bölüm 2.1'de.
2. Kurul: kelime anlamları meal sayılır mı?
3. Onaysız taslaklar `internal` derlemede "doğrulanmamış" rozetiyle gösterilecek mi, gizlenecek mi?
4. Onaylı maddelerde rozet kalkar mı? Öneri: rozet kalkar, ayrıntıda "yapay zekâ taslağı, insan onaylı" kaynak satırı görünür (K-25'in yorumu).
5. Âyet içi bağlam anlamı ne zaman ve hangi veri modeliyle gelecek?
6. Kelime anlamlarının lisansı.
7. QAC'de aynı yazılışlı lemmaların ayrımı (Doğrulanacak).

## İlgili dosyalar
- [Kaynaklar ve lisans defteri](./01-kaynaklar-ve-lisans-defteri.md) · [İçerik hattı](./02-icerik-hatti.md) · [Elmalılı hazırlığı](./03-elmalili-hazirligi.md) · [Risale hazırlığı](./05-risale-hazirligi.md)
- [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) · [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md)
- [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md) · [Arama](../03-veri/05-arama-fts5.md)
- [Okuma deneyimi](../01-urun/02-okuma-deneyimi.md) · [Mobil ekranlar](../01-urun/03-mobil-ekranlar.md) · [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md)
