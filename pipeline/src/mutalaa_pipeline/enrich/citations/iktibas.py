"""Birim basina acik atif ve iktibas motoru (Iktibas tespiti §1-§8): saf hesap.

Akis (bir meal birimi): acik atiflar (`gramer`) -> Arapca diziler (`diziler`) -> esleme
belirtecleri (`normalizasyon`) -> tohum ve Smith-Waterman (`hizala`, Uthmani ve imlai indeks) ->
ayet sinirinda parcalar -> kume (ayni dizi bolgesine hizalanan adaylar) -> kalip, f ve baglam
kurallari (§7-§8) -> `xref` adaylari (`AdayHat`).

* Hizalanan konumlar ayet sinirinda bolunur; her ayete ayri satir, satirlar `evidence.group` ile
  bagli. `dst_span` QAC kelime konumu `[ilk, son + 1)`; imlai indekste ayet kelime sayilari
  farkliysa ayet ici hizalamayla bulunur ve `evidence.konum_belirsiz = true` yazilir.
* Kume (ayni dizi bolgesi, birden cok hedef: f > 1): kalip listesinde ise satir yok; baglam tek
  hedef seciyorsa (acik atif, komsu ayet, meal benzerligi) o hedef (f = 1), digerleri
  `evidence.alternatives`; baglam yoksa en cok 3 hedef, her biri 1/f.
* Kisa kural (§7): n < 4 ve olumlu baglam sinyali yok -> satir yok (istatistik); sinyal varsa aday.
* `src_span`: Arapca dizinin birim metnindeki kod noktasi araligi (kanonik metin; NFC uygulanmaz).

Hicbir sayac, kanit ya da cikti metin tasimaz (anahtar, ofset, ozet ve sayilar).
"""

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

from mutalaa_pipeline.enrich.citations import gramer, hizala
from mutalaa_pipeline.enrich.citations.diziler import ArapcaDizi, arapca_diziler
from mutalaa_pipeline.enrich.citations.indeks import EslestirmeIndeksi
from mutalaa_pipeline.enrich.citations.kalip import kalip_mi
from mutalaa_pipeline.enrich.citations.kurallar import (
    ATIF_MESAFESI,
    IPUCU_PENCERESI,
    KOMSU_UZAKLIK,
    MEAL_PENCERESI,
    Ipuclari,
    Sinyaller,
    guven_hesapla,
    iktibas_puani,
    ipucu_var,
    meal_benzerligi,
)
from mutalaa_pipeline.enrich.citations.normalizasyon import Belirtec, belirtecler

ATIF: Final = "atif"
IKTIBAS: Final = "iktibas"
KAYNAK_ATIF: Final = "tanzil-uthmani"
KAYNAK_IMLAI: Final = "tanzil-simple-clean"
EN_COK_BAGLAMSIZ_HEDEF: Final = 3
EN_COK_ALTERNATIF: Final = 10
KISA_N: Final = 4
KISA_TOHUM: Final = 4  # tohum en az 4 kelime ister (4-gram ya da iki 3-gram)
KUME_ORTUSME: Final = 0.5


@dataclass(frozen=True)
class Birim:
    anchor: str
    metin: str
    ozet: str  # content_hash ilk 16 hane
    role: str = "govde"


@dataclass
class MotorGirdisi:
    indeksler: Sequence[EslestirmeIndeksi]  # Uthmani ilk
    ayet_capalari: Sequence[str]  # ayet sirasi -> q:s:a
    ayet_ozetleri: Sequence[str]
    kalip: frozenset[str]
    ipuclari: Ipuclari
    sozluk: gramer.AdSozlugu | None = None
    adlandirilmis: Sequence[gramer.AdlandirilmisAyet] = ()
    meal_metni: Callable[[int], str | None] = lambda _sira: None
    lemma_sozlugu: Mapping[str, frozenset[int]] = field(default_factory=dict)
    ayet_yeri: dict[str, int] = field(init=False)
    ayet_sure: list[tuple[int, int]] = field(init=False)

    def __post_init__(self) -> None:
        self.ayet_yeri = {c: i for i, c in enumerate(self.ayet_capalari)}
        self.ayet_sure = []
        for c in self.ayet_capalari:
            _, sure, ayet = c.split(":")
            self.ayet_sure.append((int(sure), int(ayet)))


