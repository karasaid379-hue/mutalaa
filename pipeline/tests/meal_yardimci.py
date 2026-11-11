# ruff: noqa: RUF001
"""Meal testlerinin ortak yardimcilari (test degildir; ACIKCA SENTETIK veri).

`meal_kok_kur`: `tmp_path` altinda uc kaynagin (Vikikaynak API yanitlari, fawazahmed0 JSON'u,
EPUB) 6.236 ayetlik SENTETIK gelen klasorlerini ve bunlara karsilik gelen sentetik kilidi yazar;
kilit yolu `meal_kilit.KILIT_YOLU` yamayla bu kilide cevrilir. Hicbir Kuran, meal, tefsir, hadis ya
da Risale metni yoktur: butun ayet metinleri "Deneme meal parcasi S-N" biciminde uretilir.

Sentetik sayfalar bilerek sinir durumlarini tasir (sure numarasi: durum):

    2 sarmalayici sablon  3 `10-11` aralikli (birlesik)  4 ardisik isaretler 20, 21 (birlesik)
    5 ardisik olmayan ortak metin 30 ve 40  6 numarasiz isaret (5'ten sonra)
    7 yinelenen 12  8 sayfa sonu kapanis etiketi  9 besmele isareti YOK (sure 9)
   10 ilk isaretten onceki sayfa basi metni
"""

import hashlib
import io
import json
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import pytest
from typer.testing import CliRunner, Result

from mutalaa_pipeline import cli
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.ingest import meal_kilit
from mutalaa_pipeline.ingest.meal_kilit import (
    DosyaKilidi,
    EpubKilidi,
    MealKilidi,
    SadeKilidi,
    SayfaKilidi,
    VikikaynakKilidi,
    kilit_metni,
)

TARIH: Final = "2026-11-11"
BASLIK_HEADER: Final = "{{Eser başlığı\n|başlık = Deneme\n|notlar = Deneme notu\n}}\n"
SADE_COMMIT: Final = "0123456789abcdef0123456789abcdef01234567"


def _sha256(veri: bytes) -> str:
    return hashlib.sha256(veri).hexdigest()


def _sha1(veri: bytes) -> str:
    return hashlib.sha1(veri, usedforsecurity=False).hexdigest()


def isaret(deger: object, metin: str) -> str:
    return "{{kısım||" + str(deger) + "}}" + metin + "\n"


def sayfa_wikitext(sure: int) -> str:
    """Bir sentetik sure sayfasi (sinir durumlariyla; yukaridaki tablo)."""
    n = AYET_SAYILARI[sure - 1]
    atla: set[int] = set()
    govde: list[str] = []
    for a in range(1, n + 1):
        if a in atla:
            continue
        m = f"Deneme meal parçası {sure}-{a}"
        if sure == 3 and a == 10:
            govde.append(isaret("10-11", f"Deneme birleşik parça {sure}-10-11"))
            atla.add(11)
        elif sure == 4 and a == 20:
            govde.append("{{kısım||20}}{{kısım||21}}Deneme birleşik parça 4-20-21\n")
            atla.add(21)
        elif sure == 5 and a == 30:
            govde.append("{{kısım||30}}{{kısım||40}}Deneme ortak parça 5\n")
        elif sure == 5 and a == 40:
            continue  # 40, 30 ile birlikte yukarida verildi
        elif sure == 6 and a == 5:
            govde.append(isaret(a, m))
            govde.append(isaret(",", "Deneme numarasız ek parça"))
        elif sure == 7 and a == 12:
            govde.append(isaret(a, m + " a"))
            govde.append(isaret(a, m + " b"))
        else:
            govde.append(isaret(a, m))
    icerik = "".join(govde)
    if sure == 2:
        return BASLIK_HEADER + "{{Ortalı ve hizalı|\n" + icerik + "}}"
    if sure == 8:
        return BASLIK_HEADER + icerik + "</div>"
    if sure == 10:
        return BASLIK_HEADER + "Deneme sayfa başı notu\n" + icerik
    return BASLIK_HEADER + icerik


def baslik(sure: int) -> str:
    return f"Kur'an/Deneme {sure:03d} Suresi"


@dataclass(frozen=True)
class MealKoku:
    veri: Path  # data/ (MUTALAA_VERI_KOK)
    kilit: MealKilidi
    kilit_yolu: Path
    wikitextler: dict[int, str]


