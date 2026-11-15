"""`export pg --source risale-kelime-frekans`: Risale lugat adaylari (A20.6, K-52 madde 9 ve 10).

`export/pg.py` ile ayni akis (dosya onkosullari -> tek veritabani islemi, advisory kilit,
`source` satiri `pg._source_satirlari` ile); sablonlar `pg_glosses.py` (hazir kaynaktan aday +
`review` acma) ve `pg_risale.py`'dir. Dosya tarafi: kaynak kaydi (G-KAY), son `ingest lugat`
calismasi (`lugat.jsonl`; lugatin ayri bir `anchor` adimi yoktur, zincirin tek halkasi ingest'tir),
ham dosyalarin (zip ve uc OCR dosyasi) manifestle tutmasi, QA raporu (DORT kapi: G-KAY, G-BUT,
G-CAP, G-NOR; kalan kapida yukleme yapilmaz) ve satirlarin kati okunmasi. Diyanet
(`risale-asil-nusha`) ve baska kaynaklar bu yoldan yuklenmez.

Sentetik fikstur (`test-risale-ornek`): 15 uydurma madde ayni kaynak adinda, `ingest risale`
calismasinin `lugat.jsonl` dosyasindadir; `pg_risale.hazirla` onu `calismadan_oku` ile okur ve
`pg._yukle` birimlerden sonra AYNI islemde `yukle` ile yazar (yalniz `dev`e girer; P-12).

YAZMA KURALI (K-52 madde 9 ve 10, Editoryal veritabani 5; hat insan kararina dokunmaz):

* Upsert `ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key` (`CONSTRAINT`;
  A20.6b'den once `..._basliksoz_key`). Madde yoksa eklenir:
  `status = 'aday'`, `origin = 'hat'`, `version = '1'` (metin), `tanim_tr` NULL (fiksturde staged
  degeri), `content_hash` staged degeri (`sha256(basliksoz + LF + coalesce(tanim_tr, ''))`; hat
  yuklemeden once yeniden hesaplar, tutmazsa cikis 1).
* Madde varsa YALNIZ `origin = 'hat' AND status = 'aday'` satirda ve YALNIZ turetilmis sutunlar
  (`kaynaklar`, `duzey`, `data_version`, `basliksoz_norm`, `updated_at = now()`) guncellenir ve
  yalniz degeri farkliysa. `origin = 'editor'` ya da `status <> 'aday'` satira HIC yazilmaz
  (`tanim_tr`, `status`, `version`, `content_hash`, `origin` dahil). Satir silinmez.
* Anlam basvurusu (`anlam_basvuru`) HICBIR tabloda madde sutununa girmez (`lugat_madde.kaynaklar`
  dahil): yalniz `review.onerilen`de durur. Staged `kaynaklar` icinde bu anahtar varsa girdi
  reddedilir (cikis 2).
* Her YENI madde icin bir `review` satiri: `hedef_tablo = 'lugat_madde'`, `hedef_anahtar =
  '{source_id}:{basliksoz}'`, `alan = 'tanim_tr'`, `eylem = 'oner'`, `koken = 'hat'`, `oneren =
  'hat'`, `onceki` NULL, `yz_modeli` ve `yz_kaydi` NULL, `onerilen = {anlam_basvuru, siklik,
  kitaplar}`. Ayni hedef icin ACIK `review` varsa yeni satir acilmaz; var olan maddenin `review`
  satirina (acik ya da kapali) dokunulmaz: `onerilen` yenilenmez, editor karari korunur.
* `--dry-run` baglanir, her seyi yapar ve geri alir (Rollback); hicbir sey yazilmaz.

Iletiler ve rapor yalniz sayi ve satir numarasi tasir; basliksoz, tanim ve anlam metni yazilmaz.
Sayaclar: `lugat_staging`, `lugat_eklenen`, `lugat_ayni_kalan`, `lugat_guncellenen`,
`lugat_atlanan_editor`, `lugat_review_acilan`, `lugat_review_acik_nedeniyle_atlanan`,
`lugat_veritabaninda_fazla`.

LUGAT KAYNAKLARI (A20.6b; `lugat-rnk`, `lugat-sozluk-rganeyev`; K-52 madde 10 ve 14): ayri yol
(`hazirla_kaynakli`, `yukle_kaynakli`), Kelime-Frekans yoluna DOKUNMAZ (yalniz cakisma kisiti
adi `lugat_madde_source_id_basliksoz_anlam_no_key` olur: eski kisit sunucu gocuyle dusurulur;
Kelime-Frekans satirlari `anlam_no = 1`, `origin = 'hat'` kalir):

* Upsert `ON CONFLICT ON CONSTRAINT lugat_madde_source_id_basliksoz_anlam_no_key` (`source_id`,
  `basliksoz`, `anlam_no`). Madde yoksa eklenir: `status = 'aday'`, `origin = 'kaynak'`,
  `version = '1'`, `anlam_no`, DOLU `tanim_tr` (kaynak satirindan bayt bayt; NFC yok) ve
  staged `content_hash`.
* Madde varsa YALNIZ `origin <> 'editor' AND status = 'aday'` satirda ve YALNIZ turetilmis
  sutunlar (`kaynaklar`, `duzey`, `data_version`, `basliksoz_norm`, `updated_at = now()`) ve
  yalniz degeri farkliysa guncellenir. `tanim_tr` ve `content_hash` var olan satirda HIC
  yazilmaz: kaynak dosyasi degisip staged tanim veritabanindakinden farkliysa satir degismez,
  `lugat_metin_degisti` sayilir (Risale metni kurali, K-52). `origin = 'editor'` ya da
  `status <> 'aday'` satira HIC yazilmaz. Satir silinmez.
* `review`: YALNIZ `duzey` 1-3 olan (Risale'de gecen) maddeler icin (`hedef_tablo =
  'lugat_madde'`, `hedef_anahtar = '{source_id}:{anlam_no}:{basliksoz}'`, `alan = 'tanim_tr'`,
  `eylem = 'oner'`, `koken = 'hat'`, `oneren = 'hat'`, `onceki` NULL, `onerilen = {kaynak,
  siklik}`; anlam basvurusu yok). `duzey` 4 maddeler review'siz `aday` kalir (toplu onay yolu ayri
  karar, BC). Ayni hedef icin HERHANGI bir review (acik ya da kapali) varsa yenisi acilmaz:
  editor karari yeniden acilmaz. Editor satirina review acilmaz.
* Sayaclar `lugat_staging`, `lugat_eklenen`, `lugat_ayni_kalan`, `lugat_guncellenen`,
  `lugat_atlanan_editor`, `lugat_metin_degisti`, `lugat_review_acilan`,
  `lugat_review_var_nedeniyle_atlanan`, `lugat_review_gerektirmeyen` (duzey 4),
  `lugat_veritabaninda_fazla`; hepsi sayidir, metin yoktur.
"""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final

