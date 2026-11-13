"""Atif ve iktibas testlerinin ortak yardimcilari (test degildir; ACIKCA SENTETIK veri).

Hicbir Kur'an, meal ya da sure adi metni yoktur: Arapca "kelimeler" Arapca harflerden kurala bagli
uretilen anlamsiz uc harfli dizilerdir (`links_yardimci.sozcuk`); Turkce metinler "Deneme paragrafi
1" gibi uydurmadir; sure adlari `Alfa`, `Beta` gibi uydurma adlardir.

Sentetik mushaf (12 ayet): `q:1:1` (besmele benzeri 4 kelime), `q:2:1`..`q:2:3` (10 kelime), ortak
bir 6 kelimelik kalibin gectigi `q:2:4`, `q:2:5`, `q:2:6` ve `q:3:3` (f = 4), `q:3:1` (imlai metinde
iki kelime birlesmis: kelime sayilari farkli), `q:3:2` (6 harfli kelimeler: bulanik eslesme) ve
ayni uc kelimelik `q:3:4` ile `q:3:5` (kisa ayet, f = 2).

`CitDunyasi`: sahte depo koku (kaynak kayitlari), sahte veri koku (Simple Clean `ingest` calismasi)
ve veritabani tohumu (`tohumla`); `enrich()`, `qa()` ve `yukle()` gercek komut govdelerini kosar.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur, ctx_kur
from links_yardimci import sozcuk
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_citations import komut_enrich_citations
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.enrich.baglantilar.girdi import Kelime
from mutalaa_pipeline.enrich.citations.indeks import (
    EslestirmeIndeksi,
    imlai_indeksi,
    uthmani_indeksi,
)
from mutalaa_pipeline.enrich.citations.kurallar import Ipuclari
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.qa.run_xref_atif import komut_qa_run_xref_atif
from mutalaa_pipeline.staged import satirlari_oku, units_yaz

UTHMANI = "tanzil-uthmani"
SIMPLE = "tanzil-simple-clean"
MEAL_O = "elmalili-meal"
MEAL_S = "elmalili-sade-meal"
KAYNAK = "xref-atif-iktibas"
ESKI_ETIKET = "xref_citations.jsonl"


def uzun(i: int) -> str:
    """6 harfli anlamsiz kelime: son harfi dusunce `fuzz.ratio` >= 80 kalir."""
    return sozcuk(i) + sozcuk(i + 400)


KALIP = tuple(range(140, 146))  # q:2:4, q:2:5, q:2:6 ve q:3:3'te ortak 6 kelimelik dizi

# capa -> kelime numaralari (sozcuk indisleri)
AYET_TOKENLERI: dict[str, tuple[str, ...]] = {
    "q:1:1": tuple(sozcuk(i) for i in (1, 2, 3, 4)),
    "q:2:1": tuple(sozcuk(i) for i in range(100, 110)),
    "q:2:2": tuple(sozcuk(i) for i in range(110, 120)),
    "q:2:3": tuple(sozcuk(i) for i in range(120, 130)),
    "q:2:4": tuple(sozcuk(i) for i in (*KALIP, 150, 151, 152, 153)),
    "q:2:5": tuple(sozcuk(i) for i in (160, 161, *KALIP, 170)),
    "q:2:6": tuple(sozcuk(i) for i in (*KALIP, 180, 181)),
    "q:3:1": tuple(sozcuk(i) for i in range(200, 210)),
    "q:3:2": tuple(uzun(i) for i in range(210, 218)),
    "q:3:3": tuple(sozcuk(i) for i in (*KALIP, 190, 191)),  # kalip 4. ayette (f = 4)
    "q:3:4": tuple(sozcuk(i) for i in (230, 231, 232)),  # kisa ayet (3 kelime), q:3:5 ile ayni
    "q:3:5": tuple(sozcuk(i) for i in (230, 231, 232)),
}
CAPALAR = tuple(AYET_TOKENLERI)
# imlai (Simple Clean) metninde q:3:1'in 4. ve 5. kelimesi tek kelime olarak yazilmis
IMLAI_BIRLESME_AYETI = "q:3:1"


def ayet_metni(capa: str) -> str:
    return " ".join(AYET_TOKENLERI[capa])


def simple_metni(capa: str) -> str:
    """Simple Clean metni: 1. sure disindaki ayet 1'ler besmele ile baslar; q:3:1'de birlesme."""
    tokenler = list(AYET_TOKENLERI[capa])
    if capa == IMLAI_BIRLESME_AYETI:
        tokenler[3:5] = [tokenler[3] + tokenler[4]]
    metin = " ".join(tokenler)
    _, sure, ayet = capa.split(":")
    if ayet == "1" and sure != "1":
        return ayet_metni("q:1:1") + " " + metin
    return metin


def ayet_ozeti(capa: str) -> str:
    return content_hash(ayet_metni(capa))[:16]


def kelimeler() -> list[Kelime]:
    sonuc: list[Kelime] = []
    for sira, capa in enumerate(CAPALAR):
        for no, tok in enumerate(AYET_TOKENLERI[capa], start=1):
            sonuc.append(Kelime(sira, no, f"{capa}:{no}", tok, None, None))
    return sonuc


def besmele_kirp(capa: str, tokenler: list[str]) -> list[str]:
    """Besmele onekini atar (hat bunu `simple_kelimeleri` ile yapar; metin kopyasi bellekte)."""
    _, sure, ayet = capa.split(":")
    return tokenler[4:] if ayet == "1" and sure != "1" else tokenler


def indeksler() -> tuple[EslestirmeIndeksi, EslestirmeIndeksi]:
    u = uthmani_indeksi(kelimeler(), len(CAPALAR))
    imlai = imlai_indeksi([besmele_kirp(c, simple_metni(c).split()) for c in CAPALAR], u)
    return u, imlai


BOS_IPUCLARI = Ipuclari((), ())

# --- paragraf kurucular (hepsi sentetik) -------------------------------------------------------


def paragraf(*parcalar: str, bas: str = "Deneme paragrafi 1") -> str:
    return " ".join((bas, *parcalar))


def meal_anchor(n: int, eser: str = "elmalili") -> str:
    return f"meal:{eser}:2:{n}"


# --- dunya -----------------------------------------------------------------------------------


def tohumla(
    conn: psycopg.Connection,
    mealler: dict[str, list[tuple[str, str]]],
    *,
    hash_eki: str = "",
) -> None:
    """Kaynak satirlari, ayet birimleri, kelimeler ve meal birimleri (hat bunlari yazmaz)."""
    for slug, tur in (
        (UTHMANI, "kuran_metni"),
        (MEAL_O, "meal"),
        (MEAL_S, "meal"),
    ):
        conn.execute(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni)"
            " VALUES (%s, %s::icerik.source_kind, 'Deneme', '1', 'Deneme atif')",
            (slug, tur),
        )
    for sira, capa in enumerate(CAPALAR, start=1):
        metin = ayet_metni(capa)
        conn.execute(
            "INSERT INTO icerik.unit (anchor, kind, role, source_id, ord, metin, content_hash,"
            " data_version) VALUES (%s, 'ayet', 'govde', %s, %s, %s, %s, 'deneme')",
            (capa, UTHMANI, sira, metin, content_hash(metin + hash_eki)),
        )
        _, sure, ayet = capa.split(":")
        bas = 0
        for no, tok in enumerate(AYET_TOKENLERI[capa], start=1):
            conn.execute(
                "INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index,"
                " text_uthmani, norm, char_start, char_end, source_id, data_version)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'deneme')",
                (
                    f"{capa}:{no}",
                    int(sure),
                    int(ayet),
                    no,
                    sira,
                    tok,
                    tok,
                    bas,
                    bas + len(tok),
                    UTHMANI,
                ),
            )
            bas += len(tok) + 1
    sira = 0
    for slug, birimler in mealler.items():
        for capa, metin in birimler:
            sira += 1
            conn.execute(
                "INSERT INTO icerik.unit (anchor, kind, role, source_id, ord, metin, content_hash,"
                " data_version) VALUES (%s, 'meal', 'govde', %s, %s, %s, %s, 'deneme')",
                (capa, slug, sira, metin, content_hash(metin)),
            )


@dataclass
class CitDunyasi:
    """Sentetik zincir; `enrich()`, `qa()` ve `yukle()` gercek komut govdelerini kosar."""

    tmp: Path
    kok: Path
    veri: Path
    conn: psycopg.Connection

    def enrich(
        self,
        hedefler: tuple[str, ...] = (MEAL_O, MEAL_S),
        *,
        dry_run: bool = False,
    ) -> int:
        return komut_enrich_citations(
            hedefler=list(hedefler),
            dry_run=dry_run,
            force=False,
            config=None,
            kok=self.kok,
            baglanti=lambda: self.conn,
            beklenen_ayet=None,
        )

    def qa(self, *, gate: list[str] | None = None, db: bool = False) -> int:
        return komut_qa_run_xref_atif(run=None, gate=gate, config=None, kok=self.kok, db=db)

    def yukle(self, *, dry_run: bool = False) -> int:
        return pg.komut_export_pg(
            ayarlar_kur(self.tmp),
            depo_kok=self.kok,
            source=KAYNAK,
            dry_run=dry_run,
            baglanti=lambda: self.conn,
        )

    def hepsi(self, hedefler: tuple[str, ...] = (MEAL_O, MEAL_S)) -> int:
        assert self.enrich(hedefler) == 0
        assert self.qa() == 0
        return self.yukle()

    def son_enrich(self) -> Path:
        sonuc = lineage.son_basarili(self.veri / "staged" / KAYNAK, "enrich")
        assert sonuc is not None
        return sonuc[1]

    def satirlar(self) -> list[dict[str, object]]:
        yol = self.son_enrich() / ESKI_ETIKET
        return [s.veri for s in satirlari_oku(yol.read_bytes(), ESKI_ETIKET, bos_olabilir=True)]

    def manifest(self) -> dict[str, object]:
        manifest = lineage.manifest_oku(self.son_enrich())
        assert manifest is not None
        return manifest

    def yukleme_sayilari(self) -> dict[str, int]:
        raporlar = [
            json.loads(p.read_bytes()) for p in sorted((self.veri / "reports").glob("*.json"))
        ]
        yuklemeler = [
            r
            for r in raporlar
            if r.get("komut") == "export pg" and r["parametreler"]["source"] == KAYNAK
        ]
        assert yuklemeler
        sayilar = yuklemeler[-1]["sayilar"]
        assert isinstance(sayilar, dict)
        return sayilar


def dunya_kur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection
) -> CitDunyasi:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur(UTHMANI, tur="kuran_metni", baslik="Deneme Uthmani", surum="1.1"))
    kayit_yaz(kok, alanlar_kur(SIMPLE, tur="kuran_metni", baslik="Deneme Simple", surum="1.1"))
    kayit_yaz(kok, alanlar_kur(MEAL_O, tur="meal", baslik="Deneme meal", surum="1"))
    kayit_yaz(kok, alanlar_kur(MEAL_S, tur="meal", baslik="Deneme sade meal", surum="1"))
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    d = CitDunyasi(tmp_path, kok, veri, conn)
    ctx = ctx_kur(tmp_path, kok, adim="ingest", kaynaklar=[SIMPLE], temiz_git=True)
    satirlar = [
        {"anchor": c, "text": simple_metni(c), "source_id": SIMPLE, "attrs": {}} for c in CAPALAR
    ]
    cikti = units_yaz(ctx, SIMPLE, satirlar)
    ctx.manifest_yaz(ctx.staged_dizin(SIMPLE), girdiler=[], ciktilar=[cikti], parmak="0" * 64)
    return d
