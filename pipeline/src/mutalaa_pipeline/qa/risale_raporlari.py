"""Risale icindekiler karsilastirma raporu (A20.2b). Rapor METIN ICERMEZ.

Iki karsilastirma, kitap basina:

1. RNK `json` icindekileri <-> staged RNK baslik birimleri (`attrs.kind = "baslik"`): `json`
   dugumleri metindeki baslik satirlariyla bulunuyor mu?
2. RNK `json` icindekileri <-> eRisale `toc-tr.json` (Turkce kitaplar; eRisale kitap bolunmesi
   farkli: Emirdag Lahikasi tek kitaptir, RNK'da `emirdag-lahikasi-1` ve `-2` iki dosyadir;
   eRisale'nin `ilk-donem-eserleri` kitabi RNK'daki `ilk-eserler`dir).

Baslik anahtari (`baslik_normalize`): kucuk harf ACIK eslemeyle (`I -> noktasiz i`, `noktali I ->
i`; `str.lower()` yok), NFKD, birlesen isaretler (sapka, hareke) ve kesme isaretleri atilir,
`noktasiz i -> i`, harf ve rakam disindaki her sey bosluk olur ve BUTUN BOSLUKLAR silinir ("on
dorduncu" = "ondorduncu"; yazim farki degil). Bas rakam siralamasi ("1." = "birinci", 1-99)
sira sozcuguyle degistirilir; rakam onekini atan ikinci bir aday da vardir (eRisale "1. Baslik"
yazarken RNK numarasiz yazabilir). Karsilastirma SIRASIZdir: eRisale icindekileri RNK'dan daha
ince taneli olabilir ve sira farki "farkli yazilan" degil "yalniz" sayilmaz.

Eslestirme: once anahtar esitligi (tekrarlayan baslik adedi kadar), kalanlar arasinda
`rapidfuzz.fuzz.ratio >= BENZERLIK_ESIGI` ya da biri oteki(nin) oneki ise ("farkli yazilan") ve
kalan "yalniz" bir kaynakta. Oran, RNK `json` dugumlerinin (basligi olan) diger kaynakta karsiligi
olan kismidir: `(eslesen + farkli_yazilan) / rnk_dugum`. "Yalniz eRisale" ve "yalniz staged"
basliklar bu orani dusurmez (eRisale ve metin daha ince taneli olabilir) ama sayilir.

`onerilen_dogrulandi` yalniz ONERIDIR; `shared/data/risale-kitaplar.json` `dogrulandi` alanina
dokunulmaz (insan adimi I-24). Kural: slug belirsiz degil, `json` dugumu en az `EN_AZ_DUGUM`,
staged orani ve (eRisale karsiligi varsa) eRisale orani en az `ORAN_ESIGI` ve sayilar tutarli.
Cikti baslik METNI tasimaz: farklar `json` dugum sirasi, eRisale `id` ve staged capa olarak
listelenir.
"""

import json
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from rapidfuzz import fuzz

from mutalaa_pipeline.anchor import risale
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_karsilastirma import rnk_birim_turu, rnk_kitap_slugu
from mutalaa_pipeline.ingest.risale_rnk_staged import JsonBilgisi
from mutalaa_pipeline.ingest.tanzil import tarih_gecerli
from mutalaa_pipeline.normalize import lower_turkish

RAPOR_SURUMU: Final = 1
ORAN_ESIGI: Final = 0.95
EN_AZ_DUGUM: Final = 5
BENZERLIK_ESIGI: Final = 80.0
ONEK_EN_AZ: Final = 8
LISTE_SINIRI: Final = 300
# eRisale kitap kimligi -> RNK kitap slug'lari (kimlik slug ile ayni degilse)
ERISALE_ESLEME: Final[Mapping[str, tuple[str, ...]]] = {
    "emirdag-lahikasi": ("emirdag-lahikasi-1", "emirdag-lahikasi-2"),
    "ilk-donem-eserleri": ("ilk-eserler",),
}
ERISALE_KULLIYAT: Final = "kulliyat"
# Slug eslemesi belirsiz (A20.2a, I-24): onerilen_dogrulandi her kosulda false.
SLUG_BELIRSIZ: Final = frozenset(
    {"yirmi-ucuncu-soz-arapca", "melahik-arapca", "saykalul-islam-arapca"}
)

