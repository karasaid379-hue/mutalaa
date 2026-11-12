"""`export pg --source quranwbw-tr`: `lemma_gloss` adaylari ve `review` satirlari (A17.6, K-50).

`export/pg_sure_adlari.py` ve `pg_meal.py` deseniyle ayni akis (dosya onkosullari -> tek
veritabani islemi, advisory kilit). Dosya tarafi: kaynak kaydi (G-KAY), son `anchor`
(`enrich glosses --wave N`) calismasi (`glosses.jsonl`), zincir (anchor -> ingest quranwbw-tr ve
anchor qac-morfoloji -> ingest qac, anchor tanzil-ust-veri ...; uc kaynagin ingest'i en sonuncu
olmali), QA raporu (G-KAY, G-BUT, G-CAP) ve QAC calismasinin da QA kabulu, satirlarin kati
okunmasi. `source` satiri YALNIZ `quranwbw-tr` icindir (`export/pg.py` ortak kodu).

YAZMA KURALI (K-50 madde 5, Editoryal veritabani §5): YALNIZ EKLER.

* Lemma icin `lemma_gloss` satiri yoksa VE o lemma icin hicbir durumda `review` kaydi yoksa:
  `status = 'aday'`, `origin = 'kaynak:quranwbw-tr'`, `version = '1'`, `content_hash =
  sha256(utf-8(anlam_kisa))` (`anchor.metin.content_hash`), `kuran_anlamlari` en cok 3 madde,
  `turkce_es_kelime` bos, `yalnizca_etimolojik = false`; ayni lemma icin bir `review`:
  `hedef_tablo = 'lemma_gloss'`, `hedef_anahtar = '{lemma_id}'`, `alan = 'anlam_kisa'`, `eylem =
  'oner'`, `koken = 'hat'`, `oneren = 'hat'`, `onceki` NULL, `onerilen = {anlam_kisa, dagilim,
  baskin_pay}`, `guven = baskin_pay`; `yz_modeli` ve `yz_kaydi` NULL. Kayitlar dalga ve `sira`
  sirasiyla eklenir (kuyruk dalga sirasini izler).
* Var olan `lemma_gloss` satirina (aday, onayli ya da red) ve var olan `review` kaydina DOKUNULMAZ
  (editorun degeri uzerine yazilmaz). Staged degeri veritabanindakinden farkliysa satir
  degistirilmez, `gloss_mevcut_farkli` sayacina girer. Acik (ya da baska durumda) `review` kaydi
  olan lemma atlanir (`review_nedeniyle_atlanan`). Hicbir satir silinmez.
* Yalniz secilen dalgalarin lemmalari yuklenir (staged `glosses.jsonl` onu tasir); her staged
  lemmanin `lemma` ve `lemma_dalga` satiri veritabaninda bulunmali (yoksa cikis 2: once
  `export pg --source qac-morfoloji`) ve veritabanindaki dalga staged dalgayla ayni olmali
  (degilse cikis 1: `enrich glosses` yeniden kosulmali).
* `--dry-run` hicbir sey yazmaz. Ikinci kosu 0 degisiklik verir.

Iletiler yalniz sayi ve `qac_ref` tasir; anlam metni yazilmaz. Sayaclar: `gloss_staging`,
`gloss_eklenen`, `gloss_degismeyen`, `gloss_mevcut`, `gloss_korunan` (aday olmayan),
`gloss_mevcut_farkli`, `review_eklenen`, `review_nedeniyle_atlanan`, `tutarli`, `tutarsiz`.
"""

