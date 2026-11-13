# ruff: noqa: RUF001
"""Sentetik Risale fiksturu (A20.5a, K-46 madde 9): `test-risale-ornek`, kitap `test-ornek`.

`mutalaa ingest risale --source test-risale-ornek` icin hazir govde (`komut_ingest_ornek`; CLI
kaydi birlestirmede yapilir). Disaridan dosya almaz (`data/gelen` ve `data/raw` kullanilmaz);
birimleri kodla uretir. Ayni surumde ayni baytlar cikar (zaman, rastgelelik, ortam yok).

Metin ACIKCA SENTETIKTIR ("Deneme paragrafi N ..."): hicbir Risale-i Nur, Kur'an, hadis ya da dua
metnine benzetilmez; Arapca blok Arap alfabesinin harflerinden olusur (ayet, hadis ya da dua
degil). Kendi urettigimiz metin oldugu icin her metne uretimde BIR KEZ `kanonik_metin` (K-35
madde 7: silinecekler, NFC, satir sonu ve bosluk) uygulanir; sonraki adimlar metne dokunmaz.

Cikti, gercek RNK yolunun (`ingest/risale_rnk_staged.py`) sema bicimiyle bire bir aynidir:
`units.jsonl` birimleri ayni `attrs` alanlarini (`kind`, `slug`, `bolum_yolu`, `p`, `baslik_yolu`,
`dil`, `yon`, `marks`, `sayfa`, baslikta `baslik_duzeyi`/`json_dugum`, hasiyede `hasiye_no`) ve
ayni `provenance` yer tutucularini (`file`, `raf`, `uid`, `konum.satir`) tasir; `sayfalar.jsonl`
RNK `sayfalar` biciminde (`dosya`, `n`, `satir`, `capa`, `ofs`, `tur`) yazilir. Boylece
`adimlar/risale.py` (normalize ve anchor) ve `adimlar/risale_ornek.py` (page_map ve xref) ayni
kodla calisir.

Yapi (kitap `test-ornek`, `dil = tr`, `yon = ltr`):

    rn:test-ornek:p1                        kitap koku paragrafi
    rn:test-ornek:bolum-1:p1..p5            baslik, kisa atif paragrafi, uzun paragraf (cumle
                                            siniri, sayfa kirilmasi), Arapca blok (`ar` marks),
                                            hasiye isaretli paragraf
    rn:test-ornek:bolum-1:hasiye-1:p1       hasiye (dipnot) birimi
    rn:test-ornek:bolum-1:hakikat-1:p1..p3  ic ice bolum
    rn:test-ornek:parca-1:p1..p3            lahika tarzi parca bolumu

Sayfalar (volume 1, sentetik dosya `ornek/test-ornek`): sayfa 1 kitap kokunde, sayfa 2 UZUN
paragrafin ICINDE (cumle ortasi), sayfa 3 `hakikat-1` basliginda, sayfa 4 `parca-1:p2`de,
sayfa 5 icerigi olmayan son sayfadir (`icerik-yok`).

Capalar `rn:test-ornek:...` gercek slug listesine (`risale-kitaplar.json`), kullanici verisine ya
da kalici capa kaydina YAZILMAZ (A20.5a).

Sentetik `xref` (K-46 madde 9; `xref_satirlari`): iki `aday` baglanti, `origin = 'hat'`,
`evidence.fikstur = true`, kaynak ucu fikstur paragrafi (aralik `src_span` sutununda, kod noktasi,
yari acik), hedef ucu bir ayet capasi (yalniz ADRES; Kur'an metni yazilmaz). Staged JSON ondalik
sayi tasimaz (`kati_json`), bu yuzden `score` ve `confidence` tam sayi degerlidir (0 ya da 1).
"""

import sys
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.anchor import kanonik_metin, parse, sort_key, to_unit_span
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest, units_satiri
from mutalaa_pipeline.ingest.lugat_madde import LUGAT_ADI, MADDE_ANAHTARI
from mutalaa_pipeline.ingest.risale_ornek_lugat import ADET as LUGAT_ADET
from mutalaa_pipeline.ingest.risale_ornek_lugat import ornek_lugat_baytlari, ornek_lugat_satirlari
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz, yapi_baytlari

