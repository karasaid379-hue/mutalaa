# A01 · Hukuk ve izin yazışma paketi

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-28](../../00-ozet/02-karar-defteri.md#k-28--ses)
> **Faz:** 0 · Hazırlık · **Önkoşul:** [A00](./A00-ortam-ve-depo.md) · **İnsan adımı:** [İ-02 … İ-08](../06-insan-adimlari.md) (gönderim)
> **Ajanlar:** `arastirmaci` · `lisans-denetcisi` · **Beceriler:** `yazisma` · `lisans-kapisi` · **Tahmini oturum:** 1–2 (gönderim ve cevap beklemesi hariç)
> **Başlat:** `/asama A01`

## Amaç
Faz 0'ın kritik yolundaki hukuk ve izin işleri kod beklemeden başlar. Kurul ön görüşmesi, avukat soruları, QAC, KFGQPC, Quran Foundation, hafız izinleri ve Tanzil sorusu için gönderilmeye hazır taslaklar `docs/yazismalar/` altına yazılır. Gönderim kullanıcının işidir; aşama gönderim ve takip tarihlerini kayda geçirir. Faz 0 çıkış ölçütü "Kurul'a talep gitti; cevap ya da takip tarihi kayıtlı" bu aşamayla sağlanır ([Fazlar](../../08-yol-haritasi/01-fazlar.md), Faz 0). Taslaklar soru sorar ve izin ister; hukuki görüş değildir.

## Okunacak belgeler
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §2.4 telif soruları, §6 atıf tablosu, §7 Kurul planı (tamamı)
- [Fazlar](../../08-yol-haritasi/01-fazlar.md): Faz 0 işleri ve çıkış ölçütleri, §4 kritik yol
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §3.1 (Tanzil, KFGQPC, QPC), §3.2 (QAC), §3.3 (Elmalılı), §3.7 (ses), §8 yazışma listesi
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §13 ÇŞ-2 · [Arama](../../03-veri/05-arama-fts5.md): §1.4 (Tanzil sorusunun bağlamı)
- [Kök ve lemma](../../05-capraz-referans/03-kok-ve-lemma.md): §2 (QAC'ye hazır İngilizce taslak)
- [Ses sistemi](../../06-mobil/02-ses-sistemi.md): §12 hafız lisans kapısı
- [Sonra yapılacaklar](../../08-yol-haritasi/02-sonra-yapilacaklar.md): S-06, S-07, S-11, S-12, S-15
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §2.4, §5 (v1 için avukata giden sorular)
- [Kapsam ve fazlar](../../01-urun/01-kapsam-ve-fazlar.md): §9 AS-01 … AS-04, AS-11 · [Ürün özeti](../../00-ozet/01-urun-ozeti.md): Kurul'a giden ürün tanımı için

## Kapsam
**Yapılır**
- Yedi taslak dosyası, muhatap başına bir dosya, `/yazisma <muhatap>` becerisiyle (`kurul`, `avukat`, `qac`, `kfgqpc`, `qf`, `hafiz`, `tanzil`).
- Kurumların iletişim kanallarının ve güncel şart sayfalarının doğrulanması.
- Gönderim ve takip tarihlerinin taslak başlığına ve `06-insan-adimlari.md` dosyasına işlenmesi.

**Yapılmaz**
- E-posta göndermek ya da görüşme ayarlamak (kullanıcı yapar: İ-02 … İ-08).
- Tarteel (QUL) ve Sunnah.com yazışmaları: kaynak seçilince A17 ve A19'da (İ-26, İ-25).
- Lisans kopyalarının `pipeline/sources/licenses/` altına alınması ve TOML kayıtları (A06).
- Cevapların lisans defterine ve kaynak kayıtlarına işlenmesi: cevap geldiğinde `/karar` ve `/belge-esitle` ile.
- Kurul başvuru dosyası ve ön yazısı (A34).

## Adımlar
### A01.1 · Kanal ve şart doğrulaması
- `arastirmaci` beş kurum için resmî iletişim yolunu ve güncel şart sayfasını kaynak bağlantısı ve okuma tarihiyle raporlar:
  - Kurul (Mushafları İnceleme ve Kıraat Kurulu): başvuru ve iletişim kanalı Doğrulanacak; `mushaflariinceleme.diyanet.gov.tr` araştırmada hata verdi (Yayın kapısı §7.2 adım 1).
  - Tanzil: iletişim yolu; canlı tanzil.net şartları (lisans defteri §3.1: canlı sayfadan okunmadı).
  - QAC: iletişim yolu (Kök ve lemma §2'deki taslak QAC sorumlusuna hitap eder).
  - KFGQPC: resmî lisans sayfası ve yazılı izin kanalı (lisans defteri §3.1: sayfa okunmadı).
  - Quran Foundation: Developer Terms'ün son sürümü (11 Ekim 2026 güncellemesi, 30 gün bildirimle fesih), Developer Console adımları, istenen kesin atıf ifadesi (Doğrulanacak).
- Doğrulanamayan kanal taslakta "Doğrulanacak" kalır; kullanıcıdan bilgi istenir. Hafız ve avukat kanalını kullanıcı bilir.
- **Bitti sayılır:** beş kurumun her biri için kanal satırı kaynaklı bir değer ya da "Doğrulanacak" notu taşıyor.

### A01.2 · Taslak dosyalarının ortak düzeni
- Dosya başı: muhatap, dil, ilgili insan adımı, kanal (A01.1), engellediği iş, durum (`Taslak`, `Onaylandı`, `Gönderildi`, `Cevaplandı`), `Gönderim tarihi:`, `Takip tarihi:` ve "> **Hukuki görüş değildir.**" satırı.
- İki bölüm: "Gönderilecek metin" ve "İç notlar (gönderilmez)". İç notlar her sorunun dayandığı belgeyi ve bölümü yazar.

| Dosya | Muhatap | İnsan adımı | Dil | Dayanak |
|---|---|---|---|---|
| `kurul-on-gorusme.md` | Kurul | İ-02 | Türkçe | Yayın kapısı §7; AS-03, AS-11 |
| `avukat-sorulari.md` | Fikri haklar avukatı | İ-03 | Türkçe | Fazlar Faz 0; Yayın kapısı §2.4; AS-04 |
| `qac-lisans.md` | Quranic Arabic Corpus | İ-04 | İngilizce | Kök ve lemma §2; AS-01; S-15 |
| `kfgqpc-hafs-font.md` | KFGQPC | İ-05 | İngilizce (öneri) | Lisans defteri §3.1, §8 satır 2 |
| `qf-developer-console.md` | Quran Foundation | İ-06 | Kontrol listesi Türkçe, sorular İngilizce | Lisans defteri §3.1, §8 satır 3; AS-02 |
| `hafiz-izin.md` | Hafızlar | İ-07 | Türkçe | Ses sistemi §12; S-07 |
| `tanzil-arama-metni.md` | Tanzil | İ-08 | İngilizce (öneri) | ÇŞ-2; lisans defteri §3.1, §8 satır 1 |

- **Bitti sayılır:** yedi dosya bu düzende açıldı.

### A01.3 · Kurul ön görüşme talebi (İ-02)
- Kısa talep yazısı ve dört ek:
  1. Bir sayfalık ürün tanımı ([Ürün özeti](../../00-ozet/01-urun-ozeti.md)'nden): çevrimdışı, reklamsız, üç mushaf görünümü, Tanzil metni, özgün baskıdan Elmalılı meali, izinli hafız kayıtları.
  2. Kaynak listesi: Yayın kapısı §7.1 tablosundaki içerik türleri ve yerleri.
  3. Sürüm dondurma yaklaşımı: içerik özeti, `release` kaydı, onay treni (§7.2 adım 2, §7.3).
  4. Soru listesi: §7.5'teki on soru; §7.3'teki açık ve doğrulanacak maddeler (ses kodlaması, zamanlama, font sürümü ve sayfa düzeni verisi değişince yeniden onay; Kur'an içeriğine dokunmayan arayüz düzeltmelerinin yeniden onay gerektirmemesi; acil düzeltme için hızlı yol); [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md) §11'in 7. ve 8. soruları (meal tek başına mı onaylanır; onaysız meal davetli testte gösterilebilir mi).
- Uygulama ekranı henüz yoktur. Görsel uydurulmaz; vitrin sayfasındaki görselleri kullanıcı ekler ya da yazı "görüşmede gösterilecek" der (öneri).
- **Bitti sayılır:** dosya dört eki ve §7.5'in on sorusunun hepsini taşıyor; her sorunun iç notunda bölüm numarası var.

### A01.4 · Avukat soruları (İ-03)
- Altı başlık; her soru iç notta belgeye bağlanır:
  1. **Risale-i Nur** (K-05, S-06): hakları bugün kim kullanıyor; telifli metin dizin, gömme ve altın set için ekip içinde işlenebilir mi (§2.4 madde 1); harici dil modeli API'sine gönderilebilir mi (madde 2); metinsiz atıf dizini `internal` ve `public` derlemede yer alabilir mi (madde 3); basılı kitaptan elle dizin çıkarmak ([Risale hazırlığı](../../04-icerik/05-risale-hazirligi.md) §3.4).
  2. **QAC ve GPL:** GPL verinin uygulama paketinde dağıtılmasının uygulama koduna etkisi (lisans defteri §3.2); dosyanın ayrı pakette aynen dağıtılıp tabloların cihazda kurulması (Kök ve lemma §2, B planı a); kelime anlamlarının QAC lemma kimliklerine bağlı olmasının etkisi ([Kelime anlamları](../../04-icerik/06-kelime-anlamlari.md) §9; Editoryal veritabanı ED-4).
  3. **Sipariş eser ve aktarım:** Elmalılı'nın Diyanet sözleşmesiyle yazılmasının ve Tecrîd'in hak durumuna etkisi (lisans defteri §8 satır 8); yayımlanmış ve koruma süresi dolmuş bir eserin düz aktarımının hususiyet ölçütüyle (FSEK m. 1/B ve m. 6) yeni hak doğurup doğurmadığı; m. 6/8 yalnız yayımlanmamış eserler içindir, kıyasen uygulanıp uygulanamayacağı sorulur (Elmalılı hazırlığı §1; hukuki görüş değildir); kütüphane taramalarının durumu ve "her hakkı saklıdır" şartının `embed_ok`'a etkisi (Elmalılı hazırlığı §3).
  4. **Kendi metinlerimizin lisansı:** aktarımlar ve kelime anlamları (S-12; Elmalılı hazırlığı §11 madde 4).
  5. **"Ticari olmayan kullanım" şartı:** gelir modeli olmayan bugünkü durum (K-22) bu şarta uyuyor mu (Kelime anlamları §2.1).
  6. **KVKK, yalnız v1:** CDN erişim kayıtları ve hata raporunun yurt dışına aktarımı; veri sorumlusunun gerçek ya da tüzel kişi olması (KVKK §5 madde 1 ve 3; S-11). Hesap soruları A35'e kalır.
- **Bitti sayılır:** dosya altı başlığı taşıyor; her soru en az bir belge bölümüne bağlı.

### A01.5 · QAC, KFGQPC, QF ve Tanzil yazıları (İ-04, İ-05, İ-06, İ-08)
- **QAC:** Kök ve lemma §2'deki İngilizce taslak temel alınır; dört soru korunur (ücretsiz ve bağış alabilen uygulama; değişmeden SQLite'a çevirme; ayrı düzeltme katmanı; atıf satırı).
- **KFGQPC:** KFGQPC Uthmanic Script HAFS (v0.09 EULA) için yazılı izin: ücretsiz uygulamada gömme ve dağıtım, değiştirmeme taahhüdü; alt kümelemenin değişiklik sayılıp sayılmadığı; atıf satırı (lisans defteri §3.1). Yedek Amiri Quran'dır; yazıda söz verilmez.
- **QF:** İ-06 kontrol listesi (Developer Console hesabı; şartları kullanıcı okur ve kabul eder; şart kopyası A06'da alınır; atıfın uygulamadaki yeri) ve QF'ye üç soru: cüz başına QPC font paketinin kendi depomuzdan indirilmesi "gömme" sayılır mı; düzen verisinin çevrimdışı paketlenmesi (Content Sync istisnası hazır veritabanı dağıtımına izin vermiyor); istenen kesin atıf ifadesi.
- **Tanzil:** ÇŞ-2: metin bayt bayt saklanır, NFC uygulanmaz, bildirim ve tanzil.net bağlantısı korunur (K-26); ayrı sütundaki normalize arama metni ya da içeriksiz FTS indeksi "changing" sayılır mı (Arama §1.4, AR-3). Uthmani dosyasının sürüm numarası da sorulur.
- **Bitti sayılır:** dört dosya hazır; QAC dosyası dört soruyu, QF dosyası kontrol listesini ve üç soruyu taşıyor.

### A01.6 · Hafız izin mektubu (İ-07)
- Şablon, S-07'deki yedi maddeyi açıkça sorar: iç test ve mağaza dağıtımı, çevrimdışı indirme, Kurul'a sunma, zamanlama verisi üretme, atıf biçimi, ücretli katmana konmama, kaldırma usulü. Kaldırma isteğinde paketin `kapali` olacağı ve dosyaların silineceği yazılır (Ses sistemi §12).
- Görüşme kontrol listesi: en az iki Türk hafız (Fazlar, Faz 0); rapordaki 3–5 okuyucuyla başlama önerisi; kayıt biçimi ve zamanlama soruları (Ses sistemi SS-5, SS-7).
- Hafız adı ve iletişim bilgisi yer tutucudur (`[Hafızın adı]`); köşeli ayraç kullanılır, çünkü ASCII harfle başlayan açılı ayraç markdown önizlemesinde HTML etiketi sayılıp kaybolabilir. Rapordaki örnek adlar yalnız iç notta durur.
- **Bitti sayılır:** şablon yedi maddenin hepsini taşıyor.

### A01.7 · İnceleme, onay ve kayıt
- `lisans-denetcisi` taslakları lisans defteri ve karar defteriyle karşılaştırır: dokümanda olmayan iddia, tarih, ücret ya da söz yok; her dosyada "Hukuki görüş değildir." var.
- Kullanıcı taslakları okur, düzeltir, onaylar ve gönderir. Gönderilen her yazı için dosya başına ve `06-insan-adimlari.md` içindeki ilgili İ satırına gönderim tarihi ve takip tarihi yazılır (takip: gönderimden 14 gün sonra; öneri). Gönderilmeyen yazı için neden yazılır.
- Cevap gelince cevabın metni taslağın "Cevap" bölümüne eklenir; sonuç `/karar` ile karar defterine, `/belge-esitle` ile lisans defterine ve ilgili belgeye işlenir.
- **Bitti sayılır:** İ-02'nin gönderim ve takip tarihi kayıtlı; diğer İ'ler gönderildi ya da neden notu taşıyor.

## Kabul ölçütleri
- [ ] `docs/yazismalar/` altında yedi dosya var (A01.2 tablosundaki adlarla).
- [ ] Yedi dosyanın her birinde "Hukuki görüş değildir." satırı var.
- [ ] `kurul-on-gorusme.md` Yayın kapısı §7.5'in on sorusunu taşıyor; iç notlar bölüm numarası veriyor (gözle).
- [ ] `lisans-denetcisi` raporu: dokümana dayanmayan iddia ya da söz yok.
- [ ] Taslaklarda Kur'an, meal, hadis ya da Risale metninden alıntı yok; kişisel iletişim bilgisi yok (gözle).
- [ ] `06-insan-adimlari.md` içinde İ-02 gönderim ve takip tarihi dolu.
- [ ] Taslaklardaki göreli bağlantılar kırık değil (`/belge-esitle` bağlantı denetimi).

## Doğrulama
```bash
ls docs/yazismalar/
grep -c "Hukuki görüş değildir" docs/yazismalar/*.md          # her dosyada en az 1
grep -n "Gönderim tarihi:\|Takip tarihi:" docs/yazismalar/*.md
grep -n "İ-02" docs/10-claude-code/06-insan-adimlari.md
git diff --stat docs/yazismalar docs/10-claude-code/06-insan-adimlari.md
```

## Dikkat
- Hukuki görüş değildir. Taslaklar soru sorar; yorum, değerlendirme ve taahhüt içermez. Ücret, tarih, onay ya da gelir modeli hakkında söz verilmez (K-22).
- İçerik etiği: taslaklara Kur'an, meal, hadis ya da Risale metni konmaz. Örnek gerekiyorsa çapa adresi verilir (`q:2:255`).
- Kişisel veri: hafızların ve avukatın telefon ve e-posta adresleri depoya yazılmaz; yer tutucu kalır, kullanıcı gönderirken doldurur.
- Claude Code e-posta göndermez, form doldurmaz, hesap açmaz. QF şartlarını kabul etmek kullanıcının işidir (New York hukuku ve 30 gün fesih koşulu kullanıcıya gösterilir).
- Muhataplara giden metin kısa ve tek konuludur; iç notlar gönderilmez.
- Cevap durum değiştirebilir: QAC cevabı `qac-morfoloji`, KFGQPC cevabı `kfgqpc-hafs-font`, Tanzil cevabı AR-3 kararını etkiler. Değişiklik yalnız `/karar` ile yapılır. Ayrıntı: `lisans-kapisi`.

## İnsan adımları
Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).
- İ-02 · Kurul ön görüşme talebini göndermek: A01.3 bittikten sonra; cevap kaydedilir.
- İ-03 · Avukatla görüşme: soru listesi A01.4'ten.
- İ-04 · QAC'ye e-posta: A01.5'ten sonra.
- İ-05 · KFGQPC'ye yazılı izin talebi: A01.5'ten sonra.
- İ-06 · Quran Foundation Developer Console hesabı ve şartların kabulü: A01.5'teki kontrol listesiyle.
- İ-07 · Hafız görüşmeleri ve yazılı izin: A01.6'dan sonra.
- İ-08 · Tanzil'e soru: A01.5'ten sonra.

## Çıktılar
- `docs/yazismalar/kurul-on-gorusme.md`, `avukat-sorulari.md`, `qac-lisans.md`, `kfgqpc-hafs-font.md`, `qf-developer-console.md`, `hafiz-izin.md`, `tanzil-arama-metni.md`
- `docs/10-claude-code/06-insan-adimlari.md`: İ-02 … İ-08 satırlarında gönderim ve takip tarihleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A01-yazisma-paketi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · [İnsan adımları](../06-insan-adimlari.md) · Önceki: [A00](./A00-ortam-ve-depo.md) · Sonraki: [A02](./A02-tek-depo-iskeleti.md)
