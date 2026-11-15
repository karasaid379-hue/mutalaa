"""Tohum bulma ve kelime duzeyinde Smith-Waterman (Iktibas tespiti §5-§6): SENTETIK kelimeler."""

from citations_yardimci import AYET_TOKENLERI, CAPALAR, indeksler
from links_yardimci import sozcuk

from mutalaa_pipeline.enrich.citations import hizala
from mutalaa_pipeline.enrich.citations.hizala import smith_waterman, tohumlari_bul
from mutalaa_pipeline.enrich.citations.iktibas import _parcalar
from mutalaa_pipeline.enrich.citations.normalizasyon import anahtar_dizisi

U, IMLAI = indeksler()


def anahtarlar(*capalar: str, bas: int = 0, son: int | None = None) -> list[str]:
    tum = [t for c in capalar for t in AYET_TOKENLERI[c]]
    return tum[bas:son]


# --- Smith-Waterman: kelime duzeyi ------------------------------------------------------------


def test_sw_tam_esleme() -> None:
    a = ["w1", "w2", "w3", "w4"]
    hiza = smith_waterman(["x", *a, "y"], ["z", *a, "k"])
    assert hiza is not None
    assert [(i, j, t) for i, j, t in hiza.ciftler] == [
        (1, 1, "tam"),
        (2, 2, "tam"),
        (3, 3, "tam"),
        (4, 4, "tam"),
    ]
    assert hiza.skor == 8 and hiza.duzenleme == 0


def test_sw_bulanik_ve_duzenleme_sayisi() -> None:
    uzun = sozcuk(10) + sozcuk(11)
    hiza = smith_waterman(["a1", "a2", uzun[:-1], "a4", "a5"], ["a1", "a2", uzun, "a4", "a5"])
    assert hiza is not None
    assert [t for _, _, t in hiza.ciftler] == ["tam", "tam", "bulanik", "tam", "tam"]
    assert hiza.skor == 2 * 4 + 1 and hiza.duzenleme == 1


def test_sw_bosluk_duzenleme_sayar() -> None:
    hiza = smith_waterman(
        ["a1", "a2", "a3", "a4", "a5", "a6"], ["a1", "a2", "a3", "ek", "a4", "a5", "a6"]
    )
    assert hiza is not None
    assert hiza.duzenleme == 1 and len(hiza.ciftler) == 6  # b'de bir fazla kelime: bir bosluk


def test_sw_hizalanacak_yoksa_none() -> None:
    assert smith_waterman(["a", "b"], ["c", "d"]) is None


def test_sw_deterministik() -> None:
    a = ["a1", "a2", "x", "a3", "a4", "a5"]
    b = ["a1", "a2", "y", "a3", "a4", "a5"]
    assert smith_waterman(a, b) == smith_waterman(a, b)


# --- tohum ------------------------------------------------------------------------------------


def test_tohum_4gram_tek_isabet_yeter() -> None:
    ts = tohumlari_bul(anahtarlar("q:2:1", bas=2, son=6), U.indeks)
    assert len(ts.tohumlar) == 1
    assert ts.tohumlar[0].kose == U.indeks.ayet_baslangic[CAPALAR.index("q:2:1")] + 2


def test_tohum_3gram_iki_isabet_ister() -> None:
    uc = anahtarlar("q:2:1", bas=0, son=3)  # tek 3-gram: tohum degil
    assert tohumlari_bul(uc, U.indeks).tohumlar == []
    dort = anahtarlar("q:2:1", bas=0, son=4)  # 4-gram isabeti
    assert len(tohumlari_bul(dort, U.indeks).tohumlar) == 1


def test_tohum_uc_kelimeden_kisa_dizide_yok() -> None:
    assert tohumlari_bul(anahtarlar("q:2:1", bas=0, son=2), U.indeks).tohumlar == []


def test_tohum_kalip_cok_kose_verir() -> None:
    kalip = anahtarlar("q:2:4", bas=0, son=6)
    ts = tohumlari_bul(kalip, U.indeks)
    assert len(ts.tohumlar) == 4  # q:2:4, q:2:5, q:2:6, q:3:3


