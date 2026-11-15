"""Atif ve iktibas motoru: GERCEK Tanzil metniyle denetim (A18.4); yalniz OKUR.

Arapca diziler hafizadan yazilmaz: yerel `mutalaa` veritabanindaki Tanzil Uthmani ayet birimlerinden
ve `data/staged/tanzil-simple-clean` ciktisindan betikle alinir. Veritabani ya da staged cikti
yoksa atlanir (`MUTALAA_DEGISMEZLIK_ZORUNLU=1` atlamayi hataya cevirir). Test hicbir satir yazmaz;
iddialar yalniz sayi, konum ve capa karsilastirir (Arapca metin ciktiya girmez).
"""

import os
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass

import pytest

from mutalaa_pipeline import lineage
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import VeritabaniHatasi, baglan
from mutalaa_pipeline.enrich.baglantilar.girdi import DbGirdisi, db_oku
from mutalaa_pipeline.enrich.baglantilar.uret import simple_kelimeleri
from mutalaa_pipeline.enrich.citations import iktibas as ik
from mutalaa_pipeline.enrich.citations.indeks import imlai_indeksi, uthmani_indeksi
from mutalaa_pipeline.enrich.citations.kurallar import ipuclari_oku
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.staged import satirlari_oku


def _yok(neden: str) -> None:
    if os.environ.get("MUTALAA_DEGISMEZLIK_ZORUNLU") == "1":
        pytest.fail(f"zorunlu gercek veri testi veri bulamadi: {neden}")
    pytest.skip(neden)


@dataclass
class Dunya:
    db: DbGirdisi
    motor: ik.MotorGirdisi
    ayet_metni: dict[str, str]
    simple_metni: dict[str, str]
    uthmani_kelime: dict[str, int]


@pytest.fixture(scope="module")
def dunya() -> Iterator[Dunya]:
    ayarlar = Ayarlar()
    try:
        conn = baglan(ayarlar)
    except (GirdiHatasi, VeritabaniHatasi) as hata:
        _yok(f"yerel veritabani yok: {hata}")
        return
    try:
        sayi = conn.execute("SELECT count(*) FROM icerik.quran_word").fetchone()
        if sayi is None or sayi[0] != 77429:
            _yok("yerel veritabaninda Tanzil kelimeleri yok (export pg --source tanzil-uthmani)")
        db = db_oku(conn, beklenen_ayet=6236)
        metin = {
            str(a): str(m)
            for a, m in conn.execute(
                "SELECT anchor, metin FROM icerik.unit WHERE kind = 'ayet'"
                " AND source_id = 'tanzil-uthmani'"
            ).fetchall()
        }
    finally:
        conn.rollback()
        conn.close()
    simple = lineage.son_basarili(ayarlar.veri_kok / "staged" / "tanzil-simple-clean", "ingest")
    if simple is None:
        _yok("tanzil-simple-clean staged ciktisi yok (ingest tanzil --variant simple-clean)")
    satirlar = satirlari_oku((simple[1] / "units.jsonl").read_bytes(), "simple units")
    simple_metni = {s.metin("anchor"): s.metin("text") for s in satirlar}
    u = uthmani_indeksi(db.kelimeler, len(db.ayetler))
    imlai = imlai_indeksi(simple_kelimeleri(simple_metni, db.ayetler).kelimeler, u)
    motor = ik.MotorGirdisi(
        indeksler=[u, imlai],
        ayet_capalari=[a.capa for a in db.ayetler],
        ayet_ozetleri=[a.ozet for a in db.ayetler],
        kalip=frozenset(),
        ipuclari=ipuclari_oku(),
    )
    yield Dunya(db, motor, metin, simple_metni, {k.capa: k.no for k in db.kelimeler})


def isle(d: Dunya, metin: str) -> list[ik.AdayHat]:
    return ik.birim_isle(d.motor, ik.Birim("meal:elmalili:2:1", metin, "0" * 16), Counter())


def ayet_kelime_sayisi(d: Dunya, capa: str) -> int:
    return sum(1 for k in d.db.kelimeler if k.capa.startswith(capa + ":"))


def test_gercek_uthmani_ayet_tam_alinti(dunya: Dunya) -> None:
    capa = "q:2:255"
    n = ayet_kelime_sayisi(dunya, capa)
    metin = "Deneme paragrafi 1 " + dunya.ayet_metni[capa] + " Deneme paragrafi 2."
    satirlar = [h for h in isle(dunya, metin) if h.tur == "iktibas"]
    hedef = [h for h in satirlar if dunya.motor.ayet_capalari[h.dst_sira] == capa]
    assert len(hedef) == 1
    h = hedef[0]
    assert h.dst_span == (1, n + 1) and h.evidence["matched_words"] == n
    assert h.evidence["coverage"] == 1.0 and h.evidence["phrase_freq"] == 1
    assert h.evidence["dst_hash"] == dunya.db.ayetler[dunya.motor.ayet_yeri[capa]].ozet


def test_gercek_imlai_ayet_alintisi(dunya: Dunya) -> None:
    capa = "q:2:255"
    n = ayet_kelime_sayisi(dunya, capa)
    metin = "Deneme paragrafi 1 " + dunya.simple_metni[capa] + " Deneme paragrafi 2."
    hedef = [
        h
        for h in isle(dunya, metin)
        if h.tur == "iktibas" and dunya.motor.ayet_capalari[h.dst_sira] == capa
    ]
    assert hedef and hedef[0].evidence["matched_words"] >= n - 2
    assert 1 <= hedef[0].dst_span[0] < hedef[0].dst_span[1] <= n + 1  # type: ignore[index]


def test_gercek_ardisik_ayetler_bolunur(dunya: Dunya) -> None:
    a, b = "q:2:255", "q:2:256"
    ta, tb = dunya.ayet_metni[a].split(" "), dunya.ayet_metni[b].split(" ")
    metin = "Deneme " + " ".join(ta[-6:]) + " " + " ".join(tb[:6])
    h = {
        dunya.motor.ayet_capalari[x.dst_sira]: x
        for x in isle(dunya, metin)
        if x.tur == "iktibas" and dunya.motor.ayet_capalari[x.dst_sira] in (a, b)
    }
    assert set(h) == {a, b}
    assert h[a].evidence["group"] == h[b].evidence["group"]
    assert h[a].dst_span[1] == ayet_kelime_sayisi(dunya, a) + 1  # type: ignore[index]
    assert h[b].dst_span[0] == 1  # type: ignore[index]


def test_gercek_imlai_uthmani_kelime_sayisi_farkli_ayetler(dunya: Dunya) -> None:
    """A18.3 raporu: Simple Clean ve Uthmani ayet basi kelime sayisi 363 ayette farkli."""
    u, imlai = dunya.motor.indeksler
    farkli = [
        i for i in range(u.ayet_sayisi) if len(u.ayet_belirtec[i]) != len(imlai.ayet_belirtec[i])
    ]
    assert len(farkli) >= 100  # sayi A18.3 raporunda 363; belirtec duzeyinde ayni mertebe
    # her farkli ayette imlai konumlari Uthmani kelime numaralarina eslenir ve araligin icindedir
    for i in farkli[:200]:
        nolar = imlai.kelime_no[i]
        assert nolar and min(nolar) >= 1 and max(nolar) <= max(u.kelime_no[i])
