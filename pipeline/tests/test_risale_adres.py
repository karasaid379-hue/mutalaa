# ruff: noqa: RUF001
"""Risale adres dogrulayicisi (A20.2a, Capa semasi bolum 5, K-51 madde 4 ve 12).

Girdiler sentetiktir; gercek Risale metni yoktur. Kitap adlari yalniz ad olarak (metin degil)
yer alir; gorunmeyen karakterler (birlesen isaretler) `chr()` ile acik yazilir.
"""

import pytest

from mutalaa_pipeline.anchor import AnchorError, parse
from mutalaa_pipeline.anchor.risale import (
    DIZIN_PAKETI,
    SABIT_BOLUMLER,
    SIRA_TURLERI,
    RisaleHatasi,
    bolum_denetle,
    bolum_kalibi,
    capa_paket_kimligi,
    hasiye_yolu,
    kardes_slug,
    kitap_slug_denetle,
    paket_kimligi,
    parca_slug,
    rn_capa,
    sira_adi,
    slug_denetle,
    slug_turet,
    yol_denetle,
)


def _kod(islev: object, *args: object) -> str:
    with pytest.raises(RisaleHatasi) as hata:
        islev(*args)  # type: ignore[operator]
    return hata.value.kod


# ---------------------------------------------------------------------------
# slug ve ayrilmis adlar


@pytest.mark.parametrize("ad", ["sozler", "a", "soz-10", "a1", "mesnevi-i-nuriye", "x-2", "a" * 64])
def test_gecerli_slug(ad: str) -> None:
    assert slug_denetle(ad) == ad


@pytest.mark.parametrize(
    "ad",
    ["", "Sozler", "sözler", "1soz", "-soz", "soz-", "soz--10", "soz_10", "soz 10", "soı"],
)
def test_gecersiz_slug_bicim(ad: str) -> None:
    assert _kod(slug_denetle, ad) == "BICIM"


@pytest.mark.parametrize("ad", ["p4", "s12", "p1", "s0", "p007"])
def test_p_ve_s_rakam_adlari_ayrilmis(ad: str) -> None:
    assert _kod(slug_denetle, ad) == "AYRILMIS"
    assert _kod(bolum_denetle, ad) == "AYRILMIS"
    assert _kod(kitap_slug_denetle, ad) == "AYRILMIS"


@pytest.mark.parametrize("ad", ["p", "s", "pa4", "p4a", "p-4", "ps4", "soz", "sp1"])
def test_ayrilmis_gorunumlu_ama_gecerli_adlar(ad: str) -> None:
    assert slug_denetle(ad) == ad


def test_64_ve_65_karakter() -> None:
    assert slug_denetle("a" * 64) == "a" * 64
    assert _kod(slug_denetle, "a" * 65) == "UZUNLUK"
    assert kitap_slug_denetle("k" * 64) == "k" * 64
    assert _kod(kitap_slug_denetle, "k" * 65) == "UZUNLUK"
    # bicim hatasi uzunluktan once (capa ile ayni oncelik)
    assert _kod(slug_denetle, "A" * 65) == "BICIM"


def test_dizin_kitap_slugi_olamaz_ama_bolum_olabilir() -> None:
    assert _kod(kitap_slug_denetle, "dizin") == "AYRILMIS"
    assert _kod(paket_kimligi, "dizin") == "AYRILMIS"
    assert bolum_denetle("dizin") == "dizin"
    assert kitap_slug_denetle("dizin-2") == "dizin-2"
    assert DIZIN_PAKETI == "risale-dizin"


# ---------------------------------------------------------------------------
# bolum kaliplari


@pytest.mark.parametrize("tur", SIRA_TURLERI)
def test_sira_kaliplari(tur: str) -> None:
    ad = f"{tur}-10"
    kalip = bolum_kalibi(ad)
    assert kalip is not None
    assert (kalip.tur, kalip.n) == (tur, 10)
    assert sira_adi(tur, 10) == ad
    assert bolum_denetle(ad) == ad


def test_kalip_listesi_belgedeki_adlari_kapsar() -> None:
    belge = {
        "soz",
        "mektup",
        "lema",
        "sua",
        "makam",
        "hakikat",
        "nukte",
        "mesele",
        "isaret",
        "hasiye",
    }
    assert belge <= set(SIRA_TURLERI)
    assert set(SABIT_BOLUMLER) == {"mukaddime", "zeyl", "hatime"}
    assert "parca" in SIRA_TURLERI


@pytest.mark.parametrize("ad", SABIT_BOLUMLER)
def test_sabit_bolumler(ad: str) -> None:
    kalip = bolum_kalibi(ad)
    assert kalip is not None
    assert (kalip.tur, kalip.n) == (ad, None)


