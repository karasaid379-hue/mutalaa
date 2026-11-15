"""Lugat kaynagi (`lugat-rnk`, `lugat-sozluk-rganeyev`) QA kapilari (A20.6b, K-52 madde 10, 14).

Kapi islevleri bellekteki `KaynakGirdisi` uzerinde calisir; ham dosyalar, kilitler, staged
Kelime-Frekans satirlari ve staged `lugat.jsonl` `qa/run_risale_lugat.py` tarafindan yuklenir.
Bulgular ASCII ve kisadir; yalniz sayi, satir numarasi ve alan adi tasir; baslik soz ve tanim
metni ASLA.

* G-KAY: kaynak kaydi gecerli ve `atif_metni` dolu; kayit adresi ve surumu kilitle ayni; ham
  dosya kilitteki boyut ve SHA-256 ile tutuyor; rganeyev icin RNK kaydi gecerli ve RNK dosyasi
  RNK kilidiyle (ve rganeyev kilidindeki `bagimli_sha256` ile) tutuyor.
* G-BUT: ham dosyadan yeniden ayristirilan sayilar kilitle ayni; madde sayisi kilitteki alinan
  madde sayisi; HER maddenin `tanim_tr` degeri kaynak satirindaki tanimla BAYT BAYT esit (tek
  istisna kirpma: bas ve sondaki U+0020/U+0009; `ingest/lugat_kaynak.py`); tanim bos degil;
  `anlam_no` her baslikta ardisik 1..n; `status = aday`, `origin = kaynak`, `version = 1`,
  `content_hash` dogru, alan kumesi tam; `kaynaklar` yalniz izinli alanlari tasir ve anlam
  dizesi icermez; `duzey` eslesmeye gore (1-3 ya da 4); rganeyev'de hicbir baslik RNK'da yok;
  staged `lugat.jsonl` ham dosyalardan ve staged Kelime-Frekans satirlarindan yeniden
  uretilenle bayt bayt ayni.
* G-CAP: UYGULANMAZ (lugat maddesinin capasi yoktur); satirlarda capa alani olmadigini sayar.
* G-NOR: `basliksoz_norm` bos degil ve baslik sozden yeniden uretilebilir.
"""

from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import lugat_kaynak
from mutalaa_pipeline.ingest.lugat_kaynak import (
    BICIMLER,
    KAYNAK_RNK,
    Ayristirma,
    Bicim,
    LugatKaynakKilidi,
    Madde,
    kilit_denetle,
    rnk_anahtarlari,
    sayilari_hesapla,
    sec,
    uret,
)
from mutalaa_pipeline.ingest.lugat_madde import (
    DURUM_ADAY,
    DUZEY_RISALEDE_YOK,
    EN_COK_ANLAM_NO,
    KOKEN_KAYNAK,
    MADDE_ALANLARI_KAYNAK,
    MADDE_ANAHTARI_KAYNAK,
    SURUM_1,
    basliksoz_norm,
    duzey_hesapla,
    madde_hash,
)
from mutalaa_pipeline.lineage import sha256_bayt
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir, yapi_baytlari

KAPILAR: Final = ("G-KAY", "G-BUT", "G-CAP", "G-NOR")
EN_COK_ORNEK: Final = 5
KAYNAKLAR_ANAHTARLARI: Final = frozenset(
    {"kelime_frekans_karsiligi", "risale_basliksoz", "siklik", "kitaplar"}
)
ESLESEN_ANAHTARLARI: Final = KAYNAKLAR_ANAHTARLARI
YASAK_ANAHTARLAR: Final = frozenset({"anlam_basvuru", "anlam", "tanim", "tanim_tr"})


