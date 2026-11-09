"""`mutalaa export test-vectors --fts-ornekleri` testleri (A12.4).

Sentetik belge ve vektor dosyasi `tmp_path` altinda kurulur; Arapca harfler `\\u` kacisiyla
yazilmis tek tek harflerdir (hicbir kelime ya da ayet hafizadan yazilmaz). Gercek belge ve
gercek `fts-query/query.jsonl` icin yalniz tutarlilik (`denetle` bos) ve bicim sinanir.
"""

import json
from pathlib import Path

import pytest
from test_export_vectors import kok_kur
from typer.testing import CliRunner, Result

from mutalaa_pipeline.cli import app
from mutalaa_pipeline.export import fts_ornekleri as fts
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.normalize import normalize_ar

runner = CliRunner()

BA, SIN, MIM, RA, FETHA = "ب", "س", "م", "ر", "َ"
TERIM = BA + SIN + MIM + RA  # yalin harfler: normalize_ar degistirmez
KOK = SIN + MIM + RA
KOK_ONEKI = "kök:"

BELGE_ONCESI = (
    "# Deneme belge\n\n| Girdi | `ar` | Sinanan kural |\n|---|---|---|\n| `x` | `y` | z |\n\n"
)


def belge_metni(terim: str = TERIM, kok: str = KOK, *, match: str | None = None) -> str:
    match_hucresi = f'`ar_norm : "{normalize_ar(terim)}"`' if match is None else match
    return (
        BELGE_ONCESI
        + "| Sorgu | MATCH ifadesi |\n|---|---|\n"
        + '| `sabir` | `tr_wide : "sabir"` |\n'
        + f"| `{terim}` | {match_hucresi}; az sonucta `unit_tri` |\n"
        + f"| `{KOK_ONEKI}{kok}` | `word_morph.root_id` sorgulari |\n\n"
        + "Sonraki bolum.\n"
    )


MEVCUT_SATIR = (
    '{"id":"fq-0001","input":{"query":"x"},"expected":{"address":null,"match":null,"tri":null,'
    '"narrow":[],"kok":null,"kaynak":null,"ignored":[],"tooLong":false},"note":"sinir"}'
)
ESKI_ARAPCA = '{"id":"fq-ar-0009","input":{"query":"x"},"expected":{},"note":"eski"}'


def kok_hazirla(tmp_path: Path, belge: str | None = None, vektor: str | None = None) -> Path:
    kok = kok_kur(tmp_path)
    belge_yolu = kok / fts.BELGE_YOLU
    belge_yolu.parent.mkdir(parents=True, exist_ok=True)
    belge_yolu.write_text(belge_metni() if belge is None else belge, encoding="utf-8", newline="\n")
    vektor_yolu = kok / fts.VEKTOR_YOLU
    vektor_yolu.parent.mkdir(parents=True, exist_ok=True)
    metin = f"{MEVCUT_SATIR}\n{ESKI_ARAPCA}\n" if vektor is None else vektor
    vektor_yolu.write_text(metin, encoding="utf-8", newline="\n")
    return kok


def calistir(kok: Path, *ek: str) -> Result:
    return runner.invoke(app, ["export", "test-vectors", "--kok", str(kok), "--fts-ornekleri", *ek])


def vektor_baytlari(kok: Path) -> bytes:
    return (kok / fts.VEKTOR_YOLU).read_bytes()


# --- belge tablosu ----------------------------------------------------------------------------


def test_tablo_oku_kod_bicimini_temizler(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    tablo = fts.tablo_oku(kok)
    assert [t.sorgu for t in tablo] == ["sabir", TERIM, KOK_ONEKI + KOK]
    assert tablo[1].ifade.startswith(f'`ar_norm : "{TERIM}"`;')


def test_tablo_basligi_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path, belge="# Tablo yok\n")
    with pytest.raises(GirdiHatasi, match="tam bir kez"):
        fts.tablo_oku(kok)


def test_belge_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    (kok / fts.BELGE_YOLU).unlink()
    with pytest.raises(GirdiHatasi, match=r"belge|yok"):
        fts.tablo_oku(kok)


