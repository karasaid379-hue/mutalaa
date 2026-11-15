# ruff: noqa: RUF001
"""Lugat kaynaklari `lugat-rnk` ve `lugat-sozluk-rganeyev` ingest'i (A20.6b; SENTETIK veri).

Hicbir lugat metni yoktur: baslik sozler "denemea", "denemeb" ..., tanimlar "TANIM-RNK-n" ve
"TANIM-RG-n" imzalidir; ciktilara (rapor, gunluk, manifest) yalniz sayi girdigi imzalarin
sizmamasiyla sinanir. Veritabani yoktur.
"""

import json
from pathlib import Path

import pytest
from hat_yardimci import ansisiz
from lugat_kaynak_yardimci import (
    NBSP,
    NFD_TANIM,
    RG_SATIRLARI,
    RNK_SATIRLARI,
    TANIM_RG,
    TANIM_RNK,
    TARIH_LUGAT,
    KaynakKoku,
    dosya_metni,
    kaynak_hazirla,
)
from typer.testing import CliRunner

from mutalaa_pipeline import cli
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import lugat_kaynak
from mutalaa_pipeline.ingest.lugat_kaynak import (
    BICIMLER,
    KAYNAK_RGANEYEV,
    KAYNAK_RNK,
    SAYI_ANAHTARLARI,
    ayristir,
    esleme_anahtari,
    kaynaklar_nesnesi,
    kilit_coz,
    kilit_denetle,
    kilit_metni,
    risale_dizini,
    sayilari_hesapla,
    sec,
    terkip_anahtari,
)
from mutalaa_pipeline.ingest.lugat_madde import (
    MADDE_ALANLARI_KAYNAK,
    madde_hash,
)

runner = CliRunner()
RNK = BICIMLER[KAYNAK_RNK]
RG = BICIMLER[KAYNAK_RGANEYEV]


@pytest.fixture
def kk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> KaynakKoku:
    return kaynak_hazirla(tmp_path, monkeypatch)


def parcala(satirlar: list[str], bicim: lugat_kaynak.Bicim = RNK) -> lugat_kaynak.Ayristirma:
    return ayristir(dosya_metni(satirlar), bicim)


# --- ayristirma: anlam_no, bozuk satir, kirpma ----------------------------------------------


def test_rnk_ayristirma_sayilari_anlam_no_ve_bozuk_satirlar() -> None:
    ayr = parcala(RNK_SATIRLARI)
    assert ayr.satir == len(RNK_SATIRLARI)
    assert ayr.bozuk == {
        "bos_satir": 1,
        "nul": 1,
        "ayracsiz": 1,
        "bos_baslik": 1,
        "bos_tanim": 1,
        "normsuz": 1,
    }
    assert len(ayr.maddeler) == 8
    anlamlar = [(m.baslik, m.anlam_no) for m in ayr.maddeler]
    # satir sirasi = anlam sirasi; ham baslik bayt bayt esit olanlar numaralanir
    assert anlamlar[:3] == [("denemea", 1), ("denemea", 2), ("Denemea", 1)]
    assert ayr.kirpilan_baslik == 1 and ayr.kirpilan_tanim == 1
    sayilar = sayilari_hesapla(ayr, sec(RNK, ayr, None))
    assert set(sayilar) == set(SAYI_ANAHTARLARI)
    assert sayilar["gecerli_madde"] == 8 and sayilar["alinan_madde"] == 8
    assert sayilar["benzersiz_ham_baslik"] == 7  # birlestirme yok: "denemea" ve "Denemea" ayri
    assert sayilar["benzersiz_esleme_anahtari"] == 6  # ... ama esleme anahtari tek
    assert sayilar["cok_anlamli_baslik"] == 1 and sayilar["en_cok_anlam"] == 2


