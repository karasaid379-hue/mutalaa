"""`mutalaa qa sample`: ikinci okuma orneklemi ve G-INC olcum raporu (A16.7, K-49 madde 12).

Yalniz iki meal kaynagi (`elmalili-meal`, `elmalili-sade-meal`; baska kimlik cikis 2).
Veritabanindan YALNIZ OKUR (`read_only` baglanti; hicbir satir yazilmaz) ve `data/reports/`
altina rapor yazar.
G-INC `qa run` kapisi DEGILDIR: sonuc yalniz bu raporda durur (Icerik hatti §9; A34 `public`
kurali bunu okur).

ORNEKLEM (tur 2, BÇ-08): evren, kaynagin birlesik izleyen OLMAYAN meal birimleridir (izleyen birim
kendi metnini tasimaz; `--onayli` verilirse yalniz `metin_durumu = 'onayli'`). Sure numarasi
mushaf sirasinda ardisik `GRUP_SAYISI` gruba bolunur: gruplarin toplam ayet sayilari birbirine
en yakin olacak sekilde (kumulatif ayet sayisinin `6236 * k / GRUP_SAYISI` degerlerine en yakin
sure sinirlari). Her gruba `n` orantili (en buyuk kalan yontemi) dagitilir; grup icinde birimler
`sha256("{tohum}|{capa}")` ozetine gore siralanir ve ilk `k` tanesi secilir. Boylece ayni tohum
ve ayni evren her zaman ayni capa listesini verir (uretec surumune bagli degildir).
Cilt tabakasi tarama ile birlikte S-15'e kalir.

CIKTI: `{run_id}-qa-sample.json` (tohum, n, grup tanimlari ve dagilimi, capa listesi, ozet, G-INC
bolumu) ve `{run_id}-ikinci-okuma.jsonl` (her capa icin `{"capa", "karar": null, "not": null}`
satiri; ikinci okuyucu `karar`i `dogru` ya da `hata` yapar). Raporlar META METIN ICERMEZ: yalniz
capa, sayi ve ozet. `--dry-run` bu iki dosyayi yazmaz.

G-INC OLCUMU: kaynak basina birim sayisi, durum dagilimi, onayli ve ikinci onayli (`review`'da
`ikinci_inceleyen` dolu, `onaylandi`) birim sayisi, acik hat ve acik toplam inceleme sayisi; tur 2
icin okunan `n` ve hatali ayet sayisi `k` (CLI'dan ya da doldurulmus sablondan) ve hatali ayet orani
icin %95 guvenle TEK YANLI USTSINIR: Clopper-Pearson (tam iki terimli) `p_ust`, `P(X <= k | n, p) =
0,05` denkleminin cozumu (ikiye bolme). Kapi gecer: butun birimler onayli VE okunan >= 600 VE
`p_ust < 0,005`. Hic hata yokken `n = 600` icin `p_ust ~ 0,004980` olur (kaba `3 / n` = 0,005).
"""

import hashlib
import json
import math
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import cikis, lineage
from mutalaa_pipeline.anchor import Meal, parse
from mutalaa_pipeline.anchor.ayet_sayilari import AYET_SAYILARI
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.db import baglan
from mutalaa_pipeline.export.ortak import GirdiHatasi, kati_json
from mutalaa_pipeline.ingest import meal_kaynaklari as kayitlar
from mutalaa_pipeline.komut_ortak import komutu_yurut
from mutalaa_pipeline.logs import json_baytlari
from mutalaa_pipeline.runctx import RAPOR_KLASORU, RunContext

SAMPLE_KOMUTU: Final = "qa sample"
GRUP_SAYISI: Final = 6
VARSAYILAN_N: Final = 600
ESIK_ORAN: Final = 0.005  # K-49 madde 12: hatali ayet orani < %0,5
GUVEN: Final = 0.95  # tek yanli
EN_AZ_OKUNAN: Final = 600
YONTEM: Final = "Clopper-Pearson tek yanli ust sinir (tam iki terimli), %95"
RAPOR_SONEKI: Final = "-qa-sample"
SABLON_SONEKI: Final = "-ikinci-okuma"
KARARLAR: Final = frozenset({"dogru", "hata"})
BaglantiUretici = Callable[[], psycopg.Connection]