@dataclass
class KaynakGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    slug: str
    kayit: Kaynak
    bagimli_kayit: Kaynak | None  # rganeyev icin RNK kaydi
    kilit: LugatKaynakKilidi
    rnk_kilit: LugatKaynakKilidi | None
    ham: bytes
    rnk_ham: bytes | None
    risale_satirlari: Sequence[Satir]  # staged Kelime-Frekans lugat.jsonl (yalniz okunur)
    satirlar: Sequence[Satir]  # staged lugat.jsonl

    @property
    def bicim(self) -> Bicim:
        return BICIMLER[self.slug]

    @cached_property
    def yeniden(self) -> tuple[list[dict[str, object]], Ayristirma, list[Madde]] | None:
        """Ham dosyalardan yeniden uretilen satirlar; uretilemezse None (G-BUT bulgu yazar)."""
        try:
            return uret(
                self.bicim,
                self.ham,
                self.kilit.sha256,
                self.rnk_ham,
                (s.veri for s in self.risale_satirlari),
            )
        except GirdiHatasi:
            return None

    @cached_property
    def rnk_anahtar_kumesi(self) -> frozenset[str] | None:
        if self.rnk_ham is None:
            return None
        try:
            return rnk_anahtarlari(lugat_kaynak.ayristir(self.rnk_ham, BICIMLER[KAYNAK_RNK]))
        except GirdiHatasi:
            return None


def _bulgu(bulgular: list[str], ad: str, satirlar: Sequence[int | str], aciklama: str) -> None:
    if satirlar:
        ornek = ", ".join(str(s) for s in satirlar[:EN_COK_ORNEK])
        bulgular.append(f"{ad}: {len(satirlar)} satir {aciklama} (ornek satir: {ornek})")


def _tam(deger: object) -> bool:
    return isinstance(deger, int) and not isinstance(deger, bool)


def _bos(metin: str) -> bool:
    return all(harf in " \t\n" for harf in metin)


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: KaynakGirdisi) -> KapiSonucu:
    """Kaynak kayitlari ve ham dosya/kilit tutarliligi."""
    bulgular: list[str] = []
    kayit, kilit = g.kayit, g.kilit
    if _bos(kayit.atif_metni):
        bulgular.append(f"{g.slug}: atif_metni bos")
    if kayit.kaynak_url != kilit.url:
        bulgular.append(f"{g.slug}: kayit kaynak_url degeri kilitteki url ile ayni degil")
    if kayit.surum != kilit.kayit_surumu:
        bulgular.append(f"{g.slug}: kayit surumu kilitteki kayit_surumu ile ayni degil")
    if sha256_bayt(g.ham) != kilit.sha256 or len(g.ham) != kilit.boyut:
        bulgular.append(f"{g.slug}: ham dosya kilitteki sha256 ve boyutla tutmuyor")
    if g.bicim.rnk_bagimli:
        if g.bagimli_kayit is None or _bos(g.bagimli_kayit.atif_metni):
            bulgular.append(f"{KAYNAK_RNK}: kayit yok ya da atif_metni bos")
        rk = g.rnk_kilit
        if rk is None or g.rnk_ham is None:
            bulgular.append(f"{KAYNAK_RNK}: kilit ya da ham dosya yok")
        else:
            if (sha256_bayt(g.rnk_ham), len(g.rnk_ham)) != (rk.sha256, rk.boyut):
                bulgular.append(f"{KAYNAK_RNK}: ham dosya kilitteki sha256 ve boyutla tutmuyor")
            if kilit.bagimli_sha256 != rk.sha256:
                bulgular.append(f"{g.slug}: kilitteki RNK ozeti RNK kilidiyle ayni degil")
    return KapiSonucu(
        "G-KAY",
        tuple(bulgular),
        {"kaynak_kaydi": 1 + (g.bagimli_kayit is not None), "ham_bayt": len(g.ham)},
    )


# --- G-BUT -------------------------------------------------------------------------------


def _anlam_sizdi(kaynaklar: Mapping[str, object], risale_sozleri: frozenset[str]) -> bool:
    """`kaynaklar` icinde anlam/tanim anahtari ya da Risale baslik soz listesinde olmayan metin."""

    def tara(deger: object, ust: str) -> bool:
        if isinstance(deger, dict):
            return any(
                a in YASAK_ANAHTARLAR or tara(v, a if ust == "" else ust) for a, v in deger.items()
            )
        if isinstance(deger, list):
            return True  # izinli alanlarda liste yok
        if isinstance(deger, str):
            return not (ust == "risale_basliksoz" and deger in risale_sozleri)
        return False

    return tara(dict(kaynaklar), "")


