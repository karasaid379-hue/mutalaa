"""Diyanet <-> RNK kelime dizisi karsilastirmasi (A20.1, K-52 madde 2). Rapor METIN ICERMEZ.

Diyanet deposu (`risale-asil-nusha`) karsilastirma verisidir; birim olarak yuklenmez. Bu modul
Diyanet'in `diyanet_karsiligi == "diyanet"` olan kitaplarinda staged Diyanet birimleri ile staged
RNK birimlerinin kelime dizisini kitap basina karsilastirir. Cikti yalniz sayi, oran, capa ve
dosya sirasi tasir; sozcuk ya da baslik metni yazmaz.

Kelime anahtari (`kelime_anahtarlari`): Cf karakterleri (U+00AD, U+200C, U+200D, U+200F, U+06DD
...) atilir; metin bosluk, noktalama ve tire ile kelimelere bolunur; kesme isaretleri silinir;
kucuk harf ACIK eslemeyle yapilir (`I -> noktasiz i`, `noktali I -> i`; `str.lower()` yok); NFKD,
birlesen isaretler atilir (sapka ve Arapca hareke dahil); `noktasiz i -> i`. Bu GEVSEK anahtar
hizalamada kullanilir. SIKI anahtar (kucuk harf ve NFC, kesme isareti tek bicime) eslesen
kelimelerde ayrica karsilastirilir: gevsek anahtarda esit, siki anahtarda farkli kelime bir
"yazim farki"dir (sapka, noktasiz i, kesme isareti vb.) ve yalniz sayilir.

Hizalama (`hizala`): iki kelime dizisi (tam sayi dizisi) uzerinde ortak onek ve sonek atilir;
kalan bolge kucukse (`DP_SINIRI`) `difflib.SequenceMatcher` ile en uzun ortak bloklara bolunur;
buyukse iki dizide de TEK gecen k-kelimelik dizilerden (k = 8, 4) en uzun artan altdizi (LIS)
secilip bolgeler bolunur ve her parca yinelenir. Bellek ve sure kitap boyuyla dogrusal, parca
basina sinirlidir. Eslesen kelime sayisi gercek LCS'nin ALT sinirina esittir (blok tabanli
hizalama); tam LCS olmak zorunda degildir. Hicbir yontemle hizalanamayan buyuk bolge `hizalanamayan`
olarak ayrica sayilir ve eslesmemis sayilir.

Akislar: ana (baslik ve paragraf) ile dipnot (Diyanet `rol = dipnot`, RNK `kind = hasiye`) ayri
hizalanir; dipnot Diyanet'te dosya sonunda, RNK'da satir icinde durdugundan siralari farklidir.
"""

import bisect
import difflib
import json
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.anchor import risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize import lower_turkish

RAPOR_SURUMU: Final = 1
DP_SINIRI: Final = 4_000_000
K_LISTESI: Final = (8, 4)
EN_BUYUK_FARK_SAYISI: Final = 10
ORTUSME_K: Final = 6
FARK_KOVALARI: Final = ((1, 1, "1"), (2, 3, "2-3"), (4, 9, "4-9"), (10, 49, "10-49"))
FARK_KOVASI_SON: Final = "50+"
DIYANET_KLASORU: Final = "txt"
REFERANS_KITAP: Final = "sozler"
REFERANS_DOSYALAR: Final = (2, 3, 4)  # Ikinci, Ucuncu ve Dorduncu Soz (dosya sirasi)

_KESME: Final = "".join(chr(c) for c in (0x27, 0x2019, 0x2018, 0x2BC, 0x2BE, 0x2BF, 0xB4, 0x60))
_NOKTASIZ_I: Final = chr(0x131)


def _sinif(*araliklar: tuple[int, int]) -> str:
    return "".join(f"{re.escape(chr(a))}-{re.escape(chr(b))}" for a, b in araliklar)


# Atilan Cf karakterleri: yumusak tire, Arapca sayi isaretleri, ZWNJ/ZWJ/yon isaretleri, BOM ...
_CF_ATILAN: Final = re.compile(
    "["
    + _sinif(
        (0xAD, 0xAD),
        (0x600, 0x605),
        (0x61C, 0x61C),
        (0x6DD, 0x6DD),
        (0x70F, 0x70F),
        (0x180E, 0x180E),
        (0x200B, 0x200F),
        (0x202A, 0x202E),
        (0x2060, 0x2064),
        (0x2066, 0x206F),
        (0xFEFF, 0xFEFF),
    )
    + "]"
)
# Kelime karakterleri: \w + birlesen isaretler (Mn: sapka, Arapca hareke) + kesme isaretleri.
_KELIME: Final = re.compile(
    r"[\w"
    + _sinif(
        (0x300, 0x36F),
        (0x483, 0x489),
        (0x610, 0x61A),
        (0x64B, 0x65F),
        (0x670, 0x670),
        (0x6D6, 0x6DC),
        (0x6DF, 0x6E4),
        (0x6E7, 0x6E8),
        (0x6EA, 0x6ED),
        (0x8D3, 0x8FF),
    )
    + re.escape(_KESME)
    + "]+"
)
_ALT_CIZGI: Final = "_"


