# ruff: noqa: RUF001
"""Diyanet <-> RNK kelime dizisi karsilastirma testleri (A20.1; ACIKCA SENTETIK veri).

Hicbir Risale metni yoktur: sozcukler "deneme", "paragraf" ve "zz..." ile baslayan yer tutucu
dizelerdir. Gercek `data/` kullanilmaz; staged dosyalari `tmp_path` altinda uretilir.
"""

import json
from pathlib import Path

import pytest

from mutalaa_pipeline.anchor.risale import Diyanet, Kitap, RnkBaglanti
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import risale_karsilastirma as rk
from mutalaa_pipeline.ingest.risale_karsilastirma import Birim

# --- kelime anahtari -----------------------------------------------------------------------


def gevsek(metin: str) -> list[str]:
    return [g for g, _ in rk.kelime_anahtarlari(metin)]


def siki(metin: str) -> list[str]:
    return [s for _, s in rk.kelime_anahtarlari(metin)]


def test_karsilastirma_anahtar_turkce_i_acik_esleme() -> None:
    assert gevsek("ISIK İşık ışık") == ["isik", "isik", "isik"]
    assert siki("ISIK İşık ışık") == ["ısık", "işık", "ışık"]


def test_karsilastirma_anahtar_sapka_ve_kesme_gevsek_esit_siki_farkli() -> None:
    assert gevsek("âlem Lem'a") == gevsek("alem Lema")
    assert siki("âlem") != siki("alem")
    assert siki("Lem'a") != siki("Lema")
    assert siki("Lem’a") == siki("Lem'a")  # kesme bicimleri siki anahtarda tek bicim


def test_karsilastirma_anahtar_cf_atilir_ve_noktalama_boler() -> None:
    yumusak_tire = chr(0xAD)
    zwnj = chr(0x200C)
    assert gevsek(f"dene{yumusak_tire}me") == ["deneme"]
    assert gevsek(f"dene{zwnj}me") == ["deneme"]
    assert gevsek("bir-iki, (üç)") == ["bir", "iki", "uc"]
    assert gevsek("12. madde") == ["12", "madde"]
    assert gevsek("  ... ") == []


def test_karsilastirma_anahtar_arapca_hareke_atilir() -> None:
    harekeli = "بَّ"  # be + fatha + shadda
    assert gevsek(harekeli) == ["ب"]


# --- hizalama ------------------------------------------------------------------------------


def eslesen(a: list[int], b: list[int]) -> int:
    return sum(n for _, _, n in rk.hizala(a, b).bloklar)


def test_karsilastirma_hizala_esit_dizi_yuzde_yuz() -> None:
    a = list(range(50))
    h = rk.hizala(a, a)
    assert h.bloklar == [(0, 0, 50)]
    assert h.hizalanamayan_bolge == 0


def test_karsilastirma_hizala_bos_girdi() -> None:
    assert rk.hizala([], []).bloklar == []
    assert rk.hizala([1, 2, 3], []).bloklar == []
    assert rk.hizala([], [1, 2, 3]).bloklar == []


def test_karsilastirma_hizala_ekleme_silme_degisim() -> None:
    a = list(range(20))
    ekleme = [*a[:10], 99, *a[10:]]
    assert eslesen(a, ekleme) == 20
    assert eslesen(ekleme, a) == 20
    silme = a[:7] + a[8:]
    assert eslesen(a, silme) == 19
    degisim = [*a[:5], 77, *a[6:]]
    assert eslesen(a, degisim) == 19


def test_karsilastirma_hizala_buyuk_bolge_benzersiz_dizi_ile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rk, "DP_SINIRI", 100)  # difflib yolunu kapat: anchor yolu denenir
    a = list(range(400))
    b = [*a[:100], 1001, 1002, 1003, *a[103:250], *a[260:]]
    h = rk.hizala(a, b)
    assert sum(n for _, _, n in h.bloklar) == 400 - 3 - 10
    assert h.hizalanamayan_bolge == 0
    # bloklar iki dizide de artan
    onceki = (0, 0)
    for i, j, n in h.bloklar:
        assert i >= onceki[0] and j >= onceki[1]
        onceki = (i + n, j + n)


