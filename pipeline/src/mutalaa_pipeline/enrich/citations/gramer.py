# ruff: noqa: RUF001
"""Acik Turkce atif grameri (Iktibas tespiti §2; K-51 madde 4): saf islevler.

Bicimler: parantezli ad, virgul, numara `(Bakara Suresi, 255)`; `Ad: 7`; `Sure-i Ad, 255`;
`Ad 2/255`; yalniz numara `(2:255)` ve `[2/255]` (yalniz parantez icinde); sira sayisiyla
`Ad Suresinin 255. ayeti`; aralik ve liste `255-257`, `255, 257` (ayet basina satir, ortak
`grup`); Arapca `<ad>: <rakam>` (Arapca-Hint rakamlar dahil); adlandirilmis ayet (editor onayli
`adlandirilmis_ayetler.toml`).

* Sayisal bicimler HER ZAMAN etkindir. Ad tabanli bicimler yalniz onayli `surah_alias`
  satirlariyla (`AdSozlugu`) acilir; sozluk bos ya da yoksa ad tabanli bicim kapalidir ve sayaca
  `ad_tabanli_kapali` yazilir.
* Ad cakismasi (K-51 madde 4): once yuzey bicimi DAR anahtarla (kesme korunur) en uzun eslesme;
  GENIS anahtar yalniz tek sureye cikiyorsa kullanilir, birden cok sureye cikiyorsa satir
  uretilmez ve `ad_cakisan_birden_cok_sure` sayilir. Arapca ad `normalize_ar` anahtariyla.
* Riskli adlar (`alias.risky` ve `ingest/riskli_adlar.txt` anahtarlari) yalniz parantez,
  "Sure/suresi" ya da "ayet" kelimesi ipucuyla kabul edilir (`riskli_ipucsuz`).
* Dogrulama: sure 1-114, ayet 1..ayet sayisi (A04 dizisi); aralik disi atilir ve sayilir. Bir
  aralik bir uc bile disardaysa tamami atilir; 30'dan uzun aralik atilir (`aralik_cok_uzun`).
* Guven: parantezli ya da anahtar kelimeli guvenli ad 0,95; cipak `Ad: SAYI` 0,85; guclu ipuclu
  riskli ad 0,85; adlandirilmis ayet 0,90; yalniz sayisal parantez bicimi 0,90 (karar: ad yok
  ama parantez ve sure/ayet cifti birlikte; ad tabanli 0,95 ile cipak 0,85 arasinda).

Hicbir sayac ya da cikti metin tasimaz.
"""

import re
import tomllib
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.anchor import AnchorError, Q, parse
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.normalize import normalize_ar, normalize_tr

GUVEN_AD_GUVENLI: Final = 0.95
GUVEN_AD_CIPLAK: Final = 0.85
GUVEN_AD_RISKLI: Final = 0.85
GUVEN_ADLANDIRILMIS: Final = 0.90
GUVEN_SAYISAL: Final = 0.90
EN_UZUN_ARALIK: Final = 30
EN_COK_AD_KELIMESI: Final = 6

BICIM_SAYISAL: Final = "sayisal"
BICIM_AD: Final = "ad"
BICIM_SIRA: Final = "ad_sira"
BICIM_ADLANDIRILMIS: Final = "adlandirilmis"

ADLANDIRILMIS_YOLU: Final = Path(__file__).resolve().parent / "adlandirilmis_ayetler.toml"
RISKLI_ADLAR_YOLU: Final = (
    Path(__file__).resolve().parent.parent.parent / "ingest" / "riskli_adlar.txt"
)

_ARAPCA_RAKAMLAR: Final = "٠١٢٣٤٥٦٧٨٩"
_RAKAM_CEVIRI: Final = str.maketrans(_ARAPCA_RAKAMLAR, "0123456789")
_RAKAM: Final = "[0-9\u0660-\u0669]"
_SAYI: Final = rf"(?<!{_RAKAM}){_RAKAM}{{1,3}}(?!{_RAKAM})"  # en cok uc haneli, sinirli
_ARALIK: Final = rf"{_SAYI}(?:[ \t]*[-–][ \t]*{_SAYI})?"
_LISTE: Final = rf"{_ARALIK}(?:[ \t]*[,،][ \t]*{_ARALIK})*"
_AYET_KELIMESI: Final = r"[AaÂâ]yet\w*(?:-i[ \t]+k[eî]rime\w*)?"

