"""Risale (Diyanet) QA kapilari (A20.1, K-51 madde 2 ve 5): G-KAY ve G-BUT.

Kapi islevleri bellekteki `RisaleGirdisi` uzerinde calisir; ham zip, staged satirlari ve ingest
manifesti `qa/run_risale.py` tarafindan yuklenir. Bulgu listesi bos ise kapi `gecti`. Bulgular
ASCII ve kisadir; yalniz kitap slug'i, capa, sayi ve kisaltilmis ozet tasir, METIN ASLA.

G-CAP bu kaynakta YOKTUR: capa yeniden numaralanmaz denetimi A20.2b'de yazilir (RNK ve derleme
capalariyla birlikte). Bu adimdaki capalar karsilastirma verisinin adresidir.

* G-KAY: kaynak kaydi gecerli (`tur = "risale"`, `atif_metni` dolu); kayit adresi ve commit
  surumu kilitle ayni; ingest manifestindeki commit kayitla ayni; ham zip kilitteki boyut ve
  SHA-256 ile tutuyor.
* G-BUT:
  * zip kilitle okunabilir ve kitap kumesi kimlik tablosuyla ayni;
  * staged birimler ham zip'ten yeniden uretilenlerle birebir ayni (metin, attrs, provenance);
  * kitap basina kilitli sayilar (dosya, satir, kelime, dipnot, Arapca isareti, birim ...)
    yeniden uretilenlerle ve staged'dekilerle ayni; dipnot tanim/atif uyusmazliklari kilitteki
    izinli listeyle ayni (yeni uyusmazlik kapiyi kaldirir);
  * bos birim yok (kanonik ya da yalniz bosluk);
  * metin bayt esitligi BAGIMSIZ denetlenir: her `txt` kaynakli birimin metni, zip'teki uyenin
    `provenance.satir` numarali satirinin baytlariyla ayni (dipnot tanim satirinda `[etiket] `
    oneki disinda); `md` kaynagi yalniz dipnotta kullanilir;
  * karakter kurali: kilit disi Cf, Cc, Cs, Co, Cn ve bosluk turu (Zs, Zl, Zp; U+0020 haric)
    karakter ya da U+FFFD kapiyi kaldirir; kilitli karakterlerin kitap basina sayilari staged
    birimlerde kilitle ayni (K-51 madde 5: "yasak karakter yok" degil, kilitli sayilar).
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_diyanet import (
    KAYNAK,
    Cikarim,
    Kimlik,
    RisaleKilidi,
    kilitli_karakter_sayilari,
    yeniden_uret,
)
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

EN_COK_ORNEK: Final = 5


@dataclass
class RisaleGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    kilit: RisaleKilidi
    kimlik: Kimlik
    ham: bytes
    ham_sha256: str
    ingest_commit: str | None
    birim_satirlari: Sequence[Satir]  # staged units.jsonl

    @cached_property
    def zip(self) -> GuvenliZip | None:
        try:
            return GuvenliZip(self.ham)
        except GirdiHatasi:
            return None

    @cached_property
    def yeniden_uretilen(self) -> Cikarim | None:
        """Ham zip'ten yeniden uretilen cikarim; uretilemiyorsa None (G-BUT bulgu yazar)."""
        try:
            return yeniden_uret(self.ham, self.kilit, self.kimlik)
        except GirdiHatasi:
            return None


def _kitap(capa: str) -> str:
    """`rn:{kitap}:...` capasinin kitap slug'i (staged capasi kapida yalniz bicimlenir)."""
    parcalar = capa.split(":")
    return parcalar[1] if len(parcalar) > 2 and parcalar[0] == "rn" else ""


# --- G-KAY ---------------------------------------------------------------------------------


