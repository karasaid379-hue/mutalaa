# ruff: noqa: RUF001
"""Sentetik `atif` ve `iktibas` seti: betikle kurulan paragraflar ve motor olcumu (A18.5).

SINIF `sentetik` (K-51 madde 10-11): kapi ACMAZ, yalniz motor testidir. Turkce cerceve cumleleri
ACIKCA sentetiktir ("Deneme paragrafi N ..."); Arapca diziler Tanzil'den (veritabani ayet metni,
`tanzil-uthmani`; imlai varyant icin `tanzil-simple-clean` staged metin) BETIKLE alinir, hicbir
Kur'an metni hafizadan yazilmaz. Dogru etiket (hedef capa ve kelime araligi) uretimden bilinir.

Bozulma kategorileri (`kategori`): `tam_uthmani`, `imlai` (Simple Clean yazimi), `hareke_yok`
(harekeler silinir), `kismi` (ayetin 4+ kelimelik parcasi), `ardisik` (iki ardisik ayet),
`tekrarli_kalip` (Kur'an'da >= 5 ayette gecen 4 kelimelik kalip), `kisa_baglamsiz`, `kisa_ipucu`
(baglam ipucu kelimesi), `kisa_atifli` (yanina dogru acik atif), `yanlis_atif` (dogru alinti,
tutarsiz numara), `atif_ile_alinti` (dogru numara), `atif_bicimleri` (Arapcasiz paragraflarda acik
atif bicimleri: `(2:255)`, `[2/255]`, ad tabanli bicimler, aralik ve liste), `arapcasiz`
(yanlis pozitif olcumu).

GECERLI HEDEFLER: bir Arapca dizi Kur'an'in birden cok yerinde gecebilir. Gecerli hedefler, dizinin
normalize kelime dizisinin (`normalize_ar`) korpusta BIREBIR gectigi butun ayetlerdir (motordan
bagimsiz, duz tarama) ve kaynak ayeti her zaman icerir. Tahmin, gecerli hedeflerden birini
tasiyorsa ve acikliklar IoU >= 0,5 ise dogrudur (`olcum.aciklik_esle`).

`ornek`: `id`, `kategori`, `paragraf` (sentetik cerceve + Tanzil dizisi), `iktibas` listesi
(`hedefler`, `birincil`, `birincil_aralik` = QAC kelime konumu [ilk, son + 1), `bas`, `son`,
`kelime`), `atif` listesi (`hedef`, `bas`, `son`, `bicim`, `bicim_sinifi`, `tutarsiz`).
"""

import random
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Final

import psycopg

