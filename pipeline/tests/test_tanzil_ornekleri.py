"""`mutalaa export test-vectors --tanzil-ornekleri` testleri (A10.7).

Metinler SENTETIKTIR: yalin Arapca harfler ve harekeler `\\u` kacisiyla, belge tablosu da bu
harflerle kurulur; hicbir ayet ya da besmele hafizadan yazilmaz. Gercek bayt gereken tek yer
`tests/fixtures/tanzil/` parcasidir (dosyadan betikle kesilmis); belgedeki gercek tablonun ilk
satiri o parcayla eslestirilir.
"""

from pathlib import Path

import pytest
from tanzil_yardimci import PARCA_CAPALAR, parca_oku, sentetik_bildirim
from test_export_vectors import calistir, kok_kur, satirlari_oku, satirlari_yaz, vektor_yolu
from typer.testing import CliRunner

from mutalaa_pipeline.cli import app
from mutalaa_pipeline.export import tanzil_ornekleri as tz
from mutalaa_pipeline.export import test_vectors as tv
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.ingest import tanzil_bicim
from mutalaa_pipeline.ingest.tanzil_bicim import Ayrisma

BA, SIN, MIM, VAV, YE_NOKTASIZ = "\u0628", "\u0633", "\u0645", "\u0648", "\u0649"
FETHA, KESRA, SEDDE, SUKUN, HANCER_ELIF = "\u064e", "\u0650", "\u0651", "\u0652", "\u0670"
TATVIL, KUCUK_YUKSEK = "\u0640", "\u06d6"
YE = "\u064a"

KELIME_A = BA + FETHA + SIN + MIM  # iskelet: BA SIN MIM
KELIME_A_YALIN = BA + SIN + MIM  # ayni iskelet, tanik (U+064E) yok
KELIME_B = MIM + VAV + SIN + YE_NOKTASIZ + HANCER_ELIF  # ikinci tablo satiri (tek belirtec)
KELIME_C = SIN + KESRA + MIM  # ucuncu satir icin tanik KESRA
DOLGU = VAV + VAV  # eslesmeyen sentetik belirtec

BELGE_BASLIGI = "# Deneme belge\n\n| Girdi | `ar` | Sinanan kural |\n|---|---|---|\n"


def belge_yaz(kok: Path, satirlar: list[tuple[str, str]], *, ek: str = "") -> None:
    yol = kok / tz.BELGE_YOLU
    yol.parent.mkdir(parents=True, exist_ok=True)
    govde = "".join(f"| `{g}` | `{a}` | deneme |\n" for g, a in satirlar)
    yol.write_text(BELGE_BASLIGI + govde + ek, encoding="utf-8", newline="\n")


def sentetik_ayrisma(*ayetler: tuple[int, str]) -> Ayrisma:
    """(sure, metin) cifti ayetleri sure 1 ve 2'ye `1|1`'den kesintisiz dagitir."""
    satirlar: list[str] = []
    sayaclar = {1: 0, 2: 0}
    for sure, metin in ayetler:
        sayaclar[sure] += 1
        satirlar.append(f"{sure}|{sayaclar[sure]}|{metin}\n")
    if sayaclar[2] == 0:  # sure tablosu iki sureyi de ister
        satirlar.append(f"2|1|{DOLGU}\n")
        sayaclar[2] = 1
    veri = "".join(satirlar).encode("utf-8") + sentetik_bildirim("uthmani")
    return tanzil_bicim.ayristir(veri, (sayaclar[1], sayaclar[2]))


# --- iskelet ve tanik ----------------------------------------------------------------------


def test_iskelet_sira_farkini_tatvili_ve_kuran_isaretlerini_atar() -> None:
    ayni = [BA + SEDDE + FETHA, BA + FETHA + SEDDE, BA + TATVIL + KUCUK_YUKSEK]
    assert {tz.iskelet(s) for s in ayni} == {BA}


def test_iskelet_harf_birlestirmez_ve_bosluga_dokunmaz() -> None:
    assert tz.iskelet(YE_NOKTASIZ + FETHA + " " + SIN) == YE_NOKTASIZ + " " + SIN
    assert tz.iskelet(YE_NOKTASIZ) != tz.iskelet(YE)


def test_tanik_kumesi_normallestiricinin_etkiledigi_kod_noktalarini_verir() -> None:
    assert tz.tanik_kumesi(KELIME_A) == {ord(FETHA)}
    assert tz.tanik_kumesi(KELIME_A_YALIN) == frozenset()
    assert tz.tanik_kumesi(KELIME_B) == {ord(YE_NOKTASIZ), ord(HANCER_ELIF)}


# --- belge tablosu -------------------------------------------------------------------------