import psycopg
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    INGEST_ADIMI,
    Hazirlik,
    ZincirRun,
    _bildirim,
    _manifest_ozet,
    _qa_denetle,
    _zincir_denetle,
)
from mutalaa_pipeline.ingest.kelime_frekans import KAYNAK
from mutalaa_pipeline.ingest.lugat_kaynak import KAYNAKLAR as LUGAT_KAYNAK_KIMLIKLERI
from mutalaa_pipeline.ingest.lugat_madde import (
    DURUM_ADAY,
    DUZEY_RISALEDE_YOK,
    EN_COK_ANLAM_NO,
    EN_SEYREK_DUZEY,
    KOKEN_HAT,
    KOKEN_KAYNAK,
    LUGAT_ADI,
    MADDE_ALANLARI,
    MADDE_ALANLARI_KAYNAK,
    SURUM_1,
    basliksoz_norm,
    duzey_hesapla,
    madde_hash,
)
from mutalaa_pipeline.ingest.risale_kaynaklari import KAYNAK_ORNEK
from mutalaa_pipeline.lineage import OZET_DESENI, RUN_ID_DESENI
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_oku

# `export pg` ile yuklenebilen lugat kaynaklari: gercek Kelime-Frekans ve sentetik fikstur.
KAYNAKLAR: Final = frozenset({KAYNAK, KAYNAK_ORNEK})
# A20.6b: tanimli lugat kaynaklari (`lugat-rnk`, `lugat-sozluk-rganeyev`); ayri yuk yolu.
KAYNAKLI: Final = frozenset(LUGAT_KAYNAK_KIMLIKLERI)
# Tekillik kisiti: (source_id, basliksoz, anlam_no). Eski kisit (source_id, basliksoz) sunucu
# gocuyle dusurulur; Kelime-Frekans satirlari `anlam_no = 1` ile ayni kisita carpar.
CONSTRAINT: Final = "lugat_madde_source_id_basliksoz_anlam_no_key"
HEDEF_TABLO: Final = "lugat_madde"
VERSION: Final = str(SURUM_1)
# Madde `kaynaklar` jsonb'sinin izinli ust anahtarlari; `siklik` ve `kitaplar` zorunludur.
KAYNAKLAR_ANAHTARLARI: Final = frozenset(
    {"siklik", "kitaplar", "sozluk_isabet", "sozluk_guvenilmez", "fikstur"}
)
ZORUNLU_KAYNAKLAR: Final = frozenset({"siklik", "kitaplar"})
ONERILEN_ANAHTARLARI: Final = frozenset({"anlam_basvuru", "siklik", "kitaplar"})
# `kaynaklar` icinde (her derinlikte) bulunmamasi gereken anahtarlar: anlam yalniz
# `review.onerilen`de durur.
YASAK_ANAHTARLAR: Final = frozenset({"anlam_basvuru", "anlam"})
BOS_ALANLAR: Final = ("osmanlica_yazim", "koken_dil", "ar_kok_id")


@dataclass(frozen=True, slots=True)
class LugatSatiri:
    """Dogrulanmis `lugat.jsonl` satiri; metin alanlari yalniz veritabanina gider."""

    source_id: str
    basliksoz: str
    basliksoz_norm: str
    tanim_tr: str | None
    kaynaklar: dict[str, object]
    duzey: int
    data_version: str
    content_hash: str
    onerilen: dict[str, object]


# --- kaynak denetimi -----------------------------------------------------------------------


def kaynak_denetle(source_id: str) -> None:
    """Yalniz Kelime-Frekans, lugat kaynaklari (ve sentetik fikstur) bu yoldan yuklenir;
    digerleri cikis 2."""
    if source_id not in KAYNAKLAR and source_id not in KAYNAKLI:
        raise GirdiHatasi(
            f"{source_id}: lugat yuklemesi yalniz {KAYNAK}, {', '.join(sorted(KAYNAKLI))}"
            " icindir (export pg lugat yolu)"
        )


# --- satirlari okuma (kati) ----------------------------------------------------------------


def _tam(deger: object) -> int | None:
    return deger if isinstance(deger, int) and not isinstance(deger, bool) else None


def _nul_var(nesne: object) -> bool:
    """JSON degerinde NUL (jsonb'ye yazilamaz) var mi."""
    return "\\u0000" in json.dumps(nesne, ensure_ascii=True)


def _yasak_anahtar_var(deger: object) -> bool:
    """`kaynaklar` icinde herhangi bir derinlikte anlam anahtari var mi."""
    if isinstance(deger, dict):
        return any(a in YASAK_ANAHTARLAR or _yasak_anahtar_var(v) for a, v in deger.items())
    if isinstance(deger, list):
        return any(_yasak_anahtar_var(v) for v in deger)
    return False


def _basvuru(yer: str, deger: object, siklik: int) -> dict[str, object]:
    """`onerilen_basvuru`: `{anlam_basvuru: [{anlam, sayi}], siklik, kitaplar}`."""
    if not isinstance(deger, dict) or set(deger) != ONERILEN_ANAHTARLARI:
        raise GirdiHatasi(f"{yer}: onerilen_basvuru alan kumesi beklenen degil")
    liste = deger["anlam_basvuru"]
    if not isinstance(liste, list):
        raise GirdiHatasi(f"{yer}: anlam_basvuru liste degil")
    for oge in liste:
        if (
            not isinstance(oge, dict)
            or set(oge) != {"anlam", "sayi"}
            or not isinstance(oge["anlam"], str)
            or oge["anlam"] == ""
            or (_tam(oge["sayi"]) or 0) < 1
        ):
            raise GirdiHatasi(f"{yer}: anlam_basvuru ogesi {{anlam, sayi}} degil")
    kitaplar = _tam(deger["kitaplar"])
    if _tam(deger["siklik"]) != siklik or kitaplar is None or kitaplar < 1:
        raise GirdiHatasi(f"{yer}: onerilen_basvuru siklik ya da kitaplar tutmuyor")
    if _nul_var(deger):
        raise GirdiHatasi(f"{yer}: onerilen_basvuru NUL iceriyor")
    return dict(deger)


