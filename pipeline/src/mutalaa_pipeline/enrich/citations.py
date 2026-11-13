"""Atif ve iktibas adaylari: arac bagimsiz `Tespit` arayuzu ve `xrefs.jsonl` yazimi (A20.7a).

Kazanan arac secilmeden de calisir: araclar `DiziTespitcisi` protokolunun arkasindadir (bir Arapca
diziyi alir, dizi icindeki eslesmeleri dondurur). Acik atiflar `atif_gramer`, Arapca dizi ve
baglam `arapca_dizi` ile bizde kalir. Cikti `xref` aday satirlaridir (Editoryal veritabani §7):
`origin = 'hat'`, `status = 'aday'`, `type` `atif` (acik gosterim) ya da `iktibas` (Arapca alinti),
`src_anchor` Risale paragraf capasi, `src_span` paragraf metninde kod noktasi `[bas, son)`,
`dst_anchor` `q:{sure}:{ayet}` (ayet duzeyi; `dst_span` bos), `evidence` yalniz sayi, bayrak ve
kisa kimlik tasir (metin yok). Kaynak `risale-atif-dizini` (`evidence.source_id`).

Tekillik: `xref_natural_key = (type, src_anchor, src_span, dst_anchor, dst_span)` (veritabani
kisiti ile ayni). Ayni anahtara dusen tespitler birlesir (en yuksek guvenli kalir); cikti anahtara
gore siralidir ve zaman damgasi tasimaz, yani ayni girdiyle ayni baytlar uretilir.
"""

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol

from mutalaa_pipeline import lineage
from mutalaa_pipeline.anchor import (
    AnchorError,
    AnchorRef,
    Q,
    Rn,
    format,
    parse,
    sort_key,
    try_parse,
)
from mutalaa_pipeline.enrich import arapca_dizi, atif_gramer
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.staged import satir_baytlari

if TYPE_CHECKING:
    from mutalaa_pipeline.runctx import RunContext

KAYNAK_ID: Final = "risale-atif-dizini"
XREFS_ADI: Final = "xrefs.jsonl"
ORIGIN: Final = "hat"
STATUS: Final = "aday"
TUR_ATIF: Final = "atif"
TUR_IKTIBAS: Final = "iktibas"
TURLER: Final = (TUR_ATIF, TUR_IKTIBAS)
YONTEM_GRAMER: Final = "atif_gramer"
YONTEM_ARAC: Final = "arac"
VARSAYILAN_SKOR: Final = 0.5  # aracin skoru yoksa; evidence.skor_yok = true

GUVEN_KAYNAGI_GRAMER: Final = "gramer_baslangic"
GUVEN_KAYNAGI_SKOR: Final = "arac_skoru"
GUVEN_KAYNAGI_VARSAYILAN: Final = "varsayilan"

# evidence: yalniz bu anahtarlar; degerler sayi, bayrak ya da kisa kimlik (serbest metin yok).
EVIDENCE_ANAHTARLARI: Final = frozenset(
    {
        "arac",
        "arac_surumu",
        "birlesen",
        "dizi_turu",
        "fikstur",
        "grup",
        "grup_boyutu",
        "hedef_sayisi",
        "guven_kaynagi",
        "kapsama",
        "kelime_sayisi",
        "parantez",
        "sinyal",
        "skor",
        "skor_yok",
        "source_id",
        "yontem",
    }
)
_KISA_KIMLIK: Final = re.compile(r"[A-Za-z0-9_.@:+-]{1,64}")

type EvidenceDegeri = bool | int | float | str
type XrefSatiri = dict[str, object]
type DogalAnahtar = tuple[str, str, tuple[int, int] | None, str, tuple[int, int] | None]


@dataclass(frozen=True, slots=True)
class DiziEslesmesi:
    """Bir aracin tek bir dizide buldugu eslesme; ofsetler dizi metnine goredir `[bas, son)`."""

    bas: int
    son: int
    ayetler: tuple[tuple[int, int], ...]  # (sure, ayet), okuma sirasinda
    skor: float | None = None
    kelime_sayisi: int | None = None


