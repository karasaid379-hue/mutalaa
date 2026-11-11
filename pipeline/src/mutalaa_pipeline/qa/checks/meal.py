"""Meal QA kapilari (A16.3, K-49 madde 12): G-KAY, G-BUT, G-CAP, G-NOR, G-HIZ.

Kapi islevleri bellekteki `MealGirdisi` uzerinde calisir; zinciri `qa/run_meal.py` yukler.
Bulgular ASCII ve kisadir: yalniz capa, sayi ve alan adi tasir, metin asla. G-MET bu yolda
uygulanmaz (OCR ile S-15).

* G-KAY: kaynak kaydi gecerli (`tur = meal`, `surum` var, `atif_metni` K-49 madde 14'teki metinle
  baslar ve `{surum}` yer tutucusu tasimaz); ingest manifestindeki kilit ozeti paketteki kilitle
  ayni (eski kilitle alinmis staged kabul edilmez).
* G-BUT: 114 sure ve 6.236 birim (sure basina Tanzil ayet sayisi); birim metni kontrol
  karakteri tasimaz (U+200C ve U+200D serbest, ote Cf ve Cc, ayrica Cs, Co, Cn red; paragraf
  ici U+000A serbest); kendi metnimiz kanonik (`kanonik_metin` metni degistirmez: NFC dahil);
  bos birim yok (istisna: `attrs.birlesik_ile` tasiyan birlesik izleyen birim) ve degismez IKI
  YONLUDUR (`birlesik_ile` varsa metin bos, metin bossa `birlesik_ile` var); `besmele_meali`
  kanonik ve ozeti dogru; her birim ham dosyadan yeniden uretilince bayt bayt ayni (metin ve
  attrs; yeniden uretilebilirlik).
* G-CAP: capa kanonik ve mealin kendi eserinden, tekil, okuma sirasinda; `ord` kuresel ayet
  sirasi; `ayah_lo`/`ayah_hi` capadan (ve `attrs.kapsam`dan) turetilen yari acik aralik;
  `content_hash` metnin SHA-256'si; sabit alanlar; onceki QA'dan gecmis anchor calismasinin her
  capasi durur ve `content_hash` YALNIZ KILIT DEGISIMINDE degisebilir (degisim sayisi rapora
  yazilir).
* G-NOR: normalizasyon vektorleri Python'da gecer; `tr_*` anahtarlari metinden `search_keys` ile
  yeniden uretilince ayni; `ar_norm` bos; `provenance.arama` surumu.
* G-HIZ (sert kapi): her `q:{s}:{a}` icin tam bir `meal:{eser}:{s}:{a}` birimi vardir (fazla
  yoktur); birlesik gruplar tutarlidir: her `attrs.kapsam` bas birimi metin tasir ve kapsadigi
  ayetlerin geri kalani tam olarak bu bas birime `birlesik_ile` ile bagli izleyen birimlerdir;
  baglanti baska sureye ya da kapsam disina isaret etmez. Kalirsa `export pg` yapilmaz.
"""

import unicodedata
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline.adimlar.anchor_tanzil import kuresel_sira
from mutalaa_pipeline.adimlar.meal import (
    ANCHOR_ALANLARI,
    ATTRS_ANAHTARLARI,
    KIND,
    METIN_DURUMU,
    ROL,
    TR_ALANLARI,
    ayet_araligi,
    kapsam_coz,
    meal_capasi,
)
from mutalaa_pipeline.anchor import AnchorError, Meal, content_hash, kanonik_metin, parse, sort_key
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import meal_kaynaklari as kayitlar
from mutalaa_pipeline.lineage import OZET_DESENI
from mutalaa_pipeline.normalize import NORMALIZER_VERSION, search_keys
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu, Onceki
from mutalaa_pipeline.qa.vektorler import vektorleri_calistir
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