KAYNAK: Final = "test-risale-ornek"
KITAP: Final = "test-ornek"
URETEC_SURUMU: Final = "1"
INGEST_ADIMI: Final = "ingest"
SAYFALAR_ADI: Final = "sayfalar.jsonl"
SAYFA_ANAHTARI: Final = ("dosya", "n")
DIL: Final = "tr"
YON: Final = "ltr"
# Sentetik RNK dosyasi `{raf}/{uid}`; `volume` sentetik cilt numarasidir (page_map).
RAF: Final = "ornek"
UID: Final = "test-ornek"
DOSYA: Final = f"{RAF}/{UID}"
CILT: Final = 1
ANCHOR_ONEKI: Final = f"rn:{KITAP}:"

TUR_BASLIK: Final = "baslik"
TUR_PARAGRAF: Final = "paragraf"
TUR_HASIYE: Final = "hasiye"
SAYFA_BAS: Final = "bas"
SAYFA_ORTASI: Final = "ortasi"
SAYFA_ICERIK_YOK: Final = "icerik-yok"

B1: Final = "bolum-1"
H1: Final = "hakikat-1"
PARCA: Final = "parca-1"
HASIYE: Final = "hasiye-1"

ARAPCA_BLOK: Final = "ا ب ت ث! ج ح خ"  # Arap alfabesinin harfleri (ayet, hadis, dua degil)
ATIF_PARCASI: Final = "sentetik atıf işareti"
SAYFA_KIRILMA_PARCASI: Final = "ve metin aynı cümleyle devam eder"
HASIYE_NOKTASI: Final = "; işaret metnin ortasındadır"

BASLIKLAR: Final[Mapping[tuple[str, ...], str]] = {
    (B1,): "Deneme bölüm başlığı 1",
    (B1, H1): "Deneme bölüm başlığı 2",
    (PARCA,): "Deneme bölüm başlığı 3",
}

HASIYE_CAPASI: Final = f"{ANCHOR_ONEKI}{B1}:{HASIYE}:p1"
UZUN_CAPA: Final = f"{ANCHOR_ONEKI}{B1}:p3"
ATIF_CAPASI: Final = f"{ANCHOR_ONEKI}{B1}:p2"
ARAPCA_CAPASI: Final = f"{ANCHOR_ONEKI}{B1}:p4"


@dataclass(frozen=True)
class Taslak:
    """Bir birimin ham tanimi (metin henuz kanonik degil)."""

    yol: tuple[str, ...]  # kitap haric bolum yolu; hasiyede son parca `hasiye-n`
    p: int
    tur: str
    ham: str
    json_dugum: tuple[int, int, int] | None = None  # baslikta (sira, pageNo, derinlik)
    sayfa_basi: bool = False  # birim yeni bir sayfanin ilk metnidir (ofs 0)
    sayfa_kirilma: str | None = None  # bu parcanin basinda (birimin ICINDE) yeni sayfa baslar
    arapca: str | None = None  # `ar` isaretli parca
    hasiye_noktasi: str | None = None  # hasiye isaretinin konumu: bu parcanin baslangici