@pytest.mark.parametrize(
    "ad", ["soz-0", "soz-01", "soz-007", "lema-00", "soz-2147483648", "hakikat-0"]
)
def test_kanonik_olmayan_numara_kalip_degildir(ad: str) -> None:
    assert bolum_kalibi(ad) is None
    assert _kod(bolum_denetle, ad) == "KALIP"


@pytest.mark.parametrize(
    "ad", ["giris", "birinci-bab", "soz", "soz-a", "sozler-1", "soz-1-2", "mukaddime-1", "lema-"]
)
def test_kalip_disi_adlar_gecerli_bolumdur(ad: str) -> None:
    if ad == "lema-":
        assert _kod(bolum_denetle, ad) == "BICIM"
        return
    assert bolum_kalibi(ad) is None
    assert bolum_denetle(ad) == ad


def test_sira_adi_sinirlari() -> None:
    assert sira_adi("soz", 2_147_483_647) == "soz-2147483647"
    for n in (0, -1, 2_147_483_648):
        assert _kod(sira_adi, "soz", n) == "KALIP"
    assert _kod(sira_adi, "bilinmeyen", 1) == "KALIP"
    assert _kod(sira_adi, "soz", True) == "KALIP"


def test_numarada_kopyalama_yalniz_ascii_rakam() -> None:
    # Arap-Hint rakami (U+0663) ve tam genislikte rakam `[0-9]` ile eslesmez
    assert bolum_kalibi("soz-٣") is None
    assert bolum_kalibi("soz-１") is None


# ---------------------------------------------------------------------------
# yol, derinlik ve capa


def test_derinlik_8_gecer_9_gecmez() -> None:
    bolumler = [f"b{i}" for i in range(1, 8)]  # kitap + 7 bolum = 8 parca
    assert len(yol_denetle(["sozler", *bolumler])) == 8
    assert _kod(yol_denetle, ["sozler", *bolumler, "b8"]) == "DERINLIK"


def test_derinlik_capa_ayristiricisiyla_ayni_sinirda() -> None:
    sekiz = ["sozler", *[f"b{i}" for i in range(1, 8)]]
    capa = rn_capa(sekiz, 1)
    assert parse(capa).anchor.t == "rn"
    dokuz = ":".join([*sekiz, "b8"]) + ":p1"
    with pytest.raises(AnchorError) as hata:
        parse("rn:" + dokuz)
    assert hata.value.code == "UZUNLUK"


def test_yol_bos_ve_kitap_denetimi() -> None:
    assert _kod(yol_denetle, []) == "BICIM"
    assert _kod(yol_denetle, ["dizin", "soz-1"]) == "AYRILMIS"
    assert _kod(yol_denetle, ["sozler", "soz-01"]) == "KALIP"
    assert _kod(yol_denetle, ["sozler", "p4"]) == "AYRILMIS"


def test_rn_capa_uretir_ve_capa_ile_dogrular() -> None:
    assert rn_capa(["sozler", "soz-10", "hakikat-3"], 4) == "rn:sozler:soz-10:hakikat-3:p4"
    assert rn_capa(["test-ornek", "bolum-1"], 2, 3) == "rn:test-ornek:bolum-1:p2:s3"
    assert _kod(rn_capa, ["dizin"], 1) == "AYRILMIS"
    with pytest.raises(AnchorError):  # p = 0 capa gramerine uymaz
        rn_capa(["sozler"], 0)


def test_hasiye_ve_parca() -> None:
    assert hasiye_yolu(["sozler", "soz-10"], 2) == ("sozler", "soz-10", "hasiye-2")
    assert rn_capa(hasiye_yolu(["sozler", "soz-10"], 1), 1) == "rn:sozler:soz-10:hasiye-1:p1"
    assert parca_slug(3) == "parca-3"
    assert _kod(hasiye_yolu, ["sozler"], 0) == "KALIP"
    sekiz = ["sozler", *[f"b{i}" for i in range(1, 8)]]
    assert _kod(hasiye_yolu, sekiz, 1) == "DERINLIK"


# ---------------------------------------------------------------------------
# kardes cakismasi


def test_kardes_slug_ek_alir() -> None:
    assert kardes_slug("soz-1", set()) == "soz-1"
    assert kardes_slug("mesele", {"mesele"}) == "mesele-2"
    assert kardes_slug("mesele", {"mesele", "mesele-2"}) == "mesele-3"
    assert kardes_slug("mesele", {"mesele-2"}) == "mesele"


