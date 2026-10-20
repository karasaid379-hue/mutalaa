# Fikri haklar avukatına sorular

> **Sürüm:** 1.0 · **Tarih:** 20 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-03](../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-19](../00-ozet/02-karar-defteri.md#k-19--kuran-kelime-anlamları) · [K-22](../00-ozet/02-karar-defteri.md#k-22--gelir-modeli) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Muhatap:** Fikri haklar avukatı · **Dil:** Türkçe · **İnsan adımı:** [İ-03](../10-claude-code/06-insan-adimlari.md)
> **Kanal:** Kullanıcı belirler; avukatın adı ve iletişim bilgisi depoya yazılmaz.
> **Engellediği iş:** Risale metninin işlenmesi ve atıf dizini (A20, A31); `kelime-kok` paketinin yayını (A17); Elmalılı aktarımının ve kelime anlamlarının lisansı; v1 gizlilik metni (A32, A34). Hesaplı sürümün soruları A35'te ayrıca sorulur.
> **Gönderim tarihi:** — · **Takip tarihi:** —

> **Hukuki görüş değildir.** Bu dosya avukata sorulacak soruları ve dayandıkları bilgileri toplar; değerlendirmeyi avukat yapar.

## Gönderilecek metin

**Konu:** Mütâlaa okuma uygulaması: telif, veri lisansı ve kişisel veri soruları

Sayın [Avukatın adı],

Mütâlaa adıyla, Kur'an-ı Kerîm'i mealiyle okumak ve hadis ile Risale-i Nur'daki ilgili yerlere bağlanarak çalışmak için Türkçe bir mobil uygulama hazırlıyoruz. Uygulama ücretsiz ve reklamsızdır, hesap istemez ve çevrimdışı çalışır; bugün bir gelir modeli yoktur. Yayından önce aşağıdaki altı konuda yazılı görüşünüzü almak istiyoruz. Her başlıkta bildiğimiz durumu kısaca yazdık; dayandığımız kaynaklar yazının sonundadır.

### 1. Risale-i Nur

Said Nursî 1960'ta vefat etti; Külliyat'ın 1 Ocak 2031'de serbest kalacağını düşünüyoruz. Kültür ve Turizm Bakanlığı 2014'te bandrol başvurularını, mirasçıların hakları birlikte kullanması gerektiği gerekçesiyle reddetmişti. Aynı yılın Kasım ayında bir Bakanlar Kurulu kararı kullanım haklarını Diyanet İşleri Başkanlığına verdi; karar, 6552 sayılı Kanunla değişen FSEK m. 47'nin birinci cümlesine dayanıyordu. Anayasa Mahkemesi bu hükmü 14 Mayıs 2015 tarihli kararıyla iptal etti (Resmî Gazete, 11 Haziran 2015). O tarihten bu yana hakları kimin kullandığını gösteren bir kaynak bulamadık. Görüşünüz gelene kadar Risale metnini (paragraflar ve cümleler) işlemiyoruz.

1. Külliyat üzerindeki mali hakları bugün kim kullanıyor; izin için kime başvurulmalı?
2. Metin, dağıtılmadan ve yalnız ekip içinde şu işler için işlenebilir mi: (a) âyet atıf dizini çıkarmak; (b) arama için metnin sayısal gösterimini (anlam vektörü, "gömme") üretmek; (c) arama ve atıf sonuçlarının doğruluğunu ölçmek için elle etiketlenmiş küçük bir örnek küme hazırlamak?
3. Yukarıdaki işlerden herhangi biri için metin, yurt dışındaki bir yapay zekâ hizmetinin (dil modeli API'si) sunucularına gönderilebilir mi?
4. Metin içermeyen bir atıf dizini (hangi âyetin hangi kitapta, hangi bölümde ve hangi baskının kaçıncı sayfasında geçtiği) uygulamanın davetli test ve mağaza sürümlerinde yayımlanabilir mi?
5. Bu dizin metnin otomatik işlenmesiyle değil, basılı kitaplardan elle çıkarılırsa cevabınız değişir mi?

### 2. Quranic Arabic Corpus verisi ve GPL

Kelimelerin kök ve lemma bilgisini Quranic Arabic Corpus'tan (QAC) almayı düşünüyoruz. İndirme sayfası veriyi GNU GPL ile (bağlantı sürüm 3 metnine gidiyor) ve dosyanın değiştirilmeden kopyalanması şartıyla, kaynak gösterilerek herhangi bir web sitesinde ya da uygulamada kullanmaya izin veriyor; sıkça sorulan sorular sayfası ise araştırma projeleri için "ticari amaçla kullanmama" şartı koyuyor. Sitenin telif satırında projenin yazarı Kais Dukes'un adı var; ikincil kaynaklara göre Dukes 2024'te vefat etti; sitenin bakımını bugün quran.com ekibi yapıyor. Bakımcılara ayrıca yazıyoruz. Cevap gelene kadar bu veri uygulamanın ana paketinden ayrı bir pakette tutulacak ve yalnız ekip içi sürümde görünecek.

1. GPL lisanslı bir veri dosyasının ya da ondan değiştirilmeden üretilen tabloların uygulamayla birlikte dağıtılması, uygulamanın kaynak kodu için GPL yükümlülüğü doğurur mu?
2. Dosya ayrı bir indirme paketinde aynen dağıtılır ve tablolar ilk açılışta kullanıcının cihazında kurulursa durum değişir mi?
3. Türkçe kelime anlamlarımız bizim verdiğimiz kalıcı lemma kimliklerine bağlı; bir Kur'an kelimesinin hangi lemmaya ait olduğu bilgisi (kelime → lemma ataması) QAC'den gelir ve ayrı bir eşleme tablosunda durur. Bu ayrım anlamları GPL kapsamı dışında tutar mı? Anlamlar QAC'nin lemma bilgisi kullanılmadan doğrudan kelime numaralarına (sure, âyet, kelime sırası) bağlanırsa sonuç değişir mi? Not: kelime numaralarımız QAC'nin kelime konumlarıyla aynıdır; kelime bölmesi Tanzil metninden yapılır ve QAC'ye karşı denetlenir.
4. Yazarın vefat ettiği haberi doğruysa veri için izni kim verebilir; sitenin bakımcısının vereceği izin yeterli olur mu?

### 3. Sipariş eser, aktarım ve taramalar

Elmalılı Muhammed Hamdi Yazır'ın Hak Dini Kur'an Dili adlı eseri (meali dahil) Diyanet İşleri Riyâseti ile yapılan bir sözleşmeyle yazıldı. Müellif 1942'de vefat etti; eserin 1 Ocak 2013'ten beri serbest olduğunu düşünüyoruz. Tecrîd-i Sarîh çevirisi de 1925'te sipariş edildi ve Babanzâde Ahmed Naim'e verildi; çevirinin bir kısmını Naim (ö. 1934), kalanını Kâmil Miras (ö. 1957) hazırladı. Hangi ciltlerin kime ait olduğunu henüz kesinleştiremedik. Elmalılı metnini özgün ilk baskının taramalarından, sadeleştirmeden ve ekleme yapmadan aktaracağız.

1. Bir eserin bir kurumla yapılan sözleşmeyle ya da kurumun siparişiyle yazılmış olması hak sahipliğini ya da koruma süresinin hesabını etkiler mi? Soru Elmalılı'nın eseri ve Tecrîd-i Sarîh tercümesi için geçerli.
2. Özgün baskının sadeleştirilmeden yapılan düz aktarımı FSEK m. 6/8'deki "alelade transkripsiyon" sayılır mı; aktarım, yapana yeni bir hak doğurur mu?
3. Bir kütüphanenin dijitalleştirdiği sayfa taramalarını kullanmanın hukuki durumu nedir? Kütüphanenin kullanım şartları dışında, taramanın kendisi üzerinde bir hak doğar mı?

### 4. Kendi ürettiğimiz metinlerin lisansı

Elmalılı aktarımımızı ve Kur'an kelimeleri için yazacağımız Türkçe anlamları uygulamada ve indirilebilir paketlerde dağıtacağız. Anlamların taslağını bir yapay zekâ modeli çıkaracak; hiçbir anlam insan onayından geçmeden yayımlanmayacak.

1. Bu metinleri hangi lisansla dağıtmamız uygun olur (ör. CC BY-SA 4.0, CC BY 4.0, CC0 ya da tüm hakları saklı)? Seçimin bize ve kullanıcılara yüklediği yükümlülükler nelerdir?
2. Yapay zekâ taslağından insan eliyle düzenlenen anlamlarda koruma doğar mı; doğarsa kimin adına?

### 5. "Ticari olmayan kullanım" şartı

QAC'nin şartı 2. başlıkta anlatıldı. Kur'an metnini aldığımız Tanzil projesinin lisans sayfası Creative Commons Atıf 3.0 derken sıkça sorulan sorular sayfası, kaynaklarının "ticari olmayan amaçlarla" kullanılabileceğini söylüyor; bunu Tanzil'e de soruyoruz. Uygulama ücretsiz ve reklamsızdır; bugün bir gelir modeli yoktur.

1. Ücretsiz ve reklamsız olan, bugün bir gelir modeli bulunmayan uygulamamız hem QAC'nin hem Tanzil'in "ticari olmayan" şartlarına uyar mı?
2. Uygulama ileride bağış kabul ederse bu değerlendirme değişir mi?

### 6. Kişisel veriler (yalnız hesapsız ilk sürüm)

İlk sürüm hesap istemez; notlar, işaretler ve okuma ilerlemesi yalnız kullanıcının cihazında kalır; reklam ve izleme yoktur. Cihazdan iki tür bilgi çıkar. İçerik paketleri ve sesler indirilirken, her internet isteğinde olduğu gibi IP adresi ve isteğin taşıdığı cihaz bilgisi içerik deposu ve içerik dağıtım ağı (CDN) sağlayıcısına ulaşır; değerlendirdiğimiz sağlayıcılar veriyi yurt dışında tutuyor. Uygulama çökerse kişisel verilerden arındırılmış teknik bir hata raporu yurt dışındaki bir hata izleme servisine gider. Kullanıcı bunu ayarlardan kapatabilecek; anahtarın varsayılan değerine henüz karar vermedik.

1. İçerik sağlayıcısının tuttuğu erişim kayıtları ile kişisel verilerden arındırılmış hata raporu KVKK anlamında kişisel verinin yurt dışına aktarımı sayılır mı? Standart sözleşme ya da bildirim gerekir mi?
2. Gizlilik metninde veri sorumlusu olarak kimin adı ve hangi iletişim bilgisi yazılmalı: gerçek kişi mi, tüzel kişi mi? Bu seçim hafız ve lisans izinlerini ve Kurul başvurusunu da etkileyeceği için hangi yapıyı önerirsiniz?

Görüşme için uygun olduğunuz zamanı bildirirseniz memnun oluruz.

Saygılarımızla,

[Ad Soyad] · [e-posta] · [telefon]

**Kaynaklar**
- Fikir ve Sanat Eserleri Kanunu (5846), güncel metin: https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=5846&MevzuatTur=1&MevzuatTertip=3
- Anayasa Mahkemesi, 14.05.2015, E.2014/177, K.2015/49 (RG 11.06.2015, sayı 29383): https://www.resmigazete.gov.tr/eskiler/2015/06/20150611.htm
- Kültür ve Turizm Bakanlığının 2014 kararı (AA/Sondakika): https://www.sondakika.com/guncel/haber-risale-i-nur-kulliyati-nin-basimi-6272228/ · Bakanlar Kurulu kararı, 2014 (Hürriyet): https://www.hurriyet.com.tr/yazarlar/yalcin-bayer/nereden-nereye-27679980
- TDV İslâm Ansiklopedisi, "Risâle-i Nûr Külliyatı": https://islamansiklopedisi.org.tr/risale-i-nur-kulliyati
- Quranic Arabic Corpus, indirme sayfası: https://corpus.quran.com/download/ · sıkça sorulan sorular: https://corpus.quran.com/faq.jsp · ana sayfa (telif ve bakım satırı altbilgide): https://corpus.quran.com/
- Kais Dukes'un vefatına dair ikincil kaynaklar: https://sohaibsandhu.com/2024/03/09/kais-dukes-author-of-the-quran-corpus-passes-away/ · https://groups.google.com/g/sigarab/c/fY7yglgHj-M/m/n82x-iqiAAAJ
- Tanzil, metin lisansı: https://tanzil.net/docs/text_license · sıkça sorulan sorular: https://tanzil.net/docs/faq
- Küre Ansiklopedi, "Hak Dini Kur'an Dili": https://kureansiklopedi.com/tr/detay/hak-dini-kuran-dili-2 · "Kâmil Miras": https://kureansiklopedi.com/tr/detay/miras-kamil

## İç notlar (gönderilmez)

**Soruların dayanağı**

| Soru | Dayanak |
|---|---|
| 1.1 | [Fazlar](../08-yol-haritasi/01-fazlar.md) Faz 0; [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) S-06; [Risale hazırlığı](../04-icerik/05-risale-hazirligi.md) §1; [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.5 |
| 1 (giriş) | AYM künyesi A01.1'de düzeltildi: iptal kararı 14.05.2015, E.2014/177, K.2015/49 (RG 11.06.2015, 29383); [Risale hazırlığı](../04-icerik/05-risale-hazirligi.md) §1, lisans defteri §3.5 ve kaynakça aynı künyeyle eşitlendi. Künyeyi göndermeden önce [Resmî Gazete fihristinde](https://www.resmigazete.gov.tr/eskiler/2015/06/20150611.htm) kendin teyit et (karar metnine araçla erişilemedi). Bakanlığın 2014 kararı Risale hazırlığı §1'de bandrol başvurularının reddi olarak geçiyor |
| 1.2 | [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) §2.4 madde 1; K-05; [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md) AS-04 |
| 1.3 | Yayın kapısı ve Kurul §2.4 madde 2; lisans defteri §1 (`embed_ok`) |
| 1.4 | Yayın kapısı ve Kurul §2.4 madde 3; Risale hazırlığı §2 (yol 2) ve §4 |
| 1.5 | Risale hazırlığı §3.4 (son paragraf) |
| 2.1 | Lisans defteri §3.2 (Açık soru) |
| 2.2 | [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) §2 madde 4 (B planı a) |
| 2.3 | [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md) §2.1 ve §9; [Editoryal veritabanı](../03-veri/02-editoryal-veritabani.md) ED-4; [Belge çelişkileri](../10-claude-code/07-belge-celiskileri.md) BÇ-02 |
| 2.4 | A01.1 araştırması (2026-10-20): [QAC lisans sorusu](./qac-lisans.md), "A01.1 bulguları" (telif satırı, bakımcı, ikincil kaynaklarda vefat haberi); lisans defteri §3.2 |
| 3.1 | Lisans defteri §3.3 ve §8 satır 8; [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) §1 ve §11 madde 3; [Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md) §1 (Tecrîd-i Sarîh'in siparişi); lisans defteri §3.4 (Naim'in çevirdiği ciltler Doğrulanacak) |
| 3.2 | Elmalılı hazırlığı §1 (FSEK m. 6/8); lisans defteri §3.3 |
| 3.3 | Elmalılı hazırlığı §3 (tarama kaynağı; FSEK m. 1/B ve m. 2/3 çıkarımı) |
| 4.1 | Sonra yapılacaklar S-12; Elmalılı hazırlığı §11 madde 4; Kelime anlamları §9 |
| 4.2 | Kelime anlamları §9 |
| 5.1, 5.2 | Kelime anlamları §2.1; lisans defteri §8 satır 4; K-22; Sonra yapılacaklar S-01; A01.1 Tanzil bulgusu ([Tanzil sorusu](./tanzil-arama-metni.md), 2. soru) |
| 6.1 | [KVKK ve gizlilik](../07-yayin/02-kvkk-ve-gizlilik.md) §2.1 (indirme isteği IP adresini ve cihaz bilgisini sağlayıcıya ulaştırır), §2.2 madde 5 (hata raporu anahtarı bulunur; varsayılan değeri Açık soru), §2.4 ve §5 madde 1 |
| 6.2 | KVKK ve gizlilik §2.5 ve §5 madde 3; Sonra yapılacaklar S-11 |

**Notlar**
- Hesaplı sürümün soruları (KVKK ve gizlilik §3, §5 madde 4–7) bu yazıya girmedi; A35'te ayrıca yazılır.
- Bağış yazıda yalnız soru olarak geçer; karar ya da söz değildir (K-22, S-01).
- "Kâr amacı gütmeyen" ifadesi kullanılmadı: tüzel kişilik yok (S-11) ve gelir modeli hakkında söz verilmez (K-22).
- Elmalılı ilk baskısının yılları belgelerde iki biçimde geçiyor ([Belge çelişkileri](../10-claude-code/07-belge-celiskileri.md) BÇ-22, A09'da çözülür); yazıda yıl verilmedi.
- Avukata ayrıca sorulabilecek, mektuba girmeyen noktalar (karar senin): (a) Mushaf sayfa yazı tiplerinin telif bildirimi yalnız Kral Fahd Kompleksi'ni gösteriyor ve haklar saklı diyor; bu yazı tiplerini dağıtan Quran Foundation'ın geliştirici şartlarındaki izin yeterli dayanak mıdır (A26'dan önce; [Lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1, Riskler R-04)? (b) Hafızların ve diğer hak sahiplerinin adı, iletişim bilgisi ve imzalı izin belgesi (Kurul'la paylaşım dahil) için aydınlatma metni gerekir mi (İ-07)? (c) Hafız izninin ileride kurulacak bir tüzel kişiliğe devri ve Kurul arşivine verilen kopyaların izin geri alındıktan sonraki durumu. (d) Risale hazırlığındaki "Şimdi" işleri (içindekiler, bölüm başı sayfa numaraları, kelime-sıklık listesi) belgelere göre Risale metnini gerektirmiyor; mektuba bu yüzden girmedi.
- Cevap gelince: cevabın metni, "İlgili dosyalar" başlığından önce açılacak "## Cevap" bölümüne tarihiyle yazılır. Risale kaynaklarının durumu (K-05, K-06; `kapali` ancak olumlu görüşle `ic_kullanim` olur; `embed_ok` değişikliği), `risale-atif-dizini`, `qac-morfoloji` ve `kelime-kok`, kendi metinlerimizin lisansı (S-12) ve gizlilik metni (KVKK ve gizlilik §2.5) güncellenir. Lisans durumunu değiştiren cevapta A39 yordamı (olay kaydı, ikinci onay), `/karar` ve `/belge-esitle` çalışır; lisans defteri ve `pipeline/sources/<kimlik>.toml` aynı değişiklikte güncellenir (A06'dan sonra). İ-03 satırı güncellenir.

## İlgili dosyalar

- [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) · [KVKK ve gizlilik](../07-yayin/02-kvkk-ve-gizlilik.md) · [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md)
- [Risale hazırlığı](../04-icerik/05-risale-hazirligi.md) · [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) · [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md) · [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md)
- [QAC lisans sorusu](./qac-lisans.md) · [Tanzil sorusu](./tanzil-arama-metni.md) · [Hafız izin mektubu](./hafiz-izin.md) · [Kurul ön görüşme talebi](./kurul-on-gorusme.md)
- [İnsan adımları](../10-claude-code/06-insan-adimlari.md) · [A01](../10-claude-code/asamalar/A01-yazisma-paketi.md)