_AYRAC_LISTE: Final = re.compile(
    rf"(?P<sep>[ \t]*[:,/،][ \t]*|[ \t]+)(?:(?P<sno>{_SAYI})[ \t]*[:/][ \t]*)?"
    rf"(?P<liste>{_LISTE})(?:\.?[ \t]*(?P<ak>{_AYET_KELIMESI}))?"
)
_SIRALI: Final = re.compile(rf"[ \t]+(?P<n>{_SAYI})\.[ \t]*(?P<ak>{_AYET_KELIMESI})")
_SAYISAL_PARANTEZ: Final = re.compile(
    rf"(?P<ac>[(\[])[ \t]*(?P<sure>{_SAYI})[ \t]*[:/][ \t]*(?P<liste>{_LISTE})[ \t]*(?P<kapa>[)\]])"
)
_ARALIK_AYIR: Final = re.compile(rf"({_SAYI})(?:[ \t]*[-–][ \t]*({_SAYI}))?")
_RAKAM_VAR: Final = re.compile(r"[0-9٠-٩]")
_SURE_EKLERI: Final = frozenset({"sure", "suresi", "suresinin", "suresinde", "suresindeki"})
_AD_ARASI: Final = frozenset(" \t-‐–")
_APOSTROFLAR: Final = frozenset("'’‘ʼ")
_ARAPCA_SURE: Final = "سوره"  # normalize_ar("sure" onegi): sin vav re he


@dataclass(frozen=True)
class Alias:
    """Bir onayli `surah_alias` satiri (yalniz motorun gerektirdigi alanlar)."""

    surah_no: int
    alias: str
    alias_key: str
    kind: str
    risky: bool = False


@dataclass(frozen=True)
class AdlandirilmisAyet:
    ad: str
    hedefler: tuple[tuple[int, int], ...]  # (sure, ayet)


@dataclass(frozen=True)
class Atif:
    bas: int  # atif ifadesinin kod noktasi baslangici (parantez dahil)
    son: int  # yari acik bitis
    sure: int
    ayet: int
    guven: float
    bicim: str
    grup: str | None  # ayni ifadenin birden cok ayet satiri varsa ortak anahtar

    @property
    def capa(self) -> str:
        return f"q:{self.sure}:{self.ayet}"


@dataclass
class Sonuc:
    atiflar: list[Atif] = field(default_factory=list)
    sayac: Counter[str] = field(default_factory=Counter)


# --- ad sozlugu --------------------------------------------------------------------------


def _harf(h: str) -> bool:
    return unicodedata.category(h)[0] in ("L", "M")


def _arapca_mi(h: str) -> bool:
    return "؀" <= h <= "ۿ" or "ݐ" <= h <= "ݿ" or "ﭐ" <= h <= "﷿"


def tokenler(metin: str) -> list[tuple[int, int]]:
    """Sozcuk dizileri `(bas, son)`; kesme sozcuk icinde kalir, tire ve bosluk ayirir."""
    sonuc: list[tuple[int, int]] = []
    i, n = 0, len(metin)
    while i < n:
        if not _harf(metin[i]):
            i += 1
            continue
        j = i + 1
        while j < n and (
            _harf(metin[j])
            or (
                metin[j] in _APOSTROFLAR
                and j + 1 < n
                and _harf(metin[j + 1])
                and _harf(metin[j - 1])
            )
        ):
            j += 1
        sonuc.append((i, j))
        i = j
    return sonuc


def riskli_anahtarlar(yol: Path | None = None) -> frozenset[str]:
    """`ingest/riskli_adlar.txt` adlarinin genis anahtarlari (A11 riskli ad listesi)."""
    ham = (yol or RISKLI_ADLAR_YOLU).read_text(encoding="utf-8")
    anahtarlar = (
        normalize_tr(satir.strip(), "genis")
        for satir in ham.splitlines()
        if satir.strip() != "" and not satir.startswith("#")
    )
    return frozenset(a for a in anahtarlar if a != "")