@dataclass
class AdayHat:
    """Bir `xref` aday satiri (staged'e cevrilmeden once)."""

    tur: str
    src_anchor: str
    src_span: tuple[int, int]
    dst_sira: int
    dst_span: tuple[int, int] | None
    score: float
    confidence: float
    evidence: dict[str, object]


@dataclass
class Parca:
    ayet: int
    a_ilk: int
    a_son: int  # dahil
    n: int
    e: int
    b_ilk: int  # ayet ici belirtec (dahil)
    b_son: int
    kelime_ilk: int
    kelime_son1: int
    belirsiz: bool
    f: int
    phrase_key: str
    b_key: str


@dataclass
class Aday:
    indeks: EslestirmeIndeksi
    run: int
    a_ilk: int
    a_son: int  # dahil
    parcalar: list[Parca]

    @property
    def n_toplam(self) -> int:
        return sum(p.n for p in self.parcalar)

    @property
    def e_toplam(self) -> int:
        return sum(p.e for p in self.parcalar)

    def ayetler(self) -> set[int]:
        return {p.ayet for p in self.parcalar}


def _parcalar(
    hiza: hizala.Hiza, indeks: EslestirmeIndeksi, anahtarlar: Sequence[str]
) -> list[Parca]:
    """Hizalanan ciftleri ayet sinirinda boler (her ayet icin bir parca)."""
    gruplar: list[tuple[int, list[tuple[int, int, str]]]] = []
    for i, g, tur in hiza.ciftler:
        ayet, yerel = indeks.ayet_ve_yerel(g)
        if gruplar and gruplar[-1][0] == ayet:
            gruplar[-1][1].append((i, yerel, tur))
        else:
            gruplar.append((ayet, [(i, yerel, tur)]))
    sonuc: list[Parca] = []
    for ayet, ciftler in gruplar:
        n = sum(1 for _, _, t in ciftler if t != hizala.HATALI)
        if n == 0:
            continue
        e, onceki = 0, None
        for i, y, t in ciftler:
            if t != hizala.TAM:
                e += 1
            if onceki is not None:
                e += (i - onceki[0] - 1) + (y - onceki[1] - 1)
            onceki = (i, y)
        a_ilk, a_son = ciftler[0][0], ciftler[-1][0]
        b_ilk, b_son = ciftler[0][1], ciftler[-1][1]
        ilk, son1, belirsiz = indeks.kelime_araligi(ayet, b_ilk, b_son)
        b_tokenler = indeks.ayet_belirtec[ayet][b_ilk : b_son + 1]
        sonuc.append(
            Parca(
                ayet,
                a_ilk,
                a_son,
                n,
                e,
                b_ilk,
                b_son,
                ilk,
                son1,
                belirsiz,
                max(1, len(indeks.dizi_ayetleri(b_tokenler))),
                " ".join(anahtarlar[a_ilk : a_son + 1]),
                " ".join(b_tokenler),
            )
        )
    return sonuc


def _tam_ayet_adaylari(
    anahtarlar: Sequence[str],
    run_no: int,
    indeksler: Sequence[EslestirmeIndeksi],
    sayac: Counter[str],
) -> list[Aday]:
    """§5 tam ayet karmasi: dort kelimeden kisa dizi, tamami bir ayetin normalize metniyse."""
    adaylar: list[Aday] = []
    gorulen: set[int] = set()
    for idx in indeksler:
        ayetler = idx.indeks.tam_ayetler(anahtarlar)
        for ayet in ayetler:
            if ayet in gorulen:
                continue
            gorulen.add(ayet)
            n = len(anahtarlar)
            ilk, son1, belirsiz = idx.kelime_araligi(ayet, 0, n - 1)
            anahtar = " ".join(anahtarlar)
            parca = Parca(
                ayet,
                0,
                n - 1,
                n,
                0,
                0,
                n - 1,
                ilk,
                son1,
                belirsiz,
                max(1, len(ayetler)),
                anahtar,
                anahtar,
            )
            adaylar.append(Aday(idx, run_no, 0, n - 1, [parca]))
    if adaylar:
        sayac["tam_ayet_kisa_dizi"] += 1
    return adaylar


def _ortusme(a: tuple[int, int], b: tuple[int, int]) -> float:
    """Iki kapali aralik `[ilk, son]` ortusmesi / kisa olanin uzunlugu."""
    ortak = min(a[1], b[1]) - max(a[0], b[0]) + 1
    return max(0, ortak) / min(a[1] - a[0] + 1, b[1] - b[0] + 1)