ORNEK_CAPA: Final = 5
SERBEST_BICIM: Final = frozenset({"‌", "‍"})  # U+200C, U+200D (yazim gerekliligi)
TOPLAM_AYET: Final = sum(AYET_SAYILARI)
YER_TUTUCU: Final = "{sürüm}"
# Sayfa basi/sonu bolgesi bu uzunlugu (kod noktasi) asarsa sezgi (bos satir ya da bilinen kapanis
# etiketi) metin kirpmis olabilir: G-BUT bulgusu. Gercek veride en uzun bolge 6 karakterdir.
BOLGE_ESIGI: Final = 100


@dataclass
class MealGirdisi:
    slug: str
    kayit: Kaynak
    anchor_satirlari: Sequence[Satir]
    yeniden: Mapping[str, tuple[str, dict[str, object]]]  # ham dosyadan yeniden uretim
    kilit_ozeti: str | None  # ingest manifestindeki kilit bolumu ozeti
    kilit_guncel: str  # paketteki kilit bolumunun ozeti
    depo_kok: Path
    onceki: Onceki | None = None
    onceki_kilit_ozeti: str | None = None
    # ingest manifestinin sayfa basi/sonu bolgeleri: `[{sure, on, son}]` (uzunluk ve ozet)
    bolgeler: Sequence[Mapping[str, object]] = ()


def _capalar(capalar: Sequence[str]) -> str:
    gosterilen = ", ".join(ascii(c)[1:-1][:64] for c in capalar[:ORNEK_CAPA])
    fazla = len(capalar) - ORNEK_CAPA
    return gosterilen + (f" (+{fazla})" if fazla > 0 else "")


def _bulgu(bulgular: list[str], ad: str, liste: Sequence[str], neden: str) -> None:
    if liste:
        bulgular.append(f"{ad}: {len(liste)} birim: {neden}: {_capalar(liste)}")


def yasak_karakter(metin: str) -> bool:
    """Kontrol (Cc), bicim (Cf), vekil (Cs), ozel (Co) ya da atanmamis (Cn) karakter var mi.

    Serbest: U+000A (paragraf ici satir sonu), U+200C ve U+200D (yazimda gerekebilir).
    """
    for harf in metin:
        if harf == "\n" or harf in SERBEST_BICIM:
            continue
        if unicodedata.category(harf) in ("Cc", "Cf", "Cs", "Co", "Cn"):
            return True
    return False


def _birimler(g: MealGirdisi) -> dict[tuple[int, int], Satir]:
    """`(sure, ayet) -> satir`; capasi ayristirilamayan satir atlanir (G-CAP bildirir)."""
    harita: dict[tuple[int, int], Satir] = {}
    for satir in g.anchor_satirlari:
        cozulen = meal_capasi(g.slug, satir.metin("anchor"))
        if cozulen is not None:
            harita.setdefault(cozulen, satir)
    return harita


def _attrs(satir: Satir) -> dict[str, object]:
    return dict(satir.nesne("attrs"))


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: MealGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    k = g.kayit
    kaynak = kayitlar.kaynak(g.slug)
    if k.slug != g.slug:
        bulgular.append("kaynak kaydi: slug kaynak kimligiyle ayni degil")
    if k.tur is not SourceKind.MEAL:
        bulgular.append("kaynak kaydi: tur meal olmali")
    if k.surum is None or k.surum == "":
        bulgular.append("kaynak kaydi: surum yok")
    if k.kaynak_url is None:
        bulgular.append("kaynak kaydi: kaynak_url yok")
    if YER_TUTUCU in k.atif_metni:
        bulgular.append("kaynak kaydi: atif_metni {surum} yer tutucusu tasiyor (K-49 madde 14)")
    beklenen = kaynak.atif
    if beklenen is not None and k.atif_metni not in (
        beklenen,
        beklenen + kayitlar.DENETLENDI_EKI,
    ):
        bulgular.append("kaynak kaydi: atif_metni K-49 madde 14'teki metinle ayni degil")
    if g.kilit_ozeti is None:
        bulgular.append("ingest manifestinde kilit ozeti yok (once ingest meal --force)")
    elif g.kilit_ozeti != g.kilit_guncel:
        bulgular.append("ingest eski bir kilitle alinmis: kilit ozeti paketteki kilitle ayni degil")
    return KapiSonucu("G-KAY", tuple(bulgular), {"kayit": 1})