class AdSozlugu:
    """Onayli `surah_alias` satirlarindan derlenen ad dizinleri (dar, genis, Arapca)."""

    def __init__(self, aliaslar: Iterable[Alias], riskli: frozenset[str] = frozenset()) -> None:
        self.dar: dict[str, list[Alias]] = {}
        self.genis: dict[str, list[Alias]] = {}
        self.arapca: dict[str, list[Alias]] = {}
        self.riskli = riskli
        self.ilk_dar: set[str] = set()
        self.ilk_genis: set[str] = set()
        self.ilk_arapca: set[str] = set()
        en_cok = 1
        for a in aliaslar:
            if any(_arapca_mi(h) for h in a.alias):
                for anahtar in {normalize_ar(a.alias), a.alias_key}:
                    if anahtar:
                        self.arapca.setdefault(anahtar, []).append(a)
                        self.ilk_arapca.add(anahtar.split()[0])
                        en_cok = max(en_cok, len(anahtar.split()))
                continue
            dar = normalize_tr(a.alias, "dar")
            genis = a.alias_key
            if dar:
                self.dar.setdefault(dar, []).append(a)
                self.ilk_dar.add(dar.split()[0])
                en_cok = max(en_cok, len(dar.split()))
            if genis:
                self.genis.setdefault(genis, []).append(a)
                self.ilk_genis.add(genis.split()[0])
                en_cok = max(en_cok, len(genis.split()))
        self.en_cok = min(en_cok, EN_COK_AD_KELIMESI)

    @property
    def bos(self) -> bool:
        return not (self.dar or self.genis or self.arapca)


@dataclass(frozen=True)
class _AdEslesmesi:
    sonuncu_token: int  # son tokenin indeksi (dahil)
    sure: int
    riskli: bool
    sure_kelimesi: bool  # eslesen ad "sure" anahtar kelimesi tasiyor


_CAKISMA: Final = "cakisma"


def _ad_eslesmesi(
    metin: str, tok: Sequence[tuple[int, int]], i: int, s: AdSozlugu, sayac: Counter[str]
) -> _AdEslesmesi | str | None:
    """`i`. tokenle baslayan en uzun ad (dar anahtar once, sonra tek sureye cikan genis anahtar)."""
    bitis = i
    while bitis + 1 < len(tok) and bitis - i + 1 < s.en_cok:
        if not set(metin[tok[bitis][1] : tok[bitis + 1][0]]) <= _AD_ARASI:
            break
        bitis += 1
    arapca = _arapca_mi(metin[tok[i][0]])
    gecisler = ("arapca",) if arapca else ("dar", "genis")
    for gecis in gecisler:
        for son in range(bitis, i - 1, -1):
            yuzey = metin[tok[i][0] : tok[son][1]]
            if gecis == "arapca":
                anahtar, tablo = normalize_ar(yuzey), s.arapca
            elif gecis == "dar":
                anahtar, tablo = normalize_tr(yuzey, "dar"), s.dar
            else:
                anahtar, tablo = normalize_tr(yuzey, "genis"), s.genis
            adaylar = tablo.get(anahtar) if anahtar else None
            if not adaylar:
                continue
            sureler = {a.surah_no for a in adaylar}
            if len(sureler) > 1:
                sayac["ad_cakisan_birden_cok_sure"] += 1
                return _CAKISMA
            if gecis == "genis":
                sayac["ad_genis_anahtarla"] += 1
            genis = anahtar if gecis == "genis" else normalize_tr(yuzey, "genis")
            riskli = any(a.risky for a in adaylar) or genis in s.riskli
            sure_kelimesi = any(t.startswith(("sure", "suretu")) for t in genis.split()) or (
                arapca and anahtar.startswith(_ARAPCA_SURE)
            )
            return _AdEslesmesi(son, next(iter(sureler)), riskli, sure_kelimesi)
    return None


# --- dogrulama ------------------------------------------------------------------------------


