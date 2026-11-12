"""`export pg --source kaikki-tr`: Turkce lemma, `review`, `tr_root_index` ve `tr_form` (A18.2).

`--source` adi `kaikki-tr`dir: Turkce lemma satirlarinin `source_id` degeri ve staged klasoru
(`staged/kaikki-tr/{run_id}/`, adim `enrich`). Iki meal (`elmalili-meal`, `elmalili-sade-meal`)
kayitlari ve `qac-morfoloji` kokleri yuklemeden once veritabaninda bulunmalidir. Akis
(`export/pg_qac.py` deseni): dosya onkosullari (kaynak kaydi, son `enrich` calismasi ve
ciktilari, QA raporu: G-KAY, G-BUT, G-CAP) -> tek veritabani islemi (advisory kilit, `source`
satiri `export/pg.py` ortak kodunda). Hat meal birimlerinin METNINE hic yazmaz (K-49); metin
yalniz okunur.

LEMMA KURALLARI (K-51 madde 9)

* `lang = 'tr'`, `text = text_clean = lemma` (lemma kucuk harf ve dar anahtara esit; bu yuzden
  `text_clean` DAR anahtardir: genis anahtar ayirt edilmesi gereken lemmalari cakistirir),
  `origin = 'kaikki'`, `source_id = 'kaikki-tr'`. Kimlik kalicidir (`kimlik_ata`): var olan
  `(lang, text_clean)` satirinin kimligi korunur, yeni satira siradaki numara verilir.
* `onayli_otomatik` -> `status = 'onayli'`, `onay_yolu = 'otomatik'`, `root_id`, `ar_lemma_id`
  (etimonla tek QAC lemmasi eslesmisse), `etymological_only = false`, `kanit` (`qac` icine
  `root_id` ve `ar_lemma_id` eklenir). `aday` -> yalniz bir kok onerisi varsa satir acilir:
  `status = 'aday'`, `onay_yolu` NULL, `root_id` NULL (oneri `kanit` ve `review` icindedir).
  Kok onerisi olmayan aday ve `kok_yok` icin satir ACILMAZ (rapora sayilir).
* Hat yalniz kendi uretimini yeniden degerlendirir: `onay_yolu = 'editor'` ya da `origin =
  'editor'` satira ve `status = 'red'` satira HIC dokunulmaz (geri acilmaz). `onay_yolu =
  'otomatik'` satir: karar ayni kalirsa yalniz turetilmis sutunlar (`root_id`, `ar_lemma_id`,
  `kanit`, `freq`, `data_version`) guncellenir; kosul artik saglanmiyorsa (karar `aday` ya da
  `kok_yok`, ya da staged'de yok) satir `aday`a doner, `onay_yolu` NULL olur ve `review` acilir.
  Hat adayi (`origin = 'kaikki'`, `status = 'aday'`): `kanit` ve `freq` yenilenir; hicbir `review`
  kaydi yoksa ve karar `onayli_otomatik` ise `onayli/otomatik`e yukseltilir. Her UPDATE, es
  zamanli bir editor karari ezilmesin diye durum kosulunu tasir.

REVIEW KURALLARI: `hedef_tablo = 'lemma'`, `hedef_anahtar = lemma_id`, `alan = 'kok_eslemesi'`,
`eylem = 'oner'`, `koken = 'hat'`, `oneren = 'hat'`, `guven` yok. `onerilen = {root_id,
ar_lemma_id, etymological_only: false, neden, kanit_ozeti}`. Acilir: (a) staged `review_onerilir`
(aday + kok onerisi + siklik >= `--min-freq`) olan ve HICBIR durumda `review` kaydi olmayan lemma;
(b) otomatikten adaya donen lemma (acik `review` yoksa; `onceki` eski deger). Kayitlar toplam
sikliga gore AZALAN sirada eklenir (kimlik sirasi kuyruk sirasidir).

`tr_root_index` ve `tr_form` her yuklemede YENIDEN URETILIR: yalniz `status = 'onayli'` (otomatik
ve editor) ve kokü olan Turkce lemmalardan; aralikliklar veritabanindaki birimin GUNCEL metninden
ayni belirtecleyiciyle (`enrich/tr_roots/bolme.py`) hesaplanir ve tur duzeyi karar tablosu
(yuzey bicim -> lemma) uygulanir. Aralik kod noktasidir ve yari aciktir; `unit_hash` birimin
`content_hash` degerinin ilk 16 hanesidir. Hedef tablolar (`meal:{eser}:` capali satirlar,
`tr_form` icin Turkce lemmalarin satirlari) staged ile FARK ALINARAK esitlenir: eksik satir
eklenir, fazla satir silinir, degisen satir guncellenir (ayni islemde); ikinci kosu 0 degisiklik
verir. Yukleme sonunda G-CAP uzantisi (`qa/checks/tr_roots.span_hatalari`) calisir; ihlal varsa
islem geri alinir.

Iletiler yalniz sayi, kimlik ve capa tasir; sozluk ve meal metni yazilmaz. Sayaclar: `lemma_*`,
`review_*`, `tri_*`, `form_*`, `span_hata`.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg
from psycopg.types.json import Jsonb

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_tr_roots import (
    KAYNAK,
    MEAL_KAYNAKLARI,
    QAC_KAYNAGI,
    TR_ROOTS_ADIMI,
)
from mutalaa_pipeline.enrich.morphology import kimlik_ata
from mutalaa_pipeline.enrich.tr_roots.bolme import parcalar
from mutalaa_pipeline.enrich.tr_roots.politika import (
    ADAY,
    KARARLAR,
    KOK_YOK,
    ONAYLI,
    Karar,
)
from mutalaa_pipeline.enrich.tr_roots.uret import FORMLAR_ADI, LEMMALAR_ADI
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.export.pg import Hazirlik, _capalar, _qa_denetle
from mutalaa_pipeline.export.pg_yapi import _dosya_oku
from mutalaa_pipeline.ingest.meal_kaynaklari import capa_onegi
from mutalaa_pipeline.normalize.turkish import normalize_tr
from mutalaa_pipeline.qa.checks.tr_roots import kanit_hatalari, span_bulgulari, span_hatalari
from mutalaa_pipeline.runctx import QaKaldi, RunContext
from mutalaa_pipeline.staged import Satir, satirlari_oku

ORIGIN: Final = "kaikki"
ONAY_YOLU: Final = "otomatik"
REVIEW_ALANI: Final = "kok_eslemesi"
EN_COK_MADDE: Final = 5


@dataclass(frozen=True)
class TrLemma:
    lemma: str
    karar: str
    neden: str
    kanit: dict[str, object]
    root_letters_bw: str | None
    ar_lemma_qac_ref: str | None
    freq: int
    review_onerilir: bool


@dataclass(frozen=True)
class TrForm:
    form: str
    lemma: str | None
    karar: str
    freq: int


@dataclass
class TrRootsHazirlik(Hazirlik):
    """`Hazirlik` + staged lemma ve form satirlari."""

    lemmalar: list[TrLemma] = field(default_factory=list)
    formlar: list[TrForm] = field(default_factory=list)
    mealler: tuple[str, ...] = ()
    data_version: str = ""


# --- satirlari okuma (kati) ------------------------------------------------------------------


def lemma_satirlarini_oku(satirlar: Sequence[Satir]) -> list[TrLemma]:
    sonuc: list[TrLemma] = []
    gorulen: set[str] = set()
    for s in satirlar:
        lemma, karar, neden = s.metin("lemma"), s.metin("karar"), s.metin("neden")
        if lemma == "" or lemma in gorulen or karar not in KARARLAR:
            raise GirdiHatasi(
                f"{LEMMALAR_ADI} satir {s.no}: lemma bos, yinelenen ya da karar gecersiz"
            )
        gorulen.add(lemma)
        if s.metin("text_clean") != lemma or normalize_tr(lemma, "dar") != lemma:
            raise GirdiHatasi(f"{LEMMALAR_ADI} satir {s.no}: text_clean lemmayla ayni degil")
        kanit = s.nesne("kanit")
        hatalar = kanit_hatalari(kanit, karar, neden)
        if hatalar:
            raise GirdiHatasi(f"{LEMMALAR_ADI} satir {s.no}: kanit gecersiz ({hatalar[0]})")
        bw = s.veri.get("root_letters_bw")
        ref = s.veri.get("ar_lemma_qac_ref")
        oneri = s.veri.get("review_onerilir")
        if (
            not (bw is None or isinstance(bw, str))
            or not (ref is None or isinstance(ref, str))
            or not isinstance(oneri, bool)
            or (karar == ONAYLI and bw is None)
        ):
            raise GirdiHatasi(
                f"{LEMMALAR_ADI} satir {s.no}: kok, Arapca lemma ya da bayrak gecersiz"
            )
        sonuc.append(TrLemma(lemma, karar, neden, kanit, bw, ref, s.sayi("freq"), oneri))
    return sonuc


def form_satirlarini_oku(satirlar: Sequence[Satir]) -> list[TrForm]:
    sonuc: list[TrForm] = []
    for s in satirlar:
        lemma = s.veri.get("lemma")
        karar = s.metin("karar")
        if karar not in KARARLAR or not (lemma is None or isinstance(lemma, str)):
            raise GirdiHatasi(f"{FORMLAR_ADI} satir {s.no}: karar ya da lemma gecersiz")
        sonuc.append(TrForm(s.metin("form"), lemma, karar, s.sayi("freq")))
    return sonuc


# --- hazirlik --------------------------------------------------------------------------------


def hazirla(
    ctx: RunContext, source_id: str, run: str | None, ek_kaynaklar: Sequence[str]
) -> Hazirlik:
    """Veritabanina dokunmadan tum dosya onkosullarini denetler (kaikki-tr kaynagi)."""
    kaynak_idleri = (source_id, *ek_kaynaklar)
    kaynaklar = ctx.require_sources(kaynak_idleri)  # G-KAY: kayit gecerli, atif_metni dolu
    ctx.require_sources((QAC_KAYNAGI, *MEAL_KAYNAKLARI))
    klasor_ust = ctx.staged_kaynak_dizini(source_id)
    if run is not None:
        if lineage.RUN_ID_DESENI.fullmatch(run) is None:
            raise GirdiHatasi("--run bir UUID degil")
        secilen = next((k for k in lineage.calismalar(klasor_ust) if k[0] == run), None)
        if secilen is None or secilen[2].get("adim") != TR_ROOTS_ADIMI:
            raise GirdiHatasi("--run icin manifestli enrich calistirmasi yok")
    else:
        secilen = lineage.son_basarili(klasor_ust, TR_ROOTS_ADIMI)
        if secilen is None:
            raise GirdiHatasi("manifestli enrich calistirmasi yok (once enrich tr-roots)")
    enrich_run_id, klasor, manifest = secilen
    if not lineage.ciktilar_saglam(ctx.veri_kok, manifest):
        raise GirdiHatasi("enrich calistirmasinin ciktilari saglam degil")
    lemma_bayt, lemma_sha = _dosya_oku(klasor, manifest, LEMMALAR_ADI)
    form_bayt, form_sha = _dosya_oku(klasor, manifest, FORMLAR_ADI)
    qa_rapor_id = _qa_denetle(ctx, source_id, enrich_run_id, lemma_sha)
    ayrintilar = manifest.get("ayrintilar")
    mealler = ayrintilar.get("mealler") if isinstance(ayrintilar, dict) else None
    surum = ayrintilar.get("data_version") if isinstance(ayrintilar, dict) else None
    if (
        not isinstance(mealler, list)
        or not mealler
        or not all(isinstance(m, str) and m in MEAL_KAYNAKLARI for m in mealler)
        or not isinstance(surum, str)
        or surum == ""
    ):
        raise GirdiHatasi("enrich manifestinde mealler ya da data_version yok ya da gecersiz")
    lemmalar = lemma_satirlarini_oku(satirlari_oku(lemma_bayt, LEMMALAR_ADI))
    formlar = form_satirlarini_oku(satirlari_oku(form_bayt, FORMLAR_ADI))
    lemma_yolu = lineage.goreli_yol(ctx.veri_kok, klasor / LEMMALAR_ADI)
    form_yolu = lineage.goreli_yol(ctx.veri_kok, klasor / FORMLAR_ADI)
    girdiler = [
        lineage.Girdi(lemma_yolu, lemma_sha, enrich_run_id),
        lineage.Girdi(form_yolu, form_sha, enrich_run_id),
    ]
    return TrRootsHazirlik(
        source_id=source_id,
        kaynak_idleri=kaynak_idleri,
        anchor_run_id=enrich_run_id,
        units_yol=lemma_yolu,
        units_sha256=lemma_sha,
        satirlar=[],
        zincir=[],
        ingest={},
        ham={slug: [] for slug in kaynak_idleri},
        qa_rapor_id=qa_rapor_id,
        kaynaklar=kaynaklar,
        bildirimler=dict.fromkeys(kaynak_idleri),
        parmak=ctx.parmak_izi(girdiler),
        lemmalar=lemmalar,
        formlar=formlar,
        mealler=tuple(str(m) for m in mealler),
        data_version=surum,
    )


# --- veritabani: lemma ------------------------------------------------------------------------


@dataclass(frozen=True)
class Mevcut:
    """Veritabanindaki bir Turkce lemma satiri (karar icin gereken alanlar)."""

    kimlik: int
    durum: str
    onay_yolu: str | None
    koken: str | None
    root_id: int | None
    ar_lemma_id: int | None
    etymological_only: bool
    kanit: object
    freq: int | None
    data_version: str


@dataclass(frozen=True)
class Eylem:
    """Bir lemma icin planlanan yazma: `ekle`, `guncelle`, `indir`, `yukselt`, `yenile`."""

    tur: str
    lemma: str
    kimlik: int
    root_id: int | None
    ar_lemma_id: int | None
    durum: str
    onay_yolu: str | None
    kanit: dict[str, object]
    freq: int
    data_version: str


@dataclass(frozen=True)
class ReviewAdayi:
    tur: str  # `aday` ya da `indir`
    kimlik: int
    freq: int
    onceki: Mapping[str, object] | None
    onerilen: Mapping[str, object]


LEMMA_STAGING: Final = (
    "CREATE TEMP TABLE staging_tr_lemma (eylem text, id integer, text_clean text, root_id integer,"
    " ar_lemma_id integer, durum text, onay_yolu text, kanit jsonb, freq integer,"
    " data_version text) ON COMMIT DROP"
)
LEMMA_COPY: Final = (
    "COPY pg_temp.staging_tr_lemma (eylem, id, text_clean, root_id, ar_lemma_id, durum, onay_yolu,"
    " kanit, freq, data_version) FROM STDIN"
)
LEMMA_EKLE: Final = (
    "INSERT INTO icerik.lemma (id, lang, text, text_clean, root_id, occurrences, ar_lemma_id,"
    " etymological_only, origin, status, onay_yolu, kanit, freq, source_id, data_version)"
    " SELECT s.id, 'tr', s.text_clean, s.text_clean, s.root_id, 0, s.ar_lemma_id, false, %s,"
    " s.durum::icerik.xref_status, s.onay_yolu, s.kanit, s.freq, %s, s.data_version"
    " FROM pg_temp.staging_tr_lemma s WHERE s.eylem = 'ekle' AND NOT EXISTS (SELECT 1 FROM"
    " icerik.lemma l WHERE l.lang = 'tr' AND l.text_clean = s.text_clean) ORDER BY s.id"
)
LEMMA_GUNCELLE: Final = (
    "UPDATE icerik.lemma l SET root_id = s.root_id, ar_lemma_id = s.ar_lemma_id, kanit = s.kanit,"
    " freq = s.freq, data_version = s.data_version FROM pg_temp.staging_tr_lemma s"
    " WHERE s.eylem = 'guncelle' AND l.id = s.id AND l.lang = 'tr' AND l.status = 'onayli'"
    " AND l.onay_yolu = 'otomatik' AND (l.root_id, l.ar_lemma_id, l.kanit, l.freq, l.data_version)"
    " IS DISTINCT FROM (s.root_id, s.ar_lemma_id, s.kanit, s.freq, s.data_version)"
)
LEMMA_INDIR: Final = (
    "UPDATE icerik.lemma l SET status = 'aday', onay_yolu = NULL, kanit = s.kanit, freq = s.freq,"
    " data_version = s.data_version FROM pg_temp.staging_tr_lemma s WHERE s.eylem = 'indir'"
    " AND l.id = s.id AND l.lang = 'tr' AND l.status = 'onayli' AND l.onay_yolu = 'otomatik'"
)
LEMMA_YUKSELT: Final = (
    "UPDATE icerik.lemma l SET status = 'onayli', onay_yolu = 'otomatik', root_id = s.root_id,"
    " ar_lemma_id = s.ar_lemma_id, kanit = s.kanit, freq = s.freq, data_version = s.data_version"
    " FROM pg_temp.staging_tr_lemma s WHERE s.eylem = 'yukselt' AND l.id = s.id AND l.lang = 'tr'"
    " AND l.status = 'aday' AND l.onay_yolu IS NULL AND l.origin = 'kaikki' AND NOT EXISTS"
    " (SELECT 1 FROM icerik.review r WHERE r.hedef_tablo = 'lemma'"
    " AND r.hedef_anahtar = l.id::text)"
)
LEMMA_YENILE: Final = (
    "UPDATE icerik.lemma l SET kanit = s.kanit, freq = s.freq, data_version = s.data_version"
    " FROM pg_temp.staging_tr_lemma s WHERE s.eylem = 'yenile' AND l.id = s.id AND l.lang = 'tr'"
    " AND l.status = 'aday' AND l.onay_yolu IS NULL AND l.origin = 'kaikki'"
    " AND (l.kanit, l.freq, l.data_version) IS DISTINCT FROM (s.kanit, s.freq, s.data_version)"
)
REVIEW_STAGING: Final = (
    "CREATE TEMP TABLE staging_tr_review (tur text, lemma_id integer, freq integer, onceki jsonb,"
    " onerilen jsonb) ON COMMIT DROP"
)
REVIEW_COPY: Final = (
    "COPY pg_temp.staging_tr_review (tur, lemma_id, freq, onceki, onerilen) FROM STDIN"
)
# `aday`: hicbir durumda review yok; `indir`: acik review yok ve satir hala hat adayi.
REVIEW_EKLE: Final = (
    "INSERT INTO icerik.review (hedef_tablo, hedef_anahtar, alan, eylem, onceki, onerilen, guven,"
    " koken, oneren) SELECT 'lemma', s.lemma_id::text, %s, 'oner', s.onceki, s.onerilen, NULL,"
    " 'hat', 'hat' FROM pg_temp.staging_tr_review s JOIN icerik.lemma l ON l.id = s.lemma_id"
    " WHERE l.lang = 'tr' AND l.status = 'aday' AND l.onay_yolu IS NULL AND ((s.tur = 'aday'"
    " AND NOT EXISTS (SELECT 1 FROM icerik.review r WHERE r.hedef_tablo = 'lemma'"
    " AND r.hedef_anahtar = s.lemma_id::text)) OR (s.tur = 'indir' AND NOT EXISTS (SELECT 1 FROM"
    " icerik.review r WHERE r.hedef_tablo = 'lemma' AND r.hedef_anahtar = s.lemma_id::text"
    " AND r.durum = 'acik'))) ORDER BY s.freq DESC, s.lemma_id"
)


def _copy(conn: psycopg.Connection, sorgu: str, satirlar: Sequence[Sequence[object]]) -> None:
    with conn.cursor() as imlec, imlec.copy(sorgu) as kopya:
        for satir in satirlar:
            kopya.write_row(satir)


def _say(conn: psycopg.Connection, sorgu: str) -> int:
    satir = conn.execute(sorgu).fetchone()
    return int(satir[0]) if satir is not None else 0


def kanit_zenginlestir(
    kanit: Mapping[str, object], root_id: int | None, ar_lemma_id: int | None
) -> dict[str, object]:
    """`kanit.qac` icine veritabani kimliklerini (`root_id`, `ar_lemma_id`) ekler (kopya)."""
    qac_ham = kanit.get("qac")
    qac = dict(qac_ham) if isinstance(qac_ham, dict) else {}
    qac["root_id"] = root_id
    qac["ar_lemma_id"] = ar_lemma_id
    return {**kanit, "qac": qac}


def kanit_ozeti(kanit: Mapping[str, object]) -> dict[str, object]:
    """`review.onerilen.kanit_ozeti`: yontem, kaynak sayisi ve ilk maddeler (sozluk metni yok)."""
    kaynaklar = kanit.get("kaynaklar")
    liste = [k for k in kaynaklar if isinstance(k, dict)] if isinstance(kaynaklar, list) else []
    maddeler = list(dict.fromkeys(str(k.get("madde")) for k in liste))[:EN_COK_MADDE]
    qac = kanit.get("qac")
    eslesme = qac.get("eslesme") if isinstance(qac, dict) else None
    return {
        "politika_surumu": kanit.get("politika_surumu"),
        "eslesme": eslesme,
        "kaynak_sayisi": len(liste),
        "maddeler": maddeler,
    }


def _kanit_yok(neden: str) -> dict[str, object]:
    """Staged'de bulunmayan lemma icin `kok_yok` kaniti (otomatik onay geri alinirken)."""
    return Karar(KOK_YOK, neden).kanit()