def test_karsilastirma_hizala_hizalanamayan_bolge_sayilir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rk, "DP_SINIRI", 10)
    a = [1, 2] * 60
    b = [2, 1] * 60  # k-kelimelik benzersiz dizi yok, onek ve sonek eslesmez
    h = rk.hizala(a, b)
    assert h.hizalanamayan_bolge == 1
    assert h.hizalanamayan_a > 0 and h.hizalanamayan_b > 0


# --- akis karsilastirmasi ------------------------------------------------------------------


def birimler(*metinler: str, dosya: int = 1, onek: str = "rn:deneme:p") -> list[Birim]:
    return [Birim(f"{onek}{i}", m, dosya) for i, m in enumerate(metinler, start=1)]


def test_karsilastirma_akis_esit_metin_yuzde_yuz() -> None:
    a = birimler("deneme paragraf bir", "deneme paragraf iki")
    s = rk.akis_karsilastir(a, a)
    assert (s.diyanet_kelime, s.rnk_kelime, s.eslesen) == (6, 6, 6)
    assert s.farklar == []
    assert s.yazim_farki == 0
    assert s.dosyalar == {1: [6, 6]}


def test_karsilastirma_akis_ekleme_silme_ve_yazim_farki_sayilari() -> None:
    d = birimler("zzbir zziki zzuc zzdort", "zzbes zzalti")
    r = [
        Birim(
            "rn:r:p1", "zzbir zziki zzüc zzdort", 0
        ),  # sapkali/ussuz harf: gevsek esit, siki farkli
        Birim("rn:r:p2", "zzekstra zzbes zzalti", 0),  # bir kelime ekleme
    ]
    s = rk.akis_karsilastir(d, r)
    assert s.diyanet_kelime == 6 and s.rnk_kelime == 7
    assert s.eslesen == 6
    assert s.yazim_farki == 1
    assert [f.tur for f in s.farklar] == ["yalniz-rnk"]
    assert s.farklar[0].rnk_kelime == 1
    assert s.farklar[0].rnk_capa == "rn:r:p2" and s.farklar[0].diyanet_capa is None

    s2 = rk.akis_karsilastir(r, d)  # ters yon: silme
    assert s2.eslesen == 6
    assert [f.tur for f in s2.farklar] == ["yalniz-diyanet"]


def test_karsilastirma_akis_degisen_kelime_farkli_bolge() -> None:
    d = birimler("zza zzb zzc zzd zze")
    r = [Birim("rn:r:p1", "zza zzb zzx zzd zze", 0)]
    s = rk.akis_karsilastir(d, r)
    assert s.eslesen == 4
    assert [(f.tur, f.diyanet_kelime, f.rnk_kelime) for f in s.farklar] == [("farkli", 1, 1)]
    assert s.farklar[0].diyanet_capa == "rn:deneme:p1"


def test_karsilastirma_akis_bos_girdi() -> None:
    s = rk.akis_karsilastir([], [])
    assert (s.diyanet_kelime, s.rnk_kelime, s.eslesen, s.farklar) == (0, 0, 0, [])
    s = rk.akis_karsilastir(birimler("zza zzb"), [])
    assert s.eslesen == 0 and s.farklar[0].tur == "yalniz-diyanet"
    ozet = rk.akis_ozeti(rk.akis_karsilastir([], []))
    assert ozet["eslesen_oran_diyanet"] is None  # sifira bolme yok


def test_karsilastirma_dosya_bazinda_sayilar() -> None:
    d = birimler("zza zzb", dosya=1) + birimler("zzc zzd", dosya=2, onek="rn:d2:p")
    r = [Birim("rn:r:p1", "zza zzb zzc", 0)]
    s = rk.akis_karsilastir(d, r)
    assert s.dosyalar == {1: [2, 2], 2: [2, 1]}


@pytest.mark.parametrize(
    ("uzunluk", "kova"),
    [(1, "1"), (2, "2-3"), (3, "2-3"), (4, "4-9"), (9, "4-9"), (10, "10-49"), (49, "10-49"),
     (50, "50+"), (5000, "50+")],
)  # fmt: skip
def test_karsilastirma_fark_kovasi(uzunluk: int, kova: str) -> None:
    assert rk.fark_kovasi(uzunluk) == kova