def _adaylari_bul(
    anahtarlar: Sequence[str],
    run_no: int,
    indeksler: Sequence[EslestirmeIndeksi],
    sayac: Counter[str],
) -> list[Aday]:
    ham: list[tuple[int, Aday]] = []
    onbellek: dict[tuple[str, str], int] = {}
    if len(anahtarlar) < KISA_TOHUM:
        return _tam_ayet_adaylari(anahtarlar, run_no, indeksler, sayac)
    for sira, idx in enumerate(indeksler):
        tohumlar = hizala.tohumlari_bul(anahtarlar, idx.indeks)
        sayac["tohum_cok_sik_atlanan"] += tohumlar.cok_sik_atlanan
        sayac["tohum_kose_siniri_asan"] += tohumlar.kose_siniri_asan
        sayac["tohum"] += len(tohumlar.tohumlar)
        for t in tohumlar.tohumlar:
            hiza = hizala.hizala(anahtarlar, idx.indeks, t, onbellek=onbellek)
            if hiza is None:
                continue
            parcalar = _parcalar(hiza, idx, anahtarlar)
            if not parcalar:
                continue
            ham.append(
                (
                    sira,
                    Aday(
                        idx,
                        run_no,
                        min(p.a_ilk for p in parcalar),
                        max(p.a_son for p in parcalar),
                        parcalar,
                    ),
                )
            )
    ham.sort(key=lambda s: (-s[1].n_toplam, s[1].e_toplam, s[0], min(s[1].ayetler())))
    tutulan: list[Aday] = []
    for _, aday in ham:
        kopya = any(
            aday.ayetler() & k.ayetler()
            and _ortusme((aday.a_ilk, aday.a_son), (k.a_ilk, k.a_son)) >= KUME_ORTUSME
            for k in tutulan
        )
        if kopya:
            sayac["hiza_tekrar_elenen"] += 1
        else:
            tutulan.append(aday)
    # alt dizi: dizi araligi daha cok kelimeli baska bir adayin icinde kalan aday ayri hedef degil
    kalan = [
        x
        for x in tutulan
        if not any(
            y is not x and y.n_toplam > x.n_toplam and y.a_ilk <= x.a_ilk and x.a_son <= y.a_son
            for y in tutulan
        )
    ]
    sayac["alt_dizi_elenen"] += len(tutulan) - len(kalan)
    return kalan


def _kumele(adaylar: list[Aday]) -> list[list[Aday]]:
    """A araligi ortusen adaylari (>= %50) bir kumede toplar (birlesim-bulma)."""
    ata = list(range(len(adaylar)))

    def bul(x: int) -> int:
        while ata[x] != x:
            ata[x] = ata[ata[x]]
            x = ata[x]
        return x

    for i in range(len(adaylar)):
        for j in range(i + 1, len(adaylar)):
            if (
                _ortusme((adaylar[i].a_ilk, adaylar[i].a_son), (adaylar[j].a_ilk, adaylar[j].a_son))
                >= KUME_ORTUSME
            ):
                ata[bul(i)] = bul(j)
    kumeler: dict[int, list[Aday]] = {}
    for i, a in enumerate(adaylar):
        kumeler.setdefault(bul(i), []).append(a)
    return list(kumeler.values())


def _mesafe(bas1: int, son1: int, bas2: int, son2: int) -> int:
    return max(0, max(bas1, bas2) - min(son1, son2))


@dataclass
class _Secim:
    kume: int
    aday: Aday
    alternatifler: list[Aday]
    mod: str  # tek | baglam | baglamsiz


@dataclass
class _Baglam:
    g: MotorGirdisi
    birim: Birim
    runlar: list[ArapcaDizi]
    belirtec: list[list[Belirtec]]
    atiflar: list[gramer.Atif]
    sayac: Counter[str]

    def yakin_atif_ayetleri(self, run: int) -> set[int]:
        r = self.runlar[run]
        sonuc: set[int] = set()
        for a in self.atiflar:
            if _mesafe(r.bas, r.son, a.bas, a.son) <= ATIF_MESAFESI:
                sira = self.g.ayet_yeri.get(a.capa)
                if sira is not None:
                    sonuc.add(sira)
        return sonuc

    def ipucu(self, run: int) -> tuple[bool, bool]:
        r = self.runlar[run]
        metin = self.birim.metin
        pencere = (
            metin[max(0, r.bas - IPUCU_PENCERESI) : r.bas]
            + " "
            + metin[r.son : r.son + IPUCU_PENCERESI]
        )
        return (
            ipucu_var(pencere, self.g.ipuclari.kuran),
            ipucu_var(pencere, self.g.ipuclari.ters),
        )

    def meal(self, run: int, ayet: int) -> float | None:
        if not self.g.lemma_sozlugu:
            return None
        r = self.runlar[run]
        takip = self.birim.metin[r.son : r.son + MEAL_PENCERESI]
        return meal_benzerligi(takip, self.g.meal_metni(ayet), self.g.lemma_sozlugu)