def _mevcutlar(conn: psycopg.Connection) -> dict[str, Mevcut]:
    sonuc: dict[str, Mevcut] = {}
    for satir in conn.execute(
        "SELECT id, text_clean, status::text, onay_yolu, origin, root_id, ar_lemma_id,"
        " etymological_only, kanit, freq, data_version FROM icerik.lemma WHERE lang = 'tr'"
    ).fetchall():
        sonuc[str(satir[1])] = Mevcut(
            int(satir[0]),
            str(satir[2]),
            None if satir[3] is None else str(satir[3]),
            None if satir[4] is None else str(satir[4]),
            None if satir[5] is None else int(satir[5]),
            None if satir[6] is None else int(satir[6]),
            bool(satir[7]),
            satir[8],
            None if satir[9] is None else int(satir[9]),
            str(satir[10]),
        )
    return sonuc


def _kimlik_haritalari(
    conn: psycopg.Connection, h: TrRootsHazirlik
) -> tuple[dict[str, int], dict[str, int]]:
    """QAC koku (`letters_bw`) ve Arapca lemma (`qac_ref`) kimlikleri; staged'in gerektirdigi."""
    kok = {
        str(bw): int(i)
        for i, bw in conn.execute(
            "SELECT id, letters_bw FROM icerik.root WHERE letters_bw IS NOT NULL"
        ).fetchall()
    }
    ar = {
        str(ref): int(i)
        for i, ref in conn.execute(
            "SELECT id, qac_ref FROM icerik.lemma WHERE lang = 'ar' AND qac_ref IS NOT NULL"
        ).fetchall()
    }
    eksik_kok = sorted({x.root_letters_bw for x in h.lemmalar if x.root_letters_bw} - set(kok))
    eksik_ar = sorted({x.ar_lemma_qac_ref for x in h.lemmalar if x.ar_lemma_qac_ref} - set(ar))
    if eksik_kok or eksik_ar:
        raise GirdiHatasi(
            f"QAC koku ya da lemmasi veritabaninda yok (kok {len(eksik_kok)}:"
            f" {_capalar(eksik_kok)}; lemma {len(eksik_ar)}: {_capalar(eksik_ar)});"
            " once export pg --source qac-morfoloji"
        )
    return kok, ar


