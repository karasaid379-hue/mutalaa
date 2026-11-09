"""Sure adi adaylarinin uretimi (A11.3, K-43 madde 4-5): saf islevler, dosya/veritabani yok.

Girdi: Vikipedi tablosu (`TabloSatiri`), tablo madde basliklarinin yonlendirmeleri
(`Yonlendirme`), `quran-meta` `surah.tr` girdileri (`MetaSatiri`) ve Tanzil ust veri sure
satirlari (`tname`, `ad_ar`, `type`, `order`, `ayas`). Cikti: her sure icin aday satirlari.

Sure adi ELLE yazilmaz: adlarin hepsi kaynak dosyalardan gelir; kural uretimi yalniz bicim
donusumudur (sapka kaldirma, noktali/noktasiz harf degisimi, "Sure-i X", "X Suresi",
"Suretu'l-X", Arapca "sure" oneki; onek ve ek metinleri modul sabitleridir).

Birlestirme (K-43 madde 5): bir surede ayni `alias_key` degerini veren butun yazimlar TEK adaydir.
Gorunen yazim kaynak onceligiyle secilir: Vikipedi tablosu (0), Vikipedi madde basligi ve
yonlendirmeleri (1), `quran-meta` (2), Tanzil `tname` (3), kural uretimi (4); ayni oncelikte
once gelen. Ote yazimlar `onerilen.yazimlar` icindedir. `kind` rol temellidir:

* `arapca`: Arapca yazim (Tanzil `ad_ar` ve "sure" onekli bicim);
* `kanonik`: anahtari tablodaki gorunen adin anahtariyla ayni olan aday (surede tam bir);
* `yazim`: anahtari kanonik adin kural biciminden (Sure-i X, X Suresi, Suretu'l-X) biri olan aday;
* `diger_ad`: oteki (yonlendirme, quran-meta, Tanzil Latin yazimi: baska ad ya da farkli yazim).

`alias_key`: Turkce adlar icin A05 genis anahtari (`normalize_tr(.., "genis")`), Arapca adlar icin
A05 `normalize_ar` (genis anahtar Arapca harfleri Turkce parca saymaz ve bos doner).

`risky` (Iktibas tespiti §2): riskli ad listesinin anahtarini veren Turkce aday `true`.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.sure_adlari import (
    KAYNAK,
    QURAN_META,
    MetaSatiri,
    TabloSatiri,
    Yonlendirme,
)
from mutalaa_pipeline.normalize import normalize_ar, normalize_tr

RISKLI_ADLAR_YOLU: Final = Path(__file__).resolve().parent.parent / "ingest" / "riskli_adlar.txt"
TANZIL_KAYNAGI: Final = "tanzil-ust-veri"
ONCELIK_TABLO: Final = 0
ONCELIK_BASLIK: Final = 1
ONCELIK_QURAN_META: Final = 2
ONCELIK_TANZIL: Final = 3
ONCELIK_KURAL: Final = 4

# Kural uretiminin sabit metinleri (sure adi degil, bicim parcalaridir); kaynak ASCII kalsin diye
# chr() ile: U+00FB (u sapkali), U+00FC (u umlautlu), Arapca "sure" sozcugu (U+0633 U+0648 U+0631
# U+0629) ve bosluk.
SURE_I: Final = "S" + chr(0xFB) + "re-i "
SURESI: Final = " S" + chr(0xFB) + "resi"
SURETUL: Final = "S" + chr(0xFB) + "ret" + chr(0xFC) + "'l-"
ARAPCA_ONEK: Final = "".join(chr(k) for k in (0x633, 0x648, 0x631, 0x629)) + " "


def _sure_i(ad: str) -> str:
    return SURE_I + ad


def _suresi(ad: str) -> str:
    return ad + SURESI


def _suretul(ad: str) -> str:
    return SURETUL + ad


def _ad(ad: str) -> str:
    return ad


KURAL_BICIMLERI: Final = (
    ("sure-i", _sure_i),
    ("suresi", _suresi),
    ("suretul", _suretul),
)
# Sapkali harf -> sapkasiz (acik eslesme; `lower()` kullanilmaz): a, A, i, buyuk noktali I, u, U.
SAPKA_ESLEME: Final = {
    0x00E2: 0x61,
    0x00C2: 0x41,
    0x00EE: 0x69,
    0x00CE: 0x0130,
    0x00FB: 0x75,
    0x00DB: 0x55,
}
# Noktali/noktasiz i degisimleri (OCR hatalari icin); her biri yalniz kaynak harf varsa uygulanir.
# 0x0130 noktali buyuk I, 0x49 buyuk I, 0x69 i, 0x0131 noktasiz kucuk i.
NOKTA_ESLEMELERI: Final = (
    ("noktasiz-buyuk", {0x0130: 0x49}),
    ("noktali-buyuk", {0x0049: 0x0130}),
    ("noktasiz-kucuk", {0x0069: 0x0131}),
    ("noktali-kucuk", {0x0131: 0x69}),
)
YER_ESLEME: Final = {"Mekke": "Meccan", "Medine": "Medinan"}  # Vikipedi -> Tanzil `type` etiketi
KIND_SIRASI: Final = {"kanonik": 0, "yazim": 1, "diger_ad": 2, "arapca": 3}


def alias_anahtari(metin: str, arapca: bool) -> str:
    """A05 genis anahtari (Turkce) ya da `normalize_ar` (Arapca); bos cikarsa `GirdiHatasi`."""
    anahtar = normalize_ar(metin) if arapca else normalize_tr(metin, "genis")
    if anahtar == "":
        raise GirdiHatasi("alias_key bos cikti (ad harf icermiyor ya da yanlis yazi sistemi)")
    return anahtar


def sapkasiz(metin: str) -> str:
    """a/i/u uzerindeki sapkalari acik eslemeyle kaldirir."""
    return metin.translate(SAPKA_ESLEME)


def nokta_degisimleri(metin: str) -> list[str]:
    """Noktali/noktasiz i degisimleri; yalniz metni gercekten degistirenler, tekrarsiz."""
    sonuc: dict[str, None] = {}
    for _, esleme in NOKTA_ESLEMELERI:
        degisen = metin.translate(esleme)
        if degisen != metin:
            sonuc[degisen] = None
    return list(sonuc)


def kural_yazimlari(ad: str) -> list[tuple[str, str]]:
    """`ad`dan `(kural, metin)` ciftleri: sure-i/suresi/suretul bicimleri, sapkasiz ve nokta
    degisimleri. Kanonik ad kendisi de sapkasiz ve nokta degisimleriyle yer alir ("ad" kurali).
    """
    cikti: dict[str, str] = {}
    for kural, bicim in (("ad", _ad), *KURAL_BICIMLERI):
        taban = bicim(ad)
        for metin in (taban, sapkasiz(taban)):
            cikti.setdefault(metin, kural)
            for degisim in nokta_degisimleri(metin):
                cikti.setdefault(degisim, kural)
    return [(kural, metin) for metin, kural in cikti.items()]


# --- riskli adlar --------------------------------------------------------------------------


def riskli_adlari_oku(yol: Path | None = None) -> list[str]:
    """Veri dosyasindan riskli adlar (`#` satirlari ve bos satirlar atlanir); bos liste hata."""
    try:
        metin = (yol if yol is not None else RISKLI_ADLAR_YOLU).read_bytes().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        raise GirdiHatasi("riskli_adlar.txt okunamadi") from None
    if "\r" in metin or not metin.endswith("\n"):
        raise GirdiHatasi("riskli_adlar.txt: LF satir sonlari ve sonda satir sonu bekleniyor")
    adlar = [s for s in metin[:-1].split("\n") if s != "" and not s.startswith("#")]
    if not adlar or len(set(adlar)) != len(adlar):
        raise GirdiHatasi("riskli_adlar.txt: bos ya da yinelenen ad")
    return adlar


# --- aday uretimi -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Gozlem:
    """Bir kaynakta gorulen yazim."""

    metin: str
    oncelik: int
    sira: int
    kaynak: Mapping[str, object]


@dataclass(frozen=True)
class SureGirdisi:
    """Bir surenin kaynak satirlari."""

    no: int
    tablo: TabloSatiri
    yonlendirmeler: Sequence[Yonlendirme]
    meta: MetaSatiri
    tanzil: Mapping[str, object]  # sure.jsonl satiri: tname, ad_ar, type, order, ayas, no


@dataclass
class _Grup:
    anahtar: str
    arapca: bool
    gozlemler: list[Gozlem] = field(default_factory=list)


def tanzil_farki(tablo: TabloSatiri, tanzil: Mapping[str, object]) -> dict[str, object] | None:
    """Vikipedi'nin ayet sayisi, inis yeri ve inis sirasi Tanzil ile ayni mi; farkli alanlar."""
    alanlar: list[str] = []
    if tablo.ayas != tanzil["ayas"]:
        alanlar.append("ayet")
    if YER_ESLEME.get(tablo.yer) != tanzil["type"]:
        alanlar.append("yer")
    if tablo.inis != tanzil["order"]:
        alanlar.append("inis_sirasi")
    if not alanlar:
        return None
    return {
        "alanlar": alanlar,
        "vikipedi": {"ayet": tablo.ayas, "yer": tablo.yer, "inis_sirasi": tablo.inis},
        "tanzil": {"ayet": tanzil["ayas"], "yer": tanzil["type"], "inis_sirasi": tanzil["order"]},
    }


