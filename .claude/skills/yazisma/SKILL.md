---
name: yazisma
description: >-
  Mütâlaa'nın insan adımları için yazışma taslakları hazırlar (Kurul ön görüşmesi, fikri haklar
  avukatı, QAC, KFGQPC, Quran Foundation, hafız izni, Tanzil sorusu, Sunnah.com, fawazahmed0, Tarteel
  QUL); taslakları docs/yazismalar/ altına yazar, asla göndermez. Bir aşama yazışma taslağı
  istediğinde ya da kullanıcı /yazisma <muhatap> yazdığında kullan.
argument-hint: "[kurul | avukat | qac | kfgqpc | qf | hafiz | tanzil | sunnah | fawaz | qul]"
---

# Yazışma taslağı

Muhatap: `$ARGUMENTS`

Taslağı sen hazırlarsın; gönderen ve karar veren kullanıcıdır. Hiçbir e-postayı, formu ya da mesajı gönderme. Taslaklar soru sorar ve izin ister; hukuki görüş değildir.

## Muhataba göre dosya ve kaynak bölümler

| Muhatap | Dosya (`docs/yazismalar/`) | İnsan adımı | Dil | Okunacak bölümler |
|---|---|---|---|---|
| `kurul` | `kurul-on-gorusme.md` | İ-02 | Türkçe | [Yayın kapısı ve Kurul](../../../docs/07-yayin/01-yayin-kapisi-ve-kurul.md) §7; [Kapsam ve fazlar](../../../docs/01-urun/01-kapsam-ve-fazlar.md) §2.2, AS-03, AS-11 |
| `avukat` | `avukat-sorulari.md` | İ-03 | Türkçe | [Fazlar](../../../docs/08-yol-haritasi/01-fazlar.md) Faz 0; [Yayın kapısı ve Kurul](../../../docs/07-yayin/01-yayin-kapisi-ve-kurul.md) §2.4; [Risale hazırlığı](../../../docs/04-icerik/05-risale-hazirligi.md); [KVKK ve gizlilik](../../../docs/07-yayin/02-kvkk-ve-gizlilik.md); AS-04 |
| `qac` | `qac-lisans.md` | İ-04 | İngilizce | [Kök ve lemma](../../../docs/05-capraz-referans/03-kok-ve-lemma.md) §2; [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.2, §8 satır 4; AS-01 |
| `kfgqpc` | `kfgqpc-hafs-font.md` | İ-05 | İngilizce | [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1, §8 satır 2 |
| `qf` | `qf-developer-console.md` | İ-06 | Kontrol listesi Türkçe, sorular İngilizce | [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1, §8 satır 3; [Mobil mimari](../../../docs/06-mobil/01-mobil-mimari.md) §7.1; AS-02 |
| `hafiz` | `hafiz-izin.md` | İ-07 | Türkçe | [Ses sistemi](../../../docs/06-mobil/02-ses-sistemi.md) §12; [Sonra yapılacaklar](../../../docs/08-yol-haritasi/02-sonra-yapilacaklar.md) |
| `tanzil` | `tanzil-arama-metni.md` | İ-08 | İngilizce | [Çapa şeması](../../../docs/03-veri/01-capa-semasi.md) §7 ve §13 (ÇŞ-2); [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.1, §8 satır 1 |
| `sunnah` | `sunnah-izin.md` | İ-25 | İngilizce | [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.4, §8 satır 6; [Hadis hazırlığı](../../../docs/04-icerik/04-hadis-hazirligi.md) §4 |
| `fawaz` | `fawazahmed0-kaynak.md` | İ-25 | İngilizce | [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.4; [Hadis hazırlığı](../../../docs/04-icerik/04-hadis-hazirligi.md) §4 |
| `qul` | `qul-lisans.md` | İ-26 | İngilizce | [Kaynaklar ve lisans defteri](../../../docs/04-icerik/01-kaynaklar-ve-lisans-defteri.md) §3.2, §8 satır 5 |

Muhatap tabloda yoksa dur ve listeyi göster. Bir muhatap için dosya zaten varsa üzerine yazma; farkı göster ve kullanıcıya sor.

## Taslak dosyasının düzeni

Bu düzen [A01](../../../docs/10-claude-code/asamalar/A01-yazisma-paketi.md) A01.2 ile aynıdır.

1. Dosya başı: muhatap, dil, ilgili insan adımı, iletişim kanalı (resmî sayfadan doğrulanmış; doğrulanamadıysa "Doğrulanacak"), engellediği iş, `Durum:` (`Taslak`, `Onaylandı`, `Gönderildi`, `Cevaplandı`), `Gönderim tarihi:`, `Takip tarihi:` ve `> **Hukuki görüş değildir.**` satırı.
2. **Gönderilecek metin:** kısa amaç paragrafı (kâr amacı gütmeyen, reklamsız uygulama; K-22, K-25), numaralı ve kısa sorular ya da talepler, ekler listesi (eki uydurma; yoksa "hazırlanacak" yaz), gönderen bilgisi yer tutucuyla (`[Ad Soyad]`, `[e-posta]`, `[telefon]`; kişisel bilgi uydurma).
3. **İç notlar (gönderilmez):** her sorunun dayandığı belge ve bölüm; İngilizce taslaklarda kullanıcı için kısa Türkçe özet.

Dosya adı ASCII'dir. Kur'an, meal, hadis ya da Risale metni örnek diye yazılmaz.

## Sonra

- `docs/10-claude-code/06-insan-adimlari.md` içinde ilgili satırın durumunu `taslak hazır` yap ve taslak dosyasına bağlan.
- Kullanıcıya taslağı gözden geçirmesini, göndermesini ve gönderim tarihini söylemesini iste. Tarih gelince taslakta `Durum: Gönderildi` ve tarih, insan adımları dosyasında `gönderildi`; cevap gelince `Cevaplandı` ve `tamam`, cevabın özeti taslak dosyasının sonuna eklenir. Cevap bir lisans durumunu değiştiriyorsa A39 yordamı ve `/karar` çalışır.