def planla(
    h: TrRootsHazirlik,
    mevcut: Mapping[str, Mevcut],
    review_var: Mapping[str, tuple[bool, bool]],
    kok_id: Mapping[str, int],
    ar_id: Mapping[str, int],
    taban: int,
) -> tuple[list[Eylem], list[ReviewAdayi], dict[str, int]]:
    """Her staged ve mevcut lemma icin yazma plani (veritabanina dokunmaz).

    `review_var`: lemma kimligi (metin) -> (herhangi bir durumda review var, acik review var).
    """
    sayac: Counter[str] = Counter()
    staged = {x.lemma: x for x in h.lemmalar}
    yeni = sorted(
        x.lemma
        for x in h.lemmalar
        if x.lemma not in mevcut and (x.karar == ONAYLI or x.root_letters_bw is not None)
    )
    kimlikler = kimlik_ata(
        {k: v.kimlik for k, v in mevcut.items()}, sorted({*mevcut, *yeni}), taban
    )
    eylemler: list[Eylem] = []
    reviewlar: list[ReviewAdayi] = []

    def ey(
        tur: str,
        lemma: str,
        kimlik: int,
        ids: tuple[int | None, int | None],
        x: TrLemma | None,
        durum: str,
        kanit: dict[str, object],
        freq: int,
    ) -> None:
        onay = ONAY_YOLU if durum == "onayli" else None
        eylemler.append(
            Eylem(tur, lemma, kimlik, ids[0], ids[1], durum, onay, kanit, freq, h.data_version)
        )

    def oneri(
        ids: tuple[int | None, int | None],
        neden: str,
        kanit: Mapping[str, object],
        etim: bool = False,
    ) -> dict[str, object]:
        return {
            "root_id": ids[0],
            "ar_lemma_id": ids[1],
            "etymological_only": etim,
            "neden": neden,
            "kanit_ozeti": kanit_ozeti(kanit),
        }

    for lemma, x in sorted(staged.items()):
        var = mevcut.get(lemma)
        koku = kok_id[x.root_letters_bw] if x.root_letters_bw else None
        ar = ar_id[x.ar_lemma_qac_ref] if x.ar_lemma_qac_ref else None
        kanit = kanit_zenginlestir(x.kanit, koku, ar)
        if var is None:
            if x.karar == ONAYLI:
                ey("ekle", lemma, kimlikler[lemma], (koku, ar), x, "onayli", kanit, x.freq)
                sayac["lemma_onayli_eklenen"] += 1
            elif x.karar == KOK_YOK:
                sayac["lemma_kok_yok_atlanan"] += 1
            elif koku is None:
                sayac["lemma_onerisiz_atlanan"] += 1
            else:
                ey("ekle", lemma, kimlikler[lemma], (None, None), x, "aday", kanit, x.freq)
                sayac["lemma_aday_eklenen"] += 1
                if x.review_onerilir:
                    o = oneri((koku, ar), x.neden, kanit)
                    reviewlar.append(ReviewAdayi("aday", kimlikler[lemma], x.freq, None, o))
                else:
                    sayac["review_esik_alti"] += 1
            continue
        if var.onay_yolu == "editor" or var.koken == "editor":
            sayac["lemma_editor_korunan"] += 1
        elif var.durum == "red":
            sayac["lemma_red_korunan"] += 1
        elif var.onay_yolu == ONAY_YOLU and var.durum == "onayli":
            if x.karar == ONAYLI:
                simdiki = (var.root_id, var.ar_lemma_id, var.kanit, var.freq, var.data_version)
                if simdiki != (koku, ar, kanit, x.freq, h.data_version):
                    ey("guncelle", lemma, var.kimlik, (koku, ar), x, "onayli", kanit, x.freq)
                    sayac["lemma_guncellenen"] += 1
            else:
                eski = (var.root_id, var.ar_lemma_id)
                ey("indir", lemma, var.kimlik, eski, x, "aday", kanit, x.freq)
                onceki = _onceki(var)
                o = (
                    oneri((koku, ar), x.neden, kanit)
                    if koku is not None
                    else oneri(eski, x.neden, kanit)
                )
                reviewlar.append(ReviewAdayi("indir", var.kimlik, x.freq, onceki, o))
                sayac["lemma_adaya_donen"] += 1
        elif var.durum == "aday" and var.onay_yolu is None:
            herhangi = review_var.get(str(var.kimlik), (False, False))[0]
            if x.karar == ONAYLI and not herhangi:
                ey("yukselt", lemma, var.kimlik, (koku, ar), x, "onayli", kanit, x.freq)
                sayac["lemma_yukselen"] += 1
                continue
            if (var.kanit, var.freq, var.data_version) != (kanit, x.freq, h.data_version):
                ey("yenile", lemma, var.kimlik, (None, None), x, "aday", kanit, x.freq)
                sayac["lemma_yenilenen"] += 1
            if x.review_onerilir and not herhangi and x.karar == ADAY:
                o = oneri((koku, ar), x.neden, kanit)
                reviewlar.append(ReviewAdayi("aday", var.kimlik, x.freq, None, o))
        else:
            sayac["lemma_korunan_diger"] += 1

    # staged'de hic bulunmayan otomatik onayli satirlar: kosul saglanmiyor demektir
    for lemma, var in sorted(mevcut.items()):
        if lemma in staged or var.onay_yolu != ONAY_YOLU or var.durum != "onayli":
            continue
        kanit = _kanit_yok("staged_yok")
        eski = (var.root_id, var.ar_lemma_id)
        ey("indir", lemma, var.kimlik, eski, None, "aday", kanit, var.freq or 0)
        o = oneri(eski, "staged_yok", kanit, var.etymological_only)
        reviewlar.append(ReviewAdayi("indir", var.kimlik, var.freq or 0, _onceki(var), o))
        sayac["lemma_adaya_donen"] += 1
    return eylemler, reviewlar, dict(sayac)