def _yanit(sayfalar: list[dict[str, object]], devam: bool) -> bytes:
    belge: dict[str, object] = {"batchcomplete": True, "query": {"pages": sayfalar}}
    if devam:
        belge["continue"] = {"gapcontinue": "x", "continue": "gapcontinue||"}
    return json.dumps(belge, ensure_ascii=False).encode("utf-8")


def sentetik_epub(yinelenen: bool = True) -> bytes:
    """6 bolumlu sentetik EPUB: her `<h2>` bir sure; ayet numarasi metnin SONUNDA `(N)`."""
    bolumler: list[list[str]] = [[] for _ in range(6)]
    for sure in range(1, 115):
        kova = bolumler[(sure - 1) * 6 // 114]
        parcalar: list[str] = [f'<h2 id="s{sure}">Deneme başlık {sure}</h2>']
        paragraf: list[str] = []
        n = AYET_SAYILARI[sure - 1]
        for a in range(1, n + 1):
            if sure == 12 and a == 3:
                continue  # numara boslugu: (3) yok, parca (4)'e kapsam [3, 4] olur
            paragraf.append(f"Deneme meal parçası {sure}-{a} ({a})")
            if yinelenen and sure == 13 and a == 4:
                paragraf.append(f"Deneme yinelenen parça ({a})")
            if len(paragraf) == 8:
                parcalar.append("<p>" + " ".join(paragraf) + "</p>")
                paragraf = []
        if paragraf:
            parcalar.append("<p>" + " ".join(paragraf) + "</p>")
        kova.append("\n".join(parcalar))
    cikti = io.BytesIO()
    with zipfile.ZipFile(cikti, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("mimetype", "application/epub+zip")
        for i, kova in enumerate(bolumler, start=1):
            html = (
                '<?xml version="1.0" encoding="utf-8"?>\n<html><head><meta charset="utf-8"/>'
                f"<title>Bölüm {i}</title></head><body><h1>Bölüm {i}</h1>\n"
                + "\n".join(kova)
                + "\n</body></html>"
            )
            z.writestr(f"OEBPS/text/chap{i:02d}.xhtml", html)
    return cikti.getvalue()


def sentetik_sade() -> bytes:
    kayitlar = [
        {"chapter": s, "verse": a, "text": f"Deneme sade parça {s}-{a}"}
        for s in range(1, 115)
        for a in range(1, AYET_SAYILARI[s - 1] + 1)
    ]
    return json.dumps({"quran": kayitlar}, ensure_ascii=False).encode("utf-8")


def meal_kok_kur(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    ozel_wikitext: dict[int, str] | None = None,
    epub_yinelenen: bool = True,
) -> MealKoku:
    """Sentetik gelen klasorleri ve kilidi yazar; `MUTALAA_VERI_KOK` ve kilit yolu yamalanir."""
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    wikitextler = {s: sayfa_wikitext(s) for s in range(1, 115)}
    wikitextler.update(ozel_wikitext or {})

    # --- Vikikaynak: uc API yaniti ve basliklar.tsv ---------------------------------------
    gelen = veri / "gelen" / "elmalili-meal" / TARIH
    gelen.mkdir(parents=True)
    sayfalar_json: list[dict[str, object]] = []
    sayfa_kilitleri: list[SayfaKilidi] = []
    for sure in range(1, 115):
        ham = wikitextler[sure].encode("utf-8")
        revid = 1000 + sure
        sayfalar_json.append(
            {
                "pageid": 5000 + sure,
                "ns": 0,
                "title": baslik(sure),
                "revisions": [
                    {
                        "revid": revid,
                        "parentid": 1,
                        "timestamp": "2019-10-19T20:46:44Z",
                        "size": len(ham),
                        "sha1": _sha1(ham),
                        "slots": {
                            "main": {
                                "contentmodel": "wikitext",
                                "contentformat": "text/x-wiki",
                                "content": wikitextler[sure],
                            }
                        },
                    }
                ],
            }
        )
        sayfa_kilitleri.append(SayfaKilidi(baslik(sure), sure, revid, _sha1(ham), _sha256(ham)))
    yanitlar = {
        "vikikaynak-01.json": _yanit(sayfalar_json[:50], True),
        "vikikaynak-02.json": _yanit(sayfalar_json[50:100], True),
        "vikikaynak-03.json": _yanit(sayfalar_json[100:], False),
    }
    liste = "".join(
        f"{s.baslik}\t{s.revid}\n" for s in sorted(sayfa_kilitleri, key=lambda s: s.baslik)
    ).encode("utf-8")
    dosyalar_v = {**yanitlar, "basliklar.tsv": liste}
    for ad, v in dosyalar_v.items():
        (gelen / ad).write_bytes(v)
    viki = VikikaynakKilidi(
        url=meal_kilit.VIKIKAYNAK_URL,
        alinma_tarihi=TARIH,
        liste_sha256=_sha256(liste),
        dosyalar=tuple(
            sorted(
                (DosyaKilidi(ad, len(v), _sha256(v)) for ad, v in dosyalar_v.items()),
                key=lambda d: d.ad,
            )
        ),
        sayfalar=tuple(sayfa_kilitleri),
    )

    # --- sade JSON ------------------------------------------------------------------------
    sade_veri = sentetik_sade()
    g = veri / "gelen" / "elmalili-sade-meal" / TARIH
    g.mkdir(parents=True)
    (g / "tur-elmallsadelesti.json").write_bytes(sade_veri)
    sade = SadeKilidi(
        url=meal_kilit.SADE_URL.format(commit=SADE_COMMIT),
        commit=SADE_COMMIT,
        alinma_tarihi=TARIH,
        dosya=DosyaKilidi("tur-elmallsadelesti.json", len(sade_veri), _sha256(sade_veri)),
    )

    # --- EPUB tanigi ----------------------------------------------------------------------
    epub_veri = sentetik_epub(epub_yinelenen)
    g = veri / "gelen" / "elmalili-meal-epub" / TARIH
    g.mkdir(parents=True)
    (g / "meal-i-serif.epub").write_bytes(epub_veri)
    epub = EpubKilidi(
        oge=meal_kilit.EPUB_OGE,
        uzak_dosya="Deneme.epub",
        url=meal_kilit.EPUB_URL.format(oge=meal_kilit.EPUB_OGE, dosya="Deneme.epub"),
        alinma_tarihi=TARIH,
        sha1=_sha1(epub_veri),
        dosya=DosyaKilidi("meal-i-serif.epub", len(epub_veri), _sha256(epub_veri)),
    )

    kilit = MealKilidi(viki, sade, epub)
    yol = tmp_path / "sentetik.lock.json"
    yol.write_bytes(kilit_metni(kilit).encode("utf-8"))
    monkeypatch.setattr(meal_kilit, "KILIT_YOLU", yol)
    return MealKoku(veri, kilit, yol, wikitextler)


# --- zincir kosucusu ve sablon/kopya ----------------------------------------------------------


def komut(*arglar: str) -> Result:
    return CliRunner().invoke(cli.app, list(arglar))


def ingest(kaynak: str, *ek: str) -> Result:
    return komut("ingest", "meal", "--source", kaynak, *ek)


def zincir_kos(slug: str) -> None:
    """normalize -> anchor -> qa; her adim 0 ile bitmeli."""
    for adim in (["normalize"], ["anchor"], ["qa", "run"]):
        sonuc = komut(*adim, "--source", slug)
        assert sonuc.exit_code == 0, (adim, sonuc.stdout, sonuc.stderr)


def tam_zincir_kur(tmp_dir: Path, mp: pytest.MonkeyPatch) -> MealKoku:
    """Sentetik gelen dosyalari ve tam zincir (ingest x3, normalize x2, anchor x2, qa x2)."""
    kok = meal_kok_kur(tmp_dir, mp)
    for slug in ("elmalili-meal-epub", "elmalili-sade-meal", "elmalili-meal"):
        sonuc = ingest(slug)
        assert sonuc.exit_code == 0, (slug, sonuc.stderr)
    zincir_kos("elmalili-sade-meal")  # sadelestirme taramasi guncel mealin staged'ini ister
    zincir_kos("elmalili-meal")
    return kok


def kopya_al(sablon: MealKoku, hedef_ust: Path, mp: pytest.MonkeyPatch) -> MealKoku:
    """Sablonun yazilabilir kopyasi `hedef_ust/data`; ortam ve kilit yolu bu kopyaya cevrilir."""
    yeni = hedef_ust / "data"
    shutil.copytree(sablon.veri, yeni)
    mp.setenv("MUTALAA_VERI_KOK", str(yeni))
    mp.setattr(meal_kilit, "KILIT_YOLU", sablon.kilit_yolu)
    return MealKoku(yeni, sablon.kilit, sablon.kilit_yolu, sablon.wikitextler)
