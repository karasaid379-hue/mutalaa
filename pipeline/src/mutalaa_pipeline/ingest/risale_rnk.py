"""RNK `txt` ayristirici (A20.1b, K-51 madde 2 ve 5): saf islevler, dosya ya da veritabani yok.

RNK Neşriyat kitap dosyasi (`{raf}/{uid}.txt`) satir satir ayristirilir:

* `#n` satirlari basili sayfa basidir (`sayfalar`); `,* * *>` ayirac ve bos satirlar `yapi`dir;
  ikisi de birim uretmez.
* Girinti 0 ve 1 (tek bosluk) ayni sinifa girer: `,* * *>` ayirac, `<&€∑...>` baslik ve `,...>`
  ortali paragraf (ayirac olmayan virgul zinciri) tek bosluk girintili de ayni sekilde sayilir.
* `<`, `&`, `€`, `∑` ile baslayip `>` ile biten satirlar baslik birimidir; girintili satirlar
  (3 sutun: 3 bosluk, 2 bosluk + `\\`, 2 bosluk + `∫`) paragraf basidir; 1 bosluklu ve girintisiz
  satirlar ayni paragrafa eklenir (ar ve ar_k raflarinda girinti yoktur: her girintisiz satir
  paragraf, `#n` sonrasi devam yalniz onceki satir cumle sonu degilse).
* `{...}` dipnot ayri `hasiye` birimi olur (cok satirli dipnotun ic paragraflari ayri birim); ana
  paragrafta `t: "hasiye"` isareti ek noktasini verir.
* Isaret karakterleri (`~ @ | \\ < > { } € ∑ ∫ ﹛ ﹜ § ÷ ` % ½ & ,`) birim metninden cikarilir ve
  `marks` icine `t: "rnk"` olarak yazilir; isaretin icindeki metin kalir. `~...|@` Arapca blok ve
  `﹛...|﹜` Arapca alinti ayrica `t: "ar"` araligi verir.

Kaynak bayt bayt yeniden kurulabilir (`yeniden_kur`): her cikarilan isaret (satir, sutun) ile,
her metin parcasi `segmentler` (`[satir, sutun, bas, bit]`) ile konumlanir. Birlestirme icin
eklenen bosluk `t: "satir"` isaretiyle belirtilir ve kaynaga ait degildir. Konumlar Unicode kod
noktasidir ve araliklar yari acik `[bas, bit)`. Kaynak NFC'ye ya da baska donusume girmez.

Dosya duzeyi bilgi (BOM, CR, son satir sonu) metne girmez; `KitapAyristirma`da durur. Anlami
veriden cikmayan isaretler yorumlanmaz: yalniz konumlari ve ham karakterleri kaydedilir.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi

AYRISTIRICI_SURUMU: Final = "2"

BOM: Final = "\ufeff"

# Isaret karakterleri (virgul haric: yalniz satir basinda isarettir).
ISARET_SIRASI: Final = (
    "~",
    "@",
    "|",
    "\\",
    "<",
    ">",
    "{",
    "}",
    "\u20ac",  # euro
    "\u2211",  # n-ary summation
    "\u222b",  # integral
    "\ufe5b",  # small left curly bracket
    "\ufe5c",  # small right curly bracket
    "\u00a7",  # section sign
    "\u00f7",  # division sign
    "`",
    "%",
    "\u00bd",  # one half
    "&",
)
ISARETLER: Final = frozenset(ISARET_SIRASI)
_ISARET_DESENI: Final = re.compile("[" + re.escape("".join(ISARET_SIRASI)) + "]")

# `>` ile kapanan acilislar.
ACI_ACILIS: Final = frozenset("\\<&\u20ac\u2211\u222b\u00a7\u00f7`%,")
BASLIK_ACILISLARI: Final = frozenset("<&\u20ac\u2211")
# Satir basinda tek basina yeni (girintisiz) paragraf baslatan isaretler.
YENI_PARAGRAF_ISARETLERI: Final = frozenset(",\u00a7\u00f7`%<&\u20ac\u2211")
AR_ACILIS: Final = "~"
AR_KAPANIS: Final = "@"
ALINTI_ACILIS: Final = "\ufe5b"
ALINTI_KAPANIS: Final = "\ufe5c"
YARIM: Final = "\u00bd"

SAYFA_DESENI: Final = re.compile("#[0-9]+")
AYIRAC_DESENI: Final = re.compile(r",[* ]*>")
AR_RAFLARI: Final = frozenset({"ar", "ar_k"})

# Cumle sonu (ar raflarinda sayfa sonrasi devam kurali): son isaret ve kapanis karakterleri.
_CUMLE_SONLARI: Final = ".?!\u2026\u061f\u06dd"
_KAPANIS: Final = "\"')]}\u00bb\u201d\u2019\ufd3e"

# Metinde olduğu gibi kalan, denetlenen karakterler (K-51 madde 5).
S12_KUMESI: Final = frozenset(
    {
        0x00A0,
        0x2005,
        0x2006,
        0x2009,
        0x200A,
        0x202F,
        0x200C,
        0x200D,
        0x200F,
        0x00AD,
        0x06DD,
        0xEEE3,
        0xEEE4,
        0xEEE5,
    }
)
_DENETLENEN_KATEGORILER: Final = frozenset({"Cc", "Cf", "Zs", "Zl", "Zp", "Co", "Cs", "Cn"})


def kod_adi(kod: int) -> str:
    return f"U+{kod:04X}"


def denetlenen_karakter_mi(ch: str) -> bool:
    """Kilitte tek tek sayilan karakter: S12 kumesi ve kontrol/bicim/bosluk/ozel kullanim siniflari.

    Satir sonu (LF, CR) ve U+0020 dosya duzeyi bilgi ya da duz bosluktur; sayilmaz.
    """
    if ch in "\n\r ":
        return False
    return ord(ch) in S12_KUMESI or unicodedata.category(ch) in _DENETLENEN_KATEGORILER


# ---------------------------------------------------------------------------
# Veri yapilari


@dataclass
class SayfaKaydi:
    """`#n` satiri: sayfa `n`, kaynak satiri; `birim` sayfanin ilk metnini tasiyan birim sirasi."""

    n: int
    satir: int
    birim: int | None = None
    ofs: int = 0


@dataclass
class Birim:
    """Ham birim: baslik, paragraf ya da hasiye paragrafi. `sira` kaynakta acilis sirasidir."""

    sira: int
    tur: str  # "baslik" | "paragraf" | "hasiye"
    ilk_satir: int
    parcalar: list[str] = field(default_factory=list)
    uzunluk: int = 0
    isaretler: list[dict[str, object]] = field(default_factory=list)
    segmentler: list[list[int]] = field(default_factory=list)
    yigin: list[dict[str, object]] = field(default_factory=list)
    ozellik: dict[str, object] = field(default_factory=dict)
    son_satir: int = 0
    ust: int | None = None  # hasiye icin ana paragrafin sirasi
    hasiye_sira: int | None = None  # kitapta hasiye sirasi (0 tabanli)
    ic_sira: int = 0  # hasiye icindeki paragraf sirasi (0 tabanli)
    acik_kolon: int | None = None  # acik metin parcasinin baslangic sutunu
    acik_satir: int = 0
    acik_bas: int = 0

    @property
    def metin(self) -> str:
        return "".join(self.parcalar)


@dataclass
class KitapAyristirma:
    birimler: list[Birim]
    sayfalar: list[SayfaKaydi]
    yapi: list[tuple[int, str]]  # (satir, ham satir): bos satir ve ayirac
    satir_sayisi: int
    bom: bool
    cr_satir: int  # sonunda CR bulunan satir sayisi
    cr_son: bool  # son satirda CR var mi (LF'siz son satirda CRLF terminatoru olmaz)
    son_lf: bool  # dosya LF ile bitiyor mu
    uyarilar: Counter[str]
    satir_turleri: Counter[str]


# ---------------------------------------------------------------------------
# Dosya duzeyi


def dosya_coz(veri: bytes) -> tuple[list[str], bool, list[bool], bool]:
    """`txt` baytlarini satirlara boler: (satirlar, bom, cr_bayraklari, son_lf).

    BOM ve satir sonundaki CR metne girmez; satir sonu LF'dir. UTF-8 olmayan bayt `GirdiHatasi`.
    """
    try:
        metin = veri.decode("utf-8")
    except UnicodeDecodeError:
        raise GirdiHatasi("rnk txt: UTF-8 degil") from None
    bom = metin.startswith(BOM)
    if bom:
        metin = metin[1:]
    satirlar = metin.split("\n") if metin != "" else []
    son_lf = False
    if satirlar and satirlar[-1] == "":
        satirlar.pop()
        son_lf = True
    cr: list[bool] = []
    temiz: list[str] = []
    for satir in satirlar:
        if satir.endswith("\r"):
            cr.append(True)
            temiz.append(satir[:-1])
        else:
            cr.append(False)
            temiz.append(satir)
    return temiz, bom, cr, son_lf


def cumle_sonu_mu(metin: str) -> bool:
    kesik = metin.rstrip().rstrip(_KAPANIS).rstrip()
    return kesik != "" and kesik[-1] in _CUMLE_SONLARI


# ---------------------------------------------------------------------------
# Ayristirici


class _Hasiye:
    __slots__ = ("ana", "birimler", "devam")

    def __init__(self, ana: Birim | None, devam: Birim | None, ilk: Birim) -> None:
        self.ana = ana  # ek noktasinin bulundugu paragraf
        self.devam = devam  # dipnottan sonra metnin donecegi birim
        self.birimler = [ilk]


class _Ayristirici:
    def __init__(self, raf: str) -> None:
        self.ar_raf = raf in AR_RAFLARI
        self.birimler: list[Birim] = []
        self.sayfalar: list[SayfaKaydi] = []
        self.yapi: list[tuple[int, str]] = []
        self.uyari: Counter[str] = Counter()
        self.tur: Counter[str] = Counter()
        self.bekleyen: list[SayfaKaydi] = []
        self.acik: Birim | None = None
        self.son_par: Birim | None = None
        self.cur: Birim | None = None
        self.hasiye: _Hasiye | None = None
        self.hasiye_sayisi = 0
        self.girinti_bekleyen = ""

    # --- birim yonetimi -------------------------------------------------------------------

    def yeni(self, tur: str, satir: int) -> Birim:
        b = Birim(sira=len(self.birimler), tur=tur, ilk_satir=satir, son_satir=satir)
        self.birimler.append(b)
        return b

    def bitir(self, b: Birim | None) -> None:
        """Birim kalici olarak kapandi: kapanmayan acilislar dengesiz isarete doner."""
        if b is None:
            return
        self._metin_kapat(b)
        for acilis in b.yigin:
            acilis["u"] = 1
            self.uyari["dengesiz_acilis"] += 1
        b.yigin.clear()

    def kapat_acik(self) -> None:
        self.bitir(self.acik)
        self.acik = None

    def _dokun(self, b: Birim, satir: int) -> None:
        if satir < b.ilk_satir:
            b.ilk_satir = satir
        if satir > b.son_satir:
            b.son_satir = satir

    # --- metin ve isaret ekleme ----------------------------------------------------------

    def _metin_kapat(self, b: Birim) -> None:
        if b.acik_kolon is not None:
            b.segmentler.append([b.acik_satir, b.acik_kolon, b.acik_bas, b.uzunluk])
            b.acik_kolon = None

    def metin_ekle(self, b: Birim, parca: str, satir: int, kolon: int) -> None:
        if parca == "":
            return
        if self.bekleyen:
            ilk = len(parca) - len(parca.lstrip())
            if ilk < len(parca):
                for kayit in self.bekleyen:
                    kayit.birim = b.sira
                    kayit.ofs = b.uzunluk + ilk
                self.bekleyen = []
        if b.acik_kolon is not None and b.acik_satir != satir:
            self._metin_kapat(b)
        if b.acik_kolon is None:
            b.acik_kolon = kolon
            b.acik_satir = satir
            b.acik_bas = b.uzunluk
        b.parcalar.append(parca)
        b.uzunluk += len(parca)
        self._dokun(b, satir)

    def isaret_yaz(
        self,
        b: Birim,
        ham: str,
        satir: int,
        kolon: int,
        *,
        dengesiz: bool = False,
    ) -> dict[str, object]:
        """Tek basina (esi olmayan) isaret; metne girmez."""
        kayit: dict[str, object] = {
            "t": "rnk",
            "c": ham,
            "s": b.uzunluk,
            "e": b.uzunluk,
            "l": satir,
            "x": kolon,
        }
        if dengesiz:
            kayit["u"] = 1
        b.isaretler.append(kayit)
        self._dokun(b, satir)
        return kayit

    def ac(self, b: Birim, ham: str, satir: int, kolon: int) -> None:
        kayit = self.isaret_yaz(b, ham, satir, kolon)
        b.yigin.append(kayit)

    def kapa(self, b: Birim, ham: str, satir: int, kolon: int) -> None:
        """Kapanis karakteri: en ustteki uygun acilisi kapatir; yoksa dengesiz tek isaret."""
        uygun = self._uygun_acilis(b, ham)
        if uygun is None:
            self.isaret_yaz(b, ham, satir, kolon, dengesiz=True)
            self.uyari["dengesiz_kapanis"] += 1
            return
        b.yigin.pop()
        uygun["k"] = ham
        uygun["e"] = b.uzunluk
        uygun["m"] = satir
        uygun["y"] = kolon
        self._dokun(b, satir)
        if uygun["c"] == AR_ACILIS:
            b.isaretler.append({"t": "ar", "s": uygun["s"], "e": b.uzunluk, "tur": "blok"})
        elif uygun["c"] == ALINTI_ACILIS:
            b.isaretler.append({"t": "ar", "s": uygun["s"], "e": b.uzunluk, "tur": "alinti"})

    @staticmethod
    def _uygun_acilis(b: Birim, kapanis: str) -> dict[str, object] | None:
        if not b.yigin:
            return None
        ust = b.yigin[-1]
        acilis = ust["c"]
        if kapanis == ">" and (acilis in ACI_ACILIS or acilis == YARIM):
            return ust
        if kapanis == AR_KAPANIS and acilis == AR_ACILIS:
            return ust
        if kapanis == ALINTI_KAPANIS and acilis == ALINTI_ACILIS:
            return ust
        if kapanis == YARIM and acilis == YARIM:
            return ust
        return None

    def birlestir(self, b: Birim, satir: int, ilk_karakter: str | None) -> None:
        """Yeni satir onceki metne eklenirken gerekirse tek bosluk koyar (`t: "satir"`)."""
        if b.uzunluk == 0:
            return
        if ilk_karakter is not None and ilk_karakter.isspace():
            return
        if b.parcalar and b.parcalar[-1][-1:].isspace():
            return
        konum = b.uzunluk
        b.parcalar.append(" ")
        b.uzunluk += 1
        b.isaretler.append({"t": "satir", "s": konum, "e": konum + 1})
        self._dokun(b, satir)

    # --- satir tarama -------------------------------------------------------------------

    def tara(self, satir_no: int, satir: str, kolon: int, ilk_bosluk_sonu: int) -> None:
        """`satir[kolon:]` taranir; metin `self.cur` birimine, isaretler isaret yazicilarina gider.

        `ilk_bosluk_sonu`: satirdaki ilk bosluk olmayan karakterin sutunu (virgul bunun icin).
        """
        i = kolon
        n = len(satir)
        while i < n:
            if self.cur is None:
                if satir[i] == "{" and self.hasiye is None:
                    i = self._hasiye_basla(None, satir_no, satir, i)
                    continue
                self._yetim_paragraf(satir_no)
            cur = self.cur
            assert cur is not None
            if i == ilk_bosluk_sonu and satir[i] == ",":
                self.ac(cur, ",", satir_no, i)
                i += 1
                continue
            eslesme = _ISARET_DESENI.search(satir, i)
            son = eslesme.start() if eslesme else n
            if son > i:
                self.metin_ekle(cur, satir[i:son], satir_no, i)
                i = son
                continue
            ch = satir[i]
            i = self._isaret(cur, ch, satir_no, satir, i)
        # satir sonu: acik metin parcasi kapanir (satir degisti)
        if self.cur is not None:
            self._metin_kapat(self.cur)
        if self.hasiye is not None:
            for h in self.hasiye.birimler:
                self._metin_kapat(h)
        if self.acik is not None:
            self._metin_kapat(self.acik)

    def _isaret(self, b: Birim, ch: str, satir_no: int, satir: str, i: int) -> int:
        if ch == "{":
            return self._hasiye_basla(b, satir_no, satir, i)
        if ch == "}":
            if self.hasiye is not None and b.tur == "hasiye":
                self.isaret_yaz(b, "}", satir_no, i)
                self._hasiye_bitir()
            else:
                self.isaret_yaz(b, "}", satir_no, i, dengesiz=True)
                self.uyari["dengesiz_kapanis"] += 1
            return i + 1
        if ch == YARIM:  # hem ½...½ hem ½...> goruluyor: ustte ½ aciksa kapatir
            if b.yigin and b.yigin[-1]["c"] == YARIM:
                self.kapa(b, ch, satir_no, i)
            else:
                self.ac(b, ch, satir_no, i)
            return i + 1
        if ch in ACI_ACILIS or ch in (AR_ACILIS, ALINTI_ACILIS):
            self.ac(b, ch, satir_no, i)
            return i + 1
        if ch in (">", AR_KAPANIS, ALINTI_KAPANIS):
            self.kapa(b, ch, satir_no, i)
            return i + 1
        # "|"
        self.isaret_yaz(b, ch, satir_no, i)
        return i + 1

    # --- hasiye ---------------------------------------------------------------------------

    def _hasiye_basla(self, b: Birim | None, satir_no: int, satir: str, i: int) -> int:
        if self.hasiye is not None and b is not None:
            self.isaret_yaz(b, "{", satir_no, i, dengesiz=True)
            self.uyari["ic_ice_hasiye"] += 1
            return i + 1
        ham, bicim, sonraki = self._etiket(satir, i + 1)
        ana = b if b is not None else self.son_par
        if b is not None:
            self._metin_kapat(b)
        h = self.yeni("hasiye", satir_no)
        h.hasiye_sira = self.hasiye_sayisi
        self.hasiye_sayisi += 1
        h.ozellik["etiket_bicimi"] = bicim
        if self.girinti_bekleyen:
            self.isaret_yaz(h, self.girinti_bekleyen, satir_no, 0)
            self.girinti_bekleyen = ""
        if ana is not None:
            h.ust = ana.sira
            ana.isaretler.append({"t": "hasiye", "s": ana.uzunluk, "e": ana.uzunluk, "h": h.sira})
            self._dokun(ana, satir_no)
        else:
            self.uyari["hasiye_ana_yok"] += 1
        self.hasiye = _Hasiye(ana, b, h)
        self.cur = h
        self.isaret_yaz(h, "{", satir_no, i)
        if ham != "":
            self.isaret_yaz(h, ham, satir_no, i + 1)
        if bicim == "-":
            self.uyari["hasiye_etiketsiz"] += 1
        return sonraki

    @staticmethod
    def _etiket(satir: str, j: int) -> tuple[str, str, int]:
        """Dipnot etiketi: (ham etiket, bicim, govdenin basladigi sutun)."""
        if satir[j : j + 1] == "(":
            k = satir.find(")", j)
            if k != -1:
                sonra = satir[k + 1 : k + 2]
                if sonra == "|":
                    return satir[j : k + 2], "(e)|", k + 2
                if sonra == " ":
                    return satir[j : k + 2], "(e) ", k + 2
                return satir[j : k + 1], "(e)", k + 1
            return "", "-", j
        k = satir.find("|", j)
        if k != -1 and 0 < k - j <= 40:
            etiket = satir[j:k]
            if not any(c.isspace() or c in ISARETLER or c == "," for c in etiket):
                return satir[j : k + 1], "e|", k + 1
        return "", "-", j

    def _hasiye_bitir(self) -> None:
        h = self.hasiye
        assert h is not None
        for b in h.birimler:
            self.bitir(b)
        self.hasiye = None
        self.cur = h.devam

    def _yetim_paragraf(self, satir_no: int) -> None:
        """Acik paragraf yokken gelen girintisiz satir yeni paragraf olur (uyari degil sayac)."""
        self.yeni_paragraf(satir_no)
        assert self.acik is not None
        self.acik.ozellik["girintisiz"] = True
        self.tur["girintisiz_paragraf"] += 1

    def yeni_paragraf(self, satir_no: int, girinti: str = "") -> Birim:
        self.kapat_acik()
        b = self.yeni("paragraf", satir_no)
        self.acik = b
        self.son_par = b
        self.cur = b
        if girinti:
            self.isaret_yaz(b, girinti, satir_no, 0)
        return b

    # --- satir siniflandirma -------------------------------------------------------------

    def satir_isle(self, no: int, satir: str) -> None:
        if SAYFA_DESENI.fullmatch(satir):
            self.tur["sayfa"] += 1
            kayit = SayfaKaydi(int(satir[1:]), no)
            self.sayfalar.append(kayit)
            self.bekleyen.append(kayit)
            return
        if satir.strip(" ") == "":
            self.tur["bos"] += 1
            self.yapi.append((no, satir))
            if self.hasiye is None:
                self.kapat_acik()
            return
        if self.hasiye is not None:
            self._hasiye_satiri(no, satir)
            return
        self._ust_satir(no, satir)

    def _ust_satir(self, no: int, satir: str) -> None:
        girinti = len(satir) - len(satir.lstrip(" "))
        govde = satir[girinti:]
        ilk = govde[0]
        # Girinti 0 ve 1 (tek bosluk) ayni sinifa girer: basta bosluk satir turunu degistirmez.
        kenar = girinti <= 1
        if kenar and AYIRAC_DESENI.fullmatch(govde):
            self.tur["ayirac"] += 1
            self.yapi.append((no, satir))
            self.kapat_acik()
            return
        if kenar and ilk in BASLIK_ACILISLARI and satir.endswith(">"):
            self.tur["baslik"] += 1
            self.kapat_acik()
            b = self.yeni("baslik", no)
            self.son_par = b  # sonraki satir basi dipnot basliga baglanir
            b.ozellik["baslik_isareti"] = ilk
            self.cur = b
            if girinti:
                self.isaret_yaz(b, satir[:girinti], no, 0)
            self.tara(no, satir, girinti, girinti)
            self.bitir(b)
            self.cur = None
            return
        if ilk == "{":
            self.tur["hasiye"] += 1
            self.cur = self.acik
            self.girinti_bekleyen = satir[:girinti]
            self.tara(no, satir, girinti, girinti)
            self.girinti_bekleyen = ""
            return
        yeni_baslangic = (
            girinti >= 3
            or (girinti == 2 and ilk in "\\\u222b")
            or (girinti == 0 and ilk in YENI_PARAGRAF_ISARETLERI)
            or (kenar and ilk == ",")  # ortali paragraf: `,...>` (K-51 madde 2); ayirac degil
        )
        if girinti == 2 and not yeni_baslangic:
            yeni_baslangic = True
            self.uyari["girinti_2_belirsiz"] += 1
        if girinti >= 4:
            self.uyari["girinti_4_ve_ustu"] += 1
        if yeni_baslangic:
            self.tur["paragraf_basi"] += 1
            b = self.yeni_paragraf(no, satir[:girinti])
            self.cur = b
            self.tara(no, satir, girinti, girinti)
            return
        # devam adayi (girinti 0 ya da 1)
        if self.ar_raf and girinti == 0 and not self._ar_devam():
            self.tur["paragraf_basi_ar"] += 1
            b = self.yeni_paragraf(no)
            self.cur = b
            self.tara(no, satir, 0, 0)
            return
        self.tur["devam"] += 1
        if self.acik is None:
            self._yetim_paragraf(no)
        else:
            self.cur = self.acik
            self.birlestir(self.acik, no, satir[0])
        self.tara(no, satir, 0, girinti)

    def _ar_devam(self) -> bool:
        """ar raflarinda girintisiz satir devam mi: sayfa sonrasi ve onceki cumle bitmemis."""
        if self.acik is None or not self.bekleyen:
            return False
        return not cumle_sonu_mu(self.acik.metin)

    def _hasiye_satiri(self, no: int, satir: str) -> None:
        h = self.hasiye
        assert h is not None
        girinti = len(satir) - len(satir.lstrip(" "))
        ilk = satir[girinti]
        yeni_ic = (
            girinti >= 2
            or (girinti == 0 and ilk in YENI_PARAGRAF_ISARETLERI)
            or (girinti == 1 and ilk == ",")
        )
        if h.birimler[-1].uzunluk == 0:  # govde onceki satirda baslamamis: ayni birim surer
            b = h.birimler[-1]
            self.tur["hasiye_govde_alt_satirda"] += 1
            self.cur = b
            if girinti:
                self.isaret_yaz(b, satir[:girinti], no, 0)
            self.tara(no, satir, girinti, girinti)
            return
        if yeni_ic:
            self.tur["hasiye_ic_paragraf"] += 1
            onceki = h.birimler[-1]
            self.bitir(onceki)
            b = self.yeni("hasiye", no)
            b.ust = onceki.ust
            b.hasiye_sira = onceki.hasiye_sira
            b.ic_sira = onceki.ic_sira + 1
            b.ozellik["etiket_bicimi"] = "-"
            h.birimler.append(b)
            self.cur = b
            if girinti:
                self.isaret_yaz(b, satir[:girinti], no, 0)
            self.tara(no, satir, girinti, girinti)
            return
        self.tur["hasiye_devam"] += 1
        b = h.birimler[-1]
        self.cur = b
        self.birlestir(b, no, satir[0])
        self.tara(no, satir, 0, girinti)

    def bitis(self) -> None:
        if self.hasiye is not None:
            self.uyari["hasiye_kapanmadi"] += 1
            for b in self.hasiye.birimler:
                self.bitir(b)
            self.hasiye = None
        self.bitir(self.acik)
        self.acik = None
        for b in self.birimler:
            if b.yigin:
                self.bitir(b)
            if b.uzunluk == 0:
                self.uyari["bos_birim"] += 1
        if self.bekleyen:
            self.uyari["icerigi_olmayan_sayfa"] += len(self.bekleyen)


def ayristir(veri: bytes, raf: str) -> KitapAyristirma:
    """`txt` baytlarini birimlere, sayfalara ve yapi satirlarina ayirir (saf islev)."""
    satirlar, bom, cr, son_lf = dosya_coz(veri)
    a = _Ayristirici(raf)
    for no, satir in enumerate(satirlar, start=1):
        a.satir_isle(no, satir)
    a.bitis()
    return KitapAyristirma(
        birimler=a.birimler,
        sayfalar=a.sayfalar,
        yapi=a.yapi,
        satir_sayisi=len(satirlar),
        bom=bom,
        cr_satir=sum(cr),
        cr_son=bool(cr) and cr[-1],
        son_lf=son_lf,
        uyarilar=a.uyari,
        satir_turleri=a.tur,
    )


# ---------------------------------------------------------------------------
# Yeniden kurma (G-BUT): birim metni + isaretler + segmentler + yapi -> kaynak baytlari


def _satir_birlestir(
    olaylar: dict[int, str], parcalar: list[tuple[int, str]], satir_no: int
) -> str | None:
    """Bir satirin sutunlarini doldurur; bosluk ya da artan parca olursa `None`."""
    sirali = sorted(parcalar)
    cikti: list[str] = []
    kolon = 0
    si = 0
    gecerli = ""
    konum = 0
    kullanilan = 0
    while True:
        ham = olaylar.get(kolon)
        if ham is not None:
            cikti.append(ham)
            kolon += len(ham)
            kullanilan += 1
            continue
        if konum >= len(gecerli):
            if si >= len(sirali):
                break
            baslangic, gecerli = sirali[si]
            si += 1
            konum = 0
            if baslangic != kolon:
                return None
            if gecerli == "":
                continue
        cikti.append(gecerli[konum])
        konum += 1
        kolon += 1
    if kullanilan != len(olaylar) or si != len(sirali) or konum != len(gecerli):
        return None
    return "".join(cikti)


def yeniden_kur(
    *,
    birimler: list[dict[str, object]],
    sayfalar: list[tuple[int, int]],
    yapi: list[tuple[int, str]],
    satir_sayisi: int,
    bom: bool,
    cr_satir: int,
    cr_son: bool,
    son_lf: bool,
) -> bytes | None:
    """Kaynak dosyayi birimlerden yeniden kurar; tutarsizlikta `None`.

    `birimler`: her biri `text`, `marks` (rnk isaretleri) ve `segmentler` (`[satir, sutun, bas,
    bit]`, satirlar 1 tabanli) tasir. `sayfalar`: `(n, satir)`. `yapi`: `(satir, ham satir)`.
    `cr_satir` (CR'li satir sayisi) ve `cr_son`: son satir disindaki satirlar ya hep ya hic
    CR'lidir.
    """
    olaylar: dict[int, dict[int, str]] = {}
    parcalar: dict[int, list[tuple[int, str]]] = {}

    def tam(deger: object) -> int:
        if not isinstance(deger, int) or isinstance(deger, bool):
            raise GirdiHatasi("isaret konumu tam sayi degil")
        return deger

    for birim in birimler:
        metin = birim["text"]
        isaretler = birim["marks"]
        segmentler = birim["segmentler"]
        assert isinstance(metin, str)
        assert isinstance(isaretler, list)
        assert isinstance(segmentler, list)
        for isaret in isaretler:
            if isaret.get("t") != "rnk":
                continue
            acilis = olaylar.setdefault(tam(isaret["l"]), {})
            if tam(isaret["x"]) in acilis:
                return None
            acilis[tam(isaret["x"])] = str(isaret["c"])
            if "k" in isaret:
                kapanis = olaylar.setdefault(tam(isaret["m"]), {})
                if tam(isaret["y"]) in kapanis:
                    return None
                kapanis[tam(isaret["y"])] = str(isaret["k"])
        for segment in segmentler:
            satir_no, kolon, bas, bit = (tam(v) for v in segment)
            parcalar.setdefault(satir_no, []).append((kolon, metin[bas:bit]))
    hedef: dict[int, str] = {}
    for no, ham in yapi:
        hedef[no] = ham
    for n, no in sayfalar:
        if no in hedef:
            return None
        hedef[no] = f"#{n}"
    for no in sorted(set(olaylar) | set(parcalar)):
        if no in hedef:
            return None
        satir = _satir_birlestir(olaylar.get(no, {}), parcalar.get(no, []), no)
        if satir is None:
            return None
        hedef[no] = satir
    if set(hedef) != set(range(1, satir_sayisi + 1)):
        return None
    ic_cr = cr_satir - (1 if cr_son else 0)
    if ic_cr not in (0, max(satir_sayisi - 1, 0)):
        return None
    govde = "\n".join(
        hedef[i] + ("\r" if (ic_cr if i < satir_sayisi else cr_son) else "")
        for i in range(1, satir_sayisi + 1)
    )
    if son_lf and satir_sayisi:
        govde += "\n"
    return ((BOM if bom else "") + govde).encode("utf-8")


def birim_sozlugu(b: Birim) -> dict[str, object]:
    """`yeniden_kur` girdisi biciminde ham birim."""
    return {"text": b.metin, "marks": b.isaretler, "segmentler": b.segmentler}


def yeniden_kur_ayristirma(a: KitapAyristirma) -> bytes | None:
    return yeniden_kur(
        birimler=[birim_sozlugu(b) for b in a.birimler],
        sayfalar=[(s.n, s.satir) for s in a.sayfalar],
        yapi=a.yapi,
        satir_sayisi=a.satir_sayisi,
        bom=a.bom,
        cr_satir=a.cr_satir,
        cr_son=a.cr_son,
        son_lf=a.son_lf,
    )


# ---------------------------------------------------------------------------
# Sayimlar (kilit ve G-BUT)


def isaret_sayilari(metin: str) -> dict[str, int]:
    """Isaret karakterlerinin ham sayilari (satir basi virgul ayri: `,`)."""
    sayac = Counter(ch for ch in metin if ch in ISARETLER)
    sonuc = {ch: sayac.get(ch, 0) for ch in ISARET_SIRASI}
    sonuc[","] = sum(1 for s in metin.split("\n") if s.lstrip(" ").startswith(","))
    return sonuc


def karakter_sayilari(metin: str) -> dict[str, int]:
    """Denetlenen karakterlerin (S12 kumesi ve kontrol/bicim/bosluk/ozel kullanim) sayilari."""
    sayac = Counter(ord(ch) for ch in metin if denetlenen_karakter_mi(ch))
    return {kod_adi(kod): sayac[kod] for kod in sorted(sayac)}


def nfc_olmayan_satir(satirlar: list[str]) -> int:
    return sum(1 for s in satirlar if unicodedata.normalize("NFC", s) != s)