def _gozlemler(g: SureGirdisi) -> list[Gozlem]:
    t = g.tablo
    sira = 0
    gozlemler: list[Gozlem] = []

    def ekle(metin: str, oncelik: int, kaynak: Mapping[str, object]) -> None:
        nonlocal sira
        sira += 1
        gozlemler.append(Gozlem(metin, oncelik, sira, kaynak))

    ekle(
        t.ad,
        ONCELIK_TABLO,
        {"kaynak": KAYNAK, "dosya": "sureler-listesi.wikitext", "satir": t.satir},
    )
    ekle(
        t.baslik,
        ONCELIK_BASLIK,
        {"kaynak": KAYNAK, "dosya": "sureler-listesi.wikitext", "satir": t.satir, "alan": "baslik"},
    )
    for y in g.yonlendirmeler:
        ekle(y.baslik, ONCELIK_BASLIK, {"kaynak": KAYNAK, "dosya": y.dosya, "yol": y.yol})
    ekle(
        g.meta.ad,
        ONCELIK_QURAN_META,
        {"kaynak": QURAN_META, "dosya": "surah.tr", "satir": g.meta.satir},
    )
    tanzil_kaynak = {"kaynak": TANZIL_KAYNAGI, "dosya": "sure.jsonl", "satir": g.no}
    ekle(str(g.tanzil["tname"]), ONCELIK_TANZIL, {**tanzil_kaynak, "alan": "tname"})
    for kural, metin in kural_yazimlari(t.ad):
        ekle(metin, ONCELIK_KURAL, {"kaynak": "kural", "kural": kural})
    return gozlemler