import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.anchor.metin import kanonik_metin
from mutalaa_pipeline.enrich.glosses import (
    ESIK_PAY,
    ESIK_PAYDA,
    GLOSSES_ADI,
    KURAN_ANLAMI_SINIRI,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import (
    Hazirlik,
    _anchor_calismasi,
    _bildirim,
    _capalar,
    _manifest_ozet,
    _qa_denetle,
    _zincir,
    _zincir_denetle,
)
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.ingest.qac import KAYNAK as QAC_KAYNAGI
from mutalaa_pipeline.ingest.quranwbw import KAYNAK
from mutalaa_pipeline.ingest.tanzil_ust_veri import KAYNAK as UST_VERI
from mutalaa_pipeline.lineage import KELIMELER_ADI
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_oku
from mutalaa_pipeline.zincir import ANCHOR_ADIMI

ORIGIN: Final = f"kaynak:{KAYNAK}"
VERSION: Final = "1"
PAY_BASAMAK: Final = 6
SON_DALGA: Final = 4
GLOSS_ALANLARI: Final = frozenset(
    {
        "qac_ref",
        "dalga",
        "sira",
        "toplam",
        "baskin_sayi",
        "anlam_kisa",
        "dagilim",
        "kuran_anlamlari",
        "tutarsiz_hazir_anlam",
        "source_id",
        "data_version",
    }
)


@dataclass(frozen=True)
class GlossSatiri:
    qac_ref: str
    dalga: int
    sira: int
    toplam: int
    baskin_sayi: int
    anlam_kisa: str
    dagilim: tuple[tuple[str, int], ...]
    kuran_anlamlari: tuple[str, ...]
    tutarsiz: bool

    @property
    def baskin_pay(self) -> float:
        return round(self.baskin_sayi / self.toplam, PAY_BASAMAK)

    def onerilen(self) -> dict[str, object]:
        """`review.onerilen`: `{anlam_kisa, dagilim: [{anlam, sayi}], baskin_pay}`."""
        return {
            "anlam_kisa": self.anlam_kisa,
            "dagilim": [{"anlam": a, "sayi": n} for a, n in self.dagilim],
            "baskin_pay": self.baskin_pay,
        }


@dataclass
class GlossHazirlik(Hazirlik):
    """`Hazirlik` + staged aday satirlari."""

    gloss_adaylari: list[GlossSatiri] = field(default_factory=list)


# --- satirlari okuma (kati) ------------------------------------------------------------------


def _metin(satir: Satir, alan: str, deger: object) -> str:
    if not isinstance(deger, str) or deger == "" or "\x00" in deger:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: {alan} bos metin degil")
    try:
        kanonik = kanonik_metin(deger) == deger and unicodedata.is_normalized("NFC", deger)
    except UnicodeEncodeError:
        kanonik = False
    if not kanonik:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: {alan} kanonik (NFC) metin degil")
    return deger


def _tam(satir: Satir, alan: str, deger: object, en_az: int) -> int:
    if not isinstance(deger, int) or isinstance(deger, bool) or deger < en_az:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: {alan} gecersiz tam sayi")
    return deger


def _dagilim(satir: Satir) -> tuple[tuple[str, int], ...]:
    ham = satir.veri.get("dagilim")
    if not isinstance(ham, list) or not ham:
        raise GirdiHatasi(f"{satir.etiket} satir {satir.no}: dagilim bos ya da liste degil")
    sonuc: list[tuple[str, int]] = []
    for oge in ham:
        if not isinstance(oge, dict) or set(oge) != {"anlam", "sayi"}:
            raise GirdiHatasi(
                f"{satir.etiket} satir {satir.no}: dagilim ogesi {{anlam, sayi}} degil"
            )
        sonuc.append((_metin(satir, "anlam", oge["anlam"]), _tam(satir, "sayi", oge["sayi"], 1)))
    anahtar = [(-n, a.encode("utf-8")) for a, n in sonuc]
    if anahtar != sorted(anahtar) or len({a for a, _ in sonuc}) != len(sonuc):
        raise GirdiHatasi(
            f"{satir.etiket} satir {satir.no}: dagilim sayiya gore azalan, yazimlar tekil degil"
        )
    return tuple(sonuc)


def gloss_satirlarini_oku(veri: bytes, izinli_dalgalar: frozenset[int]) -> list[GlossSatiri]:
    """`glosses.jsonl` baytlarini kati okur; hata iletisi yalniz satir ve alan adi tasir."""
    satirlar: list[GlossSatiri] = []
    gorulen: set[str] = set()
    surum = ""
    for s in satirlari_oku(veri, GLOSSES_ADI):
        if set(s.veri) != GLOSS_ALANLARI:
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: alan kumesi beklenen degil")
        ref = s.metin("qac_ref")
        if ref == "" or ref in gorulen:
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: qac_ref bos ya da yinelenen")
        gorulen.add(ref)
        if s.metin("source_id") != KAYNAK:
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: source_id {KAYNAK} degil")
        veri_surumu = s.metin("data_version")
        if veri_surumu == "" or (surum and veri_surumu != surum):
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: data_version gecersiz ya da tutarsiz")
        surum = veri_surumu
        dalga = _tam(s, "dalga", s.veri["dalga"], 0)
        if dalga > SON_DALGA or dalga not in izinli_dalgalar:
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: dalga secilen dalgalarin disinda")
        toplam = _tam(s, "toplam", s.veri["toplam"], 1)
        baskin = _tam(s, "baskin_sayi", s.veri["baskin_sayi"], 1)
        dagilim = _dagilim(s)
        kisa = _metin(s, "anlam_kisa", s.veri["anlam_kisa"])
        ham_kuran = s.veri["kuran_anlamlari"]
        if (
            not isinstance(ham_kuran, list)
            or not 1 <= len(ham_kuran) <= KURAN_ANLAMI_SINIRI
            or len(set(map(str, ham_kuran))) != len(ham_kuran)
        ):
            raise GirdiHatasi(
                f"{GLOSSES_ADI} satir {s.no}: kuran_anlamlari 1..3 tekil madde olmali"
            )
        kuran = tuple(_metin(s, "kuran_anlamlari", m) for m in ham_kuran)
        if sum(n for _, n in dagilim) != toplam or baskin > toplam:
            raise GirdiHatasi(
                f"{GLOSSES_ADI} satir {s.no}: dagilim toplami ya da baskin_sayi tutmuyor"
            )
        if kisa not in {a for a, _ in dagilim}:
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: anlam_kisa dagilimda yok")
        tutarsiz = s.veri["tutarsiz_hazir_anlam"]
        if not isinstance(tutarsiz, bool) or tutarsiz != (baskin * ESIK_PAYDA < toplam * ESIK_PAY):
            raise GirdiHatasi(f"{GLOSSES_ADI} satir {s.no}: tutarsiz_hazir_anlam esikle tutmuyor")
        satirlar.append(
            GlossSatiri(
                ref,
                dalga,
                _tam(s, "sira", s.veri["sira"], 1),
                toplam,
                baskin,
                kisa,
                dagilim,
                kuran,
                tutarsiz,
            )
        )
    if not satirlar:
        raise GirdiHatasi(f"{GLOSSES_ADI} bos")
    return satirlar


def _secilen_dalgalar(manifest: dict[str, object]) -> frozenset[int]:
    ayrintilar = manifest.get("ayrintilar")
    deger = ayrintilar.get("secilen_dalgalar") if isinstance(ayrintilar, dict) else None
    if (
        not isinstance(deger, list)
        or not deger
        or not all(
            isinstance(x, int) and not isinstance(x, bool) and 0 <= x <= SON_DALGA for x in deger
        )
    ):
        raise GirdiHatasi("anchor manifestinde secilen_dalgalar yok ya da gecersiz")
    return frozenset(int(x) for x in deger)


# --- hazirlik --------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (QuranWBW kaynagi)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    ctx.require_sources((QAC_KAYNAGI, UST_VERI))  # zincirin oteki kaynaklarinin kaydi da gecerli
    anchor_run_id, klasor, manifest = _anchor_calismasi(ctx, source_id, run)
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("anchor calistirmasinin ciktilari saglam degil")
    bayt, sha = _dosya_oku(klasor, manifest, GLOSSES_ADI)
    zincir = _zincir(ctx, manifest)
    ingest, ham = _zincir_denetle(ctx, zincir, (source_id, QAC_KAYNAGI, UST_VERI))
    qa_rapor_id = _qa_denetle(ctx, source_id, anchor_run_id, sha)
    qac = [r for r in zincir if r.adim == ANCHOR_ADIMI and r.source_id == QAC_KAYNAGI]
    if len(qac) != 1:
        raise GirdiHatasi(f"zincirde {QAC_KAYNAGI} icin tek anchor calistirmasi olmali")
    son = lineage.son_basarili(ctx.staged_kaynak_dizini(QAC_KAYNAGI), ANCHOR_ADIMI)
    if son is None or son[0] != qac[0].run_id:
        raise QaKaldi(f"zincirdeki {QAC_KAYNAGI} anchor calistirmasi en son degil")
    kelime_ozeti = _manifest_ozet(qac[0].manifest, KELIMELER_ADI)
    if kelime_ozeti is None:
        raise GirdiHatasi(f"{QAC_KAYNAGI} anchor manifestinde {KELIMELER_ADI} ozeti yok")
    _qa_denetle(ctx, QAC_KAYNAGI, qac[0].run_id, kelime_ozeti)  # QAC kapilari da gecmis olmali
    adaylar = gloss_satirlarini_oku(bayt, _secilen_dalgalar(manifest))
    bildirimler = {slug: _bildirim(ingest[slug], kaynaklar[slug]) for slug in kaynak_idleri}
    yol = lineage.goreli_yol(ctx.veri_kok, klasor / GLOSSES_ADI)
    girdiler = [lineage.Girdi(yol, sha, anchor_run_id)]
    for slug in kaynak_idleri:
        girdiler += [lineage.Girdi(d["yol"], d["sha256"]) for d in ham[slug]]
    return GlossHazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=anchor_run_id,
        units_yol=yol,
        units_sha256=sha,
        satirlar=[],
        zincir=zincir,
        ingest=ingest,
        ham=ham,
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=bildirimler,
        parmak=ctx.parmak_izi(girdiler),
        gloss_adaylari=adaylar,
    )