# --- hesap ---------------------------------------------------------------------------------


def _iki_terimli_cdf(k: int, n: int, p: float) -> float:
    """`P(X <= k)`, `X ~ Binom(n, p)`; log uzayinda (tasma yok)."""
    if p <= 0.0:
        return 1.0
    if p >= 1.0:
        return 1.0 if k >= n else 0.0
    log_p, log_q = math.log(p), math.log1p(-p)
    govde = [
        math.lgamma(n + 1)
        - math.lgamma(i + 1)
        - math.lgamma(n - i + 1)
        + i * log_p
        + (n - i) * log_q
        for i in range(k + 1)
    ]
    en_buyuk = max(govde)
    return min(1.0, math.exp(en_buyuk) * sum(math.exp(g - en_buyuk) for g in govde))


def clopper_pearson_ust(hata: int, n: int, guven: float = GUVEN) -> float:
    """Tek yanli `guven` duzeyinde hata orani ust siniri: `P(X <= hata | n, p) = 1 - guven` kokuu.

    `hata == n` icin 1,0. `n > 0` ve `0 <= hata <= n` olmali.
    """
    if n <= 0 or not 0 <= hata <= n:
        raise GirdiHatasi("olcum icin n > 0 ve 0 <= hata <= n olmali")
    if hata == n:
        return 1.0
    alt, ust = hata / n, 1.0
    for _ in range(200):
        orta = (alt + ust) / 2
        if _iki_terimli_cdf(hata, n, orta) > 1.0 - guven:
            alt = orta
        else:
            ust = orta
    return (alt + ust) / 2


def sure_gruplari(grup_sayisi: int = GRUP_SAYISI) -> list[tuple[int, int]]:
    """Mushaf sirasinda ardisik sure gruplari `(ilk, son)`; toplam ayet sayilari birbirine yakin.

    k. grubun son suresi, kumulatif ayet sayisi `toplam * k / grup_sayisi` degerine en yakin olan
    suredir (esitlikte kucuk sure numarasi); sinirlar kesin artandir.
    """
    kumulatif = [0]
    for adet in AYET_SAYILARI:
        kumulatif.append(kumulatif[-1] + adet)  # kumulatif[s] = 1..s. surelerin ayet toplami
    toplam = kumulatif[-1]
    sinirlar: list[int] = []
    for k in range(1, grup_sayisi):
        hedef = toplam * k / grup_sayisi
        en_yakin = min(range(1, 115), key=lambda s: (abs(kumulatif[s] - hedef), s))
        if sinirlar and en_yakin <= sinirlar[-1]:
            en_yakin = sinirlar[-1] + 1
        sinirlar.append(en_yakin)
    ilk = 1
    gruplar: list[tuple[int, int]] = []
    for son in (*sinirlar, 114):
        gruplar.append((ilk, son))
        ilk = son + 1
    return gruplar