_KESME: Final = "".join(chr(c) for c in (0x27, 0x2019, 0x2018, 0x2BC, 0x2BE, 0x2BF, 0xB4, 0x60))
_NOKTASIZ_I: Final = chr(0x131)
_BIRLER: Final = (
    "",
    "birinci",
    "ikinci",
    "ucuncu",
    "dorduncu",
    "besinci",
    "altinci",
    "yedinci",
    "sekizinci",
    "dokuzuncu",
)
_ONLAR_SIRA: Final = (
    "",
    "onuncu",
    "yirminci",
    "otuzuncu",
    "kirkinci",
    "ellinci",
    "altmisinci",
    "yetmisinci",
    "sekseninci",
    "doksaninci",
)
_ONLAR: Final = ("", "on", "yirmi", "otuz", "kirk", "elli", "altmis", "yetmis", "seksen", "doksan")


# ---------------------------------------------------------------------------
# Baslik anahtari


def sira_sozcugu(n: int) -> str | None:
    """1-99 icin sira sayisi sozcugu (ASCII katlanmis, bitisik); disindakiler icin `None`."""
    if not 1 <= n <= 99:
        return None
    onlar, birler = divmod(n, 10)
    if birler == 0:
        return _ONLAR_SIRA[onlar]
    return _ONLAR[onlar] + _BIRLER[birler]


def _temiz_sozcukler(metin: str) -> list[str]:
    kucuk = lower_turkish(metin)
    ayrik = unicodedata.normalize("NFKD", kucuk)
    govde = "".join(
        c for c in ayrik if c not in _KESME and not unicodedata.category(c).startswith("M")
    ).replace(_NOKTASIZ_I, "i")
    return "".join(c if c.isalnum() else " " for c in govde).split()


def baslik_normalize(metin: str) -> str:
    """Baslik karsilastirma anahtari (bosluksuz, bas rakam siralamasi sira sozcugu)."""
    sozcukler = _temiz_sozcukler(metin)
    if sozcukler and sozcukler[0].isascii() and sozcukler[0].isdigit():
        sira = sira_sozcugu(int(sozcukler[0]))
        if sira is not None:
            sozcukler[0] = sira
    return "".join(sozcukler)


def baslik_adaylari(*metinler: str) -> tuple[str, ...]:
    """Tercih sirali anahtar adaylari: her metin icin tam anahtar, sonra rakam onekisiz anahtar."""
    adaylar: list[str] = []
    for metin in metinler:
        if metin.lstrip().startswith("#"):  # `textInBook` sayfa gonderimi ("#11"): baslik degil
            continue
        sozcukler = _temiz_sozcukler(metin)
        if not sozcukler:
            continue
        tam = baslik_normalize(metin)
        if tam not in adaylar:
            adaylar.append(tam)
        if sozcukler[0].isascii() and sozcukler[0].isdigit() and len(sozcukler) > 1:
            oneksiz = "".join(sozcukler[1:])
            if oneksiz not in adaylar:
                adaylar.append(oneksiz)
    return tuple(adaylar)


# ---------------------------------------------------------------------------
# Eslestirme


@dataclass(frozen=True)
class Baslik:
    """Bir kaynaktaki baslik: kimlik (`json` sirasi, eRisale `id`, staged capa) ve adaylar."""

    ref: str | int
    adaylar: tuple[str, ...]