# --- veritabani ------------------------------------------------------------------------------

STAGING: Final = (
    "CREATE TEMP TABLE staging_gloss (lemma_id integer, qac_ref text, anlam_kisa text,"
    " kuran_anlamlari jsonb, content_hash char(64), onerilen jsonb, guven real, dalga smallint,"
    " sira integer) ON COMMIT DROP"
)
STAGING_COPY: Final = (
    "COPY pg_temp.staging_gloss (lemma_id, qac_ref, anlam_kisa, kuran_anlamlari, content_hash,"
    " onerilen, guven, dalga, sira) FROM STDIN"
)
# Her staged lemmanin gloss ve review durumu TEK geciste (review gruplanarak) bir gecici tabloya
# yazilir; sayaclar ve ekleme bu tabloyu okur: ekleme ONCEKI durumdan karar verir.
DURUM: Final = (
    "CREATE TEMP TABLE gloss_durum ON COMMIT DROP AS"
    " WITH rv AS (SELECT r.hedef_anahtar, bool_or(r.durum = 'acik') AS acik FROM icerik.review r"
    " WHERE r.hedef_tablo = 'lemma_gloss' GROUP BY r.hedef_anahtar)"
    " SELECT s.*, g.lemma_id AS g_var, g.status::text AS g_durum, g.anlam_kisa AS g_anlam,"
    " g.content_hash AS g_hash, rv.hedef_anahtar IS NOT NULL AS review_var,"
    " COALESCE(rv.acik, false) AS review_acik FROM pg_temp.staging_gloss s"
    " LEFT JOIN icerik.lemma_gloss g ON g.lemma_id = s.lemma_id"
    " LEFT JOIN rv ON rv.hedef_anahtar = s.lemma_id::text"
)
YENI: Final = "o.g_var IS NULL AND NOT o.review_var"
INSERT_GLOSS: Final = (
    "INSERT INTO icerik.lemma_gloss (lemma_id, anlam_kisa, kuran_anlamlari, turkce_es_kelime,"
    " yalnizca_etimolojik, status, origin, version, content_hash) SELECT o.lemma_id, o.anlam_kisa,"
    " o.kuran_anlamlari, NULL, false, 'aday', %s, %s, o.content_hash FROM pg_temp.gloss_durum o"
    " WHERE " + YENI + " ORDER BY o.dalga, o.sira, o.lemma_id"
)
INSERT_REVIEW: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onceki, onerilen, guven,"
    " koken, oneren) SELECT 'lemma_gloss', o.lemma_id::text, 'anlam_kisa', 'oner', NULL,"
    " o.onerilen, o.guven, 'hat', 'hat' FROM pg_temp.gloss_durum o WHERE "
    + YENI
    + " ORDER BY o.dalga, o.sira, o.lemma_id"
)
SAY_MEVCUT: Final = "SELECT count(*) FROM pg_temp.gloss_durum o WHERE o.g_var IS NOT NULL"
SAY_KORUNAN: Final = (
    "SELECT count(*) FROM pg_temp.gloss_durum o WHERE o.g_var IS NOT NULL AND o.g_durum <> 'aday'"
)
SAY_FARKLI: Final = (
    "SELECT count(*) FROM pg_temp.gloss_durum o WHERE o.g_var IS NOT NULL"
    " AND (o.g_anlam, o.g_hash) IS DISTINCT FROM (o.anlam_kisa, o.content_hash)"
)
SAY_REVIEW_ATLANAN: Final = (
    "SELECT count(*) FROM pg_temp.gloss_durum o WHERE o.g_var IS NULL AND o.review_var"
)
LEMMA_KIMLIKLERI: Final = (
    "SELECT l.qac_ref, l.id, d.dalga FROM icerik.lemma l"
    " LEFT JOIN icerik.lemma_dalga d ON d.lemma_id = l.id"
    " WHERE l.lang = 'ar' AND l.qac_ref = ANY(%s)"
)


