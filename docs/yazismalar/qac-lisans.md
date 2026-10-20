# QAC lisans sorusu

> **Sürüm:** 1.0 · **Tarih:** 20 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-19](../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-22](../00-ozet/02-karar-defteri.md#k-22--gelir-modeli) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Muhatap:** Quranic Arabic Corpus bakımcıları (sitenin altbilgisine göre quran.com ekibi) · **Dil:** İngilizce · **İnsan adımı:** [İ-04](../10-claude-code/06-insan-adimlari.md)
> **Kanal:** [feedback.quran.com](https://feedback.quran.com/) (quran.com destek sayfasının gösterdiği Canny panosu; gönderilerin herkese açık olup olmadığı Doğrulanacak, herkese açıksa imzaya e-posta yazılmaz) ya da Quran Foundation'ın genel iletişim adresi ([quran.foundation](https://quran.foundation/), "Contact:" satırı; adres sayfada gizli, arama dizininden okundu, Doğrulanacak). Herkese açık yol: aynı soruyu soran GitHub kaydı [#81](https://github.com/kaisdukes/quranic-corpus/issues/81) (cevapsız). [corpus.quran.com/contact.jsp](https://corpus.quran.com/contact.jsp) hâlâ Kais Dukes'un üniversite adresini gösteriyor; bu adresin reddedildiği bildirildi. Okuma: 2026-10-20.
> **Engellediği iş:** `kelime-kok` paketinin `internal` ve `public` derlemelere girmesi (A17); bu derlemelerde kelime kartının kök, lemma ve Türkçe anlam satırları (A25, A34)
> **Gönderim tarihi:** — · **Takip tarihi:** —

> **Hukuki görüş değildir.** Yazı lisans şartlarını sorar; hukuki değerlendirme içermez.

## Gönderilecek metin

**Subject:** Licensing question: Quranic Arabic Corpus morphology in a free reading app

Dear Quranic Arabic Corpus maintainers,

The corpus website says it is maintained by the quran.com team, so we are writing to you. We are building "Mütâlaa", a free, ad-free Qur'an reading and study app in Turkish for iOS and Android that works offline. We would like to use the morphology data of the Quranic Arabic Corpus (version 0.4) to show the root and lemma of each word in a word card, to list every occurrence of a root, and to link words and verses that share a root or lemma, with credit and a link to corpus.quran.com. Until we hear from you, the data stays out of every build that leaves our team.

1. The download page licenses the morphology file under the GNU GPL and allows use "in any website or application" with credit and a link; the FAQ, answering a question about research projects, says "You do not use the data for commercial purposes". Which terms apply to a free app that has no revenue model today, and would the answer change if the app ever accepted donations?
2. The download page also says: "Permission is granted to copy and distribute verbatim copies of this file, but CHANGING IT IS NOT ALLOWED." May we convert the values, without changing any of them, into our own SQLite tables, combining the segment-level records into word-level rows (root and lemma taken from the stem segment), and ship them with credit? Or would that count as changing the file?
3. We plan to keep our own corrections to the annotation (for example, tagging errors we may find) in a separate layer and never to edit your file. May we ship that layer, and would you like to receive the corrections when we have them?
4. What credit line do you prefer?
5. Our Turkish word meanings are first drafted by an AI model and then reviewed by people. May we include a word's root, lemma and part-of-speech tags (not the file itself) in the prompts we send to the AI service?
6. The copyright line on the website names Kais Dukes. Can you answer these questions on behalf of the copyright holder? If not, whom should we contact?

Thank you for keeping the corpus available.

Kind regards,

[Name] · [e-mail]

## İç notlar (gönderilmez)

**Türkçe özet.** QAC bakımcılarına altı soru soruluyor: (1) İndirme sayfasındaki GPL izni ile SSS'nin araştırma projeleri için koyduğu "ticari amaçla kullanmama" şartından hangisi, bugün gelir modeli olmayan ve ileride bağış alabilecek ücretsiz bir uygulamaya uygulanır? (2) İndirme sayfasındaki "değiştirmek yasaktır" cümlesi ışığında, değerleri değiştirmeden ama segment kayıtlarını kelime satırlarında toplayarak kendi SQLite tablolarımıza çevirip atıfla dağıtabilir miyiz? (3) Düzeltmelerimizi ayrı bir katmanda tutmayı planlıyoruz; bu katmanı dağıtabilir miyiz, düzeltmeleri almak ister misiniz? (4) Hangi atıf satırını tercih edersiniz? (5) Türkçe kelime anlamlarının taslağı yapay zekâyla çıkarılıyor; kelimenin kök, lemma ve sözcük türü etiketlerini (dosyayı değil) yapay zekâ hizmetine giden istemlere koyabilir miyiz? (6) Telif satırında Kais Dukes'un adı var; bu soruları hak sahibi adına cevaplayabilir misiniz, yoksa kime yazmalıyız? Yazı ayrıca, cevap gelene kadar verinin ekip dışına çıkan hiçbir derlemeye konmadığını söyler.

**Soruların dayanağı**

| Soru | Dayanak |
|---|---|
| 1 | [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) §2 (taslak soru 1); [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.2 ve §8 satır 4; [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md) AS-01; [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) S-15 |
| 2 | Kök ve lemma §2 (taslak soru 2) ve §3 (içe aktarma); lisans defteri §3.2 ("Dosya değiştirilmez") |
| 3 | Kök ve lemma §2 (taslak soru 3) ve §4 (düzeltme katmanı) |
| 4 | Kök ve lemma §2 (taslak soru 4); lisans defteri §3.2 (atıf) |
| 5 | Lisans defteri §3.2 (`embed_ok`: istemlere yalnız lemma, kök ve sözcük türü etiketleri girer; QAC'nin cevabı kısıtlarsa istemler etiketsiz çalışır); [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md) §2.1 (son madde); K-19 |
| 6 | A01.1 araştırması (2026-10-20): her sayfanın altbilgisi "Copyright © Kais Dukes, 2009-2017. Maintained by the quran.com team." ([corpus.quran.com](https://corpus.quran.com/)) |
| Giriş paragrafı | K-06 uygulama notu (veri `kelime-kok` paketinde, `bekliyor`, yalnız `dev`); lisans defteri §2 (özet tablo, `qac-morfoloji`: v0.4) ve Kök ve lemma §1 (QAC v0.4); Kök ve lemma §3 madde 2 (segment kayıtları kelime düzeyine toplanır; kök ve lemma gövde segmentinden gelir) ve §5 (kök gezgini, kök envanterine eşleme); A01.1 (bakım quran.com ekibinde) |

**A01.1 bulguları (2026-10-20)**
- [İletişim sayfası](https://corpus.quran.com/contact.jsp) yazışmayı hâlâ Kais Dukes'un Leeds Üniversitesi adresine yönlendiriyor. GitHub [#81](https://github.com/kaisdukes/quranic-corpus/issues/81) bu adresin posta sunucusunca reddedildiğini bildiriyor; aynı soruyu soruyor ve cevapsız.
- İkincil kaynaklara göre Dr. Kais Dukes 2024'te vefat etti ([Sohaib Sandhu, 9 Mart 2024](https://sohaibsandhu.com/2024/03/09/kais-dukes-author-of-the-quran-corpus-passes-away/); [SIGARAB grubu, 3 Nisan 2024](https://groups.google.com/g/sigarab/c/fY7yglgHj-M/m/n82x-iqiAAAJ)). QAC, Leeds ya da quran.com'da bir duyuru bulunamadı; haber doğrulanamadı. Bu yüzden yazı kişiye değil bakımcılara hitap eder ve vefattan söz etmez.
- quran.com [hakkında](https://quran.com/about-us) ve [destek](https://quran.com/support) sayfaları Corpus.Quran.com'u "Non-profit projects owned, managed, or sponsored by Quran Foundation" altında sayıyor. Bakımcıların lisans izni verme yetkisi belirsiz; 5. soru bunun için eklendi.
- Lisans ifadeleri belgedekilerle aynı. Belgede olmayan cümleler: bildirimin türetilmiş işlerde korunması; "By downloading this data, you agree to the terms and conditions of the GNU License." (bağlantı GPL sürüm 3 metnine gidiyor, [license.jsp](https://corpus.quran.com/license.jsp)); SSS'de "The data should be used purely for research and is made available under the GNU public license." ve "available freely for non-commercial use under the GNU public license" ([SSS](https://corpus.quran.com/faq.jsp)).
- QAC Version 2 deposunda veri lisansı ifadesi yok; son commit 21 Temmuz 2023; README'deki yeni sitenin alan adı satılık görünüyor. Kök ve lemma §2'deki B planı (c) zayıfladı.

**Notlar**
- Gönderilecek metin bu dosyadadır ve Kök ve lemma §2'deki taslaktan türetilmiştir; ikisi çelişirse bu dosya geçerlidir. Dört özgün soru korundu (1–4). Hitap ve giriş A01.1'e göre değişti; 1. soruya SSS alıntısının bağlamı, 2. soruya "değiştirmek yasaktır" alıntısı ve segmentlerin kelimede toplanması eklendi; 5. (yapay zekâ istemleri) ve 6. (hak sahibi) sorular yeni. Kullanım tarifi (kök gezgini, ortak kök ve lemma bağlantıları) Kök ve lemma §3 ve §5'e göre genişletildi.
- Özel yazışma için Quran Foundation'ın genel adresi önerilir. GitHub #81'e yorum yazmak herkese açıktır; istersen ikinci yol olarak kullan.
- Gönderim yolu senin kararın: feedback.quran.com ya da Quran Foundation genel adresi.
- Taahhüdün ("ekip dışına çıkan hiçbir derleme") uygulama noktaları: K-06, P-03, P-05, İçerik paketleri §7 (kaynak düzeyinde süzme), `xref.license` (P-07), BÇ-21 (A13). Kök ve lemma §2 madde 3 ("yalnız iç derlemelerde") ile İçerik paketleri §7 ("`public` derlemeye girmez") bu taahhütten daha gevşek yazıldı; `/belge-esitle` ile "yalnız `dev` derleme" olarak eşitlenir. Quran Foundation İ-06'nın da muhatabıdır; yazılar ayrı ve tek konulu kalır ([QF soruları](./qf-developer-console.md)).
- Bağış, yazıda yalnız "cevap değişir mi" sorusu olarak geçer; karar ya da söz değildir (K-22, S-01).
- Cevap senaryoları [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md) §2.1'dedir: yazılı izin gelirse `kelime-kok` `serbest` olur (atıf ve GPL bildirimiyle); yalnız ticari olmayan kullanıma izin gelirse durum avukata ve proje sahibine sorulur, o zamana kadar `bekliyor` kalır; ret ya da cevapsızlıkta kelime → lemma ataması kendimiz üretilir. Durum değişikliği A39 yordamı (olay kaydı, ikinci onay) ve `/karar` ile yapılır; lisans defteri §3.2, `pipeline/sources/<kimlik>.toml` ve `source` satırı (Kök ve lemma §2 eylem 1) aynı değişiklikte güncellenir (A06'dan sonra); S-15 ve AS-01 kapanır; İ-04 satırı güncellenir.
- Cevap, "İlgili dosyalar" başlığından önce açılacak "## Cevap" bölümüne tarihiyle yazılır.
- GPL'in uygulama koduna etkisi QAC'ye değil avukata sorulur ([avukat soruları](./avukat-sorulari.md) 2. başlık).
- Tarteel (QUL) yazışması bu aşamada yapılmaz (A17, A18; İ-26).

## İlgili dosyalar

- [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) · [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) · [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md)
- [Avukat soruları](./avukat-sorulari.md) · [İnsan adımları](../10-claude-code/06-insan-adimlari.md) · [A01](../10-claude-code/asamalar/A01-yazisma-paketi.md)
