"""RNK baski sayfa esleme QA kapilari (A20.3; K-52 madde 6 ve 7): `risale-baski-rnk`.

Kapi islevleri bellekteki `SayfaGirdisi` uzerinde calisir (`qa/run_risale_sayfa.py` yukler).
Bulgular ASCII ve kisadir: yalniz dosya (`raf/uid`), sayfa, sayi ve capa tasir; metin asla.

* G-KAY: kaynak kaydi gecerli (`slug`, `tur = baski`, `surum`, `kaynak_url`, `atif_metni`,
  `baski_bilgisi.yayinevi` dolu); manifestteki `data_version` kayittan uretilenle ayni.
* G-BUT: her satirin alan kumesi `page_map` sutunlaridir (metin tasimaz); satirlar zincirdeki
  `units.jsonl` ve `sayfalar.jsonl`den yeniden uretilince ayni (satir ve rapor); kitap basina
  sayfa sayisi kilitteki `#n` sayisiyla ayni, her sayfa tam bir satir (`icerik-yok` sayfa satir
  uretmez ve sayilir); sayfa numaralari +1 ardisik, ilk/son sayfa kilit ve json meta ile ayni;
  baslangic/bitis capalari `risale-rnk-metin` anchor ciktisinda ve ayni RNK dosyasindadir;
  ofsetler birim metnine sigar (`0 <= start_offset < uzunluk`, `0 <= end_offset <= uzunluk`);
  baslangic bitisten sonra degil; ardisik iki gercek satirda bitis, sonraki baslangicla bitisiktir
  (bosluk ve ust uste binme yok); son sayfa dosyanin son birim sonunda biter; `volume` cilt
  tablosundadir ve baslangic birimi o RNK dosyasindadir; bolum basi satirinin (tekil anahtar:
  gercek satirla ayni sayfada olamaz) baslangici bolumun baslik biriminin basidir.
* G-CAP: baslangic ve bitis capalari gramere uyan, kanonik, birim duzeyinde `rn:` capasidir ve
  kitabi `risale-kitaplar.json` tablosundadir; `(source_id, volume, page)` tekildir; `data_version`
  `risale-baski-rnk@{surum}` (bolum basinda `/bolum-basi`); onceki (kapilari gecmis) calismadaki her
  `(volume, page)` satiri durur ve capalari hala anchor ciktisindadir (satir silinmez).
* G-NOR: arama metni uretilmez; kapi uygulanmaz ve satirlarin metin tasimadigini sayar.
"""

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import pairwise
from pathlib import Path
from typing import Final

from mutalaa_pipeline import lineage
from mutalaa_pipeline.adimlar.risale import rn_yolu
from mutalaa_pipeline.adimlar.risale_sayfa import (
    BOLUM_BASI_EKI,
    KAYNAK,
    SATIR_ALANLARI,
    BirimKonumu,
    Konum,
    data_versiyonu,
)
from mutalaa_pipeline.anchor.risale import Kitap
from mutalaa_pipeline.enums import SourceKind
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.risale_kaynaklari import BASKI_KAPILARI
from mutalaa_pipeline.ingest.risale_rnk_kilit import RnkKilidi
from mutalaa_pipeline.qa.checks.tanzil import KapiSonucu
from mutalaa_pipeline.sources.kayit import Kaynak

EN_COK_ORNEK: Final = 5
EN_COK_ALAN_UZUNLUGU: Final = 256  # capa en uzun 256 karakter; hicbir alan metin tasimaz

Satir = Mapping[str, object]


@dataclass
class SayfaOnceki:
    """Onceki (kapilari gecmis) calismanin `(volume, page) -> (start_anchor, end_anchor)`."""

    run_id: str
    satirlar: Mapping[tuple[int, int], tuple[str, str]]


@dataclass
class SayfaGirdisi:
    kayit: Kaynak
    kilit: RnkKilidi
    manifest_data_version: str | None
    satirlar: Sequence[Satir]  # page_map.jsonl
    raporlar: Sequence[Satir]  # page_map_rapor.jsonl
    beklenen_satirlar: Sequence[Satir]  # zincirdeki iki dosyadan yeniden uretilen
    beklenen_raporlar: Sequence[Satir]
    birimler: Mapping[str, Sequence[BirimKonumu]]  # dosya (`raf/uid`) -> okuma sirasinda birimler
    sayfalar: Mapping[str, Sequence[Satir]]  # ingest sayfalar.jsonl: dosya -> sayfa kayitlari
    kitaplar: Sequence[Satir]  # ingest kitaplar.jsonl
    cilt: Mapping[str, int]  # `raf/uid` -> volume
    tablo: tuple[Kitap, ...]
    depo_kok: Path
    onceki: SayfaOnceki | None = None
    ek: dict[str, object] = field(default_factory=dict)