def satir_coz(satir: Satir, source_id: str) -> LugatSatiri:
    """Tek `lugat.jsonl` satirini kati dogrular; iletiler yalniz satir no ve alan adi tasir.

    Girdi bicimi hatasi `GirdiHatasi` (cikis 2); `content_hash` uyusmazligi hat hatasidir:
    `QaKaldi` (cikis 1).
    """
    yer = f"{satir.etiket}: satir {satir.no}"
    if set(satir.veri) != set(MADDE_ALANLARI):
        raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
    if satir.metin("source_id") != source_id:
        raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
    baslik = satir.metin("basliksoz")
    if baslik == "" or "\x00" in baslik:
        raise GirdiHatasi(f"{yer}: basliksoz bos ya da NUL iceriyor")
    norm = satir.metin("basliksoz_norm")
    if norm == "" or "\x00" in norm or norm != basliksoz_norm(baslik):
        raise GirdiHatasi(f"{yer}: basliksoz_norm bos ya da basliksozle tutmuyor")
    if (
        satir.metin("status") != DURUM_ADAY
        or satir.metin("origin") != KOKEN_HAT
        or satir.sayi("version") != SURUM_1
    ):
        raise GirdiHatasi(f"{yer}: durum aday, kok hat ve surum 1 olmali")
    for alan in BOS_ALANLAR:
        if satir.veri[alan] is not None:
            raise GirdiHatasi(f"{yer}: {alan} bos olmali (editor doldurur)")
    tanim = satir.veri["tanim_tr"]
    if tanim is not None and (
        source_id == KAYNAK or not isinstance(tanim, str) or tanim.strip() == "" or "\x00" in tanim
    ):
        raise GirdiHatasi(f"{yer}: tanim_tr bos olmali (tanimi editor yazar)")
    kaynaklar = satir.nesne("kaynaklar")
    if (
        not ZORUNLU_KAYNAKLAR <= set(kaynaklar) <= KAYNAKLAR_ANAHTARLARI
        or _yasak_anahtar_var(kaynaklar)
        or _nul_var(kaynaklar)
    ):
        raise GirdiHatasi(f"{yer}: kaynaklar anahtar kumesi gecersiz (anlam basvurusu girmez)")
    siklik = _tam(kaynaklar["siklik"])
    if siklik is None or siklik < 1:
        raise GirdiHatasi(f"{yer}: kaynaklar.siklik gecersiz")
    duzey = satir.sayi("duzey")
    if not 1 <= duzey <= EN_SEYREK_DUZEY or duzey != duzey_hesapla(siklik):
        raise GirdiHatasi(f"{yer}: duzey sikliga gore hesaplananla ayni degil")
    surum = satir.metin("data_version")
    if surum == "" or "\x00" in surum:
        raise GirdiHatasi(f"{yer}: data_version gecersiz")
    ozet = satir.metin("content_hash")
    if OZET_DESENI.fullmatch(ozet) is None:
        raise GirdiHatasi(f"{yer}: content_hash 64 haneli kucuk harfli onaltilik degil")
    try:
        beklenen = madde_hash(baslik, tanim if isinstance(tanim, str) else None)
    except UnicodeEncodeError:
        raise GirdiHatasi(f"{yer}: basliksoz UTF-8 olarak yazilamaz") from None
    if beklenen != ozet:  # hat hatasi: cikis 1 (cagiran yakalar)
        raise QaKaldi(f"staged content_hash maddeyle tutmuyor: satir {satir.no}")
    return LugatSatiri(
        source_id=source_id,
        basliksoz=baslik,
        basliksoz_norm=norm,
        tanim_tr=tanim if isinstance(tanim, str) else None,
        kaynaklar=dict(kaynaklar),
        duzey=duzey,
        data_version=surum,
        content_hash=ozet,
        onerilen=_basvuru(yer, satir.veri["onerilen_basvuru"], siklik),
    )


def satirlari_coz(veri: bytes, source_id: str) -> list[LugatSatiri]:
    """`lugat.jsonl` baytlarini kati okur; yinelenen baslik soz girdi hatasidir."""
    etiket = f"ingest {source_id} {LUGAT_ADI}"
    satirlar: list[LugatSatiri] = []
    gorulen: set[str] = set()
    for s in satirlari_oku(veri, etiket):
        madde = satir_coz(s, source_id)
        if madde.basliksoz in gorulen:
            raise GirdiHatasi(f"{etiket}: satir {s.no}: yinelenen basliksoz")
        gorulen.add(madde.basliksoz)
        satirlar.append(madde)
    return satirlar


# --- hazirlik ------------------------------------------------------------------------------


def calismadan_baytlar(ctx: RunContext, ingest: ZincirRun) -> tuple[str, str, bytes]:
    """Ingest calismasinin `lugat.jsonl` dosyasi: `(veri koku yolu, sha256, bayt)`.

    Dosya manifestteki ozetle dogrulanir; satirlar burada AYRISTIRILMAZ (`satirlari_coz`).
    """
    beklenen = _manifest_ozet(ingest.manifest, LUGAT_ADI)
    if beklenen is None:
        raise GirdiHatasi(f"ingest manifestinde {LUGAT_ADI} yok (once ingest, --force ile)")
    dosya = ingest.klasor / LUGAT_ADI
    try:
        veri = dosya.read_bytes()
    except OSError:
        raise GirdiHatasi(f"{LUGAT_ADI} okunamadi") from None
    sha = lineage.sha256_bayt(veri)
    if sha != beklenen:
        raise GirdiHatasi(f"{LUGAT_ADI} ozeti manifestle tutmuyor")
    return lineage.goreli_yol(ctx.veri_kok, dosya), sha, veri


def calismadan_oku(
    ctx: RunContext, ingest: ZincirRun, source_id: str
) -> tuple[str, str, list[LugatSatiri]]:
    """`calismadan_baytlar` ve kati okuma: `(veri koku yolu, sha256, satirlar)` (fikstur yolu)."""
    yol, sha, veri = calismadan_baytlar(ctx, ingest)
    return yol, sha, satirlari_coz(veri, source_id)