def test_normalize_baslik_tekil_degil_ve_birlestirilmez() -> None:
    ayr = parcala([f"denemea|{TANIM_RNK}-1", f"Denemea|{TANIM_RNK}-2", f"DENEMEA|{TANIM_RNK}-3"])
    assert len({m.norm for m in ayr.maddeler}) == 1  # basliksoz_norm ayni
    assert [(m.baslik, m.anlam_no) for m in ayr.maddeler] == [
        ("denemea", 1),
        ("Denemea", 1),
        ("DENEMEA", 1),
    ]  # her ham baslik kendi anlam_no dizisini baslatir


def test_tanim_bayt_bayt_yalniz_bosluk_ve_sekme_kirpilir() -> None:
    ayr = parcala(RNK_SATIRLARI)
    tanimlar = {m.baslik: m.tanim for m in ayr.maddeler if m.anlam_no == 1}
    assert tanimlar["denemec"] == f"{TANIM_RNK}-5 | ic ayrac korunur"  # ilk '|' ayrac
    assert tanimlar["yenia"] == NFD_TANIM  # NFC uygulanmadi: e + U+0301
    assert "\N{COMBINING ACUTE ACCENT}" in tanimlar["yenia"]
    assert tanimlar["yenib"] == f"{NBSP}{TANIM_RNK}-7{NBSP}"  # U+00A0 kirpilmaz (strip() keserdi)
    assert tanimlar["denemeb"] == f"{TANIM_RNK}-4"  # baslikta son bosluk kirpildi
    # tanim baytlari kaynak satirinin dilimiyle birebir (kirpma hari)
    kaynak = {s.partition("|")[0].strip(" \t"): s.partition("|")[2] for s in RNK_SATIRLARI[3:7]}
    for baslik, tanim in tanimlar.items():
        if baslik in kaynak:
            assert tanim.encode() == kaynak[baslik].strip(" \t").encode()


def test_rganeyev_ayraci_ilk_iki_nokta_ve_ayractan_sonraki_tek_bosluk() -> None:
    ayr = parcala(RG_SATIRLARI, RG)
    assert ayr.bozuk["ayracsiz"] == 1
    tanim = {m.baslik: m.tanim for m in ayr.maddeler}
    assert tanim["rgbitisik"] == f"{TANIM_RG}-7"  # ayractan sonra bosluk olmayan satir
    assert tanim["Denemea"] == f"{TANIM_RG}-2"  # "Denemea : ..." -> baslikta son bosluk kirpilir
    assert ayr.kirpilan_baslik == 1  # yalniz bu baslik
    assert ayr.kirpilan_tanim == 0  # ayractaki tek bosluk kirpma sayilmaz
    cift = parcala([f"a: b: {TANIM_RG}"], RG).maddeler[0]
    assert (cift.baslik, cift.tanim) == ("a", f"b: {TANIM_RG}")  # ilk ':' ayrac


@pytest.mark.parametrize(
    ("veri", "neden"),
    [
        (b"\xef\xbb\xbfa|b\n", "BOM"),
        (b"a|b\r\nc|d\n", "CR"),
        (b"a|\xff\n", "UTF-8"),
        (b"", "bos"),
    ],
)
def test_dosya_duzeyi_hatalar_girdi_hatasi(veri: bytes, neden: str) -> None:
    with pytest.raises(GirdiHatasi, match=neden if neden != "bos" else "bos"):
        ayristir(veri, RNK)


def test_yalniz_satir_sonu_madde_vermez_bozuk_satir_sayilir() -> None:
    ayr = ayristir(b"\n", RNK)  # hata degil: kilit sayilariyla tutmaz
    assert ayr.maddeler == [] and ayr.bozuk["bos_satir"] == 1


def test_cok_buyuk_dosya_reddedilir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lugat_kaynak, "EN_BUYUK_BAYT", 8)
    with pytest.raises(GirdiHatasi, match="cok buyuk"):
        ayristir(b"a|bcdefghij\n", RNK)


def test_son_lf_olmayan_ve_olan_dosya_ayni_maddeleri_verir() -> None:
    a = ayristir(dosya_metni(["a|b", "c|d"]), RNK)
    b = ayristir(dosya_metni(["a|b", "c|d"], son_lf=True), RNK)
    assert a.maddeler == b.maddeler and a.satir == b.satir == 2


