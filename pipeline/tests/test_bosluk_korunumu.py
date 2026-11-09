"""Kanonik metinde kenar ve ozel bosluk korunumu (K-26, K-39 madde 7; SENTETIK "Deneme" metni).

Gercek Tanzil dosyalarinda ve fiksturlerde baslangic/sonda bosluk, cift bosluk, NBSP, TAB, U+2028,
U+0085 ve dik cizgi yoktur; bu yuzden kirpma (`strip`), bosluk daraltma ya da `splitlines` getiren
bir degisiklik ne gercek veriyi ne de fiksturlerdeki testleri degistirir. Bu testler ayni
degismezi sentetik ayetlerle dogrudan sinar: ayristirma, `ingest -> normalize -> anchor` zinciri ve
`content_hash` ham dosyanin bayt dilimiyle tutmalidir. Kaynak yalniz ASCII'dir; ASCII disi
karakterler `chr()` ile yazilir.
"""

import hashlib
from pathlib import Path

import pytest
from tanzil_yardimci import sentetik_bildirim
from zincir_yardimci import zincir_hazirla

from mutalaa_pipeline import lineage, staged
from mutalaa_pipeline.adimlar import anchor_tanzil
from mutalaa_pipeline.adimlar.normalize_tanzil import KAYNAK
from mutalaa_pipeline.ingest import tanzil_bicim as bicim

pytestmark = pytest.mark.degismezlik

NBSP, TAB = chr(0x00A0), chr(0x0009)
SATIR_AYIRICI, SONRAKI_SATIR = chr(0x2028), chr(0x0085)  # U+2028 ve U+0085 satir sonu sayilmaz
OZEL = [
    " Deneme bir",  # bastaki bosluk
    "Deneme iki ",  # sondaki bosluk
    "Deneme  uc",  # cift bosluk
    NBSP + "Deneme dort" + NBSP,  # kenarlarda NBSP
    TAB + "Deneme" + TAB + "bes" + TAB,  # kenarlarda ve ortada TAB
    "Deneme" + SATIR_AYIRICI + "alti" + SONRAKI_SATIR + "yedi",  # U+2028 ve U+0085 ortada
    "Deneme|sekiz|9",  # dik cizgi: yalniz ilk iki ayirici onek sayilir
]
TABLO = (len(OZEL),)


def _dosya(varyant: str, metinler: list[str]) -> bytes:
    govde = "".join(f"1|{i}|{m}\n" for i, m in enumerate(metinler, start=1)).encode("utf-8")
    return govde + sentetik_bildirim(varyant)


def test_ozel_bosluk_vakalari_gercekten_ozel() -> None:
    """Vaka listesi bosluk ayrimini gercekten sinar (liste sessizce sadelesmesin)."""
    assert any(m != m.strip() for m in OZEL)
    assert any("  " in m for m in OZEL)
    assert any(NBSP in m for m in OZEL)
    assert any(TAB in m for m in OZEL)
    assert any(SATIR_AYIRICI in m and SONRAKI_SATIR in m for m in OZEL)
    assert any("|" in m for m in OZEL)
    assert len(OZEL[5].splitlines()) > 1  # splitlines() bu metni bolerdi


def test_ayristir_ozel_bosluklari_aynen_korur_ve_yeniden_kurar() -> None:
    veri = _dosya("uthmani", OZEL)
    ayrisma = bicim.ayristir(veri, TABLO)
    assert [a.metin for a in ayrisma.ayetler] == OZEL
    for ayet, metin in zip(ayrisma.ayetler, OZEL, strict=True):
        assert veri[ayet.bayt_bas : ayet.bayt_son] == metin.encode("utf-8")
    birimler = [(a.capa, a.metin) for a in ayrisma.ayetler]
    assert bicim.yeniden_kur(birimler, ayrisma.bildirim, ayrisma.duzen) == veri


def test_zincir_ozel_bosluklari_ve_content_hash_ham_dilimdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ingest -> normalize -> anchor: `text` ham dilimdir, `content_hash` onun SHA-256'sidir.

    Sentetik metin Latin harflidir: Arapca `norm` bos cikar ve kelime bolmesi (A11.2) reddeder.
    Bu test yalniz birim metnini sinar; kelime dosyasi bos uretilir.
    """
    monkeypatch.setattr(anchor_tanzil, "kelime_satirlari", lambda birimler, surum: [])
    ham = _dosya("uthmani", OZEL)
    simple = _dosya("simple-clean", [f"Deneme {i}" for i in range(1, len(OZEL) + 1)])
    z = zincir_hazirla(tmp_path, {"uthmani": ham, "simple-clean": simple}, TABLO)
    z.hepsi()
    ayrisma = bicim.ayristir(ham, TABLO)
    for adim in ("ingest", "normalize", "anchor"):
        kayit = lineage.son_basarili(z.veri_kok / "staged" / KAYNAK, adim)
        assert kayit is not None, adim
        satirlar = staged.satirlari_oku((kayit[1] / "units.jsonl").read_bytes(), adim)
        assert [s.metin("text") for s in satirlar] == OZEL, adim
        for satir, ayet in zip(satirlar, ayrisma.ayetler, strict=True):
            dilim = ham[ayet.bayt_bas : ayet.bayt_son]
            assert satir.metin("text").encode("utf-8") == dilim, adim
            if adim == "anchor":
                assert satir.metin("content_hash") == hashlib.sha256(dilim).hexdigest()