class DiziTespitcisi(Protocol):
    """Arac sarmalayicisi: kazanan secilince yalniz bu arayuzu gerceklestiren bir sinif eklenir."""

    ad: str
    surum: str

    def tespit_et(self, dizi_metni: str) -> Sequence[DiziEslesmesi]: ...


def _evidence_denetle(evidence: Mapping[str, EvidenceDegeri]) -> dict[str, EvidenceDegeri]:
    sonuc: dict[str, EvidenceDegeri] = {}
    for anahtar in sorted(evidence):
        deger = evidence[anahtar]
        if anahtar not in EVIDENCE_ANAHTARLARI:
            raise GirdiHatasi(f"evidence: izin verilmeyen anahtar '{anahtar}'")
        if isinstance(deger, str) and _KISA_KIMLIK.fullmatch(deger) is None:
            raise GirdiHatasi(f"evidence: '{anahtar}' kisa kimlik degil")
        sonuc[anahtar] = deger
    return sonuc


def _birim_aralik_denetle(src_anchor: str, bas: int, son: int) -> None:
    try:
        ref = parse(src_anchor)
    except AnchorError:
        raise GirdiHatasi("src_anchor gecersiz capa") from None
    if not isinstance(ref.anchor, Rn) or ref.anchor.s is not None or ref.span is not None:
        raise GirdiHatasi("src_anchor Risale paragraf capasi degil")
    if not 0 <= bas < son:
        raise GirdiHatasi(f"src_span gecersiz: [{bas}, {son})")


@dataclass(frozen=True, slots=True)
class Tespit:
    """Bir Risale paragrafindan bir ayete bir atif ya da iktibas adayi (araca bagli degil).

    `skor` aracin ya da gramerin ham puanidir; `guven` baslangic guvenidir (kalibre degildir;
    Iktibas tespiti §8: ilk olcumden sonra lojistik regresyonla degisir). Ikisi de 0-1 arasidir.
    """

    src_anchor: str
    src_bas: int
    src_son: int
    sure: int
    ayet: int
    tur: str
    yontem: str
    arac: str
    arac_surumu: str
    skor: float
    guven: float
    ayrintilar: Mapping[str, EvidenceDegeri] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _birim_aralik_denetle(self.src_anchor, self.src_bas, self.src_son)
        if try_parse(f"q:{self.sure}:{self.ayet}") is None:
            raise GirdiHatasi("dst: gecersiz sure ya da ayet")
        if self.tur not in TURLER:
            raise GirdiHatasi("tur atif ya da iktibas degil")
        if self.yontem not in (YONTEM_GRAMER, YONTEM_ARAC):
            raise GirdiHatasi("yontem bilinmiyor")
        for ad, deger in (("skor", self.skor), ("guven", self.guven)):
            if not 0.0 <= deger <= 1.0:
                raise GirdiHatasi(f"{ad} 0-1 arasinda degil")
        _evidence_denetle(self.ayrintilar)

    @property
    def dst_anchor(self) -> str:
        return format(AnchorRef(Q(self.sure, self.ayet)))


def tespitten_xref(tespit: Tespit, data_version: str) -> XrefSatiri:
    """`Tespit` -> `xref` aday satiri (staged `xrefs.jsonl` bicimi)."""
    evidence: dict[str, EvidenceDegeri] = {
        **tespit.ayrintilar,
        "source_id": KAYNAK_ID,
        "yontem": tespit.yontem,
        "arac": tespit.arac,
        "arac_surumu": tespit.arac_surumu,
    }
    if "skor_yok" not in evidence:
        evidence["skor"] = round(tespit.skor, 4)
    return {
        "src_anchor": tespit.src_anchor,
        "src_span": [tespit.src_bas, tespit.src_son],
        "dst_anchor": tespit.dst_anchor,
        "dst_span": None,
        "type": tespit.tur,
        "score": round(tespit.skor, 4),
        "confidence": round(tespit.guven, 4),
        "evidence": _evidence_denetle(evidence),
        "origin": ORIGIN,
        "status": STATUS,
        "data_version": data_version,
    }