def _onceki(var: Mevcut) -> dict[str, object]:
    return {
        "root_id": var.root_id,
        "ar_lemma_id": var.ar_lemma_id,
        "etymological_only": var.etymological_only,
        "durum": "onayli",
        "onay_yolu": ONAY_YOLU,
    }


def _lemma_yukle(
    conn: psycopg.Connection,
    h: TrRootsHazirlik,
    kok_id: Mapping[str, int],
    ar_id: Mapping[str, int],
) -> dict[str, int]:
    mevcut = _mevcutlar(conn)
    review_var: dict[str, tuple[bool, bool]] = {}
    for anahtar, acik in conn.execute(
        "SELECT hedef_anahtar, bool_or(durum = 'acik') FROM icerik.review"
        " WHERE hedef_tablo = 'lemma' GROUP BY hedef_anahtar"
    ).fetchall():
        review_var[str(anahtar)] = (True, bool(acik))
    taban = _say(conn, "SELECT coalesce(max(id), 0) FROM icerik.lemma")
    eylemler, reviewlar, sayac = planla(h, mevcut, review_var, kok_id, ar_id, taban)

    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_tr_lemma")
    conn.execute(LEMMA_STAGING)
    _copy(
        conn,
        LEMMA_COPY,
        [
            (
                e.tur,
                e.kimlik,
                e.lemma,
                e.root_id,
                e.ar_lemma_id,
                e.durum,
                e.onay_yolu,
                Jsonb(e.kanit),
                e.freq,
                e.data_version,
            )
            for e in eylemler
        ],
    )
    eklenen = conn.execute(LEMMA_EKLE, (ORIGIN, KAYNAK)).rowcount
    guncellenen = conn.execute(LEMMA_GUNCELLE).rowcount
    inen = conn.execute(LEMMA_INDIR).rowcount
    yukselen = conn.execute(LEMMA_YUKSELT).rowcount
    yenilenen = conn.execute(LEMMA_YENILE).rowcount

    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_tr_review")
    conn.execute(REVIEW_STAGING)
    _copy(
        conn,
        REVIEW_COPY,
        [
            (
                r.tur,
                r.kimlik,
                r.freq,
                Jsonb(r.onceki) if r.onceki is not None else None,
                Jsonb(r.onerilen),
            )
            for r in reviewlar
        ],
    )
    review = conn.execute(REVIEW_EKLE, (REVIEW_ALANI,)).rowcount
    sayilar = {
        "lemma_staging": len(h.lemmalar),
        "lemma_eklenen": eklenen,
        "lemma_guncellenen": guncellenen,
        "lemma_adaya_donen": inen,
        "lemma_yukselen": yukselen,
        "lemma_yenilenen": yenilenen,
        "review_eklenen": review,
        "review_adayi": len(reviewlar),
    }
    for ad in (
        "lemma_editor_korunan",
        "lemma_red_korunan",
        "lemma_korunan_diger",
        "lemma_onerisiz_atlanan",
        "lemma_kok_yok_atlanan",
        "review_esik_alti",
    ):
        sayilar[ad] = sayac.get(ad, 0)
    return sayilar