def test_karsilastirma_ortusme_tasinan_blok_siraya_bakmaz() -> None:
    d = [birimler("zza zzb zzc zzd")]
    r = [birimler("zzc zzd"), birimler("zza zzb")]  # blok sirasi ters
    o = rk.ortusme_hesapla(d, r, k=2)
    assert (o.diyanet_kelime, o.diyanet_kapsanan) == (4, 4)
    assert (o.rnk_kelime, o.rnk_kapsanan) == (4, 4)
    assert o.dosyalar == {1: [4, 4]}
    kisa = rk.ortusme_hesapla([birimler("zza")], [birimler("zza")], k=2)
    assert kisa.diyanet_kapsanan == 0  # pencereden kisa akis kapsanmaz


def test_karsilastirma_ozet_metin_icermez() -> None:
    d = birimler("zzgizli zzmetin bir", "zzgizli zzmetin iki")
    r = [Birim("rn:r:p1", "zzgizli zzmetin bir zzgizli zzekstra", 0)]
    s = rk.akis_karsilastir(d, r)
    ozet = json.dumps(rk.kitap_ozeti(s, rk.akis_karsilastir([], []), rk.ortusme_hesapla([d], [r])))
    assert "zzgizli" not in ozet and "zzmetin" not in ozet and "zzekstra" not in ozet
    assert "rn:deneme:p" in ozet  # yalniz capa


# --- staged okuma ve rapor -----------------------------------------------------------------

KLASOR = "01 Deneme"
DOSYALAR = ("Deneme-01-Bir.txt", "Deneme-02-Iki.txt", "Deneme-03-Uc.txt", "Deneme-04-Dort.txt")


def tablo_kur(slug: str = "sozler") -> tuple[Kitap, ...]:
    diyanetli = Kitap(
        slug=slug,
        baslik="Deneme",
        dil="tr",
        yon="ltr",
        metin_kaynagi="rnk",
        diyanet_karsiligi="diyanet",
        diyanet=Diyanet(KLASOR, DOSYALAR),
        rnk=RnkBaglanti("tr", "deneme", "Deneme"),
        dogrulandi=False,
    )
    derleme = Kitap(
        slug="deneme-derleme",
        baslik="Deneme derleme",
        dil="tr",
        yon="ltr",
        metin_kaynagi="rnk",
        diyanet_karsiligi="derleme",
        diyanet=None,
        rnk=RnkBaglanti("tr_k", "derleme", "Deneme derleme"),
        dogrulandi=False,
    )
    return (diyanetli, derleme)


def jsonl_yaz(yol: Path, satirlar: list[dict[str, object]]) -> Path:
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(
        "".join(json.dumps(s, ensure_ascii=False) + "\n" for s in satirlar), encoding="utf-8"
    )
    return yol


def diyanet_birimi(
    slug: str, bolum: str, p: int, metin: str, dosya_sira: int, satir: int, rol: str = "paragraf"
) -> dict[str, object]:
    capa = f"rn:{slug}:{bolum}:p{p}" if rol != "dipnot" else f"rn:{slug}:{bolum}:hasiye-1:p{p}"
    return {
        "anchor": capa,
        "attrs": {"rol": rol},
        "provenance": {
            "dosya": f"txt/{KLASOR}/{DOSYALAR[dosya_sira - 1]}",
            "kaynak": "txt",
            "satir": satir,
        },
        "text": metin,
    }


def rnk_birimi(
    slug: str, p: int, metin: str, satir: int, kind: str = "paragraf"
) -> dict[str, object]:
    return {
        "anchor": f"rn:{slug}:p{p}",
        "attrs": {"slug": slug, "kind": kind},
        "provenance": {"konum": {"satir": [satir, satir]}},
        "text": metin,
    }