def _aralik(deger: object) -> tuple[int, int] | None:
    if deger is None:
        return None
    if (
        not isinstance(deger, Sequence)
        or isinstance(deger, str)
        or len(deger) != 2
        or not all(isinstance(x, int) and not isinstance(x, bool) for x in deger)
    ):
        raise GirdiHatasi("span [bas, son] tam sayi cifti degil")
    return int(deger[0]), int(deger[1])


def xref_natural_key(satir: Mapping[str, object]) -> DogalAnahtar:
    """`(type, src_anchor, src_span, dst_anchor, dst_span)`; veritabani kisitiyla ayni."""
    tur, src, dst = satir.get("type"), satir.get("src_anchor"), satir.get("dst_anchor")
    if not isinstance(tur, str) or not isinstance(src, str) or not isinstance(dst, str):
        raise GirdiHatasi("xref satiri: type, src_anchor ve dst_anchor metin olmali")
    return tur, src, _aralik(satir.get("src_span")), dst, _aralik(satir.get("dst_span"))


def _siralama_anahtari(satir: Mapping[str, object]) -> tuple[object, ...]:
    tur, src, src_span, dst, dst_span = xref_natural_key(satir)
    return (
        sort_key(parse(src)),
        src_span or (-1, -1),
        sort_key(parse(dst)),
        dst_span or (-1, -1),
        tur,
    )


def xrefleri_birlestir(tespitler: Iterable[Tespit], data_version: str) -> list[XrefSatiri]:
    """Tespitleri tekil `xref` satirlarina cevirir; ayni dogal anahtar birlesir, sirali dondurur.

    Ayni anahtardaki tespitlerden guveni en yuksek olan kalir (esitlikte arac adi, sonra yontem
    sirasiyla); `evidence.birlesen` birlesen tespit sayisini yazar (1'den buyukse).
    """
    gruplar: dict[DogalAnahtar, list[Tespit]] = {}
    for tespit in tespitler:
        anahtar = xref_natural_key(tespitten_xref(tespit, data_version))
        gruplar.setdefault(anahtar, []).append(tespit)
    satirlar: list[XrefSatiri] = []
    for adaylar in gruplar.values():
        en_iyi = min(adaylar, key=lambda t: (-t.guven, -t.skor, t.arac, t.yontem))
        satir = tespitten_xref(en_iyi, data_version)
        if len(adaylar) > 1:
            evidence = dict(satir["evidence"])  # type: ignore[call-overload]
            evidence["birlesen"] = len(adaylar)
            satir["evidence"] = _evidence_denetle(evidence)
        satirlar.append(satir)
    satirlar.sort(key=_siralama_anahtari)
    return satirlar


def xrefs_baytlari(satirlar: Iterable[XrefSatiri]) -> tuple[bytes, int]:
    """Kanonik `xrefs.jsonl` baytlari (anahtar sirali, kompakt, ASCII, LF); tekillik denetli."""
    sirali = sorted(satirlar, key=_siralama_anahtari)
    gorulen: set[DogalAnahtar] = set()
    for satir in sirali:
        anahtar = xref_natural_key(satir)
        if anahtar in gorulen:
            raise GirdiHatasi(f"yinelenen xref dogal anahtari: {anahtar[1]}")
        gorulen.add(anahtar)
    return b"".join(satir_baytlari(s) for s in sirali), len(sirali)


def xrefs_yaz(yol: Path, satirlar: Iterable[XrefSatiri]) -> lineage.Cikti:
    """`xrefs.jsonl` dosyasini yazar; icerik ayniysa dosyaya dokunmaz (idempotent)."""
    veri, sayi = xrefs_baytlari(satirlar)
    if not (yol.is_file() and yol.read_bytes() == veri):
        yol.parent.mkdir(parents=True, exist_ok=True)
        gecici = yol.with_name(yol.name + ".tmp")
        gecici.write_bytes(veri)
        lineage.atomik_degistir(gecici, yol)
    return lineage.Cikti(yol=str(yol.name), sha256=lineage.sha256_bayt(veri), satir=sayi)