def _say(deger: str) -> int:
    return int(deger.translate(_RAKAM_CEVIRI))


def _ayetleri_coz(
    sure: int, liste: str, sayac: Counter[str], ayet_sayilari: Sequence[int]
) -> list[int] | None:
    """Liste metnini dogrulanmis ayet numaralarina cevirir; sure disi ise None."""
    if not 1 <= sure <= len(ayet_sayilari):
        sayac["sure_disi"] += 1
        return None
    sayi = ayet_sayilari[sure - 1]
    sonuc: list[int] = []
    for m in _ARALIK_AYIR.finditer(liste):
        a = _say(m.group(1))
        if m.group(2) is None or _say(m.group(2)) == a:
            if 1 <= a <= sayi:
                sonuc.append(a)
            else:
                sayac["ayet_disi"] += 1
            continue
        b = _say(m.group(2))
        if not 1 <= a < b <= sayi:
            sayac["aralik_disi"] += 1
        elif b - a + 1 > EN_UZUN_ARALIK:
            sayac["aralik_cok_uzun"] += 1
        else:
            sonuc.extend(range(a, b + 1))
    return list(dict.fromkeys(sonuc))


def _satirlar(
    bas: int, son: int, sure: int, ayetler: Sequence[int], guven: float, bicim: str
) -> list[Atif]:
    grup = f"{bas}-{son}" if len(ayetler) > 1 else None
    return [Atif(bas, son, sure, a, guven, bicim, grup) for a in ayetler]


def _cakisir(bas: int, son: int, kullanilan: Sequence[tuple[int, int]]) -> bool:
    return any(k0 < son and bas < k1 for k0, k1 in kullanilan)


# --- ad tabanli bicimler ---------------------------------------------------------------------


def _ad_tabanli(
    metin: str,
    s: AdSozlugu,
    sayac: Counter[str],
    ayet_sayilari: Sequence[int],
    kullanilan: list[tuple[int, int]],
) -> list[Atif]:
    sonuc: list[Atif] = []
    if _RAKAM_VAR.search(metin) is None:
        return sonuc
    tok = tokenler(metin)
    i = 0
    while i < len(tok):
        ilk = metin[tok[i][0] : tok[i][1]]
        if _arapca_mi(ilk[0]):
            ilk_anahtar = normalize_ar(ilk).split()[:1]
            uygun = bool(ilk_anahtar) and ilk_anahtar[0] in s.ilk_arapca
        else:
            uygun = any(
                a and (a in s.ilk_dar or a in s.ilk_genis)
                for a in (normalize_tr(ilk, "dar"), normalize_tr(ilk, "genis"))
            )
        if not uygun:
            i += 1
            continue
        e = _ad_eslesmesi(metin, tok, i, s, sayac)
        if not isinstance(e, _AdEslesmesi):
            i += 1
            continue
        atiflar, sonraki = _ad_sonrasi(metin, tok, i, e, s, sayac, ayet_sayilari)
        if atiflar and not _cakisir(atiflar[0].bas, atiflar[0].son, kullanilan):
            sonuc.extend(atiflar)
            kullanilan.append((atiflar[0].bas, atiflar[0].son))
            i = max(sonraki, i + 1)
        else:
            i += 1
    return sonuc


def _onceki_anahtar_kelime(metin: str, tok: Sequence[tuple[int, int]], i: int) -> int | None:
    """`Sure-i X` / `Suretu'l-X` oneki varsa onekin baslangic kod noktasi."""
    if i >= 2:
        a = metin[tok[i - 2][0] : tok[i - 2][1]]
        b = metin[tok[i - 1][0] : tok[i - 1][1]]
        ara = metin[tok[i - 2][1] : tok[i - 1][0]] + metin[tok[i - 1][1] : tok[i][0]]
        if (
            normalize_tr(a, "genis") == "sure"
            and normalize_tr(b, "genis") == "i"
            and set(ara) <= _AD_ARASI
        ):
            return tok[i - 2][0]
    if i >= 1 and set(metin[tok[i - 1][1] : tok[i][0]]) <= _AD_ARASI:
        onceki = normalize_tr(metin[tok[i - 1][0] : tok[i - 1][1]], "genis")
        if onceki.startswith("suretu"):
            return tok[i - 1][0]
    return None


