# Tanzil sorusu: ayrı arama metni

> **Sürüm:** 1.1 · **Tarih:** 24 Ekim 2026 · **Durum:** Taslak (gönderilmedi; 2. soru genişletildi, gönderimden önce kullanıcı onayı gerekir)
> **Bağlı kararlar:** [K-26](../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-17](../00-ozet/02-karar-defteri.md#k-17--arama-sqlite-fts5) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-22](../00-ozet/02-karar-defteri.md#k-22--gelir-modeli) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Muhatap:** Tanzil Project (tanzil.net) · **Dil:** İngilizce · **İnsan adımı:** [İ-08](../10-claude-code/06-insan-adimlari.md)
> **Kanal:** Doğrulanacak. Tanzil'in gösterdiği tek yol Quran Navigator'daki iletişim menüsü ([tanzil.net](https://tanzil.net/); [katkı sayfası](https://tanzil.net/docs/contribution)); menünün hedefi okunamadı, tarayıcıda açıp doğrula. `tanzil.net/contact/` 404 veriyor. Duyurular için Tanzil-Text e-posta listesi ([groups.google.com/group/tanzil-text](http://groups.google.com/group/tanzil-text)). Okuma: 2026-10-20.
> **Engellediği iş:** arama indeksinin biçimi (AR-3; A12); mağaza yayınından önce bilgi (A34)
> **Gönderim tarihi:** — · **Takip tarihi:** —

> **Hukuki görüş değildir.** Yazı Tanzil şartlarının nasıl uygulanacağını sorar; hukuki değerlendirme içermez.

## Gönderilecek metin

**Subject:** Questions about the Tanzil Text License: a normalized search index, the non-commercial note in the FAQ, and the metadata files

Dear Tanzil team,

We are developing "Mütâlaa", a free, ad-free Qur'an reading and study app in Turkish for iOS and Android. It will use the Tanzil Uthmani text (version 1.1) and will follow your Text License:

- We will store and display the Uthmani text exactly as distributed, byte for byte. We will apply no Unicode normalization (not even NFC) and no other change.
- We will include your copyright notice in full, credit "Tanzil Project" and link to tanzil.net.

For search, the app also needs a simplified form of the text, so that users can find verses without typing diacritics: diacritics, Qur'anic annotation marks and tatweel are removed, and some letter variants are unified (for example, the forms of alif). The Simple Clean text is never displayed; we plan to use it only to build this search form. We plan to derive the form from your Simple Clean edition, which your documentation describes as "Suitable for easy search". So that Uthmani text pasted into the search box is also found, we would append the simplified form of each word whose Uthmani spelling differs from the Simple Clean spelling to the same search column, never to the Qur'an text itself. The search column is kept next to the unchanged text, or, if that is a concern, only inside a full-text search index that does not keep the simplified text as a column. The index itself still contains the simplified words and their positions.

1. Does such a normalized search column, or a search index built from it, count as "changing" the text under your Text License?
2. Your Text License page names Creative Commons Attribution 3.0, while your FAQ ("For Developers") says "We have provided all resources used in Tanzil in our resources page" and that "They are available for non-commercial purposes". Does the non-commercial condition also apply to the Quran text? The same question applies to the Quran Metadata files (`quran-data.xml` and `quran-data.js`, version 1.0): the files themselves say `license="cc-by"` and "License: Creative Commons Attribution 3.0", your Text License notice is limited to the Quran text, and your resources page lists the metadata as well. We use only the number of verses of each of the 114 surahs from these files, and we keep the license and copyright lines of the file next to that data. Which terms apply to the metadata files? Our app is free and shows no ads; it has no revenue model today. Would the answer change if we ever accepted donations?
3. Your updates page lists the Uthmani and Simple Clean texts as version 1.1 (12 February 2021). Is version 1.1 still the current text, and does anything in the downloaded file, for example the year in the copyright line of the header, change between downloads while the text itself stays the same?

Thank you for maintaining Tanzil.

Kind regards,

[Name] · [e-mail]

## İç notlar (gönderilmez)

**Türkçe özet.** Tanzil'e üç soru soruluyor: (1) Kur'an metnini bayt bayt saklayıp değiştirmeden göstereceğimiz hâlde, arama için ayrı bir sütunda tuttuğumuz normalize metin (ya da metni sütun olarak saklamayan bir arama indeksi) "değiştirme" sayılır mı? (2) Lisans sayfası CC BY 3.0 derken SSS, kaynakların "ticari olmayan amaçlarla" kullanılabileceğini söylüyor; bu şart Kur'an metnine de uygulanır mı, üst veri dosyalarına (`quran-data.xml`, `quran-data.js`; dosyada CC BY 3.0 satırı var, A04'te yalnız sure başına âyet sayısı alınır) hangi şart uygulanır, bağış kabul edersek cevap değişir mi? (3) Güncellemeler sayfasındaki sürüm 1.1 (12 Şubat 2021) hâlâ güncel mi, indirilen dosyada metin aynı kalırken değişen bir şey (ör. başlıktaki telif yılı) var mı? Yazı ayrıca metni değiştirmeyeceğimizi, bildirimi ve tanzil.net bağlantısını koruyacağımızı söyler. A01.5 yalnız sürüm sorusunu istiyordu; 2. ve 3. soru A01.1 bulgularından eklendi.

**Soruların dayanağı**

| Soru | Dayanak |
|---|---|
| 1 | [Çapa şeması](../03-veri/01-capa-semasi.md) §13 ÇŞ-2 ve §7; [Arama](../03-veri/05-arama-fts5.md) §1.3, §1.4 ve AR-3; [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1 (Açık soru) ve §8 satır 1; K-26 |
| 2 | A01.1 araştırması (2026-10-20): [Tanzil SSS](https://tanzil.net/docs/faq) "They are available for non-commercial purposes."; [kaynaklar sayfası](https://tanzil.net/docs/resources) Kur'an metni için indirme sayfasını gösteriyor; [Text License](https://tanzil.net/docs/text_license) "License: Creative Commons Attribution 3.0"; üst veri (okuma 2026-10-24): [Quran Metadata](https://tanzil.net/docs/quran_metadata) sayfası (sürüm 1.0), [`quran-data.xml`](https://tanzil.net/res/text/metadata/quran-data.xml) kök öğesinde `license="cc-by"`, [`quran-data.js`](https://tanzil.net/res/text/metadata/quran-data.js) içinde `// License: Creative Commons Attribution 3.0`; Text License bildirimi yalnız Kur'an metnine bağlı; SSS "For Developers" bölümü ve [kaynaklar sayfası](https://tanzil.net/docs/resources) üst veriyi de kapsıyor görünüyor; [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1 |
| 3 | A01.5 ("Uthmani dosyasının sürüm numarası da sorulur"); [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) §7.2 adım 2 (release kaydı Tanzil dosya özeti taşır) ve §7.3 (Tanzil güncellemesi yeniden onay gerektirir); A10 |
| Giriş | Lisans defteri §3.1 (saklama ve atıf); A01.1 (sürüm 1.1, 12 Şubat 2021; Simple Clean için "Suitable for easy search.", [Quran Text Types](https://tanzil.net/docs/quran_text_types)); [İçerik paketleri](../03-veri/03-icerik-paketleri.md) §3.2 (Simple Clean pakette ayrı birim ya da sütun olarak durmaz; yalnız normalize hâli `unit_search.ar_norm` sütunundadır); Arama §1.4 (Uthmani yazımı farklı kelimelerin normalize biçimleri sona eklenir) |

**A01.1 bulguları (2026-10-20)**
- Canlı lisans sayfası [tanzil.net/docs/text_license](https://tanzil.net/docs/text_license); belgedeki alıntılarla aynı. Düzeltme (2026-10-24): sayfada bugün revizyon tarihi görünmüyor, yalnız "Copyright (C) 2007-2021 Tanzil Project" var; 12 Şubat 2021 güncellemeler sayfasındaki metin sürümü 1.1'in tarihidir.
- Uthmani ve Simple Clean: Version 1.1, 12 Şubat 2021 ([updates](https://tanzil.net/updates/)). A01.5'teki sürüm sorusu bu bulguyla 3. soruya dönüştü: sürümün güncelliğini ve indirmeler arasında değişenleri soruyor.
- SSS'deki "non-commercial purposes" cümlesi belgelerde yoktu; 2. soru bunun için eklendi. **Riski küçümseme:** Tanzil "bu şart Kur'an metnine de uygulanır" derse lisans defteri §7 akışı "kısıtı uygula ya da `kapali`" koluna girer; defter §4, benzer şart taşıyan Tanzil çevirilerini ve OpenITI'yi `kapali` tutuyor. Çekirdek Kur'an metni için bu sonuç K-22 ve S-01'i (bağış dahil) doğrudan bağlar. 2. soruyu göndermeden önce avukat yazısının 5. başlığındaki görüşü beklemen önerilir; karar senindir. 2. soruyu çıkarırsan avukat yazısının 5. başlığındaki "bunu Tanzil'e de soruyoruz" ifadesini de çıkar.
- Bağış, yazıda yalnız "cevap değişir mi" sorusu olarak geçer; karar ya da söz değildir (K-22).
- A10 için yan bulgu (çıkarım): dosya başlığındaki telif yılı satırı indirme yılına göre değişebilir ("2007-2021" ya da "2007-2026" gibi); metin aynı kalsa da dosya özeti değişebilir. İndirme seçenekleri (durak işaretleri, tatvil vb.) de baytları değiştirir. A10'da kilit dosyası (`tanzil.lock.json`) tasarlanırken dikkate alınır; bu yüzden 3. soru soruluyor.
- **Kural notu:** A01.1 doğrulaması sırasında araştırma ajanı Tanzil indirme formunu `agree=true` parametresiyle çağırdı. Bu, sitedeki "şartları kabul ediyorum" adımına karşılık geliyor görünür ve A01 "Dikkat" bölümündeki "form doldurmaz, şart kabul etmez" kuralına aykırıydı. İnen dosyalar aracın kendi önbelleğinde kaldı; depoya ve `data/raw/` altına girmedi, kaynak olarak kullanılmaz. A10'da Tanzil dosyasını, şartları kendin onaylayarak indir. Yıl satırı gözlemi yazıya konmadı; yalnız soru olarak soruldu.

**Üst veri bulgusu (2026-10-24, A04; kullanıcı kararı D1).** A04, âyet sayısı dizisini Tanzil üst veri dosyasından üretip devam eder; şart belirsizliği bu 2. soruyla kayda geçti ve karar yine kullanıcıdadır. Dosyaların lisans satırı (CC BY 3.0) ile SSS'deki "non-commercial purposes" cümlesi çelişiyor; uzlaştıran bir Tanzil ifadesi bulunamadı. Hukuki görüş değildir. Taslak gönderilmedi; 2. sorunun genişletilmiş hâli ve gönderim kullanıcı onayına bağlıdır.

**Cevap gelince:** ÇŞ-2 ve AR-3 `/karar` ile kapanır (A12: içeriksiz ya da dış içerikli FTS); 2. sorunun cevabı lisans defteri §3.1'e ve [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) S-01'e işlenir. "Ticari olmayan kullanım Kur'an metnine de uygulanır" cevabı lisans durumunu etkiler: A39 yordamı (olay kaydı, ikinci onay) ve `/karar` çalışır; lisans defteri ve `pipeline/sources/<kimlik>.toml` aynı değişiklikte güncellenir (A06'dan sonra). Cevap, "İlgili dosyalar" başlığından önce açılacak "## Cevap" bölümüne tarihiyle yazılır; İ-08 satırı güncellenir.

## İlgili dosyalar

- [Çapa şeması](../03-veri/01-capa-semasi.md) · [Arama](../03-veri/05-arama-fts5.md) · [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md)
- [QAC lisans sorusu](./qac-lisans.md) · [Avukat soruları](./avukat-sorulari.md) · [İnsan adımları](../10-claude-code/06-insan-adimlari.md) · [A01](../10-claude-code/asamalar/A01-yazisma-paketi.md)