def g_kay(g: RisaleGirdisi) -> KapiSonucu:
    """Kaynak kaydi ve ham zip/kilit tutarliligi."""
    bulgular: list[str] = []
    kayit, kilit = g.kayit, g.kilit
    if kayit.tur != "risale":
        bulgular.append(f"{KAYNAK}: kayit turu risale degil")
    if all(harf in " \t\n" for harf in kayit.atif_metni):
        bulgular.append(f"{KAYNAK}: atif_metni bos")
    if kayit.kaynak_url != kilit.depo_url:
        bulgular.append(f"{KAYNAK}: kayit kaynak_url degeri kilitteki depo_url ile ayni degil")
    if kayit.surum != kilit.commit:
        bulgular.append(f"{KAYNAK}: kayit surumu kilitteki commit ile ayni degil")
    if g.ingest_commit is not None and g.ingest_commit != kayit.surum:
        bulgular.append(f"{KAYNAK}: ingest manifestindeki commit kayit surumuyle ayni degil")
    if g.ham_sha256 != kilit.zip_sha256 or len(g.ham) != kilit.zip_boyut:
        bulgular.append(f"{KAYNAK}: ham zip kilitteki sha256 ve boyutla tutmuyor")
    return KapiSonucu("G-KAY", tuple(bulgular), {"kaynak_kaydi": 1, "ham_bayt": len(g.ham)})


# --- G-BUT ---------------------------------------------------------------------------------


def _satir_farki(
    bulgular: list[str],
    ad: str,
    beklenen: Mapping[str, object],
    bulunan: Mapping[str, object],
) -> None:
    eksik = sorted(set(beklenen) - set(bulunan))
    fazla = sorted(set(bulunan) - set(beklenen))
    degisen = sorted(a for a in set(beklenen) & set(bulunan) if beklenen[a] != bulunan[a])
    for ne, liste in (("eksik", eksik), ("fazla", fazla), ("farkli", degisen)):
        if liste:
            ornek = ", ".join(liste[:EN_COK_ORNEK])
            bulgular.append(f"{ad}: yeniden uretilenle {len(liste)} {ne} birim (ornek {ornek})")


def _staged_sozlukleri(g: RisaleGirdisi, bulgular: list[str]) -> dict[str, dict[str, object]]:
    sonuc: dict[str, dict[str, object]] = {}
    for satir in g.birim_satirlari:
        try:
            capa = satir.metin("anchor")
            sonuc[capa] = {
                "text": satir.metin("text"),
                "attrs": satir.nesne("attrs"),
                "provenance": satir.nesne("provenance"),
            }
            if satir.metin("source_id") != KAYNAK:
                bulgular.append(f"{KAYNAK}: satir {satir.no}: source_id yanlis")
        except GirdiHatasi:
            bulgular.append(f"{KAYNAK}: satir {satir.no}: birim alanlari gecersiz")
    return sonuc


def _kaynak_satirlari(
    z: GuvenliZip, kok: str, uye: str, onbellek: dict[str, list[str]]
) -> list[str]:
    """Zip uyesinin satirlari (yalniz LF'de bolunur; satir sonu CR atilir); bagimsiz okuma."""
    if uye not in onbellek:
        metin = z.oku(f"{kok}/{uye}").decode("utf-8").removeprefix("﻿")
        onbellek[uye] = [s[:-1] if s.endswith("\r") else s for s in metin.split("\n")]
    return onbellek[uye]