def _ingest_calismasi(ctx: RunContext, source_id: str, run: str | None) -> ZincirRun:
    """`--run` verilmisse o ingest calismasi, verilmediyse manifestli en son ingest."""
    klasor = ctx.staged_kaynak_dizini(source_id)
    if run is not None:
        if RUN_ID_DESENI.fullmatch(run) is None:
            raise GirdiHatasi("--run bir UUID degil")
        for kayit in lineage.calismalar(klasor):
            if kayit[0] == run:
                if kayit[2].get("adim") != INGEST_ADIMI:
                    raise GirdiHatasi("--run bir ingest calistirmasi degil")
                return ZincirRun(kayit[0], INGEST_ADIMI, source_id, kayit[1], dict(kayit[2]))
        raise GirdiHatasi("--run icin manifestli ingest calistirmasi yok")
    son = lineage.son_basarili(klasor, INGEST_ADIMI)
    if son is None:
        raise GirdiHatasi("manifestli ingest calistirmasi yok (once: ingest lugat)")
    return ZincirRun(son[0], INGEST_ADIMI, source_id, son[1], dict(son[2]))


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (Kelime-Frekans lugati)."""
    kaynak_denetle(source_id)
    if source_id in KAYNAKLI:  # A20.6b: tanimli lugat kaynaklari (ayri yol)
        return hazirla_kaynakli(ctx, source_id, run, ek_kaynaklar)
    if source_id != KAYNAK:  # fikstur: lugat birimlerle birlikte yuklenir (pg_risale.hazirla)
        raise GirdiHatasi(f"{source_id}: lugat maddeleri birimlerle birlikte yuklenir (export pg)")
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    ingest = _ingest_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, ingest.manifest):
        raise GirdiHatasi("ingest calistirmasinin ciktilari saglam degil")
    yol, sha, veri = calismadan_baytlar(ctx, ingest)
    ingestler, ham = _zincir_denetle(ctx, [ingest], kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, ingest.run_id, sha)  # dort kapi; kalirsa yukleme yok
    satirlar = satirlari_coz(veri, source_id)
    bildirimler = {slug: _bildirim(ingestler[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    # Parmak izi kaynak zip'i ve uc OCR dosyasinin hepsini kapsar; `source` satirinin
    # alinma tarihi ve dosya ozeti yalniz zip'ten dolar (tek dosyali kaynak kurali, pg._alinma).
    girdiler = [lineage.Girdi(yol, sha, ingest.run_id)]
    girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[source_id]]
    zip_dosyalari = [d for d in ham[source_id] if d["yol"].startswith(f"raw/{source_id}/")]
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=ingest.run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=[ingest],
        ingest=ingestler,
        ham={source_id: zip_dosyalari},
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=ctx.parmak_izi(girdiler),
        lugat=satirlar,
    )


# --- veritabani ----------------------------------------------------------------------------

STAGING: Final = (
    'CREATE TEMP TABLE staging_lugat (sira integer, basliksoz text COLLATE "C",'
    " basliksoz_norm text, tanim_tr text, kaynaklar jsonb, duzey smallint, data_version text,"
    " content_hash char(64), onerilen jsonb) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_lugat (sira, basliksoz, basliksoz_norm, tanim_tr, kaynaklar, duzey,"
    " data_version, content_hash, onerilen) FROM STDIN"
)
STAGING_ANALIZ: Final = "ANALYZE pg_temp.staging_lugat"
# Her staged maddenin veritabani durumu INSERT'ten ONCE tek geciste bir gecici tabloya yazilir
# (acik `review` gruplanarak); sayaclar ve review ekleme bu tabloyu okur.
DURUM: Final = (
    "CREATE TEMP TABLE lugat_durum ON COMMIT DROP AS"
    " WITH rv AS (SELECT r.hedef_anahtar FROM icerik.review r"
    " WHERE r.hedef_tablo = 'lugat_madde' AND r.durum = 'acik' GROUP BY r.hedef_anahtar)"
    " SELECT s.*, m.id AS m_id, m.origin AS m_origin, m.status::text AS m_durum,"
    " (m.kaynaklar, m.duzey, m.data_version, m.basliksoz_norm)"
    " IS DISTINCT FROM (s.kaynaklar, s.duzey, s.data_version, s.basliksoz_norm) AS farkli,"
    " rv.hedef_anahtar IS NOT NULL AS acik_review FROM pg_temp.staging_lugat s"
    " LEFT JOIN icerik.lugat_madde m ON m.source_id = %s::text AND m.basliksoz = s.basliksoz"
    " LEFT JOIN rv ON rv.hedef_anahtar = %s::text || ':' || s.basliksoz"
)
# eklenecek, editor/aday-olmayan nedeniyle atlanan, guncellenecek, acilacak review, acik review
# nedeniyle atlanan (INSERT'ten ONCE).
SAYAC: Final = (
    "SELECT count(*) FILTER (WHERE o.m_id IS NULL),"
    " count(*) FILTER (WHERE o.m_id IS NOT NULL"
    " AND NOT (o.m_origin = 'hat' AND o.m_durum = 'aday')),"
    " count(*) FILTER (WHERE o.m_origin = 'hat' AND o.m_durum = 'aday' AND o.farkli),"
    " count(*) FILTER (WHERE o.m_id IS NULL AND NOT o.acik_review),"
    " count(*) FILTER (WHERE o.m_id IS NULL AND o.acik_review)"
    " FROM pg_temp.lugat_durum o"
)
# Staged'de olmayan veritabani maddesi: hat silmez, yalniz sayar ve uyarir.
FAZLA: Final = (
    "SELECT count(*) FROM icerik.lugat_madde m WHERE m.source_id = %s::text AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_lugat s WHERE s.basliksoz = m.basliksoz)"
)
# Ekleme yalniz olmayan satirlari yazar; cakismada YALNIZ `origin = 'hat' AND status = 'aday'`
# satirin turetilmis sutunlari ve yalniz degeri farkliysa guncellenir. SET listesinde `tanim_tr`,
# `status`, `version`, `content_hash`, `origin`, `osmanlica_yazim`, `koken_dil` ve `ar_kok_id` yok.
UPSERT: Final = (
    "INSERT INTO icerik.lugat_madde (source_id, basliksoz, basliksoz_norm, tanim_tr, kaynaklar,"
    " duzey, status, origin, version, content_hash, data_version)"
    " SELECT %s::text, s.basliksoz, s.basliksoz_norm, s.tanim_tr, s.kaynaklar, s.duzey, 'aday',"
    " 'hat', %s::text, s.content_hash, s.data_version FROM pg_temp.staging_lugat s"
    " ORDER BY s.sira"
    " ON CONFLICT ON CONSTRAINT " + CONSTRAINT + " DO UPDATE SET"
    " kaynaklar = EXCLUDED.kaynaklar, duzey = EXCLUDED.duzey,"
    " data_version = EXCLUDED.data_version, basliksoz_norm = EXCLUDED.basliksoz_norm,"
    " updated_at = now()"
    " WHERE icerik.lugat_madde.origin = 'hat' AND icerik.lugat_madde.status = 'aday'"
    " AND (icerik.lugat_madde.kaynaklar, icerik.lugat_madde.duzey,"
    " icerik.lugat_madde.data_version, icerik.lugat_madde.basliksoz_norm)"
    " IS DISTINCT FROM (EXCLUDED.kaynaklar, EXCLUDED.duzey, EXCLUDED.data_version,"
    " EXCLUDED.basliksoz_norm)"
)
# Yalniz BU kosuda eklenen (durumu yazimdan once `m_id IS NULL`) ve acik review'u olmayan
# maddeler icin; var olan maddenin review satirina dokunulmaz.
INSERT_REVIEW: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onceki, onerilen,"
    " koken, oneren) SELECT 'lugat_madde', %s::text || ':' || o.basliksoz, 'tanim_tr', 'oner',"
    " NULL, o.onerilen, 'hat', 'hat' FROM pg_temp.lugat_durum o"
    " WHERE o.m_id IS NULL AND NOT o.acik_review ORDER BY o.sira"
)


def _say(conn: psycopg.Connection, sorgu: str, parametre: Sequence[object] = ()) -> int:
    satir = conn.execute(sorgu, parametre).fetchone()
    return int(satir[0]) if satir is not None else 0


def _staging_yukle(conn: psycopg.Connection, satirlar: Sequence[LugatSatiri]) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_lugat")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for sira, s in enumerate(satirlar, start=1):
            kopya.write_row(
                (
                    sira,
                    s.basliksoz,
                    s.basliksoz_norm,
                    s.tanim_tr,
                    Jsonb(s.kaynaklar),
                    s.duzey,
                    s.data_version,
                    s.content_hash,
                    Jsonb(s.onerilen),
                )
            )
    conn.execute(STAGING_ANALIZ)


def _sayilar(satirlar: Sequence[object], **degerler: int) -> Mapping[str, int]:
    return {"lugat_staging": len(satirlar), **{f"lugat_{a}": d for a, d in degerler.items()}}


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Lugat adaylarini ekler/gunceller ve her yeni madde icin `review` acar.

    Cagiran `conn.transaction()` icindedir (kilit `pg._yukle`de). Sayaclar modul belgesindedir.
    """
    satirlar_ham = h.lugat
    if not satirlar_ham:
        raise GirdiHatasi("lugat hazirligi yok")
    kaynak = satirlar_ham[0].source_id
    kaynak_denetle(kaynak)
    if kaynak in KAYNAKLI:  # A20.6b: ayri yol; asagisi Kelime-Frekans ve fikstur (degismedi)
        return yukle_kaynakli(
            conn, ctx, [s for s in satirlar_ham if isinstance(s, LugatKaynakSatiri)]
        )
    satirlar = [s for s in satirlar_ham if isinstance(s, LugatSatiri)]
    _staging_yukle(conn, satirlar)
    conn.execute("DROP TABLE IF EXISTS pg_temp.lugat_durum")
    conn.execute(DURUM, (kaynak, kaynak))
    sonuc = conn.execute(SAYAC).fetchone()  # toplama sorgusu her zaman bir satir doner
    sayac = [int(x) for x in sonuc] if sonuc is not None else [0] * 5
    eklenecek, atlanan, guncellenecek, review_acilacak, review_atlanacak = sayac
    fazla = _say(conn, FAZLA, (kaynak,))
    yazilan = conn.execute(UPSERT, (kaynak, VERSION)).rowcount
    if yazilan != eklenecek + guncellenecek:
        raise QaKaldi(
            f"lugat yazimi beklenenden farkli ({yazilan} satir, beklenen"
            f" {eklenecek + guncellenecek})"
        )
    review = conn.execute(INSERT_REVIEW, (kaynak,)).rowcount
    if review != review_acilacak:
        raise QaKaldi(f"acilan review ({review}) beklenenden farkli ({review_acilacak})")
    if atlanan:
        ctx.uyar(f"{atlanan} lugat maddesi origin=editor ya da status<>aday: dokunulmadi")
    if review_atlanacak:
        ctx.uyar(f"{review_atlanacak} yeni lugat maddesinde acik review var: yenisi acilmadi")
    if fazla:
        ctx.uyar(f"{fazla} lugat maddesi veritabaninda var, staged'de yok: silinmedi")
    return dict(
        _sayilar(
            satirlar,
            eklenen=eklenecek,
            ayni_kalan=len(satirlar) - eklenecek - guncellenecek - atlanan,
            guncellenen=guncellenecek,
            atlanan_editor=atlanan,
            review_acilan=review,
            review_acik_nedeniyle_atlanan=review_atlanacak,
            veritabaninda_fazla=fazla,
        )
    )