# ---------------------------------------------------------------------------
# Kelime anahtari


def _anahtarlar(ham: str) -> tuple[str, str] | None:
    kucuk = lower_turkish(ham.replace(_ALT_CIZGI, ""))
    siki = unicodedata.normalize("NFC", kucuk)
    for k in _KESME:
        siki = siki.replace(k, "'")
    siki = siki.strip("'")
    ayrik = unicodedata.normalize("NFKD", kucuk)
    govde = "".join(
        c for c in ayrik if c not in _KESME and not unicodedata.category(c).startswith("M")
    )
    gevsek = govde.replace(_NOKTASIZ_I, "i")
    if gevsek == "":
        return None
    return gevsek, siki


def kelime_anahtarlari(
    metin: str, onbellek: dict[str, tuple[str, str] | None] | None = None
) -> list[tuple[str, str]]:
    """`(gevsek, siki)` anahtar cifti listesi; bos anahtar uretenler atilir."""
    onbellek = {} if onbellek is None else onbellek
    sonuc: list[tuple[str, str]] = []
    for ham in _KELIME.findall(_CF_ATILAN.sub("", metin)):
        if ham not in onbellek:
            onbellek[ham] = _anahtarlar(ham)
        cift = onbellek[ham]
        if cift is not None:
            sonuc.append(cift)
    return sonuc


# ---------------------------------------------------------------------------
# Hizalama

Blok = tuple[int, int, int]  # (a konumu, b konumu, uzunluk)


@dataclass
class Hizalama:
    bloklar: list[Blok]
    hizalanamayan_a: int = 0
    hizalanamayan_b: int = 0
    hizalanamayan_bolge: int = 0


