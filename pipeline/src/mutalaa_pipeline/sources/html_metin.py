"""HTML sayfasindan duz metin cikarma (A06.3, lisans kopyasi uretimi).

Yalniz standart kutuphane (`html.parser`). Amac lisans ya da sart sayfasinin okunur metnini
almaktir; sayfa duzeni, menu ve betikler atilir. Alinan sozcuklere dokunulmaz: yalniz bosluk
sadelestirilir ve blok etiketlerinde satir sonu konur. `<pre>` icindeki metin aynen korunur.

Kesme ve secme (`baslangic`, `bitis`, `paragraf_sec`) metin uzerinde calisir; CSS secici yoktur.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Final

# Icerigi (alt etiketleriyle birlikte) tamamen atilan etiketler.
HER_ZAMAN_ATLA: Final = frozenset({"script", "style", "nav", "noscript", "template", "svg"})
# `main` ya da `article` icinde degilse atilan etiketler (sayfa ust/alt bilgisi).
KENAR_ATLA: Final = frozenset({"header", "footer"})
ICERIK_KAPLARI: Final = frozenset({"main", "article"})
# Satir sonu koyan blok etiketleri.
BLOK_ETIKETLERI: Final = frozenset(
    {
        "address", "aside", "blockquote", "dd", "details", "div", "dl", "dt", "fieldset",
        "figcaption", "figure", "form", "h1", "h2", "h3", "h4", "h5", "h6", "header", "footer",
        "hr", "li", "main", "ol", "p", "pre", "section", "summary", "table", "tbody", "thead",
        "tfoot", "tr", "ul", "article", "br",
    }
)  # fmt: skip
# Etrafina bos satir koyan etiketler (paragraf ayrimi).
BOSLUKLU_ETIKETLER: Final = frozenset(
    {"p", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote", "ul", "ol", "table", "dl"}
)
HUCRE_ETIKETLERI: Final = frozenset({"td", "th"})
BOSLUK: Final = re.compile("[ \t\r\n\f\v" + chr(0xA0) + "]+")  # ASCII bosluk ve U+00A0


# Docusaurus gibi sitelerde baslik baglantisiyla gelen gorunmez karakter (`<pre>` disinda atilir).
SIFIR_GENISLIK: Final = chr(0x200B)


class KesmeHatasi(ValueError):
    """`baslangic`, `bitis` ya da `paragraf_sec` ifadesi metinde bulunamadi."""


@dataclass(frozen=True)
class HtmlMetni:
    """Cikarilan metin: `<title>` ve govde (LF satir sonlu, sonunda satir sonu yok)."""

    baslik: str
    govde: str


class _Ayristirici(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.satirlar: list[str] = []
        self._parca: list[str] = []
        self._baslik: list[str] = []
        self._baslikta = False
        self._atla_etiket: str | None = None
        self._atla_derinlik = 0
        self._kap = 0
        self._pre = 0
        self._pre_ilk = False
        self._pre_parcalar: list[str] = []

    # --- cikti -------------------------------------------------------------------------

    def baslik(self) -> str:
        return BOSLUK.sub(" ", "".join(self._baslik)).strip(" ")

    def _satiri_kapat(self) -> None:
        metin = BOSLUK.sub(" ", "".join(self._parca)).strip(" ")
        self._parca = []
        if metin:
            self.satirlar.append(metin)

    def _bos_satir(self) -> None:
        if self.satirlar and self.satirlar[-1] != "":
            self.satirlar.append("")

    def _pre_kapat(self) -> None:
        ham = "".join(self._pre_parcalar)
        self._pre_parcalar = []
        ham = ham.replace("\r\n", "\n").replace("\r", "\n")
        if ham.endswith("\n"):
            ham = ham[:-1]
        self._bos_satir()
        self.satirlar.extend(ham.split("\n"))
        self._bos_satir()

    # --- HTMLParser --------------------------------------------------------------------

    def _atlaniyor_mu(self, etiket: str) -> bool:
        return etiket in HER_ZAMAN_ATLA or (etiket in KENAR_ATLA and self._kap == 0)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._atla_etiket is not None:
            if tag == self._atla_etiket:
                self._atla_derinlik += 1
            return
        if self._atlaniyor_mu(tag):
            self._satiri_kapat()
            self._atla_etiket = tag
            self._atla_derinlik = 1
            return
        if tag == "title":
            self._baslikta = True
            return
        if tag in ICERIK_KAPLARI:
            self._kap += 1
        if tag == "pre":
            self._satiri_kapat()
            self._bos_satir()
            self._pre += 1
            self._pre_ilk = True
            return
        if self._pre:
            return
        if tag in BOSLUKLU_ETIKETLER:
            self._satiri_kapat()
            self._bos_satir()
        elif tag in BLOK_ETIKETLERI:
            self._satiri_kapat()
        elif tag in HUCRE_ETIKETLERI:
            self._parca.append(" ")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self._atla_etiket is None and tag in BLOK_ETIKETLERI and not self._pre:
            self._satiri_kapat()

    def handle_endtag(self, tag: str) -> None:
        if self._atla_etiket is not None:
            if tag == self._atla_etiket:
                self._atla_derinlik -= 1
                if self._atla_derinlik == 0:
                    self._atla_etiket = None
            return
        if tag == "title":
            self._baslikta = False
            return
        if tag == "pre" and self._pre:
            self._pre -= 1
            if self._pre == 0:
                self._pre_kapat()
            return
        if self._pre:
            return
        if tag in ICERIK_KAPLARI and self._kap > 0:
            self._kap -= 1
        if tag in BOSLUKLU_ETIKETLER:
            self._satiri_kapat()
            self._bos_satir()
        elif tag in BLOK_ETIKETLERI:
            self._satiri_kapat()

    def handle_data(self, data: str) -> None:
        if self._atla_etiket is not None:
            return
        if self._baslikta:
            self._baslik.append(data.replace(SIFIR_GENISLIK, ""))
            return
        if self._pre:
            if self._pre_ilk:
                self._pre_ilk = False
                if data.startswith("\r\n"):
                    data = data[2:]
                elif data.startswith(("\n", "\r")):
                    data = data[1:]
            self._pre_parcalar.append(data)
            return
        self._parca.append(data.replace(SIFIR_GENISLIK, ""))

    def bitir(self) -> None:
        self._satiri_kapat()
        if self._pre_parcalar:
            self._pre_kapat()


def _kes(
    satirlar: list[str], baslangic: str | None, bitis: str | None, bitis_son: bool
) -> list[str]:
    bas = 0
    if baslangic is not None:
        yer = next((i for i, s in enumerate(satirlar) if s.startswith(baslangic)), None)
        if yer is None:
            raise KesmeHatasi("baslangic ifadesi bulunamadi")
        bas = yer
    son = len(satirlar)
    if bitis is not None:
        adaylar = [i for i in range(bas + 1, len(satirlar)) if satirlar[i].startswith(bitis)]
        if not adaylar:
            raise KesmeHatasi("bitis ifadesi bulunamadi")
        son = adaylar[-1] if bitis_son else adaylar[0]
    return satirlar[bas:son]


def html_metni(
    html: str,
    *,
    baslangic: str | None = None,
    bitis: str | None = None,
    bitis_son: bool = False,
) -> HtmlMetni:
    """HTML'i duz metne cevirir.

    `baslangic`: metnin bu ifadeyle baslayan ilk satirindan baslar (satir dahil).
    `bitis`: baslangictan sonra bu ifadeyle baslayan ilk satirda keser (satir haric);
    `bitis_son` dogruysa bu ifadeyle baslayan SON satirda keser (ornegin sayfa sonundaki
    icindekiler listesini atmak icin). Ifade bulunamazsa `KesmeHatasi`.
    """
    ayristirici = _Ayristirici()
    ayristirici.feed(html)
    ayristirici.close()
    ayristirici.bitir()
    satirlar = _kes(ayristirici.satirlar, baslangic, bitis, bitis_son)
    while satirlar and satirlar[0] == "":
        satirlar.pop(0)
    while satirlar and satirlar[-1] == "":
        satirlar.pop()
    return HtmlMetni(ayristirici.baslik(), "\n".join(satirlar))


def paragraf_sec(metin: str, ifade: str) -> str:
    """`ifade`yi iceren paragraflari (bos satirla ayrilmis bloklar) bos satirla birlestirir.

    Satir sonlari LF kabul edilir. Ifade hicbir paragrafta yoksa `KesmeHatasi`.
    """
    parcalar = re.split(r"\n[ \t]*\n", metin)
    paragraflar = [p.strip("\n") for p in parcalar if ifade in p]
    if not paragraflar:
        raise KesmeHatasi("ifade hicbir paragrafta bulunamadi")
    return "\n\n".join(paragraflar)