# --- yalniz RNK'da olmayan secim ---------------------------------------------------------------


def test_rganeyev_yalniz_rnkda_olmayan_basliklari_birlikte_alir() -> None:
    rnk = parcala(RNK_SATIRLARI)
    rg = parcala(RG_SATIRLARI, RG)
    secilen = sec(RG, rg, lugat_kaynak.rnk_anahtarlari(rnk))
    assert [(m.baslik, m.anlam_no) for m in secilen] == [
        ("denemed", 1),
        ("denemed", 2),  # ayni basligin iki satiri birlikte
        ("rgyeni", 1),
        ("\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}stekrg", 1),
        ("rgbitisik", 1),
    ]
    sayilar = sayilari_hesapla(rg, secilen)
    assert sayilar["alinan_madde"] == 5 and sayilar["alinan_ham_baslik"] == 4
    assert sayilar["gecerli_madde"] == 8 and sayilar["bozuk_ayracsiz"] == 1
    # parantezli yazim ("denemee (deneme) f") RNK'nin "denemee deneme f" basligiyla ayni anahtar
    assert "denemee (deneme) f" not in {m.baslik for m in secilen}


def test_i_sapkali_kusur_sayaci_duzeltmez() -> None:
    rnk = parcala(RNK_SATIRLARI)
    rg = parcala(RG_SATIRLARI, RG)
    secilen = sec(RG, rg, lugat_kaynak.rnk_anahtarlari(rnk))
    sayilar = sayilari_hesapla(rg, secilen)
    assert sayilar["i_sapkali_baslik"] == 1 and sayilar["i_sapkali_sozcuk_basi"] == 1
    assert "\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}stekrg" in {m.baslik for m in secilen}


def test_rganeyev_rnk_olmadan_secim_yapilamaz() -> None:
    with pytest.raises(GirdiHatasi, match="RNK"):
        sec(RG, parcala(RG_SATIRLARI, RG), None)


# --- esleme anahtari ve Risale baslik soz eslemesi ----------------------------------------------


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("denemeI", "deneme\N{LATIN SMALL LETTER DOTLESS I}"),  # I -> noktasiz i (acik esleme)
        ("DENEME\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}", "denemei"),  # noktali I -> i
        ("kâğıt", "kagit"),  # sapka ve ust isaret atilir
        ("kâ'be", "kabe"),  # kesme
        ("ab-cd", "abcd"),  # tire
        ("denemee (deneme) f", "denemee deneme f"),  # parantez ve bosluk
        ("deneme\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}", "denemei"),
    ],
)
def test_esleme_anahtari_kurallari(a: str, b: str) -> None:
    assert esleme_anahtari(a) == esleme_anahtari(b)


def test_esleme_anahtari_farkli_sozleri_ayirir() -> None:
    assert esleme_anahtari("denemea") != esleme_anahtari("denemeb")
    assert esleme_anahtari("((") == ""  # harf/rakam yok
    assert terkip_anahtari("denemee  (deneme)  f") == "denemee deneme f"  # sozcuk siniri kalir
    assert terkip_anahtari("denemeed") != terkip_anahtari("denemee d")


def kf_satir(soz: str, siklik: int, kitaplar: dict[str, int]) -> dict[str, object]:
    return {"basliksoz": soz, "kaynaklar": {"siklik": siklik, "kitaplar": kitaplar}}


def test_risale_dizini_ayni_anahtara_dusen_sozleri_toplar_en_sik_sozu_yazar() -> None:
    dizin = risale_dizini(
        [
            kf_satir("Denemea", 5, {"k1": 5}),
            kf_satir("denemea", 120, {"k1": 100, "k2": 20}),
            kf_satir("denemeb", 3, {"k2": 3}),
        ]
    )
    toplu = dizin[esleme_anahtari("denemea")]
    assert toplu.toplam == 125 and toplu.kitaplar == {"k1": 105, "k2": 20}
    assert toplu.soz == "denemea"  # en sik soz, ham yazim
    assert dizin[esleme_anahtari("denemeb")].soz == "denemeb"