@pytest.fixture
def staged(tmp_path: Path) -> tuple[Path, Path]:
    d: list[dict[str, object]] = []
    r: list[dict[str, object]] = []
    for sira in range(1, 5):
        d.append(
            diyanet_birimi("sozler", f"b{sira}", 1, f"zzmetin{sira} zzortak zzson{sira}", sira, 1)
        )
    d.append(diyanet_birimi("sozler", "b4", 2, "zzdipnot zzbir", 4, 2, rol="dipnot"))
    # RNK: satir sirasi karisik verilir; okuma sirasi `konum.satir` ile kurulur
    for sira in (4, 3, 2, 1):
        r.append(rnk_birimi("sozler", sira, f"zzmetin{sira} zzortak zzson{sira}", sira * 10))
    r.append(rnk_birimi("sozler", 5, "zzdipnot zzbir zzekstra", 99, kind="hasiye"))
    r.append(rnk_birimi("deneme-derleme", 1, "zzbaska kitap", 1))
    return (
        jsonl_yaz(tmp_path / "diyanet" / "units.jsonl", d),
        jsonl_yaz(tmp_path / "rnk" / "units.jsonl", r),
    )


def test_karsilastirma_diyanet_oku_ana_ve_dipnot_ayri_ve_dosya_sirali(
    staged: tuple[Path, Path],
) -> None:
    tablo = tablo_kur()
    kitap = rk.diyanet_oku(staged[0], {k.slug: k for k in tablo}, ["sozler"])["sozler"]
    assert [b.dosya for b in kitap.ana] == [1, 2, 3, 4]
    assert [b.capa for b in kitap.dipnot] == ["rn:sozler:b4:hasiye-1:p2"]
    assert kitap.dipnot[0].dosya == 4


def test_karsilastirma_diyanet_oku_bilinmeyen_dosya_hata(tmp_path: Path) -> None:
    yol = jsonl_yaz(
        tmp_path / "u.jsonl",
        [
            {
                "anchor": "rn:sozler:b1:p1",
                "attrs": {"rol": "paragraf"},
                "provenance": {"dosya": "txt/baska/dosya.txt", "kaynak": "txt", "satir": 1},
                "text": "zz",
            }
        ],
    )
    tablo = tablo_kur()
    with pytest.raises(GirdiHatasi, match="tablosunda yok"):
        rk.diyanet_oku(yol, {k.slug: k for k in tablo}, ["sozler"])


def test_karsilastirma_rnk_oku_belge_sirasi(staged: tuple[Path, Path]) -> None:
    kitap = rk.rnk_oku(staged[1], ["sozler"])["sozler"]
    assert [b.capa for b in kitap.ana] == [f"rn:sozler:p{i}" for i in (1, 2, 3, 4)]
    assert [b.capa for b in kitap.dipnot] == ["rn:sozler:p5"]


def test_karsilastirma_rnk_oku_gecersiz_json(tmp_path: Path) -> None:
    yol = tmp_path / "u.jsonl"
    yol.write_text("{bozuk\n", encoding="utf-8")
    with pytest.raises(GirdiHatasi, match="gecersiz JSON"):
        rk.rnk_oku(yol, ["sozler"])


def test_karsilastirma_diyanet_kitaplari_yalniz_diyanet_karsiligi() -> None:
    assert [k.slug for k in rk.diyanet_kitaplari(tablo_kur())] == ["sozler"]


def test_karsilastirma_rapor_bicimi_referans_ve_metin_sizintisi_yok(
    staged: tuple[Path, Path],
) -> None:
    rapor = rk.rapor_uret(tablo_kur(), staged[0], staged[1])
    kitap = rapor["kitaplar"]
    assert isinstance(kitap, dict) and list(kitap) == ["sozler"]  # derleme kitap yok
    s = kitap["sozler"]
    assert s["diyanet_kelime"] == 14 and s["rnk_kelime"] == 15
    assert s["ana_metin"]["eslesen_oran_diyanet"] == 1.0
    assert s["dipnot"]["rnkda_olup_diyanette_olmayan"] == 1
    assert s["ortusme"]["diyanet_oran"] == 1.0
    assert [d["dosya_sira"] for d in s["dosyalar"]] == [1, 2, 3, 4]
    ref = rapor["referans_kontrolu"]
    assert ref["yapildi"] is True and ref["dosya_sirasi"] == [2, 3, 4]
    assert ref["ana_metin_tutuyor"] is True
    assert ref["hepsi_tutuyor"] is True  # dosya 4'un dipnotu tamami Diyanet'te de RNK'da da var
    govde = json.dumps(rapor, ensure_ascii=False)
    for sizinti in ("zzmetin", "zzortak", "zzdipnot", "zzekstra", "zzbaska"):
        assert sizinti not in govde
    # yalniz sayi, oran ve capa: baslik ve sozcuk listesi alani yok
    assert "rn:sozler:p5" in govde