# --- veritabani: tr_root_index ve tr_form -----------------------------------------------------

TRI_STAGING: Final = (
    'CREATE TEMP TABLE staging_tri (anchor text COLLATE "C", span_start integer, span_end integer,'
    " root_id integer, tr_lemma_id integer, etymological_only boolean, unit_hash char(16),"
    " data_version text) ON COMMIT DROP"
)
TRI_COPY: Final = (
    "COPY pg_temp.staging_tri (anchor, span_start, span_end, root_id, tr_lemma_id,"
    " etymological_only, unit_hash, data_version) FROM STDIN"
)
TRI_KAPSAM: Final = (
    "EXISTS (SELECT 1 FROM unnest(%(onekler)s::text[]) p WHERE starts_with(t.anchor, p))"
)
TRI_SIL: Final = (
    "DELETE FROM icerik.tr_root_index t WHERE " + TRI_KAPSAM + " AND NOT EXISTS (SELECT 1 FROM"
    " pg_temp.staging_tri s WHERE s.anchor = t.anchor AND s.span_start = t.span_start)"
)
TRI_GUNCELLE: Final = (
    "UPDATE icerik.tr_root_index t SET span_end = s.span_end, root_id = s.root_id,"
    " tr_lemma_id = s.tr_lemma_id, etymological_only = s.etymological_only,"
    " unit_hash = s.unit_hash, data_version = s.data_version FROM pg_temp.staging_tri s"
    " WHERE s.anchor = t.anchor AND s.span_start = t.span_start AND (t.span_end, t.root_id,"
    " t.tr_lemma_id, t.etymological_only, t.unit_hash, t.data_version) IS DISTINCT FROM"
    " (s.span_end, s.root_id, s.tr_lemma_id, s.etymological_only, s.unit_hash, s.data_version)"
)
TRI_EKLE: Final = (
    "INSERT INTO icerik.tr_root_index (anchor, span_start, span_end, root_id, tr_lemma_id,"
    " etymological_only, unit_hash, data_version) SELECT s.anchor, s.span_start, s.span_end,"
    " s.root_id, s.tr_lemma_id, s.etymological_only, s.unit_hash, s.data_version"
    " FROM pg_temp.staging_tri s WHERE NOT EXISTS (SELECT 1 FROM icerik.tr_root_index t"
    " WHERE t.anchor = s.anchor AND t.span_start = s.span_start)"
    " ORDER BY s.anchor, s.span_start"
)
FORM_STAGING: Final = (
    "CREATE TEMP TABLE staging_tr_form (key_narrow text, tr_lemma_id integer, key_wide text,"
    " freq integer, data_version text) ON COMMIT DROP"
)
FORM_COPY: Final = (
    "COPY pg_temp.staging_tr_form (key_narrow, tr_lemma_id, key_wide, freq, data_version)"
    " FROM STDIN"
)
FORM_KAPSAM: Final = "t.tr_lemma_id IN (SELECT id FROM icerik.lemma WHERE lang = 'tr')"
FORM_SIL: Final = (
    "DELETE FROM icerik.tr_form t WHERE " + FORM_KAPSAM + " AND NOT EXISTS (SELECT 1 FROM"
    " pg_temp.staging_tr_form s WHERE s.key_narrow = t.key_narrow"
    " AND s.tr_lemma_id = t.tr_lemma_id)"
)
FORM_GUNCELLE: Final = (
    "UPDATE icerik.tr_form t SET key_wide = s.key_wide, freq = s.freq,"
    " data_version = s.data_version FROM pg_temp.staging_tr_form s"
    " WHERE s.key_narrow = t.key_narrow AND s.tr_lemma_id = t.tr_lemma_id"
    " AND (t.key_wide, t.freq, t.data_version) IS DISTINCT FROM"
    " (s.key_wide, s.freq, s.data_version)"
)
FORM_EKLE: Final = (
    "INSERT INTO icerik.tr_form (key_narrow, tr_lemma_id, key_wide, freq, data_version)"
    " SELECT s.key_narrow, s.tr_lemma_id, s.key_wide, s.freq, s.data_version"
    " FROM pg_temp.staging_tr_form s WHERE NOT EXISTS (SELECT 1 FROM icerik.tr_form t"
    " WHERE t.key_narrow = s.key_narrow AND t.tr_lemma_id = s.tr_lemma_id)"
    " ORDER BY s.key_narrow, s.tr_lemma_id"
)