def test_risale_dizini_bozuk_satir_girdi_hatasi() -> None:
    for kotu in (
        {"basliksoz": "a"},
        {"basliksoz": "a", "kaynaklar": {"siklik": 0, "kitaplar": {}}},
        {"basliksoz": "a", "kaynaklar": {"siklik": 1, "kitaplar": {"k": "x"}}},
    ):
        with pytest.raises(GirdiHatasi):
            risale_dizini([kotu])


def test_kaynaklar_nesnesi_eslesen_ve_eslesmeyen_duzey() -> None:
    dizin = risale_dizini(
        [
            kf_satir("denemea", 150, {"k1": 150}),
            kf_satir("denemeb", 30, {"k1": 30}),
            kf_satir("denemec", 7, {"k1": 7}),
        ]
    )
    for soz, duzey in (("denemea", 1), ("denemeb", 2), ("denemec", 3)):
        kaynaklar, d = kaynaklar_nesnesi(esleme_anahtari(soz), dizin)
        assert d == duzey
        assert set(kaynaklar) == {
            "kelime_frekans_karsiligi",
            "risale_basliksoz",
            "siklik",
            "kitaplar",
        }
        assert (
            kaynaklar["kelime_frekans_karsiligi"] is True and kaynaklar["risale_basliksoz"] == soz
        )
    kaynaklar, d = kaynaklar_nesnesi(esleme_anahtari("yenia"), dizin)
    assert (kaynaklar, d) == ({"kelime_frekans_karsiligi": False}, 4)  # siklik/kitaplar yok
    assert kaynaklar_nesnesi("", dizin) == ({"kelime_frekans_karsiligi": False}, 4)


# --- kilit -------------------------------------------------------------------------------------


def test_kilit_gidis_donus_ve_kati_cozum(kk: KaynakKoku) -> None:
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        ham = lugat_kaynak.KILIT_YOLLARI[slug].read_bytes()
        kilit = kilit_coz(slug, ham)
        assert kilit_metni(kilit).encode() == ham
        assert set(kilit.sayilar) == set(SAYI_ANAHTARLARI)
    veri = json.loads(lugat_kaynak.KILIT_YOLLARI[KAYNAK_RNK].read_bytes())
    for degisim in ({"fazladan": 1}, {"surum": 2}, {"sha256": "xyz"}, {"dosya": "baska.txt"}):
        kotu = json.dumps({**veri, **degisim}).encode()
        with pytest.raises(GirdiHatasi):
            kilit_coz(KAYNAK_RNK, kotu)
    eksik = {a: v for a, v in veri.items() if a != "sayilar"}
    with pytest.raises(GirdiHatasi):
        kilit_coz(KAYNAK_RNK, json.dumps(eksik).encode())


def test_kilit_denetle_ozet_boyut_ve_sayilar(kk: KaynakKoku) -> None:
    kilit = lugat_kaynak.kilit_yukle(KAYNAK_RNK)
    ayr = ayristir(kk.rnk, RNK)
    sayilar = sayilari_hesapla(ayr, sec(RNK, ayr, None))
    kilit_denetle(kilit, kk.rnk, sayilar)
    with pytest.raises(GirdiHatasi, match="ozeti kilitle tutmuyor"):
        kilit_denetle(kilit, kk.rnk + b"x", sayilar)
    with pytest.raises(GirdiHatasi, match="sayilar kilitle tutmuyor"):
        kilit_denetle(kilit, kk.rnk, {**sayilar, "alinan_madde": 1})


# --- ingest: staged satirlari ------------------------------------------------------------------