TASLAKLAR: Final[tuple[Taslak, ...]] = (
    Taslak(
        (),
        1,
        TUR_PARAGRAF,
        "Deneme paragrafı 1 kitap kökündeki sentetik paragraftır.",
        sayfa_basi=True,
    ),
    Taslak((B1,), 1, TUR_BASLIK, BASLIKLAR[(B1,)], (1, 1, 1)),
    Taslak(
        (B1,), 2, TUR_PARAGRAF, f"Deneme paragrafı 2 {ATIF_PARCASI} taşıyan kısa bir paragraftır."
    ),
    Taslak(
        (B1,),
        3,
        TUR_PARAGRAF,
        "Deneme paragrafı 3 uzun bir sentetik paragraftır. Bu paragraf cümle sınırlarını"
        " sınamak için birkaç cümleden oluşur. Üçüncü cümle, sayfa kırılmasının cümle ortasına"
        f" düşmesi için bilerek uzun yazılmıştır; sayfa burada kesilir {SAYFA_KIRILMA_PARCASI}."
        " Dördüncü cümle kısadır. Son cümle paragrafın sentetik veri olduğunu belirtir.",
        sayfa_kirilma=SAYFA_KIRILMA_PARCASI,
    ),
    Taslak(
        (B1,),
        4,
        TUR_PARAGRAF,
        f"Deneme paragrafı 4 Arap alfabesinden harfler içerir: {ARAPCA_BLOK} işaretidir."
        " Ardından Türkçe bir cümle gelir, harfler ayet, hadis ya da dua değildir.",
        arapca=ARAPCA_BLOK,
    ),
    Taslak(
        (B1,),
        5,
        TUR_PARAGRAF,
        f"Deneme paragrafı 5 bir dipnot işareti taşır{HASIYE_NOKTASI}, dipnot ayrı birimdir.",
        hasiye_noktasi=HASIYE_NOKTASI,
    ),
    Taslak(
        (B1, HASIYE),
        1,
        TUR_HASIYE,
        "Deneme paragrafı 1 dipnot olarak yazılmış sentetik bir paragraftır.",
    ),
    Taslak((B1, H1), 1, TUR_BASLIK, BASLIKLAR[(B1, H1)], (2, 3, 2), sayfa_basi=True),
    # NFD "I + U+0307": ilk kayit adimi (NFC) onu "İ" yapar.
    Taslak(
        (B1, H1),
        2,
        TUR_PARAGRAF,
        "Deneme paragrafı 2 İlk ılık sabah için İ ve ı harfleri bir arada kullanıldı;"
        " Işık sözcüğü yalnız burada geçer.",
    ),
    Taslak((B1, H1), 3, TUR_PARAGRAF, "Deneme paragrafı 3 kısa tutuldu."),
    # json pageNo bilerek 4: gercek `#n` sayfasi 3'tur (page_map raporunda `json_sayfa_farkli`).
    Taslak((PARCA,), 1, TUR_BASLIK, BASLIKLAR[(PARCA,)], (3, 4, 1)),
    Taslak(
        (PARCA,),
        2,
        TUR_PARAGRAF,
        "Deneme paragrafı 2 yeni sayfanın başında başlar.",
        sayfa_basi=True,
    ),
    Taslak((PARCA,), 3, TUR_PARAGRAF, "Deneme paragrafı 3 son paragraftır."),
)


@dataclass(frozen=True)
class OrnekBirimi:
    anchor: str
    text: str  # kanonik metin
    tur: str
    bolum_yolu: tuple[str, ...]
    p: int
    baslik_yolu: tuple[str, ...]
    marks: tuple[Mapping[str, object], ...]
    sayfa: int  # birimin ilk satirinin sayfasi
    ilk_satir: int
    son_satir: int
    json_dugum: tuple[int, int, int] | None
    hasiye_no: int | None


def _capa(yol: tuple[str, ...], p: int) -> str:
    return ":".join(("rn", KITAP, *yol, f"p{p}"))


def _bul(metin: str, parca: str, ad: str) -> int:
    sira = metin.find(parca)
    if sira < 0 or metin.find(parca, sira + 1) >= 0:
        raise GirdiHatasi(f"fikstur {ad}: parca metinde tam bir kez gecmiyor")
    return sira


