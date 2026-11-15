"""Risale lugat (Kelime-Frekans) QA kapilari (A20.6, K-51 madde 9, 10): G-KAY, G-BUT, G-CAP, G-NOR.

Lugat kaynaklari `lugat-rnk` ve `lugat-sozluk-rganeyev` (A20.6b) icin ayni dort kapi
`qa/checks/risale_lugat_kaynak.py` dosyasindadir (burada `KAYNAK_KAPI_ISLEVLERI` olarak
yeniden disa aktarilir).

Kapi islevleri bellekteki `LugatGirdisi` uzerinde calisir; ham zip, sozluk OCR dosyalari ve staged
`lugat.jsonl` `qa/run_risale_lugat.py` tarafindan yuklenir. Bulgu listesi bos ise kapi `gecti`.
Bulgular ASCII ve kisadir; yalniz sayi, satir numarasi ve alan adi tasir; baslik soz, anlam ve OCR
metni ASLA.

* G-KAY: kaynak kaydi gecerli ve `atif_metni` dolu; kayit adresi ve surumu kilitle ayni; ingest
  manifestindeki commit kayit surumuyle ayni; ham zip ve uc OCR dosyasi kilitteki boyut ve SHA-256
  ile tutuyor; uc sozluk kaydi gecerli.
* G-BUT: zipten yeniden okunan kimlik ve sayilar kilitle ayni; madde sayisi kilitteki benzersiz
  baslik soz eksi elenen noktalama; staged `lugat.jsonl` ham dosyalardan yeniden uretilenle bayt
  bayt ayni; baslik soz bayt esitligi (kume ve tekillik); her maddede `tanim_tr`, `osmanlica_yazim`,
  `koken_dil` ve `ar_kok_id` bos, durum `aday`, kok `hat`, surum 1, `content_hash` ve `duzey`
  dogru, alan kumesi tam; `anlam` sutunu maddeye gecmemis (anlam dizesi `onerilen_basvuru` disinda
  hicbir alanda yok); siklik toplami kitap siklik toplamina esit ve alt kume adi yok.
* G-CAP: UYGULANMAZ (lugat maddesinin capasi yoktur); satirlarda capa alani olmadigini sayar.
* G-NOR: `basliksoz_norm` bos degil ve baslik sozden yeniden uretilebilir.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import sozluk_ocr
from mutalaa_pipeline.ingest.kelime_frekans import (
    KAYNAK,
    KelimeFrekansKilidi,
    Okuma,
    kilit_denetle,
    lugat_satirlari,
    oku_zip,
)
from mutalaa_pipeline.ingest.lugat_madde import (
    DURUM_ADAY,
    KOKEN_HAT,
    MADDE_ALANLARI,
    MADDE_ANAHTARI,
    SURUM_1,
    basliksoz_norm,
    duzey_hesapla,
    madde_hash,
)
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip
from mutalaa_pipeline.lineage import sha256_bayt
from mutalaa_pipeline.qa.checks.risale_lugat_kaynak import (
    KAPI_ISLEVLERI as KAYNAK_KAPI_ISLEVLERI,
)
from mutalaa_pipeline.qa.checks.risale_lugat_kaynak import KaynakGirdisi
from mutalaa_pipeline.qa.checks.risale_lugat_kaynak import olcumler as kaynak_olcumler
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir, yapi_baytlari

KAPILAR: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
EN_COK_ORNEK: Final = 5
KAYNAKLAR_ANAHTARLARI: Final = frozenset(
    {"siklik", "kitaplar", "sozluk_isabet", "sozluk_guvenilmez"}
)
ISABET_ANAHTARLARI: Final = frozenset({"sozluk", "bulundu", "satir_no"})
ONERILEN_ANAHTARLARI: Final = frozenset({"anlam_basvuru", "siklik", "kitaplar"})


@dataclass
class LugatGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    sozluk_kayitlari: Mapping[str, Kaynak]
    kilit: KelimeFrekansKilidi
    zip_verisi: bytes
    ocr_verileri: Mapping[str, bytes]
    satirlar: Sequence[Satir]  # staged lugat.jsonl
    ingest_commit: str | None

    @cached_property
    def okuma(self) -> Okuma | None:
        """Ham zipten yeniden okunan veri; okunamiyorsa None (G-BUT bulgu yazar)."""
        try:
            return oku_zip(GuvenliZip(self.zip_verisi), self.kilit.commit)
        except GirdiHatasi:
            return None

    @cached_property
    def yeniden(self) -> list[dict[str, object]] | None:
        """Ham dosyalardan yeniden uretilen madde satirlari (zip, OCR); uretilemezse None."""
        okuma = self.okuma
        if okuma is None:
            return None
        try:
            indeksler = [
                sozluk_ocr.indeks_kur(s, self.ocr_verileri[s]) for s in sozluk_ocr.SOZLUKLER
            ]
            soz = sorted(
                (k for k in okuma.toplam if basliksoz_norm(k)), key=lambda k: (-okuma.toplam[k], k)
            )
            olcumu = sozluk_ocr.olcum(indeksler, soz)
            return lugat_satirlari(
                okuma, indeksler, sozluk_ocr.guvenilmezler(olcumu), self.kilit.commit
            )
        except GirdiHatasi:
            return None


def _bulgu(bulgular: list[str], ad: str, satirlar: Sequence[int | str], aciklama: str) -> None:
    if satirlar:
        ornek = ", ".join(str(s) for s in satirlar[:EN_COK_ORNEK])
        bulgular.append(f"{ad}: {len(satirlar)} satir {aciklama} (ornek satir: {ornek})")


def _tam(deger: object) -> bool:
    return isinstance(deger, int) and not isinstance(deger, bool)


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: LugatGirdisi) -> KapiSonucu:
    """Kaynak kayitlari ve ham dosya/kilit tutarliligi."""
    bulgular: list[str] = []
    kayit, kilit = g.kayit, g.kilit
    if all(harf in " \t\n" for harf in kayit.atif_metni):
        bulgular.append(f"{KAYNAK}: atif_metni bos")
    if kayit.kaynak_url != kilit.depo_url:
        bulgular.append(f"{KAYNAK}: kayit kaynak_url degeri kilitteki depo_url ile ayni degil")
    if kayit.surum != kilit.commit:
        bulgular.append(f"{KAYNAK}: kayit surumu kilitteki commit ile ayni degil")
    if g.ingest_commit is not None and g.ingest_commit != kayit.surum:
        bulgular.append(f"{KAYNAK}: ingest manifestindeki commit kayit surumuyle ayni degil")
    if sha256_bayt(g.zip_verisi) != kilit.zip_sha256 or len(g.zip_verisi) != kilit.zip_boyut:
        bulgular.append(f"{KAYNAK}: ham zip kilitteki sha256 ve boyutla tutmuyor")
    for sozluk in sozluk_ocr.SOZLUKLER:
        kayit_s = g.sozluk_kayitlari.get(sozluk)
        if kayit_s is None or all(h in " \t\n" for h in kayit_s.atif_metni):
            bulgular.append(f"{sozluk}: kayit yok ya da atif_metni bos")
        veri = g.ocr_verileri.get(sozluk)
        beklenen = kilit.sozlukler[sozluk]
        if veri is None or (sha256_bayt(veri), len(veri)) != (beklenen.sha256, beklenen.boyut):
            bulgular.append(f"{sozluk}: ham OCR dosyasi kilitteki sha256 ve boyutla tutmuyor")
    return KapiSonucu(
        "G-KAY",
        tuple(bulgular),
        {"kaynak_kaydi": 1 + len(g.sozluk_kayitlari), "ham_bayt": len(g.zip_verisi)},
    )


# --- G-BUT -------------------------------------------------------------------------------


def _madde_bulgulari(g: LugatGirdisi, anlamlar: set[str]) -> list[str]:
    """Satir bazli degismezler (ham dosyadan bagimsiz)."""
    kodlar = ("alan", "bos", "sabit", "hash", "duzey", "kaynaklar", "anlam", "sozluk")
    alan: dict[str, list[int]] = {k: [] for k in kodlar}
    kitaplar = set(g.kilit.kitaplar)
    sozlukler = list(sozluk_ocr.SOZLUKLER)
    for s in g.satirlar:
        v = s.veri
        if set(v) != set(MADDE_ALANLARI):
            alan["alan"].append(s.no)
            continue
        if v["tanim_tr"] not in (None, "") or any(
            v[a] is not None for a in ("osmanlica_yazim", "koken_dil", "ar_kok_id")
        ):
            alan["bos"].append(s.no)
        if (v["status"], v["origin"], v["version"], v["source_id"]) != (
            DURUM_ADAY,
            KOKEN_HAT,
            SURUM_1,
            KAYNAK,
        ) or not _tam(v["version"]):
            alan["sabit"].append(s.no)
        baslik = v["basliksoz"]
        kaynaklar = v["kaynaklar"]
        if not isinstance(baslik, str) or not isinstance(kaynaklar, dict):
            alan["kaynaklar"].append(s.no)
            continue
        # Anlam sutunu maddeye gecmemis: tanim, yazim, koken ve kaynaklar metinleri anlamlarda yok.
        yapraklar = _metin_yapraklari(
            {a: v[a] for a in ("tanim_tr", "osmanlica_yazim", "koken_dil", "kaynaklar")}
        )
        if any(y in anlamlar for _, y in yapraklar) or "anlam_basvuru" in kaynaklar:
            alan["anlam"].append(s.no)
        if v["content_hash"] != madde_hash(baslik, None):
            alan["hash"].append(s.no)
        siklik = kaynaklar.get("siklik")
        kitap_siklik = kaynaklar.get("kitaplar")
        isabetler = kaynaklar.get("sozluk_isabet")
        guvenilmez = kaynaklar.get("sozluk_guvenilmez")
        if (
            set(kaynaklar) != KAYNAKLAR_ANAHTARLARI
            or not _tam(siklik)
            or not isinstance(kitap_siklik, dict)
            or not kitap_siklik
            or not set(kitap_siklik) <= kitaplar
            or not all(_tam(n) and n >= 1 for n in kitap_siklik.values())
            or siklik != sum(kitap_siklik.values())
            or not isinstance(isabetler, list)
            or not isinstance(guvenilmez, list)
            or not set(guvenilmez) <= set(sozlukler)
        ):
            alan["kaynaklar"].append(s.no)
            continue
        if v["duzey"] != duzey_hesapla(int(siklik)):
            alan["duzey"].append(s.no)
        if len(isabetler) != len(sozlukler) or any(
            not isinstance(i, dict)
            or set(i) != ISABET_ANAHTARLARI
            or i["sozluk"] != sozluk
            or not isinstance(i["bulundu"], bool)
            or (i["bulundu"] != (i["satir_no"] is not None))
            or (i["satir_no"] is not None and not (_tam(i["satir_no"]) and i["satir_no"] >= 1))
            for i, sozluk in zip(isabetler, sozlukler, strict=False)
        ):
            alan["sozluk"].append(s.no)
        onerilen = v["onerilen_basvuru"]
        if (
            not isinstance(onerilen, dict)
            or set(onerilen) != ONERILEN_ANAHTARLARI
            or onerilen["siklik"] != siklik
            or onerilen["kitaplar"] != len(kitap_siklik)
        ):
            alan["kaynaklar"].append(s.no)
    ad = {
        "alan": "alan kumesi MADDE_ALANLARI ile ayni degil",
        "bos": "tanim_tr, osmanlica_yazim, koken_dil ya da ar_kok_id bos degil",
        "sabit": "status, origin, version ya da source_id sabit degerlerle ayni degil",
        "hash": "content_hash basliksoz ve bos tanimdan hesaplananla ayni degil",
        "duzey": "duzey siklik esiklerinden hesaplananla ayni degil",
        "kaynaklar": "kaynaklar ya da onerilen_basvuru bicimi bozuk (siklik, kitaplar, sozluk)",
        "anlam": "anlam dizesi maddeye gecmis (K-51 madde 10)",
        "sozluk": "sozluk_isabet kaydi bozuk",
    }
    bulgular: list[str] = []
    for kod, satirlar in alan.items():
        _bulgu(bulgular, kod, satirlar, ad[kod])
    return bulgular


def _metin_yapraklari(deger: object, alan: str = "") -> list[tuple[str, str]]:
    """`(ust alan adi, metin)` ciftleri: JSON agacinin metin yapraklari (anahtarlar dahil degil)."""
    if isinstance(deger, str):
        return [(alan, deger)]
    if isinstance(deger, dict):
        sonuc: list[tuple[str, str]] = []
        for anahtar, alt in deger.items():
            sonuc += _metin_yapraklari(alt, anahtar if alan == "" else alan)
        return sonuc
    if isinstance(deger, list):
        return [y for alt in deger for y in _metin_yapraklari(alt, alan)]
    return []


def g_but(g: LugatGirdisi) -> KapiSonucu:
    """Kilit sayilari, bayt esitligi, tekillik, tanim bos ve anlam sizmasi."""
    bulgular: list[str] = []
    kilit = g.kilit
    okuma = g.okuma
    satirlar = list(g.satirlar)
    if okuma is None:
        bulgular.append(f"{KAYNAK}: ham zip yeniden okunamadi")
        anlamlar: set[str] = set()
    else:
        try:
            kilit_denetle(kilit, okuma)
        except GirdiHatasi as hata:
            bulgular.append(str(hata))
        anlamlar = {a for sayac in okuma.basvuru.values() for a in sayac}
        beklenen = kilit.birlesik["benzersiz_kelime"] - kilit.birlesik["elenen_noktalama_soz"]
        if len(satirlar) != beklenen:
            bulgular.append(
                f"{KAYNAK}: madde sayisi {len(satirlar)}, kilitteki beklenen {beklenen}"
            )
        # Baslik soz bayt esitligi: staged kume = ham dosyalardaki kume (noktalama haric).
        staged = Counter(
            str(s.veri.get("basliksoz")).encode("utf-8", "surrogatepass") for s in satirlar
        )
        ham = {k.encode("utf-8") for k in okuma.toplam if basliksoz_norm(k)}
        if set(staged) != ham:
            bulgular.append(
                f"{KAYNAK}: baslik soz kumesi ham dosyalarla bayt bayt ayni degil"
                f" (staged {len(set(staged))}, ham {len(ham)})"
            )
        tekrar = [b for b, n in staged.items() if n > 1]
        if tekrar:
            bulgular.append(f"{KAYNAK}: {len(tekrar)} baslik soz birden cok maddede")
    bulgular += _madde_bulgulari(g, anlamlar)
    sirali = [str(s.veri.get("basliksoz")) for s in satirlar]
    if sirali != sorted(sirali):
        bulgular.append(f"{KAYNAK}: satirlar basliksoza gore sirali degil")
    yeniden = g.yeniden
    if yeniden is None:
        bulgular.append(f"{KAYNAK}: lugat satirlari ham dosyalardan yeniden uretilemedi")
    else:
        try:
            ayni = (
                yapi_baytlari(yeniden, MADDE_ANAHTARI)[0]
                == yapi_baytlari([s.veri for s in satirlar], MADDE_ANAHTARI)[0]
            )
        except GirdiHatasi:
            ayni = False
        if not ayni:
            bulgular.append(
                f"{KAYNAK}: staged lugat.jsonl ham dosyalardan yeniden uretilenle ayni degil"
            )
    return KapiSonucu(
        "G-BUT",
        tuple(bulgular),
        {
            "madde": len(satirlar),
            "benzersiz_kelime": kilit.birlesik["benzersiz_kelime"],
            "kitap": len(kilit.kitaplar),
            "alt_kume": len(kilit.dosyalar) - len(kilit.kitaplar),
            "anlam_dizesi": len(anlamlar),
        },
    )


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: LugatGirdisi) -> KapiSonucu:
    """Uygulanmaz: lugat maddesinin capasi yoktur; satirlarda capa alani olmadigini dogrular."""
    capali = [s.no for s in g.satirlar if "anchor" in s.veri]
    bulgular: list[str] = []
    _bulgu(bulgular, "capa", capali, "lugat maddesinde capa alani var")
    return KapiSonucu("G-CAP", tuple(bulgular), {"uygulanmaz": 1, "madde": len(g.satirlar)})


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: LugatGirdisi) -> KapiSonucu:
    """`basliksoz_norm` bos degil ve baslik sozden yeniden uretilebilir."""
    bulgular: list[str] = []
    bos: list[int] = []
    farkli: list[int] = []
    for s in g.satirlar:
        baslik, norm = s.veri.get("basliksoz"), s.veri.get("basliksoz_norm")
        if not isinstance(baslik, str) or not isinstance(norm, str) or norm == "":
            bos.append(s.no)
        elif basliksoz_norm(baslik) != norm:
            farkli.append(s.no)
    _bulgu(bulgular, "norm-bos", bos, "basliksoz_norm bos ya da metin degil")
    _bulgu(bulgular, "norm-fark", farkli, "basliksoz_norm yeniden uretilenle ayni degil")
    return KapiSonucu("G-NOR", tuple(bulgular), {"madde": len(g.satirlar)})


KAPI_ISLEVLERI: Final[dict[str, Callable[[LugatGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}


def olcumler(g: LugatGirdisi) -> dict[str, object]:
    """Yalniz sayilar: duzey dagilimi, sozluk isabeti, basvurulu madde, norm paylasan gruplar."""
    duzey = Counter(str(s.veri.get("duzey")) for s in g.satirlar)
    isabet: Counter[str] = Counter()
    basvurulu = 0
    norm_say: Counter[str] = Counter()
    for s in g.satirlar:
        kaynaklar = s.veri.get("kaynaklar")
        if isinstance(kaynaklar, dict) and isinstance(kaynaklar.get("sozluk_isabet"), list):
            for i in kaynaklar["sozluk_isabet"]:
                if isinstance(i, dict) and i.get("bulundu") is True:
                    isabet[str(i.get("sozluk"))] += 1
        onerilen = s.veri.get("onerilen_basvuru")
        if isinstance(onerilen, dict) and onerilen.get("anlam_basvuru"):
            basvurulu += 1
        norm_say[str(s.veri.get("basliksoz_norm"))] += 1
    return {
        "madde": len(g.satirlar),
        "duzey": dict(sorted(duzey.items())),
        "sozluk_isabet_madde": dict(sorted(isabet.items())),
        "basvurulu_madde": basvurulu,
        "norm_paylasan_grup": sum(1 for n in norm_say.values() if n > 1),
        "norm_paylasan_madde": sum(n for n in norm_say.values() if n > 1),
    }


__all__ = [
    "KAPILAR",
    "KAPI_ISLEVLERI",
    "KAYNAK_KAPI_ISLEVLERI",
    "KaynakGirdisi",
    "LugatGirdisi",
    "kaynak_olcumler",
    "olcumler",
]