def _komsu_mu(g: MotorGirdisi, ayet: int, digerleri: Sequence[int]) -> bool:
    sure, no = g.ayet_sure[ayet]
    for d in digerleri:
        s2, n2 = g.ayet_sure[d]
        if s2 == sure and abs(n2 - no) <= KOMSU_UZAKLIK:
            return True
    return False


def _sirala(adaylar: Sequence[Aday]) -> list[Aday]:
    return sorted(
        adaylar,
        key=lambda a: (
            -a.n_toplam,
            a.e_toplam,
            min(a.ayetler()),
            a.indeks.ad,
        ),
    )


def _secici_sinyal(c: _Baglam, aday: Aday, kesin_digerleri: Sequence[int]) -> bool:
    """Hedefi ayiran sinyal: acik atif, komsu ayet (kesin baska iktibas) ya da meal benzerligi."""
    atif = c.yakin_atif_ayetleri(aday.run)
    for p in aday.parcalar:
        if p.ayet in atif or _komsu_mu(c.g, p.ayet, kesin_digerleri):
            return True
        if c.meal(aday.run, p.ayet) is not None:
            return True
    return False


def _kumeleri_sec(c: _Baglam, kumeler: list[list[Aday]]) -> list[_Secim]:
    """Kalip ve f kurallari (§7): her kume icin secilen adaylar."""
    secimler: list[_Secim] = []
    kesin: list[tuple[int, int]] = []  # (kume, ayet) f = 1 tek hedefli kumeler
    belirsiz: list[tuple[int, list[Aday]]] = []
    for no, kume in enumerate(kumeler):
        ornek = _sirala(kume)[0]
        a_key = " ".join(k.anahtar for k in c.belirtec[ornek.run][ornek.a_ilk : ornek.a_son + 1])
        if kalip_mi(a_key, c.g.kalip) or any(kalip_mi(p.b_key, c.g.kalip) for p in ornek.parcalar):
            c.sayac["kalip_listesinde_kume"] += 1
            continue
        if len(kume) == 1 and all(p.f == 1 for p in kume[0].parcalar):
            secimler.append(_Secim(no, kume[0], [], "tek"))
            kesin.extend((no, p.ayet) for p in kume[0].parcalar)
        else:
            belirsiz.append((no, _sirala(kume)))
    for no, aday_listesi in belirsiz:
        digerleri = [ayet for k, ayet in kesin if k != no]
        secici = [a for a in aday_listesi if _secici_sinyal(c, a, digerleri)]
        if len(secici) == 1:
            secilen = secici
            mod = "baglam"
            c.sayac["f_baglam_tek_hedef"] += 1
        else:
            secilen = (secici or aday_listesi)[:EN_COK_BAGLAMSIZ_HEDEF]
            mod = "baglamsiz"
            c.sayac["f_baglamsiz_en_cok_3"] += 1
        for a in secilen:
            diger = [x for x in aday_listesi if x is not a]
            secimler.append(_Secim(no, a, diger, mod))
    secimler.sort(key=lambda s: (s.aday.run, s.aday.a_ilk, min(s.aday.ayetler())))
    return secimler