# --- hizalama + ayet sinirinda bolme -----------------------------------------------------------


def hizala_et(dizi: list[str], indeks=U):
    ts = tohumlari_bul(dizi, indeks.indeks)
    assert ts.tohumlar
    h = hizala.hizala(dizi, indeks.indeks, ts.tohumlar[0])
    assert h is not None
    return h


def test_hizalama_tam_ayet() -> None:
    dizi = anahtarlar("q:2:2")
    parcalar = _parcalar(hizala_et(dizi), U, dizi)
    assert len(parcalar) == 1
    p = parcalar[0]
    assert p.ayet == CAPALAR.index("q:2:2")
    assert (p.n, p.e, p.kelime_ilk, p.kelime_son1, p.belirsiz) == (10, 0, 1, 11, False)


def test_hizalama_kismi() -> None:
    dizi = anahtarlar("q:2:2", bas=3, son=9)
    (p,) = _parcalar(hizala_et(dizi), U, dizi)
    assert (p.n, p.e, p.kelime_ilk, p.kelime_son1) == (6, 0, 4, 10)


def test_hizalama_bir_iki_duzenleme() -> None:
    tokenler = list(AYET_TOKENLERI["q:3:2"])  # 6 harfli kelimeler
    dizi = tokenler[:]
    dizi[1] = dizi[1][:-1]
    dizi[6] = dizi[6][:-1]
    (p,) = _parcalar(hizala_et(dizi), U, dizi)
    assert p.ayet == CAPALAR.index("q:3:2")
    assert (p.n, p.e) == (8, 2)  # iki bulanik kelime: n sayilir, duzenleme sayilir


def test_hizalama_ardisik_ayet_sinirinda_bolunur() -> None:
    dizi = anahtarlar("q:2:1", bas=6) + anahtarlar("q:2:2", son=5)  # 4 + 5 kelime
    parcalar = _parcalar(hizala_et(dizi), U, dizi)
    assert [(CAPALAR[p.ayet], p.n, p.kelime_ilk, p.kelime_son1) for p in parcalar] == [
        ("q:2:1", 4, 7, 11),
        ("q:2:2", 5, 1, 6),
    ]
    assert parcalar[0].a_son + 1 == parcalar[1].a_ilk  # dizi araliklari bitisik


def test_hizalama_imlai_ayet_kelime_farki_belirsiz_isaretler() -> None:
    # q:3:1 imlai metninde 4. ve 5. kelime birlesik: ayet kelime sayilari farkli
    from citations_yardimci import besmele_kirp, simple_metni

    capa = "q:3:1"
    imlai_dizi = anahtar_dizisi(" ".join(besmele_kirp(capa, simple_metni(capa).split())))
    assert len(imlai_dizi) == len(AYET_TOKENLERI[capa]) - 1
    (p,) = _parcalar(hizala_et(imlai_dizi, IMLAI), IMLAI, imlai_dizi)
    assert p.n == 9 and p.belirsiz is True  # birlesik kelime konumu hizalamayla (belirsiz)
    assert (p.kelime_ilk, p.kelime_son1) == (1, 11)
    # esit kelime sayili ayette imlai konumu birebirdir
    dizi = anahtarlar("q:2:2", bas=2, son=7)
    (q,) = _parcalar(hizala_et(dizi, IMLAI), IMLAI, dizi)
    assert q.belirsiz is False and (q.kelime_ilk, q.kelime_son1) == (3, 8)


def test_imlai_kelime_haritasi_esit_sayida_birebir() -> None:
    from mutalaa_pipeline.enrich.citations.indeks import imlai_kelime_haritasi

    nolar, bel = imlai_kelime_haritasi(["a", "b", "c"], ["x", "y", "z"], [1, 2, 3])
    assert nolar == [1, 2, 3] and bel == [False] * 3
    nolar, bel = imlai_kelime_haritasi(["a", "bc", "d"], ["a", "b", "c", "d"], [1, 2, 3, 4])
    assert nolar[0] == 1 and nolar[2] == 4 and bel == [False, True, False]