def _madde_bulgulari(g: KaynakGirdisi) -> list[str]:
    """Satir bazli degismezler (ham dosyadan bagimsiz)."""
    kodlar = ("alan", "bos", "sabit", "tanim", "hash", "anlam_no", "kaynaklar", "anlam", "duzey")
    alan: dict[str, list[int]] = {k: [] for k in kodlar}
    risale_sozleri: set[str] = set()
    kitaplar_kumesi: set[str] = set()
    for r in g.risale_satirlari:
        baslik_r, kaynaklar_r = r.veri.get("basliksoz"), r.veri.get("kaynaklar")
        if isinstance(baslik_r, str):
            risale_sozleri.add(baslik_r)
        if isinstance(kaynaklar_r, dict) and isinstance(kaynaklar_r.get("kitaplar"), dict):
            kitaplar_kumesi.update(kaynaklar_r["kitaplar"])
    risale_kumesi = frozenset(risale_sozleri)
    for s in g.satirlar:
        v = s.veri
        if set(v) != set(MADDE_ALANLARI_KAYNAK):
            alan["alan"].append(s.no)
            continue
        if any(v[a] is not None for a in ("osmanlica_yazim", "koken_dil", "ar_kok_id")):
            alan["bos"].append(s.no)
        if (v["status"], v["origin"], v["version"], v["source_id"]) != (
            DURUM_ADAY,
            KOKEN_KAYNAK,
            SURUM_1,
            g.slug,
        ) or not _tam(v["version"]):
            alan["sabit"].append(s.no)
        baslik, tanim, kaynaklar = v["basliksoz"], v["tanim_tr"], v["kaynaklar"]
        if not isinstance(baslik, str) or not isinstance(kaynaklar, dict):
            alan["kaynaklar"].append(s.no)
            continue
        if not isinstance(tanim, str) or tanim == "" or tanim.strip(" \t") != tanim:
            alan["tanim"].append(s.no)
        elif v["content_hash"] != madde_hash(baslik, tanim):
            alan["hash"].append(s.no)
        no = v["anlam_no"]
        if not _tam(no) or not 1 <= int(str(no)) <= EN_COK_ANLAM_NO:
            alan["anlam_no"].append(s.no)
        if _anlam_sizdi(kaynaklar, risale_kumesi):
            alan["anlam"].append(s.no)
        karsilik = kaynaklar.get("kelime_frekans_karsiligi")
        duzey = v["duzey"]
        if karsilik is True:
            siklik, kitaplar = kaynaklar.get("siklik"), kaynaklar.get("kitaplar")
            risale_soz = kaynaklar.get("risale_basliksoz")
            if (
                set(kaynaklar) != ESLESEN_ANAHTARLARI
                or not _tam(siklik)
                or int(str(siklik)) < 1
                or not isinstance(kitaplar, dict)
                or not kitaplar
                or not set(kitaplar) <= kitaplar_kumesi
                or not all(_tam(n) and n >= 1 for n in kitaplar.values())
                or siklik != sum(kitaplar.values())
                or not isinstance(risale_soz, str)
                or risale_soz not in risale_kumesi
            ):
                alan["kaynaklar"].append(s.no)
            elif duzey != duzey_hesapla(int(str(siklik))):
                alan["duzey"].append(s.no)
        elif karsilik is False:
            if set(kaynaklar) != {"kelime_frekans_karsiligi"}:
                alan["kaynaklar"].append(s.no)
            elif duzey != DUZEY_RISALEDE_YOK:
                alan["duzey"].append(s.no)
        else:
            alan["kaynaklar"].append(s.no)
    ad = {
        "alan": "alan kumesi MADDE_ALANLARI_KAYNAK ile ayni degil",
        "bos": "osmanlica_yazim, koken_dil ya da ar_kok_id bos degil",
        "sabit": "status, origin, version ya da source_id sabit degerlerle ayni degil",
        "tanim": "tanim_tr bos ya da bas/sonunda U+0020/U+0009 var (kirpma kurali)",
        "hash": "content_hash basliksoz ve tanimdan hesaplananla ayni degil",
        "anlam_no": "anlam_no tam sayi degil ya da aralik disinda",
        "kaynaklar": "kaynaklar bicimi bozuk (bayrak, siklik, kitaplar, risale_basliksoz)",
        "anlam": "kaynaklar icinde anlam ya da tanim dizesi var (K-52 madde 10)",
        "duzey": "duzey eslesmeye gore (1-3, yoksa 4) hesaplananla ayni degil",
    }
    bulgular: list[str] = []
    for kod, satirlar in alan.items():
        _bulgu(bulgular, kod, satirlar, ad[kod])
    return bulgular