def _bulgu(bulgular: list[str], ad: str, liste: Sequence[str], neden: str) -> None:
    if liste:
        ornek = ", ".join(liste[:EN_COK_ORNEK])
        bulgular.append(f"{ad}: {len(liste)} {neden} (ornek: {ornek})")


def _tam(deger: object) -> int:
    if isinstance(deger, bool) or not isinstance(deger, int):
        raise GirdiHatasi("staged satir: tam sayi bekleniyor")
    return deger


def _metin(deger: object) -> str:
    if not isinstance(deger, str):
        raise GirdiHatasi("staged satir: metin bekleniyor")
    return deger


# --- G-KAY -------------------------------------------------------------------------------


def g_kay(g: SayfaGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    k = g.kayit
    if k.slug != KAYNAK:
        bulgular.append("kaynak kaydi: slug kaynak kimligiyle ayni degil")
    if k.tur is not SourceKind.BASKI:
        bulgular.append("kaynak kaydi: tur baski olmali")
    if k.surum is None or k.surum == "":
        bulgular.append("kaynak kaydi: surum yok")
    if k.kaynak_url is None:
        bulgular.append("kaynak kaydi: kaynak_url yok")
    if k.atif_metni.strip(" \t\n") == "":
        bulgular.append("kaynak kaydi: atif_metni bos")
    yayinevi = (k.baski_bilgisi or {}).get("yayinevi")
    if not isinstance(yayinevi, str) or yayinevi == "":
        bulgular.append("kaynak kaydi: baski_bilgisi.yayinevi bos")
    if k.surum and g.manifest_data_version != data_versiyonu(k.surum):
        bulgular.append(
            "manifest data_version kaynak kaydiyla ayni degil (anchor yeniden kosulmali)"
        )
    return KapiSonucu("G-KAY", tuple(bulgular), {"kayit": 1})


# --- G-BUT -------------------------------------------------------------------------------


@dataclass(frozen=True)
class _Dosya:
    ad: str
    indeks: Mapping[str, int]
    birimler: Sequence[BirimKonumu]


def _konum(d: _Dosya, capa: object, ofs: object) -> Konum | None:
    i = d.indeks.get(_metin(capa))
    return None if i is None else Konum(i, _tam(ofs))


def _bitis_normal(d: _Dosya, bit: Konum) -> Konum:
    """Birimin sonunda biten konum bir sonraki birimin basidir (bitisiklik karsilastirmasi)."""
    if bit.o == d.birimler[bit.r].uzunluk:
        return Konum(bit.r + 1, 0)
    return bit


def _ters_cilt(g: SayfaGirdisi) -> dict[int, str]:
    return {v: k for k, v in g.cilt.items()}


def g_but(g: SayfaGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    ters = _ters_cilt(g)
    if len(ters) != len(g.cilt):
        bulgular.append("cilt tablosu: iki dosya ayni volume numarasini tasiyor")
    alan_hatasi = [str(i + 1) for i, s in enumerate(g.satirlar) if set(s) != SATIR_ALANLARI]
    _bulgu(bulgular, "alan kumesi", alan_hatasi, "satir page_map sutunlarindan farkli alan tasiyor")
    if list(g.satirlar) != list(g.beklenen_satirlar):
        bulgular.append("page_map.jsonl zincirdeki girdilerden yeniden uretilince ayni degil")
    if list(g.raporlar) != list(g.beklenen_raporlar):
        bulgular.append("page_map_rapor.jsonl zincirdeki girdilerden yeniden uretilince ayni degil")

    dosyalar: dict[str, _Dosya] = {
        ad: _Dosya(ad, {b.capa: i for i, b in enumerate(liste)}, liste)
        for ad, liste in g.birimler.items()
    }
    gercek: dict[str, dict[int, Satir]] = defaultdict(dict)
    bolum_basi: dict[str, dict[int, Satir]] = defaultdict(dict)
    anahtarlar: set[tuple[int, int]] = set()
    sozluk: dict[str, list[str]] = defaultdict(list)
    for s in g.satirlar:
        if set(s) != SATIR_ALANLARI:
            continue
        volume, sayfa = _tam(s["volume"]), _tam(s["page"])
        yer = f"{ters.get(volume, 'volume ' + str(volume))}#{sayfa}"
        dosya = ters.get(volume)
        if dosya is None or dosya not in dosyalar:
            sozluk["volume cilt tablosunda yok"].append(yer)
            continue
        if (volume, sayfa) in anahtarlar:
            sozluk["yinelenen sayfa"].append(yer)
            continue
        anahtarlar.add((volume, sayfa))
        veri_surumu = _metin(s["data_version"])
        (bolum_basi if veri_surumu.endswith(BOLUM_BASI_EKI) else gercek)[dosya][sayfa] = s
        d = dosyalar[dosya]
        bas = _konum(d, s["start_anchor"], s["start_offset"])
        bit = _konum(d, s["end_anchor"], s["end_offset"])
        if bas is None or bit is None:
            sozluk["capa ayni dosyada degil"].append(yer)
            continue
        if (
            not 0 <= bas.o < d.birimler[bas.r].uzunluk
            or not 0 <= bit.o <= d.birimler[bit.r].uzunluk
        ):
            sozluk["ofset metne sigmiyor"].append(yer)
            continue
        if bit < bas:
            sozluk["bitis baslangictan once"].append(yer)

    # kitap basina sayfa sayilari ve ardisiklik
    rapor_satiri = {_metin(r["dosya"]): r for r in g.raporlar}
    kitap_json = {_metin(k["dosya"]): k for k in g.kitaplar}
    toplam_sayfa = toplam_gercek = toplam_yok = 0
    for ad, kitap in g.kilit.kitaplar.items():
        beklenen_sayfa = kitap.sayi("sayfa_sayisi")
        ingest_sayfalar = g.sayfalar.get(ad, ())
        yok = sum(1 for k in ingest_sayfalar if k["capa"] is None)
        satirlar_ = gercek.get(ad, {})
        toplam_sayfa += beklenen_sayfa
        toplam_gercek += len(satirlar_)
        toplam_yok += yok
        if len(ingest_sayfalar) != beklenen_sayfa:
            sozluk["sayfa sayisi ingest sayfalari kilitle farkli"].append(ad)
        if len(satirlar_) + yok != beklenen_sayfa:
            sozluk["sayfa sayisi satirlar kilitle farkli"].append(ad)
        beklenen_n = {_tam(k["n"]) for k in ingest_sayfalar if k["capa"] is not None}
        if set(satirlar_) != beklenen_n:
            sozluk["sayfa kumesi sayfalar.jsonl ile farkli"].append(ad)
        sirali = sorted(satirlar_)
        if any(b - a != 1 for a, b in pairwise(sirali)):
            sozluk["sayfa numaralari +1 ardisik degil"].append(ad)
        k = kitap_json.get(ad)
        if sirali and (
            sirali[0] != kitap.sayi("ilk_sayfa")
            or sirali[-1] != kitap.sayi("son_sayfa")
            or k is None
            or sirali[0] != k.get("json_ilk_sayfa")
            or sirali[-1] != k.get("json_son_sayfa")
        ):
            sozluk["ilk/son sayfa kilit ve json meta ile farkli"].append(ad)
        rapor = rapor_satiri.get(ad)
        if rapor is None or rapor.get("sayfa") != beklenen_sayfa:
            sozluk["rapor sayfa sayisi kilitle farkli"].append(ad)
        dosya_birimleri = dosyalar.get(ad)
        if dosya_birimleri is None:
            continue
        d = dosya_birimleri
        # bitisiklik: ardisik gercek satirlarda bitis = sonraki baslangic; son sayfa dosya sonu
        onceki_bit: Konum | None = None
        onceki_n = 0
        for n in sirali:
            s = satirlar_[n]
            bas = _konum(d, s["start_anchor"], s["start_offset"])
            bit = _konum(d, s["end_anchor"], s["end_offset"])
            if bas is None or bit is None or not 0 <= bit.o <= d.birimler[bit.r].uzunluk:
                onceki_bit = None
                continue
            if onceki_bit is not None and onceki_n + 1 == n and onceki_bit != bas:
                sozluk["ardisik satirlar bitisik degil"].append(f"{ad}#{onceki_n}")
            onceki_bit, onceki_n = _bitis_normal(d, bit), n
        if sirali and onceki_bit is not None and onceki_bit != Konum(len(d.birimler), 0):
            sozluk["son sayfa dosya sonunda bitmiyor"].append(ad)
        for n, s in bolum_basi.get(ad, {}).items():
            bas = _konum(d, s["start_anchor"], s["start_offset"])
            if (
                bas is None
                or bas.o != 0
                or d.birimler[bas.r].bolum_sayfasi is None
                or d.birimler[bas.r].sayfa != n
            ):
                sozluk["bolum basi satiri baslik birimine bagli degil"].append(f"{ad}#{n}")

    for ad, neden in (
        ("volume cilt tablosunda yok", "satir cilt tablosunda olmayan volume tasiyor"),
        ("yinelenen sayfa", "(volume, page) birden fazla satirda"),
        ("capa ayni dosyada degil", "capa risale-rnk-metin anchor ciktisinda ya da dosyada yok"),
        ("ofset metne sigmiyor", "ofset birim metnine sigmiyor"),
        ("bitis baslangictan once", "yari acik aralik ters"),
        ("sayfa sayisi ingest sayfalari kilitle farkli", "dosyada #n sayisi kilitten farkli"),
        ("sayfa sayisi satirlar kilitle farkli", "satir (+icerik-yok) sayisi kilitten farkli"),
        ("sayfa kumesi sayfalar.jsonl ile farkli", "sayfa numaralari kaynaktan farkli"),
        ("sayfa numaralari +1 ardisik degil", "dosyada sayfa numarasi atliyor"),
        ("ilk/son sayfa kilit ve json meta ile farkli", "dosyada ilk ya da son sayfa farkli"),
        ("rapor sayfa sayisi kilitle farkli", "dosyada rapor sayisi kilitten farkli"),
        ("ardisik satirlar bitisik degil", "sayfada bitis sonraki baslangicla bitisik degil"),
        ("son sayfa dosya sonunda bitmiyor", "dosyada son sayfa dosya sonunda bitmiyor"),
        ("bolum basi satiri baslik birimine bagli degil", "bolum basi satiri baslik birimine"),
    ):
        _bulgu(bulgular, ad, sozluk.get(ad, []), neden)
    sayilar = {
        "satir": len(g.satirlar),
        "dosya": len(g.kilit.kitaplar),
        "kilit_sayfa": toplam_sayfa,
        "gercek_satir": toplam_gercek,
        "icerik_yok": toplam_yok,
        "bolum_basi_satiri": sum(len(v) for v in bolum_basi.values()),
        "bos_sayfa": sum(_tam(r["bos_sayfa"]) for r in g.raporlar),
    }
    return KapiSonucu("G-BUT", tuple(bulgular), sayilar)


# --- G-CAP -------------------------------------------------------------------------------


def g_cap(g: SayfaGirdisi) -> KapiSonucu:
    bulgular: list[str] = []
    tablo = {k.slug for k in g.tablo}
    ters = _ters_cilt(g)
    tum_capalar = {b.capa for liste in g.birimler.values() for b in liste}
    ozetler = {b.capa: b.ozet for liste in g.birimler.values() for b in liste}
    sozluk: dict[str, list[str]] = defaultdict(list)
    gorulen: set[tuple[str, int, int]] = set()
    surum = g.kayit.surum or ""
    izinli = {data_versiyonu(surum), data_versiyonu(surum, bolum_basi=True)}
    for s in g.satirlar:
        if set(s) != SATIR_ALANLARI:
            continue
        yer = f"{ters.get(_tam(s['volume']), 'volume')}#{_tam(s['page'])}"
        anahtar = (_metin(s["source_id"]), _tam(s["volume"]), _tam(s["page"]))
        if anahtar in gorulen:
            sozluk["yinelenen anahtar"].append(yer)
        gorulen.add(anahtar)
        if s["source_id"] != KAYNAK:
            sozluk["source_id"].append(yer)
        if s["data_version"] not in izinli:
            sozluk["data_version"].append(yer)
        if _tam(s["page"]) < 1:
            sozluk["page"].append(yer)
        for alan in ("start_anchor", "end_anchor"):
            capa = _metin(s[alan])
            if len(capa) > EN_COK_ALAN_UZUNLUGU:
                sozluk["gecersiz capa"].append(yer)
                continue
            try:
                yol = rn_yolu(capa)
            except GirdiHatasi:
                sozluk["gecersiz capa"].append(yer)
                continue
            if yol[0] not in tablo:
                sozluk["kitap tabloda yok"].append(yer)
        for capa_alan, ozet_alan in (("start_anchor", "start_hash"), ("end_anchor", "end_hash")):
            ozet = s[ozet_alan]
            if not isinstance(ozet, str) or lineage.OZET_DESENI.fullmatch(ozet) is None:
                sozluk["ozet biciminde"].append(yer)
            elif ozetler.get(_metin(s[capa_alan])) not in (None, ozet):
                sozluk["ozet birimle farkli"].append(yer)
    sayilar: dict[str, int] = {"capa": 2 * len(g.satirlar), "onceki_run": 0, "onceki_satir": 0}
    if g.onceki is not None:
        sayilar["onceki_run"] = 1
        sayilar["onceki_satir"] = len(g.onceki.satirlar)
        simdiki = {(_tam(s["volume"]), _tam(s["page"])) for s in g.satirlar}
        kayip = [
            f"{ters.get(v, 'volume')}#{p}"
            for v, p in sorted(g.onceki.satirlar)
            if (v, p) not in simdiki
        ]
        sozluk["onceki surumde olup kaybolan satir"] = kayip
        kayip_capa = sorted(
            {c for cift in g.onceki.satirlar.values() for c in cift if c not in tum_capalar}
        )
        sozluk["onceki capa anchor ciktisinda yok"] = kayip_capa
        sayilar["onceki_degisen"] = sum(
            1
            for s in g.satirlar
            if g.onceki.satirlar.get((_tam(s["volume"]), _tam(s["page"])))
            not in (None, (s["start_anchor"], s["end_anchor"]))
        )
    for ad, neden in (
        ("yinelenen anahtar", "(source_id, volume, page) birden fazla satirda"),
        ("source_id", "satirda source_id risale-baski-rnk degil"),
        ("data_version", "data_version kayittan uretilenle ayni degil"),
        ("page", "page 1'den kucuk"),
        ("gecersiz capa", "capa gramere, rn: dogrulayicisina ya da kanonik bicime uymuyor"),
        ("kitap tabloda yok", "kitap slug'i risale-kitaplar.json'da yok"),
        ("ozet biciminde", "start_hash/end_hash 64 haneli kucuk harfli onaltilik degil"),
        ("ozet birimle farkli", "start_hash/end_hash anchor ciktisindaki content_hash ile farkli"),
        ("onceki surumde olup kaybolan satir", "satir silinemez"),
        ("onceki capa anchor ciktisinda yok", "onceki satirin capasi kullanim disi olamaz"),
    ):
        _bulgu(bulgular, ad, sozluk.get(ad, []), neden)
    return KapiSonucu("G-CAP", tuple(bulgular), sayilar)


# --- G-NOR -------------------------------------------------------------------------------


def g_nor(g: SayfaGirdisi) -> KapiSonucu:
    """Arama metni uretilmez: kapi uygulanmaz; satirlarin metin tasimadigini dogrular."""
    bulgular: list[str] = []
    fazla = [
        str(i + 1)
        for i, s in enumerate(g.satirlar)
        if any(isinstance(v, str) and len(v) > EN_COK_ALAN_UZUNLUGU for v in s.values())
    ]
    _bulgu(bulgular, "metin", fazla, "satirda capadan uzun metin alani var")
    return KapiSonucu("G-NOR", tuple(bulgular), {"uygulanmaz": 1, "satir": len(g.satirlar)})


KAPI_ISLEVLERI: Final[dict[str, Callable[[SayfaGirdisi], KapiSonucu]]] = {
    "G-KAY": g_kay,
    "G-BUT": g_but,
    "G-CAP": g_cap,
    "G-NOR": g_nor,
}
SAYFA_KAPILARI: Final = BASKI_KAPILARI

__all__ = ["KAPI_ISLEVLERI", "SAYFA_KAPILARI", "SayfaGirdisi", "SayfaOnceki"]