def test_tablo_oku_sira_ve_belge_satiri(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_A, KELIME_A_YALIN), (KELIME_B + " " + KELIME_C, MIM)])
    tablo = tz.tablo_oku(tmp_path)
    assert [(t.sira, t.belge_satiri) for t in tablo] == [(1, 5), (2, 6)]
    assert tablo[0].girdi == KELIME_A
    assert tablo[0].ar == KELIME_A_YALIN
    assert tablo[1].girdi.count(" ") == 1


def test_tablo_oku_belge_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi, match="yok"):
        tz.tablo_oku(tmp_path)


@pytest.mark.parametrize(
    ("satir", "ileti"),
    [
        ("| `abc` | `abc` | deneme |", "yalniz Arapca harf"),
        (f"| `{BA}{BA}  {SIN}` | `{BA}` | deneme |", "yalniz Arapca harf"),
        (f"| `{BA}` | `{BA}` |", "bicimi gecersiz"),
        (f"| {BA} | {BA} | deneme |", "bicimi gecersiz"),
    ],
)
def test_tablo_oku_bozuk_satir_girdi_hatasi(tmp_path: Path, satir: str, ileti: str) -> None:
    yol = tmp_path / tz.BELGE_YOLU
    yol.parent.mkdir(parents=True)
    yol.write_text(BELGE_BASLIGI + satir + "\n", encoding="utf-8", newline="\n")
    with pytest.raises(GirdiHatasi, match=ileti):
        tz.tablo_oku(tmp_path)


def test_tablo_oku_yinelenen_girdi_ve_baslik_hatalari(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_A, MIM), (KELIME_A, SIN)])
    with pytest.raises(GirdiHatasi, match="yinelenen"):
        tz.tablo_oku(tmp_path)
    yol = tmp_path / tz.BELGE_YOLU
    yol.write_text("# Deneme belge\n\nTablo yok.\n", encoding="utf-8", newline="\n")
    with pytest.raises(GirdiHatasi, match="tam bir kez"):
        tz.tablo_oku(tmp_path)
    yol.write_text(BELGE_BASLIGI.replace("|---|---|---|\n", ""), encoding="utf-8", newline="\n")
    with pytest.raises(GirdiHatasi, match="ayirici"):
        tz.tablo_oku(tmp_path)


def test_tablo_oku_bos_tablo_girdi_hatasi(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [])
    with pytest.raises(GirdiHatasi, match="satir yok"):
        tz.tablo_oku(tmp_path)


# --- eslestirme ----------------------------------------------------------------------------


def test_eslestir_okuma_sirasindaki_ilk_tanikli_eslesmeyi_alir(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_A, KELIME_A_YALIN)])
    ayrisma = sentetik_ayrisma(
        (1, DOLGU + " " + KELIME_A_YALIN),  # iskelet ayni ama tanik (fetha) yok: atlanir
        (1, KELIME_A + " " + DOLGU),  # secilen
        (2, KELIME_A),  # ikinci tanikli eslesme: alinmaz
    )
    (e,) = tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler)
    assert (e.capa, e.belirtec_bas, e.belirtec_son, e.atlanan) == ("q:1:2", 1, 1, 1)
    assert e.dilim == KELIME_A
    assert e.kimlik == "ar-tz-0001"
    assert e.satir() == tv.Satir("ar-tz-0001", KELIME_A, KELIME_A_YALIN, "tanzil-uthmani q:1:2")


def test_eslestir_cok_belirtecli_girdi_ardisik_belirtecleri_arar(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_A + " " + KELIME_C, KELIME_A_YALIN + " " + MIM + SIN + MIM)])
    ayrisma = sentetik_ayrisma(
        (1, KELIME_A + " " + DOLGU + " " + KELIME_C),  # ardisik degil
        (2, DOLGU + " " + KELIME_A + " " + KELIME_C),
    )
    (e,) = tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler)
    assert (e.capa, e.belirtec_bas, e.belirtec_son) == ("q:2:1", 2, 3)
    assert e.dilim == KELIME_A + " " + KELIME_C
    assert e.ozet().startswith("ar-tz-0001 q:2:1 belirtec 2-3 atlanan 0 tanik U+")


def test_eslestir_dilim_kaynak_baytlariyla_ayni_kalir(tmp_path: Path) -> None:
    """Girdi Tanzil'in baytlaridir: sedde-hareke sirasi ve NFC olmayan hal degismez."""
    sira = BA + SEDDE + FETHA + SIN  # NFC'de BA FETHA SEDDE olurdu
    belge_yaz(tmp_path, [(BA + FETHA + SEDDE + SIN, BA + SIN)])
    ayrisma = sentetik_ayrisma((1, sira))
    (e,) = tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler)
    assert e.dilim == sira
    assert e.dilim != BA + FETHA + SEDDE + SIN