def _anlam_bulgulari(g: KaynakGirdisi) -> list[str]:
    """`anlam_no` her baslikta ardisik 1..n; satirlar `(basliksoz, anlam_no)` sirali ve tekil."""
    bulgular: list[str] = []
    gruplar: defaultdict[str, list[int]] = defaultdict(list)
    for s in g.satirlar:
        baslik, no = s.veri.get("basliksoz"), s.veri.get("anlam_no")
        if isinstance(baslik, str) and _tam(no):
            gruplar[baslik].append(int(str(no)))
    bozuk = [b for b, nolar in gruplar.items() if sorted(nolar) != list(range(1, len(nolar) + 1))]
    if bozuk:
        bulgular.append(f"anlam_no: {len(bozuk)} basligin anlam numaralari 1..n ardisik degil")
    anahtarlar = [(str(s.veri.get("basliksoz")), s.veri.get("anlam_no")) for s in g.satirlar]
    if anahtarlar != sorted(anahtarlar, key=lambda a: (a[0], int(str(a[1])) if _tam(a[1]) else 0)):
        bulgular.append(f"{g.slug}: satirlar (basliksoz, anlam_no) sirali degil")
    if len(set(anahtarlar)) != len(anahtarlar):
        bulgular.append(f"{g.slug}: yinelenen (basliksoz, anlam_no)")
    return bulgular


