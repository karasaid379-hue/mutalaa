"""Normalizasyon vektorleri kosucusu (G-NOR): `shared/test-vectors/normalize/{tr,ar}.jsonl`.

Vektorler depo kokunden okunur ve Python normallestiricisinde (`mutalaa_pipeline.normalize`)
kosulur. Dosya yoksa, bicimi bozuksa (BOM, CR, bos satir, yinelenen kimlik, JSON hatasi) ya da
bir vektorun `expected` alani beklenen sekilde degilse `GirdiHatasi` (cikis 2): kapi
degerlendirilemez. Bir vektor beklenen degeri vermezse (ya da normallestirici hata verirse)
o vektor `kalan` listesine girer: kapi kalir (cikis 1). Iletilerde vektor icerigi yoktur,
yalniz kimlik.

Degismez kural (Arama §1.2 madde 7, A12.6): her Turkce vektor girdisinde `tr_narrow`, `tr_wide`
ve `tr_stem` ayni sayida sozcuk tasir ve sozcuk sirasi aynidir (Yayinlayici sutunlari sozcuk
sayisi bakimindan hizali varsayar). Kural bozulursa vektor `hizasiz` listesine girer ve kapi
kalir; beklenen degerden bagimsiz bir ek denetimdir.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.normalize import SearchKeys, normalize_ar, normalize_tr, search_keys

VEKTOR_DIZINI: Final = "shared/test-vectors/normalize"
DOSYALAR: Final = (("tr.jsonl", "tr"), ("ar.jsonl", "ar"))
BOM: Final = b"\xef\xbb\xbf"
CR: Final = b"\r"
TR_ANAHTARLARI: Final = frozenset({"dar", "genis"})


@dataclass(frozen=True)
class VektorSonucu:
    toplam: int
    kalan: tuple[str, ...]  # beklenen degeri vermeyen vektor kimlikleri
    hizasiz: tuple[str, ...] = ()  # tr_wide ve tr_stem sozcuk hizasini bozan vektor kimlikleri


def _oku(depo_kok: Path, ad: str, onek: str) -> list[dict[str, object]]:
    yer = f"{VEKTOR_DIZINI}/{ad}"
    try:
        ham = (depo_kok / VEKTOR_DIZINI / ad).read_bytes()
    except OSError:
        raise GirdiHatasi(f"{yer} okunamadi") from None
    if ham.startswith(BOM) or CR in ham:
        raise GirdiHatasi(f"{yer}: BOM ya da CR var (UTF-8 BOM'suz, LF olmali)")
    try:
        satirlar = ham.decode("utf-8").split("\n")
    except UnicodeDecodeError:
        raise GirdiHatasi(f"{yer}: UTF-8 degil") from None
    if satirlar and satirlar[-1] == "":
        satirlar.pop()
    if not satirlar:
        raise GirdiHatasi(f"{yer} bos")
    vektorler: list[dict[str, object]] = []
    kimlikler: set[str] = set()
    for no, satir in enumerate(satirlar, start=1):
        if satir == "":
            raise GirdiHatasi(f"{yer}: satir {no}: bos satir")
        try:
            nesne = kati_json(satir)
        except GirdiHatasi:
            raise GirdiHatasi(f"{yer}: satir {no}: JSON gecersiz") from None
        if not isinstance(nesne, dict):
            raise GirdiHatasi(f"{yer}: satir {no}: nesne degil")
        kimlik = nesne.get("id")
        if not isinstance(kimlik, str) or not kimlik.startswith(f"{onek}-"):
            raise GirdiHatasi(f"{yer}: satir {no}: id {onek}- ile baslayan metin olmali")
        if kimlik in kimlikler:
            raise GirdiHatasi(f"{yer}: yinelenen id: {kimlik}")
        kimlikler.add(kimlik)
        if not isinstance(nesne.get("input"), str) or "expected" not in nesne:
            raise GirdiHatasi(f"{yer}: {kimlik}: input (metin) ve expected zorunlu")
        vektorler.append(nesne)
    return vektorler


def _tr_gecer(vektor: dict[str, object]) -> bool:
    girdi, beklenen = str(vektor["input"]), vektor["expected"]
    if (
        not isinstance(beklenen, dict)
        or set(beklenen) != TR_ANAHTARLARI
        or not all(isinstance(deger, str) for deger in beklenen.values())
    ):
        raise GirdiHatasi(f"tr vektoru {vektor['id']}: expected {{dar, genis}} olmali")
    anahtarlar = search_keys(girdi)
    return bool(
        normalize_tr(girdi, "dar") == beklenen["dar"]
        and normalize_tr(girdi, "genis") == beklenen["genis"]
        and anahtarlar.tr_narrow == beklenen["dar"]
        and anahtarlar.tr_wide == beklenen["genis"]
    )


def sozcuk_hizali(anahtarlar: SearchKeys) -> bool:
    """`tr_narrow`, `tr_wide`, `tr_stem` ayni sayida sozcuk tasir.

    Anahtarlar tek U+0020 ile ayrilir; bos anahtar sifir sozcuktur, bos sozcuk (cift bosluk,
    bastaki ya da sondaki bosluk) hizayi bozar. Sira, uc anahtarin da ayni dar sozcuk dizisinden
    uretilmesiyle saglanir (`search_keys`).
    """
    dizilar = [a.split(" ") if a else [] for a in (anahtarlar.tr_narrow, anahtarlar.tr_wide)]
    dizilar.append(anahtarlar.tr_stem.split(" ") if anahtarlar.tr_stem else [])
    dar, genis, govde = dizilar
    return len(dar) == len(genis) == len(govde) and "" not in (*dar, *genis, *govde)


def _ar_gecer(vektor: dict[str, object]) -> bool:
    girdi, beklenen = str(vektor["input"]), vektor["expected"]
    if not isinstance(beklenen, str):
        raise GirdiHatasi(f"ar vektoru {vektor['id']}: expected metin olmali")
    return normalize_ar(girdi) == beklenen and search_keys(girdi).ar_norm == beklenen


def vektorleri_calistir(depo_kok: Path) -> VektorSonucu:
    """Iki vektor dosyasini kosar: toplam, beklenen degeri vermeyenler, hizasiz olanlar."""
    toplam = 0
    kalan: list[str] = []
    hizasiz: list[str] = []
    for ad, onek in DOSYALAR:
        for vektor in _oku(depo_kok, ad, onek):
            toplam += 1
            try:
                gecti = _tr_gecer(vektor) if onek == "tr" else _ar_gecer(vektor)
                if onek == "tr" and not sozcuk_hizali(search_keys(str(vektor["input"]))):
                    hizasiz.append(str(vektor["id"]))
            except GirdiHatasi:
                raise
            except Exception:  # normallestirici hata verdiyse vektor kalmistir
                gecti = False
            if not gecti:
                kalan.append(str(vektor["id"]))
    return VektorSonucu(toplam=toplam, kalan=tuple(kalan), hizasiz=tuple(hizasiz))
