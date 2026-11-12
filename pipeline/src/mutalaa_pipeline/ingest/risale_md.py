"""Diyanet Obsidian markdown ayristirmasi (A20.1, K-51 madde 2): yapi bilgisi, metin DEGIL.

Birim METNI `txt` satirlarindan gelir; bu modul yalniz markdown'un tasidigi ek bilgiyi cikarir:

* baslik duzeyi (`#` ... `######`);
* Arapca isareti (`class="arabic"` iceren `<span>` ve `<p>` etiketleri): satir ici aralik ve
  butun satir (`<p ...>` icinde `<br/>` ile bolunen her parca ayri bir satirdir);
* dipnot tanimi (`[^etiket]: metin`; ilk tanimdan sonraki bos olmayan satirlar onceki tanimin
  devamidir) ve dipnot atfi (`[^etiket]`);
* `***` ayiraci, on yuz (front matter) ve cit (``` ... ```) bloklari: Mermaid gibi cit bloklari
  editoryal ekleme sayilir ve alinmaz.

`duz` alani isaretlemesi arindirilmis dizgidir: etiketler, dipnot atiflari ve yildizlar atilir;
Arapca aralik ucu `duz` uzerinde kod noktasidir (yari acik). `anahtar` hizalama anahtaridir:
NFC sonrasi yalniz harf ve rakamlar; bu yuzden `Aa` ile `Aa:`, kalin yazi isareti ve hareke sirasi
fark yaratmaz. Hizalayamadigi seyi tahmin etmez; cagiran rapora yazar.

Iletiler ve donen yapilar yalniz sayi tasir; metin yalniz bellek ici yapilarda bulunur.
"""

import html
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Final, Literal

BASLIK: Final = re.compile(r"(?P<d>#{1,6}) +(?P<m>.*?)(?: +#+)?")
DIPNOT_TANIMI: Final = re.compile(r"\[\^(?P<e>[^\]\s]+)\]: ?(?P<m>.*)")
DIPNOT_ATFI: Final = re.compile(r"\[\^[^\]\s]+\](?!:)")
ARAPCA_ETIKETI: Final = re.compile(r"<(?:span|p)\b[^>]*\bclass=\"arabic\"[^>]*>")
_P_ARAPCA: Final = re.compile(r"<p\b[^>]*\bclass=\"arabic\"[^>]*>(?P<g>.*)</p>")
_SPAN_ARAPCA: Final = re.compile(r"<span\b[^>]*\bclass=\"arabic\"[^>]*>(?P<g>.*?)</span>")
_BR: Final = re.compile(r"<br\s*/?>")
_ETIKET: Final = re.compile(r"</?[A-Za-z][^>]*>")
_AYIRAC: Final = re.compile(r"\s*(?:\*\s*){3,}|\s*-{3,}|\s*_{3,}")
_KOD_CITI: Final = re.compile(r"\s*(?:`{3,}|~{3,})")

Tur = Literal["baslik", "paragraf"]


@dataclass(frozen=True, slots=True)
class MdSatir:
    """Bir mantiksal markdown satiri (`<br/>` ile bolunmus parca dahil)."""

    tur: Tur
    duzey: int | None  # yalniz baslikta
    duz: str
    anahtar: str
    araplar: tuple[tuple[int, int], ...]  # duz uzerinde yari acik kod noktasi araliklari
    arapca_metinleri: tuple[str, ...]  # araliklarin metinleri (txt satirinda aramak icin)
    tam_arapca: bool  # satirin tamami Arapca isaretli
    grup: int = 0  # ayni markdown satirindan (`<br/>` ile bolunmus) gelen parcalarin ortak no'su


@dataclass(frozen=True, slots=True)
class MdDipnot:
    etiket: str
    satirlar: tuple[MdSatir, ...]  # ilk satir tanim satiri, gerisi devam


@dataclass(frozen=True)
class MdBelge:
    govde: tuple[MdSatir, ...]
    dipnotlar: tuple[MdDipnot, ...]
    sayilar: dict[str, int] = field(default_factory=dict)


def anahtar_uret(metin: str) -> str:
    """Hizalama anahtari: NFC, yalniz harf ve rakamlar (hareke, noktalama ve bosluk atilir)."""
    return "".join(h for h in unicodedata.normalize("NFC", metin) if h.isalnum())


def _parca_duz(parca: str, cikti: list[str], uzunluk: int) -> int:
    """Arapca olmayan parcayi isaretlemeden arindirip `cikti`ya ekler; yeni uzunluk."""
    parca = DIPNOT_ATFI.sub("", parca)
    parca = _ETIKET.sub("", parca)
    parca = html.unescape(parca).replace("*", "")
    cikti.append(parca)
    return uzunluk + len(parca)