def _lis(ciftler: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """`ciftler` i'ye gore sirali; j icin en uzun kesin artan altdizi."""
    kuyruk: list[int] = []  # her uzunluk icin en kucuk j
    kuyruk_idx: list[int] = []
    onceki: list[int] = [-1] * len(ciftler)
    for n, (_, j) in enumerate(ciftler):
        p = bisect.bisect_left(kuyruk, j)
        if p == len(kuyruk):
            kuyruk.append(j)
            kuyruk_idx.append(n)
        else:
            kuyruk[p] = j
            kuyruk_idx[p] = n
        onceki[n] = kuyruk_idx[p - 1] if p > 0 else -1
    sonuc: list[tuple[int, int]] = []
    n = kuyruk_idx[-1] if kuyruk_idx else -1
    while n >= 0:
        sonuc.append(ciftler[n])
        n = onceki[n]
    sonuc.reverse()
    return sonuc


def _benzersiz(seq: Sequence[int], lo: int, hi: int, k: int) -> dict[tuple[int, ...], int]:
    gorulen: dict[tuple[int, ...], int] = {}
    for i in range(lo, hi - k + 1):
        g = tuple(seq[i : i + k])
        gorulen[g] = -1 if g in gorulen else i
    return {g: i for g, i in gorulen.items() if i >= 0}


def _capalar(
    a: Sequence[int], alo: int, ahi: int, b: Sequence[int], blo: int, bhi: int, k: int
) -> list[Blok]:
    """Iki bolgede de tek gecen k-kelimelik dizilerden artan, cakismayan bloklar."""
    if ahi - alo < k or bhi - blo < k:
        return []
    pa = _benzersiz(a, alo, ahi, k)
    pb = _benzersiz(b, blo, bhi, k)
    ciftler = sorted((i, pb[g]) for g, i in pa.items() if g in pb)
    secilen = _lis(ciftler)
    bloklar: list[Blok] = []
    for i, j in secilen:
        if bloklar:
            pi, pj, pn = bloklar[-1]
            if i - j == pi - pj and i <= pi + pn:  # ayni kosegen: birlestir
                bloklar[-1] = (pi, pj, i + k - pi)
                continue
            if i < pi + pn or j < pj + pn:
                continue
        bloklar.append((i, j, k))
    return bloklar


def hizala(a: Sequence[int], b: Sequence[int]) -> Hizalama:
    """Iki tam sayi dizisini bloklara hizalar; bloklar iki dizide de artan ve cakismaz."""
    sonuc = Hizalama(bloklar=[])
    bloklar = sonuc.bloklar
    yigin: list[tuple[int, int, int, int, int]] = [(0, len(a), 0, len(b), 0)]
    while yigin:
        alo, ahi, blo, bhi, ki = yigin.pop()
        bas = 0
        while alo + bas < ahi and blo + bas < bhi and a[alo + bas] == b[blo + bas]:
            bas += 1
        if bas:
            bloklar.append((alo, blo, bas))
            alo += bas
            blo += bas
        son = 0
        while ahi - son > alo and bhi - son > blo and a[ahi - son - 1] == b[bhi - son - 1]:
            son += 1
        if son:
            bloklar.append((ahi - son, bhi - son, son))
            ahi -= son
            bhi -= son
        if alo >= ahi or blo >= bhi:
            continue
        if (ahi - alo) * (bhi - blo) <= DP_SINIRI:
            esleyici = difflib.SequenceMatcher(None, a[alo:ahi], b[blo:bhi], autojunk=False)
            for i, j, n in esleyici.get_matching_blocks():
                if n:
                    bloklar.append((alo + i, blo + j, n))
            continue
        bulundu = False
        for kk in range(ki, len(K_LISTESI)):
            capalar = _capalar(a, alo, ahi, b, blo, bhi, K_LISTESI[kk])
            if not capalar:
                continue
            bulundu = True
            oa, ob = alo, blo
            for i, j, n in capalar:
                bloklar.append((i, j, n))
                yigin.append((oa, i, ob, j, kk))
                oa, ob = i + n, j + n
            yigin.append((oa, ahi, ob, bhi, kk))
            break
        if not bulundu:
            sonuc.hizalanamayan_a += ahi - alo
            sonuc.hizalanamayan_b += bhi - blo
            sonuc.hizalanamayan_bolge += 1
    bloklar.sort()
    birlesik: list[Blok] = []
    for i, j, n in bloklar:
        if birlesik:
            pi, pj, pn = birlesik[-1]
            if pi + pn == i and pj + pn == j:
                birlesik[-1] = (pi, pj, pn + n)
                continue
        birlesik.append((i, j, n))
    sonuc.bloklar = birlesik
    return sonuc


# ---------------------------------------------------------------------------
# Akis karsilastirmasi


@dataclass(frozen=True)
class Birim:
    """Bir kaynak biriminin karsilastirma girdisi (siralanmis akista)."""

    capa: str
    metin: str
    dosya: int = 0  # Diyanet dosya sirasi (1 tabanli); RNK icin 0


@dataclass(frozen=True)
class Fark:
    tur: str  # "yalniz-diyanet" | "yalniz-rnk" | "farkli"
    diyanet_kelime: int
    rnk_kelime: int
    diyanet_capa: str | None
    rnk_capa: str | None


@dataclass
class AkisSonucu:
    diyanet_kelime: int = 0
    rnk_kelime: int = 0
    eslesen: int = 0
    yazim_farki: int = 0
    farklar: list[Fark] = field(default_factory=list)
    dosyalar: dict[int, list[int]] = field(default_factory=dict)  # dosya -> [kelime, eslesen]
    hizalanamayan_a: int = 0
    hizalanamayan_b: int = 0
    hizalanamayan_bolge: int = 0


def _akis_anahtari(
    birimler: Sequence[Birim], onbellek: dict[str, tuple[str, str] | None]
) -> tuple[list[str], list[str], list[int]]:
    gevsek: list[str] = []
    siki: list[str] = []
    baslangic: list[int] = []
    for b in birimler:
        baslangic.append(len(gevsek))
        for g, s in kelime_anahtarlari(b.metin, onbellek):
            gevsek.append(g)
            siki.append(s)
    baslangic.append(len(gevsek))
    return gevsek, siki, baslangic


def _capa_konumu(birimler: Sequence[Birim], baslangic: Sequence[int], konum: int) -> str | None:
    if not birimler:
        return None
    i = bisect.bisect_right(baslangic, konum) - 1
    return birimler[min(max(i, 0), len(birimler) - 1)].capa


def akis_karsilastir(
    diyanet: Sequence[Birim],
    rnk: Sequence[Birim],
    onbellek: dict[str, tuple[str, str] | None] | None = None,
) -> AkisSonucu:
    """Iki siralanmis birim akisinin kelime dizilerini hizalar; yalniz sayi ve capa dondurur."""
    onbellek = {} if onbellek is None else onbellek
    ga, sa, ba = _akis_anahtari(diyanet, onbellek)
    gb, sb, bb = _akis_anahtari(rnk, onbellek)
    kimlik: dict[str, int] = {}
    ia = [kimlik.setdefault(x, len(kimlik)) for x in ga]
    ib = [kimlik.setdefault(x, len(kimlik)) for x in gb]
    h = hizala(ia, ib)
    sonuc = AkisSonucu(
        diyanet_kelime=len(ia),
        rnk_kelime=len(ib),
        hizalanamayan_a=h.hizalanamayan_a,
        hizalanamayan_b=h.hizalanamayan_b,
        hizalanamayan_bolge=h.hizalanamayan_bolge,
    )
    esleme = bytearray(len(ia))
    pa = pb = 0
    for i, j, n in h.bloklar:
        sonuc.eslesen += n
        esleme[i : i + n] = b"\x01" * n
        sonuc.yazim_farki += sum(
            1 for x, y in zip(sa[i : i + n], sb[j : j + n], strict=True) if x != y
        )
        _fark_ekle(sonuc, diyanet, rnk, ba, bb, pa, i, pb, j)
        pa, pb = i + n, j + n
    _fark_ekle(sonuc, diyanet, rnk, ba, bb, pa, len(ia), pb, len(ib))
    for k, birim in enumerate(diyanet):
        kayit = sonuc.dosyalar.setdefault(birim.dosya, [0, 0])
        kayit[0] += ba[k + 1] - ba[k]
        kayit[1] += sum(esleme[ba[k] : ba[k + 1]])
    return sonuc


def _fark_ekle(
    sonuc: AkisSonucu,
    diyanet: Sequence[Birim],
    rnk: Sequence[Birim],
    ba: Sequence[int],
    bb: Sequence[int],
    a0: int,
    a1: int,
    b0: int,
    b1: int,
) -> None:
    da, db = a1 - a0, b1 - b0
    if da == 0 and db == 0:
        return
    tur = "yalniz-rnk" if da == 0 else "yalniz-diyanet" if db == 0 else "farkli"
    sonuc.farklar.append(
        Fark(
            tur,
            da,
            db,
            _capa_konumu(diyanet, ba, a0) if da else None,
            _capa_konumu(rnk, bb, b0) if db else None,
        )
    )


# ---------------------------------------------------------------------------
# Rapor ozeti


@dataclass
class Ortusme:
    """Sirasiz `ORTUSME_K`-kelimelik dizi ortusmesi (ana ve dipnot akislari birlikte)."""

    diyanet_kelime: int = 0
    diyanet_kapsanan: int = 0
    rnk_kelime: int = 0
    rnk_kapsanan: int = 0
    dosyalar: dict[int, list[int]] = field(default_factory=dict)  # dosya -> [kelime, kapsanan]


def _kapsanan(kaynak: Sequence[int], hedef: Sequence[int], k: int) -> bytearray:
    """`kaynak` kelimelerinden `hedef`te de gecen bir `k`-dizinin icinde kalanlar (1)."""
    isaret = bytearray(len(kaynak))
    if len(kaynak) < k or len(hedef) < k:
        return isaret
    pencereler = {tuple(hedef[i : i + k]) for i in range(len(hedef) - k + 1)}
    for i in range(len(kaynak) - k + 1):
        if tuple(kaynak[i : i + k]) in pencereler:
            isaret[i : i + k] = b"\x01" * k
    return isaret


def ortusme_hesapla(
    diyanet: Sequence[Sequence[Birim]],
    rnk: Sequence[Sequence[Birim]],
    onbellek: dict[str, tuple[str, str] | None] | None = None,
    k: int = ORTUSME_K,
) -> Ortusme:
    """Diyanet ve RNK akislarini birlestirip (sirasiz) `k`-kelimelik dizi ortusmesini sayar.

    Dipnotun bir kaynakta ana metinde, oteki dipnotta durdugu yerleri de kapsar; siraya
    duyarli hizalamanin (`akis_karsilastir`) tamamlayicisidir.
    """
    onbellek = {} if onbellek is None else onbellek
    kimlik: dict[str, int] = {}
    da: list[int] = []
    dosya_of: list[int] = []
    for akis in diyanet:
        for b in akis:
            ids = [
                kimlik.setdefault(g, len(kimlik)) for g, _ in kelime_anahtarlari(b.metin, onbellek)
            ]
            da.extend(ids)
            dosya_of.extend([b.dosya] * len(ids))
    ra = [
        kimlik.setdefault(g, len(kimlik))
        for akis in rnk
        for b in akis
        for g, _ in kelime_anahtarlari(b.metin, onbellek)
    ]
    d_isaret = _kapsanan(da, ra, k)
    r_isaret = _kapsanan(ra, da, k)
    sonuc = Ortusme(len(da), sum(d_isaret), len(ra), sum(r_isaret))
    for dosya, isaret in zip(dosya_of, d_isaret, strict=True):
        kayit = sonuc.dosyalar.setdefault(dosya, [0, 0])
        kayit[0] += 1
        kayit[1] += isaret
    return sonuc


def fark_kovasi(uzunluk: int) -> str:
    for en_az, en_cok, ad in FARK_KOVALARI:
        if en_az <= uzunluk <= en_cok:
            return ad
    return FARK_KOVASI_SON


def _oran(pay: int, payda: int) -> float | None:
    return None if payda == 0 else round(pay / payda, 6)


def akis_ozeti(s: AkisSonucu) -> dict[str, object]:
    kova: Counter[str] = Counter()
    tur: Counter[str] = Counter()
    for f in s.farklar:
        kova[fark_kovasi(max(f.diyanet_kelime, f.rnk_kelime))] += 1
        tur[f.tur] += 1
    sirali = sorted(
        s.farklar, key=lambda f: (-max(f.diyanet_kelime, f.rnk_kelime), f.diyanet_capa or "")
    )
    kovalar = [ad for _, _, ad in FARK_KOVALARI] + [FARK_KOVASI_SON]
    return {
        "diyanet_kelime": s.diyanet_kelime,
        "rnk_kelime": s.rnk_kelime,
        "eslesen_kelime": s.eslesen,
        "eslesen_oran_diyanet": _oran(s.eslesen, s.diyanet_kelime),
        "eslesen_oran_rnk": _oran(s.eslesen, s.rnk_kelime),
        "diyanet_da_olup_rnkda_olmayan": s.diyanet_kelime - s.eslesen,
        "rnkda_olup_diyanette_olmayan": s.rnk_kelime - s.eslesen,
        "yazim_farki_kelime": s.yazim_farki,
        "fark_sayisi": len(s.farklar),
        "fark_turleri": {t: tur.get(t, 0) for t in ("yalniz-diyanet", "yalniz-rnk", "farkli")},
        "fark_uzunluk_dagilimi": {k: kova.get(k, 0) for k in kovalar},
        "en_buyuk_farklar": [
            {
                "tur": f.tur,
                "diyanet_kelime": f.diyanet_kelime,
                "rnk_kelime": f.rnk_kelime,
                "diyanet_capa": f.diyanet_capa,
                "rnk_capa": f.rnk_capa,
            }
            for f in sirali[:EN_BUYUK_FARK_SAYISI]
        ],
        "hizalanamayan": {
            "bolge": s.hizalanamayan_bolge,
            "diyanet_kelime": s.hizalanamayan_a,
            "rnk_kelime": s.hizalanamayan_b,
        },
    }


def _toplam(parcalar: Iterable[AkisSonucu]) -> AkisSonucu:
    t = AkisSonucu()
    for p in parcalar:
        t.diyanet_kelime += p.diyanet_kelime
        t.rnk_kelime += p.rnk_kelime
        t.eslesen += p.eslesen
        t.yazim_farki += p.yazim_farki
        t.farklar.extend(p.farklar)
        t.hizalanamayan_a += p.hizalanamayan_a
        t.hizalanamayan_b += p.hizalanamayan_b
        t.hizalanamayan_bolge += p.hizalanamayan_bolge
        for d, (n, e) in p.dosyalar.items():
            kayit = t.dosyalar.setdefault(d, [0, 0])
            kayit[0] += n
            kayit[1] += e
    return t


def _dosya_satiri(n: int, e: int) -> dict[str, object]:
    return {"diyanet_kelime": n, "eslesen_kelime": e, "eslesen_oran": _oran(e, n)}


def kitap_ozeti(
    ana: AkisSonucu,
    dipnot: AkisSonucu,
    ortusme: Ortusme,
    bolum_adlari: Mapping[int, str] | None = None,
) -> dict[str, object]:
    """Bir kitabin ana, dipnot, toplam ve sirasiz ortusme ozeti; Diyanet dosyasi basina oranlar."""
    toplam = _toplam((ana, dipnot))
    dosyalar: list[dict[str, object]] = []
    for d in sorted(toplam.dosyalar):
        n, e = toplam.dosyalar[d]
        an, ae = ana.dosyalar.get(d, [0, 0])
        dn, de = dipnot.dosyalar.get(d, [0, 0])
        on, oe = ortusme.dosyalar.get(d, [0, 0])
        dosyalar.append(
            {
                "dosya_sira": d,
                "bolum": (bolum_adlari or {}).get(d),
                "ana_metin": _dosya_satiri(an, ae),
                "dipnot": _dosya_satiri(dn, de),
                "toplam": _dosya_satiri(n, e),
                "ortusme": {"diyanet_kelime": on, "kapsanan": oe, "oran": _oran(oe, on)},
            }
        )
    return {
        **akis_ozeti(toplam),
        "ana_metin": akis_ozeti(ana),
        "dipnot": akis_ozeti(dipnot),
        "ortusme": {
            "k": ORTUSME_K,
            "diyanet_kelime": ortusme.diyanet_kelime,
            "diyanet_kapsanan": ortusme.diyanet_kapsanan,
            "diyanet_oran": _oran(ortusme.diyanet_kapsanan, ortusme.diyanet_kelime),
            "rnk_kelime": ortusme.rnk_kelime,
            "rnk_kapsanan": ortusme.rnk_kapsanan,
            "rnk_oran": _oran(ortusme.rnk_kapsanan, ortusme.rnk_kelime),
        },
        "dosyalar": dosyalar,
    }


# ---------------------------------------------------------------------------
# Staged girdi


def _manifest_adimi(calisma: Path) -> str | None:
    try:
        ham = json.loads((calisma / "manifest.json").read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    adim = ham.get("adim") if isinstance(ham, dict) else None
    return adim if isinstance(adim, str) else None


def son_calisma(klasor: Path, adim: str | None = "ingest") -> Path:
    """`klasor` altindaki en yeni (run_id'ye gore) `units.jsonl` tasiyan calisma klasoru.

    `adim` verilirse yalniz manifestinde `adim` ayni olan calismalar secilir (varsayilan
    `ingest`: normalize ve anchor ciktilari ayni kitaplari baska bicimde tasir; karsilastirma
    ham ayristirma ciktisini okur). `adim=None` her calismayi kabul eder.
    """
    adaylar = sorted(
        (
            p
            for p in klasor.iterdir()
            if p.is_dir()
            and (p / "units.jsonl").is_file()
            and (adim is None or _manifest_adimi(p) == adim)
        ),
        key=lambda p: p.name,
    )
    if not adaylar:
        raise GirdiHatasi(f"{klasor.name}: staged calisma bulunamadi")
    return adaylar[-1]


def _satirlar(yol: Path) -> Iterator[dict[str, object]]:
    with yol.open(encoding="utf-8") as f:
        for no, satir in enumerate(f, start=1):
            if not satir.strip():
                continue
            try:
                nesne = json.loads(satir)
            except json.JSONDecodeError:
                raise GirdiHatasi(f"{yol.name} satir {no}: gecersiz JSON") from None
            if not isinstance(nesne, dict):
                raise GirdiHatasi(f"{yol.name} satir {no}: nesne bekleniyor")
            yield nesne


def _sozluk(deger: object, ad: str) -> Mapping[str, object]:
    if not isinstance(deger, dict):
        raise GirdiHatasi(f"staged satir: {ad} nesne degil")
    return deger


def _metin(deger: object, ad: str) -> str:
    if not isinstance(deger, str):
        raise GirdiHatasi(f"staged satir: {ad} metin degil")
    return deger


def _kitap_slug(capa: str) -> str:
    parcalar = capa.split(":")
    if len(parcalar) < 3 or parcalar[0] != "rn":
        raise GirdiHatasi("staged satir: rn capasi bekleniyor")
    return parcalar[1]


def _bolum_anahtari(capa: str) -> str:
    """`rn:{kitap}[:{bolum}]...[:hasiye-n]:p{n}` -> bolum yolu (kitap sonrasi, hasiye ve p yok)."""
    parcalar = capa.split(":")[2:]
    while parcalar and (
        re.fullmatch(r"p[0-9]+", parcalar[-1]) or re.fullmatch(r"hasiye-[0-9]+", parcalar[-1])
    ):
        parcalar.pop()
    return ":".join(parcalar)


@dataclass
class DiyanetKitabi:
    ana: list[Birim] = field(default_factory=list)
    dipnot: list[Birim] = field(default_factory=list)
    bolum_adlari: dict[int, str] = field(default_factory=dict)


def diyanet_oku(
    units: Path, kitaplar: Mapping[str, risale.Kitap], slug_listesi: Iterable[str]
) -> dict[str, DiyanetKitabi]:
    """Diyanet `units.jsonl`'u kitap basina siralanmis ana ve dipnot akislarina ayirir.

    Siralama: `txt` biriminde (dosya sirasi, satir); markdown kaynakli dipnot tanimi dosya
    sonuna (bolum anahtariyla bulunan dosyaya) capa sirasiyla eklenir.
    """
    istenen = set(slug_listesi)
    dosya_sirasi: dict[str, dict[str, int]] = {}
    for slug in istenen:
        d = kitaplar[slug].diyanet
        if d is None:
            raise GirdiHatasi(f"{slug}: Diyanet karsiligi yok")
        dosya_sirasi[slug] = {
            f"{DIYANET_KLASORU}/{d.klasor}/{ad}": i for i, ad in enumerate(d.dosyalar, start=1)
        }
    ham: dict[str, list[tuple[int, int, str, str, str]]] = {s: [] for s in istenen}
    md_dipnot: dict[str, list[tuple[str, str, str]]] = {s: [] for s in istenen}
    bolum_dosya: dict[tuple[str, str], int] = {}
    for u in _satirlar(units):
        capa = _metin(u.get("anchor"), "anchor")
        slug = _kitap_slug(capa)
        if slug not in istenen:
            continue
        attrs = _sozluk(u.get("attrs"), "attrs")
        prov = _sozluk(u.get("provenance"), "provenance")
        metin = _metin(u.get("text"), "text")
        rol = "dipnot" if attrs.get("rol") == "dipnot" else "ana"
        if prov.get("kaynak") == "md":
            md_dipnot[slug].append((capa, rol, metin))
            continue
        yol = _metin(prov.get("dosya"), "provenance.dosya")
        sira = dosya_sirasi[slug].get(yol)
        if sira is None:
            raise GirdiHatasi(f"{slug}: Diyanet dosyasi kitap tablosunda yok")
        satir = prov.get("satir")
        if isinstance(satir, bool) or not isinstance(satir, int):
            raise GirdiHatasi(f"{slug}: provenance.satir tam sayi degil")
        bolum_dosya[(slug, _bolum_anahtari(capa))] = sira
        ham[slug].append((sira, satir, capa, rol, metin))
    sonuc: dict[str, DiyanetKitabi] = {}
    for slug in sorted(istenen):
        kitap = DiyanetKitabi()
        for sira, _satir, capa, rol, metin in sorted(ham[slug]):
            (kitap.ana if rol == "ana" else kitap.dipnot).append(Birim(capa, metin, sira))
            kitap.bolum_adlari.setdefault(sira, _bolum_anahtari(capa))
        for capa, _rol, metin in sorted(md_dipnot[slug]):
            sira = bolum_dosya.get((slug, _bolum_anahtari(capa)), 0)
            kitap.dipnot.append(Birim(capa, metin, sira))
        kitap.dipnot.sort(key=lambda b: b.dosya)  # kararli: dosya sirasi, sonra mevcut sira
        sonuc[slug] = kitap
    return sonuc


def rnk_birim_turu(u: Mapping[str, object]) -> str | None:
    """RNK staged biriminin turu (`baslik`, `paragraf`, `hasiye`).

    Ingest ciktisinda `attrs.kind`, anchor ciktisinda ust duzey `kind` alanidir; ikisi de okunur.
    """
    tur = u.get("kind")
    if isinstance(tur, str):
        return tur
    attrs = u.get("attrs")
    if isinstance(attrs, dict):
        tur = attrs.get("kind")
        if isinstance(tur, str):
            return tur
    return None


def rnk_kitap_slugu(capa: str) -> str:
    """`rn:{kitap}:...` capasindan kitap slug'i (bolunen dosyada parca slug'i)."""
    return _kitap_slug(capa)


@dataclass
class RnkKitabi:
    ana: list[Birim] = field(default_factory=list)
    dipnot: list[Birim] = field(default_factory=list)


def rnk_oku(units: Path, slug_listesi: Iterable[str]) -> dict[str, RnkKitabi]:
    """RNK `units.jsonl`: kitap basina, kaynak satir sirasiyla ana ve dipnot akisi."""
    istenen = set(slug_listesi)
    ham: dict[str, list[tuple[int, str, str, str]]] = {s: [] for s in istenen}
    for u in _satirlar(units):
        slug = _kitap_slug(_metin(u.get("anchor"), "anchor"))
        if slug not in istenen:
            continue
        prov = _sozluk(u.get("provenance"), "provenance")
        konum = _sozluk(prov.get("konum"), "provenance.konum")
        satir = konum.get("satir")
        if not isinstance(satir, list) or not satir or not isinstance(satir[0], int):
            raise GirdiHatasi(f"{slug}: konum.satir bekleniyor")
        tur = "dipnot" if rnk_birim_turu(u) == "hasiye" else "ana"
        ham[slug].append(
            (satir[0], tur, _metin(u.get("anchor"), "anchor"), _metin(u.get("text"), "text"))
        )
    sonuc: dict[str, RnkKitabi] = {}
    for slug in sorted(istenen):
        kitap = RnkKitabi()
        for _satir, tur, capa, metin in sorted(ham[slug]):
            (kitap.ana if tur == "ana" else kitap.dipnot).append(Birim(capa, metin))
        sonuc[slug] = kitap
    return sonuc


# ---------------------------------------------------------------------------
# Rapor


def diyanet_kitaplari(tablo: Iterable[risale.Kitap]) -> list[risale.Kitap]:
    """`diyanet_karsiligi == "diyanet"` kitaplar (tablo sirasiyla)."""
    return [k for k in tablo if k.diyanet_karsiligi == "diyanet" and k.diyanet is not None]


def referans_kontrolu(satirlar: Mapping[str, Mapping[str, object]]) -> dict[str, object]:
    """Ikinci, Ucuncu ve Dorduncu Soz'de Diyanet kelimelerinin eslesme orani (beklenen: 1.0).

    Uc olcu ayri raporlanir: ana metin hizalamasi, ana + dipnot hizalamasi ve sirasiz
    `ORTUSME_K`-kelimelik ortusme. `ana_metin_tutuyor`: ana metin olcusu uc dosyada da 1.0;
    `hepsi_tutuyor`: uc olcu de 1.0 (dipnot dahil).
    """
    kitap = satirlar.get(REFERANS_KITAP)
    if kitap is None:
        return {"kitap": REFERANS_KITAP, "yapildi": False}
    dosyalar = kitap.get("dosyalar")
    olcular: dict[str, dict[str, float | None]] = {"ana_metin": {}, "toplam": {}, "ortusme": {}}
    if isinstance(dosyalar, list):
        for d in dosyalar:
            if not isinstance(d, dict) or d.get("dosya_sira") not in REFERANS_DOSYALAR:
                continue
            for ad, olcu in olcular.items():
                oge = d.get(ad)
                o = oge.get("eslesen_oran", oge.get("oran")) if isinstance(oge, dict) else None
                olcu[str(d["dosya_sira"])] = o if isinstance(o, float) else None
    tam = {
        ad: len(olcu) == len(REFERANS_DOSYALAR) and all(o == 1.0 for o in olcu.values())
        for ad, olcu in olcular.items()
    }
    return {
        "kitap": REFERANS_KITAP,
        "yapildi": True,
        "dosya_sirasi": list(REFERANS_DOSYALAR),
        "beklenen_oran": 1.0,
        "dosya_oranlari": olcular,
        "ana_metin_tutuyor": tam["ana_metin"],
        "hepsi_tutuyor": all(tam.values()),
    }


def rapor_uret(
    tablo: Sequence[risale.Kitap], diyanet_units: Path, rnk_units: Path
) -> dict[str, object]:
    """Diyanet'te karsiligi olan her kitap icin kelime dizisi karsilastirma raporu."""
    kitaplar = {k.slug: k for k in tablo}
    secilen = diyanet_kitaplari(tablo)
    slug_listesi = [k.slug for k in secilen]
    d = diyanet_oku(diyanet_units, kitaplar, slug_listesi)
    r = rnk_oku(rnk_units, slug_listesi)
    onbellek: dict[str, tuple[str, str] | None] = {}
    satirlar: dict[str, dict[str, object]] = {}
    toplamlar: list[AkisSonucu] = []
    ortusmeler: list[Ortusme] = []
    for k in secilen:
        ana = akis_karsilastir(d[k.slug].ana, r[k.slug].ana, onbellek)
        dipnot = akis_karsilastir(d[k.slug].dipnot, r[k.slug].dipnot, onbellek)
        toplamlar.extend((ana, dipnot))
        ortusme = ortusme_hesapla(
            (d[k.slug].ana, d[k.slug].dipnot), (r[k.slug].ana, r[k.slug].dipnot), onbellek
        )
        ortusmeler.append(ortusme)
        ozet = kitap_ozeti(ana, dipnot, ortusme, d[k.slug].bolum_adlari)
        ozet["rnk"] = None if k.rnk is None else {"raf": k.rnk.raf, "uid": k.rnk.uid}
        ozet["diyanet_dosya_sayisi"] = 0 if k.diyanet is None else len(k.diyanet.dosyalar)
        satirlar[k.slug] = ozet
    genel = _toplam(toplamlar)
    return {
        "surum": RAPOR_SURUMU,
        "yontem": {
            "kelime_anahtari": "kucuk harf (I -> noktasiz i, noktali I -> i), NFKD, birlesen isaret"
            " atilir, kesme silinir, noktasiz i -> i; Cf atilir",
            "hizalama": "ortak onek/sonek + difflib (kucuk bolge) + benzersiz k-kelime LIS"
            " (k = 8, 4); kitap ici yerel hizalama",
            "dp_siniri": DP_SINIRI,
            "akislar": ["ana_metin (baslik, paragraf)", "dipnot"],
            "ortusme": f"sirasiz {ORTUSME_K}-kelimelik dizi ortusmesi (ana + dipnot birlikte)",
        },
        "referans_kontrolu": referans_kontrolu(satirlar),
        "toplam": {
            "kitap": len(satirlar),
            "diyanet_kelime": genel.diyanet_kelime,
            "rnk_kelime": genel.rnk_kelime,
            "eslesen_kelime": genel.eslesen,
            "eslesen_oran_diyanet": _oran(genel.eslesen, genel.diyanet_kelime),
            "ortusme_oran_diyanet": _oran(
                sum(o.diyanet_kapsanan for o in ortusmeler),
                sum(o.diyanet_kelime for o in ortusmeler),
            ),
            "ortusme_oran_rnk": _oran(
                sum(o.rnk_kapsanan for o in ortusmeler), sum(o.rnk_kelime for o in ortusmeler)
            ),
        },
        "kitaplar": satirlar,
    }