# --- lugat kaynaklari (A20.6b): satirlar, hazirlik ve yukleme ----------------------------------

# `kaynaklar` jsonb'sinin izinli anahtarlari (Kelime-Frekans satirlarindan farkli: karsilik
# bayragi ve eslesen Risale baslik sozu); anlam dizesi hicbir derinlikte yoktur.
KAYNAKLI_KAYNAKLAR_ANAHTARLARI: Final = frozenset(
    {"kelime_frekans_karsiligi", "risale_basliksoz", "siklik", "kitaplar"}
)
KAYNAKLI_ONERILEN_ANAHTARLARI: Final = frozenset({"kaynak", "siklik"})


@dataclass(frozen=True, slots=True)
class LugatKaynakSatiri:
    """Dogrulanmis `lugat.jsonl` satiri (lugat kaynagi); metin alanlari yalniz veritabanina gider.

    `onerilen` yalniz `duzey` 1-3 maddede dolu: `{kaynak, siklik}` (review icin).
    """

    source_id: str
    basliksoz: str
    anlam_no: int
    basliksoz_norm: str
    tanim_tr: str
    kaynaklar: dict[str, object]
    duzey: int
    data_version: str
    content_hash: str
    onerilen: dict[str, object] | None


def kaynakli_satir_coz(satir: Satir, source_id: str) -> LugatKaynakSatiri:
    """Tek lugat kaynagi `lugat.jsonl` satirini kati dogrular; iletiler yalniz satir no ve alan
    adi tasir. Girdi bicimi hatasi `GirdiHatasi` (cikis 2); `content_hash` uyusmazligi hat
    hatasidir: `QaKaldi` (cikis 1)."""
    yer = f"{satir.etiket}: satir {satir.no}"
    if set(satir.veri) != set(MADDE_ALANLARI_KAYNAK):
        raise GirdiHatasi(f"{yer}: alan kumesi beklenen degil")
    if satir.metin("source_id") != source_id:
        raise GirdiHatasi(f"{yer}: source_id --source ile ayni degil")
    baslik = satir.metin("basliksoz")
    if baslik == "" or "\x00" in baslik:
        raise GirdiHatasi(f"{yer}: basliksoz bos ya da NUL iceriyor")
    norm = satir.metin("basliksoz_norm")
    if norm == "" or "\x00" in norm or norm != basliksoz_norm(baslik):
        raise GirdiHatasi(f"{yer}: basliksoz_norm bos ya da basliksozle tutmuyor")
    if (
        satir.metin("status") != DURUM_ADAY
        or satir.metin("origin") != KOKEN_KAYNAK
        or satir.sayi("version") != SURUM_1
    ):
        raise GirdiHatasi(f"{yer}: durum aday, kok kaynak ve surum 1 olmali")
    for alan in BOS_ALANLAR:
        if satir.veri[alan] is not None:
            raise GirdiHatasi(f"{yer}: {alan} bos olmali (editor doldurur)")
    tanim = satir.metin("tanim_tr")
    if tanim.strip(" \t") == "" or "\x00" in tanim:
        raise GirdiHatasi(f"{yer}: tanim_tr bos ya da NUL iceriyor")
    anlam_no = satir.sayi("anlam_no")
    if not 1 <= anlam_no <= EN_COK_ANLAM_NO:
        raise GirdiHatasi(f"{yer}: anlam_no aralik disi")
    kaynaklar = satir.nesne("kaynaklar")
    karsilik = kaynaklar.get("kelime_frekans_karsiligi")
    if (
        not isinstance(karsilik, bool)
        or not set(kaynaklar) <= KAYNAKLI_KAYNAKLAR_ANAHTARLARI
        or _yasak_anahtar_var(kaynaklar)
        or _nul_var(kaynaklar)
    ):
        raise GirdiHatasi(f"{yer}: kaynaklar anahtar kumesi gecersiz (anlam dizesi girmez)")
    duzey = satir.sayi("duzey")
    onerilen: dict[str, object] | None = None
    if karsilik:
        siklik = _tam(kaynaklar.get("siklik"))
        kitaplar, soz = kaynaklar.get("kitaplar"), kaynaklar.get("risale_basliksoz")
        if (
            set(kaynaklar) != KAYNAKLI_KAYNAKLAR_ANAHTARLARI
            or siklik is None
            or siklik < 1
            or not isinstance(kitaplar, dict)
            or not kitaplar
            or not all((_tam(n) or 0) >= 1 for n in kitaplar.values())
            or siklik != sum(int(str(n)) for n in kitaplar.values())
            or not isinstance(soz, str)
            or soz == ""
        ):
            raise GirdiHatasi(f"{yer}: kaynaklar siklik, kitaplar ya da risale_basliksoz gecersiz")
        if not 1 <= duzey <= EN_SEYREK_DUZEY or duzey != duzey_hesapla(siklik):
            raise GirdiHatasi(f"{yer}: duzey sikliga gore hesaplananla ayni degil")
        onerilen = {"kaynak": source_id, "siklik": siklik}
    elif set(kaynaklar) != {"kelime_frekans_karsiligi"} or duzey != DUZEY_RISALEDE_YOK:
        raise GirdiHatasi(f"{yer}: karsiliksiz madde yalniz bayrak tasimali ve duzey 4 olmali")
    surum = satir.metin("data_version")
    if surum == "" or "\x00" in surum:
        raise GirdiHatasi(f"{yer}: data_version gecersiz")
    ozet = satir.metin("content_hash")
    if OZET_DESENI.fullmatch(ozet) is None:
        raise GirdiHatasi(f"{yer}: content_hash 64 haneli kucuk harfli onaltilik degil")
    try:
        beklenen = madde_hash(baslik, tanim)
    except UnicodeEncodeError:
        raise GirdiHatasi(f"{yer}: basliksoz ya da tanim UTF-8 olarak yazilamaz") from None
    if beklenen != ozet:  # hat hatasi: cikis 1 (cagiran yakalar)
        raise QaKaldi(f"staged content_hash maddeyle tutmuyor: satir {satir.no}")
    return LugatKaynakSatiri(
        source_id=source_id,
        basliksoz=baslik,
        anlam_no=anlam_no,
        basliksoz_norm=norm,
        tanim_tr=tanim,
        kaynaklar=dict(kaynaklar),
        duzey=duzey,
        data_version=surum,
        content_hash=ozet,
        onerilen=onerilen,
    )