def _arapca_gozlemler(g: SureGirdisi) -> list[Gozlem]:
    ad_ar = str(g.tanzil["ad_ar"])
    tanzil_kaynak = {"kaynak": TANZIL_KAYNAGI, "dosya": "sure.jsonl", "satir": g.no}
    return [
        Gozlem(ad_ar, ONCELIK_TANZIL, 1, {**tanzil_kaynak, "alan": "ad_ar"}),
        Gozlem(ARAPCA_ONEK + ad_ar, ONCELIK_KURAL, 2, {"kaynak": "kural", "kural": "arapca-onek"}),
    ]


def sure_adaylari(g: SureGirdisi, riskli_anahtarlar: frozenset[str]) -> list[dict[str, object]]:
    """Bir surenin aday satirlari (kanonik, yazim, diger_ad, arapca)."""
    kanonik_anahtar = alias_anahtari(g.tablo.ad, False)
    kural_anahtarlari = {
        alias_anahtari(metin, False)
        for kural, metin in kural_yazimlari(g.tablo.ad)
        if kural != "ad"
    }
    gruplar: dict[tuple[bool, str], _Grup] = {}
    for arapca, gozlemler in ((False, _gozlemler(g)), (True, _arapca_gozlemler(g))):
        for o in gozlemler:
            anahtar = alias_anahtari(o.metin, arapca)
            grup = gruplar.setdefault((arapca, anahtar), _Grup(anahtar, arapca))
            grup.gozlemler.append(o)
    fark = tanzil_farki(g.tablo, g.tanzil)
    adaylar: list[dict[str, object]] = []
    for grup in gruplar.values():
        sirali = sorted(grup.gozlemler, key=lambda o: (o.oncelik, o.sira))
        gorunen = sirali[0].metin
        yazimlar = list(dict.fromkeys(o.metin for o in sirali if o.metin != gorunen))
        if grup.arapca:
            kind = "arapca"
        elif grup.anahtar == kanonik_anahtar:
            kind = "kanonik"
        elif grup.anahtar in kural_anahtarlari:
            kind = "yazim"
        else:
            kind = "diger_ad"
        risky = (not grup.arapca) and grup.anahtar in riskli_anahtarlar
        onerilen: dict[str, object] = {
            "kind": kind,
            "alias": gorunen,
            "risky": risky,
            "kaynaklar": [dict(o.kaynak) for o in sirali],
        }
        if kind == "kanonik":
            onerilen["anlam"] = g.tablo.anlam
            if fark is not None:
                onerilen["tanzil_fark"] = fark
        onerilen["yazimlar"] = yazimlar
        adaylar.append(
            {
                "surah_no": g.no,
                "alias": gorunen,
                "alias_key": grup.anahtar,
                "kind": kind,
                "risky": risky,
                "status": "aday",
                "onerilen": onerilen,
            }
        )
    return sorted(adaylar, key=lambda a: (KIND_SIRASI[str(a["kind"])], str(a["alias"])))


