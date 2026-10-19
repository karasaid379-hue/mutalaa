---
name: asama
description: >-
  Mütâlaa'nın bir geliştirme aşamasını (A00–A40) baştan sona yürütür; önkoşul denetimi, plan ve onay,
  uygulama, doğrulama, inceleme, belge ve ilerleme kaydı, commit. Kullanıcı /asama A07, /asama A07.2
  ya da /asama sonraki yazdığında kullanılır.
argument-hint: "[A07 | A07.2 | sonraki]"
disable-model-invocation: true
---

# Aşama yürütücüsü

İstenen: `$ARGUMENTS`

Aşamalar `docs/10-claude-code/asamalar/` altındadır. Harita: `docs/10-claude-code/04-asama-haritasi.md`. Durum: `docs/10-claude-code/05-ilerleme.md`. İnsan adımları: `docs/10-claude-code/06-insan-adimlari.md`.

## 0. Aşamayı belirle

- `A07` biçimindeyse dosya `docs/10-claude-code/asamalar/A07-*.md` olur. `A07.2` biçimindeyse yalnız o adım yürütülür, ama önce adımın önkoşulu olan önceki adımlar ilerleme notunda tamam görünmelidir.
- Boşsa ya da `sonraki` ise: ilerleme tablosunda durumu `bekliyor` olan ve bütün önkoşulları `tamam` olan (adım listeli önkoşulda yalnız o adımlar; bölüm 1) ilk aşamayı seç. Birden çok aday varsa listele ve kullanıcıya sor.
- Dosya bulunamazsa dur; aşama haritasındaki listeyi göster.

## 1. Önkoşulları denetle

1. Aşama dosyasının başlığındaki "Önkoşul" aşamaları ilerleme tablosunda `tamam` mı? Önkoşulda yalnız belirli adımlar yazılıysa (ör. "A11 (A11.2 yeterli)"), o adımların ilerleme notunda tamam görünmesi yeterlidir.
2. "İnsan adımı" maddeleri insan adımları dosyasında `tamam` mı? Değilse hangi adımın beklendiğini ve aşamanın hangi kısmının yine de yapılabileceğini söyle; devam için kullanıcıya sor.
3. `git status --short` temiz mi? Değilse değişiklikleri göster ve ne yapılacağını sor (commit, ayrı tutma ya da vazgeçme kullanıcının kararıdır). Depo henüz yoksa (A00.4 öncesi) bu denetim atlanır.
4. Hepsi uygunsa ilerleme dosyasında aşama satırını `sürüyor` yap, başlangıç tarihini yaz, durum bloğunu güncelle (biçim aşağıda).

## 2. Hazırlan

- Aşama dosyasını baştan sona oku. "Okunacak belgeler" listesindeki bölümleri oku; listede olmayan belgeyi gerekmedikçe açma.
- Dosyada "Doğrulanacak" ya da `arastirmaci` adımı varsa ilgili maddeleri `arastirmaci` ajanına ver. Birbirinden bağımsız maddeleri paralel çalıştır.
- `docs/10-claude-code/07-belge-celiskileri.md` §1 tablosunda "Aşama" sütunu bu aşama olan ve durumu `açık` olan maddeleri bul. Her birini ilgili belge bölümleriyle oku; plana "Önce karar" başlığıyla koy.

## 3. Plan ve onay

- Planı göster: önce karar bekleyen belge çelişkileri (öneriyle birlikte), sonra adımlar, oluşacak ve değişecek dosyalar, her adımı hangi ajanın yapacağı, çalıştırılacak testler, riskler ve açık sorular.
- Kullanıcı bir çelişki için karar verince: karar defterini etkiliyorsa `/karar`, yalnız belgeyi etkiliyorsa `belge-bekcisi` ile belgeyi düzelt; maddenin durumunu `çözüldü (YYYY-AA-GG)` yap ve kararı tek cümleyle yaz. Karar ertelenirse madde `açık` kalır; ona bağlı iş yapılmaz.
- Kullanıcı onay vermeden kod yazma. Kullanıcı planı değiştirirse planı güncelle ve yeniden onay al.

## 4. Uygula

