# ruff: noqa: RUF001
"""Turkce kok hatti testlerinin ortak yardimcilari (test degildir; ACIKCA SENTETIK veri).

Hicbir Kur'an, meal, tefsir, hadis ya da sozluk metni yoktur: meal metinleri "Deneme tavan ve
dolap" gibi uydurma sozcuklerdir; Arapca kok ve etimon bicimleri anlamsiz, uydurma harf
dizileridir (`ب ن ر` gibi). `SahteLemmatizer` zeyrek yerine sabit bir tablo kullanir.

`TrDunya`: sahte depo koku (kaynak kayitlari) + sahte veri koku (iki meal ve QAC `anchor`
calismalari, iki kaikki dokumu ve `SHA256SUMS`); `enrich()` ve `qa()` gercek adimlari kosar.
"""

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur
from test_sources import alanlar_kur, kayit_yaz, kok_kur

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_tr_roots import komut_enrich_tr_roots
from mutalaa_pipeline.anchor import content_hash
from mutalaa_pipeline.enrich.tr_roots.eslesme import QacEnvanteri
from mutalaa_pipeline.enrich.tr_roots.etimoloji import KaikkiIndeksi, Kanit, Madde
from mutalaa_pipeline.enrich.tr_roots.lemmatize import Analiz, Cozum
from mutalaa_pipeline.qa.run_tr_roots import komut_qa_run_tr_roots
from mutalaa_pipeline.runctx import RunContext
from mutalaa_pipeline.staged import dosya_yaz, satirlari_oku, units_yaz

TARIH = "2026-11-12"
TR_DOSYASI = "kaikki.org-dictionary-Turkish.jsonl.gz"
OTA_DOSYASI = "kaikki.org-dictionary-OttomanTurkish.jsonl"
SURUM = "2026-10-30"
MEAL_O = "elmalili-meal"
MEAL_S = "elmalili-sade-meal"
QAC = "qac-morfoloji"
KAIKKI = "kaikki-tr"

# Uydurma Arapca harf dizileri (anlamsiz; kok harfi ve etimon bicimi)
KOK_BNR = "ب ن ر"
KOK_SML = "ص م ل"
KOK_AMN = "ء م ن"
KOK_AMN_ELIFLI = "أ م ن"  # kaikki imlai: hemze elif uzerinde (katlama ile ء)
ETIMON_SML = "صَمَال"  # uzun unlu elifi var; normalize + elifsiz anahtar: صمل
ETIMON_MRT = "مَرَات"  # anahtar: مرت (iki QAC lemmasi, iki kok)
ETIMON_BNR = "بِنَار"  # anahtar: بنر
OSMANLICA_BICIM = "ددد"

QAC_KOKLER = [
    {"letters_bw": "bnr", "letters": KOK_BNR},
    {"letters_bw": "Sml", "letters": KOK_SML},
    {"letters_bw": "Amn", "letters": KOK_AMN},
]
QAC_LEMMALAR = [
    {"qac_ref": "banar", "text_clean": "بنر", "root_letters_bw": "bnr"},
    {"qac_ref": "samal", "text_clean": "صمل", "root_letters_bw": "Sml"},
    {"qac_ref": "mrt1", "text_clean": "مرت", "root_letters_bw": "bnr"},
    {"qac_ref": "mrt2", "text_clean": "مرت", "root_letters_bw": "Sml"},
]


def kok_kanit(harfler: str, sablon: str = "root") -> Kanit:
    return Kanit("kok", f"etymology_templates.{sablon}", harfler)


def etimon_kanit(etimon: str, sablon: str = "ety") -> Kanit:
    return Kanit("etimon", f"etymology_templates.{sablon}", etimon)


def tr_madde(
    sozcuk: str,
    *kanitlar: Kanit,
    pos: str = "noun",
    osmanlica: tuple[str, ...] = (),
    zayif: bool = False,
) -> Madde:
    return Madde(sozcuk, "tr", pos, tuple(kanitlar), osmanlica, zayif)


def ota_madde(sozcuk: str, *kanitlar: Kanit, pos: str = "noun", zayif: bool = False) -> Madde:
    return Madde(sozcuk, "ota", pos, tuple(kanitlar), (), zayif)


def indeks_kur(*maddeler: Madde) -> KaikkiIndeksi:
    indeks = KaikkiIndeksi(SURUM)
    for m in maddeler:
        indeks.ekle(m)
    return indeks


def env_kur() -> QacEnvanteri:
    return QacEnvanteri.kur(QAC_KOKLER, QAC_LEMMALAR)


class SahteLemmatizer:
    """`bicim -> [(lemma, tur)]` tablosu; tabloda olmayan bicim bilinmeyendir."""

    def __init__(self, tablo: dict[str, list[tuple[str, str]]]) -> None:
        self._tablo = tablo
        self.cagrilar: list[str] = []

    def analiz(self, bicim: str) -> Analiz:
        self.cagrilar.append(bicim)
        return Analiz(frozenset(Cozum(lm, tur) for lm, tur in self._tablo.get(bicim, [])))