def _say(conn: psycopg.Connection, sorgu: str) -> int:
    satir = conn.execute(sorgu).fetchone()
    return int(satir[0]) if satir is not None else 0


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Yeni adaylari `lemma_gloss` + `review` olarak ekler; var olan satira dokunmaz.

    Cagiran `conn.transaction()` icindedir. Sayaclar modul belgesindedir.
    """
    if not isinstance(h, GlossHazirlik):
        raise TypeError("QuranWBW yuklemesi GlossHazirlik ister")
    adaylar = h.gloss_adaylari
    bulunan: dict[str, tuple[int, int | None]] = {
        str(ref): (int(kimlik), None if dalga is None else int(dalga))
        for ref, kimlik, dalga in conn.execute(
            LEMMA_KIMLIKLERI, ([a.qac_ref for a in adaylar],)
        ).fetchall()
    }
    yok = [a.qac_ref for a in adaylar if a.qac_ref not in bulunan]
    if yok:
        raise GirdiHatasi(
            f"QAC lemmasi veritabaninda yok ({len(yok)}): {_capalar(yok)};"
            " once export pg --source qac-morfoloji"
        )
    dalgasiz = [a.qac_ref for a in adaylar if bulunan[a.qac_ref][1] is None]
    if dalgasiz:
        raise GirdiHatasi(f"lemma_dalga satiri yok ({len(dalgasiz)}): {_capalar(dalgasiz)}")
    farkli = [a.qac_ref for a in adaylar if bulunan[a.qac_ref][1] != a.dalga]
    if farkli:
        raise QaKaldi(
            f"veritabanindaki dalga staged dalgayla farkli ({len(farkli)}): {_capalar(farkli)};"
            " enrich glosses yeniden kosulmali"
        )
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_gloss")
    conn.execute(STAGING)
    with conn.cursor() as imlec, imlec.copy(STAGING_COPY) as kopya:
        for a in adaylar:
            pay = a.baskin_pay
            kopya.write_row(
                (
                    bulunan[a.qac_ref][0],
                    a.qac_ref,
                    a.anlam_kisa,
                    Jsonb(list(a.kuran_anlamlari)),
                    content_hash(a.anlam_kisa),
                    Jsonb(a.onerilen()),
                    pay,
                    a.dalga,
                    a.sira,
                )
            )
    conn.execute("DROP TABLE IF EXISTS pg_temp.gloss_durum")
    conn.execute(DURUM)
    mevcut = _say(conn, SAY_MEVCUT)
    korunan = _say(conn, SAY_KORUNAN)
    mevcut_farkli = _say(conn, SAY_FARKLI)
    atlanan = _say(conn, SAY_REVIEW_ATLANAN)
    gloss = conn.execute(INSERT_GLOSS, (ORIGIN, VERSION)).rowcount
    review = conn.execute(INSERT_REVIEW).rowcount
    if gloss != review:
        raise QaKaldi(f"eklenen lemma_gloss ({gloss}) ve review ({review}) sayilari esit degil")
    if mevcut_farkli:
        ctx.uyar(f"{mevcut_farkli} lemmada lemma_gloss staged ile farkli (hat yazmaz)")
    if atlanan:
        ctx.uyar(f"{atlanan} lemma review kaydi nedeniyle atlandi")
    tutarsiz = sum(1 for a in adaylar if a.tutarsiz)
    return {
        "gloss_staging": len(adaylar),
        "gloss_eklenen": gloss,
        "gloss_degismeyen": len(adaylar) - gloss,
        "gloss_mevcut": mevcut,
        "gloss_korunan": korunan,
        "gloss_mevcut_farkli": mevcut_farkli,
        "review_eklenen": review,
        "review_nedeniyle_atlanan": atlanan,
        "tutarli": len(adaylar) - tutarsiz,
        "tutarsiz": tutarsiz,
    }