def _bayt_esitligi(
    g: RisaleGirdisi, staged: dict[str, dict[str, object]], bulgular: list[str]
) -> dict[str, int]:
    """Her txt kaynakli birim, zip uyesinin ilgili satiriyla (bagimsiz okuma) ayni olmali."""
    z = g.zip
    sayilar = {"txt_birimi": 0, "md_birimi": 0, "bos_birim": 0}
    if z is None:
        return sayilar
    onbellek: dict[str, list[str]] = {}
    sorunlu: list[str] = []
    for capa, b in staged.items():
        metin = b["text"]
        prov = b["provenance"]
        attrs = b["attrs"]
        if not isinstance(metin, str) or not isinstance(prov, dict) or not isinstance(attrs, dict):
            sorunlu.append(capa)
            continue
        if metin.strip() == "":
            sayilar["bos_birim"] += 1
            sorunlu.append(capa)
            continue
        kaynak = prov.get("kaynak")
        if kaynak == "md":
            sayilar["md_birimi"] += 1
            if attrs.get("rol") != "dipnot":
                sorunlu.append(capa)  # md yalniz eksik dipnot icin yedektir
            continue
        sayilar["txt_birimi"] += 1
        satir_no, uye = prov.get("satir"), prov.get("dosya")
        if kaynak != "txt" or type(satir_no) is not int or not isinstance(uye, str):
            sorunlu.append(capa)
            continue
        try:
            satirlar = _kaynak_satirlari(z, g.kilit.kok, uye, onbellek)
        except (GirdiHatasi, UnicodeDecodeError):
            sorunlu.append(capa)
            continue
        if not 1 <= satir_no <= len(satirlar):
            sorunlu.append(capa)
            continue
        satir = satirlar[satir_no - 1]
        if attrs.get("rol") == "dipnot" and not attrs.get("devam"):
            etiket = attrs.get("etiket")
            beklenen = f"[{etiket}] {metin}"
        else:
            beklenen = metin
        if satir != beklenen:
            sorunlu.append(capa)
    if sorunlu:
        ornek = ", ".join(sorunlu[:EN_COK_ORNEK])
        bulgular.append(
            f"{KAYNAK}: {len(sorunlu)} birim kaynak satir baytlariyla ayni degil"
            f" ya da bos/gecersiz (ornek {ornek})"
        )
    return sayilar


def _karakter_denetimi(
    g: RisaleGirdisi, staged: dict[str, dict[str, object]], bulgular: list[str]
) -> None:
    """Kitap basina kilitli karakter sayilari staged metinlerde kilitle ayni olmali."""
    harfler: dict[str, Counter[str]] = {}
    for capa, b in staged.items():
        metin = b["text"]
        if isinstance(metin, str):
            harfler.setdefault(_kitap(capa), Counter()).update(metin)
    for slug, sayac in sorted(harfler.items()):
        kitap = g.kilit.kitaplar.get(slug)
        if kitap is None:
            bulgular.append(f"{KAYNAK}: kilitte olmayan kitap: {slug or '?'}")
            continue
        bulunan = kilitli_karakter_sayilari(sayac)
        if bulunan != dict(kitap.karakterler):
            fark = sorted(
                a
                for a in set(bulunan) | set(kitap.karakterler)
                if bulunan.get(a) != kitap.karakterler.get(a)
            )
            bulgular.append(
                f"{slug}: kilitli karakter sayilari kilitle ayni degil ({', '.join(fark[:8])})"
            )
        if "�" in sayac:
            bulgular.append(f"{slug}: U+FFFD (degistirme karakteri) var")


