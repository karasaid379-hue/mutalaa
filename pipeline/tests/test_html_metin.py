"""`html_metin` testleri (A06.3). Tum HTML SENTETIKTIR ("Deneme ..." metinleri)."""

import pytest

from mutalaa_pipeline.sources.html_metin import KesmeHatasi, html_metni, paragraf_sec

SAYFA = """<!doctype html>
<html><head>
<title>  Deneme   sayfa
 basligi </title>
<style>.x { color: red }</style>
<script>var gizli = "SCRIPT_METNI";</script>
</head>
<body>
<nav><a href="/">MENU_METNI</a></nav>
<header><h1>UST_BILGI</h1></header>
<main>
<h1>Deneme baslik</h1>
<p>Deneme   paragrafi 1,
 ikinci satir &amp; &lt;etiket&gt; &copy;.</p>
<p>Deneme paragrafi 2<br>satir sonu<br/>bir daha.</p>
<ul><li>Madde 1</li><li>Madde 2</li></ul>
<table><tr><td>Hucre A</td><td>Hucre B</td></tr></table>
<script>icerideki_betik()</script>
</main>
<footer>ALT_BILGI</footer>
</body></html>
"""


def test_baslik_ve_gizli_etiketler() -> None:
    sonuc = html_metni(SAYFA)
    assert sonuc.baslik == "Deneme sayfa basligi"
    for gizli in ("SCRIPT_METNI", "MENU_METNI", "UST_BILGI", "ALT_BILGI", "icerideki_betik"):
        assert gizli not in sonuc.govde


def test_bosluk_sadelestirme_ve_blok_satir_sonlari() -> None:
    govde = html_metni(SAYFA).govde
    assert govde.split("\n") == [
        "Deneme baslik",
        "",
        "Deneme paragrafi 1, ikinci satir & <etiket> ©.",
        "",
        "Deneme paragrafi 2",
        "satir sonu",
        "bir daha.",
        "",
        "Madde 1",
        "Madde 2",
        "",
        "Hucre A Hucre B",
    ]


def test_header_footer_icerik_kabinin_icinde_korunur() -> None:
    html = (
        "<body><footer>DIS_ALT</footer>"
        "<article><header><h1>Deneme baslik</h1></header><p>Deneme govde</p>"
        "<footer>IC_ALT</footer></article></body>"
    )
    govde = html_metni(html).govde
    assert "DIS_ALT" not in govde
    assert govde.split("\n") == ["Deneme baslik", "", "Deneme govde", "", "IC_ALT"]


def test_ic_ice_atlanan_etiket() -> None:
    html = "<p>A</p><nav><nav>x</nav>GIZLI</nav><p>B</p>"
    assert html_metni(html).govde == "A\n\nB"


def test_pre_aynen_korunur() -> None:
    html = (
        '<p>Giris</p><pre class="code">\n  Deneme  satir 1 \n\n    Deneme satir 2\n</pre><p>Son</p>'
    )
    assert html_metni(html).govde.split("\n") == [
        "Giris",
        "",
        "  Deneme  satir 1 ",
        "",
        "    Deneme satir 2",
        "",
        "Son",
    ]


def test_pre_icinde_varlik_cozumu() -> None:
    assert html_metni("<pre>a &amp; b\r\nc</pre>").govde == "a & b\nc"


def test_baslangic_ve_bitis_kesmesi() -> None:
    html = "<h2>Bir</h2><p>A</p><h2>Iki baslik</h2><p>B</p><h2>Uc</h2><p>C</p>"
    assert html_metni(html, baslangic="Iki").govde == "Iki baslik\n\nB\n\nUc\n\nC"
    assert html_metni(html, baslangic="Iki", bitis="Uc").govde == "Iki baslik\n\nB"
    assert html_metni(html, bitis="Iki").govde == "Bir\n\nA"
    # bitis, baslangic satirinin kendisiyle eslesmez (sonraki satirlar aranir)
    with pytest.raises(KesmeHatasi):
        html_metni(html, baslangic="Bir", bitis="Bir")


def test_kesme_bulunamazsa_hata() -> None:
    with pytest.raises(KesmeHatasi):
        html_metni("<p>Deneme</p>", baslangic="Yok")
    with pytest.raises(KesmeHatasi):
        html_metni("<p>Deneme</p>", baslangic="Deneme", bitis="Yok")


def test_bozuk_html_cokmez() -> None:
    assert html_metni("<p>Deneme <b>kalin <i>egik</p> son").govde == "Deneme kalin egik\n\nson"
    assert html_metni("").govde == ""


def test_paragraf_sec() -> None:
    metin = "Deneme bir.\nsatir iki.\n\nBaska paragraf.\n\nDeneme uc, anahtar ifade burada."
    assert paragraf_sec(metin, "anahtar ifade") == "Deneme uc, anahtar ifade burada."
    assert paragraf_sec(metin, "Deneme") == (
        "Deneme bir.\nsatir iki.\n\nDeneme uc, anahtar ifade burada."
    )
    with pytest.raises(KesmeHatasi):
        paragraf_sec(metin, "yok")


def test_bitis_son_icindekiler_listesini_atar() -> None:
    html = (
        "<h1>Deneme baslik</h1><h2>1. Giris</h2><p>A</p><h2>2. Son</h2><p>B</p>"
        "<ul><li>1. Giris</li><li>2. Son</li></ul>"
    )
    assert html_metni(html, baslangic="Deneme", bitis="1. Giris").govde == "Deneme baslik"
    assert html_metni(html, baslangic="Deneme", bitis="1. Giris", bitis_son=True).govde == (
        "Deneme baslik\n\n1. Giris\n\nA\n\n2. Son\n\nB"
    )


def test_sifir_genislikli_bosluk_atilir() -> None:
    sifir = chr(0x200B)
    sonuc = html_metni(f"<title>Ba{sifir}slik</title><h2>1. Tanim{sifir}</h2>")
    assert sonuc.baslik == "Baslik"
    assert sonuc.govde == "1. Tanim"


def test_paragraf_sec_bastaki_satir_sonlari_atilir_bosluklar_korunur() -> None:
    metin = "Deneme bir.\n\n\nAnahtar ifade burada. \nikinci satir \n\n\nSon."
    assert paragraf_sec(metin, "Anahtar") == "Anahtar ifade burada. \nikinci satir "
