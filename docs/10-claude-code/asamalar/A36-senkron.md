# A36 · Senkron ve bağlantı oyları (HLC, giden kutusu, `server_seq`, birleştirme)

> **Sürüm:** 1.0 · **Tarih:** 19 Ekim 2026 · **Durum:** Taslak · **Bağlı kararlar:** [K-16](../../00-ozet/02-karar-defteri.md#k-16--senkron-çakışma-çözümü) · [K-15](../../00-ozet/02-karar-defteri.md#k-15--hesap-ve-senkron-v1xte) · [K-26](../../00-ozet/02-karar-defteri.md#k-26--kalıcı-adresler-çapa-şeması) · [K-10](../../00-ozet/02-karar-defteri.md#k-10--arka-uç)
> **Faz:** 4 · v1.x · **Önkoşul:** [A35](./A35-hesap-ve-kvkk.md) · **İnsan adımı:** İ-03 · İ-20 (yalnız canlıya açılış adımı için; A35'teki gibi)
> **Ajanlar:** `sunucu-gelistirici` · `mobil-gelistirici` · `test-yazari` · `arastirmaci` · `arayuz-denetcisi` · `inceleyici` · **Beceriler:** `ef-goc` · `test-vektoru` · `mobil-ekran` · **Tahmini oturum:** 5–7
> **Başlat:** `/asama A36`

## Amaç
Hesabı bağlı cihazlar arasında kullanıcı verisi eşitlenir: UUIDv7 kimlikler, HLC zaman damgası, giden kutusu, `op_id` ile idempotent yükleme, `server_seq` imleçli çekme, 410 `imlec-eskidi` ile tam eşitleme ve K-16'nın veri türüne göre birleştirme kuralları. İki cihazda değişen not iki sürüm olarak korunur ve kullanıcı seçer. Kurallar sunucuda (C#) ve istemcide (TypeScript) aynı sonucu verir; bu ortak vektörlerle ve özellik tabanlı testlerle kilitlenir. Hesapla gelen bağlantı oyları ("Yararlı", "Yararsız", "Hata bildir") da bu aşamada açılır. Aşama, A35'in hazırladığı listeyle hesap, senkron ve oyların canlıya açılmasıyla biter.

## Okunacak belgeler
- [Kullanıcı verisi ve senkron](../../03-veri/04-kullanici-verisi-ve-senkron.md): tamamı
- [Backend API](../../02-mimari/05-backend-api.md): §5 senkron uçları, §6 hata modeli, §7 EF Core, §9 kültür
- [KVKK ve gizlilik](../../07-yayin/02-kvkk-ve-gizlilik.md): §3.2, §3.5 özel nitelikli veri önlemleri, §3.6
- [Çapa şeması](../../03-veri/01-capa-semasi.md): §8 depolama biçimi, §9 yeniden çapalama (senkronlanan kayıt kendiliğinden değişmez)
- [Test stratejisi](../../07-yayin/03-test-stratejisi.md): §6 kullanıcı veritabanı göç testleri · [Mobil ekranlar](../../01-urun/03-mobil-ekranlar.md): §6 ayarlar ağacı
- [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md): §12 oylar ve inceleme kuyruğu · [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md): §7 `xref_vote`

## Kapsam
**Yapılır**
- HLC ve birleştirme kurallarının iki dilde saf işlevler olarak yazılması; ortak vektörler.
- Sunucuda `kullanici` şeması, `POST /api/v1/sync/push`, `GET /api/v1/sync/pull`, silinmiş satır temizliği ve `gc_seq`.
- İstemcide giden kutusu, yükleme ve çekme döngüsü, birleştirme, tam eşitleme; not çakışması arayüzü.
- v1 "Geri yükle" akışının aynı birleştirme işlevlerine bağlanması; özellik tabanlı testler; canlıya açılış.
- Bağlantı oyları: `xref_vote`, `PUT` ve `DELETE /api/v1/xrefs/{id}/vote`, gece işi ve Bağlantılar panelindeki oy menüsü.

**Yapılmaz**
- Hesap, kimlik ve silme akışı (A35); silme ve döküm akışları oyları da kapsar (A35).
- Uçtan uca şifreli notlar (ertelenmiş seçenek, KVKK §3.5). Metin CRDT'si (yalnız ortak düzenleme gelirse). PowerSync (gereksinim büyürse değerlendirilir; §8 "Seçenekler").

## Adımlar
### A36.1 · Doğrulamalar ve ortak çekirdek
- `arastirmaci`: UUIDv7 üretimi için kitaplık ve Hermes'te güvenli rastgele sayı kaynağı (KV-4); not karşılaştırması için fark kitaplığı (KV-6); TypeScript ve .NET için özellik tabanlı test kitaplığı; expo-sqlite oturum değişiklik kümelerinin (SDK 56) bu tasarıma etkisi ("kullanımı Doğrulanacak").
- `packages/reader-core/src/sync/hlc.ts`: §3'teki sabit genişlikli biçim (`{12}-{4}-{16}` küçük harf onaltılık; düğüm `device_id`'nin tiresiz ilk 16 hanesi), `tick`, `recv`, sayaç taşması, `sync_state.hlc_last` kalıcılığı. C# karşılığı Domain'de (öneri `Mutalaa.Domain/Sync`; altyapı bağımlılığı yok).
- Birleştirme kuralları iki dilde saf işlev: §4 tablosu (kayıt bazında son yazan kazanır; `setting` anahtar başına; `hatim_page` küme birleşimi; `reading_position` cihaz başına; `note` iki sürüm) ve ek kurallar (silinen koleksiyonda `collection_id = NULL`; aynı çapa ve koleksiyonda başlıksız iki canlı yer iminden küçük `id` kalır; `vocab` `(lang, key)` için tek satır, büyük `seen_count`).
- Ortak vektörler (öneri, yeni aile; `/karar` ile kayda geçer): `shared/test-vectors/sync/hlc.jsonl` ve `shared/test-vectors/sync/merge.jsonl`; §4'teki beş örnek ilk satırlardır. Biçim `test-vektoru` becerisine uyar (JSONL, UTF-8, BOM yok, LF).
- **Bitti sayılır:** HLC ve birleştirme vektörleri TypeScript ve C#'ta yeşil.

### A36.2 · Sunucu: `kullanici` şeması ve senkron uçları
- `ef-goc`: `sync_user`, `device`, `op_log` ve §2'deki her kullanıcı tablosu §8'deki `kullanici.note` kalıbıyla (`user_id`, `server_seq`, birincil anahtar `(user_id, id)`, `(user_id, server_seq)` dizini; `reading_position` için `(user_id, device_id, context)` tekil). Tablolar A35'te seçilen kullanıcı veritabanındadır.
- `push`: işlemler sırayla uygulanır: `op_log`'da aynı `op_id` varsa kayıtlı sonuç döner; çapa `AnchorRef` ile ve boyutlar doğrulanır; tablo kuralı uygulanır; `server_seq` kullanıcının sayacından alınır (`UPDATE kullanici.sync_user SET last_seq = last_seq + $2 … RETURNING`; genel dizi kullanılmaz); sonuç `op_log`'a yazılır. İstek en çok 500 işlem taşır. Sonuç kodları `uygulandi`, `eskimis`, `reddedildi`; not çakışması `cakisma_kopyasi` (`id = op_id`, `conflict_of`). Yanıt `server_seq` ve `server_hlc` taşır.
- `pull`: her tablodan `server_seq > cursor` ilk `limit` satır okunur, birleştirilir, sıralanır; `next_cursor`, `has_more`, `server_hlc`.
- Silinmiş satırlar 180 gün tutulur (öneri, KV-1); temizlik işi `gc_seq` yazar; imleci gerideki istek 410 ve `imlec-eskidi` alır. Saati 10 dakikadan fazla ileride olan işlem `saat_ileri` ile reddedilir (öneri, KV-2). İki kod da Backend API §6 hata tablosundadır; `saat_ileri`'nin HTTP kodu ve istek düzeyinde mi işlem sonucu olarak mı döndüğü Doğrulanacak; karar verilince `/belge-esitle` ile işlenir.
- Testler (Testcontainers `postgres:18`): aynı `op_id` ile yeniden gönderim aynı sonucu verir ve `last_seq` artmaz; aynı kullanıcının eşzamanlı iki yüklemesinde `server_seq` tekrarsız ve artan; sayfalı çekme atlamasız; 501 işlem 400; 410 yolu; A35 silme testi yeni tabloları da kapsıyor.
- **Bitti sayılır:** `dotnet test` yeşil; OpenAPI farkı temiz.

### A36.3 · İstemci: giden kutusu, döngü ve birleştirme
- Hesap bağlıyken her kullanıcı yazması ile `outbox` satırı aynı işlemde yazılır (§2 "Yazma"). İlk bağlamada bütün yerel satırlar bir kez kuyruğa alınır ve hesaptaki verilerle §4 kurallarıyla birleşir; ikinci cihaz da aynı yolla katılır.
- Giden kutusunda aynı satırın gönderilmemiş işlemleri teke iner; yanıtı gelmemiş işlem aynı `op_id` ile yeniden gönderilir; o arada gelen değişiklik yeni `op_id` alır. Yanıttaki `accepted` ve `conflicts` listelerindeki işlemler giden kutusundan silinir ve satırın `base_version` değeri dönen `server_seq` olur.
- Tetikler: uygulama öne gelince, yerel yazmadan 5 saniye sonra (toplanarak), "Şimdi eşitle". Önce yükleme, sonra `has_more` bitene kadar çekme; imleç `sync_state`'e yazılır; `recv(server_hlc)` çağrılır.
- 410'da tam eşitleme: giden kutusu yüklenir, canlı satırların tamamı indirilir, giden kutusunda olmayan ve sunucuda bulunmayan yerel satırlar silinir. Cihaz kendi silinmiş satırlarını 365 gün tutar (öneri).
- v1 "Geri yükle" (A30) aynı birleştirme işlevlerini çağırır; ayrı kural kopyası kalmaz.
- Gizlilik: senkron kullanıcı açınca başlar; okuma ilerlemesi ve hatim için ayrı anahtar (öneri, KVKK §3.5); Gizli modda okuma geçmişi, otomatik hatim işareti ve seri kaydı yazılmaz (01-urun/02 §14, 03-veri/04 §7). Eşitlenen ayarlar §7 tablosundadır.
- Yeniden çapalama sonucu yalnız `device.db` `anchor_resolution` önbelleğine yazılır; senkronlanan kayıt kullanıcı eylemi olmadan değişmez.
- **Bitti sayılır:** istemci birim testleri ve vektörler yeşil; `user.db` göç testleri yayımlanmış her şema sürümünün fikstüründe veri kaybı göstermiyor.

### A36.4 · Not çakışması arayüzü ve bildirimler
- §5: asıl notta şerit ("Bu not iki cihazda değiştirildi · Sürümleri karşılaştır"), Defterim'de metinli "Çakışma" rozeti, karşılaştırma ekranı (telefonda alt alta, tablette yan yana; cihaz adı ve zaman), dört eylem; çözüm tek işlemdir.
- Örnek 5 bildirimi ("Bu not başka bir cihazda düzenlendiği için geri getirildi") ve Örnek 4 önerisi ("Diğer cihazda: Bakara 255 · 2 saat önce").
- Ekran okuyucu etiketi, 44×44 pt hedefler; renk tek başına anlam taşımaz. Ekran görüntüsüyle denetim (`mobil-ekran`, `arayuz-denetcisi`).
- **Bitti sayılır:** bileşen testleri yeşil; Kâğıt ve Gece temasında ekran görüntüleri incelendi.

### A36.5 · Özellik tabanlı testler ve iki cihaz senaryoları
- `test-yazari`: sabit tohumlu üreteçle, özellik başına en az 1.000 rastgele işlem dizisi (öneri), iki dilde:
  1. Yakınsama: aynı işlem kümesi farklı sıralarla uygulanınca bütün kopyalar aynı duruma varır.
  2. İdempotentlik: aynı `op_id` iki kez uygulanınca durum ve `server_seq` değişmez.
  3. HLC tekdüzeliği: `tick` ve `recv` sonrası değer görülen her değerden büyüktür; cihaz saati geri alınsa da küçülmez.
  4. Not kaybı yok: iki tarafta değişen notta iki metin de korunur (asıl ve tek kopya, `conflict_of`); silme ile düzenleme yarışında düzenleme kazanır.
  5. Hatim işareti kaybolmaz: eşzamanlı işaretler korunur; silme yalnız gördüğü satırları kaldırır.
  6. `reading_position` çakışmaz: `(device_id, context)` başına tek satır.
  7. İmleç: sayfalı çekme her değişikliği tam bir kez verir.
- İki cihaz: C# bütünleşik testinde iki sanal istemci (HTTP) §4'teki beş örneği adıyla koşar. Gerçek iki cihazla (emülatör ve telefon, yerel API) bir elle tur yapılır ve sonucu kayda yazılır.
- **Bitti sayılır:** özellik ve senaryo testleri yeşil; tohumlar test çıktısında.

### A36.6 · Bağlantı oyları
- Sunucu (`sunucu-gelistirici`, `ef-goc`): `xref_vote(xref_id, account_hash, vote, reason, data_version, created_at)` A35'te seçilen kullanıcı veritabanındadır; `account_hash = HMAC-SHA256(sunucu sırrı, hesap kimliği)`, sır kullanıcı sırlarında durur ([Backend API](../../02-mimari/05-backend-api.md) §5; [Editoryal veritabanı](../../03-veri/02-editoryal-veritabani.md) §7).
- `PUT /api/v1/xrefs/{id}/vote` (`{vote: up|down, reason?}`; nedenler `yanlis_ayet`, `iktibas_degil`, `kok_yanlis`, `alakasiz`) ve `DELETE`; hesap başına tek oy; hız sınırı hesap ve IP başına. Hesap silinince oylar silinir (A35 silme işi).
- Gece işi oyları editoryal veritabanındaki `xref.votes_up` ve `votes_down` sayaçlarına işler ve [Bağlantı modeli](../../05-capraz-referans/01-baglanti-modeli.md) §12'deki Wilson eşikleriyle `review` satırı açar. Oy bağlantının durumunu kendiliğinden değiştirmez; karar editöründür. Etki sonraki paket sürümüyle cihaza ulaşır.
- Mobil (`mobil-gelistirici`): Bağlantılar panelinde satır menüsüne "Yararlı", "Yararsız" ve nedenli "Hata bildir"; yalnız hesap bağlıyken ve `hesapVeSenkron` açıkken görünür. Oy sayısı ve katkı sıralaması gösterilmez (K-25). Çevrimdışıyken menü devre dışıdır (öneri; başka bir yol `/karar` ister).
- **Bitti sayılır:** oy uçlarının bütünleşik testleri (tek oy, oyu geri alma, hesap silinince oyların silinmesi) ve gece işinin eşik testleri yeşil; menü ekran görüntüsüyle incelendi.

### A36.7 · Canlıya açılış (A35 listesiyle)
- Önkoşul: İ-20 ve İ-03 tamam; A35'in `docs/07-yayin/surum-kayitlari/v1x-kvkk.md` (öneri) listesinde KVKK §4 "Faz 4 öncesi" maddeleri kapalı. Değilse aşama bu adımda `sürüyor` kalır ve beklenen insan adımı ilerleme dosyasına yazılır.
- A35.5 listesi uygulanır. `hesapVeSenkron` önce `internal`, sonra yeni uygulama sürümüyle `public` için açılır (A34 yordamı).
- **Bitti sayılır:** canlı `/health/ready` HTTPS üzerinden 200; canlıda editör uçları 404; gerçek iki cihazla canlı senkron turu başarılı.

## Kabul ölçütleri
- [ ] `shared/test-vectors/sync/*.jsonl` TypeScript ve C#'ta yeşil; JSONL biçim denetimi geçiyor.
- [ ] Yedi özellik testi sabit tohumla yeşil; tohumlar raporda.
- [ ] §4'teki beş örnek sunucu ve istemci tarafında adlandırılmış senaryo testi olarak yeşil.
- [ ] Aynı `op_id` ile yeniden gönderimde sonuç aynı, `last_seq` değişmiyor; eşzamanlı yüklemelerde `server_seq` tekrarsız ve artan.
- [ ] `gc_seq` gerisindeki imleç 410 ve `imlec-eskidi` alıyor; tam eşitlemeden sonra istemcinin canlı satır kümesi sunucuyla aynı.
- [ ] 501 işlemli istek 400 alıyor.
- [ ] Altı ortak sütun testi ve `user.db` göç testleri yeşil; `outbox` ve `sync_state` yedek dosyasına girmiyor.
- [ ] A35 silme testi yeni `kullanici` tablolarını kapsayarak yeşil.
- [ ] Backend API §6 hata tablosunda `imlec-eskidi` var (`grep`).
- [ ] Oy uçları hesap başına tek oy yazıyor; `DELETE` oyu kaldırıyor; hesap silinince oylar siliniyor; gece işi bağlantı durumunu değiştirmeden `review` satırı açıyor (bütünleşik testler).
- [ ] Canlıya açılış yapıldıysa canlı sağlık ucu 200, editör ucu 404.

## Doğrulama
```bash
pnpm --filter @mutalaa/test-vectors build          # JSONL biçim denetimi
pnpm --filter @mutalaa/reader-core test
pnpm --filter @mutalaa/mobile test                 # user.db göç ve ortak sütun testleri dahil
dotnet test --solution server/Mutalaa.slnx
git diff --exit-code server/Mutalaa.Api/openapi
grep -n "imlec-eskidi" docs/02-mimari/05-backend-api.md
# Canlıya açılıştan sonra (A36.7)
curl -sSf "https://<api-alanı>/health/ready"
curl -s -o /dev/null -w "%{http_code}\n" "https://<api-alanı>/api/v1/sources"   # 404
```
PowerShell'de `curl` yerine `curl.exe` yazılır.

## Dikkat
- Birleştirmede `updated_at` kullanılmaz; sıra yalnız HLC'dir. HLC biçimi sabit genişliklidir ve değişmez; dizgi karşılaştırması ordinaldir.
- Kayıt bazında son yazan kazanır; alan bazında birleştirme yapılmaz (Örnek 1'in bilinen bedeli, K-16).
- Notta kullanıcının yazdığı metin hiçbir yolda kaybolmaz.
- Sunucu kayıt içeriğini işlemez, analiz etmez, günlüğe yazmaz; yalnız saklar ve eşler (KVKK §3.5). Günlükte not metni yok.
- Çapalar kalıcıdır; sunucu çapayı doğrular ama yeniden çapalamaz.
- Kültürden bağımsızlık: Domain testleri `tr-TR` kültüründe de geçer; zaman `timestamptz` ve UTC.

## İnsan adımları
- İ-03 · İ-20: canlıya açılış (A36.7) A35'teki gibi bu iki adımın tamamlanmasını bekler. Gerçek iki cihazla elle senkron turu kullanıcıyla yapılır. Ayrıntı: [İnsan adımları](../06-insan-adimlari.md).

## Çıktılar
- `packages/reader-core/src/sync/` (HLC, birleştirme, giden kutusu, döngü) ve testleri
- `apps/mobile/src/features/notebook/` ve `src/features/settings/` (çakışma ekranı, senkron ayarları); `src/db/` yazma yolu
- `server/Mutalaa.Domain/Sync/` (öneri), `server/Mutalaa.Infrastructure/` göçleri, `server/Mutalaa.Api/Endpoints/` senkron uçları, `openapi/v1.json`, `server/tests/`
- `shared/test-vectors/sync/hlc.jsonl`, `merge.jsonl` (öneri)
- Belge güncellemeleri: Backend API §6, Kullanıcı verisi ve senkron §9 (KV maddeleri), karar defteri

## Elle başlatma istemi
```text
docs/10-claude-code/asamalar/A36-senkron.md dosyasındaki aşamayı yürüt. Önce önkoşulları ve planı göster, onayımı bekle.
```

## İlgili dosyalar
- [Aşama haritası](../04-asama-haritasi.md) · [İlerleme](../05-ilerleme.md) · Önceki: [A35](./A35-hesap-ve-kvkk.md) · Sonraki: [A37](./A37-elmalili-tefsir-paketi.md)