def test_rnk_ingest_staged_satirlari(kk: KaynakKoku) -> None:
    assert kk.ingest(KAYNAK_RNK) == 0
    satirlar = kk.satirlar(KAYNAK_RNK)
    assert len(satirlar) == 8
    assert [(s["basliksoz"], s["anlam_no"]) for s in satirlar] == sorted(
        (s["basliksoz"], s["anlam_no"])
        for s in satirlar  # type: ignore[type-var]
    )  # (basliksoz, anlam_no) sirali
    for s in satirlar:
        assert set(s) == set(MADDE_ALANLARI_KAYNAK)
        assert (s["status"], s["origin"], s["version"], s["source_id"]) == (
            "aday",
            "kaynak",
            1,
            KAYNAK_RNK,
        )
        assert s["content_hash"] == madde_hash(str(s["basliksoz"]), str(s["tanim_tr"]))
        assert s["osmanlica_yazim"] is None and s["koken_dil"] is None and s["ar_kok_id"] is None
    ilk = kk.madde(KAYNAK_RNK, "denemea", 1)
    assert ilk["tanim_tr"] == f"{TANIM_RNK}-1"
    assert kk.madde(KAYNAK_RNK, "denemea", 2)["tanim_tr"] == f"{TANIM_RNK}-2"
    assert kk.madde(KAYNAK_RNK, "yenia")["tanim_tr"] == NFD_TANIM  # NFC yok


def test_rnk_eslesme_siklik_kitaplar_duzey(kk: KaynakKoku) -> None:
    assert kk.ingest(KAYNAK_RNK) == 0
    a1, a2, buyuk = (
        kk.madde(KAYNAK_RNK, "denemea", 1),
        kk.madde(KAYNAK_RNK, "denemea", 2),
        kk.madde(KAYNAK_RNK, "Denemea"),
    )
    for m in (a1, a2, buyuk):  # ayni anahtar: her anlam satirina ayni Risale bilgisi
        assert m["duzey"] == 1
        k = m["kaynaklar"]
        assert isinstance(k, dict) and k["kelime_frekans_karsiligi"] is True
        assert k["risale_basliksoz"] == "denemea"  # en sik Risale sozu (ham yazim)
        assert k["siklik"] == 141 and k["kitaplar"] == {
            "1-Deneme Kitap A": 121,
            "2-Deneme Kitap B": 20,
        }
    assert kk.madde(KAYNAK_RNK, "denemeb")["duzey"] == 2
    assert kk.madde(KAYNAK_RNK, "denemec")["duzey"] == 3
    for soz in ("yenia", "yenib", "denemee deneme f"):  # Risale'de yok: duzey 4, siklik yok
        m = kk.madde(KAYNAK_RNK, soz)
        assert m["duzey"] == 4 and m["kaynaklar"] == {"kelime_frekans_karsiligi": False}


def test_rganeyev_ingest_yalniz_rnkda_olmayanlar_ve_duzey(kk: KaynakKoku) -> None:
    assert kk.ingest(KAYNAK_RNK) == 0
    assert kk.ingest(KAYNAK_RGANEYEV) == 0
    satirlar = kk.satirlar(KAYNAK_RGANEYEV)
    assert [(s["basliksoz"], s["anlam_no"]) for s in satirlar] == [
        ("denemed", 1),
        ("denemed", 2),
        ("rgbitisik", 1),
        ("rgyeni", 1),
        ("\N{LATIN SMALL LETTER I WITH CIRCUMFLEX}stekrg", 1),
    ]
    assert {s["source_id"] for s in satirlar} == {KAYNAK_RGANEYEV}
    assert kk.madde(KAYNAK_RGANEYEV, "denemed", 2)["tanim_tr"] == f"{TANIM_RG}-4"
    assert [s["duzey"] for s in satirlar if s["basliksoz"] == "denemed"] == [3, 3]  # 7 gecis
    assert kk.madde(KAYNAK_RGANEYEV, "rgyeni")["duzey"] == 4