def orantili_dagit(agirliklar: Sequence[int], n: int) -> list[int]:
    """`n` ogeyi agirliklarla orantili dagitir (en buyuk kalan yontemi); toplam tam `n`."""
    toplam = sum(agirliklar)
    if toplam <= 0 or n < 0:
        raise GirdiHatasi("dagitim icin pozitif agirlik ve n >= 0 gerekir")
    taban = [n * a // toplam for a in agirliklar]
    kalan = sorted(range(len(agirliklar)), key=lambda i: (-(n * agirliklar[i] % toplam), i))
    for i in kalan[: n - sum(taban)]:
        taban[i] += 1
    return taban


def _anahtar(tohum: int, capa: str) -> str:
    return hashlib.sha256(f"{tohum}|{capa}".encode()).hexdigest()


def ornekle(
    evren: Sequence[tuple[str, int]], n: int, tohum: int
) -> tuple[list[tuple[int, int]], list[int], list[str]]:
    """`evren`: `(capa, sure)` ciftleri. Donus: gruplar, grup basina dagitim, secilen capalar.

    Secilen capalar evren sirasinda (okuma sirasi) doner. Bir grubun evreni dagitimdan kucukse
    `GirdiHatasi`.
    """
    gruplar = sure_gruplari()
    kovalar: list[list[str]] = [[] for _ in gruplar]
    for capa, sure in evren:
        for i, (ilk, son) in enumerate(gruplar):
            if ilk <= sure <= son:
                kovalar[i].append(capa)
                break
    if n <= 0 or n > sum(len(k) for k in kovalar):
        raise GirdiHatasi("--n 1 ile evren buyuklugu arasinda olmali")
    dagitim = orantili_dagit([len(k) for k in kovalar], n)
    secilen: set[str] = set()
    for kova, adet in zip(kovalar, dagitim, strict=True):
        if adet > len(kova):
            raise GirdiHatasi("grup evreni dagitimdan kucuk (n cok buyuk)")
        secilen.update(sorted(kova, key=lambda c: _anahtar(tohum, c))[:adet])
    sirali = [capa for capa, _ in evren if capa in secilen]
    return gruplar, dagitim, sirali


# --- veritabani (yalniz SELECT) --------------------------------------------------------------


def evren_oku(conn: psycopg.Connection, slug: str, yalniz_onayli: bool) -> list[tuple[str, int]]:
    """Birlesik izleyen OLMAYAN meal birimlerinin `(capa, sure)` listesi, `ord` sirasinda."""
    kosul = " AND metin_durumu = 'onayli'" if yalniz_onayli else ""
    satirlar = conn.execute(
        "SELECT anchor FROM icerik.unit WHERE source_id = %s AND kind = 'meal'"
        " AND NOT (attrs ? 'birlesik_ile')" + kosul + " ORDER BY ord",
        (slug,),
    ).fetchall()
    sonuc: list[tuple[str, int]] = []
    for (capa,) in satirlar:
        cozulen = parse(str(capa)).anchor
        if not isinstance(cozulen, Meal):
            raise GirdiHatasi("veritabanindaki meal capasi meal: capasi degil")
        sonuc.append((str(capa), cozulen.sure))
    return sonuc


def _say(conn: psycopg.Connection, sorgu: str, *param: object) -> int:
    satir = conn.execute(sorgu, param).fetchone()
    return int(satir[0]) if satir is not None else 0


def veritabani_olcumu(conn: psycopg.Connection, slug: str) -> dict[str, object]:
    """G-INC'in veritabani tarafi (yalniz sayilar)."""
    durumlar = {
        str(d): int(c)
        for d, c in conn.execute(
            "SELECT metin_durumu::text, count(*) FROM icerik.unit WHERE source_id = %s"
            " AND kind = 'meal' GROUP BY 1 ORDER BY 1",
            (slug,),
        ).fetchall()
    }
    birim = sum(durumlar.values())
    birimler = "icerik.unit u WHERE u.source_id = %s AND u.kind = 'meal'"
    inceleme = (
        "SELECT count(*) FROM icerik.review r JOIN icerik.unit u ON u.anchor = r.hedef_anahtar"
        " WHERE r.hedef_tablo = 'unit' AND r.alan = 'metin' AND u.source_id = %s"
    )
    return {
        "birim": birim,
        "birlesik_izleyen": _say(
            conn, "SELECT count(*) FROM " + birimler + " AND u.attrs ? 'birlesik_ile'", slug
        ),
        "durum_dagilimi": durumlar,
        "onayli": durumlar.get("onayli", 0),
        "ikinci_onayli": _say(
            conn,
            "SELECT count(DISTINCT r.hedef_anahtar) FROM icerik.review r JOIN icerik.unit u"
            " ON u.anchor = r.hedef_anahtar WHERE r.hedef_tablo = 'unit' AND r.alan = 'metin'"
            " AND u.source_id = %s AND r.durum = 'onaylandi' AND r.ikinci_inceleyen IS NOT NULL",
            slug,
        ),
        "acik_hat_inceleme": _say(
            conn, inceleme + " AND r.durum = 'acik' AND r.koken = 'hat'", slug
        ),
        "acik_inceleme": _say(conn, inceleme + " AND r.durum = 'acik'", slug),
        "tamami_onayli": birim > 0 and durumlar.get("onayli", 0) == birim,
    }


# --- tur 2 girdisi -----------------------------------------------------------------------------


def sablondan_say(yol: Path) -> tuple[int, int]:
    """Doldurulmus sablondan `(okunan, hatali)`; `karar` `dogru` ya da `hata`, bos okunmamis."""
    try:
        ham = yol.read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        raise GirdiHatasi("--sablon okunamadi (UTF-8 JSONL olmali)") from None
    okunan = hatali = 0
    gorulen: set[str] = set()
    for no, satir in enumerate(ham.split("\n"), start=1):
        if satir == "":
            continue
        nesne = kati_json(satir)
        if not isinstance(nesne, dict) or not isinstance(nesne.get("capa"), str):
            raise GirdiHatasi(f"--sablon satir {no}: capa yok")
        capa = str(nesne["capa"])
        if capa in gorulen:
            raise GirdiHatasi(f"--sablon satir {no}: yinelenen capa")
        gorulen.add(capa)
        karar = nesne.get("karar")
        if karar is None:
            continue
        if karar not in KARARLAR:
            raise GirdiHatasi(f"--sablon satir {no}: karar dogru ya da hata olmali")
        okunan += 1
        hatali += 1 if karar == "hata" else 0
    return okunan, hatali


def g_inc(olcum: Mapping[str, object], okunan: int | None, hatali: int | None) -> dict[str, object]:
    """G-INC sonucu (yalniz rapora yazilir; `qa run`a baglanmaz)."""
    tur2: dict[str, object]
    if okunan is None or hatali is None:
        tur2 = {"olculdu": False, "neden": "tur 2 sonucu (okunan, hatali) verilmedi"}
        gecti_tur2 = False
    else:
        ust = clopper_pearson_ust(hatali, okunan)
        gecti_tur2 = okunan >= EN_AZ_OKUNAN and ust < ESIK_ORAN
        tur2 = {
            "olculdu": True,
            "okunan": okunan,
            "hatali": hatali,
            "gozlenen_oran": round(hatali / okunan, 6),
            "ust_sinir_95": round(ust, 6),
            "yontem": YONTEM,
            "esik": ESIK_ORAN,
            "en_az_okunan": EN_AZ_OKUNAN,
            "gecti": gecti_tur2,
        }
    tamami = bool(olcum.get("tamami_onayli"))
    return {
        "tum_birimler_onayli": tamami,
        "tur2": tur2,
        "kapi": "gecti" if tamami and gecti_tur2 else "kaldi",
        "not": "G-INC qa run kapisi degildir; sonuc yalniz bu rapordadir (K-49 madde 12).",
    }


# --- komut -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class OrnekSonucu:
    rapor: dict[str, object]
    sablon: bytes
    capalar: list[str]
    dagilim: list[tuple[int, int]]  # grup basina (secilen, evren)
    g_inc_kapi: str


def ornek_kur(
    conn: psycopg.Connection,
    slug: str,
    n: int,
    tohum: int,
    *,
    yalniz_onayli: bool,
    okunan: int | None,
    hatali: int | None,
) -> OrnekSonucu:
    evren = evren_oku(conn, slug, yalniz_onayli)
    if not evren:
        raise GirdiHatasi("evren bos: kaynak icin uygun meal birimi yok")
    gruplar, dagitim, capalar = ornekle(evren, n, tohum)
    olcum = veritabani_olcumu(conn, slug)
    capa_sure = dict(evren)
    grup_dagilimi = [
        {
            "grup": i + 1,
            "sure_ilk": ilk,
            "sure_son": son,
            "evren": sum(1 for _, s in evren if ilk <= s <= son),
            "secilen": sum(1 for c in capalar if ilk <= capa_sure[c] <= son),
            "hedef": dagitim[i],
        }
        for i, (ilk, son) in enumerate(gruplar)
    ]
    rapor: dict[str, object] = {
        "kaynak": slug,
        "tohum": tohum,
        "n": n,
        "yalniz_onayli": yalniz_onayli,
        "yontem": "sure grubuna gore tabakali, orantili, sha256(tohum|capa) siralamasi",
        "cilt_tabakasi": "S-15",
        "evren": len(evren),
        "gruplar": grup_dagilimi,
        "capalar": capalar,
        "capalar_sha256": lineage.sha256_bayt("\n".join(capalar).encode("utf-8")),
        "veritabani": olcum,
        "g_inc": g_inc(olcum, okunan, hatali),
    }
    sablon = "".join(
        json_bayt_satiri({"capa": c, "karar": None, "not": None}) for c in capalar
    ).encode("utf-8")
    gi = g_inc(olcum, okunan, hatali)
    rapor["g_inc"] = gi
    return OrnekSonucu(
        rapor,
        sablon,
        capalar,
        [(int(str(g["secilen"])), int(str(g["evren"]))) for g in grup_dagilimi],
        str(gi["kapi"]),
    )


def json_bayt_satiri(nesne: Mapping[str, object]) -> str:
    return json.dumps(nesne, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"


def _yaz(ctx: RunContext, ad: str, veri: bytes) -> str:
    klasor = ctx.veri_kok / RAPOR_KLASORU
    klasor.mkdir(parents=True, exist_ok=True)
    hedef = klasor / ad
    gecici = klasor / (ad + ".tmp")
    gecici.write_bytes(veri)
    lineage.atomik_degistir(gecici, hedef)
    return lineage.goreli_yol(ctx.veri_kok, hedef)


def komut_qa_sample(
    *,
    source: str,
    n: int,
    seed: int,
    dry_run: bool,
    yalniz_onayli: bool,
    okunan: int | None,
    hatali: int | None,
    sablon: Path | None,
    config: Path | None,
    kok: Path | None,
    baglanti: BaglantiUretici | None = None,
    ayarlar: Ayarlar | None = None,
) -> int:
    """`qa sample` komutu; cikis kodu 0 ya da 2 (G-INC sonucu cikis kodunu etkilemez)."""

    def govde(ctx: RunContext) -> int:
        if not kayitlar.meal_mi(source):
            raise GirdiHatasi("qa sample yalniz elmalili-meal ve elmalili-sade-meal icindir")
        if (okunan is None) != (hatali is None):
            raise GirdiHatasi("--okunan ve --hatali birlikte verilmeli")
        if sablon is not None and okunan is not None:
            raise GirdiHatasi("--sablon ile --okunan/--hatali birlikte verilmez")
        if okunan is not None and hatali is not None and not 0 <= hatali <= okunan:
            raise GirdiHatasi("--hatali 0 ile --okunan arasinda olmali")
        o, h = okunan, hatali
        if sablon is not None:
            o, h = sablondan_say(sablon)
        kapat = baglanti is None
        conn = baglanti() if baglanti is not None else baglan(ayarlar or ctx.ayarlar)
        try:
            if kapat:  # kendi baglantimiz: yazma denemesi veritabaninca reddedilir
                conn.read_only = True
            sonuc = ornek_kur(
                conn, source, n, seed, yalniz_onayli=yalniz_onayli, okunan=o, hatali=h
            )
        finally:
            if kapat:
                conn.close()
        ctx.rapor_ek.update(
            kaynak=source,
            tohum=seed,
            n=n,
            capalar_sha256=sonuc.rapor["capalar_sha256"],
            g_inc_kapi=sonuc.g_inc_kapi,
        )
        if not dry_run:
            ctx.rapor_ek["ornek_raporu"] = _yaz(
                ctx, f"{ctx.run_id}{RAPOR_SONEKI}.json", json_baytlari(sonuc.rapor)
            )
            ctx.rapor_ek["ikinci_okuma_sablonu"] = _yaz(
                ctx, f"{ctx.run_id}{SABLON_SONEKI}.jsonl", sonuc.sablon
            )
        dagilim = ", ".join(f"{sec}/{evren}" for sec, evren in sonuc.dagilim)
        sys.stdout.write(
            f"qa sample {source}: {len(sonuc.capalar)} capa (tohum {seed}; grup secilen/evren:"
            f" {dagilim}){' [dry-run: dosya yazilmadi]' if dry_run else ''};"
            f" G-INC {sonuc.g_inc_kapi}\n"
        )
        return cikis.BASARILI

    parametreler: dict[str, object] = {
        "source": source,
        "n": n,
        "seed": seed,
        "yalniz_onayli": yalniz_onayli,
    }
    return komutu_yurut(
        komut=SAMPLE_KOMUTU,
        adim="qa",
        kaynaklar=[source],
        config=config,
        kok=kok,
        govde=govde,
        dry_run=dry_run,
        parametreler=parametreler,
    )