# --- G-BUT -------------------------------------------------------------------------------


def g_but(g: MealGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    satirlar = g.anchor_satirlari
    if len(satirlar) != TOPLAM_AYET:
        bulgular.append(f"birim sayisi {len(satirlar)}, {TOPLAM_AYET} bekleniyor")
    sure_sayilari: dict[int, int] = {}
    for sure, _ in _birimler(g):
        sure_sayilari[sure] = sure_sayilari.get(sure, 0) + 1
    farkli_sure = [str(s) for s in range(1, 115) if sure_sayilari.get(s, 0) != AYET_SAYILARI[s - 1]]
    if farkli_sure or len(sure_sayilari) != 114:
        bulgular.append(
            f"sure basina birim sayisi Tanzil ayet sayisiyla ayni degil: {len(farkli_sure)} sure"
        )
    bos: list[str] = []
    cift_yon: list[str] = []
    kontrol: list[str] = []
    kanonik_degil: list[str] = []
    besmele_hatasi: list[str] = []
    attrs_hatasi: list[str] = []
    farkli: list[str] = []
    var: set[str] = set()
    for satir in satirlar:
        capa = satir.metin("anchor")
        var.add(capa)
        metin = satir.metin("text")
        attrs = _attrs(satir)
        izleyen = "birlesik_ile" in attrs
        if not set(attrs) <= ATTRS_ANAHTARLARI:
            attrs_hatasi.append(capa)
        if (metin == "" or all(h in " \t\n" for h in metin)) and not izleyen:
            bos.append(capa)
        if izleyen != (
            metin == ""
        ):  # iki yonlu: birlesik_ile varsa metin bos, bossa birlesik_ile var
            cift_yon.append(capa)
        if yasak_karakter(metin):
            kontrol.append(capa)
        if kanonik_metin(metin) != metin:
            kanonik_degil.append(capa)
        b = attrs.get("besmele_meali")
        if b is not None and (
            not isinstance(b, dict)
            or set(b) != {"metin", "content_hash"}
            or not isinstance(b["metin"], str)
            or kanonik_metin(b["metin"]) != b["metin"]
            or b["content_hash"] != content_hash(b["metin"])
        ):
            besmele_hatasi.append(capa)
        yeni = g.yeniden.get(capa)
        if yeni is None or yeni[0].encode("utf-8") != metin.encode("utf-8") or yeni[1] != attrs:
            farkli.append(capa)
    uzun_bolge: list[str] = []
    for b in g.bolgeler:
        for taraf in ("on", "son"):
            bolge = b.get(taraf)
            uzunluk = bolge.get("uzunluk") if isinstance(bolge, dict) else None
            if isinstance(uzunluk, int) and uzunluk > BOLGE_ESIGI:
                uzun_bolge.append(f"sure {b.get('sure')} {taraf}")
    if uzun_bolge:
        bulgular.append(
            f"sayfa basi/sonu bolgesi {BOLGE_ESIGI} karakteri asiyor ({len(uzun_bolge)}): "
            + ", ".join(uzun_bolge[:ORNEK_CAPA])
        )
    eksik_yeniden = sorted(set(g.yeniden) - var)
    for ad, liste, neden in (
        ("bos birim", bos, "metin bos ve birlesik_ile yok"),
        ("birlesik_ile degismezi", cift_yon, "birlesik_ile ile bos metin birbirini gerektirir"),
        ("kontrol karakteri", kontrol, "metinde yasak kontrol ya da bicim karakteri var"),
        ("kanonik olmayan metin", kanonik_degil, "kanonik_metin (NFC dahil) metni degistiriyor"),
        ("besmele_meali", besmele_hatasi, "ozet ya da kanonik bicim tutmuyor"),
        ("attrs", attrs_hatasi, "bilinmeyen anahtar"),
        ("yeniden uretilebilirlik", farkli, "ham dosyadan yeniden uretilen metin/attrs ayni degil"),
        ("yeniden uretilebilirlik", eksik_yeniden, "yeniden uretilen capa staged'de yok"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    sayilar = {
        "birim": len(satirlar),
        "beklenen_birim": TOPLAM_AYET,
        "sure": len(sure_sayilari),
        "birlesik_izleyen": sum(1 for s in satirlar if "birlesik_ile" in _attrs(s)),
        "yeniden_uretilen": len(g.yeniden),
        "bolge_sayisi": len(g.bolgeler),
        "en_uzun_bolge": max(
            (
                int(b[t]["uzunluk"])  # type: ignore[index]
                for b in g.bolgeler
                for t in ("on", "son")
                if isinstance(b.get(t), dict)
            ),
            default=0,
        ),
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: MealGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    gecersiz: list[str] = []
    tekrar: list[str] = []
    gorulen: set[str] = set()
    anahtarlar = []
    sira_hatasi: list[str] = []
    aralik_hatasi: list[str] = []
    ozet_hatasi: list[str] = []
    ozet_yanlis: list[str] = []
    sabit_hatasi: list[str] = []
    alan_hatasi: list[str] = []
    data_version = f"{g.slug}@{g.kayit.surum}"
    for satir in g.anchor_satirlari:
        capa = satir.metin("anchor")
        if capa in gorulen:
            tekrar.append(capa)
        gorulen.add(capa)
        if set(satir.veri) != ANCHOR_ALANLARI:
            alan_hatasi.append(capa)
            continue
        cozulen = meal_capasi(g.slug, capa)
        if cozulen is None:
            gecersiz.append(capa)
            continue
        anahtarlar.append((sort_key(parse(capa)), capa))
        sure, ayet = cozulen
        if satir.veri.get("ord") != kuresel_sira(sure, ayet):
            sira_hatasi.append(capa)
        try:
            beklenen_aralik: tuple[int, int] | None = ayet_araligi(sure, ayet, _attrs(satir))
        except GirdiHatasi:
            beklenen_aralik = None
        if (satir.veri.get("ayah_lo"), satir.veri.get("ayah_hi")) != beklenen_aralik:
            aralik_hatasi.append(capa)
        ozet, metin = satir.metin("content_hash"), satir.metin("text")
        if OZET_DESENI.fullmatch(ozet) is None:
            ozet_hatasi.append(capa)
        elif ozet != content_hash(metin):
            ozet_yanlis.append(capa)
        if (
            satir.metin("kind") != KIND
            or satir.metin("source_id") != g.slug
            or satir.metin("metin_durumu") != METIN_DURUMU
            or satir.metin("role") != ROL
            or satir.metin("data_version") != data_version
        ):
            sabit_hatasi.append(capa)
    siralama = [c for (a, _), (b, c) in pairwise(anahtarlar) if not a < b]
    for ad, liste, neden in (
        ("alan kumesi", alan_hatasi, "anchor cikisinin alan kumesi degil"),
        ("gecersiz capa", gecersiz, "kanonik degil ya da mealin capa ailesinden degil"),
        ("yinelenen capa", tekrar, "capa birden fazla satirda"),
        ("okuma sirasi", siralama, "satir onceki capadan sonra gelmiyor"),
        ("ord", sira_hatasi, "ord kuresel ayet sirasi degil"),
        ("ayah_lo/ayah_hi", aralik_hatasi, "capadan ve kapsamdan turetilen aralikla ayni degil"),
        ("content_hash biciminde", ozet_hatasi, "64 haneli kucuk harfli onaltilik degil"),
        ("content_hash", ozet_yanlis, "metnin SHA-256'siyla tutmuyor"),
        ("sabit alan", sabit_hatasi, "kind, source_id, metin_durumu, role ya da data_version"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    sayilar = {"capa": len(gorulen), "onceki_run": 0, "hash_degisen": 0, "kilit_degisti": 0}
    if g.onceki is not None:
        sayilar["onceki_run"] = 1
        simdiki = {s.metin("anchor"): s.metin("content_hash") for s in g.anchor_satirlari}
        kayip = sorted(c for c in g.onceki.ozetler if c not in simdiki)
        degisen = sorted(
            c for c, ozet in g.onceki.ozetler.items() if c in simdiki and simdiki[c] != ozet
        )
        kilit_degisti = g.onceki_kilit_ozeti is None or g.onceki_kilit_ozeti != g.kilit_ozeti
        sayilar.update(
            onceki_capa=len(g.onceki.ozetler),
            hash_degisen=len(degisen),
            kilit_degisti=1 if kilit_degisti else 0,
        )
        _bulgu(bulgular, "onceki surumde olup kaybolan capa", kayip, "capa kullanim disi olamaz")
        if not kilit_degisti:  # content_hash yalniz kilit degisiminde degisebilir (K-49 madde 12)
            _bulgu(
                bulgular,
                "onceki surumle content_hash farkli",
                degisen,
                "kilit ayni iken metin degismis",
            )
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: MealGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    vektor = vektorleri_calistir(g.depo_kok)
    if vektor.kalan:
        bulgular.append(
            f"normalizasyon vektoru: {len(vektor.kalan)}/{vektor.toplam} kaldi:"
            f" {_capalar(vektor.kalan)}"
        )
    if vektor.hizasiz:
        bulgular.append(
            f"tr_wide/tr_stem sozcuk hizasi: {len(vektor.hizasiz)} vektor:"
            f" {_capalar(vektor.hizasiz)}"
        )
    farkli: list[str] = []
    ar_dolu: list[str] = []
    surum: list[str] = []
    for satir in g.anchor_satirlari:
        capa = satir.metin("anchor")
        anahtarlar = search_keys(satir.metin("text"))
        beklenen = {
            "tr_narrow": anahtarlar.tr_narrow,
            "tr_wide": anahtarlar.tr_wide,
            "tr_stem": anahtarlar.tr_stem,
        }
        if any(satir.veri.get(alan) != beklenen[alan] for alan in TR_ALANLARI):
            farkli.append(capa)
        if satir.veri.get("ar_norm") is not None:
            ar_dolu.append(capa)
        arama = satir.nesne("provenance").get("arama")
        if not isinstance(arama, dict) or arama.get("normalizer_version") != NORMALIZER_VERSION:
            surum.append(capa)
    for ad, liste, neden in (
        ("arama anahtari", farkli, "metinden search_keys ile uretilen degerle ayni degil"),
        ("ar_norm", ar_dolu, "mealde ar_norm bos (null) olmali"),
        ("provenance.arama", surum, "normalizer_version yok ya da bu surumle ayni degil"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    sayilar = {
        "vektor": vektor.toplam,
        "vektor_kalan": len(vektor.kalan),
        "vektor_hizasiz": len(vektor.hizasiz),
        "anahtar_farki": len(farkli),
    }
    return KapiSonucu("G-NOR", tuple(bulgular), sayilar)


# --- G-HIZ -------------------------------------------------------------------------------


def g_hiz(g: MealGirdisi) -> KapiSonucu:
    """Her `q:{s}:{a}` icin tam bir meal birimi; birlesik gruplar tutarli (sert kapi)."""
    bulgular: list[str] = []
    birimler = _birimler(g)
    eser = kayitlar.capa_eseri(g.slug)
    eksik = [
        f"q:{s}:{a}"
        for s in range(1, 115)
        for a in range(1, AYET_SAYILARI[s - 1] + 1)
        if (s, a) not in birimler
    ]
    sayac = Counter(satir.metin("anchor") for satir in g.anchor_satirlari)
    cift = sorted(capa for capa, adet in sayac.items() if adet > 1)
    fazla = sorted(
        satir.metin("anchor")
        for satir in g.anchor_satirlari
        if meal_capasi(g.slug, satir.metin("anchor")) is None
    )
    bagsiz: list[str] = []
    baglanti_hatasi: list[str] = []
    kapsam_hatasi: list[str] = []
    bas_bos: list[str] = []
    beklenen_izleyen: dict[tuple[int, int], tuple[int, int]] = {}  # izleyen -> bas
    for (sure, ayet), satir in birimler.items():
        attrs = _attrs(satir)
        if "kapsam" in attrs:
            k = kapsam_coz(sure, ayet, attrs["kapsam"])
            if k is None or k[1] <= k[0]:
                kapsam_hatasi.append(satir.metin("anchor"))
                continue
            if satir.metin("text") == "":
                bas_bos.append(satir.metin("anchor"))
            for n in range(k[0] + 1, k[1] + 1):
                beklenen_izleyen[(sure, n)] = (sure, ayet)
    for (sure, ayet), satir in birimler.items():
        bag = _attrs(satir).get("birlesik_ile")
        if bag is None:
            if (sure, ayet) in beklenen_izleyen:
                bagsiz.append(satir.metin("anchor"))
            continue
        hedef = _bag_coz(bag, eser)
        if hedef is None or beklenen_izleyen.get((sure, ayet)) != hedef:
            baglanti_hatasi.append(satir.metin("anchor"))
    for ad, liste, neden in (
        ("eksik ayet", eksik, "q: ayetinin meal birimi ya da birlesik baglantisi yok"),
        ("yinelenen meal capasi", cift, "ayni capa birden fazla satirda"),
        ("fazla birim", fazla, "Tanzil ayeti olmayan ya da bu mealin disindaki capa"),
        ("birlesik kapsam", kapsam_hatasi, "attrs.kapsam gecersiz ya da bas ayetle baslamiyor"),
        ("birlesik bas birim", bas_bos, "kapsam tasiyan bas birimin metni bos"),
        ("birlesik izleyen", bagsiz, "kapsam icinde ama birlesik_ile baglantisi yok"),
        ("birlesik_ile", baglanti_hatasi, "bas birimin kapsaminda olmayan birime baglanmis"),
    ):
        _bulgu(bulgular, ad, liste, neden)
    sayilar = {
        "ayet": TOPLAM_AYET,
        "meal_birimi": len(birimler),
        "birlesik_bas": sum(1 for s in birimler.values() if "kapsam" in _attrs(s)),
        "birlesik_izleyen": len(beklenen_izleyen),
        "eksik": len(eksik),
    }
    return KapiSonucu("G-HIZ", tuple(bulgular), sayilar)


def _bag_coz(bag: object, eser: str) -> tuple[int, int] | None:
    """`birlesik_ile` capasi (`meal:{eser}:{s}:{a}`) -> `(sure, ayet)`; gecersizse None."""
    if not isinstance(bag, str):
        return None
    try:
        ref = parse(bag)
    except AnchorError:
        return None
    k = ref.anchor
    if not isinstance(k, Meal) or k.meal != eser or ref.span is not None:
        return None
    if not 1 <= k.sure <= 114 or not 1 <= k.ayet <= AYET_SAYILARI[k.sure - 1]:
        return None
    return k.sure, k.ayet


KAPI_ISLEVLERI: Final[dict[str, Callable[[MealGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
    "G-HIZ": g_hiz,
}