def test_arapca_terim_ya_da_kok_satiri_eksikse_girdi_hatasi(tmp_path: Path) -> None:
    govde = '| Sorgu | MATCH ifadesi |\n|---|---|\n| `sabir` | `tr_wide : "sabir"` |\n'
    kok = kok_hazirla(tmp_path, belge=BELGE_ONCESI + govde)
    with pytest.raises(GirdiHatasi, match="Arapca terim satiri tam bir kez"):
        fts.satirlari_kur(fts.tablo_oku(kok))


# --- satirlar -----------------------------------------------------------------------------------


def test_satirlar_beklenen_biciminde(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    terim, kok_satiri = fts.satirlari_kur(fts.tablo_oku(kok))
    norm = normalize_ar(TERIM)
    assert terim == {
        "id": "fq-ar-0001",
        "input": {"query": TERIM},
        "expected": {
            "address": None,
            "match": f'ar_norm : "{norm}"',
            "tri": f'"{norm}"',
            "narrow": [],
            "kok": None,
            "kaynak": None,
            "ignored": [],
            "tooLong": False,
        },
        "note": fts.NOT_METNI,
    }
    assert list(terim) == ["id", "input", "expected", "note"]  # anahtar sirasi
    assert list(terim["expected"]) == [  # type: ignore[call-overload]
        "address",
        "match",
        "tri",
        "narrow",
        "kok",
        "kaynak",
        "ignored",
        "tooLong",
    ]
    assert kok_satiri["id"] == "fq-ar-0002"
    assert kok_satiri["input"] == {"query": KOK_ONEKI + KOK}
    beklenen = kok_satiri["expected"]
    assert isinstance(beklenen, dict)
    assert beklenen["kok"] == normalize_ar(KOK)
    assert beklenen["match"] is None
    assert beklenen["tri"] is None


def test_beklenen_deger_normalize_ar_ile_hesaplanir(tmp_path: Path) -> None:
    """Hareke tasiyan terim: sorgu belgedeki gibi, beklenen normalize hali."""
    terim = BA + FETHA + SIN + MIM + RA
    kok = kok_hazirla(tmp_path, belge=belge_metni(terim=terim))
    satir, _ = fts.satirlari_kur(fts.tablo_oku(kok))
    assert satir["input"] == {"query": terim}
    beklenen = satir["expected"]
    assert isinstance(beklenen, dict)
    assert beklenen["match"] == f'ar_norm : "{BA + SIN + MIM + RA}"'


def test_match_hucresi_normalize_ile_uyusmazsa_girdi_hatasi(tmp_path: Path) -> None:
    belge = belge_metni(match='`ar_norm : "' + BA + '"`')
    kok = kok_hazirla(tmp_path, belge=belge)
    with pytest.raises(GirdiHatasi, match="MATCH hucresi"):
        fts.satirlari_kur(fts.tablo_oku(kok))


# --- dosya ve komut -----------------------------------------------------------------------------


def test_uret_mevcut_satirlari_korur_eski_arapca_satirlari_degistirir(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    sonuc = calistir(kok)
    assert sonuc.exit_code == 0, sonuc.output
    satirlar = vektor_baytlari(kok).decode("utf-8").split("\n")
    assert satirlar[-1] == ""
    assert satirlar[0] == MEVCUT_SATIR  # bayt bayt
    kimlikler = [json.loads(s)["id"] for s in satirlar[:-1]]
    assert kimlikler == ["fq-0001", "fq-ar-0001", "fq-ar-0002"]
    assert kimlikler == sorted(kimlikler)


def test_ikinci_calistirma_degisiklik_yok_ve_check_sifir(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    assert calistir(kok).exit_code == 0
    ilk = vektor_baytlari(kok)
    ikinci = calistir(kok)
    assert ikinci.exit_code == 0
    assert "degisiklik yok" in ikinci.output
    assert vektor_baytlari(kok) == ilk
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 0, denetim.output
    assert "fark yok" in denetim.output


def test_check_fark_varsa_bir_ve_yazmaz(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    onceki = vektor_baytlari(kok)
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert "fts-query/query.jsonl" in denetim.output
    assert vektor_baytlari(kok) == onceki
    # Uretildikten sonra bir satir elle bozulursa yine 1.
    assert calistir(kok).exit_code == 0
    bozuk = vektor_baytlari(kok).replace(b'"kok":"', b'"kok":"x', 1)  # yalniz fq-ar-0002
    (kok / fts.VEKTOR_YOLU).write_bytes(bozuk)
    assert calistir(kok, "--check").exit_code == 1


def test_bayt_bicimi_utf8_lf_bom_yok_kacis_yok(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    assert calistir(kok).exit_code == 0
    veri = vektor_baytlari(kok)
    assert not veri.startswith(b"\xef\xbb\xbf")
    assert b"\r" not in veri
    yeni = veri.decode("utf-8").split("\n")[1:-1]
    assert all("\\u" not in s for s in yeni)  # ham UTF-8
    assert TERIM in yeni[0]


def test_belge_uyusmazligi_cikis_iki_ve_dosya_degismez(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path, belge=belge_metni(match='`ar_norm : "' + BA + '"`'))
    onceki = vektor_baytlari(kok)
    sonuc = calistir(kok)
    assert sonuc.exit_code == 2
    assert vektor_baytlari(kok) == onceki
    assert calistir(kok, "--check").exit_code == 2


def test_sirasi_bozuk_mevcut_satir_girdi_hatasi(tmp_path: Path) -> None:
    sonraki = MEVCUT_SATIR.replace("fq-0001", "fq-b001")
    kok = kok_hazirla(tmp_path, vektor=f"{sonraki}\n")
    with pytest.raises(GirdiHatasi, match="siralanmali"):
        fts.dosya_metni(kok)
    assert calistir(kok).exit_code == 2


@pytest.mark.parametrize(
    ("veri", "ileti"),
    [
        (b"\xef\xbb\xbf" + MEVCUT_SATIR.encode("utf-8") + b"\n", "BOM ya da CR"),
        (MEVCUT_SATIR.encode("utf-8") + b"\r\n", "BOM ya da CR"),
        (MEVCUT_SATIR.encode("utf-8"), "satir sonu yok"),
        (b'{"input":1}\n', "id"),
    ],
)
def test_bozuk_vektor_dosyasi_girdi_hatasi(tmp_path: Path, veri: bytes, ileti: str) -> None:
    kok = kok_hazirla(tmp_path)
    (kok / fts.VEKTOR_YOLU).write_bytes(veri)
    with pytest.raises(GirdiHatasi, match=ileti):
        fts.dosya_metni(kok)


def test_vektor_dosyasi_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    (kok / fts.VEKTOR_YOLU).unlink()
    with pytest.raises(GirdiHatasi, match="yok"):
        fts.dosya_metni(kok)


def test_ana_uretec_fts_dosyasina_dokunmaz(tmp_path: Path) -> None:
    kok = kok_hazirla(tmp_path)
    onceki = vektor_baytlari(kok)
    sonuc = runner.invoke(app, ["export", "test-vectors", "--kok", str(kok)])
    assert sonuc.exit_code == 0, sonuc.output
    assert vektor_baytlari(kok) == onceki


# --- gercek belge ve dosya -----------------------------------------------------------------------


def test_gercek_belge_iki_arapca_sorgu_ve_dosya_tutarli() -> None:
    kok = depo_koku()
    tablo = fts.tablo_oku(kok)
    terim, kok_satiri = fts.satirlari_kur(tablo)
    sorgular = {t.sorgu for t in tablo}
    assert terim["input"] == {"query": next(s for s in sorgular if fts._arapca(s))}
    assert isinstance(kok_satiri["input"], dict)
    assert kok_satiri["input"]["query"] in sorgular
    assert str(kok_satiri["input"]["query"]).startswith(fts.KOK_ONEKI)
    assert fts.denetle(kok) == []  # diskteki fq-ar- satirlari belgeyle ayni