def _satir_kur(
    c: _Baglam,
    s: _Secim,
    atif_ayetleri: set[int],
    tum_secimler: Sequence[_Secim],
) -> list[AdayHat]:
    g, birim = c.g, c.birim
    run = c.runlar[s.aday.run]
    bel = c.belirtec[s.aday.run]
    kuran_ipucu, ters_ipucu = c.ipucu(s.aday.run)
    konum = run.position == "baslik" or run.suslu
    sonuc: list[AdayHat] = []
    ayni_aday_ayetleri = {p.ayet for p in s.aday.parcalar}
    tutarli_ayet = bool(atif_ayetleri & ayni_aday_ayetleri)
    baska_kume = [q.ayet for t in tum_secimler if t.kume != s.kume for q in t.aday.parcalar]
    for p in s.aday.parcalar:
        # ayni adayin baska parcasi yalniz kendisi kisa degilse (n >= 4) baglam sayilir
        komsu = _komsu_mu(
            g,
            p.ayet,
            [*baska_kume, *(q.ayet for q in s.aday.parcalar if q is not p and q.n >= KISA_N)],
        )
        f = 1 if s.mod in ("tek", "baglam") else p.f
        puan = iktibas_puani(p.n, g.indeksler[0].ayet_kelime_sayisi[p.ayet], p.e, f)
        meal = c.meal(s.aday.run, p.ayet)
        acik_atif = p.ayet in atif_ayetleri
        sinyal = Sinyaller(
            acik_atif=acik_atif,
            komsu=komsu,
            meal_benzerligi=meal,
            kuran_ipucu=kuran_ipucu,
            ters_ipucu=ters_ipucu,
            konum=konum,
        )
        if p.n < KISA_N:
            if not sinyal.olumlu:
                c.sayac["kisa_baglamsiz_satir_yok"] += 1
                continue
            c.sayac["kisa_baglamli_aday"] += 1
        tutarli: bool | None
        if acik_atif:
            tutarli = True
        elif atif_ayetleri and not tutarli_ayet:
            tutarli = False
        else:
            tutarli = None
        guven = guven_hesapla(puan, sinyal, tutarli=tutarli)
        ilk, son = bel[p.a_ilk], bel[p.a_son]
        evidence: dict[str, object] = {
            "matched_words": p.n,
            "ayah_words": g.indeksler[0].ayet_kelime_sayisi[p.ayet],
            "coverage": min(1.0, p.n / g.indeksler[0].ayet_kelime_sayisi[p.ayet]),
            "identity": p.n / (p.n + p.e),
            "edits": p.e,
            "index": s.aday.indeks.ad,
            "phrase_freq": p.f,
            "position": run.position,
            "phrase_key": p.phrase_key,
            "src_hash": birim.ozet,
            "dst_hash": g.ayet_ozetleri[p.ayet],
            "source_id": KAYNAK_IMLAI if s.aday.indeks.ad == "imlai" else KAYNAK_ATIF,
            "src_span": [run.bas + ilk.bas, run.bas + son.son],
        }
        baglam: dict[str, object] = {}
        if acik_atif:
            baglam["acik_atif"] = True
        if komsu:
            baglam["komsu_ayet"] = True
        if meal is not None:
            baglam["meal_benzerligi"] = meal
        if kuran_ipucu:
            baglam["kuran_ipucu"] = True
        if ters_ipucu:
            baglam["ters_ipucu"] = True
        if konum:
            baglam["konum"] = True
        if run.suslu:
            baglam["suslu_parantez"] = True
        if baglam:
            evidence["context"] = baglam
        if tutarli is not None:
            evidence["consistent_quote"] = tutarli
        if len(s.aday.parcalar) > 1:
            evidence["group"] = f"{run.bas}-{run.son}:{g.ayet_capalari[s.aday.parcalar[0].ayet]}"
        if p.belirsiz:
            evidence["konum_belirsiz"] = True
        alternatifler = [
            {"dst_anchor": g.ayet_capalari[x.parcalar[0].ayet], "matched_words": x.n_toplam}
            for x in s.alternatifler
        ]
        if not alternatifler and p.f > 1:
            diger = sorted(
                s_
                for s_ in s.aday.indeks.dizi_ayetleri(
                    s.aday.indeks.ayet_belirtec[p.ayet][p.b_ilk : p.b_son + 1]
                )
                if s_ != p.ayet
            )
            alternatifler = [{"dst_anchor": g.ayet_capalari[x]} for x in diger]
        if alternatifler:
            evidence["alternatives"] = alternatifler[:EN_COK_ALTERNATIF]
        sonuc.append(
            AdayHat(
                IKTIBAS,
                birim.anchor,
                (run.bas + ilk.bas, run.bas + son.son),
                p.ayet,
                (p.kelime_ilk, p.kelime_son1),
                puan,
                guven,
                evidence,
            )
        )
    return sonuc


