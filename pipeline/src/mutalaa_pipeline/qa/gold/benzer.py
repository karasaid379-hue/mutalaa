"""`benzer-ayet` seti ve olcumu (A18.5; K-51 madde 10-12).

OLCULEN: kendi sozluksel secimimiz: Uthmani ve imlai n-gram indekslerinden QurSim'den BAGIMSIZ
secilen ciftler (`adaylari_bul` + `sinirla`; A18.3 uretiminin QurSim'i katmadan onceki hali,
yeniden hesaplanir ve veritabanindaki `sozluksel` satirlarla tutarliligi denetlenir). QurSim
kaynakli satirlar (`subtype = 'alim'`) QurSim ile OLCULMEZ (dongusellik yasagi).

NEDEN VERITABANI FILTRESI DEGIL: `evidence.subtype = 'sozluksel'` ve `evidence.qursim` /
`evidence.dongusel` YOK filtresi, uretimin birlestirme kurali geregi (QurSim cifti kendi
indeksimizde de adaysa `qursim` isareti alir) QurSim ciftlerinden TANIM GEREGI ayrik bir kume verir:
bu filtreyle QurSim kesinligi yapisal olarak 0'dir ve bir olcum degildir. Rapor bu sayiyi
`literal_veritabani_filtresi_bilgi` altinda yazar.

REFERANS 1 (`altin`): QurSim (`data/gelen/qursim/<tarih>/QurSim_filtered.csv`; yalniz `SS`, `SV`,
`TS`, `TV`, `Label` okunur, metin sutunlarina dokunulmaz); alim kaynakli cift listesi. Label
anlami dogrulanamadi: TUM etiketler pozitif sayilir (Label'a bagli esik yok); Label 0/1/2
kirilimi yalniz bilgi olarak raporlanir.
REFERANS 2 (`silver`): arriqaaq/ilm `qul/matching-ayah.json` (commit 6e03b8de43f3...;
hesaplamali); `data/gelen/ilm-matching-ayah/<tarih>/`. JSON `json` modulu ile okunur, hicbir sey
calistirilmaz. Tum eslesme girdileri cift sayilir (esik yok).

KESINLIK = olculen satirlardan referans cift kumesinde olanlarin orani. Kapi: QurSim ile (`altin`),
dondurulmus parcada; ilm ve birlesim kesinligi bilgi olarak yazilir. REFERANSLAR TAM KAPSAMLI
DEGILDIR: dusuk kesinlik "yanlis" demek degildir; referansta bulunmayan satirlarin sayisi ayri
yazilir.

Cift anahtari `q:s:a|q:s:a` (kucuk global ayet sirasi once). Bolme cift anahtariyla yapilir.
"""

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.enrich_tr_roots import ozetler_oku
from mutalaa_pipeline.enrich.baglantilar.qursim import qursim_oku
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.qa.gold import setler
from mutalaa_pipeline.qa.gold.kapi import TurSonucu, tahmin_ozeti
from mutalaa_pipeline.qa.gold.olcum import ESIKLER, esik_degerlendir, kapi_karari
from mutalaa_pipeline.qa.uyum import wilson_alt_sinir, wilson_ust_sinir

KAYNAK_QURSIM: Final = "qursim"
KAYNAK_ILM: Final = "ilm-matching-ayah"
QURSIM_DOSYASI: Final = "QurSim_filtered.csv"
ILM_DOSYASI: Final = "matching-ayah.json"
EN_BUYUK_BAYT: Final = 16 << 20
URETIM_KOMUTU: Final = "uv run --directory pipeline mutalaa qa gold --type benzer-ayet --build"
DOGRULAMA_YONTEMI: Final = (
    "QurSim (alim kaynakli cift listesi; tum Label degerleri pozitif) ve arriqaaq/ilm"
    " qul/matching-ayah.json (hesaplamali) cift kumeleri; olculen satirlarin referans cift"
    " kumesinde bulunma orani."
)
CiftAnahtari = tuple[int, int]