def analiz(*cozumler: tuple[str, str]) -> Analiz:
    return Analiz(frozenset(Cozum(lm, tur) for lm, tur in cozumler))


LEMMATIZER_TABLOSU: dict[str, list[tuple[str, str]]] = {
    "tavan": [("tavan", "Noun")],
    "tavanlar": [("tavan", "Noun")],
    "dolap": [("dolap", "Noun")],
    "zorba": [("zorba", "Noun")],
    "morta": [("morta", "Noun")],
    "pelin": [("pelin", "Noun")],
    "kelin": [("kelin", "Noun")],
    "fisto": [("fisto", "Noun")],
    "kalem": [("kalem", "Adj")],  # kaikki maddesi isim: tur uyusmazligi
    "bobin": [("bobin", "Noun")],
    "emin": [("emin", "Noun")],
    "ve": [("ve", "Conj")],
    "oldu": [("olmak", "Verb")],
    "okur": [("oku", "Verb"), ("okur", "Noun")],
    "oku": [("oku", "Verb")],
}

MEAL_METINLERI: dict[str, list[tuple[str, str]]] = {
    MEAL_O: [
        ("meal:elmalili:1:1", "Deneme tavan ve dolap, tavan-i dolap."),
        ("meal:elmalili:1:2", "Zorba morta pelin kelin."),
        ("meal:elmalili:1:3", "Fisto kalem oldu okur yokluk emin."),
    ],
    MEAL_S: [
        ("meal:elmalili-sade:1:1", "Tavan'ın kalem bobin kalem."),
        ("meal:elmalili-sade:1:2", "Deneme dolap emin pelin."),
    ],
}


def kaikki_tr_satirlari() -> list[dict[str, object]]:
    def kayit(
        sozcuk: str, sablonlar: list[dict[str, object]], pos: str = "noun", metin: str = ""
    ) -> dict[str, object]:
        return {
            "word": sozcuk,
            "lang_code": "tr",
            "pos": pos,
            "etymology_templates": sablonlar,
            "etymology_text": metin,
        }

    def kok(harfler: str) -> dict[str, object]:
        return {"name": "root", "args": {"1": "tr", "2": "ar", "3": harfler}}

    def agac(ham: str) -> dict[str, object]:
        return {"name": "ety", "args": {"1": "tr", "2": ":inh", "3": ham}}

    return [
        kayit("tavan", [kok(KOK_BNR)]),
        kayit("dolap", [agac(f"ota:{OSMANLICA_BICIM}\n<ety:uder<ar:{ETIMON_SML}>>")]),
        kayit("zorba", [kok(KOK_BNR)]),
        kayit("zorba", [kok(KOK_SML)]),
        kayit("morta", [{"name": "bor", "args": {"1": "tr", "2": "ar", "3": ETIMON_MRT}}]),
        kayit("pelin", [{"name": "inh", "args": {"1": "tr", "2": "ota", "3": "ععع"}}]),
        kayit(
            "kelin", [kok(KOK_BNR), {"name": "inh", "args": {"1": "tr", "2": "ota", "3": "غغغ"}}]
        ),
        kayit("fisto", [], metin="Borrowed from Arabic (deneme)."),
        kayit("kalem", [kok(KOK_BNR)]),
        kayit("bobin", [kok(KOK_BNR)]),
        kayit("bobin", []),
        kayit("emin", [kok(KOK_AMN_ELIFLI)]),
        kayit("ve", [kok(KOK_BNR)], pos="conj"),
        kayit("oku", [kok(KOK_BNR)], pos="verb"),
    ]


def kaikki_ota_satirlari() -> list[dict[str, object]]:
    def kayit(sozcuk: str, sablonlar: list[dict[str, object]]) -> dict[str, object]:
        return {
            "word": sozcuk,
            "lang_code": "ota",
            "pos": "noun",
            "etymology_templates": sablonlar,
            "etymology_text": "",
        }

    def kok(harfler: str) -> dict[str, object]:
        return {"name": "root", "args": {"1": "ota", "2": "ar", "3": harfler}}

    return [
        kayit("ععع", [kok(KOK_SML)]),  # pelin: Osmanlicadan gelen kok
        kayit("غغغ", [kok(KOK_SML)]),  # kelin: Turkce bnr, Osmanlica Sml: celisir
        kayit(OSMANLICA_BICIM, []),  # dolap: baglanti var, kanit yok
    ]