def test_eslestir_eslesme_yoksa_girdi_hatasi_ve_ileti_icerik_tasimaz(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_B, MIM)])
    ayrisma = sentetik_ayrisma((1, DOLGU), (2, KELIME_A))
    with pytest.raises(GirdiHatasi) as hata:
        tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler)
    ileti = str(hata.value)
    assert "tablo satiri 1" in ileti
    assert "belge satiri 5" in ileti
    assert "uydurulmaz" in ileti
    assert ileti.isascii()


def test_eslestir_yalniz_tanik_denetimi_gecmeyen_eslesme_varsa_hata_sayisi_yazar(
    tmp_path: Path,
) -> None:
    belge_yaz(tmp_path, [(KELIME_A, KELIME_A_YALIN)])
    ayrisma = sentetik_ayrisma((1, KELIME_A_YALIN), (2, KELIME_A_YALIN))
    with pytest.raises(GirdiHatasi, match=r"2 iskelet eslesmesi tanik denetiminden gecemedi"):
        tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler)


# --- normallestirici dogrulamasi -----------------------------------------------------------


def test_normalize_denetle_tabloyla_uyusuyorsa_sessiz(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_B, MIM + VAV + SIN + YE)])
    ayrisma = sentetik_ayrisma((1, KELIME_B))
    tz.normalize_denetle(tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler))


def test_normalize_denetle_tablodaki_deger_cikmazsa_girdi_hatasi(tmp_path: Path) -> None:
    belge_yaz(tmp_path, [(KELIME_B, MIM + VAV + SIN + YE_NOKTASIZ)])  # tabloda ye birlesmemis
    ayrisma = sentetik_ayrisma((1, KELIME_B))
    eslesmeler = tz.eslestir(tz.tablo_oku(tmp_path), ayrisma.ayetler)
    with pytest.raises(GirdiHatasi) as hata:
        tz.normalize_denetle(eslesmeler)
    ileti = str(hata.value)
    assert "normalize_ar tablodaki degeri vermiyor" in ileti
    assert "ilk fark konum 3: U+064A / U+0649" in ileti
    assert "uydurulmaz" in ileti
    assert ileti.isascii()


# --- gercek tablo, gercek bayt parcasi ------------------------------------------------------


def test_belgedeki_gercek_tablonun_ilk_satiri_fikstur_parcasinda_bulunur() -> None:
    """Besmele satiri: kaynak parcadaki 1:1'in ilk belirteclerinin baytlariyla eslesir."""
    tablo = tz.tablo_oku(depo_koku())
    assert len(tablo) == 7  # A10.7: tablonun yedi girdisi
    ayrisma = tanzil_bicim.ayristir(parca_oku("uthmani"), tam=False)  # parca 40 ayetlik
    (e,) = tz.eslestir(tablo[:1], ayrisma.ayetler)
    assert e.capa == "q:1:1"
    assert e.capa in PARCA_CAPALAR
    ayet = ayrisma.ayetler[0]
    assert e.dilim in ayet.metin  # bayt bayt alt dizi
    assert e.dilim.encode("utf-8") in parca_oku("uthmani")
    tz.normalize_denetle([e])


# --- komut -----------------------------------------------------------------------------------


def komut_kur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, satirlar: list[tuple[str, str]]
) -> Path:
    """Sahte depo kokunde sentetik tablo; Tanzil dosyasi yerine sentetik ayrisma verilir."""
    kok = kok_kur(tmp_path)
    belge_yaz(kok, satirlar)
    ayrisma = sentetik_ayrisma((1, DOLGU + " " + KELIME_A), (2, KELIME_B + " " + KELIME_C))
    monkeypatch.setattr(tz, "tanzil_oku", lambda _veri_kok: ayrisma)
    return kok


TABLO = [(KELIME_A, KELIME_A_YALIN), (KELIME_B, MIM + VAV + SIN + YE)]