- Adımları sırayla yürüt. Bağımsız işleri ilgili geliştirici ajanlara paralel devret (ör. aynı kuralın üç dildeki uygulaması: `web-gelistirici`, `sunucu-gelistirici`, `hat-gelistirici`); sonuçları birleştir ve çakışmaları çöz.
- Her adımın "Bitti sayılır" ölçütünü komut çıktısıyla kanıtla, sonra sonraki adıma geç. Uzun bir adım yarıda kalırsa ilerleme notuna nerede kalındığını yaz.
- Kapsamda kal. Aşama dosyasının "Yapılmaz" listesindeki işi, adını vererek o aşamaya bırak.
- Yeni bir karar gerekirse dur ve `/karar` öner. Bir "Doğrulanacak" çözülürse kaynağıyla not al (7. adımda belgeye işlenir).

## 5. Doğrula

- "Doğrulama" bölümündeki komutların hepsini çalıştır; çıktıları kısaltarak rapora koy.
- "Kabul ölçütleri"nin her maddesini kanıtıyla işaretle. Kanıtlanamayan madde varsa aşama bitmiş sayılmaz; nedenini yaz.

## 6. İncele

- `inceleyici` ajanını çalıştır.
- Ek denetçiler: metin, çapa, normalizasyon ya da arama koduna dokunulduysa `metin-denetcisi`; kaynak, paket, görünürlük, manifest ya da bağımlılık değiştiyse `lisans-denetcisi`; ekran ya da bileşen değiştiyse `arayuz-denetcisi`.
- Engelleyici ve önemli bulguları düzelt, ilgili testleri yeniden çalıştır, gerekirse denetimi tekrarla. Öneri düzeyindeki bulguları kullanıcıya listele.

## 7. Belgeleri ve ilerlemeyi güncelle

- Kod belgeden saptıysa ya da bir "Doğrulanacak" çözüldüyse `belge-bekcisi` ajanıyla ilgili belgeyi güncelle (karar değişikliği `/karar` ile yapılır).
- İlerleme dosyasında:
  - Aşama satırı: durum (`tamam`; insan adımı bekliyorsa `engelli`; başka bir nedenle yarıda kaldıysa `sürüyor`), bitiş tarihi, commit kısa özeti, kısa not. `engelli` ve `sürüyor` durumunda Not sütunu biten adımları ve bekleneni yazar (ör. "A11.1, A11.2, A11.4–A11.6 tamam; İ-23 bekleniyor"); kısmi önkoşul denetimi bu nota bakar.
  - Durum bloğu (işaretler aynen kalır):
    ```
    <!-- durum:baslangic -->
    - Aktif aşama: yok
    - Son tamamlanan: A07 · Editoryal veritabanı (2026-10-25)
    - Sıradaki: A08 · CI iş akışları
    - Bekleyen insan adımları: İ-02 (Kurul cevabı)
    - Son güncelleme: 2026-10-25
    <!-- durum:bitis -->
    ```
  - Oturum günlüğüne bir satır: `2026-10-25 · A07 · ne yapıldı · sıradaki adım`.
- Tarihleri `YYYY-AA-GG` biçiminde yaz; bugünün tarihini sistemden al, uydurma.

## 8. Commit

- `/commit` becerisinin kurallarıyla, değişiklikleri anlamlı birimlere bölerek commit at.
- Push: A08'e kadar aşama bittiğinde dalı ve hedefi göster (`git status -sb`, `git remote -v`), sonra `git push origin main` çalıştır; komut kullanıcıdan onay ister. A08'den sonra aşama dalı açılır, dal itilir ve PR'ı kullanıcı birleştirir ([Proje yapısı](../../../docs/02-mimari/03-proje-yapisi.md) §6). Zorla push yapılmaz.

## 9. Kapanış raporu

Türkçe ve kısa:
- Yapılanlar ve kabul ölçütleri (`[x]` ya da `[ ]` ve kanıt).
- Açık kalanlar, bekleyen insan adımları, kullanıcı kararı gereken noktalar.
- Sıradaki aşama ve öneri: "Yeni bir oturum için `/clear`, ardından `/asama <no>`."

## Kurallar

- CLAUDE.md'deki kesin kurallar her adımda geçerlidir (klasör sınırı, içerik etiği, kanonik metin, lisans kapısı).
- Geri dönüşü zor işlem (push, EAS derlemesi ve güncellemesi, veritabanı birimini silmek) yalnız kullanıcının açık onayıyla yapılır; `eas submit` hiç çalıştırılmaz.
- Kullanıcı "onaysız devam" demedikçe her plan değişikliğinde onay al.
