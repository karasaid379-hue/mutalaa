# ruff: noqa: RUF003
"""Kelime-Frekans lugat ingest'i (A20.6; SENTETIK veri, veritabani yok)."""

import json
import unicodedata
from pathlib import Path

import pytest
from hat_yardimci import TEMIZ_GIT
from lugat_yardimci import (
    ALT_A,
    ANLAM_IMZASI,
    COMMIT,
    DENEMEI_BUYUK,
    DENEMEI_NOKTASIZ,
    KITAP_A,
    KITAP_B,
    NFD_SOZ,
    OCR_IMZASI,
    TARIH,
    ZIP_ADI,
    LugatKoku,
    lugat_hazirla,
    sentetik_zip,
)

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest import kelime_frekans
from mutalaa_pipeline.ingest.kelime_frekans import (
    KAYNAK,
    csv_coz,
    frekans_coz,
    kilit_coz,
    kilit_metni,
    oku_zip,
    siniflandir,
)
from mutalaa_pipeline.ingest.lugat_madde import (
    DUZEY_ESIKLERI,
    EN_SEYREK_DUZEY,
    MADDE_ALANLARI,
    duzey_hesapla,
    madde_satiri,
)
from mutalaa_pipeline.ingest.risale_zip import GuvenliZip


@pytest.fixture
def kk(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LugatKoku:
    return lugat_hazirla(tmp_path, monkeypatch)


def madde(kk: LugatKoku, soz: str) -> dict[str, object]:
    (satir,) = [s for s in kk.satirlar() if s["basliksoz"] == soz]
    return satir


# --- ayristirma ----------------------------------------------------------------------------


def test_frekans_coz_toplar_ve_satir_sayar() -> None:
    sonuc, satir = frekans_coz(b"kelime,frekans\nabc,2\nxyz,5\nabc,3\n", "d")
    assert sonuc == {"abc": 5, "xyz": 5}
    assert satir == 3  # yinelenen kelime satiri ayri sayilir


@pytest.mark.parametrize(
    "veri",
    [
        b"\xef\xbb\xbfkelime,frekans\nabc,1\n",  # BOM
        b"kelime,frekans\r\nabc,1\r\n",  # CR
        b"kelime,sayi\nabc,1\n",  # baslik
        b"kelime,frekans\nabc,1",  # son LF yok
        b"kelime,frekans\nabc,0\n",  # siklik >= 1
        b"kelime,frekans\nabc,x\n",
        b"kelime,frekans\nabc,1.5\n",
        b"kelime,frekans\n,3\n",  # bos kelime
        b"kelime,frekans\nab c,3\n",  # bosluk
        b"kelime,frekans\nabc\n",  # ayrac yok
        b"kelime,frekans\n\nabc,1\n",  # bos satir
        b"kelime,frekans\nab\x01c,1\n",  # kontrol karakteri
        b"kelime,frekans\n\xff,1\n",  # UTF-8 degil
    ],
)
def test_frekans_coz_reddeder(veri: bytes) -> None:
    with pytest.raises(GirdiHatasi):
        frekans_coz(veri, "d")


def test_csv_coz_bozuk_satir_sayilir_bos_satir_atlanir() -> None:
    ham = b'"kelime","anlam"\n"a","x"\n"a","x"\n\n"b","y","z"\n"c",""\n"","q"\n"d"\n'
    sayac, bozuk = csv_coz(ham, "d")
    assert sayac == {("a", "x"): 2}
    assert bozuk == 4  # uc sutun, bos anlam, bos kelime, tek sutun


@pytest.mark.parametrize("veri", [b'"kelime","sayi"\n"a","x"\n', b"", b"\xff"])
def test_csv_coz_reddeder(veri: bytes) -> None:
    with pytest.raises(GirdiHatasi):
        csv_coz(veri, "d")


def test_siniflandir_alt_kume_olcuyle() -> None:
    kitap = {"a": 5, "b": 3, "c": 1}
    sonuc = siniflandir(
        {
            "kitap": kitap,
            "alt": {"a": 2, "b": 3},  # alt kume
            "ic-ice": {"a": 1},  # alt kumenin alt kumesi: en buyuk ust kitaptir
            "siklik-fazla": {"a": 6},  # siklik buyuk: alt kume degil
            "sozu-fazla": {"a": 1, "z": 1},  # kitapta olmayan soz: alt kume degil
            "diger-kitap": {"x": 1},
        }
    )
    assert sonuc == {
        "kitap": None,
        "alt": "kitap",
        "ic-ice": "kitap",
        "siklik-fazla": None,
        "sozu-fazla": None,
        "diger-kitap": None,
    }


def test_oku_zip_kitap_alt_kume_ve_birlestirme() -> None:
    okuma = oku_zip(GuvenliZip(sentetik_zip()), COMMIT)
    assert {a: d.ust for a, d in okuma.dosyalar.items()} == {
        KITAP_A: None,
        KITAP_B: None,
        ALT_A: KITAP_A,
    }
    assert okuma.toplam["denemea"] == 140  # 120 + 20; alt kumedeki 10 cift sayilmadi
    assert okuma.toplam["denemeb"] == 30
    assert okuma.kitap_siklik["denemea"] == {KITAP_A: 120, KITAP_B: 20}
    assert okuma.birlesik() == {
        "benzersiz_kelime": len(okuma.toplam),
        "toplam_frekans": sum(okuma.toplam.values()),
        "elenen_noktalama_soz": 1,
        "elenen_noktalama_siklik": 4,
    }


def test_duzey_esikleri() -> None:
    (e1, d1), (e2, d2) = DUZEY_ESIKLERI
    assert duzey_hesapla(e1) == d1 and duzey_hesapla(e1 - 1) == d2
    assert duzey_hesapla(e2) == d2 and duzey_hesapla(e2 - 1) == EN_SEYREK_DUZEY
    assert duzey_hesapla(1) == EN_SEYREK_DUZEY


# --- ingest ----------------------------------------------------------------------------------


def test_ingest_staged_alanlari_ve_sayilari(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    satirlar = kk.satirlar()
    # 8 baslik sozden `(` elenir; Denemea ayri maddedir.
    assert {s["basliksoz"] for s in satirlar} == {
        "denemea",
        "Denemea",
        "denemeb",
        "denemec",
        "denemed",
        DENEMEI_BUYUK,
        DENEMEI_NOKTASIZ,
        NFD_SOZ,
    }
    for s in satirlar:
        assert set(s) == set(MADDE_ALANLARI)
        assert (s["status"], s["origin"], s["version"], s["source_id"]) == (
            "aday",
            "hat",
            1,
            KAYNAK,
        )
        assert s["tanim_tr"] is None  # K-51 madde 10: HER ZAMAN bos
        assert s["osmanlica_yazim"] is None and s["koken_dil"] is None
        assert s["ar_kok_id"] is None
        assert s["data_version"] == f"{KAYNAK}@{COMMIT}"
    a = madde(kk, "denemea")
    assert a["kaynaklar"]["siklik"] == 140  # type: ignore[index]
    assert a["kaynaklar"]["kitaplar"] == {KITAP_A: 120, KITAP_B: 20}  # type: ignore[index]
    assert ALT_A not in a["kaynaklar"]["kitaplar"]  # type: ignore[index]
    duzeyler = {x: madde(kk, x)["duzey"] for x in ("denemea", "denemeb", "denemec")}
    assert duzeyler == {"denemea": 1, "denemeb": 2, "denemec": 3}
    assert a["onerilen_basvuru"]["siklik"] == 140  # type: ignore[index]
    assert a["onerilen_basvuru"]["kitaplar"] == 2  # type: ignore[index]


def test_basvuru_anlamlari_yalniz_onerilende_ve_alt_kume_cift_saymaz(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    basvuru = madde(kk, "denemea")["onerilen_basvuru"]["anlam_basvuru"]  # type: ignore[index]
    # ANLAM-1: A'da 2 (alt kumedeki 1 sayilmaz); ANLAM-2: A'da 1 + B'de 1
    assert basvuru == [
        {"anlam": f"{ANLAM_IMZASI}-1", "sayi": 2},
        {"anlam": f"{ANLAM_IMZASI}-2", "sayi": 2},
    ]
    assert madde(kk, "denemed")["onerilen_basvuru"]["anlam_basvuru"] == [  # type: ignore[index]
        {"anlam": f"{ANLAM_IMZASI}-5", "sayi": 1}
    ]
    assert madde(kk, "denemeb")["onerilen_basvuru"]["anlam_basvuru"] == []  # type: ignore[index]
    # iki sozlu CSV kelimesi hicbir baslik soza eslesmez
    assert not any(f"{ANLAM_IMZASI}-4" in json.dumps(s["onerilen_basvuru"]) for s in kk.satirlar())


def test_anlam_madde_ve_kaynaklara_sizmaz_ciktilar_metin_tasimaz(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    assert kk.qa() == 0
    for s in kk.satirlar():
        govde = {a: v for a, v in s.items() if a != "onerilen_basvuru"}
        metin = json.dumps(govde, ensure_ascii=False)
        assert ANLAM_IMZASI not in metin
        assert OCR_IMZASI not in metin
        assert "anlam_basvuru" not in metin
    # Anlam yalniz lugat.jsonl `onerilen_basvuru` alaninda; manifest, rapor, gunluk metin tasimaz.
    for yol, veri in kk.tum_cikti_baytlari().items():
        metin = veri.decode("utf-8")
        assert OCR_IMZASI not in metin, yol
        if not yol.endswith("lugat.jsonl"):
            assert ANLAM_IMZASI not in metin, yol
            assert "denemea" not in metin, yol
            assert "denemeb" not in metin, yol


def test_basliksoz_bayt_bayt_nfc_uygulanmaz_norm_nfc(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    nfd = madde(kk, NFD_SOZ)
    assert nfd["basliksoz"] == NFD_SOZ and unicodedata.normalize("NFC", NFD_SOZ) != NFD_SOZ
    assert nfd["basliksoz_norm"] == unicodedata.normalize("NFC", str(nfd["basliksoz_norm"]))
    assert not unicodedata.is_normalized("NFC", NFD_SOZ)


def test_turkce_i_acik_eslemesi_ve_ortak_norm(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    buyuk, noktasiz = madde(kk, DENEMEI_BUYUK), madde(kk, DENEMEI_NOKTASIZ)
    assert buyuk["basliksoz_norm"] == noktasiz["basliksoz_norm"] == DENEMEI_NOKTASIZ  # I -> i
    assert madde(kk, "Denemea")["basliksoz_norm"] == "denemea"
    # Ortak normu olan iki maddenin ikisi de ayni basvuruyu gorur (CSV `denemeı` anlami).
    for s in (buyuk, noktasiz):
        assert s["onerilen_basvuru"]["anlam_basvuru"] == [  # type: ignore[index]
            {"anlam": f"{ANLAM_IMZASI}-3", "sayi": 1}
        ]
    assert madde(kk, "Denemea")["onerilen_basvuru"] == madde(kk, "denemea")["onerilen_basvuru"] | {
        "siklik": 1,
        "kitaplar": 1,
    }


def test_sozluk_isabeti_yalniz_konum(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    isabet = madde(kk, "denemeb")["kaynaklar"]["sozluk_isabet"]  # type: ignore[index]
    assert isabet == [
        {"sozluk": "lugat-redhouse-1890", "bulundu": False, "satir_no": None},
        {"sozluk": "lugat-kamus-i-turki", "bulundu": True, "satir_no": 2},
        {"sozluk": "lugat-naci", "bulundu": False, "satir_no": None},
    ]
    for kayit in isabet:
        assert set(kayit) == {"sozluk", "bulundu", "satir_no"}
    # Ornek cok kucuk (7 soz): olcum yine yapilir ve guvenilmez bayragi ciktida durur.
    guvenilmez = madde(kk, "denemeb")["kaynaklar"]["sozluk_guvenilmez"]  # type: ignore[index]
    assert "lugat-naci" in guvenilmez


def test_ingest_ham_kopya_zip_acilmaz_betik_calismaz(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    assert (kk.veri_kok / "raw" / KAYNAK / TARIH / ZIP_ADI).read_bytes() == kk.zip_verisi
    for sozluk in kk.ocr:
        ham = kk.veri_kok / "raw" / sozluk / TARIH / "ocr_djvu.txt"
        assert ham.read_bytes() == kk.ocr[sozluk]
    # zip diske acilmadi: gelen klasorunde yalniz zip, raw'da yalniz zip ve fetch.json
    assert [p.name for p in (kk.veri_kok / "gelen" / KAYNAK / TARIH).iterdir()] == [ZIP_ADI]
    assert sorted(p.name for p in (kk.veri_kok / "raw" / KAYNAK / TARIH).iterdir()) == sorted(
        [ZIP_ADI, "fetch.json"]
    )
    assert not (kk.tmp / "CALISTI.txt").exists()  # zip icindeki betik calistirilmadi


def test_ingest_ikinci_kosu_bayt_ayni_ve_force(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    assert kk.ingest(force=True) == 0
    klasorler = kk.staged_klasorleri()
    assert len(klasorler) == 2
    assert (klasorler[0] / "lugat.jsonl").read_bytes() == (
        klasorler[1] / "lugat.jsonl"
    ).read_bytes()
    assert len(list((kk.veri_kok / "raw" / KAYNAK).iterdir())) == 1  # ham kopya tekrarlanmadi


def test_ingest_ikinci_kosu_atlanir(kk: LugatKoku, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(lineage, "git_durumu", lambda _kok: TEMIZ_GIT)
    assert kk.ingest() == 0
    assert kk.ingest() == 0
    assert len(kk.staged_klasorleri()) == 1


def test_dry_run_hicbir_sey_yazmaz(kk: LugatKoku) -> None:
    assert kk.ingest(dry_run=True) == 0
    assert not (kk.veri_kok / "raw").exists()
    assert not (kk.veri_kok / "staged").exists()
    assert not (kk.veri_kok / "reports" / "a20").exists()


def test_sozluk_olcum_raporu_yalniz_sayi(kk: LugatKoku) -> None:
    assert kk.ingest() == 0
    rapor = json.loads((kk.veri_kok / "reports" / "a20" / "lugat-sozluk-isabet.json").read_bytes())
    assert rapor["yontem"] == "satir-basi-ilk-jeton-1" and rapor["tohum"] == 20261113
    assert set(rapor["sozlukler"]) == {"lugat-redhouse-1890", "lugat-kamus-i-turki", "lugat-naci"}
    assert rapor["sozlukler"]["lugat-naci"]["guvenilmez"] is True

    def yapraklar(deger: object) -> list[object]:
        if isinstance(deger, dict):
            return [y for v in deger.values() for y in yapraklar(v)]
        if isinstance(deger, list):
            return [y for v in deger for y in yapraklar(v)]
        return [deger]

    for y in yapraklar(rapor):
        if isinstance(y, str):  # yalniz sabit etiketler: yontem, sozluk kimligi, tur, neden, commit
            assert OCR_IMZASI not in y and "denemea" not in y


# --- kilit ve girdi hatalari (cikis 2; raw'a yazilmaz) --------------------------------------


def _kilit_degistir(kk: LugatKoku, **degisim: object) -> None:
    veri = json.loads(kk.kilit_yolu.read_bytes())
    veri.update(degisim)
    kk.kilit_yolu.write_bytes((json.dumps(veri, indent=1, sort_keys=True) + "\n").encode("utf-8"))


def test_zip_ozeti_kilitle_tutmazsa_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    digeri = sentetik_zip(frekans={KITAP_A: {"baska": 1}}, csvler={KITAP_A: [("baska", "x")]})
    kk = lugat_hazirla(tmp_path, monkeypatch, gelen_zip=digeri)
    assert kk.ingest() == 2
    assert "kilit guncellenerek" in capsys.readouterr().err
    assert not (kk.veri_kok / "raw").exists() and not (kk.veri_kok / "staged").exists()


def test_kilit_sayilari_tutmazsa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kk = lugat_hazirla(tmp_path, monkeypatch)
    kilit = json.loads(kk.kilit_yolu.read_bytes())
    kilit["dosyalar"][KITAP_B]["sayilar"]["toplam_frekans"] += 1
    kk.kilit_yolu.write_bytes((json.dumps(kilit, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    assert kk.ingest() == 2
    assert not (kk.veri_kok / "raw").exists()


def test_kilit_uye_ozeti_tutmazsa_cikis_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kk = lugat_hazirla(tmp_path, monkeypatch)
    kilit = json.loads(kk.kilit_yolu.read_bytes())
    kilit["dosyalar"][KITAP_A]["frekans_sha256"] = "0" * 64
    kk.kilit_yolu.write_bytes((json.dumps(kilit, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    assert kk.ingest() == 2
    assert not (kk.veri_kok / "raw").exists()


def test_kilitteki_kitap_alt_kume_ayrimi_olculenle_tutmazsa_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kk = lugat_hazirla(tmp_path, monkeypatch)
    kilit = json.loads(kk.kilit_yolu.read_bytes())
    kilit["dosyalar"][ALT_A]["ust"] = None  # alt kume kitap sayilsin: olculen ayrimla tutmaz
    kk.kilit_yolu.write_bytes((json.dumps(kilit, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    assert kk.ingest() == 2


def test_ocr_ozeti_kilitle_tutmazsa_cikis_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kk = lugat_hazirla(tmp_path, monkeypatch)
    dosya = next((kk.veri_kok / "gelen" / "lugat-naci" / TARIH).iterdir())
    dosya.write_bytes(dosya.read_bytes() + b"x\n")
    assert kk.ingest() == 2
    assert not (kk.veri_kok / "raw").exists()


def test_kilit_bicimi_kati(kk: LugatKoku) -> None:
    ham = kk.kilit_yolu.read_bytes()
    assert kilit_metni(kilit_coz(ham)).encode("utf-8") == ham  # gidis-donus bayt ayni
    for bozuk in (b"\xef\xbb\xbf" + ham, ham.replace(b"\n", b"\r\n"), b"{}", ham[:-3]):
        with pytest.raises(GirdiHatasi):
            kilit_coz(bozuk)


def test_kayitsiz_kaynak_cikis_2(kk: LugatKoku) -> None:
    (kk.kok / "pipeline" / "sources" / "lugat-naci.toml").unlink()
    assert kk.ingest() == 2
    assert not (kk.veri_kok / "raw").exists()


def test_gelen_klasoru_yoksa_cikis_2(kk: LugatKoku) -> None:
    (kk.veri_kok / "gelen" / KAYNAK / TARIH / ZIP_ADI).unlink()
    assert kk.ingest() == 2


def test_zip_guvenligi_guvensiz_uye_adi_reddedilir() -> None:
    guvensiz = sentetik_zip(ekstra={"../disari.txt": b"x"})
    with pytest.raises(GirdiHatasi, match="guvensiz uye adi"):
        kelime_frekans.kilit_onerisi(guvensiz, {}, TARIH, "https://d", "https://u", COMMIT)


def test_eksik_csv_ya_da_frekans_dosyasi_reddedilir() -> None:
    zip_verisi = sentetik_zip(csvler={KITAP_A: [("a", "x")]})  # B ve ALT icin CSV yok
    with pytest.raises(GirdiHatasi, match="ayni degil"):
        oku_zip(GuvenliZip(zip_verisi), COMMIT)


def test_csv_bozuk_satirlar_kilitte_sayilir() -> None:
    zip_verisi = sentetik_zip(csv_ek={KITAP_A: '"x","y","z"\n"","q"\n'})
    sayilar = oku_zip(GuvenliZip(zip_verisi), COMMIT).dosyalar[KITAP_A].sayilar
    assert sayilar["csv_bozuk"] == 2
    assert sayilar["csv_kayit"] == 5  # bozuk satirlar kayit sayilmaz


def test_madde_satiri_bos_norm_reddeder() -> None:
    with pytest.raises(GirdiHatasi, match="normalize"):
        madde_satiri(
            source_id=KAYNAK,
            basliksoz="(",
            duzey=3,
            kaynaklar={},
            onerilen_basvuru={},
            data_version="x",
        )
    with pytest.raises(GirdiHatasi, match="bos baslik"):
        madde_satiri(
            source_id=KAYNAK,
            basliksoz="",
            duzey=3,
            kaynaklar={},
            onerilen_basvuru={},
            data_version="x",
        )