def gelen_dosyasi(veri_kok: Path, slug: str, ad: str) -> tuple[Path, str]:
    """`data/gelen/<slug>/<en yeni tarih>/<ad>`: SHA256SUMS ile dogrulanir; `(yol, tarih)`."""
    taban = veri_kok / "gelen" / slug
    tarihler = sorted(p.name for p in taban.iterdir() if p.is_dir()) if taban.is_dir() else []
    if not tarihler:
        raise GirdiHatasi(f"data/gelen/{slug}/<tarih> klasoru yok")
    klasor = taban / tarihler[-1]
    yol = klasor / ad
    if not yol.is_file():
        raise GirdiHatasi(f"data/gelen/{slug}/{tarihler[-1]}/{ad} yok")
    if yol.stat().st_size > EN_BUYUK_BAYT:
        raise GirdiHatasi(f"{slug}: dosya cok buyuk")
    if ozetler_oku(klasor).get(ad) != lineage.sha256_dosya(yol):
        raise GirdiHatasi(f"{slug}: {ad} SHA256SUMS ile tutmuyor")
    return yol, tarihler[-1]


def cift(a: int, b: int) -> CiftAnahtari:
    return (a, b) if a < b else (b, a)


def ilm_oku(yol: Path, ayet_sirasi: Mapping[str, int]) -> tuple[dict[CiftAnahtari, int], int]:
    """ilm JSON'u: `(lo, hi) -> en buyuk matched_words_count`, gecersiz girdi sayisi.

    Guvenilmeyen veri: yalniz `json` modulu; `s:a` anahtarlari 6.236 ayetlik kumeyle dogrulanir.
    """
    try:
        veri = json.loads(yol.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise GirdiHatasi("ilm matching-ayah.json okunamadi ya da gecersiz") from None
    if not isinstance(veri, dict):
        raise GirdiHatasi("ilm matching-ayah.json kok nesne degil")
    sonuc: dict[CiftAnahtari, int] = {}
    gecersiz = 0
    for anahtar, liste in veri.items():
        a = ayet_sirasi.get(f"q:{anahtar}") if isinstance(anahtar, str) else None
        if a is None or not isinstance(liste, list):
            gecersiz += 1
            continue
        for g in liste:
            ham = g.get("matched_ayah_key") if isinstance(g, dict) else None
            b = ayet_sirasi.get(f"q:{ham}") if isinstance(ham, str) else None
            sayi = g.get("matched_words_count") if isinstance(g, dict) else None
            if b is None or a == b or not isinstance(sayi, int):
                gecersiz += 1
                continue
            c = cift(a, b)
            sonuc[c] = max(sonuc.get(c, 0), sayi)
    return sonuc, gecersiz


def ornekleri_kur(
    qursim: Mapping[CiftAnahtari, int],
    ilm: Mapping[CiftAnahtari, int],
    ayet_capasi: Mapping[int, str],
    qursim_surum: str,
    ilm_surum: str,
) -> list[dict[str, object]]:
    ornekler: list[dict[str, object]] = []
    for c in sorted(qursim.keys() | ilm.keys()):
        kaynaklar: list[dict[str, str]] = []
        o: dict[str, object] = {}
        if c in qursim:
            kaynaklar.append(
                {
                    "source_id": KAYNAK_QURSIM,
                    "surum": qursim_surum,
                    "madde": "QurSim_filtered.csv cift",
                }
            )
            o["qursim_label"] = qursim[c]
        if c in ilm:
            kaynaklar.append(
                {"source_id": KAYNAK_ILM, "surum": ilm_surum, "madde": "matching-ayah.json cift"}
            )
            o["ilm_eslesen_kelime"] = ilm[c]
        ornekler.append(
            {
                "id": f"{ayet_capasi[c[0]]}|{ayet_capasi[c[1]]}",
                "sinif": "altin" if c in qursim else "silver",
                "kaynak": kaynaklar,
                "dogrulama_yontemi": DOGRULAMA_YONTEMI,
                "uretim_komutu": URETIM_KOMUTU,
                "referanslar": sorted(
                    ([KAYNAK_QURSIM] if c in qursim else []) + ([KAYNAK_ILM] if c in ilm else [])
                ),
                **o,
            }
        )
    return ornekler


def taslak(qursim_surum: str, ilm_surum: str, sayilar: Mapping[str, object]) -> dict[str, object]:
    return {
        "sinif": "altin",
        "olcum_turu": "dogruluk",
        "kaynak": [
            {
                "source_id": KAYNAK_QURSIM,
                "surum": qursim_surum,
                "madde": "QurSim_filtered.csv (SS, SV, TS, TV, Label)",
                "rol": "kanit",
            },
            {
                "source_id": KAYNAK_ILM,
                "surum": ilm_surum,
                "madde": "qul/matching-ayah.json",
                "rol": "kanit",
            },
        ],
        "referans_siniflari": {KAYNAK_QURSIM: "altin", KAYNAK_ILM: "silver"},
        "dogrulama_yontemi": DOGRULAMA_YONTEMI,
        "uretim_komutu": URETIM_KOMUTU,
        "tohum": setler.VARSAYILAN_TOHUM,
        "label_notu": (
            "QurSim Label anlami dogrulanamadi: tum etiketler pozitif; Label'a bagli esik yok."
        ),
        "kapsam_notu": "Referanslar tam kapsamli degildir; dusuk kesinlik 'yanlis' demek degildir.",
        "ozet_sayilar": dict(sayilar),
    }


# --- olculen satirlar --------------------------------------------------------------------

SORGU_SATIRLAR: Final = (
    "SELECT src_anchor, dst_anchor, evidence FROM icerik.xref"
    " WHERE type = 'benzer_ayet' AND origin = 'hat' ORDER BY src_anchor, dst_anchor"
)


def ayet_sirasi_oku(conn: psycopg.Connection) -> dict[str, int]:
    return {
        f"q:{int(s)}:{int(a)}": int(i)
        for s, a, i in conn.execute(
            "SELECT DISTINCT surah, ayah, ayah_index FROM icerik.quran_word"
        ).fetchall()
    }


def satirlari_oku(
    conn: psycopg.Connection, ayet_sirasi: Mapping[str, int]
) -> tuple[list[CiftAnahtari], dict[str, int], set[str]]:
    """Olculen satirlar (`(lo, hi)`), olculmeyen sayaclari ve olculenlerin uretim kaynaklari."""
    olculen: list[CiftAnahtari] = []
    sayac: Counter[str] = Counter()
    kaynaklar: set[str] = set()
    for src, dst, kanit in conn.execute(SORGU_SATIRLAR).fetchall():
        sayac["toplam"] += 1
        k = kanit if isinstance(kanit, dict) else {}
        if k.get("subtype") != "sozluksel":
            sayac["olculmeyen_alim_qursim_kaynakli"] += 1
            continue
        if "qursim" in k or k.get("dongusel"):
            sayac["olculmeyen_dongusel_sozluksel_qursim_ortak"] += 1
            continue
        a, b = ayet_sirasi.get(str(src)), ayet_sirasi.get(str(dst))
        if a is None or b is None:
            raise GirdiHatasi("benzer_ayet satirinin ayeti veritabaninda yok")
        olculen.append(cift(a, b))
        kaynaklar.add(str(k.get("source_id")))
    sayac["olculen"] = len(olculen)
    return olculen, dict(sayac), kaynaklar


def benzer_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    olculen: Sequence[CiftAnahtari],
    sayaclar: Mapping[str, int],
    uretim_kaynaklari: set[str],
    ayet_capasi: Mapping[int, str],
    literal_filtre: Sequence[CiftAnahtari] = (),
) -> TurSonucu:
    setler.manifest_dongusellik_denetle(manifest, uretim_kaynaklari)
    qursim: dict[CiftAnahtari, int] = {}
    ilm: set[CiftAnahtari] = set()
    ters = {v: k for k, v in ayet_capasi.items()}
    for o in ornekler:
        a, b = str(o["id"]).split("|")
        c = cift(ters[a], ters[b])
        if "qursim_label" in o:
            qursim[c] = int(str(o["qursim_label"]))
        if "ilm_eslesen_kelime" in o:
            ilm.add(c)
    tohum = int(str(manifest["tohum"]))

    def bolme_ad(c: CiftAnahtari) -> str:
        return setler.bolme("benzer-ayet", f"{ayet_capasi[c[0]]}|{ayet_capasi[c[1]]}", tohum)

    def oran(sec: Sequence[CiftAnahtari], ref: set[CiftAnahtari]) -> dict[str, object]:
        n = len(sec)
        dogru = sum(1 for c in sec if c in ref)
        sonuc: dict[str, object] = {"olculen": n, "referansta": dogru, "referansta_yok": n - dogru}
        sonuc["kesinlik"] = round(dogru / n, 6) if n else None
        if n:
            sonuc["kesinlik_wilson_alt_95"] = round(1.0 - wilson_ust_sinir(n - dogru, n), 6)
            sonuc["kesinlik_wilson_ust_95"] = round(1.0 - wilson_alt_sinir(n - dogru, n), 6)
        return sonuc

    donduruldu = [c for c in olculen if bolme_ad(c) == setler.DONDURULMUS]
    gelistirme = [c for c in olculen if bolme_ad(c) == setler.GELISTIRME]
    q_kume = set(qursim)
    ilm_kume = set(ilm)
    birlesim = q_kume | ilm_kume
    label_kirilim: dict[str, object] = {}
    for ad, etiketler in (
        ("label_0", {0}),
        ("label_1", {1}),
        ("label_2", {2}),
        ("label_1_2", {1, 2}),
    ):
        label_kirilim[ad] = oran(donduruldu, {c for c, lb in qursim.items() if lb in etiketler})
    kapi = oran(donduruldu, q_kume)
    kesinlik = float(str(kapi["kesinlik"])) if kapi["kesinlik"] is not None else 0.0
    olculer = {"kesinlik": kesinlik}
    esikler = dict(ESIKLER["benzer_ayet"])
    sonuc = kapi_karari(esikler, olculer)
    referansta_yok = len(donduruldu) - int(str(kapi["referansta"]))
    return TurSonucu(
        cli_tur="benzer-ayet",
        manifest=manifest,
        sonuc=sonuc,
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=esik_degerlendir(esikler, olculer),
        tahmin_ozeti=tahmin_ozeti(
            [f"{ayet_capasi[a]}|{ayet_capasi[b]}" for a, b in sorted(olculen)]
        ),
        olculen_ornek=len(donduruldu),
        ayrintilar={
            "kapi_qursim_dondurulmus": kapi,
            "ilm_silver_dondurulmus_bilgi": oran(donduruldu, ilm_kume),
            "birlesim_dondurulmus_bilgi": oran(donduruldu, birlesim),
            "literal_veritabani_filtresi_bilgi": {
                **oran(list(literal_filtre), q_kume),
                "not": (
                    "subtype=sozluksel ve qursim/dongusel yok: uretim birlestirmesi geregi QurSim"
                    " ciftleriyle tanim geregi ayrik; yapisal olarak 0, olcum degil"
                ),
            },
            "qursim_gelistirme_bilgi": oran(gelistirme, q_kume),
            "qursim_tum_olculen_bilgi": oran(list(olculen), q_kume),
            "ilm_tum_olculen_bilgi": oran(list(olculen), ilm_kume),
            "birlesim_tum_olculen_bilgi": oran(list(olculen), birlesim),
            "qursim_label_kirilimi_bilgi_dondurulmus": label_kirilim,
            "qursim_label_dagilimi": dict(
                sorted(Counter(str(lb) for lb in qursim.values()).items())
            ),
            "referans_cift_sayilari": {
                "qursim": len(q_kume),
                "ilm": len(ilm_kume),
                "kesisim": len(q_kume & ilm_kume),
                "birlesim": len(birlesim),
            },
            "olculen_satirlar": dict(sorted(sayaclar.items())),
        },
        notlar=[
            (
                "Referanslar tam kapsamli degildir: dusuk kesinlik yanlis demek degildir "
                "(referansta "
                "olmayan satir olculmemistir)."
            ),
            (
                "QurSim Label anlami dogrulanamadi: tum etiketler pozitif sayildi; Label kirilimi "
                "bilgidir."
            ),
            (
                "Olculen: yalniz kendi sozluksel satirlarimiz; QurSim kaynakli satirlar QurSim ile "
                "olculmez (dongusellik)."
            ),
            (
                "Kapi QurSim (altin) ile dondurulmus parcada olculur; ilm (silver) ve birlesim "
                "bilgidir."
            ),
        ],
        referans_kapsami={
            "olculen_satirlar_toplam": sum(1 for _ in olculen),
            "dondurulmus_referansta_olmayan": referansta_yok,
            "olculmeyen_satirlar": {
                k: v for k, v in sorted(sayaclar.items()) if k.startswith("olculmeyen")
            },
            "not": (
                "Referansta bulunmayan satirlar ayri sayildi; bunlarin hicbiri 'yanlis' ilan "
                "edilmedi."
            ),
        },
        uretim_kaynaklari=sorted(uretim_kaynaklari),
    )


def ozet_sha(baytlar: bytes) -> str:
    return hashlib.sha256(baytlar).hexdigest()


def qursim_cifti_oku(
    yol: Path, ayet_sirasi: Mapping[str, int]
) -> tuple[dict[CiftAnahtari, int], dict[str, int]]:
    """QurSim ciftleri ve okuma sayaclari (A18.3 okuyucusu; metin sutunlari okunmaz)."""
    s = qursim_oku(yol, ayet_sirasi)
    return dict(s.ciftler), {
        "satir": s.satir,
        "gecerli_tekil_cift": s.gecerli,
        "gecersiz": s.gecersiz_toplam,
        "yinelenen": s.yinelenen,
    }
