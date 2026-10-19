---
name: mobil-ekran
description: >-
  Mütâlaa mobil ekranı ya da bileşeni yazma ve denetleme kontrol listesi; tasarım jetonları, Türkçe
  metin, erişilebilirlik, Arapça sağdan sola, durum ekranları, test kimlikleri, performans bütçesi ve
  Android emülatöründen ekran görüntüsü alarak görsel doğrulama. apps/mobile içinde ekran, bileşen ya
  da etkileşim yazarken veya incelerken kullan.
---

# Mobil ekran kontrol listesi

Kaynaklar: [Mobil ekranlar](../../../docs/01-urun/03-mobil-ekranlar.md), [Okuma deneyimi](../../../docs/01-urun/02-okuma-deneyimi.md), [Tasarım sistemi](../../../docs/01-urun/04-tasarim-sistemi.md), [Mobil mimari](../../../docs/06-mobil/01-mobil-mimari.md) §9 ve §13.

## Yazarken

- **Yer:** rota dosyası `app/` altında yalnız bir özellik bileşenini çağırır; bileşen `src/features/<özellik>/components/` altındadır; dışa açık API `index.ts`.
- **Jeton:** renk, boşluk, köşe, yazı ölçeği yalnız `packages/ui-tokens` üzerinden (NativeWind sınıfları jetonlara bağlı). Sabit renk kodu yok. Altın rengi metin rengi olarak kullanılmaz.
- **Tema:** Kâğıt, Âhar, Gece ve Sistem; her ekran üç temada okunur.
- **Metin:** Türkçe metin i18n dosyasından; arayüzde sabit Türkçe dize yok. Arapça metin `lang="ar"`, sağdan sola; Arapça ve Türkçe yazı boyutu ayrı ayarlanır.
- **Durumlar:** yükleniyor, boş, hata ve çevrimdışı durumları [Mobil ekranlar](../../../docs/01-urun/03-mobil-ekranlar.md) §3.1 kurallarına göre.
- **Erişilebilirlik:** dokunma hedefi en az 44×44 pt; Türkçe `accessibilityLabel`; her kaydırma jestinin görünür düğme karşılığı; alt sayfada görünür Kapat düğmesi; Hareketi Azalt açıkken solma; renk tek başına anlam taşımaz; metin %200 büyür ve kesilmez.
- **Mushaf A:** glif kelimeler ekran okuyucudan gizlidir; her âyet Unicode metin ve "Bakara Sûresi, 255. âyet" gibi etiketle tek öğedir.
- **Test kimliği:** çapa grameriyle: `ayet-q:2:255`, `kelime-q:2:255:3`, `kelime-karti`, `geri-don-cipi`.
- **Sure adı:** her etiket (başlık, konum, çip, duyuru, erişilebilirlik etiketi) adı `core`'daki `sure` tablosundan alır. Tablo boşsa (sure adları İ-23 onayını bekliyor) sayısal biçim kullanılır: "2:255", "2. sûre". Ad elle yazılmaz; ad gerektiren testler `shared/data/sure-adlari.json` yokken atlanır ve ilerleme notuna yazılır.
- **İçerik:** ekranda yalnız paketten gelen kanonik metin; örnek ya da yer tutucu Kur'an, meal, hadis, Risale metni yazılmaz. Geliştirme için açıkça sentetik `test-` fikstürü kullanılır.
- **İlkeler:** liderlik tablosu, sosyal karşılaştırma, kırılan seri uyarısı yok (K-25).

## Test

- Jest (jest-expo) ve React Native Testing Library: davranış, erişilebilirlik etiketi, test kimliği.
- `pnpm --filter @mutalaa/mobile lint`, `typecheck`, `test`.
- Performans bütçesine dokunan ekranlarda (sayfa çevirme, kelime kartı, arama) [Mobil mimari](../../../docs/06-mobil/01-mobil-mimari.md) §9 ölçümünü yap.

## Görsel doğrulama (Android emülatörü)

Komutları Git Bash'te çalıştır (PowerShell 5.1'de `>` ikili dosyayı bozar). Görüntüler yalnız `.tmp/` altına yazılır.

```bash
adb devices                                   # emülatör listede olmalı
adb shell am start -W -a android.intent.action.VIEW -d "mutalaa-dev://q/2/255"
adb exec-out screencap -p > .tmp/ekran-q-2-255.png
```

1. Görüntüyü `Read` aracıyla aç ve incele: hizalama, taşma, kontrast, Arapça yönü, Türkçe karakterler.
2. Büyük yazı: `adb shell settings put system font_scale 2.0`, ekranı yeniden aç, görüntü al; sonra `adb shell settings put system font_scale 1.0`.
3. Gece teması: uygulamanın tema ayarından ya da `adb shell cmd uimode night yes`; bitince `adb shell cmd uimode night no`.
4. Bulguları `arayuz-denetcisi` ajanına ver ya da kendin raporla; görüntü yollarını rapora yaz.

### Dokunma ve yazma

Öğenin yerini ekran görüntüsünden tahmin etme; görünüm ağacından bul:

```bash
adb exec-out "uiautomator dump /dev/tty" > .tmp/ui.xml    # görünüm ağacı; tırnak Git Bash yol çevirisini önler
grep -o '<node[^>]*fihrist-giris[^>]*>' .tmp/ui.xml       # öğenin resource-id ya da content-desc değeri ve bounds
adb shell input tap 540 1210                              # bounds="[x1,y1][x2,y2]" kutusunun orta noktası
adb shell input text "2:255"                              # yalnız ASCII; boşluk için %s
adb shell input keyevent 66                               # Enter
```

- React Native `testID` değeri Android görünüm ağacında `resource-id` olarak görünür (Doğrulanacak); görünmüyorsa `content-desc` içindeki `accessibilityLabel` aranır.
- Koordinat `bounds` değerinden hesaplanır: x = (x1 + x2) / 2, y = (y1 + y2) / 2. Ekran yönü ya da yazı boyutu değişince ağaç yeniden alınır.
- İlk komut boş dönerse iki adımda alınır: `adb shell "uiautomator dump /sdcard/ui.xml"` ve `adb exec-out "cat /sdcard/ui.xml" > .tmp/ui.xml`. `/sdcard/` emülatörün içidir; dosya yalnız `.tmp/` altına alınır.
- `adb shell input text` ASCII dışı karakter gönderemeyebilir; Türkçe ya da Arapça girdi gereken akış Maestro ile sınanır (A33).

Geliştirme derlemesi emülatörde yoksa kullanıcıdan EAS derlemesi için onay iste (`eas build` onay ister; `--non-interactive --no-wait` ile başlatılır, izleme ve indirme A21.7'deki gibi); derlemeyi kendiliğinden başlatma.
