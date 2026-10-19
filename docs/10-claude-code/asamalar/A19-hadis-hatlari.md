# A19 · Hadis hatları (Tecrîd + Naim, Kütüb-i Sitte Arapça)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-04](../../00-ozet/02-karar-defteri.md#k-04--hadis-kaynakları) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu)
> **Faz:** 1 · İçerik hattı · **Önkoşul:** [A10](./A10-tanzil-alimi.md) · [A15](./A15-editor-paneli.md) · **İnsan adımı:** İ-11 (Naim düzeltme turları) · İ-14 · İ-25 (Sunnah.com, fawazahmed0)
> **Ajanlar:** `hat-gelistirici` · `lisans-denetcisi` · `arastirmaci` · `metin-denetcisi` · `test-yazari` · `sunucu-gelistirici` (şema eki gerekirse) · `inceleyici` · **Beceriler:** `icerik-hatti` · `lisans-kapisi` · `capa-gramer` · `metin-butunlugu` · **Tahmini oturum:** 3–4 Claude Code oturumu; insan işleri ayrıca
> **Başlat:** `/asama A19`

## Amaç
K-04 gereği Tecrîd-i Sarîh'in Arapça metni ve Ahmed Naim çevirisi ile Kütüb-i Sitte'nin Arapça metni için hat kurulur: kaynak kayıtları ve kapalı kaynak korumaları, tarama ve OCR, hadis birimleri (`h:{koleksiyon}:{no}`, `ht:naim:tecrid:{no}`), numara eşleme ve konum tabloları, Tecrîd → Buhârî eşlemesi ve hadis atıf ayrıştırıcısı. Kâmil Miras ciltleri 1 Ocak 2028'e kadar hiç işlenmez. Kaynak seçimi ve taramalar insan işidir (İ-14).

