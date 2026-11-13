"""Kur'an ici baglanti testlerinin ortak yardimcilari (test degildir; ACIKCA SENTETIK veri).

Hicbir Kur'an metni yoktur: kelimeler Arapca harflerden kurala bagli uretilen anlamsiz uc
harfli dizilerdir (`sozcuk(i)`), kok ve lemma kimlikleri tam sayidir. Dunya 10 ayetlik kucuk bir
mushaftir: `q:1:1` (besmele benzeri 4 kelime) ve `q:2:1` ... `q:2:9`.

`LinksDunyasi`: sahte depo koku (dort kaynak kaydi), sahte veri koku (Simple Clean `ingest`
calismasi ve QurSim dosyasi) ve veritabani tohumu (`tohumla`: kaynak, ayet birimleri, kok, lemma,
kelimeler); `enrich()`, `qa()` ve `yukle()` gercek komut govdelerini kosar.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from hat_yardimci import ayarlar_kur, ctx_kur
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_links import komut_enrich_links
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.export import pg
from mutalaa_pipeline.qa.run_xref import komut_qa_run_xref
from mutalaa_pipeline.staged import satirlari_oku, units_yaz

TARIH = "2026-11-12"
QAC = "qac-morfoloji"
UTHMANI = "tanzil-uthmani"
SIMPLE = "tanzil-simple-clean"
QURSIM = "qursim"
KAYNAK = "xref-baglantilar"
QURSIM_DOSYASI = "QurSim_filtered.csv"
KOK_ID = {1: 1, 2: 2, 8: 3, 9: 4}  # sentetik kok kimlikleri (testte kendi anahtarlariyla)
SUTUN_BASLIGI = ",ID,SS,SV,Verse1,TS,TV,Verse2,Label"

_HARFLER = [chr(c) for c in (0x0628, *range(0x062A, 0x0639), 0x0639, 0x063A)]  # hamzasiz, 18 harf


def sozcuk(i: int) -> str:
    """`i`. anlamsiz uc harfli Arapca-harf dizisi (normalize anahtari kendisidir)."""
    n = len(_HARFLER)
    return _HARFLER[i % n] + _HARFLER[(i // n) % n] + _HARFLER[(i // (n * n)) % n]


@dataclass(frozen=True)
class Ay:
    capa: str
    tokenler: tuple[int, ...]
    morf: tuple[tuple[int | None, int | None], ...]  # kelime basina (kok, lemma) kimlikleri


# Dunya: toplam 10 ayet (IDF paydasi 10). Kok 8 (df 6, idf_n 0,22) esigin altindadir.
YOK = (None, None)
AYETLER: tuple[Ay, ...] = (
    Ay("q:1:1", (1, 2, 3, 4), (YOK,) * 4),
    Ay("q:2:1", (10, 11, 12), ((1, 101), (2, 102), (9, 109))),
    Ay("q:2:2", (20, 21, 22), ((1, 101), (2, 103), YOK)),
    Ay("q:2:3", (30, 31), ((2, 102), YOK)),
    Ay("q:2:4", (60, 61, 62, 63, 64), ((8, 108),) * 5),
    Ay("q:2:5", (70, 60, 61, 62, 63, 71), ((8, 108),) * 6),
    Ay("q:2:6", (60, 61, 62, 80), ((8, 108),) * 4),
    Ay("q:2:7", (90, 91, 92, 93), ((8, 108),) * 4),
    Ay("q:2:8", (90, 91, 92, 93), ((8, 108),) * 4),
    Ay("q:2:9", (95, 96), ((8, 108),) * 2),
)
QURSIM_SATIRLARI = (
    ("q:2:7", "q:2:8", 2),  # kendi indeksimizde de aday: tek satir, sozluksel + qursim
    ("q:2:1", "q:2:3", 0),  # saf QurSim
    ("q:2:9", "q:2:2", 1),  # ters sirali, saf QurSim
)


def kok_harfleri(kok: int) -> tuple[str, str]:
    """Sentetik koku icin (letters, letters_bw): tekil, anlamsiz."""
    return f"{sozcuk(500 + kok)[0]}{sozcuk(600 + kok)}", f"r{kok}x"


def morf_kimlikleri() -> tuple[dict[int, int], dict[int, int]]:
    """(kok -> ayet sayisi, lemma -> ayet sayisi) sentetik dunyada."""
    kok: dict[int, set[str]] = {}
    lemma: dict[int, set[str]] = {}
    for ay in AYETLER:
        for r, lm in ay.morf:
            if r is not None:
                kok.setdefault(r, set()).add(ay.capa)
            if lm is not None:
                lemma.setdefault(lm, set()).add(ay.capa)
    return {k: len(v) for k, v in kok.items()}, {k: len(v) for k, v in lemma.items()}


def ayet_metni(ay: Ay) -> str:
    """Birimin (Uthmani) sentetik metni: kelimeler bosluklu."""
    return " ".join(sozcuk(t) for t in ay.tokenler)


def ayet_ozeti(ay: Ay, surum: str = "") -> str:
    return content_hash(ayet_metni(ay) + surum)


def tohumla(conn: psycopg.Connection, *, hash_eki: str = "") -> None:
    """Kaynak satirlari, ayet birimleri, kok, lemma ve kelimeler (hat bunlari yazmaz)."""
    for slug, tur in ((QAC, "morfoloji"), (UTHMANI, "kuran_metni")):
        conn.execute(
            "INSERT INTO icerik.source (slug, tur, baslik, surum, atif_metni)"
            " VALUES (%s, %s::icerik.source_kind, 'Deneme', '1', 'Deneme atif')",
            (slug, tur),
        )
    kok_sayilari, lemma_sayilari = morf_kimlikleri()
    for kok, sayi in sorted(kok_sayilari.items()):
        harf, bw = kok_harfleri(kok)
        conn.execute(
            "INSERT INTO icerik.root (id, letters, letters_bw, ayah_count, source_id, data_version)"
            " VALUES (%s, %s, %s, %s, %s, 'deneme')",
            (kok, harf, bw, sayi, QAC),
        )
    for lm in sorted(lemma_sayilari):
        metin = sozcuk(700 + lm)
        conn.execute(
            "INSERT INTO icerik.lemma (id, lang, text, text_clean, qac_ref, origin, status,"
            " source_id, data_version) VALUES (%s, 'ar', %s, %s, %s, 'qac', 'onayli', %s,"
            " 'deneme')",
            (lm, metin, metin, f"lm{lm}", QAC),
        )
    for sira, ay in enumerate(AYETLER, start=1):
        metin = ayet_metni(ay)
        conn.execute(
            "INSERT INTO icerik.unit (anchor, kind, role, source_id, ord, metin, content_hash,"
            " data_version) VALUES (%s, 'ayet', 'govde', %s, %s, %s, %s, 'deneme')",
            (ay.capa, UTHMANI, sira, metin, ayet_ozeti(ay, hash_eki)),
        )
        _, sure, ayet = ay.capa.split(":")
        bas = 0
        for no, (tok, (kok, lemma)) in enumerate(zip(ay.tokenler, ay.morf, strict=True), start=1):
            kelime = sozcuk(tok)
            conn.execute(
                "INSERT INTO icerik.quran_word (anchor, surah, ayah, word, ayah_index,"
                " text_uthmani, norm, char_start, char_end, root_id, lemma_id, source_id,"
                " data_version)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'deneme')",
                (
                    f"{ay.capa}:{no}",
                    int(sure),
                    int(ayet),
                    no,
                    sira,
                    kelime,
                    kelime,
                    bas,
                    bas + len(kelime),
                    kok,
                    lemma,
                    UTHMANI,
                ),
            )
            bas += len(kelime) + 1


def simple_metni(ay: Ay) -> str:
    """Simple Clean sentetik metni: sure basi ayetler (1. sure disinda) besmeleyle baslar."""
    metin = ayet_metni(ay)
    _, sure, ayet = ay.capa.split(":")
    if ayet == "1" and sure != "1":
        return ayet_metni(AYETLER[0]) + " " + metin
    return metin


@dataclass
class LinksDunyasi:
    """Sentetik zincir; `enrich()`, `qa()` ve `yukle()` gercek komut govdelerini kosar."""

    tmp: Path
    kok: Path
    veri: Path
    conn: psycopg.Connection

    def enrich(self, tur: str = "hepsi", *, dry_run: bool = False) -> int:
        return komut_enrich_links(
            tur=tur,
            gelen_tarih=None,
            dry_run=dry_run,
            force=False,
            config=None,
            kok=self.kok,
            baglanti=lambda: self.conn,
            beklenen_ayet=None,
        )

    def qa(self, *, gate: list[str] | None = None) -> int:
        return komut_qa_run_xref(run=None, gate=gate, config=None, kok=self.kok)

    def yukle(self, *, dry_run: bool = False) -> int:
        return pg.komut_export_pg(
            ayarlar_kur(self.tmp),
            depo_kok=self.kok,
            source=KAYNAK,
            dry_run=dry_run,
            baglanti=lambda: self.conn,
        )

    def hepsi(self, tur: str = "hepsi") -> int:
        assert self.enrich(tur) == 0
        assert self.qa() == 0
        return self.yukle()

    def son_enrich(self) -> Path:
        sonuc = lineage.son_basarili(self.veri / "staged" / KAYNAK, "enrich")
        assert sonuc is not None
        return sonuc[1]

    def satirlar(self) -> list[dict[str, object]]:
        yol = self.son_enrich() / "xref_links.jsonl"
        return [s.veri for s in satirlari_oku(yol.read_bytes(), "xref_links.jsonl")]

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


def csv_yaz(
    gelen: Path, satirlar: tuple[tuple[str, str, int], ...], ek: tuple[str, ...] = ()
) -> None:
    """QurSim sentetik dosyasi ve `SHA256SUMS`; `Verse` sutunlari yer tutucudur."""
    govde = [SUTUN_BASLIGI]
    for i, (a, b, label) in enumerate(satirlar):
        _, ss, sv = a.split(":")
        _, ts, tv = b.split(":")
        govde.append(f'{i},{i},{ss},{sv},"Deneme metni 1",{ts},{tv},"Deneme metni 2",{label}')
    govde.extend(ek)
    gelen.mkdir(parents=True, exist_ok=True)
    yol = gelen / QURSIM_DOSYASI
    yol.write_bytes(("\n".join(govde) + "\n").encode("utf-8"))
    (gelen / "SHA256SUMS").write_bytes(f"{lineage.sha256_dosya(yol)} *{QURSIM_DOSYASI}\n".encode())


def dunya_kur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, conn: psycopg.Connection
) -> LinksDunyasi:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur(QAC, tur="morfoloji", baslik="Deneme QAC", surum="0.4"))
    kayit_yaz(kok, alanlar_kur(UTHMANI, tur="kuran_metni", baslik="Deneme Uthmani", surum="1.1"))
    kayit_yaz(kok, alanlar_kur(SIMPLE, tur="kuran_metni", baslik="Deneme Simple", surum="1.1"))
    kayit_yaz(
        kok,
        alanlar_kur(QURSIM, tur="baglanti_verisi", baslik="Deneme QurSim", surum="abc12345"),
    )
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    d = LinksDunyasi(tmp_path, kok, veri, conn)
    ctx = ctx_kur(tmp_path, kok, adim="ingest", kaynaklar=[SIMPLE], temiz_git=True)
    satirlar = [
        {"anchor": ay.capa, "text": simple_metni(ay), "source_id": SIMPLE, "attrs": {}}
        for ay in AYETLER
    ]
    cikti = units_yaz(ctx, SIMPLE, satirlar)
    ctx.manifest_yaz(ctx.staged_dizin(SIMPLE), girdiler=[], ciktilar=[cikti], parmak="0" * 64)
    csv_yaz(veri / "gelen" / QURSIM / TARIH, QURSIM_SATIRLARI, ek=("9,9,9,9,x,9,9,y,1",))
    return d