def _ad_sonrasi(
    metin: str,
    tok: Sequence[tuple[int, int]],
    i: int,
    e: _AdEslesmesi,
    s: AdSozlugu,
    sayac: Counter[str],
    ayet_sayilari: Sequence[int],
) -> tuple[list[Atif], int]:
    """Ad eslesmesinden sonra sayiyi ayristirir; `(atiflar, sonraki token)`."""
    bas = tok[i][0]
    onek = _onceki_anahtar_kelime(metin, tok, i)
    anahtar_kelime = e.sure_kelimesi or onek is not None
    if onek is not None:
        bas = onek
    son_tok = e.sonuncu_token
    pos = tok[son_tok][1]
    if son_tok + 1 < len(tok) and set(metin[pos : tok[son_tok + 1][0]]) <= _AD_ARASI:
        ek = normalize_tr(metin[tok[son_tok + 1][0] : tok[son_tok + 1][1]], "genis").split("'")[0]
        if ek in _SURE_EKLERI:
            son_tok += 1
            pos = tok[son_tok][1]
            anahtar_kelime = True
    parantez_acik = False
    bas_parantez = bas
    onceki = bas - 1
    while onceki >= 0 and metin[onceki] in " \t":
        onceki -= 1
    if onceki >= 0 and metin[onceki] in "([":
        parantez_acik, bas_parantez = True, onceki
    sira = _SIRALI.match(metin, pos)
    if sira is not None:
        liste, ak, bitis = sira.group("n"), True, sira.end()
    else:
        m = _AYRAC_LISTE.match(metin, pos)
        if m is None:
            return [], son_tok + 1
        liste, ak, bitis = m.group("liste"), m.group("ak") is not None, m.end()
        sno = m.group("sno")
        if sno is not None and _say(sno) != e.sure:
            sayac["ad_no_uyumsuz"] += 1
            return [], son_tok + 1
    kapanis = bitis
    while kapanis < len(metin) and metin[kapanis] in " \t":
        kapanis += 1
    parantez = parantez_acik and kapanis < len(metin) and metin[kapanis] in ")]"
    if parantez:
        bas, bitis = bas_parantez, kapanis + 1
    anahtar_kelime = anahtar_kelime or ak
    if e.riskli and not (parantez or anahtar_kelime):
        sayac["riskli_ipucsuz"] += 1
        return [], son_tok + 1
    if e.riskli:
        guven = GUVEN_AD_RISKLI
    elif parantez or anahtar_kelime:
        guven = GUVEN_AD_GUVENLI
    else:
        guven = GUVEN_AD_CIPLAK
    ayetler = _ayetleri_coz(e.sure, liste, sayac, ayet_sayilari)
    sonraki = next((k for k, (b, _) in enumerate(tok) if b >= bitis), len(tok))
    if not ayetler:
        return [], sonraki
    bicim = BICIM_SIRA if sira is not None else BICIM_AD
    sayac["atif_" + bicim] += 1
    return _satirlar(bas, bitis, e.sure, ayetler, guven, bicim), sonraki


# --- sayisal ve adlandirilmis bicimler ---------------------------------------------------------


def _sayisal(
    metin: str,
    sayac: Counter[str],
    ayet_sayilari: Sequence[int],
    kullanilan: list[tuple[int, int]],
) -> list[Atif]:
    sonuc: list[Atif] = []
    for m in _SAYISAL_PARANTEZ.finditer(metin):
        if (m.group("ac"), m.group("kapa")) not in (("(", ")"), ("[", "]")):
            continue
        if _cakisir(m.start(), m.end(), kullanilan):
            continue
        sure = _say(m.group("sure"))
        ayetler = _ayetleri_coz(sure, m.group("liste"), sayac, ayet_sayilari)
        if not ayetler:
            continue
        sayac["atif_" + BICIM_SAYISAL] += 1
        sonuc.extend(_satirlar(m.start(), m.end(), sure, ayetler, GUVEN_SAYISAL, BICIM_SAYISAL))
    return sonuc