@dataclass(frozen=True)
class OnayliLemma:
    kimlik: int
    root_id: int
    etymological_only: bool


def span_satirlari(
    birimler: Sequence[tuple[str, str, str]],
    form_lemma: Mapping[str, OnayliLemma],
    data_version: str,
) -> list[tuple[str, int, int, int, int, bool, str, str]]:
    """`(capa, metin, content_hash)` birimlerinden tr_root_index satirlari.

    Aralik, metnin kod noktasi dizinidir ve yari aciktir; satir yalniz yuzey bicim karar
    tablosunda onayli bir lemmaya bagliysa uretilir.
    """
    satirlar: list[tuple[str, int, int, int, int, bool, str, str]] = []
    for capa, metin, ozet in birimler:
        for p in parcalar(metin):
            hedef = form_lemma.get(p.anahtar)
            if hedef is not None:
                satirlar.append(
                    (
                        capa,
                        p.bas,
                        p.son,
                        hedef.root_id,
                        hedef.kimlik,
                        hedef.etymological_only,
                        ozet[:16],
                        data_version,
                    )
                )
    satirlar.sort(key=lambda s: (s[0].encode("utf-8"), s[1]))
    return satirlar


def form_satirlari(
    formlar: Sequence[TrForm], onayli: Mapping[str, OnayliLemma], data_version: str
) -> list[tuple[str, int, str, int, str]]:
    """`tr_form` satirlari: `(key_narrow, tr_lemma_id, key_wide, freq, data_version)`."""
    toplam: dict[tuple[str, int], tuple[str, int]] = {}
    for f in formlar:
        if f.lemma is None or f.lemma not in onayli:
            continue
        dar = normalize_tr(f.form, "dar")
        genis = normalize_tr(f.form, "genis")
        if dar == "" or " " in dar or genis == "":
            continue
        anahtar = (dar, onayli[f.lemma].kimlik)
        onceki = toplam.get(anahtar, (genis, 0))
        toplam[anahtar] = (onceki[0], onceki[1] + f.freq)
    return [
        (dar, kimlik, genis, freq, data_version)
        for (dar, kimlik), (genis, freq) in sorted(toplam.items())
    ]