def test_kardes_slug_64_sinirina_uyar() -> None:
    uzun = "a" * 64
    sonuc = kardes_slug(uzun, {uzun})
    assert sonuc == "a" * 62 + "-2"
    assert len(sonuc) == 64
    assert slug_denetle(sonuc) == sonuc
    # kisaltilan tabanin sonundaki tire birikmez
    tireli = "a" * 61 + "-bb"
    assert kardes_slug(tireli, {tireli}).endswith("-2")
    assert "--" not in kardes_slug(tireli, {tireli})


# ---------------------------------------------------------------------------
# paket kimligi


def test_paket_kimligi() -> None:
    assert paket_kimligi("sozler") == "risale-sozler"
    assert paket_kimligi("sozler-osmanlica") == "risale-sozler-osmanlica"
    assert capa_paket_kimligi("rn:sozler:soz-10:hakikat-3:p4") == "risale-sozler"
    assert capa_paket_kimligi("rn:mesnevi-i-nuriye:p1:s2") == "risale-mesnevi-i-nuriye"
    assert capa_paket_kimligi("rn:sozler:p1@0-5") == "risale-sozler"
    assert _kod(capa_paket_kimligi, "h:buhari:52") == "BICIM"
    with pytest.raises(AnchorError):
        capa_paket_kimligi("rn:sözler:p1")


# ---------------------------------------------------------------------------
# slug_turet: acik harf esleme, str.lower() yok


@pytest.mark.parametrize(
    ("ad", "slug"),
    [
        ("Sözler", "sozler"),
        ("Lem'alar", "lemalar"),
        ("Lem’alar", "lemalar"),
        ("Asa-yı Musa", "asa-yi-musa"),
        ("Asâ-yı Mûsâ", "asa-yi-musa"),
        ("Mesnevî-i Nûriye", "mesnevi-i-nuriye"),
        ("İşârâtü'l-İ'câz", "isaratul-icaz"),
        ("Emirdağ Lâhikası 1", "emirdag-lahikasi-1"),
        ("Tarihçe-i Hayat", "tarihce-i-hayat"),
        ("  Şualar  ", "sualar"),
        ("Nur'un İlk Kapısı", "nurun-ilk-kapisi"),
        ("a...b", "a-b"),
        ("Deneme  Kitap, 2", "deneme-kitap-2"),
    ],
)
def test_slug_turet(ad: str, slug: str) -> None:
    assert slug_turet(ad) == slug
    assert slug_denetle(slug) == slug


def test_slug_turet_i_ve_dotless_i() -> None:
    # I (ASCII buyuk), U+0130 (noktali buyuk), U+0131 (noktasiz kucuk), i: hepsi `i`
    assert slug_turet("I" + chr(0x0130) + chr(0x0131) + "i") == "iiii"
    # ayrik yazim (NFC olmayan Diyanet dosya adlari): I + U+0307 (birlesen nokta)
    nokta = chr(0x0307)
    assert slug_turet("I" + nokta + chr(0x015F) + "arat") == "isarat"
    assert slug_turet("Hutbe-i" + nokta + " " + chr(0x015E) + "ami" + nokta + "ye") == (
        "hutbe-i-samiye"
    )
    assert slug_turet("Di" + nokta + "van-i Harb-i" + nokta + " Orf" + chr(0x00EE)) == (
        "divan-i-harb-i-orfi"
    )
    # ayrik sapka: a + U+0302
    assert slug_turet("As" + "a" + chr(0x0302)) == "asa"


def test_slug_turet_buyuk_ascii_ve_rakam() -> None:
    assert slug_turet("ABC xyz 09") == "abc-xyz-09"
    assert slug_turet("Deneme Kitap 1") == "deneme-kitap-1"


def test_slug_turet_bos_sonuc_hata() -> None:
    for ad in ("", "   ", "...", "'''", "اب"):
        assert _kod(slug_turet, ad) == "BICIM"


def test_slug_turet_64_kesme() -> None:
    uzun = " ".join(["kelime"] * 20)  # 20 * 6 + 19 tire = 139
    ham = slug_turet(uzun, kes=False)
    assert len(ham) == 139
    kesik = slug_turet(uzun)
    assert len(kesik) <= 64
    assert not kesik.endswith("-")
    assert kesik == "-".join(["kelime"] * 9)  # 9 * 6 + 8 = 62 (sozcuk sinirinda kesilir)
    # tire sinirina tam oturan uzunluk
    tam = slug_turet("a" * 64 + " b")
    assert tam == "a" * 64
    # sinirda uzayan tek sozcuk sert kesilir
    assert slug_turet("a" * 70) == "a" * 64


def test_slug_turet_str_lower_kullanmaz() -> None:
    from pathlib import Path

    import mutalaa_pipeline.anchor.risale as modul

    kaynak = Path(modul.__file__).read_text(encoding="utf-8")
    assert ".lower(" not in kaynak.replace("`str.lower()`", "")