@dataclass
class Eslesme:
    eslesen: list[tuple[str | int, str | int]]
    farkli: list[tuple[str | int, str | int]]
    yalniz_sol: list[str | int]
    yalniz_sag: list[str | int]


def _secim(oge: Baslik, hedefler: set[str]) -> str:
    for a in oge.adaylar:
        if a in hedefler:
            return a
    return oge.adaylar[0]


def _benzerlik(a: str, b: str) -> float:
    kisa, uzun = (a, b) if len(a) <= len(b) else (b, a)
    if len(kisa) >= ONEK_EN_AZ and uzun.startswith(kisa):
        return 100.0
    return float(fuzz.ratio(a, b))


def eslestir(sol: Sequence[Baslik], sag: Sequence[Baslik]) -> Eslesme:
    """Iki baslik listesini sirasiz eslestirir; adaysiz (bos anahtarli) basliklar dahil edilmez."""
    sol = [b for b in sol if b.adaylar]
    sag = [b for b in sag if b.adaylar]
    sol_tum = {a for b in sol for a in b.adaylar}
    sag_anahtar = {b.ref: _secim(b, sol_tum) for b in sag}
    sol_anahtar = {b.ref: _secim(b, set(sag_anahtar.values())) for b in sol}
    gruplar_sol: dict[str, list[str | int]] = defaultdict(list)
    gruplar_sag: dict[str, list[str | int]] = defaultdict(list)
    for b in sol:
        gruplar_sol[sol_anahtar[b.ref]].append(b.ref)
    for b in sag:
        gruplar_sag[sag_anahtar[b.ref]].append(b.ref)
    sonuc = Eslesme([], [], [], [])
    artan_sol: list[tuple[str | int, str]] = []
    artan_sag: list[tuple[str | int, str]] = []
    for anahtar in sorted(gruplar_sol.keys() | gruplar_sag.keys()):
        s, g = gruplar_sol.get(anahtar, []), gruplar_sag.get(anahtar, [])
        n = min(len(s), len(g))
        sonuc.eslesen.extend(zip(s[:n], g[:n], strict=True))
        artan_sol.extend((r, anahtar) for r in s[n:])
        artan_sag.extend((r, anahtar) for r in g[n:])
    adaylar = sorted(
        (
            (-_benzerlik(a, b), i, j)
            for i, (_, a) in enumerate(artan_sol)
            for j, (_, b) in enumerate(artan_sag)
        )
    )
    kullanilan_sol: set[int] = set()
    kullanilan_sag: set[int] = set()
    for eksi_skor, i, j in adaylar:
        if -eksi_skor < BENZERLIK_ESIGI:
            break
        if i in kullanilan_sol or j in kullanilan_sag:
            continue
        kullanilan_sol.add(i)
        kullanilan_sag.add(j)
        sonuc.farkli.append((artan_sol[i][0], artan_sag[j][0]))
    sonuc.yalniz_sol = [r for i, (r, _) in enumerate(artan_sol) if i not in kullanilan_sol]
    sonuc.yalniz_sag = [r for j, (r, _) in enumerate(artan_sag) if j not in kullanilan_sag]
    return sonuc


def _oran(pay: int, payda: int) -> float | None:
    return None if payda == 0 else round(pay / payda, 6)


def _sinirla(liste: Sequence[object]) -> list[object]:
    return list(liste[:LISTE_SINIRI])