def g_but(g: KaynakGirdisi) -> KapiSonucu:
    """Kilit sayilari, tanim bayt esitligi, anlam sirasi, sabitler ve yeniden uretim."""
    bulgular: list[str] = []
    kilit = g.kilit
    satirlar = list(g.satirlar)
    yeniden = g.yeniden
    if yeniden is None:
        bulgular.append(f"{g.slug}: ham dosyadan yeniden uretilemedi")
    else:
        _, ayr, secilen = yeniden
        try:
            kilit_denetle(kilit, g.ham, sayilari_hesapla(ayr, secilen))
        except GirdiHatasi as hata:
            bulgular.append(str(hata))
        if len(satirlar) != kilit.sayilar["alinan_madde"]:
            bulgular.append(
                f"{g.slug}: madde sayisi {len(satirlar)}, kilitteki alinan"
                f" {kilit.sayilar['alinan_madde']}"
            )
        # Tanim bayt esitligi: (basliksoz, anlam_no) -> kaynak satirindaki tanim.
        beklenen = {(m.baslik, m.anlam_no): m.tanim.encode("utf-8") for m in secilen}
        bulunan: dict[tuple[str, int], bytes] = {}
        for s in satirlar:
            baslik, no, tanim = (
                s.veri.get("basliksoz"),
                s.veri.get("anlam_no"),
                s.veri.get("tanim_tr"),
            )
            if isinstance(baslik, str) and _tam(no) and isinstance(tanim, str):
                bulunan[(baslik, int(str(no)))] = tanim.encode("utf-8", "surrogatepass")
        eksik = len(beklenen.keys() - bulunan.keys())
        fazla = len(bulunan.keys() - beklenen.keys())
        farkli = sum(1 for k, v in bulunan.items() if k in beklenen and beklenen[k] != v)
        if eksik or fazla:
            bulgular.append(f"{g.slug}: kaynak satirlariyla {eksik} eksik, {fazla} fazla madde")
        if farkli:
            bulgular.append(f"{g.slug}: {farkli} maddenin tanimi kaynak satiriyla bayt esit degil")
        try:
            ayni = (
                yapi_baytlari(yeniden[0], MADDE_ANAHTARI_KAYNAK)[0]
                == yapi_baytlari([s.veri for s in satirlar], MADDE_ANAHTARI_KAYNAK)[0]
            )
        except GirdiHatasi:
            ayni = False
        if not ayni:
            bulgular.append(
                f"{g.slug}: staged lugat.jsonl ham dosyalardan yeniden uretilenle ayni degil"
            )
    if g.bicim.rnk_bagimli:
        rnk = g.rnk_anahtar_kumesi
        if rnk is None:
            bulgular.append(f"{g.slug}: RNK dosyasi ayristirilamadi")
        else:
            cakisan = [
                s.no
                for s in satirlar
                if lugat_kaynak.esleme_anahtari(str(s.veri.get("basliksoz"))) in rnk
            ]
            _bulgu(
                bulgular,
                "rnk-cakisma",
                cakisan,
                "baslik RNK lugatinda var (yalniz RNK'da olmayan alinir)",
            )
        if g.rnk_kilit is not None and g.rnk_ham is not None:
            rnk_ayr = lugat_kaynak.ayristir(g.rnk_ham, BICIMLER[KAYNAK_RNK])
            try:
                kilit_denetle(
                    g.rnk_kilit,
                    g.rnk_ham,
                    sayilari_hesapla(rnk_ayr, sec(BICIMLER[KAYNAK_RNK], rnk_ayr, None)),
                )
            except GirdiHatasi as hata:
                bulgular.append(str(hata))
    bulgular += _madde_bulgulari(g)
    bulgular += _anlam_bulgulari(g)
    return KapiSonucu(
        "G-BUT",
        tuple(bulgular),
        {
            "madde": len(satirlar),
            "satir": kilit.sayilar["satir"],
            "bozuk": kilit.sayilar["satir"] - kilit.sayilar["gecerli_madde"],
            "benzersiz_baslik": kilit.sayilar["alinan_ham_baslik"],
            "cok_anlamli_baslik": kilit.sayilar["cok_anlamli_baslik"],
        },
    )


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: KaynakGirdisi) -> KapiSonucu:
    """Uygulanmaz: lugat maddesinin capasi yoktur; satirlarda capa alani olmadigini dogrular."""
    capali = [s.no for s in g.satirlar if "anchor" in s.veri]
    bulgular: list[str] = []
    _bulgu(bulgular, "capa", capali, "lugat maddesinde capa alani var")
    return KapiSonucu("G-CAP", tuple(bulgular), {"uygulanmaz": 1, "madde": len(g.satirlar)})


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: KaynakGirdisi) -> KapiSonucu:
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


KAPI_ISLEVLERI: Final[dict[str, Callable[[KaynakGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}


def olcumler(g: KaynakGirdisi) -> dict[str, object]:
    """Yalniz sayilar: madde, anlam, duzey dagilimi, Risale eslesmesi, cok anlamli baslik."""
    duzey = Counter(str(s.veri.get("duzey")) for s in g.satirlar)
    basliklar = Counter(str(s.veri.get("basliksoz")) for s in g.satirlar)
    eslesen = 0
    for s in g.satirlar:
        kaynaklar = s.veri.get("kaynaklar")
        if isinstance(kaynaklar, dict) and kaynaklar.get("kelime_frekans_karsiligi") is True:
            eslesen += 1
    return {
        "madde": len(g.satirlar),
        "benzersiz_baslik": len(basliklar),
        "cok_anlamli_baslik": sum(1 for n in basliklar.values() if n > 1),
        "en_cok_anlam": max(basliklar.values(), default=0),
        "duzey": dict(sorted(duzey.items())),
        "risale_eslesen_madde": eslesen,
        "risale_eslesmeyen_madde": len(g.satirlar) - eslesen,
    }


__all__ = ["KAPILAR", "KAPI_ISLEVLERI", "KaynakGirdisi", "olcumler"]