def kaynakli_satirlari_coz(veri: bytes, source_id: str) -> list[LugatKaynakSatiri]:
    """Lugat kaynagi `lugat.jsonl` baytlarini kati okur; yinelenen (basliksoz, anlam_no) hata."""
    etiket = f"ingest {source_id} {LUGAT_ADI}"
    satirlar: list[LugatKaynakSatiri] = []
    gorulen: set[tuple[str, int]] = set()
    for s in satirlari_oku(veri, etiket):
        madde = kaynakli_satir_coz(s, source_id)
        anahtar = (madde.basliksoz, madde.anlam_no)
        if anahtar in gorulen:
            raise GirdiHatasi(f"{etiket}: satir {s.no}: yinelenen basliksoz ve anlam_no")
        gorulen.add(anahtar)
        satirlar.append(madde)
    return satirlar


def hazirla_kaynakli(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (lugat kaynagi).

    Kelime-Frekans yolundan farklari: ham girdiler kaynagin kendi dosyasi (rganeyev icin RNK
    dosyasi da) ve staged Kelime-Frekans girdisidir; `source` satiri yalniz kaynagin kendi ham
    dosyasindan dolar (tek dosyali kaynak kurali, `pg._alinma`).
    """
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    ingest = _ingest_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, ingest.manifest):
        raise GirdiHatasi("ingest calistirmasinin ciktilari saglam degil")
    yol, sha, veri = calismadan_baytlar(ctx, ingest)
    ingestler, ham = _zincir_denetle(ctx, [ingest], kaynak_idleri)
    qa_rapor_id = _qa_denetle(ctx, source_id, ingest.run_id, sha)  # dort kapi; kalirsa yukleme yok
    satirlar = kaynakli_satirlari_coz(veri, source_id)
    bildirimler = {slug: _bildirim(ingestler[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    girdiler = [lineage.Girdi(yol, sha, ingest.run_id)]
    girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[source_id]]
    kendi_ham = [d for d in ham[source_id] if d["yol"].startswith(f"raw/{source_id}/")]
    return Hazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=ingest.run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=[ingest],
        ingest=ingestler,
        ham={source_id: kendi_ham},
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=ctx.parmak_izi(girdiler),
        lugat=list(satirlar),
    )


STAGING_K: Final = (
    'CREATE TEMP TABLE staging_lugat_k (sira integer, basliksoz text COLLATE "C",'
    " anlam_no smallint, basliksoz_norm text, tanim_tr text, kaynaklar jsonb, duzey smallint,"
    " data_version text, content_hash char(64), onerilen jsonb) ON COMMIT DROP"
)
STAGING_K_COPY: Final = (
    "COPY pg_temp.staging_lugat_k (sira, basliksoz, anlam_no, basliksoz_norm, tanim_tr, kaynaklar,"
    " duzey, data_version, content_hash, onerilen) FROM STDIN"
)
STAGING_K_ANALIZ: Final = "ANALYZE pg_temp.staging_lugat_k"
# Her staged maddenin veritabani durumu INSERT'ten ONCE tek geciste bir gecici tabloya yazilir.
# `var_review`: ayni hedef icin HERHANGI bir review (acik ya da kapali) var mi; `farkli`: turetilmis
# sutunlar degisti mi; `metin_farkli`: kaynak tanimi/ozeti veritabanindakinden farkli mi.
DURUM_K: Final = (
    "CREATE TEMP TABLE lugat_durum_k ON COMMIT DROP AS"
    " WITH rv AS (SELECT r.hedef_anahtar FROM icerik.review r"
    " WHERE r.hedef_tablo = 'lugat_madde' AND starts_with(r.hedef_anahtar, %s::text || ':')"
    " GROUP BY r.hedef_anahtar)"
    " SELECT s.*, m.id AS m_id, m.origin AS m_origin, m.status::text AS m_durum,"
    " (m.kaynaklar, m.duzey, m.data_version, m.basliksoz_norm)"
    " IS DISTINCT FROM (s.kaynaklar, s.duzey, s.data_version, s.basliksoz_norm) AS farkli,"
    " (m.tanim_tr, m.content_hash) IS DISTINCT FROM (s.tanim_tr, s.content_hash) AS metin_farkli,"
    " rv.hedef_anahtar IS NOT NULL AS var_review FROM pg_temp.staging_lugat_k s"
    " LEFT JOIN icerik.lugat_madde m ON m.source_id = %s::text AND m.basliksoz = s.basliksoz"
    " AND m.anlam_no = s.anlam_no"
    " LEFT JOIN rv ON rv.hedef_anahtar = %s::text || ':' || s.anlam_no::text || ':' || s.basliksoz"
)
# Yazilabilir satir: yok (yeni) ya da `origin <> 'editor' AND status = 'aday'`.
YAZILABILIR: Final = "(o.m_id IS NULL OR (o.m_origin <> 'editor' AND o.m_durum = 'aday'))"
# eklenecek, editor/aday-olmayan nedeniyle atlanan, guncellenecek, metin degisen, acilacak review,
# review var nedeniyle atlanan, review gerektirmeyen (duzey 4) (INSERT'ten ONCE).
SAYAC_K: Final = (
    "SELECT count(*) FILTER (WHERE o.m_id IS NULL),"
    " count(*) FILTER (WHERE o.m_id IS NOT NULL"
    " AND NOT (o.m_origin <> 'editor' AND o.m_durum = 'aday')),"
    " count(*) FILTER (WHERE o.m_origin <> 'editor' AND o.m_durum = 'aday' AND o.farkli),"
    " count(*) FILTER (WHERE o.m_origin <> 'editor' AND o.m_durum = 'aday' AND o.metin_farkli),"
    f" count(*) FILTER (WHERE o.duzey BETWEEN 1 AND 3 AND NOT o.var_review AND {YAZILABILIR}),"
    f" count(*) FILTER (WHERE o.duzey BETWEEN 1 AND 3 AND o.var_review AND {YAZILABILIR}),"
    " count(*) FILTER (WHERE o.duzey = 4)"
    " FROM pg_temp.lugat_durum_k o"
)
# Staged'de olmayan veritabani maddesi: hat silmez, yalniz sayar ve uyarir.
FAZLA_K: Final = (
    "SELECT count(*) FROM icerik.lugat_madde m WHERE m.source_id = %s::text AND NOT EXISTS"
    " (SELECT 1 FROM pg_temp.staging_lugat_k s WHERE s.basliksoz = m.basliksoz"
    " AND s.anlam_no = m.anlam_no)"
)
# Ekleme yeni satirlari yazar; cakismada YALNIZ `origin <> 'editor' AND status = 'aday'` satirin
# turetilmis sutunlari ve yalniz degeri farkliysa guncellenir. SET listesinde `tanim_tr`,
# `content_hash`, `status`, `version`, `origin`, `anlam_no`, `osmanlica_yazim`, `koken_dil` ve
# `ar_kok_id` yok: kaynak satirindaki tanim var olan satirda degismez.
UPSERT_K: Final = (
    "INSERT INTO icerik.lugat_madde (source_id, basliksoz, anlam_no, basliksoz_norm, tanim_tr,"
    " kaynaklar, duzey, status, origin, version, content_hash, data_version)"
    " SELECT %s::text, s.basliksoz, s.anlam_no, s.basliksoz_norm, s.tanim_tr, s.kaynaklar,"
    " s.duzey, 'aday', 'kaynak', %s::text, s.content_hash, s.data_version"
    " FROM pg_temp.staging_lugat_k s ORDER BY s.sira"
    " ON CONFLICT ON CONSTRAINT " + CONSTRAINT + " DO UPDATE SET"
    " kaynaklar = EXCLUDED.kaynaklar, duzey = EXCLUDED.duzey,"
    " data_version = EXCLUDED.data_version, basliksoz_norm = EXCLUDED.basliksoz_norm,"
    " updated_at = now()"
    " WHERE icerik.lugat_madde.origin <> 'editor' AND icerik.lugat_madde.status = 'aday'"
    " AND (icerik.lugat_madde.kaynaklar, icerik.lugat_madde.duzey,"
    " icerik.lugat_madde.data_version, icerik.lugat_madde.basliksoz_norm)"
    " IS DISTINCT FROM (EXCLUDED.kaynaklar, EXCLUDED.duzey, EXCLUDED.data_version,"
    " EXCLUDED.basliksoz_norm)"
)
# Yalniz `duzey` 1-3, hicbir review'u olmayan ve yazilabilir (yeni ya da editor olmayan aday)
# maddeler icin; var olan review'a (acik ya da kapali) dokunulmaz, editor karari yeniden acilmaz.
INSERT_REVIEW_K: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onceki, onerilen,"
    " koken, oneren) SELECT 'lugat_madde',"
    " %s::text || ':' || o.anlam_no::text || ':' || o.basliksoz, 'tanim_tr', 'oner',"
    " NULL, o.onerilen, 'hat', 'hat' FROM pg_temp.lugat_durum_k o"
    f" WHERE o.duzey BETWEEN 1 AND 3 AND NOT o.var_review AND {YAZILABILIR} ORDER BY o.sira"
)


def _kaynakli_staging_yukle(
    conn: psycopg.Connection, satirlar: Sequence[LugatKaynakSatiri]
) -> None:
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_lugat_k")
    conn.execute(STAGING_K)
    with conn.cursor() as imlec, imlec.copy(STAGING_K_COPY) as kopya:
        for sira, s in enumerate(satirlar, start=1):
            kopya.write_row(
                (
                    sira,
                    s.basliksoz,
                    s.anlam_no,
                    s.basliksoz_norm,
                    s.tanim_tr,
                    Jsonb(s.kaynaklar),
                    s.duzey,
                    s.data_version,
                    s.content_hash,
                    Jsonb(s.onerilen) if s.onerilen is not None else None,
                )
            )
    conn.execute(STAGING_K_ANALIZ)


def yukle_kaynakli(
    conn: psycopg.Connection, ctx: RunContext, satirlar: Sequence[LugatKaynakSatiri]
) -> dict[str, int]:
    """Tanimli lugat maddelerini ekler/gunceller; `duzey` 1-3 maddeler icin `review` acar.

    Cagiran `conn.transaction()` icindedir (kilit `pg._yukle`de). Sayaclar modul belgesindedir.
    """
    if not satirlar:
        raise GirdiHatasi("lugat hazirligi yok")
    kaynak = satirlar[0].source_id
    if kaynak not in KAYNAKLI:
        raise GirdiHatasi(f"{kaynak}: lugat kaynagi degil")
    _kaynakli_staging_yukle(conn, satirlar)
    conn.execute("DROP TABLE IF EXISTS pg_temp.lugat_durum_k")
    conn.execute(DURUM_K, (kaynak, kaynak, kaynak))
    sonuc = conn.execute(SAYAC_K).fetchone()  # toplama sorgusu her zaman bir satir doner
    sayac = [int(x) for x in sonuc] if sonuc is not None else [0] * 7
    eklenecek, atlanan, guncellenecek, metin_degisti, review_acilacak, review_var, gerekmeyen = (
        sayac
    )
    fazla = _say(conn, FAZLA_K, (kaynak,))
    yazilan = conn.execute(UPSERT_K, (kaynak, VERSION)).rowcount
    if yazilan != eklenecek + guncellenecek:
        raise QaKaldi(
            f"lugat yazimi beklenenden farkli ({yazilan} satir, beklenen"
            f" {eklenecek + guncellenecek})"
        )
    review = conn.execute(INSERT_REVIEW_K, (kaynak,)).rowcount
    if review != review_acilacak:
        raise QaKaldi(f"acilan review ({review}) beklenenden farkli ({review_acilacak})")
    if atlanan:
        ctx.uyar(f"{atlanan} lugat maddesi origin=editor ya da status<>aday: dokunulmadi")
    if metin_degisti:
        ctx.uyar(
            f"{metin_degisti} lugat maddesinde kaynak tanimi veritabanindakinden farkli:"
            " tanim degismedi (kaynak dosyasi degismis olabilir)"
        )
    if review_var:
        ctx.uyar(f"{review_var} lugat maddesinde review zaten var: yenisi acilmadi")
    if fazla:
        ctx.uyar(f"{fazla} lugat maddesi veritabaninda var, staged'de yok: silinmedi")
    return dict(
        _sayilar(
            satirlar,
            eklenen=eklenecek,
            ayni_kalan=len(satirlar) - eklenecek - guncellenecek - atlanan,
            guncellenen=guncellenecek,
            atlanan_editor=atlanan,
            metin_degisti=metin_degisti,
            review_acilan=review,
            review_var_nedeniyle_atlanan=review_var,
            review_gerektirmeyen=gerekmeyen,
            veritabaninda_fazla=fazla,
        )
    )


__all__ = [
    "KAYNAKLAR",
    "KAYNAKLI",
    "LugatKaynakSatiri",
    "LugatSatiri",
    "calismadan_baytlar",
    "calismadan_oku",
    "hazirla",
    "hazirla_kaynakli",
    "kaynak_denetle",
    "kaynakli_satir_coz",
    "kaynakli_satirlari_coz",
    "satir_coz",
    "satirlari_coz",
    "yukle",
    "yukle_kaynakli",
]