def test_komut_satirlari_yazar_ikinci_calisma_degistirmez_check_sifir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = komut_kur(tmp_path, monkeypatch, TABLO)
    # --check: henuz ar-tz- satiri yok
    assert calistir(kok, "--tanzil-ornekleri", "--check").exit_code == 1
    ilk = calistir(kok, "--tanzil-ornekleri")
    assert ilk.exit_code == 0
    assert "tanzil: ar-tz-0001 q:1:1 belirtec 2 atlanan 0" in ilk.output
    assert "tanzil: ar-tz-0002 q:2:1 belirtec 1 atlanan 0" in ilk.output
    satirlar = satirlari_oku(kok, tv.NORMALIZE_AR)
    assert [s["id"] for s in satirlar] == ["ar-tz-0001", "ar-tz-0002"]
    assert satirlar[0] == {
        "id": "ar-tz-0001",
        "input": KELIME_A,
        "expected": KELIME_A_YALIN,
        "note": "tanzil-uthmani q:1:1",
    }
    once = vektor_yolu(kok, tv.NORMALIZE_AR).read_bytes()
    assert b"\\u064e" in once  # birlesen isaret dosyada \u kacisiyla yazilir
    ikinci = calistir(kok, "--tanzil-ornekleri")
    assert ikinci.exit_code == 0
    assert "test-vectors: degisiklik yok" in ikinci.output
    assert vektor_yolu(kok, tv.NORMALIZE_AR).read_bytes() == once
    assert calistir(kok, "--tanzil-ornekleri", "--check").exit_code == 0


def test_komut_yalniz_kendi_satirlarini_yeniler_oteki_ar_satirlarina_dokunmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = komut_kur(tmp_path, monkeypatch, TABLO)
    sentetik = {"id": "ar-0001", "input": "x" + FETHA, "expected": "x"}
    eski_tz = {"id": "ar-tz-0099", "input": "eski", "expected": "eski", "note": "eski"}
    satirlari_yaz(kok, tv.NORMALIZE_AR, [sentetik, eski_tz])
    assert calistir(kok, "--tanzil-ornekleri").exit_code == 0
    satirlar = satirlari_oku(kok, tv.NORMALIZE_AR)
    assert [s["id"] for s in satirlar] == ["ar-0001", "ar-tz-0001", "ar-tz-0002"]
    assert satirlar[0]["expected"] == "x"  # sentetik satir ayni


def test_komut_tanzil_ornekleri_olmadan_mevcut_satirlari_oldugu_gibi_korur(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = komut_kur(tmp_path, monkeypatch, TABLO)
    assert calistir(kok, "--tanzil-ornekleri").exit_code == 0
    once = vektor_yolu(kok, tv.NORMALIZE_AR).read_bytes()
    assert calistir(kok).exit_code == 0
    assert vektor_yolu(kok, tv.NORMALIZE_AR).read_bytes() == once
    assert calistir(kok, "--check").exit_code == 0


def test_komut_eslesme_yoksa_iki_ve_dosya_degismez(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = komut_kur(tmp_path, monkeypatch, [(KELIME_C + " " + KELIME_C, MIM)])
    satirlari_yaz(kok, tv.NORMALIZE_AR, [{"id": "ar-0001", "input": "x", "expected": "x"}])
    once = vektor_yolu(kok, tv.NORMALIZE_AR).read_bytes()
    sonuc = calistir(kok, "--tanzil-ornekleri")
    assert sonuc.exit_code == 2
    assert "eslesme yok" in sonuc.output
    assert vektor_yolu(kok, tv.NORMALIZE_AR).read_bytes() == once


def test_komut_normallestirici_tablodaki_degeri_vermezse_iki_ve_yazmaz(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = komut_kur(tmp_path, monkeypatch, [(KELIME_A, KELIME_A_YALIN + MIM)])
    sonuc = calistir(kok, "--tanzil-ornekleri")
    assert sonuc.exit_code == 2
    assert "normalize_ar tablodaki degeri vermiyor" in sonuc.output
    assert not vektor_yolu(kok, tv.NORMALIZE_AR).exists()


def test_komut_tanzil_dosyasi_yoksa_anlasilir_iletiyle_iki(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = kok_kur(tmp_path)
    belge_yaz(kok, TABLO)
    bos_veri = tmp_path / "bos-veri"
    bos_veri.mkdir()
    monkeypatch.setenv("MUTALAA_VERI_KOK", str(bos_veri))  # mutlak yol: pipeline/ altina cozulmez
    sonuc = CliRunner().invoke(
        app, ["export", "test-vectors", "--kok", str(kok), "--tanzil-ornekleri"]
    )
    assert sonuc.exit_code == 2
    assert "Tanzil Uthmani dosyasi kullanilamadi" in sonuc.output
    assert "quran-uthmani.txt gerekir" in sonuc.output
    assert not vektor_yolu(kok, tv.NORMALIZE_AR).exists()


def test_komut_config_yalniz_tanzil_ornekleri_ile_verilir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    sonuc = calistir(kok, "--config", str(tmp_path / "mutalaa.toml"))
    assert sonuc.exit_code == 2
    assert "--config yalniz --tanzil-ornekleri ile verilir" in sonuc.output


def test_hazirla_tanzil_satiri_ar_tz_oneki_olmadan_reddedilir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    with pytest.raises(GirdiHatasi, match="ar-tz-"):
        tv.hazirla(kok, [tv.Satir("ar-0001", "x", "x", "n")])