def test_ingest_risale_staged_olmadan_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    kok = kaynak_hazirla(tmp_path, monkeypatch, kf_ingest=False)
    assert kok.ingest(KAYNAK_RNK) == 2
    assert "once: ingest lugat --source risale-kelime-frekans" in capsys.readouterr().err
    assert kok.staged_klasorleri(KAYNAK_RNK) == []


def test_rganeyev_rnk_kilidiyle_baglidir(kk: KaynakKoku) -> None:
    yol = lugat_kaynak.KILIT_YOLLARI[KAYNAK_RGANEYEV]
    kilit = json.loads(yol.read_bytes())
    kilit["bagimli_sha256"] = "0" * 64
    yol.write_bytes(json.dumps(kilit).encode())
    assert kk.ingest(KAYNAK_RGANEYEV) == 2
    assert not (kk.veri_kok / "raw" / KAYNAK_RGANEYEV).exists()


# --- idempotentlik, ham kopya, kilit uyusmazligi -----------------------------------------------


def test_ikinci_kosu_bayt_bayt_ayni_ham_kopya_degismez(kk: KaynakKoku) -> None:
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        assert kk.ingest(slug) == 0
        assert kk.ingest(slug, force=True) == 0
        a, b = kk.staged_klasorleri(slug)
        assert (a / "lugat.jsonl").read_bytes() == (b / "lugat.jsonl").read_bytes()
        ham = kk.veri_kok / "raw" / slug / TARIH_LUGAT / BICIMLER[slug].dosya
        assert ham.read_bytes() == kk.gelen(slug).read_bytes()  # ham kopya bayt bayt
        assert sorted(p.name for p in (kk.veri_kok / "raw" / slug).iterdir()) == [TARIH_LUGAT]


def test_kilit_uyusmazliginda_cikis_2_ve_raw_staged_bos(
    kk: KaynakKoku, capsys: pytest.CaptureFixture[str]
) -> None:
    kk.gelen(KAYNAK_RNK).write_bytes(kk.rnk + b"\nyeni|TANIM-DEGISTI")
    assert kk.ingest(KAYNAK_RNK) == 2
    assert "kilit guncellenerek" in capsys.readouterr().err
    assert not (kk.veri_kok / "raw" / KAYNAK_RNK).exists()
    assert kk.staged_klasorleri(KAYNAK_RNK) == []


def test_kayitsiz_kaynak_cikis_2(kk: KaynakKoku) -> None:
    (kk.kok / "pipeline" / "sources" / f"{KAYNAK_RNK}.toml").unlink()
    assert kk.ingest(KAYNAK_RNK) == 2


def agac(kk: KaynakKoku, alt: str) -> dict[str, bytes]:
    kok = kk.veri_kok / alt
    return {
        p.relative_to(kk.veri_kok).as_posix(): p.read_bytes()
        for p in sorted(kok.rglob("*"))
        if p.is_file()
    }


def test_dry_run_hicbir_sey_yazmaz(kk: KaynakKoku) -> None:
    onceki = (agac(kk, "raw"), agac(kk, "staged"))
    assert kk.ingest(KAYNAK_RNK, dry_run=True) == 0
    assert kk.ingest(KAYNAK_RGANEYEV, dry_run=True) == 0
    assert (agac(kk, "raw"), agac(kk, "staged")) == onceki
    assert not (kk.veri_kok / "raw" / KAYNAK_RNK).exists()
    assert kk.staged_klasorleri(KAYNAK_RNK) == []


def test_kelime_frekans_staged_ciktisi_degismez(kk: KaynakKoku) -> None:
    kf = {
        p.relative_to(kk.veri_kok).as_posix(): p.read_bytes()
        for p in (kk.veri_kok / "staged" / "risale-kelime-frekans").rglob("*")
        if p.is_file()
    }
    assert kf
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        assert kk.ingest(slug) == 0
    sonra = {
        p.relative_to(kk.veri_kok).as_posix(): p.read_bytes()
        for p in (kk.veri_kok / "staged" / "risale-kelime-frekans").rglob("*")
        if p.is_file()
    }
    assert sonra == kf  # Kelime-Frekans satirlarina hic dokunulmaz