def xrefs_yaz_baglam(ctx: "RunContext", satirlar: Iterable[XrefSatiri]) -> lineage.Cikti:
    """`staged/risale-atif-dizini/{run_id}/xrefs.jsonl` (`--dry-run`'da yazmaz)."""
    veri, sayi = xrefs_baytlari(satirlar)
    hedef = ctx.staged_dizin(KAYNAK_ID) / XREFS_ADI
    if not ctx.dry_run:
        hedef.parent.mkdir(parents=True, exist_ok=True)
        hedef.write_bytes(veri)
    return lineage.Cikti(
        yol=lineage.goreli_yol(ctx.veri_kok, hedef), sha256=lineage.sha256_bayt(veri), satir=sayi
    )


# --- birimden tespit --------------------------------------------------------------------


def birimden_tespitler(
    src_anchor: str,
    metin: str,
    marks: Iterable[Mapping[str, object]],
    *,
    tablo: atif_gramer.SureAdTablosu | None = None,
    tespitci: DiziTespitcisi | None = None,
    min_skor: float = 0.0,
) -> list[Tespit]:
    """Bir Risale biriminden atif (gramer) ve iktibas (arac) tespitlerini cikarir.

    Acik atiflar butun metinde aranir (dipnot gostermeleri de ayni gramerle). Arapca dizilerde
    yalniz `ar` isaretli araliklar araca verilir; arac yoksa yalniz atiflar uretilir.
    """
    sonuc: list[Tespit] = []
    for atif in atif_gramer.ayristir(metin, tablo).atiflar:
        ayrintilar: dict[str, EvidenceDegeri] = {
            **atif_gramer.evidence_sinyalleri(atif),
            "guven_kaynagi": GUVEN_KAYNAGI_GRAMER,
        }
        if atif.grup:
            ayrintilar["grup"] = f"g{atif.bas}-{atif.son}"
            ayrintilar["grup_boyutu"] = len(atif.ayetler)
        for ayet in atif.ayetler:
            sonuc.append(
                Tespit(
                    src_anchor,
                    atif.bas,
                    atif.son,
                    atif.sure,
                    ayet,
                    TUR_ATIF,
                    YONTEM_GRAMER,
                    YONTEM_GRAMER,
                    "1",
                    atif.guven,
                    atif.guven,
                    ayrintilar,
                )
            )
    if tespitci is None:
        return sonuc
    for dizi in arapca_dizi.isaretlerden(metin, marks):
        for es in tespitci.tespit_et(dizi.metin):
            if not 0 <= es.bas < es.son <= dizi.uzunluk:
                raise GirdiHatasi("arac eslesme araligi dizi disinda")
            skor = es.skor if es.skor is not None else VARSAYILAN_SKOR
            if skor < min_skor:
                continue
            ayrintilar = {
                "dizi_turu": dizi.tur,
                "guven_kaynagi": (
                    GUVEN_KAYNAGI_SKOR if es.skor is not None else GUVEN_KAYNAGI_VARSAYILAN
                ),
                "hedef_sayisi": len(es.ayetler),
            }
            if es.skor is None:
                ayrintilar["skor_yok"] = True
            if es.kelime_sayisi is not None:
                ayrintilar["kelime_sayisi"] = es.kelime_sayisi
            if len(es.ayetler) > 1:
                ayrintilar["grup"] = f"g{dizi.bas + es.bas}-{dizi.bas + es.son}"
                ayrintilar["grup_boyutu"] = len(es.ayetler)
            for sure, ayet in es.ayetler:
                sonuc.append(
                    Tespit(
                        src_anchor,
                        dizi.bas + es.bas,
                        dizi.bas + es.son,
                        sure,
                        ayet,
                        TUR_IKTIBAS,
                        YONTEM_ARAC,
                        tespitci.ad,
                        tespitci.surum,
                        skor,
                        skor,
                        ayrintilar,
                    )
                )
    return sonuc