def _atif_satirlari(c: _Baglam, iktibas: Sequence[AdayHat]) -> list[AdayHat]:
    """Acik atif satirlari; yakin iktibasla tutarlilik (`consistent_quote`) ve guven."""
    g, birim = c.g, c.birim
    gruplar: dict[tuple[int, int], list[gramer.Atif]] = {}
    for a in c.atiflar:
        gruplar.setdefault((a.bas, a.son), []).append(a)
    sonuc: list[AdayHat] = []
    pozisyon = "baslik" if birim.role == "baslik" else "metin"
    for (bas, son), grup in sorted(gruplar.items()):
        sirali = [(a, g.ayet_yeri[a.capa]) for a in grup if a.capa in g.ayet_yeri]
        yakin = [
            h for h in iktibas if _mesafe(bas, son, h.src_span[0], h.src_span[1]) <= ATIF_MESAFESI
        ]
        yakin_ayetler = {h.dst_sira for h in yakin}
        grup_ayetleri = {s for _, s in sirali}
        grup_tutarli = bool(yakin_ayetler & grup_ayetleri)
        for a, ayet in sirali:
            tutarli: bool | None = None
            if ayet in yakin_ayetler:
                tutarli = True
            elif yakin and not grup_tutarli:
                tutarli = False
            guven = (
                a.guven if tutarli is None else guven_hesapla(a.guven, Sinyaller(), tutarli=tutarli)
            )
            evidence: dict[str, object] = {
                "bicim": a.bicim,
                "position": pozisyon,
                "src_hash": birim.ozet,
                "dst_hash": g.ayet_ozetleri[ayet],
                "source_id": KAYNAK_ATIF,
            }
            if a.grup is not None:
                evidence["group"] = f"{a.bas}-{a.son}"
            if tutarli is not None:
                evidence["consistent_quote"] = tutarli
            sonuc.append(
                AdayHat(ATIF, birim.anchor, (a.bas, a.son), ayet, None, 1.0, guven, evidence)
            )
    return sonuc


def birim_isle(g: MotorGirdisi, birim: Birim, sayac: Counter[str]) -> list[AdayHat]:
    """Bir meal biriminin atif ve iktibas adaylari (birim sirasinda, tekil dogal anahtarli)."""
    sayac["birim"] += 1
    sonuc = gramer.atiflari_bul(birim.metin, sozluk=g.sozluk, adlandirilmis=g.adlandirilmis)
    sayac.update(sonuc.sayac)
    atif_gecerli = [a for a in sonuc.atiflar if a.capa in g.ayet_yeri]
    position = "baslik" if birim.role == "baslik" else "metin"
    runlar = arapca_diziler(birim.metin, position)
    sayac["arapca_dizi"] += len(runlar)
    belirtec = [belirtecler(r.metin) for r in runlar]
    c = _Baglam(g, birim, runlar, belirtec, atif_gecerli, sayac)
    if runlar:
        sayac["arapca_iceren_birim"] += 1
    kumeler: list[list[Aday]] = []
    for no, bel in enumerate(belirtec):
        anahtarlar = [b.anahtar for b in bel]
        adaylar = _adaylari_bul(anahtarlar, no, g.indeksler, sayac)
        if not adaylar:
            sayac[
                "dizi_kisa_tam_ayet_yok" if len(anahtarlar) < KISA_TOHUM else "dizi_eslesmesiz"
            ] += 1
            continue
        kumeler.extend(_kumele(adaylar))
    tum = _kumeleri_sec(c, kumeler)
    iktibaslar: list[AdayHat] = []
    for s in tum:
        atif_ayetleri = c.yakin_atif_ayetleri(s.aday.run)
        iktibaslar.extend(_satir_kur(c, s, atif_ayetleri, tum))
    # ayni dogal anahtar (kaynak aralik + hedef + kelime konumu): en yuksek guven
    benzersiz: dict[tuple[tuple[int, int], int, tuple[int, int] | None], AdayHat] = {}
    for h in iktibaslar:
        anahtar = (h.src_span, h.dst_sira, h.dst_span)
        onceki = benzersiz.get(anahtar)
        if onceki is None or h.confidence > onceki.confidence:
            benzersiz[anahtar] = h
    iktibaslar = sorted(
        benzersiz.values(), key=lambda h: (h.src_span, h.dst_sira, h.dst_span or (0, 0))
    )
    atiflar = _atif_satirlari(c, iktibaslar)
    return [*atiflar, *iktibaslar]
