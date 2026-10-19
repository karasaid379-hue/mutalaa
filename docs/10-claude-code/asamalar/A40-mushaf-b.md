# A40 · Mushaf B (Türk hattı; lisans gelince)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-07](../../00-ozet/02-karar-defteri.md#k-07--mushaf-görünümü-üç-seçenek) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-05](../../00-ozet/02-karar-defteri.md#k-05--risale-i-nur-ve-lisansı-bekleyen-içerik) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması)
> **Faz:** 6 · Takvime bağlı · **Önkoşul:** [A24](./A24-okuyucu-mushaf-c.md) ve lisans (A40.1'deki koşullar) · **İnsan adımı:** lisans (S-04, Türk hattı) · İ-03 (iznin kapsamı) · İ-19 (Kurul, public için)
> **Ajanlar:** `mobil-gelistirici` · `lisans-denetcisi` · `hat-gelistirici` · `sunucu-gelistirici` · `test-yazari` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `mobil-ekran` · `lisans-kapisi` · `paket-yayini` · `icerik-hatti` · **Tahmini oturum:** lisanstan sonra 4–6
> **Başlat:** `/asama A40`

## Amaç
Türk hattı sayfa görselleri ve sayfa başına âyet koordinatlarıyla (`ayah_box`) Mushaf B açılır: âyet vurgusu ve âyet seçimi vardır, kelime seçimi yoktur (K-07). **Bu aşama bugün kilitlidir:** lisans defterinde `mushaf-b-*` kaynakları `kapali` durumundadır ve `kapali` kaynağın ham verisi hatta alınmaz. A40.1'deki beş koşulun hepsi kanıtla sağlanmadan hiçbir adım başlamaz ve ilerleme tablosunda aşama `engelli` kalır. Kilit açılınca aşama hattan pakete, paketten mobil Mod B'ye ilerler; `public` için ayrıca Kurul onayı gerekir.

## Okunacak belgeler
- [Mobil mimari](../../06-mobil/01-mobil-mimari.md): §7 tablo ve ortak sözleşme, §7.2 Mod B, §7.4 eksik paket, §9 bellek, §10 bayraklar, §13, §15 MM-7
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1 `mushaf-b`, §3.5, §6 içerik özeti · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §3 `kurul_gerekli` varsayılanı, §8 `review`, §9.1 `page_map` ve `ayah_box`
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §1 iç kullanım kuralı, §2 `mushaf-b-*`, §3.8, §7 yeni kaynak kontrol listesi
- [Sonra yapılacaklar](../../08-yol-haritasi/02-sonra-yapilacaklar.md): S-04 · [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §7.1
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §2, §3 Mod B seçimi, §5, §10 vurgu, §13 · [Çapa şeması](../../03-veri/01-capa-semasi.md): §10 Mod B eşleme birimi
- [Tasarım sistemi](../../01-urun/04-tasarim-sistemi.md): §2.5 Mod B Gece denetimi, §12 TS-6 · [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §8 yeni kaynak

## Kapsam
**Yapılır**
- Kilit denetimi; görsel biçimi, paket bölünmesi ve veri kaynağı kararları.
- Kaynak kaydı, görsel bağdaştırıcısı, Türk düzeni `page_map`, `ayah_box` ve QA kuralları.
- `mushaf-b` paketinin yazımı ve `dev` yayını; mobil Mod B; Kurul treni ve yayın hazırlığı.

**Yapılmaz**
- Lisans görüşmesi ve kaynak seçimi (S-04; insan). Lisans durumunun değiştirilmesi ([A39](./A39-takvim-ve-lisans-olaylari.md) yordamı).
- Görselden metin okumak: Mod B'nin metin katmanı Tanzil'den çapayla gelir; görsel OCR edilmez.
- Kelime seçimi ve kelime kartı (Mod B'de yok; "Kelimeler" düğmesi âyeti Âyet âyet biçiminde açar). Mağaza sürümü ([A34](./A34-magaza-yayini.md) yordamı).

## Adımlar
### A40.1 · Kilit denetimi (her oturumun ilk işi)
`lisans-denetcisi` şu maddeleri denetler. Biri eksikse aşama durur; ilerleme tablosunda `engelli` ve eksik madde yazılır; kullanıcıya bekleyen insan adımı söylenir.
1. Lisans defterinde `mushaf-b-{kimlik}` kaynak kaydı ve kartı var; durum A39 yordamıyla, ikinci onayla `serbest` (mağaza dahil) ya da en az `ic_kullanim` (yalnız `dev`).
2. Dayanak yazılı: hak sahibinin yazılı izni ya da telifsiz bir Osmanlı mushafı (hattatın ölüm tarihi ve FSEK hesabı kaynaklı; S-04'te örnekler Kayışzâde ve Hasan Rıza Efendi); tarama bir kütüphaneden geliyorsa kütüphanenin kullanım şartı okunmuş.
3. Tarihli lisans kopyası `pipeline/sources/licenses/mushaf-b-{kimlik}-{YYYY-MM-DD}.txt` ve SHA-256'sı TOML'da.
4. İznin şu kullanımları kapsadığı avukatla teyit edilmiş (İ-03): uygulamada gösterim ve paket olarak indirme; tema için boyama ya da ters çevirme (Mobil mimari §7.2); yakınlaştırma; `ayah_box` koordinat verisinin üretimi ve dağıtımı; `public` hedefleniyorsa mağaza dağıtımı.
5. `ayah_box` verisinin kaynağı belli: izinle gelen veri ya da kendi işaretlememiz; S-04'teki 10 sayfalık prototiple emek ölçülmüş.
- **Bitti sayılır:** beş madde de kayıtlı kanıtla sağlanıyor; değilse eksik liste kullanıcıya gösterildi ve aşama `engelli` olarak durdu.

### A40.2 · Kararlar
- `arastirmaci`: React Native'de görsel renk ters çevirme (`filter`) desteği ve expo-image `tintColor` davranışı (Mobil mimari §7.2 "Doğrulanacak").
- `/karar`: görsel biçimi (saydam zeminli mürekkep maskesi ve `tintColor` ya da ters çevirme; MM-7, TS-6); paket bölünmesi (tek `mushaf-b` ya da cüzlere bölünme; İçerik paketleri §3.5 Açık soru); Türk düzeni `page_map` kaynağı; `ayah_box` üretim yöntemi ve işaretleme aracı.
- **Bitti sayılır:** kararlar defterde; İçerik paketleri §3.5 ve Mobil mimari MM-7 `/belge-esitle` ile güncel.

### A40.3 · Hat: kaynak, `page_map`, `ayah_box`
- `pipeline/sources/mushaf-b-{kimlik}.toml` (`tur = "mushaf_gorseli"`, `kurul_gerekli = true`); görseller için yeni bağdaştırıcı (İçerik hattı §8); `uv run mutalaa sources check`.
- `page_map` (Türk düzeni): sayfa başına âyet aralığı. Âyet berkenar düzeninde her sayfanın tam âyetle başlayıp tam âyetle bittiği veriyle denetlenir (Çapa şeması §10).
- `ayah_box`: âyetin satır başına kutuları (`seq`), görsel piksel uzayında. Koordinatlar işaretleme aracından ya da izinli veriden gelir; Claude Code koordinat uydurmaz. Kutular editörde `hedef_tablo = 'ayah_box'` kuyruğuyla onaylanır.
- QA (`pipeline/src/mutalaa_pipeline/qa/checks/mushaf_b.py`, öneri): 6.236 âyetin her biri en az bir kutuda; kutular görsel sınırları içinde; `seq` kesintisiz; bir sayfanın kutuları o sayfanın `page_map` aralığındaki âyetleri kapsıyor; her görselin sha256'sı kayıtlı.
- **Bitti sayılır:** `qa run` 0 ile çıkıyor; `export pg` sonrası satır sayıları raporda.

### A40.4 · `mushaf-b` paketi
- `sunucu-gelistirici`: Yayınlayıcı paketi İçerik paketleri §3.5'e göre yazar: `page_image(page, format, width, height, data, sha256)`, `ayah_box(page, anchor, seq, x, y, w, h)`, `page_map` (Türk düzeni); her pakette olduğu gibi `pack_meta`, `pack_source`, `attribution`. İçerik özeti görsel dosyalarının yol ve sha256 satırlarıyla hesaplanır (§6).
- `publish --flavor dev` ve `verify --flavor dev`. Paket ATTACH edilmez; kendi salt okunur bağlantısıyla açılır.
- **Bitti sayılır:** `dev` manifestinde `mushaf-b` var ve `kurul_gerekli: true` taşıyor; `verify` 0.

### A40.5 · Mobil Mod B
- `mobil-gelistirici` + `mobil-ekran`: `src/features/reader/mushaf-b/` içinde `MushafImagePage` (Mobil mimari §7.2): expo-image ve A40.2'deki tema yolu; etkin âyetin kutuları zemin tonu ve alt kenar çizgisiyle; dokunuş âyeti seçer, "Seç" âyet aralığı kurar; kelime aralığına yapılmış vurgular kutu kenarında işaretle görünür; sesli takipte kutu vurgusu; meal dokunuşunda kutu tonu; kıstırma yakınlaştırması kutu katmanını aynı dönüşümle büyütür; aynı anda en çok üç çözülmüş sayfa.
- Erişilebilirlik: görsel ekran okuyucudan gizli; her âyet Türkçe etiket ve Arapça Unicode metinli tek öğe.
- `src/lib/flags.ts` `mushafB: 'paket'`: paket derlemede görünmüyorsa Mod B ayarlarda ve tanıtımda listelenmez (§7.4).
- Görsel denetim: `adb exec-out screencap -p > .tmp/mushaf-b-<tema>.png` (Kâğıt, Âhar, Gece); Gece'de boyanan sayfaların okunurluğu elle denetlenir; `arayuz-denetcisi` inceler.
- **Bitti sayılır:** isabet, ölçek ve görünürlük birim testleri yeşil; üç temada ekran görüntüleri incelendi.

### A40.6 · Kurul ve yayın
- `public` için onay treni (A39.3; İ-19): başvuruya görseller ve `ayah_box` girer; onay `source` alanlarına ikinci onayla yazılır.
- `internal` ve `public` yalnız `serbest` ve gerekiyorsa onaylı içerik görür. Mod B kodunu taşıyan uygulama sürümü mağazaya A34 yordamıyla çıkar.
- **Bitti sayılır:** `public` kuru çalıştırmasında `mushaf-b` P-04'ten geçiyor ya da Kurul gerekçesiyle "girmedi" ve bu durum kayıtta.

## Kabul ölçütleri
- [ ] A40.1'in beş maddesi kanıtla kayıtlı: lisans defteri satırı, lisans kopyasının SHA-256'sı, ikinci onaylı `review` satırı, avukat teyidi, `ayah_box` kaynağı.
- [ ] `uv run mutalaa sources check` ve `qa run --source mushaf-b-{kimlik}` 0 ile çıkıyor.
- [ ] `ayah_box` içinde farklı âyet sayısı 6.236 (SQL).
- [ ] `publish --flavor dev` ve `verify --flavor dev` 0; `dev` manifestinde `mushaf-b` `kurul_gerekli: true` taşıyor.
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil: isabet testi, ölçek dönüşümü, `isPackVisible` ile `internal` ve `public` derlemede onaysız paketin gizlenmesi.
- [ ] Kâğıt, Âhar ve Gece ekran görüntüleri incelendi; `arayuz-denetcisi` bulguları kapalı.
- [ ] VoiceOver ve TalkBack ile Fâtiha ve Bakara 255 Mod B'de okunuyor (B-10; elle, kayıtta).
- [ ] `public` kapı raporunda `mushaf-b` P-04'ten geçti ya da gerekçesiyle dışarıda.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources check); echo "çıkış: $?"
(cd pipeline && uv run mutalaa qa run --source "mushaf-b-<kimlik>"); echo "çıkış: $?"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(DISTINCT anchor) FROM icerik.ayah_box WHERE source_id = 'mushaf-b-<kimlik>';"   # 6236
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT hedef_anahtar, inceleyen, ikinci_inceleyen FROM icerik.review WHERE hedef_tablo = 'source' AND alan = 'license_status' AND hedef_anahtar LIKE 'mushaf-b-%';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run
pnpm --filter @mutalaa/mobile test
adb exec-out screencap -p > .tmp/mushaf-b-gece.png
```
`<kimlik>` A40.1'deki kaynak kimliğidir. `-U` ve `-d` değerleri `.env.example` varsayılanlarıdır.

## Dikkat
- Kilit kesindir: `kapali` iken görsel indirilmez, taranmaz, hatta alınmaz ve yapay zekâ servisine gönderilmez. Modern mushafların hattı ve tezhibi FSEK m. 4 ile korunur. Ayrıntı: `lisans-kapisi`.
- `mushaf-b-*` lisans gelene kadar `kapali`dır (lisans defteri §2; Kapsam ve fazlar §3 de aynı değeri taşır).
- Kur'an metni görselden okunmaz; kopyalama, arama ve ekran okuyucu Tanzil Unicode metnini kullanır.
- Mod B âyet çapası kullanır; kullanıcı vurguları ve notlar modlar arasında kopmaz (K-07). Renk tek başına anlam taşımaz.
- Görsel biçimi ve paket bölünmesi kararı verilmeden paket üretilmez. Kurul onayı olmadan `public` yoktur. Hukuki görüş değildir.

## İnsan adımları
- Türk hattı lisansı (S-04): aday kaynak listesi, yazılı talepler (taslak `docs/yazismalar/` biçimiyle), izin belgesi; A40.1'den önce.
- İ-03 · İznin kapsamının avukatla teyidi: A40.1 madde 4.
- İ-19 · Kurul onayı: A40.6.
- `ayah_box` işaretlemesi ve onayı (kendi işaretlememizse), ekran okuyucu denetimi: insan. İsteğe bağlı kullanıcı araştırması (AS-07) öncelik kararı içindir.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/sources/mushaf-b-{kimlik}.toml`, `pipeline/sources/licenses/…`, görsel bağdaştırıcısı, `qa/checks/mushaf_b.py` (öneri)
- Editoryal veritabanında `page_map` (Türk düzeni) ve `ayah_box` satırları
- Yayınlayıcıda `mushaf-b` paket yazıcısı ve testleri; `dev` manifestinde `mushaf-b`
- `apps/mobile/src/features/reader/mushaf-b/`, bayrak ve görünürlük testleri
- Karar defteri girdileri (MM-7, paket bölünmesi, `ayah_box` yöntemi)

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A40-mushaf-b.md dosyasındaki aşamayı yürüt. Önce A40.1 kilit denetimini yap; kilit açık değilse dur ve eksik maddeleri listele. Kilit açıksa önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A39](./A39-takvim-ve-lisans-olaylari.md) · Sonraki: yok