from mutalaa_pipeline.enrich.citations.iktibas import (
    ATIF,
    IKTIBAS,
    AdayHat,
    Birim,
    MotorGirdisi,
    birim_isle,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.normalize import normalize_ar
from mutalaa_pipeline.qa.gold import setler
from mutalaa_pipeline.qa.gold.kapi import TurSonucu, tahmin_ozeti
from mutalaa_pipeline.qa.gold.olcum import (
    ESIKLER,
    AciklikSonucu,
    ReferansAciklik,
    TahminAciklik,
    aciklik_esle,
    esik_degerlendir,
    eslesir,
    kapi_karari,
)

KAYNAK_UTHMANI: Final = "tanzil-uthmani"
KAYNAK_SIMPLE: Final = "tanzil-simple-clean"
KISA_N: Final = 4
URETIM_KOMUTU: Final = "uv run --directory pipeline mutalaa qa gold --type hepsi --build"
DOGRULAMA_YONTEMI: Final = (
    "Sentetik paragraf: Turkce cerceve (betik) + Tanzil'den betikle alinan Arapca dizi; dogru"
    " etiket (hedef capa, kelime araligi, paragraf ofseti) uretimden bilinir; gecerli hedefler"
    " normalize kelime dizisinin korpusta birebir gectigi ayetlerdir."
)
ADETLER: Final[Mapping[str, int]] = {
    "tam_uthmani": 60,
    "imlai": 60,
    "hareke_yok": 60,
    "kismi": 60,
    "ardisik": 40,
    "tekrarli_kalip": 40,
    "kisa_baglamsiz": 40,
    "kisa_ipucu": 40,
    "kisa_atifli": 40,
    "yanlis_atif": 40,
    "atif_ile_alinti": 40,
    "atif_bicimleri": 108,  # 9 bicim x 12
    "arapcasiz": 60,
}
BICIMLER: Final = (
    ("parantez_sayi", "sayi"),
    ("koseli_sayi", "sayi"),
    ("aralik_sayi", "sayi"),
    ("parantez_ad", "ad"),
    ("ad_iki_nokta", "ad"),
    ("sure_i_ad", "ad"),
    ("ad_sayi_bolu", "ad"),
    ("sira_sayisi", "ad"),
    ("liste_ad", "ad"),
)
BICIM_ADET: Final = 12
AD_KAPALI_NOTU: Final = (
    "Uretim yapilandirmasinda onayli sure adi takma adi yoktur: ad tabanli atif bicimleri kapali"
    " olculur; bicim_sinifi_kirilimi sayi ve ad bicimlerini ayirir."
)


# --- korpus ------------------------------------------------------------------------------


@dataclass
class Korpus:
    capalar: list[str]  # ayet sirasi -> q:s:a
    kelimeler: list[list[str]]  # Uthmani kelimeler (QAC konum sirasi)
    metin: list[str]  # Uthmani ayet metni
    ofsetler: list[list[tuple[int, int]]]  # kelime (char_start, char_end), kod noktasi
    simple: list[str]  # Simple Clean ham ayet metni
    ayet_sayisi: dict[int, int]
    sure_adi: dict[int, str]  # sure -> riskli olmayan kanonik ad (ad tabanli bicimler icin)
    norm: list[list[str]] = field(default_factory=list)
    indeks: dict[str, list[tuple[int, int]]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.norm = [kelimeler_norm(k) for k in self.kelimeler]
        self.indeks = defaultdict(list)
        for a, kel in enumerate(self.norm):
            for p, w in enumerate(kel):
                self.indeks[w].append((a, p))

    def sure_ayet(self, a: int) -> tuple[int, int]:
        _, s, y = self.capalar[a].split(":")
        return int(s), int(y)


def kelimeler_norm(kelimeler: Sequence[str]) -> list[str]:
    """Her kelime `normalize_ar`; bos kalanlar atilir."""
    return [w for w in (normalize_ar(k) for k in kelimeler) if w]


def korpus_oku(conn: psycopg.Connection, simple_metni: Mapping[str, str]) -> Korpus:
    """Veritabanindan Uthmani kelimeler/metin ve staged Simple Clean metinleri."""
    metinler = {
        str(a): str(m)
        for a, m in conn.execute(
            "SELECT anchor, metin FROM icerik.unit WHERE kind = 'ayet' AND source_id = %s"
            " AND status = 'etkin'",
            (KAYNAK_UTHMANI,),
        ).fetchall()
    }
    capalar: list[str] = []
    kelimeler: list[list[str]] = []
    ofsetler: list[list[tuple[int, int]]] = []
    onceki = 0
    for indeks, sure, ayet, _, bas, son, metin in conn.execute(
        "SELECT ayah_index, surah, ayah, word, char_start, char_end, text_uthmani"
        " FROM icerik.quran_word ORDER BY ayah_index, word"
    ).fetchall():
        if int(indeks) != onceki:
            onceki = int(indeks)
            capalar.append(f"q:{int(sure)}:{int(ayet)}")
            kelimeler.append([])
            ofsetler.append([])
        kelimeler[-1].append(str(metin))
        ofsetler[-1].append((int(bas), int(son)))
    if len(capalar) != 6236:
        raise GirdiHatasi(f"{len(capalar)} ayet okundu; 6236 bekleniyor")
    ayet_sayisi: dict[int, int] = {}
    for c in capalar:
        _, s, a = c.split(":")
        ayet_sayisi[int(s)] = max(ayet_sayisi.get(int(s), 0), int(a))
    sure_adi: dict[int, str] = {}
    for no, alias in conn.execute(
        "SELECT surah_no, alias FROM icerik.surah_alias WHERE kind = 'kanonik' AND NOT risky"
        " ORDER BY surah_no, alias"
    ).fetchall():
        sure_adi.setdefault(int(no), str(alias))
    eksik = [c for c in capalar if c not in metinler or c not in simple_metni]
    if eksik:
        raise GirdiHatasi("ayet metni (Uthmani ya da Simple Clean) eksik")
    return Korpus(
        capalar,
        kelimeler,
        [metinler[c] for c in capalar],
        ofsetler,
        [simple_metni[c] for c in capalar],
        ayet_sayisi,
        sure_adi,
    )


def gecerli_hedefler(k: Korpus, dizi: Sequence[str], kaynak_ayet: int) -> list[str]:
    """Normalize kelime dizisinin korpusta birebir gectigi ayetler (kaynak ayet dahil), sirali."""
    m = len(dizi)
    bulunan = {kaynak_ayet}
    for a, p in k.indeks.get(dizi[0], ()):
        if k.norm[a][p : p + m] == list(dizi):
            bulunan.add(a)
    return [k.capalar[a] for a in sorted(bulunan)]


# --- paragraf kurma ----------------------------------------------------------------------

CERCEVE_ON: Final = "Deneme paragrafı {n}. Bu çerçeve sentetik bir metindir"
CERCEVE_IPUCU: Final = " ve âyet-i kerîme şudur: "
CERCEVE_SIRADAN: Final = ". "
CERCEVE_SON: Final = " Çerçeve metni burada biter."


def hareke_sil(metin: str) -> str:
    """Birlesen isaretleri (Mn) siler; harf ve bosluk korunur."""
    return "".join(c for c in metin if unicodedata.category(c) != "Mn")


@dataclass
class Paragraf:
    metin: str
    govde_bas: int
    govde_son: int
    atif_bas: int | None = None
    atif_son: int | None = None


def paragraf_kur(
    n: int, govde: str | None, *, ipucu: bool = False, atif: str | None = None
) -> Paragraf:
    on = CERCEVE_ON.format(n=n) + (CERCEVE_IPUCU if ipucu else CERCEVE_SIRADAN)
    if govde is None:  # Arapcasiz: atif (varsa) cerceve icinde
        govde_bas = govde_son = len(on)
        metin = on
        atif_bas = atif_son = None
        if atif is not None:
            atif_bas = len(metin)
            metin += atif
            atif_son = len(metin)
        return Paragraf(metin + CERCEVE_SON, govde_bas, govde_son, atif_bas, atif_son)
    metin = on + govde
    bas, son = len(on), len(metin)
    atif_bas = atif_son = None
    if atif is not None:
        metin += " "
        atif_bas = len(metin)
        metin += atif
        atif_son = len(metin)
    return Paragraf(metin + CERCEVE_SON, bas, son, atif_bas, atif_son)


def _kaynak(capa: str, surum: str, simple_surum: str | None = None) -> list[dict[str, str]]:
    kaynaklar = [{"source_id": KAYNAK_UTHMANI, "surum": surum, "madde": capa}]
    if simple_surum is not None:
        kaynaklar.append({"source_id": KAYNAK_SIMPLE, "surum": simple_surum, "madde": capa})
    return kaynaklar


def atif_dizgesi(
    k: Korpus, bicim: str, sure: int, ayet: int, ayet2: int | None
) -> tuple[str, list[int]] | None:
    """Acik atif metni ve hedef ayet numaralari; bicim bu sure icin kurulamazsa `None`."""
    ad = k.sure_adi.get(sure)
    s2 = ayet2 if ayet2 is not None else ayet
    ayetler = [ayet] if ayet2 is None else list(range(ayet, ayet2 + 1))
    kurallar: dict[str, tuple[str | None, list[int]]] = {
        "parantez_sayi": (f"({sure}:{ayet})", [ayet]),
        "koseli_sayi": (f"[{sure}/{ayet}]", [ayet]),
        "aralik_sayi": (f"({sure}:{ayet}-{s2})", ayetler),
        "parantez_ad": (f"({ad} Sûresi, {ayet})" if ad else None, [ayet]),
        "ad_iki_nokta": (f"{ad}: {ayet}" if ad else None, [ayet]),
        "sure_i_ad": (f"Sûre-i {ad}, {ayet}" if ad else None, [ayet]),
        "ad_sayi_bolu": (f"{ad} {sure}/{ayet}" if ad else None, [ayet]),
        "sira_sayisi": (f"{ad} Sûresinin {ayet}. âyeti" if ad else None, [ayet]),
        "liste_ad": (f"{ad}, {ayet}, {s2}" if ad else None, [ayet, s2]),
    }
    metin, hedefler = kurallar[bicim]
    if metin is None:
        return None
    return metin, sorted(set(hedefler))


# --- set uretimi -------------------------------------------------------------------------


@dataclass
class _Uretici:
    k: Korpus
    surum: str
    simple_surum: str
    tohum: int
    adetler: Mapping[str, int] = field(default_factory=lambda: dict(ADETLER))
    bicim_adet: int = BICIM_ADET
    ornekler: list[dict[str, object]] = field(default_factory=list)
    sayac: int = 0

    def rng(self, kategori: str) -> random.Random:
        return random.Random(f"{self.tohum}:{kategori}")

    def ekle(
        self,
        kategori: str,
        p: Paragraf,
        iktibas: list[dict[str, object]],
        atif: list[dict[str, object]],
        kaynak: list[dict[str, str]],
        no: int,
    ) -> None:
        self.ornekler.append(
            {
                "id": f"{kategori}-{no:03d}",
                "sinif": "sentetik",
                "kaynak": kaynak,
                "dogrulama_yontemi": DOGRULAMA_YONTEMI,
                "uretim_komutu": URETIM_KOMUTU,
                "kategori": kategori,
                "paragraf": p.metin,
                "iktibas": iktibas,
                "atif": atif,
            }
        )

    def n_ata(self) -> int:
        self.sayac += 1
        return self.sayac

    def iktibas_kaydi(
        self, bas: int, son: int, dizi_norm: Sequence[str], ayet: int, ilk: int, m: int
    ) -> dict[str, object]:
        return {
            "hedefler": gecerli_hedefler(self.k, dizi_norm, ayet),
            "birincil": self.k.capalar[ayet],
            "birincil_aralik": [ilk + 1, ilk + m + 1],
            "bas": bas,
            "son": son,
            "kelime": m,
        }

    def ayet_metni(self, a: int, ilk: int, son: int) -> str:
        """Uthmani ayet metninden `[ilk, son)` kelime parcasi (kaynak metnin kod noktasi dilimi)."""
        o = self.k.ofsetler[a]
        return self.k.metin[a][o[ilk][0] : o[son - 1][1]]

    def uygun_ayetler(self, en_az: int, en_cok: int, ilk_ayet_haric: bool = True) -> list[int]:
        sonuc: list[int] = []
        for a, kel in enumerate(self.k.kelimeler):
            _, y = self.k.sure_ayet(a)
            if ilk_ayet_haric and y == 1:
                continue
            if en_az <= len(kel) <= en_cok and len(self.k.norm[a]) == len(kel):
                sonuc.append(a)
        return sonuc

    def atif_kaydi(
        self,
        bas: int,
        son: int,
        ayet_no: Sequence[int],
        sure: int,
        bicim: str,
        sinif: str,
        tutarsiz: bool = False,
    ) -> list[dict[str, object]]:
        return [
            {
                "hedef": f"q:{sure}:{y}",
                "bas": bas,
                "son": son,
                "bicim": bicim,
                "bicim_sinifi": sinif,
                "tutarsiz": tutarsiz,
            }
            for y in ayet_no
        ]

    # --- kategoriler ---

    def tam(self, kategori: str, donusum: str) -> None:
        rng = self.rng(kategori)
        havuz = self.uygun_ayetler(5, 25)
        if donusum == "imlai":  # Simple Clean kelime sayisi QAC kelime sayisiyla ayni olanlar
            havuz = [a for a in havuz if len(self.k.simple[a].split()) == len(self.k.kelimeler[a])]
        for i, a in enumerate(rng.sample(havuz, self.adetler[kategori])):
            kel = self.k.kelimeler[a]
            if donusum == "imlai":
                metin = self.k.simple[a]
                dizi = kelimeler_norm(metin.split())
            elif donusum == "hareke":
                metin = hareke_sil(self.ayet_metni(a, 0, len(kel)))
                dizi = kelimeler_norm(metin.split())
            else:
                metin = self.ayet_metni(a, 0, len(kel))
                dizi = self.k.norm[a]
            p = paragraf_kur(self.n_ata(), metin, ipucu=i % 2 == 1)
            self.ekle(
                kategori,
                p,
                [self.iktibas_kaydi(p.govde_bas, p.govde_son, dizi, a, 0, len(kel))],
                [],
                _kaynak(
                    self.k.capalar[a], self.surum, self.simple_surum if donusum == "imlai" else None
                ),
                i,
            )

    def kismi(self) -> None:
        rng = self.rng("kismi")
        havuz = self.uygun_ayetler(8, 30)
        for i, a in enumerate(rng.sample(havuz, self.adetler["kismi"])):
            kel = self.k.kelimeler[a]
            m = rng.randint(4, min(8, len(kel) - 2))
            ilk = rng.randint(0, len(kel) - m)
            metin = self.ayet_metni(a, ilk, ilk + m)
            p = paragraf_kur(self.n_ata(), metin, ipucu=i % 2 == 1)
            self.ekle(
                "kismi",
                p,
                [
                    self.iktibas_kaydi(
                        p.govde_bas, p.govde_son, self.k.norm[a][ilk : ilk + m], a, ilk, m
                    )
                ],
                [],
                _kaynak(self.k.capalar[a], self.surum),
                i,
            )

    def ardisik(self) -> None:
        rng = self.rng("ardisik")
        aday = [
            a
            for a in range(len(self.k.capalar) - 1)
            if self.k.sure_ayet(a)[0] == self.k.sure_ayet(a + 1)[0]
            and 4 <= len(self.k.kelimeler[a]) <= 12
            and 4 <= len(self.k.kelimeler[a + 1]) <= 12
            and len(self.k.norm[a]) == len(self.k.kelimeler[a])
            and len(self.k.norm[a + 1]) == len(self.k.kelimeler[a + 1])
        ]
        for i, a in enumerate(rng.sample(aday, self.adetler["ardisik"])):
            m1, m2 = len(self.k.kelimeler[a]), len(self.k.kelimeler[a + 1])
            t1, t2 = self.ayet_metni(a, 0, m1), self.ayet_metni(a + 1, 0, m2)
            p = paragraf_kur(self.n_ata(), f"{t1} {t2}", ipucu=i % 2 == 1)
            b1 = p.govde_bas
            s1 = b1 + len(t1)
            b2 = s1 + 1
            s2 = b2 + len(t2)
            self.ekle(
                "ardisik",
                p,
                [
                    self.iktibas_kaydi(b1, s1, self.k.norm[a], a, 0, m1),
                    self.iktibas_kaydi(b2, s2, self.k.norm[a + 1], a + 1, 0, m2),
                ],
                [],
                _kaynak(self.k.capalar[a], self.surum) + _kaynak(self.k.capalar[a + 1], self.surum),
                i,
            )

    def tekrarli_kalip(self) -> None:
        rng = self.rng("tekrarli_kalip")
        sayim: Counter[tuple[str, ...]] = Counter()
        ilk_yer: dict[tuple[str, ...], tuple[int, int]] = {}
        for a, kel in enumerate(self.k.norm):
            for p in range(len(kel) - 3):
                g = tuple(kel[p : p + 4])
                sayim[g] += 1
                ilk_yer.setdefault(g, (a, p))
        adaylar = sorted(g for g, n in sayim.items() if 5 <= n <= 60)
        for i, g in enumerate(rng.sample(adaylar, self.adetler["tekrarli_kalip"])):
            ayetler = [
                a
                for a, kel in enumerate(self.k.norm)
                if any(tuple(kel[p : p + 4]) == g for p in range(len(kel) - 3))
            ]
            a = rng.choice(ayetler)
            ilk = next(
                p for p in range(len(self.k.norm[a]) - 3) if tuple(self.k.norm[a][p : p + 4]) == g
            )
            if len(self.k.norm[a]) != len(self.k.kelimeler[a]):
                continue
            metin = self.ayet_metni(a, ilk, ilk + 4)
            p_ = paragraf_kur(self.n_ata(), metin, ipucu=i % 2 == 1)
            self.ekle(
                "tekrarli_kalip",
                p_,
                [self.iktibas_kaydi(p_.govde_bas, p_.govde_son, list(g), a, ilk, 4)],
                [],
                _kaynak(self.k.capalar[a], self.surum),
                i,
            )

    def kisa(self, kategori: str) -> None:
        rng = self.rng(kategori)
        havuz = self.uygun_ayetler(6, 30)
        for i, a in enumerate(rng.sample(havuz, self.adetler[kategori])):
            kel = self.k.kelimeler[a]
            ilk = rng.randint(0, len(kel) - 3)
            metin = self.ayet_metni(a, ilk, ilk + 3)
            sure, ayet = self.k.sure_ayet(a)
            atif = f"({sure}:{ayet})" if kategori == "kisa_atifli" else None
            p = paragraf_kur(self.n_ata(), metin, ipucu=kategori == "kisa_ipucu", atif=atif)
            atiflar: list[dict[str, object]] = []
            if atif is not None and p.atif_bas is not None and p.atif_son is not None:
                atiflar = self.atif_kaydi(
                    p.atif_bas, p.atif_son, [ayet], sure, "parantez_sayi", "sayi"
                )
            self.ekle(
                kategori,
                p,
                [
                    self.iktibas_kaydi(
                        p.govde_bas, p.govde_son, self.k.norm[a][ilk : ilk + 3], a, ilk, 3
                    )
                ],
                atiflar,
                _kaynak(self.k.capalar[a], self.surum),
                i,
            )

    def atifli(self, kategori: str) -> None:
        rng = self.rng(kategori)
        havuz = self.uygun_ayetler(5, 25)
        for i, a in enumerate(rng.sample(havuz, self.adetler[kategori])):
            kel = self.k.kelimeler[a]
            metin = self.ayet_metni(a, 0, len(kel))
            sure, ayet = self.k.sure_ayet(a)
            ikt_hedefler = gecerli_hedefler(self.k, self.k.norm[a], a)
            if kategori == "yanlis_atif":
                diger = [
                    b for b in range(len(self.k.capalar)) if self.k.capalar[b] not in ikt_hedefler
                ]
                b = rng.choice(diger)
                s2, y2 = self.k.sure_ayet(b)
                numara = (s2, y2)
            else:
                numara = (sure, ayet)
            atif = f"({numara[0]}:{numara[1]})"
            p = paragraf_kur(self.n_ata(), metin, ipucu=i % 2 == 1, atif=atif)
            assert p.atif_bas is not None and p.atif_son is not None
            self.ekle(
                kategori,
                p,
                [self.iktibas_kaydi(p.govde_bas, p.govde_son, self.k.norm[a], a, 0, len(kel))],
                self.atif_kaydi(
                    p.atif_bas,
                    p.atif_son,
                    [numara[1]],
                    numara[0],
                    "parantez_sayi",
                    "sayi",
                    tutarsiz=kategori == "yanlis_atif",
                ),
                _kaynak(self.k.capalar[a], self.surum),
                i,
            )

    def atif_bicimleri(self) -> None:
        rng = self.rng("atif_bicimleri")
        sure_havuzu = sorted(
            s for s in self.k.ayet_sayisi if s in self.k.sure_adi and self.k.ayet_sayisi[s] >= 6
        )
        no = 0
        for bicim, sinif in BICIMLER:
            for _ in range(self.bicim_adet):
                sure = rng.choice(sure_havuzu)
                ayet = rng.randint(1, self.k.ayet_sayisi[sure] - 3)
                ayet2 = ayet + rng.randint(1, 3) if bicim in ("aralik_sayi", "liste_ad") else None
                kurulan = atif_dizgesi(self.k, bicim, sure, ayet, ayet2)
                assert kurulan is not None
                metin, ayetler = kurulan
                p = paragraf_kur(self.n_ata(), None, atif=metin)
                assert p.atif_bas is not None and p.atif_son is not None
                self.ekle(
                    "atif_bicimleri",
                    p,
                    [],
                    self.atif_kaydi(p.atif_bas, p.atif_son, ayetler, sure, bicim, sinif),
                    _kaynak(f"q:{sure}:{ayet}", self.surum),
                    no,
                )
                no += 1

    def arapcasiz(self) -> None:
        for i in range(self.adetler["arapcasiz"]):
            n = self.n_ata()
            tuzak = i % 3 == 0
            metin = f"Deneme paragrafı {n}. Bu çerçeve sentetik bir metindir."
            if tuzak:
                metin += f" Madde {n}, sayfa 3/4 ve ({n}) numaralı bölüm."
            metin += CERCEVE_SON
            self.ornekler.append(
                {
                    "id": f"arapcasiz-{i:03d}",
                    "sinif": "sentetik",
                    "kaynak": [
                        {"source_id": "sentetik-cerceve", "surum": "1", "madde": "betik cercevesi"}
                    ],
                    "dogrulama_yontemi": DOGRULAMA_YONTEMI,
                    "uretim_komutu": URETIM_KOMUTU,
                    "kategori": "arapcasiz",
                    "paragraf": metin,
                    "iktibas": [],
                    "atif": [],
                }
            )


def uret(
    k: Korpus,
    surum: str,
    simple_surum: str,
    tohum: int = setler.VARSAYILAN_TOHUM,
    adetler: Mapping[str, int] | None = None,
    bicim_adet: int = BICIM_ADET,
) -> list[dict[str, object]]:
    """Butun kategorilerin ornekleri (tohumla deterministik); `adetler` testte kucultulur."""
    u = _Uretici(k, surum, simple_surum, tohum, dict(adetler or ADETLER), bicim_adet)
    u.tam("tam_uthmani", "uthmani")
    u.tam("imlai", "imlai")
    u.tam("hareke_yok", "hareke")
    u.kismi()
    u.ardisik()
    u.tekrarli_kalip()
    for kat in ("kisa_baglamsiz", "kisa_ipucu", "kisa_atifli"):
        u.kisa(kat)
    u.atifli("yanlis_atif")
    u.atifli("atif_ile_alinti")
    u.atif_bicimleri()
    u.arapcasiz()
    return u.ornekler


def taslak(
    surum: str, simple_surum: str, tohum: int = setler.VARSAYILAN_TOHUM
) -> dict[str, object]:
    return {
        "sinif": "sentetik",
        "olcum_turu": "motor_testi",
        "kaynak": [
            {
                "source_id": KAYNAK_UTHMANI,
                "surum": surum,
                "madde": "ayet metni (veritabani, betikle)",
                "rol": "kanit",
            },
            {
                "source_id": KAYNAK_SIMPLE,
                "surum": simple_surum,
                "madde": "imlai varyant (staged, betikle)",
                "rol": "kanit",
            },
        ],
        "dogrulama_yontemi": DOGRULAMA_YONTEMI,
        "uretim_komutu": URETIM_KOMUTU,
        "tohum": tohum,
        "kategoriler": dict(ADETLER),
        "kapi_notu": (
            "Sentetik set kapi acmaz; yalniz motor testidir (K-51 madde 11). Dongusellik denetimi "
            "muaf."
        ),
    }


# --- motoru calistirma -------------------------------------------------------------------


@dataclass
class OrnekCikti:
    ornek_id: str
    satirlar: list[AdayHat]


def motoru_calistir(
    motor: MotorGirdisi, ornekler: Sequence[Mapping[str, object]], surum: str = "gold"
) -> list[OrnekCikti]:
    """Her paragrafi motorla isler (veritabanina ve dosyaya YAZMAZ)."""
    sonuc: list[OrnekCikti] = []
    sayac: Counter[str] = Counter()
    for o in ornekler:
        metin = str(o["paragraf"])
        birim = Birim(f"meal:sentetik:1:{len(sonuc) + 1}", metin, "0" * 16)
        sonuc.append(OrnekCikti(str(o["id"]), birim_isle(motor, birim, sayac)))
    return sonuc


# --- olcum -------------------------------------------------------------------------------


def _iktibas_olc(
    ornekler: Sequence[Mapping[str, object]],
    ciktilar: Mapping[str, OrnekCikti],
    motor: MotorGirdisi,
    *,
    ayet_duzeyi: bool,
) -> tuple[AciklikSonucu, list[int], list[int], dict[str, int]]:
    """Toplu eslesme; tahmin ve referans basina kelime sayilari ve hedef aralik sayaclari."""
    t_n: list[int] = []
    r_n: list[int] = []
    t_ok: list[bool] = []
    r_ok: list[bool] = []
    aralik = {"karsilastirilan": 0, "dogru": 0}
    for o in ornekler:
        satirlar = [h for h in ciktilar[str(o["id"])].satirlar if h.tur == IKTIBAS]
        golds = o["iktibas"]
        assert isinstance(golds, list)
        if ayet_duzeyi:
            tah = sorted({motor.ayet_capalari[h.dst_sira] for h in satirlar})
            t_list = [TahminAciklik(c, 0, 1) for c in tah]
            r_list = [ReferansAciklik(frozenset(g["hedefler"]), 0, 1) for g in golds]
            for c in tah:
                n_ler = [
                    int(h.evidence["matched_words"])  # type: ignore[call-overload]
                    for h in satirlar
                    if motor.ayet_capalari[h.dst_sira] == c
                ]
                t_n.append(max(n_ler))
        else:
            t_list = [
                TahminAciklik(motor.ayet_capalari[h.dst_sira], h.src_span[0], h.src_span[1])
                for h in satirlar
            ]
            r_list = [ReferansAciklik(frozenset(g["hedefler"]), g["bas"], g["son"]) for g in golds]
            t_n.extend(int(h.evidence["matched_words"]) for h in satirlar)  # type: ignore[call-overload]
            for h, t in zip(satirlar, t_list, strict=True):
                for g, r in zip(golds, r_list, strict=True):
                    if t.hedef == g["birincil"] and h.dst_span is not None and eslesir(t, r):
                        aralik["karsilastirilan"] += 1
                        aralik["dogru"] += int(list(h.dst_span) == g["birincil_aralik"])
        s = aciklik_esle(t_list, r_list)
        t_ok.extend(s.tahmin_eslesen)
        r_ok.extend(s.referans_eslesen)
        r_n.extend(int(g["kelime"]) for g in golds)
    return AciklikSonucu(len(t_ok), len(r_ok), tuple(t_ok), tuple(r_ok)), t_n, r_n, aralik


def _prf_kesit(
    toplu: AciklikSonucu, t_n: Sequence[int], r_n: Sequence[int]
) -> dict[str, dict[str, float | int]]:
    return {
        "tum": toplu.prf().sozluk(),
        "uzun": toplu.prf([n >= KISA_N for n in t_n], [n >= KISA_N for n in r_n]).sozluk(),
        "kisa": toplu.prf([n < KISA_N for n in t_n], [n < KISA_N for n in r_n]).sozluk(),
    }


def _atif_olc(
    ornekler: Sequence[Mapping[str, object]],
    ciktilar: Mapping[str, OrnekCikti],
    motor: MotorGirdisi,
    *,
    ayet_duzeyi: bool,
) -> tuple[AciklikSonucu, list[str], list[str], dict[str, int]]:
    t_list: list[TahminAciklik] = []
    r_list: list[ReferansAciklik] = []
    t_ok: list[bool] = []
    r_ok: list[bool] = []
    r_bicim: list[str] = []
    r_sinif: list[str] = []
    tutarsiz = {"tutarsiz_gold": 0, "tutarsiz_isaretlendi": 0}
    for o in ornekler:
        satirlar = [h for h in ciktilar[str(o["id"])].satirlar if h.tur == ATIF]
        golds = o["atif"]
        assert isinstance(golds, list)
        if ayet_duzeyi:
            tah = sorted({motor.ayet_capalari[h.dst_sira] for h in satirlar})
            t = [TahminAciklik(c, 0, 1) for c in tah]
            r = [ReferansAciklik(frozenset([g["hedef"]]), 0, 1) for g in golds]
        else:
            t = [
                TahminAciklik(motor.ayet_capalari[h.dst_sira], h.src_span[0], h.src_span[1])
                for h in satirlar
            ]
            r = [ReferansAciklik(frozenset([g["hedef"]]), g["bas"], g["son"]) for g in golds]
        s = aciklik_esle(t, r)
        t_list.extend(t)
        r_list.extend(r)
        t_ok.extend(s.tahmin_eslesen)
        r_ok.extend(s.referans_eslesen)
        r_bicim.extend(str(g["bicim"]) for g in golds)
        r_sinif.extend(str(g["bicim_sinifi"]) for g in golds)
        if not ayet_duzeyi:
            for g in golds:
                if g["tutarsiz"]:
                    tutarsiz["tutarsiz_gold"] += 1
                    for h in satirlar:
                        if (
                            motor.ayet_capalari[h.dst_sira] == g["hedef"]
                            and h.evidence.get("consistent_quote") is False
                        ):
                            tutarsiz["tutarsiz_isaretlendi"] += 1
                            break
    toplu = AciklikSonucu(len(t_list), len(r_list), tuple(t_ok), tuple(r_ok))
    return toplu, r_bicim, r_sinif, tutarsiz


def bol(
    set_adi: str, ornekler: Sequence[Mapping[str, object]], tohum: int
) -> tuple[list[Mapping[str, object]], list[Mapping[str, object]]]:
    """`(dondurulmus, gelistirme)` ornekleri (bolme `setler.bolme`)."""
    don: list[Mapping[str, object]] = []
    gel: list[Mapping[str, object]] = []
    for o in ornekler:
        (don if setler.bolme(set_adi, str(o["id"]), tohum) == setler.DONDURULMUS else gel).append(o)
    return don, gel


def kategori_kirilimi(
    ornekler: Sequence[Mapping[str, object]],
    ciktilar: Mapping[str, OrnekCikti],
    motor: MotorGirdisi,
    tur: str,
) -> dict[str, object]:
    """Kategori basina dizi duzeyi PRF (bilgi): hangi bozulmada motor ne yapiyor."""
    sonuc: dict[str, object] = {}
    kategoriler = sorted({str(o["kategori"]) for o in ornekler})
    for kat in kategoriler:
        alt = [o for o in ornekler if o["kategori"] == kat]
        if tur == IKTIBAS:
            toplu, t_n, r_n, _ = _iktibas_olc(alt, ciktilar, motor, ayet_duzeyi=False)
            satir: dict[str, object] = {"ornek": len(alt), **_prf_kesit(toplu, t_n, r_n)["tum"]}
        else:
            toplu2, _, _, _ = _atif_olc(alt, ciktilar, motor, ayet_duzeyi=False)
            satir = {"ornek": len(alt), **toplu2.prf().sozluk()}
        sonuc[kat] = satir
    return sonuc


def kisa_notu(dizi: Mapping[str, Mapping[str, float | int]]) -> list[str]:
    """Kisa (n < 4) tahmin yoksa kisa kesinligin bos kume kurali geregi 1,0 oldugu uyarisi."""
    kisa = dizi["kisa"]
    tahmin = int(kisa["dp"]) + int(kisa["yp"])
    if tahmin:
        return []
    return [
        f"Kisa (n < 4) tahmin sayisi 0: kisa kesinlik bos kume kurali geregi 1,0'dir ve kapi"
        f" gecisi bir kanit degildir (kisa duyarlilik {kisa['duyarlilik']}; {kisa['yn']} kisa"
        " referans kacirildi)."
    ]


def iktibas_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    ciktilar: Mapping[str, OrnekCikti],
    motor: MotorGirdisi,
    *,
    ad_sozlugu_etkin: bool,
) -> TurSonucu:
    tohum = int(str(manifest["tohum"]))
    donduruldu, gelistirme = bol("iktibas", ornekler, tohum)
    toplu, t_n, r_n, aralik = _iktibas_olc(donduruldu, ciktilar, motor, ayet_duzeyi=False)
    dizi = _prf_kesit(toplu, t_n, r_n)
    ayet_t, at_n, ar_n, _ = _iktibas_olc(donduruldu, ciktilar, motor, ayet_duzeyi=True)
    ayet = _prf_kesit(ayet_t, at_n, ar_n)
    g_toplu, g_t, g_r, _ = _iktibas_olc(gelistirme, ciktilar, motor, ayet_duzeyi=False)
    olculer = {
        "uzun_kesinlik": float(dizi["uzun"]["kesinlik"]),
        "uzun_duyarlilik": float(dizi["uzun"]["duyarlilik"]),
        "kisa_kesinlik": float(dizi["kisa"]["kesinlik"]),
    }
    esikler = {
        "uzun_kesinlik": ESIKLER["iktibas_uzun"]["kesinlik"],
        "uzun_duyarlilik": ESIKLER["iktibas_uzun"]["duyarlilik"],
        "kisa_kesinlik": ESIKLER["iktibas_kisa"]["kesinlik"],
    }
    sonuclar = esik_degerlendir(esikler, olculer)
    uzun_ok = sonuclar["uzun_kesinlik"] and sonuclar["uzun_duyarlilik"]
    kisa_ok = sonuclar["kisa_kesinlik"]
    return TurSonucu(
        cli_tur="iktibas",
        manifest=manifest,
        sonuc=kapi_karari(esikler, olculer),
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=sonuclar,
        tahmin_ozeti=_motor_ozeti(ciktilar, motor),
        olculen_ornek=len(donduruldu),
        ayrintilar={
            "dizi_duzeyi_dondurulmus": dizi,
            "kisa_tahmin_sayisi": int(dizi["kisa"]["dp"]) + int(dizi["kisa"]["yp"]),
            "uzun_tahmin_sayisi": int(dizi["uzun"]["dp"]) + int(dizi["uzun"]["yp"]),
            "ayet_duzeyi_dondurulmus": ayet,
            "dizi_duzeyi_gelistirme_bilgi": _prf_kesit(g_toplu, g_t, g_r),
            "hedef_kelime_araligi_dogru_bilgi": aralik,
            "kategori_kirilimi_dondurulmus": kategori_kirilimi(
                donduruldu, ciktilar, motor, IKTIBAS
            ),
            "ad_sozlugu_etkin": ad_sozlugu_etkin,
            "iou_esigi": 0.5,
            "esik_alani": "dizi duzeyi, dondurulmus parca",
        },
        notlar=[
            "Sentetik set kapi ACMAZ; yalniz motor testidir (K-51 madde 11).",
            "Esikler dizi duzeyi (IoU >= 0,5) olcumune uygulanir; ayet duzeyi bilgidir.",
            *kisa_notu(dizi),
        ],
        referans_kapsami={"kapsam": "yalniz betikle kurulan paragraflar"},
        alt_sonuclar={
            "uzun": "gecti" if uzun_ok else "kaldi",
            "kisa": "gecti" if kisa_ok else "kaldi",
        },
        uretim_kaynaklari=[KAYNAK_UTHMANI, KAYNAK_SIMPLE],
    )


def atif_olc(
    manifest: Mapping[str, object],
    ornekler: Sequence[Mapping[str, object]],
    ciktilar: Mapping[str, OrnekCikti],
    motor: MotorGirdisi,
    *,
    ad_sozlugu_etkin: bool,
) -> TurSonucu:
    tohum = int(str(manifest["tohum"]))
    donduruldu, gelistirme = bol("atif", ornekler, tohum)
    toplu, r_bicim, r_sinif, tutarsiz = _atif_olc(donduruldu, ciktilar, motor, ayet_duzeyi=False)
    ayet_toplu, _, _, _ = _atif_olc(donduruldu, ciktilar, motor, ayet_duzeyi=True)
    g_toplu, _, _, _ = _atif_olc(gelistirme, ciktilar, motor, ayet_duzeyi=False)
    p = toplu.prf()
    sinif_kirilimi: dict[str, object] = {}
    for sinif in sorted(set(r_sinif)):
        sinif_kirilimi[sinif] = toplu.prf(None, [s == sinif for s in r_sinif]).sozluk()
    bicim_duyarlilik: dict[str, object] = {}
    for bicim in sorted(set(r_bicim)):
        secim = [b == bicim for b in r_bicim]
        n = sum(secim)
        bulunan = sum(1 for s, e in zip(secim, toplu.referans_eslesen, strict=True) if s and e)
        bicim_duyarlilik[bicim] = {
            "gold": n,
            "bulunan": bulunan,
            "duyarlilik": round(bulunan / n, 6) if n else None,
        }
    olculer = {"kesinlik": p.kesinlik, "duyarlilik": p.duyarlilik, "f1": p.f1}
    esikler = dict(ESIKLER["atif"])
    return TurSonucu(
        cli_tur="atif",
        manifest=manifest,
        sonuc=kapi_karari(esikler, olculer),
        olculer=olculer,
        esikler=esikler,
        esik_sonuclari=esik_degerlendir(esikler, olculer),
        tahmin_ozeti=_motor_ozeti(ciktilar, motor),
        olculen_ornek=len(donduruldu),
        ayrintilar={
            "dizi_duzeyi_dondurulmus": p.sozluk(),
            "ayet_duzeyi_dondurulmus": ayet_toplu.prf().sozluk(),
            "dizi_duzeyi_gelistirme_bilgi": g_toplu.prf().sozluk(),
            "bicim_sinifi_kirilimi_dondurulmus": sinif_kirilimi,
            "bicim_duyarlilik_dondurulmus": bicim_duyarlilik,
            "tutarsiz_numara_isaretleme": tutarsiz,
            "kategori_kirilimi_dondurulmus": kategori_kirilimi(donduruldu, ciktilar, motor, ATIF),
            "ad_sozlugu_etkin": ad_sozlugu_etkin,
            "iou_esigi": 0.5,
            "esik_alani": "dizi duzeyi, dondurulmus parca",
        },
        notlar=[
            "Sentetik set kapi ACMAZ; yalniz motor testidir (K-51 madde 11).",
            AD_KAPALI_NOTU if not ad_sozlugu_etkin else "Ad sozlugu bellekte acildi (tani).",
        ],
        referans_kapsami={"kapsam": "yalniz betikle kurulan paragraflar"},
        uretim_kaynaklari=[KAYNAK_UTHMANI, KAYNAK_SIMPLE],
    )


def _motor_ozeti(ciktilar: Mapping[str, OrnekCikti], motor: MotorGirdisi) -> str:
    parcalar: list[str] = []
    for kimlik in sorted(ciktilar):
        for h in ciktilar[kimlik].satirlar:
            parcalar.append(
                f"{kimlik}|{h.tur}|{h.src_span}|{motor.ayet_capalari[h.dst_sira]}|{h.dst_span}"
            )
    return tahmin_ozeti(parcalar)
