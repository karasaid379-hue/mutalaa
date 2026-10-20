# Mütâlaa · Proje Dokümanları

> **Sürüm:** 1.1 · **Tarih:** 19 Ekim 2026 · **Durum:** Onaylı (v1 planı)

**Mütâlaa**, Kur'an-ı Kerîm'i mushaf sayfasında, karşısında Elmalılı meali ve yanında âyeti izleyen tefsiriyle okutan, seçilen hafızla dinleten ve bir kelimeye ya da kelime grubuna dokununca Kur'an'da, tefsirde, hadiste ve Risale-i Nur'da nerede geçtiğini gösterip okunan yere geri döndüren, çevrimdışı çalışan bir mobil okuma ve öğrenme uygulamasıdır.

Bu klasör (`docs/`), 16–18 Ekim 2026 araştırma ve beyin fırtınası oturumunda verilen kararları uygulanabilir bir plana çevirir. Proje kökü masaüstündeki `mutalaa-kit` klasörüdür (ilk adı `mutalaa-docs`; [K-23](./00-ozet/02-karar-defteri.md) güncelleme notu); kod da aynı kökte durur ve yalnız Claude Code ile geliştirilir ([K-31](./00-ozet/02-karar-defteri.md#k-31--geliştirme-aracı-claude-code)). Eski `quran-app-docs` planı (Mayıs 2026) arşiv ve referans olarak kalır; çelişkide bu klasör geçerlidir.

## Nereden başlamalı

1. [Ürün özeti](./00-ozet/01-urun-ozeti.md): ne yapıyoruz, kimin için, neden farklı.
2. [Karar defteri](./00-ozet/02-karar-defteri.md): bütün kararlar ve gerekçeleri. **Tek doğruluk kaynağı.**
3. [Kapsam ve fazlar](./01-urun/01-kapsam-ve-fazlar.md): ilk sürümde ne var, ne yok.
4. [Genel mimari](./02-mimari/01-genel-mimari.md): parçalar ve veri akışı.
5. [Yerel geliştirme](./02-mimari/04-yerel-gelistirme.md): kendi bilgisayarında kurulum.
6. [Fazlar](./08-yol-haritasi/01-fazlar.md): iş sırası ve bitiş ölçütleri.
7. [Claude Code ile geliştirme](./10-claude-code/README.md): kurulum, çalışma düzeni, A00–A40 aşamaları, ilerleme.

## Klasörler

| Klasör | İçerik | Dosyalar |
|---|---|---|
| `00-ozet/` | Ürünün özü, kararlar, terimler | [Ürün özeti](./00-ozet/01-urun-ozeti.md) · [Karar defteri](./00-ozet/02-karar-defteri.md) · [Sözlük](./00-ozet/03-sozluk.md) |
| `01-urun/` | Kapsam, okuma deneyimi, ekranlar, tasarım sistemi | [Kapsam ve fazlar](./01-urun/01-kapsam-ve-fazlar.md) · [Okuma deneyimi](./01-urun/02-okuma-deneyimi.md) · [Mobil ekranlar](./01-urun/03-mobil-ekranlar.md) · [Tasarım sistemi](./01-urun/04-tasarim-sistemi.md) |
| `02-mimari/` | Sistem, teknoloji yığını, depo yapısı, kurulum, API | [Genel mimari](./02-mimari/01-genel-mimari.md) · [Teknoloji yığını](./02-mimari/02-teknoloji-yigini.md) · [Proje yapısı](./02-mimari/03-proje-yapisi.md) · [Yerel geliştirme](./02-mimari/04-yerel-gelistirme.md) · [Backend API](./02-mimari/05-backend-api.md) |
| `03-veri/` | Adresler, veritabanı, paketler, kullanıcı verisi, arama | [Çapa şeması](./03-veri/01-capa-semasi.md) · [Editoryal veritabanı](./03-veri/02-editoryal-veritabani.md) · [İçerik paketleri](./03-veri/03-icerik-paketleri.md) · [Kullanıcı verisi ve senkron](./03-veri/04-kullanici-verisi-ve-senkron.md) · [Arama (FTS5)](./03-veri/05-arama-fts5.md) |
| `04-icerik/` | Kaynaklar, lisanslar ve içerik hazırlığı | [Kaynaklar ve lisans defteri](./04-icerik/01-kaynaklar-ve-lisans-defteri.md) · [İçerik hattı](./04-icerik/02-icerik-hatti.md) · [Elmalılı](./04-icerik/03-elmalili-hazirligi.md) · [Hadis](./04-icerik/04-hadis-hazirligi.md) · [Risale-i Nur](./04-icerik/05-risale-hazirligi.md) · [Kelime anlamları](./04-icerik/06-kelime-anlamlari.md) |
| `05-capraz-referans/` | Bağlantıların türleri ve üretimi | [Bağlantı modeli](./05-capraz-referans/01-baglanti-modeli.md) · [İktibas tespiti](./05-capraz-referans/02-iktibas-tespiti.md) · [Kök ve lemma](./05-capraz-referans/03-kok-ve-lemma.md) · [Anlamsal katman](./05-capraz-referans/04-anlamsal-katman.md) |
| `06-mobil/` | Mobil uygulamanın iç yapısı | [Mobil mimari](./06-mobil/01-mobil-mimari.md) · [Ses sistemi](./06-mobil/02-ses-sistemi.md) · [Depolama yöneticisi](./06-mobil/03-depolama-yoneticisi.md) |
| `07-yayin/` | Lisans kapısı, Kurul, KVKK, testler | [Yayın kapısı ve Kurul](./07-yayin/01-yayin-kapisi-ve-kurul.md) · [KVKK ve gizlilik](./07-yayin/02-kvkk-ve-gizlilik.md) · [Test stratejisi](./07-yayin/03-test-stratejisi.md) |
| `08-yol-haritasi/` | Fazlar, sonra yapılacaklar, riskler | [Fazlar](./08-yol-haritasi/01-fazlar.md) · [Sonra yapılacaklar](./08-yol-haritasi/02-sonra-yapilacaklar.md) · [Riskler](./08-yol-haritasi/03-riskler.md) |
| — | Kaynak listesi | [Kaynakça](./09-kaynakca.md) |
| `yazismalar/` | Kurul, avukat ve izin sahiplerine gidecek yazışma taslakları (gönderen kullanıcıdır) | [Kurul](./yazismalar/kurul-on-gorusme.md) · [Avukat](./yazismalar/avukat-sorulari.md) · [QAC](./yazismalar/qac-lisans.md) · [KFGQPC](./yazismalar/kfgqpc-hafs-font.md) · [Quran Foundation](./yazismalar/qf-developer-console.md) · [Hafız](./yazismalar/hafiz-izin.md) · [Tanzil](./yazismalar/tanzil-arama-metni.md) |
| `10-claude-code/` | Claude Code ile geliştirme: rehber, aşamalar, ilerleme, insan adımları | [Rehber](./10-claude-code/README.md) · [Kurulum](./10-claude-code/01-kurulum.md) · [Çalışma düzeni](./10-claude-code/02-calisma-duzeni.md) · [Ajanlar, beceriler ve kurallar](./10-claude-code/03-ajanlar-beceriler-kurallar.md) · [Aşama haritası](./10-claude-code/04-asama-haritasi.md) · [İlerleme](./10-claude-code/05-ilerleme.md) · [İnsan adımları](./10-claude-code/06-insan-adimlari.md) |

## Kararlar bir bakışta

| Konu | Karar |
|---|---|
| İçerik | Kur'an + Elmalılı meali, hadis (Tecrîd-i Sarîh + Kütüb-i Sitte Arapça), Risale-i Nur altyapısı; kitaplar sonra |
| Lisans | Her şey şimdi hazırlanır; yayın kapısı yalnız serbest ve onaylı içeriği mağazaya çıkarır |
| Mushaf | A · Medine düzeni, B · Türk hattı, C · akan metin; kullanıcı seçer |
| Platform | Önce mobil (Expo SDK 57 → 58), web sonra (Next.js 16) |
| Arka uç | ASP.NET Core 10 + PostgreSQL 18 |
| İçerik hattı | Python 3.13 (uv) |
| Hesap | v1.x'te; ilk sürüm hesapsız ve çevrimdışı |
| Arama | Cihazda SQLite FTS5 |
| Barındırma | Şimdilik kendi bilgisayarda; canlıda düşük maliyetli yöntem sonra |
| Gelir | Şimdilik yok; fiyatlandırma sonra |
| Geliştirme | Yalnız Claude Code ile, proje klasörünün içinde, aşama aşama |

Tamamı ve gerekçeleri: [Karar defteri](./00-ozet/02-karar-defteri.md).

## Çalışma kuralları

- **Önce karar defteri.** Bir karar değişecekse önce [karar defteri](./00-ozet/02-karar-defteri.md) güncellenir, sonra ilgili dosyalar.
- **Dosya başlığı.** Her dosya sürüm, tarih, durum (Onaylı / Taslak) ve bağlı karar numaralarıyla açılır, "İlgili dosyalar" ile biter.
- **Bilinmeyenler işaretli.** Henüz bilinmeyen noktalar "Açık soru", doğrulanması gerekenler "Doğrulanacak" diye yazılır. Hepsini bulmak için klasörde bu iki ifadeyi aratın.
- **Hukuki konular.** Lisans ve mevzuat notları araştırma raporuna dayanır, kaynak linki taşır ve hukuki görüş yerine geçmez.

## Referanslar

- **Vitrin sayfası:** "Mütâlaa Okuma Uygulaması". Tıklanabilir okuma masası, mushaf seçenekleri, özellik haritası, tasarım dili, içerik takvimi.
- **Araştırma raporu:** `Kuran Risale okuma uygulaması araştırması.md` (16 Ekim 2026).
- **Eski plan:** `quran-app-docs/` (Mayıs 2026). Teknoloji kararları [K-30](./00-ozet/02-karar-defteri.md#k-30--eski-plandan-çıkarılanlar) ile geçersiz; okuyucu tasarımları ve ilkeler referans.