def adlandirilmis_oku(yol: Path | None = None) -> list[AdlandirilmisAyet]:
    """Editor onayli adlandirilmis ayet listesi (TOML); hedefler `q:s:a` capalaridir."""
    veri = tomllib.loads((yol or ADLANDIRILMIS_YOLU).read_text(encoding="utf-8"))
    ham = veri.get("ayet", [])
    if not isinstance(ham, list):
        raise ValueError("adlandirilmis ayet listesi: `ayet` dizi olmali")
    sonuc: list[AdlandirilmisAyet] = []
    for girdi in ham:
        ad, hedefler = girdi.get("ad"), girdi.get("hedefler")
        if not isinstance(ad, str) or not ad or not isinstance(hedefler, list) or not hedefler:
            raise ValueError("adlandirilmis ayet: `ad` ve `hedefler` zorunlu")
        cozulen: list[tuple[int, int]] = []
        for capa in hedefler:
            try:
                r = parse(str(capa)).anchor
            except AnchorError:
                raise ValueError("adlandirilmis ayet: hedef capa gecersiz") from None
            if not isinstance(r, Q) or r.ilk is not None:
                raise ValueError("adlandirilmis ayet: hedef `q:s:a` olmali")
            cozulen.append((r.sure, r.ayet))
        sonuc.append(AdlandirilmisAyet(ad, tuple(cozulen)))
    return sonuc


def _adlandirilmis(
    metin: str,
    liste: Sequence[AdlandirilmisAyet],
    sayac: Counter[str],
    ayet_sayilari: Sequence[int],
    kullanilan: list[tuple[int, int]],
) -> list[Atif]:
    sonuc: list[Atif] = []
    if not liste:
        return sonuc
    tok = tokenler(metin)
    for giris in liste:
        anahtar = normalize_tr(giris.ad, "genis")
        n = len(anahtar.split())
        for i in range(len(tok) - n + 1):
            bas, bit = tok[i][0], tok[i + n - 1][1]
            if normalize_tr(metin[bas:bit], "genis") != anahtar or _cakisir(bas, bit, kullanilan):
                continue
            gecerli = [
                (sr, ay)
                for sr, ay in giris.hedefler
                if 1 <= sr <= len(ayet_sayilari) and 1 <= ay <= ayet_sayilari[sr - 1]
            ]
            if len(gecerli) != len(giris.hedefler):
                sayac["ayet_disi"] += 1
                continue
            kullanilan.append((bas, bit))
            sayac["atif_" + BICIM_ADLANDIRILMIS] += 1
            grup = f"{bas}-{bit}" if len(gecerli) > 1 else None
            sonuc.extend(
                Atif(bas, bit, sr, ay, GUVEN_ADLANDIRILMIS, BICIM_ADLANDIRILMIS, grup)
                for sr, ay in gecerli
            )
    return sonuc


def atiflari_bul(
    metin: str,
    *,
    sozluk: AdSozlugu | None = None,
    adlandirilmis: Sequence[AdlandirilmisAyet] = (),
    ayet_sayilari: Sequence[int] = AYET_SAYILARI,
) -> Sonuc:
    """Metindeki acik atiflar (metin sirasinda) ve sayaclar."""
    sonuc = Sonuc()
    kullanilan: list[tuple[int, int]] = []
    atiflar: list[Atif] = []
    if sozluk is None or sozluk.bos:
        sonuc.sayac["ad_tabanli_kapali"] += 1
    else:
        atiflar.extend(_ad_tabanli(metin, sozluk, sonuc.sayac, ayet_sayilari, kullanilan))
    atiflar.extend(_adlandirilmis(metin, adlandirilmis, sonuc.sayac, ayet_sayilari, kullanilan))
    atiflar.extend(_sayisal(metin, sonuc.sayac, ayet_sayilari, kullanilan))
    atiflar.sort(key=lambda a: (a.bas, a.son, a.sure, a.ayet))
    sonuc.atiflar = atiflar
    return sonuc
