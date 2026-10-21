# İnsan adımları

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Canlı belge
> **Bağlı kararlar:** [K-05](../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-06](../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-31](../00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)

Claude Code bu işleri yapamaz: hukuki ve kurumsal yazışma, hesap açma, ödeme, izin almak, insan editör kararı, sistem geneli kurulum. Claude Code hazırlığı yapar (taslak, kontrol listesi, araç), işi siz yaparsınız ve sonucu Claude Code'a söylersiniz; Claude Code bu dosyayı günceller. Bir aşama, bağlı olduğu insan adımı `tamam` olmadan o kısmına başlamaz.

Durum değerleri: `bekliyor`, `taslak hazır`, `gönderildi`, `sürüyor`, `tamam`, `gerekmiyor`.

| No | İş | Dayanak | Beklettiği aşama | Claude Code'un desteği | Durum | Tarih ve not |
|---|---|---|---|---|---|---|
| İ-01 | Araç kurulumu ve ilk açılış (Git, Node 24, pnpm, .NET 10, uv, WSL2, Docker Desktop, EAS CLI, isteğe bağlı Android Studio, Claude Code) ve Windows hazırlığı; uçtan uca testler için Maestro CLI (Windows kurulumu A33'te doğrulanır) | [Kurulum](./01-kurulum.md) | A00, A03, A21, A33 (Maestro) | A00'da sürüm denetimi ve eksik listesi; A33'te Maestro kurulum yolu | sürüyor | 2026-10-19: Git 2.53, Node 24.21, .NET 10.0.402, uv 0.13.1, EAS 25.2.0 ve pnpm 12.14.0 (npm ile) tamam. 2026-10-20: Docker Desktop 4.95.0 `winget` ile kuruldu (Docker 29.8.2, Compose v5.6.0); motor ilk açılış ve şartların kabulüyle başlatılacak, `docker version` sunucu sürümü dönünce tamam (A03 öncesi). Eksik: adb/Android Studio (isteğe bağlı). Yönetici gerektirenler: `LongPathsEnabled` (şu an 0), 8081 ve 8333 güvenlik duvarı kuralları, Wi-Fi ağı "Özel" profili. Yapıldı: `git config --global core.longpaths true`, `PYTHONUTF8=1` (kullanıcı ortamı). WSL varsayılan dağıtım Ubuntu, sürüm 2. Notlar: varsayılan `dotnet` şu an 11.0 RC (`global.json` A02'de 10.0'a sabitler); küresel `core.autocrlf` tanımsız, bu depoda yerel `false` geçerli; yol 53 karakter, boşluk ve ASCII dışı karakter içeriyor, C: sürücüsünde 454 GB boş. Güvenlik duvarı kuralları yönetici yetkisi olmadan sorgulanamadı. 2026-10-21: Docker motoru çalışıyor (sunucu 29.8.2); A03.3'ten önceki Docker koşulu sağlandı. Yönetici ayarları (LongPathsEnabled, 8081/8333 güvenlik duvarı kuralları, Özel ağ profili) hâlâ doğrulanmadı: A03.4'teki LAN testi aynı makineden yapıldığı için güvenlik duvarı kuralını kanıtlamaz |
| İ-02 | Kurul ön görüşme talebini göndermek, cevabı kaydetmek | [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) §7 | A33 (dış test), A34, A38 | `/yazisma kurul` | taslak hazır | [taslak](../yazismalar/kurul-on-gorusme.md) · 2026-10-20 |
| İ-03 | Fikri haklar avukatıyla görüşme: Risale metninin işlenmesi, metinsiz atıf dizini, harici API'ye gönderim, hesaplar için KVKK | [Fazlar](../08-yol-haritasi/01-fazlar.md) Faz 0 | A20 (metin), A31 (Risale metni), A35 | `/yazisma avukat` | taslak hazır | [taslak](../yazismalar/avukat-sorulari.md) · 2026-10-20 |
| İ-04 | QAC bakımcılarına (quran.com ekibi) lisans sorusu (kök ve lemma verisi) | AS-01, [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md) §2 | A17 (`kelime-kok` yayını) | `/yazisma qac` | taslak hazır | [taslak](../yazismalar/qac-lisans.md) · 2026-10-20 |
| İ-05 | KFGQPC'ye Hafs yazı tipi için yazılı izin talebi | [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) | Mushaf C'de KFGQPC fontu (yedek: Amiri Quran) | `/yazisma kfgqpc` | taslak hazır | [taslak](../yazismalar/kfgqpc-hafs-font.md) · 2026-10-20 |
| İ-06 | Quran Foundation Developer Console hesabı ve şartların okunması | AS-02 | A26 | `/yazisma qf` (kontrol listesi) | taslak hazır | [taslak](../yazismalar/qf-developer-console.md) · 2026-10-20 |
| İ-07 | Hafız görüşmeleri ve yazılı izin (en az iki Türk hafız) | [Ses sistemi](../06-mobil/02-ses-sistemi.md) §12 | A27 (yayın için), A34 | `/yazisma hafiz` | taslak hazır | [taslak](../yazismalar/hafiz-izin.md) · 2026-10-20 |
| İ-08 | Tanzil'e soru: ayrı sütundaki normalize arama metni "değiştirme" sayılır mı | ÇŞ-2, [Çapa şeması](../03-veri/01-capa-semasi.md) §13 | A34 (bilgi) | `/yazisma tanzil` | taslak hazır | [taslak](../yazismalar/tanzil-arama-metni.md) · 2026-10-20 |
| İ-09 | Elmalılı özgün baskısının (1935–38) tarama nüshasını edinmek | [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) | A09, A16 | Tarama envanteri şablonu, alım komutu | bekliyor | |
| İ-10 | OCR altın örneklemini elle yazmak (CER ölçümü için) | [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md) | A09 | Örneklem listesi ve yazım kuralları | bekliyor | |
| İ-11 | Meal, Naim tercümesi aktarımı ve (sonra) tefsir düzeltme turları | [Elmalılı hazırlığı](../04-icerik/03-elmalili-hazirligi.md), [Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md), G-MET, G-INC | A16, A19, A37 | Editör panelinde düzeltme kuyruğu, ilerleme raporu | bekliyor | |
| İ-12 | Kelime anlamı taslaklarını ve Türkçe kelime → kök eşlemelerini onaylamak | [Kelime anlamları](../04-icerik/06-kelime-anlamlari.md), [Kök ve lemma](../05-capraz-referans/03-kok-ve-lemma.md), K-19 | A17, A18 (A18.2) | Taslak üretimi, inceleme kuyruğu | bekliyor | |
| İ-13 | Altın set etiketleme (atıf, iktibas, kök) | [Test stratejisi](../07-yayin/03-test-stratejisi.md) §4 | A18 | Örneklem seçimi, etiketleme arayüzü, ölçüm | bekliyor | |
| İ-14 | Hadis kaynak seçimi ve Naim tercümesinin taranması | [Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md) | A19 | Aday kaynak karşılaştırması, alım bağdaştırıcısı | bekliyor | |
| İ-15 | Expo hesabı ve `eas login`; Apple Developer ve Google Play hesapları | [Yerel geliştirme](../02-mimari/04-yerel-gelistirme.md) §1 | A21 (Expo), A34 (mağaza) | Hesap kontrol listesi, `eas.json` | bekliyor | |
| İ-16 | GitHub özel deposu, `git remote add`, `EXPO_TOKEN` sırrı | [Proje yapısı](../02-mimari/03-proje-yapisi.md) §7 | A08 | İş akışı dosyaları, kontrol listesi | sürüyor | 2026-10-19: private depo `karasaid379-hue/mutalaa` ve `origin` hazır. Kalan: `EXPO_TOKEN` sırrı (A08) |
| İ-17 | Anthropic API anahtarı ve bütçe (hattaki yapay zekâ taslakları, görsel OCR) | [İçerik hattı](../04-icerik/02-icerik-hatti.md) §10–§11 | A09 (görsel OCR denemesi), A16, A17 | `uv run mutalaa llm estimate` ile maliyet tahmini | bekliyor | Anahtar `pipeline/.env` dosyasına sizin tarafınızdan yazılır |
| İ-18 | Canlı içerik deposu (öneri Cloudflare R2) ve alan adı | K-21, [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md) | A33 (iç dağıtım paketleri), A34 | Depo ayar kontrol listesi | bekliyor | |
| İ-19 | Kurul başvurusu ve onayı | [Yayın kapısı ve Kurul](../07-yayin/01-yayin-kapisi-ve-kurul.md) §7 | A34 | Başvuru dosyası, içerik özetleri, değişiklik listesi | bekliyor | |
| İ-20 | Barındırma seçimi (v1.x hesapları için) | K-20 | A35 | Seçenek karşılaştırması (`arastirmaci`) | bekliyor | |
| İ-21 | Referans cihazların seçimi (orta seviye Android, iOS 16.4 sınıfı) | AS-08 | A33 | Ölçüm betikleri | bekliyor | |
| İ-22 | "Öneri" işaretli hedeflerin onayı (B-03, B-04, B-11, B-13 ve diğerleri) | AS-09 | A33, A34 | Listeyi çıkarır, `/karar` ile kaydeder | bekliyor | |
| İ-23 | Türkçe sure adlarının ve varyantlarının girişi ve editör onayı (`surah_alias`, `shared/data/sure-adlari.json`) | [İktibas tespiti](../05-capraz-referans/02-iktibas-tespiti.md) §2; [A11](./asamalar/A11-kuran-yapisi-ve-sayfa-eslemesi.md) | A11 (A11.3) | Giriş şablonu (`.tmp/sure-adlari-girdi.tsv`), içe aktarma, editör kuyruğu | bekliyor | |
| İ-24 | Risale içindekilerinin ve baskı sayfa verisinin basılı nüshadan girilmesi | [Risale hazırlığı](../04-icerik/05-risale-hazirligi.md) §3; [A20](./asamalar/A20-risale-altyapisi.md) | A20 (A20.2, A20.3) | Dosya biçimi ve doğrulayıcı | bekliyor | Değerleri Claude Code yazmaz |
| İ-25 | Sunnah.com'a izin talebi ve fawazahmed0 bakımcısına metin kaynağı sorusu | [Hadis hazırlığı](../04-icerik/04-hadis-hazirligi.md) §4; [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §8 satır 6 | A19 | `/yazisma sunnah` · `/yazisma fawaz` | bekliyor | |
| İ-26 | Tarteel (QUL) kaynak lisansı yazışması | [Kaynaklar ve lisans defteri](../04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.2, §8 satır 5 | Yalnız QUL verisi pakete alınacaksa (A17, A18) | `/yazisma qul` | gerekmiyor | QUL verisi pakete alınmaya karar verilirse `bekliyor` olur |
| İ-27 | Sentry hesabı, projesi ve DSN; proje ayarında IP saklamanın kapatılması, kaynak eşlemesi yükleme sırrı | [Mobil mimari](../06-mobil/01-mobil-mimari.md) §12; [KVKK ve gizlilik](../07-yayin/02-kvkk-ve-gizlilik.md) | A32 (`internal` derlemeden önce), A33, A34 | DSN'in yazılacağı yerlerin listesi, `beforeSend` testi | bekliyor | DSN'i `apps/mobile/.env.local` ve EAS ortamına siz yazarsınız |
| İ-28 | Risale lügati maddelerinin yazımı ve onayı (editör; korumalı lügatlere bakılmaz) | [Risale hazırlığı](../04-icerik/05-risale-hazirligi.md) §3.5 | A20 (altyapı hazır olunca), A31 (gerçek maddelerle gösterim) | Başlık söz listesi, editör kuyruğu, serbest sözlüklerden taslak | bekliyor | Durdurmaz; metin `kapali` olduğu sürece yalnız `dev` |

## Nasıl güncellenir

- Bir taslak hazırlanınca (`/yazisma`) durum `taslak hazır` olur ve taslak dosyasına bağlanır (`docs/yazismalar/`).
- Gönderdiğinizde Claude Code'a "İ-02 gönderildi, tarih …" deyin: durum `gönderildi`, takip tarihi not sütununa yazılır.
- Cevap gelince özeti söyleyin ya da dosyayı verin: durum `tamam`, cevabın özeti ve etkisi (ör. lisans durumu değişikliği) yazılır; lisans durumu değişiyorsa A39 yordamı ve `/karar` çalışır.
- İlerleme dosyasının durum bloğundaki "Bekleyen insan adımları" satırı buna göre güncellenir.

## İlgili dosyalar

- [Aşama haritası](./04-asama-haritasi.md) · [İlerleme](./05-ilerleme.md) · [Çalışma düzeni](./02-calisma-duzeni.md)
- [Fazlar](../08-yol-haritasi/01-fazlar.md) · [Riskler](../08-yol-haritasi/03-riskler.md) · [Sonra yapılacaklar](../08-yol-haritasi/02-sonra-yapilacaklar.md)
