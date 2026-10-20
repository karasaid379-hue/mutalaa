# Quran Foundation: Developer Console ve sorular

> **Sürüm:** 1.0 · **Tarih:** 20 Ekim 2026 · **Durum:** Taslak
> **Bağlı kararlar:** [K-07](../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-21](../00-ozet/02-karar-defteri.md#k-21--i̇çerik-dağıtımı) · [K-22](../00-ozet/02-karar-defteri.md#k-22--gelir-modeli) · [K-25](../00-ozet/02-karar-defteri.md#k-25--i̇lkeler)
> **Muhatap:** Quran Foundation geliştirici desteği · **Dil:** Kontrol listesi Türkçe, sorular İngilizce · **İnsan adımı:** [İ-06](../10-claude-code/06-insan-adimlari.md)
> **Kanal:** developers@quran.com (şartlara göre QF'ye yazılı bildirim adresi; [Connected Apps](https://api-docs.quran.foundation/docs/connected-apps/) sayfası genel sorular için de bu adresi veriyor). Developer Console: [dev-console.quran.foundation](https://dev-console.quran.foundation/projects). Şartlar: [QF Developer Terms](https://api-docs.quran.foundation/legal/developer-terms/), "Last updated: 2026-10-11". Okuma: 2026-10-20.
> **Engellediği iş:** Mushaf A çevrimdışı paketleri (`mushaf-a-cuz-*`; A26); AS-02
> **Gönderim tarihi:** — · **Takip tarihi:** —

> **Hukuki görüş değildir.** Kontrol listesi ve sorular şartların nasıl uygulanacağını sorar; şartları kabul etmek kullanıcının kararıdır.

## Gönderilecek metin

**Subject:** Questions about QCF page fonts and Mushaf layout data in an offline app

Hello Quran Foundation team,

We are developing "Mütâlaa", a free, ad-free Qur'an reading and study app in Turkish for iOS and Android that works fully offline. We would like to offer a Medina Mushaf page view with the QCF page fonts (one font file per Mushaf page) and page layout data, in line with your Developer Terms (last updated 11 October 2026). Before we build it, we would like to check three points.

1. **Fonts.** The QCF V2 page fonts (one file per page) are large (about 93 MB in total), so we would rather not put all of them in the app binary. Suppose we fetch the font files from your documented CDN URLs, group them into 30 per-juz packages and let our app download each package on demand from our own storage, only inside the app and only for its users. Would that be an "integrated part of the Application", or would it count as an "asset package" or "standalone download" under the Developer Terms? If it is not allowed, is loading the fonts at runtime from your CDN the path you recommend?
2. **Layout data.** Offline page rendering needs the page layout data (the "mushafs" resource: page mappings and positioned words). We understand that Content Sync is the only permitted path for an offline copy, that a next sync is required at least every 7 days "when connectivity to QF permits", and that the Application may continue using its previously synced copy while connectivity is unavailable. Would per-juz packages built from a Content Sync copy on our backend, and delivered only to our app's devices, be allowed, or would they be a "prepackaged database or build-time bundle of QF Content"? For the copies on users' devices, is it enough that each device refreshes its packages from our backend copy, which itself syncs with QF at least every 7 days, or must each device sync with QF directly?
3. **Attribution.** Your Developer Terms ask for credit "in a reasonably accessible place" but give no exact wording, and your font rendering guide uses "Quran fonts provided by Quran Foundation." as an example. Is there an exact credit line you require? Our app's Sources and Licenses screen is in Turkish. We would like to show: "Mushaf sayfa fontları: King Fahd Glorious Qur'an Printing Complex; Quran Foundation aracılığıyla." (in English: "Mushaf page fonts: King Fahd Glorious Qur'an Printing Complex; via Quran Foundation."), with a link to quran.foundation. Is this acceptable, or should we show your English sentence as it is?

Kind regards,

[Name] · [e-mail] · Developer Console account: [account e-mail]

## İç notlar (gönderilmez)

**Türkçe özet.** QF'ye üç soru soruluyor:
1. QCF sayfa fontlarını QF'nin belgeli CDN adreslerinden alıp 30 cüz paketine koyarsak ve uygulama bunları yalnız kendi içinde, kendi depomuzdan indirirse bu "uygulamanın bütünleşik parçası" mı sayılır, yoksa şartların yasakladığı "asset package / standalone download" mı? İzinli değilse çalışma anında QF CDN'inden yüklemeyi mi önerirsiniz?
2. Sayfa düzeni verisi (`mushafs`) Content Sync kapsamında. Arka uçtaki Content Sync kopyasından üretilen ve yalnız uygulamamızın cihazlarına giden cüz paketleri izinli mi, yoksa "hazır veritabanı" mı? 7 günlük eşitleme ("bağlantı izin verdiğinde") yükümlülüğü cihazlardaki kopyalara nasıl uygulanır: her cihaz paketlerini arka uçtaki kopyadan yenilerse yeterli mi, yoksa her cihaz doğrudan QF ile mi eşitlenmeli? (Şartlar, 7 günden uzun kesintide önceki eşitlenmiş kopyanın kullanılabileceğini söylüyor.)
3. Şartlar atıf için "makul ölçüde erişilebilir bir yer" diyor ama kesin ifade vermiyor; kılavuzdaki örnek satır "Quran fonts provided by Quran Foundation." İstediğiniz kesin bir satır var mı; Türkçe atıf satırı (İngilizce karşılığıyla) kabul edilir mi?

**Kontrol listesi (İ-06; senin işin)**
- [ ] Quran Foundation hesabıyla [Developer Console](https://dev-console.quran.foundation/projects)'a gir ve [yeni proje](https://dev-console.quran.foundation/projects/new) aç. Hesap e-postası düzenli okunan bir adres olsun: QF'nin bildirimleri bu adrese gider. Şartlar, QF'ye yapılacak bildirimlerin yazılı olmasını ve developers@quran.com'a gönderildiği anda yapılmış sayılmasını söylüyor; QF'nin sana yapacağı bildirimin ne zaman yapılmış sayılacağı şart metninden doğrulanır (A06'da şart kopyası alınırken). Hesap bilgileri depoya yazılmaz.
- [ ] [Şartları](https://api-docs.quran.foundation/legal/developer-terms/) ve [Developer Privacy Policy Packet](https://api-docs.quran.foundation/legal/developer-privacy/)'i baştan sona oku. Kabul, API'yi kullanmakla olur ("By accessing or using ... agree to be bound by these Terms"). Dikkat:
  - Şartlar New York eyaleti hukukuna bağlı; uyuşmazlıkta New York County mahkemeleri yetkili.
  - QF şartları 30 gün önceden bildirerek ya da ihlalde derhâl feshedebilir; fesihte QF içeriğinin silinmesi gerekir.
  - Şartlarda değişiklik bildirimi maddesi bulunamadı; "Last updated" tarihi izlenir ([lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §6: çeyrekte bir ve her `public` sürümden önce).
- [ ] Şartlar uygulama için herkese açık bir gizlilik politikası ve kullanım şartları ister ("Provide a publicly reachable Privacy Policy and Terms of Use for the Application."). Sayfa alan adına bağlıdır (İ-18; [KVKK ve gizlilik](../07-yayin/02-kvkk-ve-gizlilik.md) §2.5).
- [ ] Content API arka uç (backend/server) uygulaması ister; yeni uygulama pre-live ortamında başlar, production izni ayrıca istenir (pre-live ortamındaki veri kapsamının sınırlı olup olmadığı Doğrulanacak). Kimlik bilgileri depoya yazılmaz.
- [ ] Şartların tarihli kopyası A06'da `pipeline/sources/licenses/` altına alınır; bu aşamada alınmaz.
- [ ] Atıfın yeri Ayarlar › Kaynaklar ve lisanslar ("in a reasonably accessible place in the Application or its associated credits"); kesin metin 3. sorunun cevabına göre yazılır.
- [ ] QF içeriği `embed_ok = false` (lisans defteri §1): gömme vektörüne çevrilmez, yapay zekâ API'sine gönderilmez.

**Soruların dayanağı**

| Soru | Dayanak |
|---|---|
| 1 | [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md) AS-02; lisans defteri §3.1 (QPC kartı, Açık soru) ve §8 satır 3; [Mobil mimari](../06-mobil/01-mobil-mimari.md) §7.1; A01.1: şartlarda "cache or bundle", "integrated part of the Application", "asset package, or standalone download"; [Font Rendering kılavuzu](https://api-docs.quran.foundation/docs/tutorials/fonts/font-rendering/) (çalışma anında CDN'den yükleme) |
| 2 | AS-02 (satır düzeni verisi); lisans defteri §3.1 (Content Sync istisnası); A01.1: [Content Sync](https://api-docs.quran.foundation/docs/tutorials/content-sync/getting-started/) `mushafs` kaynağı, 7 günlük eşitleme, "redistribution" tanımı |
| 3 | Lisans defteri §3.1 (atıf, Doğrulanacak); [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) §6; A01.1: kılavuzdaki örnek satır; şartlarda kesin ifade yok |

**A01.1 bulguları (2026-10-20)**
- Şartlar hâlâ "Last updated: 2026-10-11"; belgedeki ifadelerin hepsi duruyor. Font maddesi belgedekinden dar: "A Developer may cache or bundle font files and Mushaf images obtained through QF APIs or documented CDN URLs for use in an Application if the Developer maintains an active account in the Developer Console and credits Quran Foundation in a reasonably accessible place in the Application or its associated credits." Ardından: "The files may be distributed only as an integrated part of the Application. They may not be offered separately to others—for example, through the Developer's own API, asset package, or standalone download." Font maddesinde "embed" sözcüğü geçmiyor; izin "cache or bundle" diye yazılı. "Embeddings" sözcüğü Derived Materials tanımında ve yapay zekâ bölümünde geçiyor (yeniden üretmeye ya da yeniden kurmaya izin veren gömmeler için kısıt); lisans defterindeki `embed_ok = false` kuralının dayanağı budur.
- Sayfa düzeni verisi Content Sync'in `mushafs` kaynağında ("Mushaf metadata, page mappings, and positioned words. Font files and images are not included."). Content Sync çevrimdışı kopya için tek izinli yol; kopya en az 7 günde bir eşitlenir ve yükümlülük "copies kept on a backend or an offline device" için de geçerli. "Serving QF Content from a Developer-controlled backend within the Application's end-user experience is not, by itself, redistribution."
- Şartlar kesin atıf ifadesi tanımlamıyor; kılavuz örnek olarak "Quran fonts provided by Quran Foundation." veriyor.
- Arama dizininde görünen "Mushaf Fonts and Images" sayfası bugün şartları gösteriyor; eski içeriği doğrulanamadı.
- Alıntılar araç tarafından parça parça verildi; A06'da şart kopyası alınırken sayfadan yeniden doğrulanır.
- Belgelerde "gömme" denen izin şartlarda "cache or bundle" olarak geçiyor. 7 günlük eşitleme ve "documented CDN URLs" koşulu Mushaf A paket tasarımını etkiler; A26'da ele alınır.

**Cevap gelince:** AS-02 kapanır; `qpc-v1-font`, `qpc-v2-font`, `qpc-v4-font` ve `medine-604-duzen` kayıtları lisans defterine işlenir (kayıt kimlikleri değişmez; QF'nin kılavuzu sayfa fontlarına "QCF" der). Durum değişikliği A39 yordamı (olay kaydı, ikinci onay) ve `/karar` ile yapılır; lisans defteri ve `pipeline/sources/<kimlik>.toml` aynı değişiklikte güncellenir (A06'dan sonra). "Prepackaged database" cevabı gelirse `medine-604-duzen` `kisitlar.hazir_vt_yasak` alır (P-02: hiçbir pakete giremez); Mushaf A düzen verisi kaynağı yeniden seçilir (lisans defteri §3.1 Açık soru, ED-5, AS-10). Cevap, "İlgili dosyalar" başlığından önce açılacak "## Cevap" bölümüne tarihiyle yazılır; İ-06 satırı güncellenir.

## İlgili dosyalar

- [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) · [Mobil mimari](../06-mobil/01-mobil-mimari.md) · [Kapsam ve fazlar](../01-urun/01-kapsam-ve-fazlar.md) · [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md)
- [QAC lisans sorusu](./qac-lisans.md) · [İnsan adımları](../10-claude-code/06-insan-adimlari.md) · [A01](../10-claude-code/asamalar/A01-yazisma-paketi.md)