## Okunacak belgeler
- [Hadis hazırlığı](../../04-icerik/04-hadis-hazirligi.md): tamamı
- [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §13 hadis atıfları; motor için §3–§6
- [Kaynaklar ve lisans defteri](../../04-icerik/01-kaynaklar-ve-lisans-defteri.md): §2 (`tecrid-*`, `hadis-*`), §3.4, §4, §7, §8 yazışma 6
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §2–§5 (`h`, `ht`, slug kuralları), §13 ÇŞ-3
- [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §4 `unit`, §9.1 `page_map`, §11 `hadith_number_map` ve `hadith_location`
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1 hadis paketleri, §7 süzme
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §4 OCR değerlendirme yöntemi, §5 aktarım kılavuzu (ciltler Osmanlıca harfliyse)
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §8 yeni kaynak ekleme, §10 yapay zekâ politikası

## Kapsam
**Yapılır**
- Kaynak kayıtları ve korumalar: `tecrid-ar`, `tecrid-naim`, `tecrid-miras` (`kapali`), `hadis-fawaz-ar`, `hadis-sunnah-api` (`bekliyor`).
- Numaralandırma kararı; `hadith_number_map`, `hadith_location`.
- Tecrîd tarama kaydı, OCR değerlendirmesi, hadis birimlerine bölme, Naim aktarımı için inceleme kuyruğu.
- Kütüb-i Sitte Arapça kaynak yolu: yazışma taslakları ve yalnız `dev` prototipi.
- Tecrîd → Buhârî eşlemesi, hadis atıf ayrıştırıcısı; `hadis-tecrid` ve `hadis-kutub-i-sitte` paketlerinin `dev` yayını.

**Yapılmaz**
- Kâmil Miras ciltleri: indirilmez, taranmaz, işlenmez (1 Ocak 2028; A39).
- Sıhhat derecesi etiketleri (sonra; yapay zekâ derece atamaz). Hadis okuyucusu (A31).
- Yapay zekâ ile hadis çevirisi (yasak). Risale metnindeki hadis atıfları (İ-03'e bağlı).

## Adımlar
### A19.1 · Kaynak kayıtları ve kapalı korumalar
- Kayıtlar A06'da açıldı. `lisans-denetcisi` her kaynak için lisans defteri §7 kontrol listesini yeniden yürütür ve eksikleri tamamlar (tarama künyesi, tarihli lisans kopyası). `tecrid-miras`: `kapali`, `embed_ok = false`, `kamu_mali_tarihi = 2028-01-01`. Naim'in ciltleri doğrulanana kadar III. cilt Miras kısmı sayılır.
- Cilt → kaynak eşlemesi yapılandırmada durur: Miras cildi için `ingest scans`, `ocr run` ve `anchor` 3 ile çıkar. `hadis-fawaz-ar` ve `hadis-sunnah-api` `embed_ok = false` taşır; yapay zekâ ya da gömme çağrısı 3 ile durur.
- Lisans defteri §4'teki kaynaklar (AhmedBaset/hadith-json, fawazahmed0 Türkçe hadisleri, OpenITI) kaynak kaydı almaz.
- **Bitti sayılır:** `sources check` 0; korumaların testleri yeşil.

### A19.2 · Doğrulamalar ve numaralandırma kararı
- `arastirmaci` doğrular: Sunnah.com geliştirici şartları; fawazahmed0 deposunun metin kaynağı belgeleri; Tecrîd ilk baskı künyesi (`tecrid-ilk-baski`); Tecrîd numarasının ciltler boyunca sürekliliği; atıflardaki numaranın bâb mı hadis mi olduğu; Tecrîd'in Buhârî kitap sırasını izleyip izlemediği.
- Naim'in çevirdiği ciltler (§3 doğrulama listesi) basılı ciltlerden kullanıcıyla doğrulanır (İ-14); Claude Code listeyi tutar ve bulguları lisans defterine işler.
- Numaralandırma (§5: A, B, C, D) proje sahibinin kararıdır; ilk hadis çapası `internal` derlemeye girmeden `/karar` ile yazılır. Alt numaralar (`2564a`, ÇŞ-3) gramerde yoktur; gerekiyorsa aynı kararda ele alınır. Koleksiyon kısa adları Çapa şemasına `/belge-esitle` ile işlenir.
- **Bitti sayılır:** karar defterinde numaralandırma ve koleksiyon adları kararı var.

### A19.3 · Tecrîd tarama, OCR ve birimler
- İ-14 tamamlanmadan başlamaz; yalnız Naim ciltleri işlenir. `uv run mutalaa ingest scans --edition tecrid-ilk-baski --dir <klasör> --cilt <n>`; taramalar proje klasörüne kopyalanır.
- OCR değerlendirmesi Elmalılı yöntemiyle yapılır: tabakalı örneklem, iki kişinin yazdığı altın metin (`data/gold/tecrid-ocr/`), CER. Arapçada temel harf CER'i ile hareke CER'i ayrı ölçülür. Ciltler Osmanlıca harfli çıkarsa Elmalılı §5 aktarım kılavuzu uygulanır. Motor seçimi `/karar` ile.
- `ocr run`, hadis numarası işaretlerinin bulunması, Arapça blok ile Türkçe bloğun eşlenmesi. Birimler: `h:tecrid:{no}` ve `ht:naim:tecrid:{no}`, `ceviri = 'naim'`. Kendi taramamızdan aktarılan metin bizim ürettiğimiz metindir ve ilk kayıtta NFC'ye çevrilir.
- `hadith_location` (kitap › bâb › hadis, `ord`), `hadith_number_map` (sistemler) ve baskı sayfa eşlemesi (`page_map`; `source_id` birimin kaynağıdır, baskı künyesi kaynağın `baski_bilgisi` alanındadır; Hadis hazırlığı §7, Editoryal veritabanı §9.1).
- Naim aktarımı `review` (`hedef_tablo = 'unit'`, `alan = 'metin'`) kuyruğuna düşer; düzeltme ve onay insan işidir. Bekleme noktasında `/asama` aşamayı ilerleme dosyasında `engelli` durumuna alır ve Not sütununa bekleyen işi yazar.
- **Bitti sayılır:** örneklem CER raporu var; birimler G-CAP ve G-BUT'tan geçiyor; `tecrid-miras` birimi 0.

### A19.4 · Kütüb-i Sitte Arapça kaynak yolu
- Önerilen yol §4'tedir: Tecrîd Arapçası kendi taramamızdan; Sunnah.com'a yazılı izin talebi; fawazahmed0 bakımcısına kaynak sorusu ve bir koleksiyonun örnekleminin serbest basılı nüshayla karşılaştırılması; sonuç çıkmazsa kendi sayısallaştırmamız.
- Yazışma taslakları `/yazisma` ile `docs/yazismalar/` altına yazılır; kullanıcı onaylar ve gönderir (İ-14). Beceri listesinde bu muhataplar yoktur; taslak genel yazışma kalıbıyla hazırlanır.
- Prototip: `hadis-fawaz-ar` bağdaştırıcısı (`ingest/hadith_ar.py`), yalnız `dev`. Üçüncü taraf Arapça metin dağıtıldığı hâliyle saklanır, NFC uygulanmaz; metin yapay zekâya gönderilmez ve gömülmez.
- **Bitti sayılır:** taslaklar `docs/yazismalar/` altında; prototip birimleri yalnız `bekliyor` kaynakla yüklü.

### A19.5 · Tecrîd → Buhârî eşlemesi ve atıf ayrıştırıcısı
- `uv run mutalaa enrich hadith-map --from tecrid --to buhari`: §6 adımları (basılı gösterge, normalize edilmiş 3–4 gram ve Smith-Waterman hizalaması, kapsama, sıra kısıtı, tekrarlarda birincil ve ikincil aday). Sonuç `xref`: `type = 'atif'`, `origin = 'hat'`, `status = 'aday'`, `evidence = {"iliski": "muhtasar-asli", "kapsama": …, "yontem": "hizalama"}`. Ayrı bir `xref.type` (ör. `paralel`) Açık sorudur. Buhârî tarafı A19.4'teki kaynağa bağlıdır.
- Altın set: ciltlere göre tabakalı 200 Tecrîd hadisi elle eşlenir (İ-13 kapsamında atıf etiketlemesi). Öneri eşiği: birincil eşlemede kesinlik ≥ 0,98; altına düşerse bütün eşlemeler tek tek onaylanır.
- Hadis atıf ayrıştırıcısı (İktibas tespiti §13 ve Hadis hazırlığı §9): "Buhârî, Îmân 12" biçimleri, kitap adı eşleme tablosu, numaranın iki yorumu, çözülemeyen atıf `evidence.unresolved = true`. Koleksiyon adı tablosu (`collection_alias`) editoryal DDL'de yoktur; yeri `/karar` ile belirlenir (gerekirse `sunucu-gelistirici` EF göçü). Ayrıştırıcı sentetik örneklerle sınanır; Elmalılı tefsiri üzerinde koşu A37'dedir (`uv run mutalaa enrich hadith-refs --target elmalili-tefsir`).
- **Bitti sayılır:** eşleme ve ayrıştırıcı testleri yeşil; altın set etiketlendiyse kesinlik raporu var.

### A19.6 · Paketler ve yayın
- `hadis-tecrid` (`h:tecrid` ve `ht:naim`; `ht:miras` 2028'den önce yok) ve `hadis-kutub-i-sitte` paketleri `publish --flavor dev` ile yayımlanır. Genel metin paketi tanımı A13'tedir; eksik varsa `sunucu-gelistirici` ekler.
- `bekliyor` kaynaktan gelen içerik `internal` ve `public`'e girmez. Derece etiketi gösterilmez; Sünen koleksiyonlarının gösterimi Açık sorudur (§8).
- **Bitti sayılır:** `dev` manifestinde hadis paketleri var; `internal` kuru çalıştırmasında `bekliyor` kaynaklı içerik yok.

## Kabul ölçütleri
- [ ] `tecrid-miras` için `ingest scans`, `ocr run` ve `anchor` 3 ile çıkıyor; `embed_ok = false` kaynakla yapay zekâ çağrısı 3 ile duruyor (testler).
- [ ] PostgreSQL'de `tecrid-miras` kaynaklı birim 0.
- [ ] Numaralandırma, koleksiyon adları, OCR motoru ve `collection_alias` kararları karar defterinde.
- [ ] Tecrîd OCR örnekleminde temel harf ve hareke CER'leri ayrı raporlanmış.
- [ ] `h:tecrid` ve `ht:naim:tecrid` birimleri G-CAP ve G-BUT'tan geçiyor; kendi aktarımımız NFC, üçüncü taraf metni NFC uygulanmamış (`metin-denetcisi`).
- [ ] Sunnah.com ve fawazahmed0 yazışma taslakları `docs/yazismalar/` altında.
- [ ] Tecrîd → Buhârî eşlemesi ve atıf ayrıştırıcısı testleri yeşil; eşleme satırları `aday`.
- [ ] `dev` manifestinde hadis paketleri; `internal` kuru çalıştırma raporunda `bekliyor` kaynaklı paket yok.

## Doğrulama
```bash
(cd pipeline && uv run mutalaa sources list && uv run mutalaa sources check)
(cd pipeline && uv run pytest && uv run ruff check .)
(cd pipeline && uv run mutalaa ocr eval --edition tecrid-ilk-baski --gold data/gold/tecrid-ocr/)
(cd pipeline && uv run mutalaa qa run --source tecrid-naim)
(cd pipeline && uv run mutalaa enrich hadith-map --from tecrid --to buhari --dry-run)
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT source_id, kind, count(*) FROM icerik.unit WHERE kind IN ('hadis', 'hadis_ceviri') GROUP BY 1, 2;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'tecrid-miras';"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev
dotnet run --project server/Mutalaa.Publisher -- publish --flavor internal --dry-run
```

## Dikkat
- Hadis metni hafızadan yazılmaz, tamamlanmaz, düzeltilmez. Yapay zekâ hadis çevirmez ve derece atamaz (K-25); OCR'da yalnız görsel okuma yapar.
- Miras ciltleri ve sonraki baskılardaki sadeleştirme ve editoryal ekler kullanılmaz; modern dipnot ve fihristler kopyalanmaz.
- Üçüncü taraf Arapça metin dağıtıldığı hâliyle saklanır; kendi aktarımımız ilk kayıtta NFC'dir (K-26).
- Hadis çapası bir kez verilir ve yeniden numaralanmaz; numaralandırma kararı bu yüzden ilk `internal` derlemeden önce verilir.
- `bekliyor` kaynaklı içerik yalnız `dev`'de görünür; `kapali` içerik hiçbir adımda okunmaz.
- Günlüklere metin yazılmaz.

## İnsan adımları
- İ-14 · Hadis kaynak seçimi ve Naim tercümesinin taranması: A19.3 ve A19.4'ten önce gerekir; ciltlerin künye ve mütercim doğrulaması da bu adımdadır.
- Tecrîd OCR altın örneklemi İ-10 ile aynı türden iştir; Tecrîd → Buhârî altın seti İ-13 kapsamındadır.
- İ-11 · Naim aktarımının düzeltme turları ve onayı: bekleme noktası olarak ilerleme dosyasına yazılır ([İnsan adımları](../06-insan-adimlari.md)).
- İ-25 · Sunnah.com izin talebi ve fawazahmed0 kaynak sorusu: taslaklar `/yazisma sunnah` ve `/yazisma fawaz` ile hazırlanır; gönderim kullanıcıdadır.

## Çıktılar
- `pipeline/sources/tecrid-*.toml`, `hadis-*.toml` ve lisans kopyaları; cilt → kaynak eşlemesi
- `pipeline/src/mutalaa_pipeline/ingest/hadith_ar.py`, `anchor/hadith.py`, `enrich/hadith_map.py`, `enrich/hadith_refs.py`, testler
- PostgreSQL'de hadis birimleri, `hadith_number_map`, `hadith_location`, `page_map`, `xref` adayları, `review` kayıtları
- `docs/yazismalar/` altında taslaklar; karar defterinde numaralandırma ve diğer kararlar; `dev` kanalında hadis paketleri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A19-hadis-hatlari.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A18](./A18-baglantilar-ve-altin-setler.md) · Sonraki: [A20](./A20-risale-altyapisi.md)