def _satir_duz(
    segment: str, *, tam: bool
) -> tuple[str, tuple[tuple[int, int], ...], tuple[str, ...]]:
    """Bir mantiksal satirin `duz` metni, Arapca araliklari ve Arapca parca metinleri."""
    cikti: list[str] = []
    uzunluk = 0
    araliklar: list[tuple[int, int]] = []
    metinler: list[str] = []
    if tam:
        govde = html.unescape(_ETIKET.sub("", segment)).replace("*", "")
        return govde, ((0, len(govde)),) if govde else (), (govde,) if govde else ()
    son = 0
    for eslesme in _SPAN_ARAPCA.finditer(segment):
        uzunluk = _parca_duz(segment[son : eslesme.start()], cikti, uzunluk)
        govde = html.unescape(_ETIKET.sub("", eslesme.group("g"))).replace("*", "")
        if govde:
            araliklar.append((uzunluk, uzunluk + len(govde)))
            metinler.append(govde)
        cikti.append(govde)
        uzunluk += len(govde)
        son = eslesme.end()
    _parca_duz(segment[son:], cikti, uzunluk)
    return "".join(cikti), tuple(araliklar), tuple(metinler)


def _mantiksal_satirlar(ham: str) -> list[tuple[str, bool]]:
    """Bir markdown satirini `<br/>` ve `<p class="arabic">` kurallarina gore parcalar.

    Doner: (parca, tam_arapca) listesi. `<p class="arabic">` butun satiri sariyorsa her `<br/>`
    parcasi tam Arapca bir satirdir.
    """
    p = _P_ARAPCA.fullmatch(ham.strip())
    if p is not None:
        return [(parca, True) for parca in _BR.split(p.group("g"))]
    return [(parca, False) for parca in _BR.split(ham)]


def _satir_yap(parca: str, tam: bool, tur: Tur, duzey: int | None, grup: int = 0) -> MdSatir:
    duz, araliklar, metinler = _satir_duz(parca, tam=tam)
    return MdSatir(tur, duzey, duz, anahtar_uret(duz), araliklar, metinler, tam, grup)


def md_coz(metin: str) -> MdBelge:
    """Bir markdown dosyasini cozer; yapi hatasi vermez (tanimadigi satir paragraftir)."""
    satirlar = [s[:-1] if s.endswith("\r") else s for s in metin.split("\n")]
    i = 0
    if satirlar and satirlar[0].strip() == "---":
        j = next((k for k in range(1, len(satirlar)) if satirlar[k].strip() == "---"), None)
        if j is not None:
            i = j + 1
    govde: list[MdSatir] = []
    dipnotlar: list[tuple[str, list[MdSatir]]] = []
    arapca = atif = tanim = kod_blogu = ayirac = grup = 0
    kod_icinde = False
    for ham in satirlar[i:]:
        if _KOD_CITI.match(ham):
            kod_icinde = not kod_icinde
            if kod_icinde:
                kod_blogu += 1
            continue
        if kod_icinde or ham.strip() == "":
            continue
        if _AYIRAC.fullmatch(ham.strip()) is not None:
            ayirac += 1
            continue
        arapca += len(ARAPCA_ETIKETI.findall(ham))
        tanimi = DIPNOT_TANIMI.fullmatch(ham)
        atif += len(DIPNOT_ATFI.findall(tanimi.group("m") if tanimi else ham))
        if tanimi is not None:
            tanim += 1
            parcalar = _mantiksal_satirlar(tanimi.group("m"))
            ilk = _satir_yap(parcalar[0][0], parcalar[0][1], "paragraf", None)
            kalan = [_satir_yap(p, t, "paragraf", None) for p, t in parcalar[1:]]
            dipnotlar.append((tanimi.group("e"), [ilk, *kalan]))
            continue
        if dipnotlar:  # ilk tanimdan sonrasi: onceki tanimin devami
            dipnotlar[-1][1].extend(
                _satir_yap(p, t, "paragraf", None) for p, t in _mantiksal_satirlar(ham)
            )
            continue
        baslik = BASLIK.fullmatch(ham)
        if baslik is not None:
            govde.append(_satir_yap(baslik.group("m"), False, "baslik", len(baslik.group("d"))))
            continue
        grup += 1
        govde.extend(_satir_yap(p, t, "paragraf", None, grup) for p, t in _mantiksal_satirlar(ham))
    return MdBelge(
        govde=tuple(govde),
        dipnotlar=tuple(MdDipnot(e, tuple(s)) for e, s in dipnotlar),
        sayilar={
            "dipnot_tanimi": tanim,
            "dipnot_atfi": atif,
            "arapca_isareti": arapca,
            "baslik": sum(1 for s in govde if s.tur == "baslik"),
            "kod_blogu": kod_blogu,
            "ayirac": ayirac,
        },
    )