def _indeks_yukle(conn: psycopg.Connection, h: TrRootsHazirlik) -> dict[str, int]:
    onayli: dict[str, OnayliLemma] = {}
    for kimlik, temiz, kok, etim in conn.execute(
        "SELECT id, text_clean, root_id, etymological_only FROM icerik.lemma"
        " WHERE lang = 'tr' AND status = 'onayli' AND root_id IS NOT NULL"
    ).fetchall():
        onayli[str(temiz)] = OnayliLemma(int(kimlik), int(kok), bool(etim))
    form_lemma = {
        f.form: onayli[f.lemma] for f in h.formlar if f.lemma is not None and f.lemma in onayli
    }
    birimler: list[tuple[str, str, str]] = []
    onekler: list[str] = []
    for meal in h.mealler:
        onekler.append(capa_onegi(meal))
        for capa, metin, ozet in conn.execute(
            "SELECT anchor, metin, content_hash FROM icerik.unit WHERE source_id = %s"
            " AND kind = 'meal' AND status = 'etkin' ORDER BY anchor",
            (meal,),
        ).fetchall():
            if metin != "":
                birimler.append((str(capa), str(metin), str(ozet)))
    satirlar = span_satirlari(birimler, form_lemma, h.data_version)
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_tri")
    conn.execute(TRI_STAGING)
    _copy(conn, TRI_COPY, satirlar)
    silinen = conn.execute(TRI_SIL, {"onekler": onekler}).rowcount
    guncellenen = conn.execute(TRI_GUNCELLE).rowcount
    eklenen = conn.execute(TRI_EKLE).rowcount

    forms = form_satirlari(h.formlar, onayli, h.data_version)
    conn.execute("DROP TABLE IF EXISTS pg_temp.staging_tr_form")
    conn.execute(FORM_STAGING)
    _copy(conn, FORM_COPY, forms)
    f_silinen = conn.execute(FORM_SIL).rowcount
    f_guncellenen = conn.execute(FORM_GUNCELLE).rowcount
    f_eklenen = conn.execute(FORM_EKLE).rowcount
    return {
        "tri_staging": len(satirlar),
        "tri_eklenen": eklenen,
        "tri_silinen": silinen,
        "tri_guncellenen": guncellenen,
        "tri_degismeyen": len(satirlar) - eklenen - guncellenen,
        "form_staging": len(forms),
        "form_eklenen": f_eklenen,
        "form_silinen": f_silinen,
        "form_guncellenen": f_guncellenen,
        "form_degismeyen": len(forms) - f_eklenen - f_guncellenen,
        "onayli_lemma": len(onayli),
    }


def yukle(conn: psycopg.Connection, ctx: RunContext, h: Hazirlik) -> dict[str, int]:
    """Lemma, review, tr_root_index ve tr_form yazar (cagiran `conn.transaction()` icindedir)."""
    if not isinstance(h, TrRootsHazirlik):
        raise TypeError("kaikki-tr yuklemesi TrRootsHazirlik ister")
    kok_id, ar_id = _kimlik_haritalari(conn, h)
    sayilar = _lemma_yukle(conn, h, kok_id, ar_id)
    sayilar.update(_indeks_yukle(conn, h))
    hatalar = span_hatalari(conn)
    bulgu = span_bulgulari(hatalar)
    if bulgu:
        raise QaKaldi("G-CAP (tr_root_index): " + "; ".join(bulgu))
    sayilar["span_hata"] = sum(hatalar.values())
    ctx.gunluk.bilgi("export_pg_tr_roots", **{k: v for k, v in sayilar.items() if v})
    return sayilar