def eslesme_ozeti(
    e: Eslesme, sol_adet: int, sag_adet: int, sol_ad: str, sag_ad: str
) -> dict[str, object]:
    """Sayilar, oran ve tutarlilik; `sol_adet` RNK `json` dugum sayisi (orani belirler)."""
    ortak = len(e.eslesen) + len(e.farkli)
    tutarli = ortak + len(e.yalniz_sol) == sol_adet and ortak + len(e.yalniz_sag) == sag_adet
    return {
        f"{sol_ad}_baslik": sol_adet,
        f"{sag_ad}_baslik": sag_adet,
        "eslesen": len(e.eslesen),
        "farkli_yazilan": len(e.farkli),
        f"yalniz_{sol_ad}": len(e.yalniz_sol),
        f"yalniz_{sag_ad}": len(e.yalniz_sag),
        "eslesme_orani": _oran(len(e.eslesen), sol_adet),
        "karsilik_orani": _oran(ortak, sol_adet),
        "sayilar_tutarli": tutarli,
        "farkli_yazilan_listesi": _sinirla([[s, g] for s, g in e.farkli]),
        f"yalniz_{sol_ad}_listesi": _sinirla(e.yalniz_sol),
        f"yalniz_{sag_ad}_listesi": _sinirla(e.yalniz_sag),
        "liste_siniri": LISTE_SINIRI,
    }


# ---------------------------------------------------------------------------
# Girdi okuma


def son_tarih(klasor: Path) -> str:
    """`klasor` altindaki en yeni tarih klasorunun adi."""
    adaylar = sorted(p.name for p in klasor.iterdir() if p.is_dir() and tarih_gecerli(p.name))
    if not adaylar:
        raise GirdiHatasi(f"{klasor.name}: tarih klasoru bulunamadi")
    return adaylar[-1]