def adaylari_uret(
    tablo: Sequence[TabloSatiri],
    yonlendirmeler: Iterable[Yonlendirme],
    meta: Sequence[MetaSatiri],
    tanzil: Sequence[Mapping[str, object]],
    riskli_adlar: Sequence[str],
) -> list[dict[str, object]]:
    """114 surenin butun adaylari, `(surah_no, alias)` sirasinda.

    Girdi uzunluklari ve numaralar eslesmeli (1..N kesintisiz) aksi halde `GirdiHatasi`.
    Tum riskli ad anahtarlari hesaplanir; eslesme sayisi QA'da (`riskli_eslesme`) denetlenir.
    """
    n = len(tablo)
    if not (len(meta) == len(tanzil) == n) or [t.no for t in tablo] != list(range(1, n + 1)):
        raise GirdiHatasi("sure adi girdileri ayni uzunlukta ve 1..N kesintisiz degil")
    if [m.no for m in meta] != list(range(1, n + 1)):
        raise GirdiHatasi("quran-meta numaralari 1..N kesintisiz degil")
    if [t["no"] for t in tanzil] != list(range(1, n + 1)):
        raise GirdiHatasi("Tanzil sure numaralari 1..N kesintisiz degil")
    yonlendirme_haritasi: dict[int, list[Yonlendirme]] = {}
    for y in yonlendirmeler:
        yonlendirme_haritasi.setdefault(y.no, []).append(y)
    riskli_anahtarlar = frozenset(alias_anahtari(ad, False) for ad in riskli_adlar)
    hepsi: list[dict[str, object]] = []
    for i in range(n):
        girdi = SureGirdisi(
            no=i + 1,
            tablo=tablo[i],
            yonlendirmeler=yonlendirme_haritasi.get(i + 1, ()),
            meta=meta[i],
            tanzil=tanzil[i],
        )
        hepsi += sure_adaylari(girdi, riskli_anahtarlar)
    return sorted(hepsi, key=lambda a: (int(str(a["surah_no"])), str(a["alias"])))


def riskli_eslesme(
    adaylar: Iterable[Mapping[str, object]], riskli_adlar: Sequence[str]
) -> dict[str, list[int]]:
    """Her riskli ad icin anahtarini veren (Turkce) aday satirlarinin sure numaralari."""
    sonuc: dict[str, list[int]] = {}
    turkce = [a for a in adaylar if a["kind"] != "arapca"]
    for ad in riskli_adlar:
        anahtar = alias_anahtari(ad, False)
        sonuc[ad] = sorted({int(str(a["surah_no"])) for a in turkce if a["alias_key"] == anahtar})
    return sonuc


def capraz_sure_cakismalari(adaylar: Iterable[Mapping[str, object]]) -> dict[str, list[int]]:
    """Birden fazla surede ayni `alias_key` degerini veren (Turkce) anahtarlar -> sure numaralari.

    Ayni surede ayni anahtar zaten tek adaydir; burada farkli surelerin anahtari cakisir
    (A05 genis anahtari kesme isaretinden sonrasini ek sayar: `A'raf` -> `a`).
    """
    anahtar_sureler: dict[str, set[int]] = {}
    for a in adaylar:
        if a["kind"] == "arapca":
            continue
        anahtar_sureler.setdefault(str(a["alias_key"]), set()).add(int(str(a["surah_no"])))
    return {k: sorted(v) for k, v in sorted(anahtar_sureler.items()) if len(v) > 1}