def test_cikti_gunluk_manifest_ve_rapor_metin_tasimaz(kk: KaynakKoku) -> None:
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        assert kk.ingest(slug) == 0
        assert kk.qa(slug) == 0
    for yol, veri in kk.tum_cikti_baytlari().items():
        if yol.endswith("lugat.jsonl"):
            continue  # tanim yalniz maddede (bayt bayt) bulunur
        metin = veri.decode("utf-8", "replace")
        assert TANIM_RNK not in metin and TANIM_RG not in metin, yol
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        manifest = (kk.staged_klasorleri(slug)[-1] / "manifest.json").read_text(encoding="utf-8")
        ayrintilar = json.loads(manifest)["ayrintilar"]
        assert all(isinstance(v, int) for v in ayrintilar["sayilar"].values())
        assert "denemed" not in manifest and TANIM_RG not in manifest


# --- CLI -------------------------------------------------------------------------------------


def test_cli_yardim_uc_kaynagi_ve_kilit_oneri_anlatir() -> None:
    sonuc = runner.invoke(cli.app, ["ingest", "lugat", "--help"])
    assert sonuc.exit_code == 0
    metin = ansisiz(sonuc.output)
    for parca in (
        "risale-kelime-frekans",
        "lugat-rnk",
        "lugat-sozluk-rganeyev",
        "--kilit-oner",
        "--gelen-tarih",
        "anlam_no",
    ):
        assert parca in metin, parca
    assert "Yeğin" not in metin and "Yegin" not in metin  # atif satiri kaynagin kendi adi


def test_cli_ingest_ve_qa_iki_yeni_kaynak(kk: KaynakKoku) -> None:
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        s1 = runner.invoke(cli.app, ["ingest", "lugat", "--source", slug, "--kok", str(kk.kok)])
        assert s1.exit_code == 0, s1.output
        assert f"ingest {slug}:" in s1.output
        s2 = runner.invoke(cli.app, ["qa", "run", "--source", slug, "--kok", str(kk.kok)])
        assert s2.exit_code == 0, s2.output
        assert "G-KAY gecti, G-BUT gecti, G-CAP gecti, G-NOR gecti" in s2.output


def test_cli_bilinmeyen_lugat_kaynagi_cikis_2(kk: KaynakKoku) -> None:
    sonuc = runner.invoke(
        cli.app, ["ingest", "lugat", "--source", "lugat-baska", "--kok", str(kk.kok)]
    )
    assert sonuc.exit_code == 2
    assert "bilinmeyen lugat kaynagi" in sonuc.output


def test_cli_kilit_oner_mevcut_kilitle_ayni_ve_hicbir_sey_yazmaz(kk: KaynakKoku) -> None:
    onceki = kk.tum_cikti_baytlari()
    for slug in (KAYNAK_RNK, KAYNAK_RGANEYEV):
        sonuc = runner.invoke(
            cli.app,
            ["ingest", "lugat", "--source", slug, "--kilit-oner", "--kok", str(kk.kok)],
        )
        assert sonuc.exit_code == 0, sonuc.output
        assert sonuc.stdout.encode() == lugat_kaynak.KILIT_YOLLARI[slug].read_bytes()
    assert kk.tum_cikti_baytlari() == onceki
    assert not (kk.veri_kok / "raw" / KAYNAK_RNK).exists()
    kotu = runner.invoke(
        cli.app,
        [
            "ingest",
            "lugat",
            "--source",
            KAYNAK_RNK,
            "--kilit-oner",
            "--dry-run",
            "--kok",
            str(kk.kok),
        ],
    )
    assert kotu.exit_code == 2


def test_modul_belgesi_kirpmayi_anlatir() -> None:
    belge = lugat_kaynak.__doc__ or ""
    for parca in ("KIRPMA", "U+0020", "U+0009", "BAYT BAYT", "birlestirme YAPILMAZ"):
        assert parca in belge, parca