def erisale_oku(yol: Path) -> dict[str, list[Baslik]]:
    """`toc-tr.json` -> kitap kimligi basina basliklar (kitap kokleri ve `kulliyat` haric)."""
    try:
        ham = json.loads(yol.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise GirdiHatasi("erisale toc-tr.json okunamadi (UTF-8 JSON olmali)") from None
    if not isinstance(ham, list):
        raise GirdiHatasi("erisale toc-tr.json: liste bekleniyor")
    kitaplar: dict[str, list[Baslik]] = defaultdict(list)
    for oge in ham:
        if not isinstance(oge, dict):
            raise GirdiHatasi("erisale toc-tr.json: nesne bekleniyor")
        kitap, baslik, duzey, kimlik = (
            oge.get("bookId"),
            oge.get("title"),
            oge.get("level"),
            oge.get("id"),
        )
        if (
            not isinstance(kitap, str)
            or not isinstance(baslik, str)
            or isinstance(duzey, bool)
            or not isinstance(duzey, int)
            or isinstance(kimlik, bool)
            or not isinstance(kimlik, int)
        ):
            raise GirdiHatasi("erisale toc-tr.json: bookId, title, level ve id bekleniyor")
        if kitap == ERISALE_KULLIYAT or duzey <= 0:
            continue
        kitaplar[kitap].append(Baslik(kimlik, baslik_adaylari(baslik)))
    return dict(kitaplar)


def json_basliklari(bilgi: JsonBilgisi, slug: str, kitap: risale.Kitap) -> tuple[list[Baslik], int]:
    """RNK `json` dugumlerinden `slug` kitabina dusenler ve basliksiz dugum sayisi.

    Bolunen dosyada (`sunuhat`) dugum, `pageNo` degerine gore parcaya gider.
    """
    dugumler = bilgi.dugumler[1:]
    rnk = kitap.rnk
    if rnk is not None and rnk.bolunme is not None:
        parcalar = rnk.bolunme.parcalar
        sira = [p.slug for p in parcalar].index(slug)
        alt = 0 if sira == 0 else parcalar[sira].baslangic_sayfasi
        ust = parcalar[sira + 1].baslangic_sayfasi if sira + 1 < len(parcalar) else None
        dugumler = tuple(d for d in dugumler if d.sayfa >= alt and (ust is None or d.sayfa < ust))
    sonuc: list[Baslik] = []
    basliksiz = 0
    for d in dugumler:
        adaylar = baslik_adaylari(d.baslik, d.metin_kitapta)
        if adaylar:
            sonuc.append(Baslik(d.sira, adaylar))
        else:
            basliksiz += 1
    return sonuc, basliksiz


def staged_basliklari(units: Path, slug_listesi: Iterable[str]) -> dict[str, list[Baslik]]:
    """Staged RNK `units.jsonl`: kitap basina baslik birimleri (ingest ve anchor bicimi)."""
    istenen = set(slug_listesi)
    sonuc: dict[str, list[Baslik]] = {s: [] for s in istenen}
    with units.open(encoding="utf-8") as f:
        for no, satir in enumerate(f, start=1):
            if '"baslik"' not in satir:
                continue
            try:
                u = json.loads(satir)
            except json.JSONDecodeError:
                raise GirdiHatasi(f"{units.name} satir {no}: gecersiz JSON") from None
            if not isinstance(u, dict) or rnk_birim_turu(u) != "baslik":
                continue
            capa, metin = u.get("anchor"), u.get("text")
            if not isinstance(capa, str) or not isinstance(metin, str):
                raise GirdiHatasi(f"{units.name} satir {no}: anchor ve text metin olmali")
            slug = rnk_kitap_slugu(capa)
            if slug not in istenen:
                continue
            adaylar = baslik_adaylari(metin)
            if adaylar:
                sonuc[slug].append(Baslik(capa, adaylar))
    return sonuc


# ---------------------------------------------------------------------------
# Rapor


def onerilen_dogrulandi(
    *,
    slug: str,
    json_dugum: int,
    staged: Mapping[str, object],
    erisale: Mapping[str, object] | None,
) -> tuple[bool, list[str]]:
    """Oneri ve gerekce kodlari (bos liste = tum kosullar tuttu)."""
    gerekce: list[str] = []
    if slug in SLUG_BELIRSIZ:
        gerekce.append("slug_belirsiz")
    if json_dugum == 0:
        gerekce.append("json_dugum_yok")
    elif json_dugum < EN_AZ_DUGUM:
        gerekce.append("yetersiz_dugum")
    for ad, ozet in (("staged", staged), ("erisale", erisale)):
        if ozet is None:
            continue
        oran = ozet.get("karsilik_orani")
        if not isinstance(oran, float) or oran < ORAN_ESIGI:
            gerekce.append(f"{ad}_orani_dusuk")
        if ozet.get("sayilar_tutarli") is not True:
            gerekce.append(f"{ad}_sayilar_tutarsiz")
    return (not gerekce), gerekce


def rapor_uret(
    tablo: Sequence[risale.Kitap],
    rnk_json: Mapping[str, JsonBilgisi],
    staged: Mapping[str, Sequence[Baslik]],
    erisale: Mapping[str, Sequence[Baslik]],
    kaynaklar: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """`rnk_json`: `raf/uid` -> `json` bilgisi; `staged`: slug -> baslik birimleri."""
    kitap_json: dict[str, list[Baslik]] = {}
    basliksiz: dict[str, int] = {}
    for k in tablo:
        if k.rnk is None:
            raise GirdiHatasi(f"{k.slug}: RNK baglantisi yok")
        bilgi = rnk_json.get(f"{k.rnk.raf}/{k.rnk.uid}")
        if bilgi is None:
            raise GirdiHatasi(f"{k.slug}: RNK json eksik")
        kitap_json[k.slug], basliksiz[k.slug] = json_basliklari(bilgi, k.slug, k)

    gruplar: dict[str, dict[str, object]] = {}
    grup_of: dict[str, str] = {}
    bilinen = {k.slug for k in tablo}
    for kimlik, basliklar in sorted(erisale.items()):
        slugs = ERISALE_ESLEME.get(kimlik, (kimlik,))
        eksik = [s for s in slugs if s not in bilinen]
        if eksik:
            raise GirdiHatasi(f"erisale kitabi {kimlik}: RNK kitabi tabloda yok")
        sol = [b for s in slugs for b in _on_ek(s, kitap_json[s])]
        sag = list(basliklar)
        e = eslestir(sol, sag)
        ozet = eslesme_ozeti(e, len(sol), len(sag), "rnk", "erisale")
        ozet["slug"] = list(slugs)
        ozet["rnk_dugum_referansi"] = "slug/json_sira"
        gruplar[kimlik] = ozet
        for s in slugs:
            grup_of[s] = kimlik

    satirlar: list[dict[str, object]] = []
    for k in tablo:
        assert k.rnk is not None
        sol = kitap_json[k.slug]
        e = eslestir(sol, list(staged.get(k.slug, ())))
        staged_ozet = eslesme_ozeti(e, len(sol), len(staged.get(k.slug, ())), "json", "staged")
        grup = gruplar.get(grup_of[k.slug]) if k.slug in grup_of else None
        oneri, gerekce = onerilen_dogrulandi(
            slug=k.slug, json_dugum=len(sol), staged=staged_ozet, erisale=grup
        )
        satirlar.append(
            {
                "slug": k.slug,
                "dil": k.dil,
                "rnk": {"raf": k.rnk.raf, "uid": k.rnk.uid},
                "json_basliksiz_dugum": basliksiz[k.slug],
                "json_staged": staged_ozet,
                "erisale_grup": grup_of.get(k.slug),
                "erisale_karsilik_orani": None if grup is None else grup["karsilik_orani"],
                "erisale_sayilar_tutarli": None if grup is None else grup["sayilar_tutarli"],
                "mevcut_dogrulandi": k.dogrulandi,
                "onerilen_dogrulandi": oneri,
                "dayanak": "erisale+staged" if grup is not None else "staged",
                "gerekce": gerekce,
            }
        )
    dagilim = Counter((str(s["dayanak"]), bool(s["onerilen_dogrulandi"])) for s in satirlar)
    return {
        "surum": RAPOR_SURUMU,
        "yontem": {
            "anahtar": "kucuk harf (I -> noktasiz i, noktali I -> i), NFKD, isaret ve kesme atilir,"
            " harf/rakam disi bosluk, butun bosluklar silinir; bas rakam 1-99 sira sozcugu",
            "eslestirme": "sirasiz; anahtar esitligi, sonra rapidfuzz.fuzz.ratio ya da onek"
            " (farkli yazilan), kalan yalniz",
            "karsilik_orani": "(eslesen + farkli_yazilan) / rnk json baslikli dugum sayisi",
            "metin": "rapor baslik metni icermez: json dugum sirasi, eRisale id, staged capa",
        },
        "esikler": {
            "oran": ORAN_ESIGI,
            "en_az_dugum": EN_AZ_DUGUM,
            "benzerlik": BENZERLIK_ESIGI,
            "gerekce": (
                "onerilen_dogrulandi: slug belirsiz degil, json dugumu >= en_az_dugum, staged ve"
                " (varsa) eRisale karsilik orani >= oran, sayilar tutarli. Yalniz oneridir;"
                " dogrulandi alani risale-kitaplar.json'da degismez (I-24)."
            ),
        },
        "kaynaklar": dict(kaynaklar or {}),
        "erisale_gruplari": gruplar,
        "kitaplar": satirlar,
        "ozet": {
            "kitap": len(satirlar),
            "onerilen_dogrulandi_true": sum(1 for s in satirlar if s["onerilen_dogrulandi"]),
            "onerilen_dogrulandi_false": sum(1 for s in satirlar if not s["onerilen_dogrulandi"]),
            "dayanak_dagilimi": {
                f"{d}:{'true' if v else 'false'}": n for (d, v), n in sorted(dagilim.items())
            },
        },
    }


def _on_ek(slug: str, basliklar: Sequence[Baslik]) -> list[Baslik]:
    """Birden cok dosyali eRisale kitabinda `json` sirasi cakismasin: referansa slug eklenir."""
    return [Baslik(f"{slug}/{b.ref}", b.adaylar) for b in basliklar]
