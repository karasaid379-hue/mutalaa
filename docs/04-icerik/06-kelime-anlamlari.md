# Kelime Anlamları
> **Sürüm:** 1.4 · **Tarih:** 12 Kasım 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-19](../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-13](../00-ozet/02-karar-defteri.md#k-13--editör-paneli) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-42](../00-ozet/02-karar-defteri.md#k-42--kaynak-ilkesi-ve-kalite-temelli-görünürlük) · [K-12](../00-ozet/02-karar-defteri.md#k-12--i̇çerik-hattı-python) · [K-37](../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları) · [K-50](../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü)

K-19 gereği Kur'an kelimelerinin Türkçe anlamları için önce hazır kaynak aranır; uygun hazır kaynak her lemma için aday olur. Hazır anlamı yetmeyen lemmanın anlamını editör yazar. Yapay zekâ lemma taslağı proje sonuna ertelendi (K-50; [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) S-16) ve S-16'ya kadar kullanılmaz. Her durumda insan onaylar. A17 tedariki hazır kaynak olarak QuranWBW'nin Türkçe kelime anlamlarını seçti (bölüm 1). İş yükü farklı lemma sayısına bağlıdır (QAC v0.4'te 4.832 farklı lemma dizgisi); 77.429 kelimenin her biri ayrı yazılmaz. QAC kaynaklı kök ve lemma verisi `core` paketinden ayrı, boyutu yüzünden isteğe bağlı `kelime-kok` paketindedir ve bütün derlemelerde (`dev`, `internal`, `public`) yer alır; onaylı Türkçe anlamlar da bu paketle kelime kartına gider ([İçerik paketleri](../03-veri/03-icerik-paketleri.md)). Onaysız aday `dev` ve `internal`'da "doğrulanmamış" işaretiyle görünür; `public`'e girmez.

## 1. Kapsam