def g_but(g: RisaleGirdisi) -> KapiSonucu:
    """Metin butunlugu: yeniden uretilebilirlik, kilitli sayilar, bos birim, bayt esitligi."""
    bulgular: list[str] = []
    kilit = g.kilit
    if g.zip is None:
        bulgular.append(f"{KAYNAK}: ham zip guvenli bicimde okunamadi")
    yeni = g.yeniden_uretilen
    if yeni is None:
        bulgular.append(f"{KAYNAK}: ham zip'ten birimler yeniden uretilemedi")
    if {k.slug for k in g.kimlik.kitaplar} != set(kilit.kitaplar):
        bulgular.append(f"{KAYNAK}: kimlik tablosu kitaplari kilit kitaplariyla ayni degil")
    staged = _staged_sozlukleri(g, bulgular)
    if len(staged) != len(g.birim_satirlari):
        bulgular.append(f"{KAYNAK}: staged'de yinelenen ya da gecersiz capa")

    # 1. yeniden uretilebilirlik
    if yeni is not None:
        beklenen = {
            b.anchor: {"text": b.text, "attrs": b.attrs, "provenance": b.provenance}
            for b in yeni.birimler
        }
        _satir_farki(bulgular, KAYNAK, beklenen, staged)
        # 2. kilitli sayilar (yeniden uretilen)
        for slug, kitap in kilit.kitaplar.items():
            if yeni.sayilar.get(slug) != dict(kitap.sayilar):
                fark = sorted(
                    a
                    for a in kitap.sayilar
                    if (yeni.sayilar.get(slug) or {}).get(a) != kitap.sayilar[a]
                )
                bulgular.append(
                    f"{slug}: kilitli sayilar kilitle ayni degil ({', '.join(fark[:8])})"
                )
            if tuple(yeni.uyusmazliklar.get(slug, [])) != kitap.dipnot_uyusmazliklari:
                bulgular.append(
                    f"{slug}: dipnot tanim/atif uyusmazliklari izinli listeyle ayni degil"
                )

    # 3. staged'den bagimsiz sayim
    rol_sayilari: dict[str, Counter[str]] = {}
    for capa, b in staged.items():
        attrs = b["attrs"]
        rol = attrs.get("rol") if isinstance(attrs, dict) else None
        rol_sayilari.setdefault(_kitap(capa), Counter())[str(rol)] += 1
    for slug, kitap in kilit.kitaplar.items():
        sayac = rol_sayilari.get(slug, Counter())
        s = kitap.sayilar
        if (
            sum(sayac.values()) != s["birim"]
            or sayac["baslik"] != s["baslik"]
            or sayac["paragraf"] != s["paragraf"]
            or sayac["dipnot"] != s["dipnot_birimi_txt"] + s["dipnot_birimi_md"]
        ):
            bulgular.append(f"{slug}: staged birim sayilari kilitle ayni degil")
        if (
            s["paragraf"] + s["baslik"] + s["dipnot_birimi_txt"]
            != s["bos_olmayan_satir"] - s["ayirici_satir"]
        ):
            bulgular.append(f"{slug}: txt birimleri ile bos olmayan satirlar tutarsiz")

    # 4. bos birim ve bagimsiz bayt esitligi
    sayilar = _bayt_esitligi(g, staged, bulgular)
    # 5. karakter kurali
    _karakter_denetimi(g, staged, bulgular)

    toplam: Counter[str] = Counter()
    for kitap in kilit.kitaplar.values():
        toplam.update({a: kitap.sayilar[a] for a in ("birim", "dosya", "baslik", "paragraf")})
    return KapiSonucu(
        "G-BUT",
        tuple(bulgular),
        {"kitap": len(kilit.kitaplar), "staged_birim": len(g.birim_satirlari), **toplam, **sayilar},
    )


KAPI_ISLEVLERI: Final = {"G-KAY": g_kay, "G-BUT": g_but}


def olcumler(g: RisaleGirdisi) -> dict[str, object]:
    """Rapora yazilan olcumler: kitap basina birim sayilari (icerik yok)."""
    return {
        "kitap_birim": {s: k.sayilar["birim"] for s, k in g.kilit.kitaplar.items()},
        "toplam_birim": sum(k.sayilar["birim"] for k in g.kilit.kitaplar.values()),
        "md_kaynakli_dipnot_tanimi": sum(
            k.sayilar["dipnot_tanimi_md_kaynakli"] for k in g.kilit.kitaplar.values()
        ),
        "baslik_hizalanamayan": sum(
            k.sayilar["baslik_hizalanamayan"] for k in g.kilit.kitaplar.values()
        ),
        "isaret_cozulemeyen": sum(
            k.sayilar["isaret_cozulemeyen"] for k in g.kilit.kitaplar.values()
        ),
    }