@dataclass
class TrDunya:
    """Sentetik zincir; `enrich()` ve `qa()` gercek komut govdelerini kosar."""

    tmp: Path
    kok: Path
    veri: Path
    lemmatizer: SahteLemmatizer

    def ctx(self, adim: str, kaynaklar: list[str]) -> RunContext:
        return ctx_kur(self.tmp, self.kok, adim=adim, kaynaklar=kaynaklar, temiz_git=True)

    def enrich(
        self,
        *,
        min_sik: int = 2,
        dry_run: bool = False,
        kaynaklar: list[str] | None = None,
        tarih: str | None = None,
        force: bool = False,
    ) -> int:
        return komut_enrich_tr_roots(
            kaynaklar=kaynaklar if kaynaklar is not None else [MEAL_O, MEAL_S],
            min_sik=min_sik,
            gelen_tarih=tarih,
            dry_run=dry_run,
            force=force,
            config=None,
            kok=self.kok,
            lemmatizer_kur=lambda: self.lemmatizer,
        )

    def qa(self, *, gate: list[str] | None = None) -> int:
        return komut_qa_run_tr_roots(run=None, gate=gate, config=None, kok=self.kok)

    def son_calisma(self, kaynak: str, adim: str) -> Path:
        klasor = self.veri / "staged" / kaynak
        sonuc = lineage.son_basarili(klasor, adim)
        assert sonuc is not None
        return sonuc[1]

    def satirlar(self, ad: str) -> list[dict[str, object]]:
        yol = self.son_calisma(KAIKKI, "enrich") / ad
        return [s.veri for s in satirlari_oku(yol.read_bytes(), ad)]

    def manifest(self) -> dict[str, object]:
        klasor = self.son_calisma(KAIKKI, "enrich")
        manifest = lineage.manifest_oku(klasor)
        assert manifest is not None
        return manifest


def _asama_yaz(
    d: "TrDunya",
    kaynak: str,
    dosyalar: list[tuple[str, list[dict[str, object]], tuple[str, ...] | None]],
) -> None:
    """`anchor` adiminda sahte bir calisma: dosyalar ve manifest."""
    ctx = d.ctx("anchor", [kaynak])
    ciktilar = []
    for ad, satirlar, anahtar in dosyalar:
        if anahtar is None:
            ciktilar.append(units_yaz(ctx, kaynak, satirlar))
        else:
            ciktilar.append(dosya_yaz(ctx, kaynak, ad, satirlar, anahtar))
    ctx.manifest_yaz(ctx.staged_dizin(kaynak), girdiler=[], ciktilar=ciktilar, parmak="0" * 64)


def dunya_kur(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    lemmatizer_tablosu: dict[str, list[tuple[str, str]]] | None = None,
    mealler: dict[str, list[tuple[str, str]]] | None = None,
    tr_satirlari: list[dict[str, object]] | None = None,
    ota_satirlari: list[dict[str, object]] | None = None,
) -> TrDunya:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur(KAIKKI, tur="sozluk", baslik="Deneme sozluk", surum=SURUM))
    kayit_yaz(kok, alanlar_kur(QAC, tur="morfoloji", baslik="Deneme QAC", surum="0.4"))
    kayit_yaz(kok, alanlar_kur(MEAL_O, tur="meal", baslik="Deneme meal", surum="1"))
    kayit_yaz(kok, alanlar_kur(MEAL_S, tur="meal", baslik="Deneme sade meal", surum="1"))
    veri = tmp_path / "data"
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(veri))
    d = TrDunya(
        tmp_path,
        kok,
        veri,
        SahteLemmatizer(
            lemmatizer_tablosu if lemmatizer_tablosu is not None else LEMMATIZER_TABLOSU
        ),
    )
    for slug, birimler in (mealler if mealler is not None else MEAL_METINLERI).items():
        satirlar = [
            {"anchor": a, "text": t, "content_hash": content_hash(t), "source_id": slug}
            for a, t in birimler
        ]
        _asama_yaz(d, slug, [("units.jsonl", satirlar, None)])
    _asama_yaz(
        d,
        QAC,
        [
            ("roots.jsonl", [dict(k) for k in QAC_KOKLER], ("letters_bw",)),
            ("lemmas.jsonl", [dict(lm) for lm in QAC_LEMMALAR], ("qac_ref",)),
        ],
    )
    kaikki_yaz(
        d,
        tr_satirlari if tr_satirlari is not None else kaikki_tr_satirlari(),
        ota_satirlari if ota_satirlari is not None else kaikki_ota_satirlari(),
    )
    return d


def kaikki_yaz(
    d: TrDunya, tr_satirlari: list[dict[str, object]], ota_satirlari: list[dict[str, object]]
) -> None:
    """Iki kaikki dokumunu (yeniden) yazar ve `SHA256SUMS` dosyasini gunceller."""
    gelen = d.veri / "gelen" / "kaikki-tr" / TARIH
    gelen.mkdir(parents=True, exist_ok=True)
    tr = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in tr_satirlari).encode("utf-8")
    ota = "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in ota_satirlari).encode("utf-8")
    (gelen / TR_DOSYASI).write_bytes(gzip.compress(tr, mtime=0))
    (gelen / OTA_DOSYASI).write_bytes(ota)
    ozetler = [f"{lineage.sha256_dosya(gelen / ad)} *{ad}" for ad in (TR_DOSYASI, OTA_DOSYASI)]
    (gelen / "SHA256SUMS").write_bytes(("\n".join(ozetler) + "\n").encode("utf-8"))