- **İş birimi lemmadır.** Lemma ve kök kimlikleri Quranic Arabic Corpus (QAC) v0.4'ten gelir. Kökün temel anlamı `root` tablosunda kök başına bir kez yazılır; lemmanın Kur'an'daki anlamları `lemma` tablosunda tutulur.
- **Kelime kartında görünen.** Arapça kelime (Tanzil), Türkçe kısa anlam, kök ve "Bu kök Kur'an'da N yerde geçer" bilgisi, kısa morfoloji satırı. Kartın tasarımı [Okuma deneyimi](../01-urun/02-okuma-deneyimi.md) dosyasındadır.
- **v1 dışı.** Âyet içindeki her geçiş için ayrı bağlam anlamı (Açık soru).
- **Hazır kaynak (K-19).** `quranwbw-tr`: QuranWBW Türkçe kelime anlamları (`https://static.quranwbw.com/data/v4/words-data/translations/6.json?version=1`, 1.043.145 bayt). Dosya sure → âyet → kelime sırasıyla 77.429 girdi taşır (boş girdi yok; 6.236 âyetin hepsinde kelime sayısı QAC ile aynı). Anlam çekimli kelime biçimine bağlıdır: 4.832 lemmadan yalnız 2.212'sinde baskın anlamın payı 0,8 ve üstündedir (A17.0 ölçümü). Bu yüzden hazır anlam her lemma için aday olur ve onaya kadar doğrulanmamış aday sayılır; editör onaylar ya da "Düzenle ve onayla" ile kendi anlamını yazar (K-50 madde 5 ve 6). Baskın pay 0,8 ve üstü olan lemma "tutarlı", altındaki "tutarsız hazır anlam" diye işaretlenir; eşik aday kümesini değiştirmez, yalnız işareti ve kuyruk sırasını belirler. Uygulama çevirmen adı vermez; atıf satırı kaynağın adıyla yazılır.
- **Seçilmeyenler.** QUL "Word lemma" kaynağı (indirme için giriş ister); quran.com kelime çevirisi (Quran Foundation ailesi; QuranWBW ile 63 âyetlik örnekte 766 kelimenin 716'sı aynı); `hablullah/data-quran` (adres açılmıyor, 404). Ayrıntı: [Kaynaklar](./01-kaynaklar.md) §4.
- **Kaynaklar ve bağımlılık.** Kök, lemma ve morfoloji `qac-morfoloji` kaydıyla QAC v0.4'ten gelir (GitHub `q-ran/quran`, commit sabitli; A17.0). QAC kök ve lemma satırları kaynak verisidir: `onayli` girer ve inceleme açılmaz (K-50 madde 4). `kelime-kok` paketi bütün derlemelerde yer alır; `public`'te yalnız onaylı anlamlar bulunur. Bir kelimenin anlamını göstermek QAC'nin kelime → lemma eşlemesine bağlıdır; anlam metni ile QAC verisi ayrı tutulur (bölüm 2.1).

## 2. Lemma envanteri

Sayılar hatta ölçülür, elle yazılmaz. Kaynaklardaki kelime sayıları bile farklıdır: QAC 77.429 kelime diyor ([QAC SSS](https://corpus.quran.com/faq.jsp)), QUL'un morfoloji kategorisi 77.432 öğe listeliyor ([QUL kaynaklar](https://qul.tarteel.ai/resources)). Fark büyük olasılıkla kelime bölme farkından gelir; G-BUT kapısı farkı raporlar ve çözer ([İçerik hattı](./02-icerik-hatti.md)). QAC v0.4 dosyasında ölçüm (A17.0): 128.219 segment, 77.429 kelime, 4.832 farklı lemma dizgisi (LEM), 1.642 farklı kök (ROOT). Sayılar aşağıdaki sorgularla hatta yeniden çıkarılır.

- **Girdi.** QAC v0.4 morfoloji dosyası (`q-ran/quran` deposu, `sources/1.0/quranic-corpus-morphology-0.4.txt`, 6.309.503 bayt; A17.0 commit'i sabitler). Sekmeyle ayrılmış dört sütun (LOCATION, FORM, TAG, FEATURES), ASCII Buckwalter dökümü; satır başına bir kelime parçası (kelime başına en çok 5 segment). Lemma ve kök FEATURES içinde `LEM:` ve `ROOT:` alanlarındadır. FORM, LEM ve ROOT Buckwalter olduğundan Arapça yazı eşlemeyle üretilir (A17.1).
- **Çapraz kontrol.** İç çapraz sayım `mustafa0x/quran-morphology` kopyasıyla yapılır (QAC'den türetilmiş, Arapça yazılı lemma ve kök; 130.030 satır, 4.776 LEM, 1.651 ROOT). Kopya yalnız sayım içindir ve pakete girmez. QUL'un lemma SQLite dosyası (kaynak 75, [QUL lemma](https://qul.tarteel.ai/resources/morphology/75)) indirme için giriş istediğinden seçilmedi.
- **Kimlik.** `lemma.id` bizim verdiğimiz kalıcı tamsayıdır ve yeniden numaralanmaz. QAC lemma dizgisi ayrı alanda tutulur. QAC v0.4'te hiçbir LEM dizgisi birden çok kökle geçmez ve dizgi sonunda sıra numarası yoktur; 304 dizgi birden çok sözcük türüyle geçer, 175 dizgi köksüzdür. Bu yüzden `lemma.id` yalnız LEM dizgisine göre verilir, sözcük türü anahtara girmez.

```bash
uv run mutalaa ingest qac
uv run mutalaa ingest quranwbw-tr                # hazır Türkçe kelime anlamı (K-19)
uv run mutalaa enrich morphology                 # quran_word ↔ lemma ↔ root
uv run mutalaa export pg --source qac-morfoloji
uv run mutalaa enrich glosses --wave 1           # yalnız hazır kaynaktan toplar (K-50)
uv run mutalaa export pg --source quranwbw-tr
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
# mustafa0x kopyasıyla çapraz sayım (sekmeyle ayrılmış dört sütun; özellikler "|" ile ayrılır)
from collections import Counter

lem, kok = Counter(), Counter()
with open("data/gelen/mustafa0x-morfoloji/<YYYY-AA-GG>/quran-morphology.txt", encoding="utf-8") as f:
    for satir in f:
        _konum, _bicim, _etiket, ozellik = satir.rstrip("\n").split("\t")
        alanlar = dict(a.split(":", 1) for a in ozellik.split("|") if ":" in a)
        if "LEM" in alanlar:
            lem[alanlar["LEM"]] += 1
        if "ROOT" in alanlar:
            kok[alanlar["ROOT"]] += 1
print(len(lem), len(kok))   # QAC sayılarıyla karşılaştırılır (A17.5)
```

### 2.1 Lemma kaynağı ve kimlik ayrımı

Anlam metni ile QAC verisi ayrı tutulur. Anlamlar bizim kalıcı `lemma.id` kimliğimize bağlanır; QAC'nin lemma dizgisi ve kelime → lemma ataması ayrı tablolarda durur. Böylece lemma kaynağı değişse de anlamlar yeniden yazılmaz.

Şemada bu ayrım iki alanla kurulur ([Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) §5):

- `lemma.qac_ref`: QAC lemma dizgisi. Lemma kaynağı değişirse eşleme buradan yapılır.
- `quran_word.morph_source`: kök, lemma ve sözcük türü atamasının kaynağı (`qac-morfoloji`). Bu sütunları yalnız `export pg --source qac-morfoloji` yazar (K-50 madde 3).

QAC Version 2 yayımlanırsa ayrı bir `lemma_kaynak` eşleme tablosu açılabilir; bu yalnız öneridir, şemada yoktur ve v0.4 için gerekmez:

```sql
-- Yalnız öneri (QAC v2 gelirse); bugün şemada yok
CREATE TABLE lemma_kaynak (
  lemma_id       int  NOT NULL REFERENCES lemma(id),
  kaynak         text NOT NULL,      -- 'qac-2.0' gibi; lemma kaynağı değişirse yeni değer
  kaynak_anahtar text NOT NULL,      -- QAC lemma dizgisi (gerekirse sözcük türüyle)
  PRIMARY KEY (kaynak, kaynak_anahtar)
);
```

- Lemma kaynağı değişirse (düzeltme ya da QAC Version 2'ye geçiş) yalnız eşleme değişir (`lemma.qac_ref`, gerekirse `lemma_kaynak`); `lemma.id` ve anlamlar korunur. Ayrılan ya da birleşen lemmalar `kullanim_disi` ve yönlendirmeyle çözülür.
- QAC dosyası değiştirilmez (`data/raw` değişmez); düzeltmeler `quran_word_fix` katmanında tutulur ([Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) §4).
- Araştırma notu Kur'an kelimeleri için çözümleyici yerine insan doğrulamalı QAC verisini öneriyor; bu yüzden envanter QAC v0.4'tür.
- QUL'un ve Quranpedia'nın morfoloji verisi QAC'den türediği için bağımsız ikinci kaynak sayılmaz.
- QAC'nin 2. sürümü geliştiriliyor; standart veri setleri henüz yayımlanmadı ([kaisdukes/quranic-corpus](https://github.com/kaisdukes/quranic-corpus)). Yayımlanırsa `lemma.qac_ref` üzerinden, gerekirse `lemma_kaynak` önerisiyle eşlenir.

## 3. Önceliklendirme

| Dalga | Kapsam | Not |
|---|---|---|
| 0 | Zamir ve harf/edat sınıfındaki lemmalar (lemmanın en sık gövde etiketi QAC etiket kümesinde bu sınıflardan biridir) | Çok sık geçer; dil bilgisi işleviyle anlamlandırılır. Kesin etiket listesi A17.0'da QAC etiket sayfasından türetilir ve karar defterine tarihli notla yazılır |
| 1 | Dalga 0 dışında kelime geçişlerinin ilk %50'sini kapsayan lemmalar, artı Fâtiha ve 30. cüz lemmaları | Fâtiha ve 30. cüz lemmalarından dalga 0'a düşenler dalga 0'da kalır |
| 2 | %80'e kadar | |
| 3 | %95'e kadar | |
| 4 | Kalanlar (az geçenler) | |

Sayım kelime düzeyindedir ve gövde lemmasını sayar (bölüm 2 sorgusu). Yüzdeler dalga 0 dışarıda bırakılarak hesaplanır. Cüz sınırı `tanzil-ust-veri` işaretlerinden (`quran_marker`, `kind = 'cuz'`) alınır. Dalga 0 ile dalga 1 birlikte açılır. Dalgalar `lemma_dalga(lemma_id PK FK, dalga, sira, data_version)` tablosunda saklanır; hat yazar, API okur ve sıralar.

Sıra kuralı: dalga içinde kökün toplam geçişine göre azalan (eşitlikte `root.id`), köksüzler sonda; kök içinde lemma geçişine göre azalan (eşitlikte `lemma.id`). Aynı kökün lemmaları böylece art arda gelir. Kural K-50 madde 7'dedir.

Dalgadaki lemma sayısı `lemma_dalga` tablosundan okunur. Zipf dağılımı nedeniyle ilk dalgaların az sayıda lemmayla büyük kapsama vermesi beklenir (araştırma notu çıkarımı); QAC v0.4 üzerindeki ön ölçüm bunu doğruluyor: LEM taşıyan 74.608 segmentte (dalga 0 dahil, dalga ayrımından önce) ilk %50 için 60, %80 için 470, %95 için 2.012 lemma yeter (A17.0). Dalga içinde lemmalar köke göre gruplanır; aynı kökün lemmaları aynı oturumda incelenir ve anlamlar tutarlı kalır. Fâtiha ve 30. cüz lemmalarının dalga 1'e alınması çözüldü (12 Kasım 2026, K-50 madde 7): proje sahibine bu konuda artık sorulmaz.

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
6. Hazır kaynaktan gelen kelime anlamı taslak girdisidir; kılavuza uymayan ifade (tefsir dili, uzunluk, çekimli biçim) editörce lemma anlamına çevrilir. Elmalılı meali onaylıysa bağlam örneği olarak kullanılabilir.
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

## 5. Yapay zekâ taslak istemi (S-16'da kullanılacak)

> **S-16'ya ertelendi (K-50 madde 1).** Bu bölüm bugün uygulanmaz: hat Anthropic çağrısı yapmaz, `pipeline/prompts/kelime-anlami/v1.md` yazılmaz, JSON şeması ve Batch çağrıları kurulmaz. Bölümün içeriği S-16 için korunur; model, fiyat ve örnekleme ayarları S-16 açılınca yeniden araştırılır (güncel API'de sıcaklık parametresi reddedilebilir). Bugünkü yol: hazır kaynaktan aday, editör onayı ya da editörün yazdığı anlam (bölüm 1 ve 6).

- **Girdi.** Lemma (harekeli Arapça), QAC kökü ve türü, sıklık, hazır kelime anlamları (`quranwbw-tr`; varsa), en fazla 8 örnek âyet (Tanzil Arapçası; Elmalılı meali onaylıysa meal, değilse yalnız Arapça), aynı kökün onaylı anlamları, kılavuz özeti. S-16'da hangi lemmaların yapay zekâya gideceği (hazır adayı ya da reddi olan lemmaya taslağın nasıl gireceği) S-16'nın konusudur (K-50 madde 11).
- **Girmeyenler.** Kişisel veri. Onaysız metin girdi sayılmaz: onaylı olmayan meal isteme girmez.
- **Ayarlar.** Claude Haiku 5.5 (`claude-haiku-5-5`), Batch API, sıcaklık 0 (A17.0 ayarı doğrular). İstem `pipeline/prompts/kelime-anlami/v1.md` dosyasında sürümlüdür. Çıktı JSON şemasıyla doğrulanır; taslağın kökü QAC kökünden farklıysa çıktı reddedilir.
- **Çoklu taslak (isteğe bağlı).** İki farklı istem sürümüyle iki taslak alınır; ayrışan maddeler incelemede öne çıkar. Yayımlanmış bir protokol üç dil modelinin çoğunluk oyunu kullanıyor ve üç modelin ayrıştığı maddeleri insana yönlendiriyor ([protocols.io](https://www.protocols.io/view/llm-assisted-expert-annotation-for-systematic-lite-4r3l2dw5jg1y/v1.pdf)).

```text
SİSTEM
Kur'an Arapçası için Türkçe lemma anlamı TASLAĞI yazıyorsun. Taslağı bir editör onaylayacak.
Kurallar:
- Yalnız sözlük anlamı yaz. Tefsir, mezhep tercihi, fıkhî hüküm ve öğüt yazma.
- anlam_kisa 1–4 kelime; en fazla 3 karşılık; noktalı virgülle ayır.
- Fiilleri mastarla (-mak/-mek), isimleri yalın tekil yaz. Harf ve edatlarda önce işlevi parantezle yaz.
- Verilen QAC kökünü kullan; kök önerme.
- Verilen hazır kelime anlamları girdidir; kılavuza uymayanı lemma anlamına çevir.
- Emin değilsen "emin_degil": true yaz; karşılık uydurma.
- Çıktıyı yalnız verilen JSON şemasına uygun yaz.

KULLANICI
lemma: {lemma_ar}   QAC: {qac_lemma}   tür: {pos}   kök: {kok_ar}   sıklık: {n}
hazır kelime anlamları: {hazir_anlamlar}
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

S-16'da taslaklar veritabanına `status = 'aday'` ile girer; model, istem sürümü ve girdi hash'i taslağın `review` satırında durur (`yz_modeli`, `yz_kaydi`). `dogrulanmis` saklanmaz; taslak onaylanana kadar `false` sayılır ([İçerik hattı, yapay zekâ politikası](./02-icerik-hatti.md); [K-37](../00-ozet/02-karar-defteri.md#k-37--editoryal-şema-ayrıntıları)). Bugünkü hazır kaynak adaylarında `origin = 'kaynak:quranwbw-tr'` olur ([Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) §5'teki `origin` değer listesi buna göre genişler) ve `yz_modeli` ile `yz_kaydi` boştur (K-50 madde 5).

## 6. Editör panelinde inceleme

- **Kuyruk.** `lemma_dalga` tablosundaki dalga ve sıra kuralına göre dizilir (bölüm 3); "tutarsız hazır anlam" işareti kuyrukta öncelik verir.
- **Kart.** Lemma, kök, tür, sıklık; KWIC dizini (az geçen lemmada bütün geçişler, sık geçende örneklem) Arapça ve Elmalılı mealiyle; aday alanları ve kaynağı (`origin`: hazır kaynak; S-16'dan sonra yapay zekâ da); hazır anlamın dağılımı (`review.onerilen.dagilim`; hedefe uygulanmaz) ve baskın payı; aynı kökün onaylı anlamları; kılavuz uyarıları (uzunluk, tefsir dili, eksik alan).
- **Eylemler.** Onayla; Düzenle ve onayla (editör `anlam_kisa` değerini yazar; K-48 madde 2 güncellemesi); Reddet; Uzmana gönder; "yalnızca etimolojik" işaretle. "Reddet ve yeniden taslak iste" S-16'ya ertelendi (K-50 madde 1).
- **Kayıt.** Her eylem `review` tablosuna yazılır: inceleyen, eylem, önceki ve sonraki değer, süre, not. Madde başına harcanan süre maliyet tahminini besler.
- **Durum.** `aday` → `onayli` ya da `red`. `aday` anlamlar `dev` ve `internal` derlemelerinde durumdan türeyen "doğrulanmamış" işaretiyle görünür (K-42 madde 5; K-50 madde 8); K-25 rozeti yapay zekâ taslağına çıkar (`yz_modeli` dolu). `public` derlemeye yalnız `onayli` anlamlar girer, `red` hiçbirine girmez ([İçerik paketleri](../03-veri/03-icerik-paketleri.md) §3.3).
- **İnceleyen.** Arapça ve Türkçe yetkinliği olan kişi. Rol ve yetkiler [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) dosyasında.

## 7. QA: iki gözden geçirenli örneklem ve uyum ölçüsü

Bu bölümdeki araçlar insan değerlendirmesi için kalır; hazır kaynak adaylarının ve editör yazımlarının kalitesini ölçer. Yapay zekâ taslağına bağlı kısımlar S-16'ya aittir.

1. **Kalibrasyon.** Dalga 1'den önce inceleyenler 30 maddeyi birlikte işler ve kılavuzu örneklerle netleştirir. Protokolde insanlar 11 maddeyle kalibre olup 20 maddeyle altın veri kurmuş, 66 maddeyle doğrulama yapmıştır ([protocols.io](https://www.protocols.io/view/llm-assisted-expert-annotation-for-systematic-lite-4r3l2dw5jg1y/v1.pdf)).
2. **Çift değerlendirme seti.** Dalga ve sözcük türüne göre tabakalı 300 lemma seçilir. İki inceleyen aynı taslağı birbirinden habersiz `kabul`, `duzelt`, `red` diye değerlendirir. Uyum Cohen kappa ile ölçülür: `κ = (p_o − p_e) / (1 − p_e)`; `p_o` gözlenen uyum, `p_e` şans uyumu. Protokolde insanlar arası κ 0,60 ± 0,24, üç modelin çoğunluk oyu ile insan arası κ 0,57 ± 0,08 bulunmuş. Hedef: inceleyenler arası κ ≥ 0,60. Altında kalırsa kılavuz netleştirilir ve kalibrasyon tekrarlanır.
3. **Onay sonrası ikinci okuma.** Her dalgada onaylı maddelerden rastgele örneklem (en az 300 ya da %10) ikinci bir inceleyene gider: `dogru`, `kucuk_hata`, `yanlis`. `yanlis` oranı %95 Wilson aralığıyla raporlanır. Öneri eşiği: üst sınır ≤ %2; aşılırsa dalga yeniden incelenir.
4. **Aday kalitesi.** Değiştirilmeden kabul oranı, düzenleme mesafesi ve ret oranı sözcük türüne göre izlenir. İstemin bu verilere göre sürüm atlaması S-16'ya aittir.
5. **Hakemlik.** İki inceleyen ayrışırsa üçüncü kişi karar verir; karar kılavuza örnek olarak eklenir.

## 8. Sürümleme

- Veri seti `kelime-anlam-tr` adıyla anlamsal sürüm taşır. Her madde `version` ve `content_hash` taşır; hazır kaynak adayında `version = '1'`, "Düzenle ve onayla"da `version` +1 olur; değişiklik `review` kaydıyla izlenir; iki sürüm arasında fark raporu üretilir.
- Anlam metni bizim ürettiğimiz metindir; ilk kayıtta NFC'ye çevrilir ve `content_hash = sha256(kanonik anlam_kisa)` bu metinden hesaplanır (K-26; K-46 madde 4 biçimi). Hazır kaynaktan gelen ham girdi `data/raw` altında değişmeden durur ve onay görene kadar "doğrulanmamış"tır.
- `lemma.id` yeniden numaralanmaz. QAC düzeltmesiyle bir lemma kalkarsa madde `kullanim_disi` olur ve yeni lemmaya yönlendirilir.
- `kelime-kok` paketi `data_version` taşır. Düzeltmeler planlı sürümlerde toplu yayımlanır.

## 9. Maliyet tahmini

Yapay zekâ taslağı kalemi S-16'ya ertelendi (K-50); bugün ücretli çağrı yoktur ve İ-17 gerekmez. Aşağıdaki tablo S-16 için başvuru olarak kalır; model ve fiyat S-16'da yeniden araştırılır. Bugünkü asıl maliyet insan zamanıdır.

| Kalem | Formül | Örnek (varsayım) |
|---|---|---|
| Yapay zekâ taslağı | `N × k × (T_girdi × p_girdi + T_cikti × p_cikti) / 10⁶` | Haiku 5.5 Batch fiyatıyla (girdi 0,05 $, çıktı 0,25 $ / milyon token) `T_girdi = 1.500`, `T_cikti = 250`, `k = 1`: 1.000 lemma ≈ 0,14 $; `k = 2` ile ≈ 0,28 $ |
| İnceleme | `N × t_madde` | `t_madde = 2 dk` ise 1.000 lemma ≈ 33 saat |
| QA | `300 × 2 × t_değerlendirme` + ikinci okuma örneklemi | Pilotta ölçülür |

Fiyatlar [Claude fiyatlandırma](https://platform.claude.com/docs/en/about-claude/pricing) sayfasından alındı (18 Ekim 2026). S-16'da token sayıları 50 lemmalık pilotta token sayma uç noktasıyla ölçülür (`uv run mutalaa llm estimate --task glosses --sample 50`; komut S-16'ya ertelendi); `t_madde` pilotta kronometreyle ölçülür. Bu ölçekte asıl maliyet insan zamanıdır. Toplu iş ücretlidir: S-16'da koşudan önce tahmini maliyet kullanıcıya gösterilir ve İ-17 bütçesiyle onaylanır. Bugün `N` (editörün incelediği lemma sayısı) bütün lemmalardır, çünkü her lemma hazır kaynaktan aday olur.

## 10. Açık sorular

1. Onaylı maddelerde rozet kalkar mı? Öneri: rozet kalkar, ayrıntıda "hazır kaynak (QuranWBW) taslağı, editör onaylı" kaynak satırı görünür (K-25'in yorumu). S-16'dan sonra yapay zekâ taslağı için "yapay zekâ taslağı, insan onaylı" satırı eklenir.
2. Âyet içi bağlam anlamı ne zaman ve hangi veri modeliyle gelecek?
3. ~~Hazır anlamın (`quranwbw-tr`) tutarlılık eşiği.~~ Çözüldü (12 Kasım 2026, [K-50](../00-ozet/02-karar-defteri.md#k-50--yapay-zekâ-işlerinin-proje-sonuna-ertelenmesi-hazır-anlam-adayları-qac-sözlüğü-ve-kelime-anlamı-görünürlüğü) madde 5): eşik 0,8'dir ve yalnız "tutarlı" ve "tutarsız hazır anlam" işareti ile kuyruk sırasını belirler; aday kümesini değiştirmez (ön ölçüm: baskın anlam payı 0,8 ve üstü olan 2.212, 0,5 ve üstü olan 3.226 lemma).
4. QuranWBW Türkçe anlamının çevirmeni ve kalitesi (uygulama çevirmen adı vermiyor; Doğrulanacak).

## İlgili dosyalar
- [Kaynaklar](./01-kaynaklar.md) · [İçerik hattı](./02-icerik-hatti.md) · [Elmalılı hazırlığı](./03-elmalili-hazirligi.md) · [Risale hazırlığı](./05-risale-hazirligi.md)
- [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) · [Bağlantı modeli](../05-capraz-referans/01-baglanti-modeli.md)
- [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](../03-veri/03-icerik-paketleri.md) · [Arama](../03-veri/05-arama-fts5.md)
- [Okuma deneyimi](../01-urun/02-okuma-deneyimi.md) · [Mobil ekranlar](../01-urun/03-mobil-ekranlar.md) · [Yayın süreci](../07-yayin/01-yayin-sureci.md)