def _basliklar(bolum_yolu: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(BASLIKLAR[bolum_yolu[: n + 1]] for n in range(len(bolum_yolu)))


def birimler() -> list[OrnekBirimi]:
    """Birimler okuma sirasinda; satir numaralari sentetik RNK `txt` duzenindedir."""
    sonuc: list[OrnekBirimi] = []
    satir = 0
    sayfa = 0
    for t in TASLAKLAR:
        metin = kanonik_metin(t.ham)
        capa = _capa(t.yol, t.p)
        hasiye = t.tur == TUR_HASIYE
        bolum_yolu = t.yol[:-1] if hasiye else t.yol
        if t.sayfa_basi:
            satir += 1  # `#n` satiri
            sayfa += 1
        ilk = satir + 1
        son = ilk
        gecen_sayfa = sayfa
        if t.sayfa_kirilma is not None:
            satir_ek = 2  # birim, `#n` satiri, birimin devami
            son = ilk + satir_ek
            sayfa += 1
        satir = son
        isaretler: list[Mapping[str, object]] = []
        if t.arapca is not None:
            bas = _bul(metin, t.arapca, capa)
            isaretler.append({"t": "ar", "s": bas, "e": bas + len(t.arapca), "tur": "blok"})
        if t.hasiye_noktasi is not None:
            konum = _bul(metin, t.hasiye_noktasi, capa)
            isaretler.append({"t": "hasiye", "s": konum, "e": konum, "a": HASIYE_CAPASI})
        sonuc.append(
            OrnekBirimi(
                anchor=capa,
                text=metin,
                tur=t.tur,
                bolum_yolu=bolum_yolu,
                p=t.p,
                baslik_yolu=_basliklar(bolum_yolu),
                marks=tuple(isaretler),
                sayfa=gecen_sayfa,
                ilk_satir=ilk,
                son_satir=son,
                json_dugum=t.json_dugum,
                hasiye_no=1 if hasiye else None,
            )
        )
    return sonuc


def sayfalar() -> list[dict[str, object]]:
    """RNK `sayfalar.jsonl` bicimi: sayfa basi konumlari (cumle ortasina dusen sayfa dahil)."""
    kayitlar: list[dict[str, object]] = []
    sayfa = 0
    tum = birimler()
    for t, b in zip(TASLAKLAR, tum, strict=True):
        if t.sayfa_basi:
            sayfa += 1
            kayitlar.append(
                {
                    "dosya": DOSYA,
                    "n": sayfa,
                    "satir": b.ilk_satir - 1,
                    "capa": b.anchor,
                    "ofs": 0,
                    "tur": SAYFA_BAS,
                }
            )
        if t.sayfa_kirilma is not None:
            sayfa += 1
            kayitlar.append(
                {
                    "dosya": DOSYA,
                    "n": sayfa,
                    "satir": b.ilk_satir + 1,
                    "capa": b.anchor,
                    "ofs": _bul(b.text, t.sayfa_kirilma, b.anchor),
                    "tur": SAYFA_ORTASI,
                }
            )
    son_satir = tum[-1].son_satir
    kayitlar.append(
        {
            "dosya": DOSYA,
            "n": sayfa + 1,
            "satir": son_satir + 1,
            "capa": None,
            "ofs": 0,
            "tur": SAYFA_ICERIK_YOK,
        }
    )
    return kayitlar


def staged_birimleri() -> list[StagedUnit]:
    """Ingest `units.jsonl` birimleri: gercek RNK yoluyla ayni `attrs` ve `provenance` bicimi."""
    sonuc: list[StagedUnit] = []
    for b in birimler():
        attrs: dict[str, object] = {
            "kind": b.tur,
            "slug": KITAP,
            "bolum_yolu": list(b.bolum_yolu),
            "p": b.p,
            "baslik_yolu": list(b.baslik_yolu),
            "dil": DIL,
            "yon": YON,
            "marks": [dict(m) for m in b.marks],
            "sayfa": b.sayfa,
        }
        if b.tur == TUR_BASLIK:
            attrs["baslik_isareti"] = None
            if b.json_dugum is not None:
                sira, sayfa_no, duzey = b.json_dugum
                attrs["baslik_duzeyi"] = duzey
                attrs["json_dugum"] = {"sira": sira, "pageNo": sayfa_no}
            else:
                attrs["baslik_duzeysiz"] = True
        if b.tur == TUR_HASIYE:
            attrs["hasiye_no"] = b.hasiye_no
            attrs["etiket_bicimi"] = "-"
        sonuc.append(
            StagedUnit(
                anchor=b.anchor,
                text=b.text,
                attrs=attrs,
                provenance={
                    "kaynak": "fikstur",
                    "uretec": "risale-ornek",
                    "uretec_surumu": URETEC_SURUMU,
                    "file": f"{DOSYA}.txt",
                    "raf": RAF,
                    "uid": UID,
                    "konum": {"satir": [b.ilk_satir, b.son_satir]},
                },
            )
        )
    return sonuc


def icerik_baytlari() -> bytes:
    """Uretecin baytlari: `units.jsonl`, `sayfalar.jsonl` ve `lugat.jsonl` (parmak izi icin)."""
    sirali = sorted(staged_birimleri(), key=lambda b: sort_key(parse(b.anchor)))
    units = "".join(units_satiri(KAYNAK, b) for b in sirali).encode("utf-8")
    sayfa, _ = yapi_baytlari(sayfalar(), SAYFA_ANAHTARI)
    return units + sayfa + ornek_lugat_baytlari()


# --- sentetik xref -------------------------------------------------------------------------


@dataclass(frozen=True)
class XrefTanimi:
    tur: str
    kaynak_capa: str
    parca: str  # kaynak birim metninde tam bir kez gecen parca: `src_span` onun araligi
    hedef: str  # hedef capa (yalniz adres): `to_unit_span` ile `dst_anchor` + `dst_span`


# K-46 / A20.5a: fikstur paragrafindan bir ayet capasina; `aday`, `evidence.fikstur = true`.
# Hedefler yalniz ADRESTIR (Fatiha'nin ilk iki ayeti); fikstur hicbir Kur'an metni tasimaz. Gercek
# ayet capasi kullanilir, cunku sentetik `q:` capasi yoktur (Kur'an capalari Tanzil'den gelir).
XREFLER: Final[tuple[XrefTanimi, ...]] = (
    XrefTanimi("atif", ATIF_CAPASI, ATIF_PARCASI, "q:1:2"),
    XrefTanimi("iktibas", ARAPCA_CAPASI, ARAPCA_BLOK, "q:1:1:1-2"),
)
XREF_TURLERI: Final = frozenset({"atif", "iktibas"})


def xref_satirlari(metinler: Mapping[str, str], surum: str) -> list[dict[str, object]]:
    """Iki sentetik `xref` satiri; `metinler` capa -> kanonik metin (aralik metinden hesaplanir).

    Aralik kod noktasidir ve yari acik; `src_span` sutunu `[bas, son)` (`xref.src_span`). Satirlar
    dogal anahtarla `(type, src_anchor, src_span, dst_anchor, dst_span)` siralidir.
    """
    satirlar: list[dict[str, object]] = []
    for x in XREFLER:
        metin = metinler.get(x.kaynak_capa)
        if metin is None:
            raise GirdiHatasi(f"xref kaynak birimi yok: {x.kaynak_capa}")
        bas = _bul(metin, x.parca, x.kaynak_capa)
        son = bas + len(x.parca)
        kaynak = to_unit_span(parse(f"{x.kaynak_capa}@{bas}-{son}"))
        hedef = to_unit_span(parse(x.hedef))
        if kaynak.unit != x.kaynak_capa or kaynak.span != (bas, son):
            raise GirdiHatasi(f"xref kaynak ucu cozulemedi: {x.kaynak_capa}")
        satirlar.append(
            {
                "type": x.tur,
                "src_anchor": kaynak.unit,
                "src_span": [bas, son],
                "dst_anchor": hedef.unit,
                "dst_span": list(hedef.span) if hedef.span is not None else None,
                "score": 1,
                "confidence": 1,
                "evidence": {"fikstur": True, "source_id": KAYNAK, "yontem": "sentetik"},
                "origin": "hat",
                "status": "aday",
                "data_version": f"{KAYNAK}@{surum}",
            }
        )
    return satirlar


def dogal_anahtar(satir: Mapping[str, object]) -> tuple[object, ...]:
    """`xref_natural_key`: `(type, src_anchor, src_span, dst_anchor, dst_span)`."""

    def aralik(deger: object) -> tuple[int, int] | None:
        if deger is None:
            return None
        if not isinstance(deger, list) or len(deger) != 2:
            raise GirdiHatasi("xref aralik [bas, son] degil")
        return (int(deger[0]), int(deger[1]))

    return (
        satir["type"],
        satir["src_anchor"],
        aralik(satir["src_span"]),
        satir["dst_anchor"],
        aralik(satir["dst_span"]),
    )


# --- bagdastirici ----------------------------------------------------------------------------


class OrnekBagdastirici:
    """`SourceAdapter`: `fetch` dosya almaz, `parse` birimleri ve `sayfalar.jsonl` uretir."""

    source_id = KAYNAK

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        return []

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        dosya_yaz(ctx, KAYNAK, SAYFALAR_ADI, sayfalar(), anahtar=SAYFA_ANAHTARI)
        # Sentetik lugat (A20.6): ayni kaynak adinda 15 uydurma madde; `risale-dizin` Glossary
        # kaynagi ayni slug'dir (`export pg --source test-risale-ornek` birimlerle yukler).
        dosya_yaz(ctx, KAYNAK, LUGAT_ADI, ornek_lugat_satirlari(), MADDE_ANAHTARI)
        yield from staged_birimleri()

    def manifest_ayrintilari(self) -> dict[str, object]:
        return {
            "kaynak": KAYNAK,
            "uretec_surumu": URETEC_SURUMU,
            "kitap": KITAP,
            "birim": len(TASLAKLAR),
            "sayfa": len(sayfalar()),
            "lugat_madde": LUGAT_ADET,
            "cilt": {DOSYA: CILT},
        }


def komut_ingest_ornek(
    *,
    gelen_tarih: str | None,
    dry_run: bool,
    force: bool,
    config: Path | None,
    kok: Path | None,
) -> int:
    """`ingest risale --source test-risale-ornek` govdesi; cikis kodunu dondurur.

    `gelen_tarih` CLI ile ayni imza icin kabul edilir ve REDDEDILIR (cikis 2): fiksturun gelen
    dosyasi yoktur.
    """
    if gelen_tarih is not None:
        sys.stderr.write("hata: --gelen-tarih fikstur icin anlamsiz (dosya alinmaz)\n")
        return cikis.GIRDI_HATASI

    def govde(ctx: RunContext) -> int:
        sonuc = run_ingest(OrnekBagdastirici(), ctx)
        if sonuc.atlandi:
            ozet = f"atlandi (parmak izi onceki calistirmayla ayni, run {sonuc.onceki_run_id})"
        elif ctx.dry_run:
            ozet = f"{sonuc.birim_sayisi} birim (dry-run, hicbir sey yazilmadi)"
        else:
            ozet = f"{sonuc.birim_sayisi} birim, run {sonuc.run_id}"
        sys.stdout.write(f"ingest {KAYNAK}: {ozet}\n")
        return cikis.BASARILI

    parametreler: dict[str, object] = {
        "source": KAYNAK,
        "uretec_surumu": URETEC_SURUMU,
        "icerik_sha256": lineage.sha256_bayt(icerik_baytlari()),
    }
    return komutu_yurut(
        komut=f"ingest risale --source {KAYNAK}",
        adim=INGEST_ADIMI,
        kaynaklar=[KAYNAK],
        config=config,
        kok=kok,
        govde=govde,
        force=force,
        dry_run=dry_run,
        parametreler=parametreler,
    )


__all__ = [
    "ARAPCA_BLOK",
    "CILT",
    "DOSYA",
    "KAYNAK",
    "KITAP",
    "OrnekBagdastirici",
    "birimler",
    "dogal_anahtar",
    "icerik_baytlari",
    "komut_ingest_ornek",
    "sayfalar",
    "staged_birimleri",
    "xref_satirlari",
]
