"""Sure adi adaylari QA kapilari (A11.3): G-KAY ve G-BUT, olcumler (K-43 madde 4-5).

Kapi islevleri bellekteki `SureAdlariGirdisi` uzerinde calisir; ham dosyalar, staged satirlari ve
Tanzil sure satirlari `qa/run_sure_adlari.py` tarafindan zincirden yuklenir. Bulgular ASCII ve
kisadir; yalniz sure numarasi, sayi ve kisaltilmis ozet tasir, ad metni asla.

G-CAP ve G-NOR bu kaynakta YOKTUR:

* G-CAP capa gramerini, tekilligi ve okuma sirasini sinar. Bu kaynak capa uretmez; adayin anahtari
  `(surah_no, alias)`dir (`surah_no` 1..114 tam sayi). Anahtar tekilligi ve numara araligi
  G-BUT'ta sinanir.
* G-NOR arama metni (`ar_norm`, `search_text`) uretimini ve A05 vektorlerini sinar. Bu kaynak arama
  metni uretmez; yalniz `alias_key` hesaplar. `alias_key` yeniden uretimi (A05 `normalize_tr` genis
  anahtar, Arapcada `normalize_ar`) G-BUT'ta sinanir; A05 vektorleri `tanzil-uthmani` G-NOR'undadir.

* G-KAY: uc kaynak kaydi (`sure-adlari-vikipedi`, `quran-meta`, `tanzil-ust-veri`) gecerli ve
  `atif_metni` dolu; ham dosyalar `sure_adlari.lock.json` boyut ve ozetleriyle ayni; `revizyon.json`
  kilitteki revizyonu tasir ve kayit surumu o revizyonu anar; kayit adresleri kilitle ayni.
* G-BUT: 114 sure; her surede tam bir `kanonik` aday ve o Vikipedi tablosundaki gorunen addir;
  `(surah_no, alias)` ve `(surah_no, alias_key)` tekil; `status` hep `aday`; her surede Tanzil
  `ad_ar` Arapca aday olarak vardir; her `alias_key` yeniden uretilince tutar; riskli listesindeki
  her ad tam bir sureye eslenir ve `risky` bayragi listeyle ayni; staged adaylar ham dosyalardan
  yeniden uretilenle ayni; Tanzil karsilastirmasinda fark isaretli kanonik satirlar yeniden
  hesaplananla ayni. Tanzil farki kapiyi kirmaz (satir isaretli editor kuyruguna girer); sayisi
  `olcumler`de.
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any, Final

from mutalaa_pipeline.adimlar.sure_adlari_adaylar import (
    adaylari_uret,
    alias_anahtari,
    capraz_sure_cakismalari,
    riskli_eslesme,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.sure_adlari import (
    KAYNAK,
    QURAN_META,
    SURE_SAYISI,
    VIKIPEDI_REVIZYON,
    VIKIPEDI_TABLO,
    MetaSatiri,
    SureAdlariKilidi,
    TabloSatiri,
    Yonlendirme,
    quran_meta_ayristir,
    revizyon_denetle,
    tablo_ayristir,
    yonlendirme_adi_uygun,
    yonlendirmeleri_ayikla,
)
from mutalaa_pipeline.lineage import kisa_ozet, sha256_bayt
from mutalaa_pipeline.normalize import normalize_tr
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak
from mutalaa_pipeline.staged import Satir

ORNEK: Final = 5
KINDLER: Final = frozenset({"kanonik", "yazim", "arapca", "diger_ad"})
TANZIL: Final = "tanzil-ust-veri"


@dataclass
class SureAdlariGirdisi:
    """Zincirden yuklenmis, kapilarin okudugu veri."""

    kayit: Kaynak
    diger_kayitlar: Mapping[str, Kaynak]  # quran-meta, tanzil-ust-veri
    kilit: SureAdlariKilidi
    ham: Mapping[str, Mapping[str, bytes]]  # slug -> dosya adi -> baytlar
    tablo: Sequence[TabloSatiri]  # staged ingest
    yonlendirmeler: Sequence[Yonlendirme]
    meta: Sequence[MetaSatiri]
    tanzil: Sequence[Mapping[str, Any]]  # ust veri sure.jsonl
    adaylar: Sequence[Satir]  # aliases.jsonl
    riskli_adlar: Sequence[str]
    depo_kok: Path

    @cached_property
    def satirlar(self) -> list[Mapping[str, Any]]:
        return [s.veri for s in self.adaylar]


def _g(deger: object, en_uzun: int = 60) -> str:
    return ascii(str(deger))[1:-1][:en_uzun]


def _ekle(bulgular: list[str], ad: str, liste: Sequence[object], neden: str) -> None:
    if liste:
        gosterilen = ", ".join(_g(x) for x in liste[:ORNEK])
        fazla = len(liste) - ORNEK
        bulgular.append(
            f"{ad}: {len(liste)} birim: {neden}: {gosterilen}"
            + (f" (+{fazla})" if fazla > 0 else "")
        )


def _bos(metin: str) -> bool:
    return all(harf in " \t\n" for harf in metin)


# --- yeniden uretim ----------------------------------------------------------------------


def yeniden_uret(g: SureAdlariGirdisi) -> tuple[list[dict[str, object]], dict[str, Any]]:
    """Ham dosyalardan ayristirip adaylari yeniden uretir: `(adaylar, ayristirilanlar)`.

    Donen sozluk `tablo`, `yonlendirmeler`, `elenen`, `meta` anahtarlarini tasir. Ayristirma
    hatasi `GirdiHatasi` olarak yukari cikar (QA cikis 2).
    """
    viki = g.ham[KAYNAK]
    tablo = tablo_ayristir(viki[VIKIPEDI_TABLO].decode("utf-8"))
    yonlendirmeler, elenen = yonlendirmeleri_ayikla(
        {ad: v for ad, v in viki.items() if ad.startswith("yonlendirmeler-")}, tablo
    )
    meta = quran_meta_ayristir(g.ham[QURAN_META]["quran-meta-7.0.0.tgz"])
    adaylar = adaylari_uret(tablo, yonlendirmeler, meta, g.tanzil, g.riskli_adlar)
    return adaylar, {
        "tablo": tablo,
        "yonlendirmeler": yonlendirmeler,
        "elenen": elenen,
        "meta": meta,
    }


# --- G-KAY -------------------------------------------------------------------------------------


def g_kay(g: SureAdlariGirdisi) -> KapiSonucu:
    """Kaynak kayitlari, ham dosya ozetleri ve revizyon tutarliligi."""
    bulgular: list[str] = []
    kayitlar = {KAYNAK: g.kayit, **g.diger_kayitlar}
    for ad, kayit in kayitlar.items():
        if _bos(kayit.atif_metni):
            bulgular.append(f"{ad}: atif_metni bos")
    for slug, kilit in ((KAYNAK, g.kilit.vikipedi), (QURAN_META, g.kilit.quran_meta)):
        dosyalar = g.ham.get(slug, {})
        for ad, (boyut, ozet) in kilit.dosyalar.items():
            veri = dosyalar.get(ad)
            if veri is None:
                bulgular.append(f"{slug}: {ad} ham dosyada yok")
            elif sha256_bayt(veri) != ozet or len(veri) != boyut:
                bulgular.append(
                    f"{slug}: {ad} ham dosya kilitle tutmuyor (beklenen {kisa_ozet(ozet)})"
                )
    if g.kayit.kaynak_url != g.kilit.vikipedi.url:
        bulgular.append(f"{KAYNAK}: kayit kaynak_url degeri kilitteki url ile ayni degil")
    meta_kayit = g.diger_kayitlar.get(QURAN_META)
    if meta_kayit is not None:
        if meta_kayit.kaynak_url != g.kilit.quran_meta.url:
            bulgular.append(f"{QURAN_META}: kayit kaynak_url degeri kilitteki url ile ayni degil")
        if meta_kayit.surum != g.kilit.quran_meta.surum:
            bulgular.append(f"{QURAN_META}: kayit surumu kilit surumuyle ayni degil")
    if g.kayit.surum is None or g.kilit.vikipedi.surum not in g.kayit.surum:
        bulgular.append(f"{KAYNAK}: kayit surumu kilitteki revizyon numarasini anmiyor")
    try:
        revizyon_denetle(
            g.ham[KAYNAK][VIKIPEDI_REVIZYON],
            g.kilit.vikipedi,
            len(g.ham[KAYNAK][VIKIPEDI_TABLO]),
        )
    except (GirdiHatasi, KeyError) as hata:
        bulgular.append(f"revizyon.json: {_g(hata, 120)}")
    sayilar = {"kaynak_kaydi": len(kayitlar), "ham_dosya": sum(len(d) for d in g.ham.values())}
    return KapiSonucu("G-KAY", tuple(bulgular), sayilar)


# --- G-BUT -------------------------------------------------------------------------------------


def _tanzil_farki_olcumu(satirlar: Sequence[Mapping[str, Any]]) -> list[int]:
    return sorted(
        int(s["surah_no"])
        for s in satirlar
        if s["kind"] == "kanonik" and "tanzil_fark" in s["onerilen"]
    )


def g_but(g: SureAdlariGirdisi) -> KapiSonucu:
    """114 sure, kanonik tekligi, anahtar tekilligi, yeniden uretim, riskli eslesme."""
    bulgular: list[str] = []
    satirlar = g.satirlar
    anahtar_sayisi = Counter((s["surah_no"], s["alias"]) for s in satirlar)
    _ekle(
        bulgular,
        "yinelenen (surah_no, alias)",
        [f"{k[0]}" for k, n in anahtar_sayisi.items() if n > 1],
        "ayni sure ve alias birden fazla satirda",
    )
    key_sayisi = Counter((s["surah_no"], s["alias_key"], s["kind"] == "arapca") for s in satirlar)
    _ekle(
        bulgular,
        "yinelenen (surah_no, alias_key)",
        [f"{k[0]}" for k, n in key_sayisi.items() if n > 1],
        "ayni surede ayni anahtar tek aday olmali",
    )
    gecersiz = [
        f"{s.get('surah_no')}"
        for s in satirlar
        if not isinstance(s.get("surah_no"), int)
        or isinstance(s["surah_no"], bool)
        or not 1 <= s["surah_no"] <= SURE_SAYISI
        or s.get("kind") not in KINDLER
        or s.get("status") != "aday"
        or not isinstance(s.get("alias"), str)
        or _bos(str(s.get("alias")))
        or not isinstance(s.get("risky"), bool)
    ]
    _ekle(bulgular, "gecersiz aday satiri", gecersiz, "surah_no, kind, status, alias ya da risky")
    sureler = {int(s["surah_no"]) for s in satirlar if isinstance(s.get("surah_no"), int)}
    if sureler != set(range(1, SURE_SAYISI + 1)):
        bulgular.append(f"sure kumesi 1..{SURE_SAYISI} degil (sayi {len(sureler)})")
    kanonik = Counter(int(s["surah_no"]) for s in satirlar if s.get("kind") == "kanonik")
    _ekle(
        bulgular,
        "kanonik aday sayisi",
        [f"sure {n}" for n in range(1, SURE_SAYISI + 1) if kanonik.get(n, 0) != 1],
        "her surede tam bir kanonik aday olmali",
    )
    tablo_adlari = {t.no: t.ad for t in g.tablo}
    _ekle(
        bulgular,
        "kanonik ad",
        [
            f"sure {s['surah_no']}"
            for s in satirlar
            if s["kind"] == "kanonik" and tablo_adlari.get(int(s["surah_no"])) != s["alias"]
        ],
        "Vikipedi tablosundaki gorunen ad degil",
    )
    arapca = {(int(s["surah_no"]), s["alias"]) for s in satirlar if s["kind"] == "arapca"}
    _ekle(
        bulgular,
        "Arapca ad",
        [f"sure {int(t['no'])}" for t in g.tanzil if (int(t["no"]), t["ad_ar"]) not in arapca],
        "Tanzil ad_ar Arapca aday olarak yok",
    )
    yanlis_anahtar: list[str] = []
    for s in satirlar:
        try:
            if alias_anahtari(s["alias"], s["kind"] == "arapca") != s["alias_key"]:
                yanlis_anahtar.append(f"sure {s['surah_no']}")
        except GirdiHatasi:
            yanlis_anahtar.append(f"sure {s['surah_no']}")
    _ekle(bulgular, "alias_key", yanlis_anahtar, "yeniden uretilen anahtarla ayni degil")
    elenmemis = [f"sure {y.no}" for y in g.yonlendirmeler if not yonlendirme_adi_uygun(y.baslik)]
    _ekle(bulgular, "yonlendirme", elenmemis, "suzgecten gecmeyen baslik staged'de")

    try:
        yeni, ayristirilan = yeniden_uret(g)
    except (GirdiHatasi, KeyError) as hata:
        bulgular.append(f"ham dosyalar yeniden ayristirilamadi: {_g(hata, 120)}")
        yeni, ayristirilan = [], {}
    else:
        if list(map(dict, satirlar)) != yeni:
            fark = sorted(
                {int(str(a["surah_no"])) for a in yeni if a not in [dict(s) for s in satirlar]}
                | {int(s["surah_no"]) for s in satirlar if dict(s) not in yeni}
            )
            bulgular.append(
                f"aliases.jsonl yeniden uretilenle ayni degil (sure sayisi {len(fark)})"
            )
        if [t.sozluk() for t in g.tablo] != [t.sozluk() for t in ayristirilan["tablo"]]:
            bulgular.append("tablo.jsonl ham vikimetinden yeniden ayristirilanla ayni degil")
        if [y.sozluk() for y in g.yonlendirmeler] != [
            y.sozluk() for y in ayristirilan["yonlendirmeler"]
        ]:
            bulgular.append("yonlendirmeler.jsonl ham dosyalardan yeniden uretilenle ayni degil")
        if [m.sozluk() for m in g.meta] != [m.sozluk() for m in ayristirilan["meta"]]:
            bulgular.append("quran-meta.jsonl ham tarball'dan yeniden ayristirilanla ayni degil")
    eslesme = riskli_eslesme(satirlar, g.riskli_adlar)
    _ekle(
        bulgular,
        "riskli ad",
        [f"{i + 1}. ad ({len(v)} sure)" for i, v in enumerate(eslesme.values()) if len(v) != 1],
        "tam bir sureye eslenmiyor",
    )
    riskli_anahtarlar = {alias_anahtari(ad, False) for ad in g.riskli_adlar}
    _ekle(
        bulgular,
        "risky bayragi",
        [
            f"sure {s['surah_no']}"
            for s in satirlar
            if s["risky"] != (s["kind"] != "arapca" and s["alias_key"] in riskli_anahtarlar)
        ],
        "riskli ad listesiyle ayni degil",
    )
    beklenen_fark = sorted(
        t.no
        for t in g.tablo
        if _farkli(t, g.tanzil[t.no - 1] if t.no - 1 < len(g.tanzil) else None)
    )
    if _tanzil_farki_olcumu(satirlar) != beklenen_fark:
        bulgular.append("Tanzil fark isaretleri yeniden hesaplananla ayni degil")
    sayilar = {
        "aday": len(satirlar),
        "sure": len(sureler),
        "kanonik": sum(kanonik.values()),
        "riskli": sum(1 for s in satirlar if s["risky"]),
        "tanzil_fark_sure": len(_tanzil_farki_olcumu(satirlar)),
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


def _farkli(t: TabloSatiri, tanzil: Mapping[str, Any] | None) -> bool:
    from mutalaa_pipeline.adimlar.sure_adlari_adaylar import tanzil_farki

    return tanzil is not None and tanzil_farki(t, tanzil) is not None


KAPI_ISLEVLERI: Final[dict[str, Callable[[SureAdlariGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
}


# --- olcumler (kapi degil; rapora yazilir) -------------------------------------------------------


def olcumler(g: SureAdlariGirdisi, elenen_yonlendirme: int | None = None) -> dict[str, object]:
    """Rapora yazilan olcumler: sayilar, riskli eslesme, Tanzil farki, Arapca anahtar."""
    satirlar = g.satirlar
    arapca = [s for s in satirlar if s["kind"] == "arapca"]
    capraz = capraz_sure_cakismalari(satirlar)
    return {
        "aday": len(satirlar),
        "kind": dict(sorted(Counter(str(s["kind"]) for s in satirlar).items())),
        "kanonik_olan_sure": len({s["surah_no"] for s in satirlar if s["kind"] == "kanonik"}),
        "riskli_aday": sum(1 for s in satirlar if s["risky"]),
        # Rapor ad metni tasimaz: anahtar, riskli_adlar.txt icindeki ad sirasidir (1 tabanli).
        "riskli_eslesme": {
            str(i): v for i, v in enumerate(riskli_eslesme(satirlar, g.riskli_adlar).values(), 1)
        },
        "tanzil_fark_sure": _tanzil_farki_olcumu(satirlar),
        "yonlendirme": {"kabul": len(g.yonlendirmeler), "elenen": elenen_yonlendirme},
        "arapca_anahtar": {
            "aday": len(arapca),
            "genis_anahtar_bos": sum(1 for s in arapca if normalize_tr(s["alias"], "genis") == ""),
            "normalize_ar_benzersiz_sure_basina": all(
                len({s["alias_key"] for s in arapca if s["surah_no"] == n})
                == sum(1 for s in arapca if s["surah_no"] == n)
                for n in {s["surah_no"] for s in arapca}
            ),
            "ad_ar_benzersiz": len(
                {
                    s["alias_key"]
                    for s in arapca
                    if s["onerilen"]["kaynaklar"][0].get("alan") == "ad_ar"
                }
            ),
        },
        "capraz_sure_anahtar": {k: v for k, v in capraz.items()},
        "kaynak_ozetleri": {
            "vikipedi_revizyon": g.kilit.vikipedi.surum,
            "vikipedi_dosyalar": {
                ad: sha for ad, (_, sha) in sorted(g.kilit.vikipedi.dosyalar.items())
            },
            "quran_meta_surum": g.kilit.quran_meta.surum,
            "quran_meta_dosyalar": {
                ad: sha for ad, (_, sha) in sorted(g.kilit.quran_meta.dosyalar.items())
            },
        },
    }
