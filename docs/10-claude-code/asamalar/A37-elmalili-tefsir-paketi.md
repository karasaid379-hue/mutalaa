# A37 · Elmalılı tefsir paketi (`tefsir-elmalili`)

> **Sürüm:** 1.1 · **Tarih:** 27 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-03](../../00-ozet/02-karar-defteri.md#k-03--tefsir-önce-elmalılı-meali) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-27](../../00-ozet/02-karar-defteri.md#k-27--tek-bağlantı-tablosu) · [K-06](../../00-ozet/02-karar-defteri.md#k-06--yayın-kapısı) · [K-25](../../00-ozet/02-karar-defteri.md#k-25--i̇lkeler) · [K-38](../../00-ozet/02-karar-defteri.md#k-38--kaynak-edinimi-dijital-öncelikli-kanıtla-yükseltme)
> **Faz:** 4 · v1.x · **Önkoşul:** [A16](./A16-elmalili-meali.md) · [A18](./A18-baglantilar-ve-altin-setler.md) · **İnsan adımı:** İ-11 (tefsir düzeltme turları) · İ-17 (görsel OCR bütçesi)
> **Ajanlar:** `hat-gelistirici` · `metin-denetcisi` · `test-yazari` · `sunucu-gelistirici` · `mobil-gelistirici` · `lisans-denetcisi` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `icerik-hatti` · `metin-butunlugu` · `capa-gramer` · `paket-yayini` · `mobil-ekran` · **Tahmini oturum:** 6+ (insan düzeltme süresine bağlı)
> **Başlat:** `/asama A37`

## Amaç
*Hak Dini Kur'an Dili*'nin tefsir paragrafları ve haşiyeleri özgün baskıdan, A16'nın OCR, aktarım ve düzeltme araçlarıyla `tf:elmalili:…` çapalarına alınır, iki düzeltme turundan geçer ve `tefsir-elmalili` paketi olarak yayımlanır. v1'de yazılan tefsir görünümü gerçek pakete bağlanır. Tefsirin Kurul kapsamı Açık soru'dur; cevap gelene kadar paket ihtiyatla `kurul_gerekli` taşır ve `internal` ile `public` derlemede görünmez.

## Okunacak belgeler
- [Elmalılı hazırlığı](../../04-icerik/03-elmalili-hazirligi.md): §1, §4 OCR ve hazır metin ölçümü, §5 Yol B kuralı, §6 sınır durumları, §7 editör, §8 QA ve örneklem, §9 atıf, §10 tefsir metni
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §1, §2 kural 4, §3 `tf` deseni, §4, §5 haşiye adlandırması, §6 kararlılık, §7 kanonik metin, §10 baskı sayfaları, §13 ÇŞ-4
- [İçerik hattı](../../04-icerik/02-icerik-hatti.md): §4 komutlar, §6 idempotentlik, §9 QA kapıları, §10 yapay zekâ politikası, §11 maliyet
- [İçerik paketleri](../../03-veri/03-icerik-paketleri.md): §1, §3.2, §4 · [Arama](../../03-veri/05-arama-fts5.md): §2 paket tabloları, §5
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §2, §3 yapısal bağlantılar · [İktibas tespiti](../../05-capraz-referans/02-iktibas-tespiti.md): §1, §2
- [Okuma deneyimi](../../01-urun/02-okuma-deneyimi.md): §6 tefsir görünümü, §8 Bağlantılar paneli
- [Yayın kapısı ve Kurul](../../07-yayin/01-yayin-kapisi-ve-kurul.md): §7.1, §7.5 soru 5 · [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §4 altın setler

## Kapsam
**Yapılır**
- Tefsir çapası, haşiye ve sure girişi kararları; yeni çapa vektörleri.
- OCR ve aktarım (A16 araçları), `anchor/tefsir.py`, sayfa eşlemesi, `export pg`.
- Düzeltme turları ve QA kapıları; iktibas, atıf ve hadis atfı adayları; altın sete tefsir örneklemi.
- `tefsir-elmalili` paketinin `dev` yayını ve tefsir görünümünün, Kütüphane'nin, aramanın ve Bağlantılar panelinin bu pakete bağlanması.

**Yapılmaz**
- Meal (A16), kelime katmanı (A17), altın set araçları ve eşik altyapısı (A18; burada yalnız tefsir örneklemi eklenir).
- Tefsir görünümünün ilk kodu (A24'te sentetik `test-` fikstürüyle yazıldı, ör. `test-tefsir-ornek`).
- `public` yayın: Kurul cevabı ve kararı gelince [A39](./A39-takvim-ve-lisans-olaylari.md) yordamı ve A34 sürüm yordamıyla. Diğer tefsirler (S-09).

## Adımlar
### A37.1 · Çapa, kapsam ve Kurul kararları
- Âyete bağlı bölüm `tf:elmalili:{sure}-{ilk}-{son}:p{n}`; aralık `ayet_ar` bloğundan gelir, iki uç her zaman yazılır, aralık sure sınırını geçmez (kaynak geçerse hat bölümü ikiye ayırır). Âyete bağlı olmayan bölüm `tf:elmalili:{bolum}:p{n}` (`mukaddime`; sure girişi önerisi `sure-{n}-giris`).
- Haşiye modeli (ÇŞ-4 açık). Öneri: haşiye aynı bölümde ayrı paragraf birimidir (`role = 'hasiye'`, bölümde kullanılmamış sıradaki `p{n}`); ana paragrafın `marks` alanı `{"t":"hasiye","a":"tf:…"}` ile ona bağlanır; gramer değişmez. Dipnotlar meal kuralıyla `attrs.dipnotlar` içinde, yarı açık `@{başlangıç}-{bitiş}` adresiyle.
- `p{n}` kimliktir, okuma sırası `unit.ord`'dadır; bölünme ve birleşme Çapa şeması §6'daki yönlendirmeyle yapılır. Çapalar ilk `internal` yayından önce donar.
- Öncelik sırası (ör. önce sık okunan sureler) ve kısmi yayın proje sahibince belirlenir.
- Kurul: `elmalili-tefsir` için `kurul_gerekli = true` (ihtiyatlı öneri); Kurul "gerekmez" derse değer A39 yordamıyla ve ikinci onayla değişir. Soru `/yazisma kurul` ile taslaklanır (İ-02 kanalı).
- `lisans-denetcisi`: P-04 kuralı kesindir: onaysız `kurul_gerekli` paket kapı raporunda "girmedi" olur ve `public` derlemeyi durdurur (çıkış `2`; Backend API §10.3, Yayın kapısı §4). Bu yüzden onay gelene kadar `tefsir-elmalili` `public` yayının paket listesine alınmaz (öneri: `publish --flavor public --pack …`); yoksa `core`'un public yayınları da durur. Denetçi `public` kuru çalıştırmasında P-04 gerekçesini ve `2` çıkış kodunu görür.
- Kararlar `/karar` ile deftere; yeni çapa örnekleri `test-vektoru` ile `shared/test-vectors/anchors/valid.jsonl` ve `invalid.jsonl` dosyalarına eklenir.
- **Bitti sayılır:** kararlar defterde; yeni vektörler TypeScript, C# ve Python'da yeşil.

### A37.2 · OCR ve aktarım
- Metin yolu (K-38): tefsir için hazır metin adayı archive.org metin katmanıdır; kalitesi bilinmiyor. Aday A09'da `bekliyor` olarak kaydedilir ve tefsir düzyazısı örneğinde aynı ölçümle (CER, sadeleştirme izi) sınanır. Aday eşiği geçerse ve A16 hazır metin dalındaki kalıcı içe aktarım araçları (planlı; `ingest register`, okuyucular, çıkarılmış metin vektörü) varsa tefsir metni bu yoldan `taslak` olarak alınır ve özgün baskı görseliyle karşılaştırılır; geçmezse aşağıdaki OCR yolu aynen sürer. Karar A37 başında A09 raporuna ve gerekirse tefsir için yenilenen küçük bir ölçüme bakılarak verilir.
- Taramalar A16'dakiyle aynıdır (baskı `elmalili-1935`). A16'nın OCR çıktısında `tefsir`, `dipnot` ve `baslik` bölgeleri varsa yeniden OCR yapılmaz (parmak izi aynıysa adım atlanır). Yoksa A09'da seçilen motorla: `uv run mutalaa ocr run --edition elmalili-1935 --engine <seçilen> --pages <aralık>`. Görsel model kullanılacaksa önce `uv run mutalaa llm estimate` ile maliyet ölçülür ve bütçe onaylanır (İ-17).
- A09'da seçilen yol uygulanır. Yol B (Latin harfli baskı): metin baskıdaki imlâyla aynen alınır; açık dizgi hataları metinde değil ayrı "tashih" katmanında tutulur. Yol A ise Elmalılı hazırlığı §5'teki aktarım kılavuzu ve `elmalili_imla.tsv` sözlüğü kullanılır. Arapça alıntılar Arapça harfle ve baskıdaki harekeyle kalır, `lang="ar"` aralığı olarak işaretlenir.
- `pipeline/src/mutalaa_pipeline/anchor/tefsir.py`: bölgeleri bölümlere ve paragraflara böler, çapa verir; kendi ürettiğimiz metin olduğu için ilk kayıtta NFC uygular ve `content_hash` hesaplar; `attrs` cilt, sayfa ve bölge kutusunu taşır. Baskı sayfa eşlemesi meal ile aynı biçimde `page_map`'e yazılır (c. ve s. atfı için).
- `uv run mutalaa anchor --source elmalili-tefsir`, `qa run --source elmalili-tefsir`, `export pg --source elmalili-tefsir --dry-run`, sonra `export pg`. Birimler `metin_durumu = 'taslak'` girer.
- **Bitti sayılır:** `qa run` G-LIS, G-BUT, G-CAP ve G-HIZ (tefsir aralıkları âyet sınırında) kapılarını geçiyor; kuru yükleme raporu incelendi.

### A37.3 · Düzeltme turları ve nitelik (İ-11)
- Editör panelindeki OCR ve metin kuyruğu (A15, A16) tefsir birimleriyle çalışır: dört göz; tefsir metni ikinci onay gerektirir (`inceleyen` ve `ikinci_inceleyen` farklı editör).
- Claude Code tefsir metnini hafızadan yazmaz, tamamlamaz, "düzeltmez". Yalnız inceleme adayı üretir: imlâ sözlüğü çakışmaları, `⟦?⟧` işaretleri, Arapça alıntının Tanzil hizalamasında çıkan farkı. Karar görsele bakan insanındır; alıntı Tanzil metniyle değiştirilmez.
- G-MET (CER eşiği, imlâ tutarlılığı, `⟦?⟧` = 0), G-INC (ikinci okuma örneklemi; hata yoksa %95 üst sınır ≈ 3/n, öneri en az 600 birim) ve sadeleştirme denetimi (0) uygulanır.
- **Bitti sayılır:** yayın kapsamındaki bütün birimler `onayli`; `⟦?⟧` sayısı 0; QA raporu `data/reports/` altında.

### A37.4 · Bağlantılar
- `uv run mutalaa enrich citations --target elmalili-tefsir` (açık atıf ve iktibas) ve `uv run mutalaa enrich hadith-refs --target elmalili-tefsir`. Satırlar `aday` girer ve editörde onaylanır.
- Âyet ↔ tefsir aralığı ilişkisi çapadan türetilir; `xref`'e yazılmaz (K-27).
- Atıf ve iktibas altın setine Elmalılı tefsir örneklemi eklenir (Test stratejisi §4). Eşik tutmazsa o türün `aday` satırları pakete girmez. Rapor `data/reports/{data_version}.json`.
- **Bitti sayılır:** değerlendirme raporu "geçti"; onaylı bağlantılar veritabanında.

### A37.5 · Paket ve mobil bağlama
- `dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev`: paket `unit`, `unit_search`, `unit_fts`, `unit_tri`, `tr_stem_lex`, `xref_idx`, `page_map`, `pack_meta`, `pack_source`, `attribution` taşır; `depends_on: ["core"]`; öz denetimde kapsamdaki bir âyeti kapsayan paragraf sorgusu ve bir FTS sorgusu sonuç verir. QAC'ye bağlı `tr_root_index` satırları QAC `bekliyor` kaldıkça yalnız `dev` paketine girer (P-05; İçerik paketleri §7). Ardından `verify --flavor dev`.
- `mobil-gelistirici` + `mobil-ekran`: tefsir görünümü `p_tefsir_elmalili` şemasından okur (küresel âyet sırası `ayah_first`, `ayah_last`); "Takip et", başlık ve âyet çipleri; "Paket yok · İndir (boyut)" ve "Tefsir hazırlanıyor" durumları; Kütüphane içindekiler (sureler, mukaddime); Ara'da "Tefsir" kapsamı; Bağlantılar panelinde Tefsir grubu; tefsirdeki Arapça alıntıda iktibas kartı; `mutalaa-dev://tf/elmalili/2-255-257/p3` derin bağlantısı. Kısmi yayında kapsanmayan âyetin mesajı öneri olarak kayda yazılır.
- Görsel denetim: `adb exec-out screencap -p > .tmp/tefsir.png` (Kâğıt, Gece, %200); `arayuz-denetcisi` inceler.
- **Bitti sayılır:** `dev` manifestinde `tefsir-elmalili` var; mobil testler yeşil; `public` kuru çalıştırmasında paket P-04 gerekçesiyle dışarıda.

## Kabul ölçütleri
- [ ] Çapa vektörleri yeni tefsir örnekleriyle üç dilde yeşil.
- [ ] `uv run mutalaa qa run --source elmalili-tefsir` 0 ile çıkıyor.
- [ ] Kapsamdaki birimlerde `onayli` olmayan ya da `⟦?⟧` içeren satır sayısı 0 (SQL).
- [ ] Âyete bağlı tefsir birimlerinde `ayah_range` boş satır sayısı 0 (SQL).
- [ ] Onaylanmış tefsir metin incelemelerinde `ikinci_inceleyen` boş ya da `inceleyen` ile aynı satır sayısı 0 (SQL).
- [ ] Altın set raporunda tefsir örneklemi "geçti".
- [ ] `publish --flavor dev` ve `verify --flavor dev` 0 ile çıkıyor; `dev` manifestinde `tefsir-elmalili` `depends_on` olarak `core` taşıyor.
- [ ] `public` kuru çalıştırmasının kapı raporunda `tefsir-elmalili` P-04 gerekçesiyle "girmedi", `core` "girdi" (gözle).
- [ ] `pnpm --filter @mutalaa/mobile test` yeşil; ekran görüntüleri incelendi, `arayuz-denetcisi` bulguları kapalı.
- [ ] `metin-denetcisi` raporunda kanonik metne izinsiz dönüşüm yok.

## Doğrulama
```bash
pnpm --filter @mutalaa/anchors test && dotnet test --solution server/Mutalaa.slnx && (cd pipeline && uv run pytest && uv run ruff check .)
(cd pipeline && uv run mutalaa qa run --source elmalili-tefsir); echo "çıkış: $?"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'elmalili-tefsir' AND (metin_durumu <> 'onayli' OR strpos(metin, chr(10214) || '?' || chr(10215)) > 0);"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.unit WHERE source_id = 'elmalili-tefsir' AND anchor ~ '^tf:elmalili:[0-9]' AND ayah_range IS NULL;"
docker compose exec -T postgres psql -U mutalaa -d mutalaa -c "SELECT count(*) FROM icerik.review WHERE hedef_tablo = 'unit' AND alan = 'metin' AND hedef_anahtar LIKE 'tf:elmalili:%' AND durum = 'onaylandi' AND (ikinci_inceleyen IS NULL OR ikinci_inceleyen = inceleyen);"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- verify --flavor dev; echo "çıkış: $?"
dotnet run --project server/Mutalaa.Publisher -- publish --flavor public --dry-run   # P-04 gerekçesi beklenir
curl -sS http://localhost:8333/mutalaa/dev/manifest.json -o .tmp/dev-manifest.json && grep -c '"tefsir-elmalili"' .tmp/dev-manifest.json
pnpm --filter @mutalaa/mobile test
adb exec-out screencap -p > .tmp/tefsir.png
```
`chr(10214)` ve `chr(10215)` `⟦` ve `⟧` işaretleridir; kabuk ve konsol kodlamasına takılmasın diye `chr()` kullanılır (`windows-sorun`). Kısmi yayında ilk sorgu kapsamdaki surelerle süzülür. `-U` ve `-d` değerleri `.env.example` varsayılanlarıdır.

## Dikkat
- İçerik etiği: tefsir, âyet ve meal metni hafızadan yazılmaz, tamamlanmaz, düzeltilmez; testte açıkça sentetik `test-` metin ("Deneme paragrafı 1 …") ya da kaynak dosyadan betikle kesilmiş parça kullanılır.
- Sadeleştirilmiş baskılar kullanılmaz (K-03). Başkasının "orijinal metin" aktarımı (tefsir için archive.org metin katmanı) yalnız kontrollü yolla girer (K-38): `bekliyor` kaydı, aynı ölçüm (CER, sadeleştirme izi), eşik geçilirse `taslak` giriş ve özgün baskı görseliyle karşılaştırma. Metin katmanının kalitesi bilinmiyor; ölçüm yapılmadan ve eşik geçilmeden hiçbir parçası kopyalanmaz. Yapay zekâ tefsir üretmez ve çevirmez; görsel model yalnız ham OCR yapar, her çıktı insan onayından geçer.
- `embed_ok`: tarama bir kütüphaneden geldiyse kütüphanenin şartı görsellerin yapay zekâ servisine gönderilmesini belirler (Elmalılı hazırlığı §4).
- Kanonik metin: kendi aktarımımız ilk kayıtta bir kez NFC olur, sonra değişmez; ofsetler kod noktası, aralık yarı açık. Ayrıntı: `metin-butunlugu`, `capa-gramer`.
- `public` kararı Kurul cevabına ve aktarımımızın lisansına (S-12, Açık soru) bağlıdır. Hukuki görüş değildir.
- Onaysız `kurul_gerekli` paket `public` derlemeyi durdurur (P-04, çıkış `2`); onay gelene kadar `tefsir-elmalili` `public` paket listesine alınmaz (A37.1).
- İş büyüktür: oturumlar sure grupları hâlinde planlanır; yarıda kalan adımın yeri ilerleme notuna yazılır. Windows'ta dosyalar `encoding="utf-8"` ile açılır.

## İnsan adımları
- İ-11 · Tefsir düzeltme turları ve ikinci okuma: A37.3 boyunca.
- İ-17 · Görsel OCR bütçesi: A37.2'deki maliyet tahmininden sonra.
- Kurul'a tefsirin onay kapsamı sorusu (İ-02 kanalı): `public` kararından önce.
- Proje sahibi: öncelik sırası ve kısmi yayın; aktarımımızın lisansı (S-12) `public`'ten önce.
- Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `pipeline/src/mutalaa_pipeline/anchor/tefsir.py`, `qa/checks/` tefsir kuralları, `pipeline/tests/` tefsir testleri
- `shared/test-vectors/anchors/valid.jsonl`, `invalid.jsonl` ekleri
- Editoryal veritabanında `elmalili-tefsir` birimleri, `page_map`, `review` ve `xref` satırları; `data/ocr/`, `data/reports/` (git dışı)
- `tefsir-elmalili` paketi (`dev`); `apps/mobile/src/features/library/` ve `src/features/reader/` bağlama değişiklikleri ve testleri
- Karar defteri girdileri (haşiye, sure girişi, Kurul ihtiyatı); `docs/yazismalar/` Kurul sorusu taslağı

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A37-elmalili-tefsir-paketi.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A36](./A36-senkron.md) · Sonraki: [A38](./A38-web.md)