def test_karsilastirma_referans_kontrolu_eksik_kitap_ve_tutmayan_oran() -> None:
    assert rk.referans_kontrolu({}) == {"kitap": "sozler", "yapildi": False}

    def dosya(sira: int, ana: float, toplam: float, ortusme: float) -> dict[str, object]:
        return {
            "dosya_sira": sira,
            "ana_metin": {"eslesen_oran": ana},
            "toplam": {"eslesen_oran": toplam},
            "ortusme": {"oran": ortusme},
        }

    dosyalar = [dosya(2, 1.0, 0.97, 1.0), dosya(3, 1.0, 1.0, 1.0), dosya(4, 1.0, 1.0, 1.0)]
    satirlar = {"sozler": {"dosyalar": dosyalar}}
    ref = rk.referans_kontrolu(satirlar)
    assert ref["ana_metin_tutuyor"] is True
    assert ref["hepsi_tutuyor"] is False
    eksik = rk.referans_kontrolu({"sozler": {"dosyalar": [dosya(2, 1.0, 1.0, 1.0)]}})
    assert eksik["ana_metin_tutuyor"] is False  # uc dosyanin hepsi bulunmali


def test_karsilastirma_son_calisma_en_yeni_run(tmp_path: Path) -> None:
    for ad in ("01a", "01c", "01b"):
        (tmp_path / ad).mkdir()
        (tmp_path / ad / "units.jsonl").write_bytes(b"")
    (tmp_path / "01z").mkdir()  # units.jsonl yok: atlanir
    assert rk.son_calisma(tmp_path, None).name == "01c"
    with pytest.raises(GirdiHatasi, match="bulunamadi"):
        rk.son_calisma(tmp_path / "01z", None)


def test_karsilastirma_son_calisma_adima_gore(tmp_path: Path) -> None:
    for ad, adim in (("01a", "ingest"), ("01b", "ingest"), ("01c", "normalize"), ("01d", "anchor")):
        (tmp_path / ad).mkdir()
        (tmp_path / ad / "units.jsonl").write_bytes(b"")
        (tmp_path / ad / "manifest.json").write_text(json.dumps({"adim": adim}), encoding="utf-8")
    (tmp_path / "01e").mkdir()  # manifest yok
    (tmp_path / "01e" / "units.jsonl").write_bytes(b"")
    assert rk.son_calisma(tmp_path).name == "01b"  # varsayilan: ingest
    assert rk.son_calisma(tmp_path, "anchor").name == "01d"
    assert rk.son_calisma(tmp_path, None).name == "01e"
    with pytest.raises(GirdiHatasi, match="bulunamadi"):
        rk.son_calisma(tmp_path, "yok")


def test_karsilastirma_rnk_birim_turu_iki_bicim() -> None:
    assert rk.rnk_birim_turu({"attrs": {"kind": "hasiye"}}) == "hasiye"  # ingest bicimi
    assert rk.rnk_birim_turu({"kind": "baslik", "attrs": {}}) == "baslik"  # anchor bicimi
    assert rk.rnk_birim_turu({"attrs": {}}) is None
    assert rk.rnk_kitap_slugu("rn:deneme:bolum:p3") == "deneme"
    with pytest.raises(GirdiHatasi):
        rk.rnk_kitap_slugu("q:2:255")


def test_karsilastirma_rnk_oku_anchor_bicimi(tmp_path: Path) -> None:
    yol = jsonl_yaz(
        tmp_path / "u.jsonl",
        [
            {
                "anchor": "rn:sozler:p1",
                "kind": "paragraf",
                "attrs": {},
                "provenance": {"konum": {"satir": [2, 2]}},
                "text": "zza zzb",
            },
            {
                "anchor": "rn:sozler:hasiye-1:p1",
                "kind": "hasiye",
                "attrs": {},
                "provenance": {"konum": {"satir": [3, 3]}},
                "text": "zzc",
            },
        ],
    )
    kitap = rk.rnk_oku(yol, ["sozler"])["sozler"]
    assert [b.capa for b in kitap.ana] == ["rn:sozler:p1"]
    assert [b.capa for b in kitap.dipnot] == ["rn:sozler:hasiye-1:p1"]
