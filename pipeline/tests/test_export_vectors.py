"""`mutalaa export test-vectors` testleri (A04.2).

Her test `tmp_path` altinda kendi kokunu kurar ve `--kok` ile calisir; gercek
`shared/test-vectors` klasorune dokunulmaz. Metinler sentetiktir: Latin harf, kacisla
yazilmis tek tek Arapca harf ve isaretler, BMP disi bir harf. Kaynak yalniz ASCII'dir:
ASCII disi karakterler `\\x..`, `\\N{...}` ve `\\U........` kacisiyla yazilir.
"""

import ast
import hashlib
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from mutalaa_pipeline.cli import app
from mutalaa_pipeline.export import test_vectors as tv
from mutalaa_pipeline.export.ayet_sayilari import JSON_YOLU, AyetSayilariBelgesi, json_metni
from mutalaa_pipeline.export.ortak import GirdiHatasi

runner = CliRunner()

SENTETIK_SAYILAR = tuple((sira % 7) + 1 for sira in range(114))
ALEM = "\xe2lem \U0001d400"  # 6 kod noktasi, 7 UTF-16 birimi
NOKTASIZ_I = "\N{LATIN SMALL LETTER DOTLESS I}"
CENGELLI_S = "\N{LATIN SMALL LETTER S WITH CEDILLA}"
NOT_METNI = f"girdi NFC bi\xe7iminde; U+1D400 BMP d{NOKTASIZ_I}{CENGELLI_S}{NOKTASIZ_I}"
BA_SEDDE_FETHA = "\N{ARABIC LETTER BEH}\N{ARABIC SHADDA}\N{ARABIC FATHA}"  # NFC olmayan sira
SAPKA = "\N{COMBINING CIRCUMFLEX ACCENT}"
AKUT = "\N{COMBINING ACUTE ACCENT}"


def kok_kur(tmp_path: Path) -> Path:
    kok = tmp_path / "kok"
    belge = AyetSayilariBelgesi(
        kaynak_url="https://example.invalid/quran-data.xml",
        alinma_tarihi="2026-01-02",
        sha256="0" * 64,
        lisans="deneme",
        telif="deneme",
        surum="0",
        sayilar=SENTETIK_SAYILAR,
    )
    yol = kok / JSON_YOLU
    yol.parent.mkdir(parents=True)
    yol.write_text(json_metni(belge), encoding="utf-8", newline="\n")
    return kok


def vektor_yolu(kok: Path, dosya: str) -> Path:
    return kok / tv.VEKTOR_KLASORU / dosya


def satirlari_yaz(kok: Path, dosya: str, satirlar: list[object]) -> None:
    """Satirlari json.dumps ile (kendi kacis kuralimiz olmadan) yazar."""
    yol = vektor_yolu(kok, dosya)
    yol.parent.mkdir(parents=True, exist_ok=True)
    metin = "".join(
        (satir if isinstance(satir, str) else json.dumps(satir)) + "\n" for satir in satirlar
    )
    yol.write_text(metin, encoding="utf-8", newline="\n")


def satirlari_oku(kok: Path, dosya: str) -> list[dict[str, object]]:
    metin = vektor_yolu(kok, dosya).read_bytes().decode("utf-8")
    return [json.loads(satir) for satir in metin.split("\n") if satir]


def ham_satirlar(kok: Path, dosya: str) -> list[str]:
    return vektor_yolu(kok, dosya).read_bytes().decode("utf-8").split("\n")[:-1]


def calistir(kok: Path, *ek: str) -> Result:
    return runner.invoke(app, ["export", "test-vectors", "--kok", str(kok), *ek])


def tum_baytlar(kok: Path) -> dict[str, bytes]:
    return {dosya: vektor_yolu(kok, dosya).read_bytes() for dosya in tv.DOSYALAR}


GECERLI_SATIR: dict[str, object] = {
    "id": "an-0001",
    "input": "q:2:255:3-7",
    "expected": {
        "ref": {"anchor": {"t": "q", "sure": 2, "ayet": 255, "ilk": 3, "son": 7}},
        "canonical": "q:2:255:3-7",
        "unit": "q:2:255",
        "unit_span": {"unit": "q:2:255", "span": [3, 8]},
        "ayahs": [{"sure": 2, "ayet": 255}],
    },
}


# --- Hesaplanan alanlar ------------------------------------------------------------------


def test_alem_bmp_disi_6_kod_noktasi_7_utf16(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(
        kok,
        tv.OFFSETS,
        [
            {
                "id": "of-0001",
                "input": ALEM,
                "expected": {"codepoints": 0, "utf16": 0, "snap": [{"in": [0, 6], "out": [0, 6]}]},
                "note": NOT_METNI,
            }
        ],
    )
    sonuc = calistir(kok)
    assert sonuc.exit_code == 0, sonuc.output
    (satir,) = satirlari_oku(kok, tv.OFFSETS)
    assert satir["input"] == ALEM
    assert satir["expected"] == {
        "codepoints": 6,
        "utf16": 7,
        "cp_to_utf16": [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 7]],
        "snap": [{"in": [0, 6], "out": [0, 6]}],
    }
    assert satir["note"] == NOT_METNI
    (ham,) = ham_satirlar(kok, tv.OFFSETS)
    assert ham.startswith('{"id":"of-0001","input":"\xe2lem \\ud835\\udc00","expected":')
    assert ham.endswith(f',"note":"{NOT_METNI}"}}')  # Turkce harfler duz yazilir


def test_cp_to_utf16_ciftleri(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    bmp_disi_mn = "a\U0001d167b"  # U+1D167 BMP disi birlesen isaret
    satirlari_yaz(
        kok,
        tv.OFFSETS,
        [
            {"id": "of-0002", "input": bmp_disi_mn, "expected": {}},
            {"id": "of-0003", "input": "", "expected": {}},
            {"id": "of-0004", "input": f"a{SAPKA}b", "expected": {}},
        ],
    )
    assert calistir(kok).exit_code == 0
    satirlar = {s["id"]: s["expected"] for s in satirlari_oku(kok, tv.OFFSETS)}
    assert satirlar["of-0002"] == {
        "codepoints": 3,
        "utf16": 4,
        "cp_to_utf16": [[0, 0], [1, 1], [2, 3], [3, 4]],
    }
    assert satirlar["of-0003"] == {"codepoints": 0, "utf16": 0, "cp_to_utf16": [[0, 0]]}
    assert satirlar["of-0004"] == {
        "codepoints": 3,
        "utf16": 3,
        "cp_to_utf16": [[0, 0], [1, 1], [2, 2], [3, 3]],
    }


def test_ham_ve_kanonik_sha256(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(
        kok,
        tv.HASH,
        [
            {"id": "ch-0001", "input": {"op": "ham", "text": "abc"}, "expected": {"sha256": "x"}},
            {"id": "ch-0002", "input": {"text": "", "op": "ham"}, "expected": {}},
            {"id": "ch-0003", "input": {"text": BA_SEDDE_FETHA, "op": "ham"}, "expected": {}},
            {
                "id": "ch-0004",
                "input": {"text": f"a{AKUT}", "op": "kanonik"},
                "expected": {"text": "\xe1"},
            },
        ],
    )
    assert calistir(kok).exit_code == 0
    satirlar = {s["id"]: s for s in satirlari_oku(kok, tv.HASH)}
    # FIPS 180-2 ornekleri: "abc" ve bos dizgi.
    abc = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    bos = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert satirlar["ch-0001"]["expected"] == {"sha256": abc}
    assert satirlar["ch-0001"]["input"] == {"text": "abc", "op": "ham"}  # anahtar sirasi
    assert satirlar["ch-0002"]["expected"] == {"sha256": bos}
    ham_ozet = hashlib.sha256(BA_SEDDE_FETHA.encode("utf-8")).hexdigest()
    assert satirlar["ch-0003"]["expected"] == {"sha256": ham_ozet}
    assert satirlar["ch-0003"]["input"] == {"text": BA_SEDDE_FETHA, "op": "ham"}  # NFC yok
    kanonik_ozet = hashlib.sha256("\xe1".encode()).hexdigest()
    assert satirlar["ch-0004"]["expected"] == {"sha256": kanonik_ozet, "text": "\xe1"}
    assert kanonik_ozet != hashlib.sha256(f"a{AKUT}".encode()).hexdigest()


# --- Yazim -------------------------------------------------------------------------------


def test_kacis_kurali(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    metin = (
        f"{BA_SEDDE_FETHA} \xf6 a{SAPKA} \U0001d400 "
        'x\xa0y\N{ZERO WIDTH NON-JOINER}z\N{LINE SEPARATOR}\xad\x7f\x01\b\f\n\r\t"\\/'
    )
    satirlari_yaz(kok, tv.OFFSETS, [{"id": "of-0001", "input": metin, "expected": {}}])
    assert calistir(kok).exit_code == 0
    (ham,) = ham_satirlar(kok, tv.OFFSETS)
    girdi = ham.split('"input":', 1)[1].split(',"expected"', 1)[0]
    ters = "\\"
    beklenen = (
        '"'
        + f"{ters}u0628{ters}u0651{ters}u064e \xf6 a{ters}u0302 {ters}ud835{ters}udc00 "
        + f"x{ters}u00a0y{ters}u200cz{ters}u2028{ters}u00ad{ters}u007f{ters}u0001"
        + f'{ters}b{ters}f{ters}n{ters}r{ters}t{ters}"{ters}{ters}/'
        + '"'
    )
    assert girdi == beklenen
    assert "\xf6" in ham  # Turkce harf duz yazilir
    assert "\N{ARABIC LETTER BEH}" not in ham
    assert SAPKA not in ham
    assert "\U0001d400" not in ham
    assert json.loads(ham)["input"] == metin  # gidis-donus


def test_arapca_bloklari_kacisli_turkce_harfler_duz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    turkce = (
        "\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}"
        f"{NOKTASIZ_I}"
        "\N{LATIN SMALL LETTER S WITH CEDILLA}"
        "\N{LATIN SMALL LETTER G WITH BREVE}"
        "\xe7\xfc\xe2"
    )
    arapca = (
        "\N{ARABIC LETTER ALEF WASLA ISOLATED FORM}"
        "\N{EXTENDED ARABIC-INDIC DIGIT ZERO}"
        "\N{ARABIC LETTER BEH WITH THREE DOTS HORIZONTALLY BELOW}"
        "\N{ARABIC LETTER BEH WITH SMALL V BELOW}"
        "\N{ARABIC FATHATAN ISOLATED FORM}"
    )
    satirlari_yaz(
        kok, tv.OFFSETS, [{"id": "of-0001", "input": f"{turkce} {arapca}", "expected": {}}]
    )
    assert calistir(kok).exit_code == 0
    (ham,) = ham_satirlar(kok, tv.OFFSETS)
    ters = "\\"
    assert f'"input":"{turkce} ' in ham
    assert f"{ters}ufb50{ters}u06f0{ters}u0750{ters}u08a0{ters}ufe70" in ham


def test_satirlar_id_sirasinda_ve_anahtarlar_sartname_sirasinda(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(
        kok,
        tv.COMPARE,
        [
            {"note": "c", "expected": 1, "input": ["q:2:256", "q:2:255"], "id": "cm-0003"},
            {"id": "cm-0001", "input": ["q:2:255", "q:2:256"], "expected": -1},
            {"id": "cm-0002", "input": ["q:2:255", "q:2:255"], "expected": 0},
        ],
    )
    karisik = dict(GECERLI_SATIR)
    beklenen = GECERLI_SATIR["expected"]
    assert isinstance(beklenen, dict)
    karisik["expected"] = dict(reversed(list(beklenen.items())))
    satirlari_yaz(kok, tv.VALID, [karisik])
    assert calistir(kok).exit_code == 0
    ham = ham_satirlar(kok, tv.COMPARE)
    assert [json.loads(s)["id"] for s in ham] == ["cm-0001", "cm-0002", "cm-0003"]
    assert ham[2] == '{"id":"cm-0003","input":["q:2:256","q:2:255"],"expected":1,"note":"c"}'
    gecerli = next(s for s in ham_satirlar(kok, tv.VALID) if '"id":"an-0001"' in s)
    assert gecerli == (
        '{"id":"an-0001","input":"q:2:255:3-7","expected":{"ref":{"anchor":'
        '{"t":"q","sure":2,"ayet":255,"ilk":3,"son":7}},"canonical":"q:2:255:3-7",'
        '"unit":"q:2:255","unit_span":{"unit":"q:2:255","span":[3,8]},'
        '"ayahs":[{"sure":2,"ayet":255}]}}'
    )
    kimlikler = [json.loads(s)["id"] for s in ham_satirlar(kok, tv.VALID)]
    assert kimlikler == sorted(kimlikler)


def test_iki_kez_calistirmak_ayni_bayti_verir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(kok, tv.VALID, [GECERLI_SATIR])
    satirlari_yaz(kok, tv.OFFSETS, [{"id": "of-0001", "input": ALEM, "expected": {}}])
    assert calistir(kok).exit_code == 0
    once = tum_baytlar(kok)
    ikinci = calistir(kok)
    assert ikinci.exit_code == 0
    assert "degisiklik yok" in ikinci.output
    assert tum_baytlar(kok) == once
    for icerik in once.values():
        assert not icerik.startswith(b"\xef\xbb\xbf")
        assert b"\r" not in icerik
        assert icerik == b"" or icerik.endswith(b"}\n")


def test_eksik_dosyalar_bos_sayilir_ve_dokuz_dosya_yazilir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    assert calistir(kok).exit_code == 0
    baytlar = tum_baytlar(kok)
    assert len(baytlar) == 9
    assert baytlar[tv.NORMALIZE_TR] == b""
    assert baytlar[tv.NORMALIZE_AR] == b""
    assert baytlar[tv.COMPARE] == b""
    assert len(satirlari_oku(kok, tv.VALID)) == 114 + 4
    assert len(satirlari_oku(kok, tv.INVALID)) == 114 + 4


def test_bom_ve_crlf_yazimda_duzelir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    assert calistir(kok).exit_code == 0
    yol = vektor_yolu(kok, tv.COMPARE)
    yol.write_bytes(b'\xef\xbb\xbf{"id":"cm-0001","input":["q:1:1","q:1:2"],"expected":-1}\r\n\r\n')
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert "BOM var" in denetim.output
    assert calistir(kok).exit_code == 0
    assert yol.read_bytes() == b'{"id":"cm-0001","input":["q:1:1","q:1:2"],"expected":-1}\n'


def test_satir_ici_u2028_satir_sonu_sayilmaz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    yol = vektor_yolu(kok, tv.OFFSETS)
    yol.parent.mkdir(parents=True)
    # JSON dizgisinde kacissiz U+2028 ve U+0085 gecerlidir; str.splitlines bunlari boler.
    girdi = "a\N{LINE SEPARATOR}b\x85c"
    yol.write_text(
        '{"id":"of-0001","input":"' + girdi + '","expected":{}}\n',
        encoding="utf-8",
        newline="\n",
    )
    assert calistir(kok).exit_code == 0
    (satir,) = satirlari_oku(kok, tv.OFFSETS)
    assert satir["input"] == girdi
    assert satir["expected"] == {
        "codepoints": 5,
        "utf16": 5,
        "cp_to_utf16": [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5]],
    }
    ters = "\\"
    assert f"a{ters}u2028b{ters}u0085c" in ham_satirlar(kok, tv.OFFSETS)[0]


# --- --check -----------------------------------------------------------------------------


def test_check_sifir_bir_ve_yazmaz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(kok, tv.OFFSETS, [{"id": "of-0001", "input": ALEM, "expected": {}}])
    ilk = calistir(kok, "--check")
    assert ilk.exit_code == 1  # hesaplanan alanlar henuz yok
    assert "offsets/offsets.jsonl (ilk farkli id: of-0001)" in ilk.output
    assert calistir(kok).exit_code == 0
    assert calistir(kok, "--check").exit_code == 0

    yol = vektor_yolu(kok, tv.OFFSETS)
    bozuk = yol.read_bytes().replace(b'"codepoints":6', b'"codepoints":5')
    yol.write_bytes(bozuk)
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert "offsets/offsets.jsonl (ilk farkli id: of-0001)" in denetim.output
    assert "anchors/valid.jsonl" not in denetim.output
    assert yol.read_bytes() == bozuk


def test_check_eksik_uretilmis_satiri_bildirir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    assert calistir(kok).exit_code == 0
    yol = vektor_yolu(kok, tv.INVALID)
    satirlar = ham_satirlar(kok, tv.INVALID)
    yol.write_text(
        "".join(s + "\n" for s in satirlar if '"an-s050-fazla"' not in s),
        encoding="utf-8",
        newline="\n",
    )
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert "anchors/invalid.jsonl (ilk farkli id: an-s050-fazla)" in denetim.output


def test_check_ayet_sayilari_json_yoksa_iki(tmp_path: Path) -> None:
    kok = tmp_path / "bos"
    kok.mkdir()
    assert calistir(kok, "--check").exit_code == 2
    assert calistir(kok).exit_code == 2


@pytest.mark.parametrize(
    ("dosya", "satirlar", "ileti"),
    [
        (tv.VALID, ['{"id":"an-0001",'], "JSON hatasi"),
        (tv.INVALID, [{"id": "an-0002", "input": "q:", "expected": "YOK"}], "bilinmeyen hata"),
        (
            tv.HASH,
            [{"id": "ch-0001", "input": {"text": "a", "op": "kanonik"}, "expected": {}}],
            "'text' eksik",
        ),
        (
            tv.HASH,
            [
                {
                    "id": "ch-0001",
                    "input": {"text": "a", "op": "ham"},
                    "expected": {"text": "a"},
                }
            ],
            "'text' tanimsiz",
        ),
        (
            tv.HASH,
            [{"id": "ch-0001", "input": {"text": "a", "op": "nfc"}, "expected": {}}],
            "'ham' ya da 'kanonik'",
        ),
        (
            tv.COMPARE,
            [
                {"id": "cm-0001", "input": ["q:1:1", "q:1:2"], "expected": -1},
                {"id": "cm-0001", "input": ["q:1:2", "q:1:3"], "expected": -1},
            ],
            "yinelenen id cm-0001",
        ),
        (tv.COMPARE, [{"id": "an-0001", "input": ["a", "b"], "expected": 0}], "'cm-'"),
        (tv.COMPARE, ['{"id":"cm-0001","input":["a","b"],"expected":1.0}'], "ondalik"),
        (tv.COMPARE, [{"id": "cm-0001", "input": ["a", "b"], "expected": 2}], "-1, 0 ya da 1"),
        (tv.CONTAINS, [{"id": "ct-0001", "input": ["a", "b"], "expected": 1}], "true ya da"),
        (tv.VALID, [{"id": "an-0001", "input": "q:1:1", "expected": {"ref": {}}}], "eksik alan"),
        (
            tv.VALID,
            [{"id": "an-0001", "input": "q:1:1", "expected": {}, "fazla": 1}],
            "tanimsiz alan: fazla",
        ),
        (
            tv.OFFSETS,
            [
                {
                    "id": "of-0001",
                    "input": "ab",
                    "expected": {"snap": [{"in": [0, 3], "out": [0, 2]}]},
                }
            ],
            "codepoints degil",
        ),
        (tv.OFFSETS, ['{"id":"of-0001","input":"\\ud835","expected":{}}'], "vekil"),
        (tv.ROUTE, [{"id": "ro-0001", "input": {"capa": "q:1:1"}, "expected": {}}], "eksik alan"),
        (
            tv.NORMALIZE_TR,
            [{"id": "tr-0001", "input": "a", "expected": "a"}],
            "expected: nesne bekleniyor",
        ),
        (
            tv.NORMALIZE_TR,
            [{"id": "tr-0001", "input": "a", "expected": {"dar": "a"}}],
            "eksik alan: genis",
        ),
        (
            tv.NORMALIZE_TR,
            [{"id": "tr-0001", "input": "a", "expected": {"dar": "a", "genis": "a", "stem": "a"}}],
            "tanimsiz alan: stem",
        ),
        (
            tv.NORMALIZE_TR,
            [{"id": "tr-0001", "input": "a", "expected": {"dar": "a", "genis": 1}}],
            "expected.genis: dizgi bekleniyor",
        ),
        (
            tv.NORMALIZE_TR,
            [{"id": "tr-0001", "input": ["a"], "expected": {"dar": "a", "genis": "a"}}],
            "input: dizgi bekleniyor",
        ),
        (tv.NORMALIZE_TR, [{"id": "ar-0001", "input": "a", "expected": {}}], "'tr-'"),
        (
            tv.NORMALIZE_TR,
            [
                {"id": "tr-0001", "input": "a", "expected": {"dar": "a", "genis": "a"}},
                {"id": "tr-0001", "input": "b", "expected": {"dar": "b", "genis": "b"}},
            ],
            "yinelenen id tr-0001",
        ),
        (
            tv.NORMALIZE_AR,
            [{"id": "ar-0001", "input": "a", "expected": {"dar": "a", "genis": "a"}}],
            "expected: dizgi bekleniyor",
        ),
        (tv.NORMALIZE_AR, [{"id": "ar-0001", "input": 1, "expected": "a"}], "input: dizgi"),
        (tv.NORMALIZE_AR, [{"id": "tr-0001", "input": "a", "expected": "a"}], "'ar-'"),
        (
            tv.NORMALIZE_AR,
            [{"id": "ar-0001", "input": "a", "expected": "a", "ek": 1}],
            "tanimsiz alan: ek",
        ),
    ],
    ids=[
        "json-hatasi",
        "bilinmeyen-hata-kodu",
        "kanonik-text-eksik",
        "ham-text-tanimsiz",
        "bilinmeyen-op",
        "yinelenen-id",
        "yanlis-onek",
        "ondalik-sayi",
        "compare-araligi",
        "contains-bool",
        "valid-eksik-alan",
        "tanimsiz-alan",
        "snap-araligi",
        "tek-vekil",
        "route-eksik",
        "tr-expected-dizgi",
        "tr-genis-eksik",
        "tr-fazla-anahtar",
        "tr-genis-sayi",
        "tr-input-dizi",
        "tr-yanlis-onek",
        "tr-yinelenen-id",
        "ar-expected-nesne",
        "ar-input-sayi",
        "ar-yanlis-onek",
        "ar-fazla-alan",
    ],
)
def test_girdi_hatalari_iki(tmp_path: Path, dosya: str, satirlar: list[object], ileti: str) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(kok, dosya, satirlar)
    for ek in ([], ["--check"]):
        sonuc = calistir(kok, *ek)
        assert sonuc.exit_code == 2, sonuc.output
        assert ileti in sonuc.output


def test_valid_ve_invalid_arasinda_yinelenen_id_iki(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(kok, tv.VALID, [GECERLI_SATIR])
    satirlari_yaz(kok, tv.INVALID, [{"id": "an-0001", "input": "q:115:1", "expected": "BICIM"}])
    sonuc = calistir(kok)
    assert sonuc.exit_code == 2
    assert "yinelenen id an-0001" in sonuc.output


# --- Sinir satirlari ---------------------------------------------------------------------


def test_sinir_satirlari_sayisi_ve_uzunluklari(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    eski = {"id": "an-s001-son", "input": "q:1:999", "expected": {"ref": {}, "canonical": "x"}}
    bayat = {"id": "an-s999-son", "input": "q:999:1", "expected": "bozuk"}
    satirlari_yaz(kok, tv.VALID, [GECERLI_SATIR, eski, bayat])
    satirlari_yaz(kok, tv.INVALID, [{"id": "an-u-eski", "input": "x", "expected": "YOK"}])
    sonuc = calistir(kok)
    assert sonuc.exit_code == 0, sonuc.output

    gecerli = {s["id"]: s for s in satirlari_oku(kok, tv.VALID)}
    gecersiz = {s["id"]: s for s in satirlari_oku(kok, tv.INVALID)}
    assert "an-0001" in gecerli
    assert "an-s999-son" not in gecerli and "an-u-eski" not in gecersiz
    assert sum(1 for k in gecerli if k.startswith("an-s") and k.endswith("-son")) == 114
    assert sum(1 for k in gecersiz if k.startswith("an-s") and k.endswith("-fazla")) == 114
    assert sorted(k for k in gecerli if k.startswith("an-u-")) == [
        "an-u-derinlik-8",
        "an-u-sayi-2147483647",
        "an-u-slug-64",
        "an-u-toplam-256",
    ]
    assert sorted(k for k in gecersiz if k.startswith("an-u-")) == [
        "an-u-derinlik-9",
        "an-u-sayi-2147483648",
        "an-u-slug-65",
        "an-u-toplam-257",
    ]

    for sure, son in enumerate(SENTETIK_SAYILAR, start=1):
        capa = f"q:{sure}:{son}"
        assert gecerli[f"an-s{sure:03d}-son"] == {
            "id": f"an-s{sure:03d}-son",
            "input": capa,
            "expected": {
                "ref": {"anchor": {"t": "q", "sure": sure, "ayet": son}},
                "canonical": capa,
                "unit": capa,
                "unit_span": {"unit": capa},
                "ayahs": [{"sure": sure, "ayet": son}],
            },
        }
        assert gecersiz[f"an-s{sure:03d}-fazla"] == {
            "id": f"an-s{sure:03d}-fazla",
            "input": f"q:{sure}:{son + 1}",
            "expected": "AYET_ARALIGI",
        }

    toplam_256 = gecerli["an-u-toplam-256"]["input"]
    toplam_257 = gecersiz["an-u-toplam-257"]["input"]
    assert isinstance(toplam_256, str) and isinstance(toplam_257, str)
    assert len(toplam_256) == 256
    assert len(toplam_257) == 257
    assert gecersiz["an-u-toplam-257"]["expected"] == "UZUNLUK"
    assert gecerli["an-u-slug-64"]["input"] == "konu:" + "a" * 64
    assert gecersiz["an-u-slug-65"]["input"] == "konu:" + "a" * 65
    assert gecerli["an-u-derinlik-8"]["input"] == "rn:a:b:c:d:e:f:g:h:p1"
    assert gecersiz["an-u-derinlik-9"]["input"] == "rn:a:b:c:d:e:f:g:h:i:p1"
    assert gecerli["an-u-sayi-2147483647"]["expected"] == {
        "ref": {"anchor": {"t": "h", "koleksiyon": "deneme", "no": 2147483647}},
        "canonical": "h:deneme:2147483647",
        "unit": "h:deneme:2147483647",
        "unit_span": {"unit": "h:deneme:2147483647"},
        "ayahs": [],
    }
    assert gecersiz["an-u-sayi-2147483648"]["input"] == "h:deneme:2147483648"
    toplam_ref = gecerli["an-u-toplam-256"]["expected"]
    assert isinstance(toplam_ref, dict)
    assert toplam_ref["ref"] == {
        "anchor": {"t": "rn", "yol": ["a" * 64, "b" * 64, "c" * 64, "d" * 55], "p": 1}
    }


def test_uretec_capa_ayristiricisini_ice_aktarmaz() -> None:
    kaynak = Path(tv.__file__).read_text(encoding="utf-8")
    assert "mutalaa_pipeline.anchor" not in kaynak
    assert "ayet_sayilari import json_oku" in kaynak


def test_uretec_normalizasyon_modulunu_ice_aktarmaz() -> None:
    """`expected` elle yazilir; normallestiriciden uretilirse vektor kendini dogrular."""
    kaynak = Path(tv.__file__).read_text(encoding="utf-8")
    ice_aktarilan: list[str] = []
    for dugum in ast.walk(ast.parse(kaynak)):
        if isinstance(dugum, ast.Import):
            ice_aktarilan += [oge.name for oge in dugum.names]
        elif isinstance(dugum, ast.ImportFrom):
            modul = dugum.module or ""
            ice_aktarilan.append(modul)
            ice_aktarilan += [f"{modul}.{oge.name}" for oge in dugum.names]
    assert ice_aktarilan
    assert not [ad for ad in ice_aktarilan if "normalize" in ad.split(".")]
    assert not [ad for ad in ice_aktarilan if ad.startswith("mutalaa_pipeline.anchor")]
    assert "from mutalaa_pipeline.normalize" not in kaynak


def test_uzunluk_denetimi_girdi_hatasidir() -> None:
    with pytest.raises(GirdiHatasi):
        tv._uzunluk_denetle("abc", 4)
    assert tv._uzunluk_denetle("abc", 3) == "abc"


def test_sinir_capasi_uzunluk_hatasi_cikis_ikidir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dahili uzunluk hatasi 1 (--check farki) ile karismaz; GirdiHatasi 2 ile cikar."""

    def bozuk(_sayilar: object) -> object:
        return tv._uzunluk_denetle("abc", 4)

    monkeypatch.setattr(tv, "sinir_satirlari", bozuk)
    kok = kok_kur(tmp_path)
    assert calistir(kok).exit_code == 2
    assert calistir(kok, "--check").exit_code == 2


# --- Normalizasyon vektorleri (A05.2): elle yazilan expected, yalniz bicim -----------------

# Sentetik girdiler: Turkce harfler ve tek tek Arapca harf/isaretler; hicbiri metin alintisi degil.
ISARETLI_I = "\N{LATIN CAPITAL LETTER I WITH DOT ABOVE}"
BA = "\N{ARABIC LETTER BEH}"
ELIF = "\N{ARABIC LETTER ALEF}"
FETHA = "\N{ARABIC FATHA}"
SEDDE = "\N{ARABIC SHADDA}"
YUMUSAK_TIRE = "\N{SOFT HYPHEN}"
SIFIR_GENISLIK_BOSLUK = "\N{ZERO WIDTH SPACE}"
TEK_VEKIL = "\ud835"
OK = "\N{RIGHTWARDS ARROW}"
TERS = "\\"


def tr_satiri(kimlik: str, girdi: str, dar: str, genis: str) -> dict[str, object]:
    return {"id": kimlik, "input": girdi, "expected": {"dar": dar, "genis": genis}}


def test_normalize_tr_ar_kacis_ve_anahtar_sirasi(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    karisik = {
        "note": f"I {OK} {NOKTASIZ_I}; {ISARETLI_I} {OK} i",
        "expected": {"genis": "isik", "dar": f"{NOKTASIZ_I}{CENGELLI_S}{NOKTASIZ_I}k"},
        "input": f"I{CENGELLI_S}{NOKTASIZ_I}k {ISARETLI_I}",
        "id": "tr-0001",
    }
    satirlari_yaz(
        kok,
        tv.NORMALIZE_TR,
        [
            tr_satiri("tr-0003", f"a{SAPKA}lem", "alem", "alem"),
            karisik,
            tr_satiri("tr-0002", f"x{YUMUSAK_TIRE}y{SIFIR_GENISLIK_BOSLUK}z", "xy z", "xy z"),
            tr_satiri("tr-0004", f"a{TEK_VEKIL}b", "a b", "a b"),
        ],
    )
    satirlari_yaz(
        kok,
        tv.NORMALIZE_AR,
        [
            {"id": "ar-0002", "input": ELIF, "expected": ELIF},
            {"id": "ar-0001", "input": BA + FETHA + SEDDE, "expected": BA, "note": "isaret silme"},
        ],
    )
    sonuc = calistir(kok)
    assert sonuc.exit_code == 0, sonuc.output

    tr_ham = ham_satirlar(kok, tv.NORMALIZE_TR)
    assert [json.loads(s)["id"] for s in tr_ham] == ["tr-0001", "tr-0002", "tr-0003", "tr-0004"]
    # Anahtar sirasi: id, input, expected{dar, genis}, note. Turkce harfler duz; bicim
    # karakterleri, birlesen isaretler ve tek vekil \u kacisli.
    assert tr_ham[0] == (
        f'{{"id":"tr-0001","input":"I{CENGELLI_S}{NOKTASIZ_I}k {ISARETLI_I}",'
        f'"expected":{{"dar":"{NOKTASIZ_I}{CENGELLI_S}{NOKTASIZ_I}k","genis":"isik"}},'
        f'"note":"I {OK} {NOKTASIZ_I}; {ISARETLI_I} {OK} i"}}'
    )
    assert f"x{TERS}u00ady{TERS}u200bz" in tr_ham[1]
    assert f"a{TERS}u0302lem" in tr_ham[2]
    assert f"a{TERS}ud835b" in tr_ham[3]
    for ham in tr_ham:
        assert SAPKA not in ham
        assert YUMUSAK_TIRE not in ham
        assert SIFIR_GENISLIK_BOSLUK not in ham
    assert json.loads(tr_ham[3])["input"] == f"a{TEK_VEKIL}b"  # gidis-donus

    ar_ham = ham_satirlar(kok, tv.NORMALIZE_AR)
    assert [json.loads(s)["id"] for s in ar_ham] == ["ar-0001", "ar-0002"]
    assert ar_ham[0] == (
        f'{{"id":"ar-0001","input":"{TERS}u0628{TERS}u064e{TERS}u0651",'
        f'"expected":"{TERS}u0628","note":"isaret silme"}}'
    )
    assert BA not in ar_ham[0]
    assert ar_ham[1] == f'{{"id":"ar-0002","input":"{TERS}u0627","expected":"{TERS}u0627"}}'

    ikinci = calistir(kok)
    assert ikinci.exit_code == 0
    assert "degisiklik yok" in ikinci.output
    assert calistir(kok, "--check").exit_code == 0


def test_normalize_expected_hesaplanmaz_oldugu_gibi_yazilir(tmp_path: Path) -> None:
    """Yanlis gorunen expected da degistirilmez: uretec normalizasyon hesaplamaz."""
    kok = kok_kur(tmp_path)
    satirlari_yaz(kok, tv.NORMALIZE_TR, [tr_satiri("tr-0001", "Abc", "YANLIS", "yanlis")])
    satirlari_yaz(kok, tv.NORMALIZE_AR, [{"id": "ar-0001", "input": "x", "expected": "y"}])
    assert calistir(kok).exit_code == 0
    (tr,) = satirlari_oku(kok, tv.NORMALIZE_TR)
    (ar,) = satirlari_oku(kok, tv.NORMALIZE_AR)
    assert tr["expected"] == {"dar": "YANLIS", "genis": "yanlis"}
    assert ar["expected"] == "y"


def test_normalize_dosyalari_ayri_kimlik_gruplari(tmp_path: Path) -> None:
    """tr ve ar farkli onek tasir; ikisi birlikte sorunsuz yazilir."""
    kok = kok_kur(tmp_path)
    satirlari_yaz(kok, tv.NORMALIZE_TR, [tr_satiri("tr-0001", "a", "a", "a")])
    satirlari_yaz(kok, tv.NORMALIZE_AR, [{"id": "ar-0001", "input": "a", "expected": "a"}])
    assert calistir(kok).exit_code == 0


def test_normalize_check_fark_ve_bicim(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    satirlari_yaz(
        kok,
        tv.NORMALIZE_TR,
        [tr_satiri("tr-0002", "b", "b", "b"), tr_satiri("tr-0001", "a", "a", "a")],
    )
    ilk = calistir(kok, "--check")  # sirasiz ve bicimsiz (json.dumps) yazildi
    assert ilk.exit_code == 1
    assert "normalize/tr.jsonl (ilk farkli id: tr-0001)" in ilk.output
    assert calistir(kok).exit_code == 0
    assert calistir(kok, "--check").exit_code == 0
    yol = vektor_yolu(kok, tv.NORMALIZE_TR)
    # expected elle yazildigi icin deger degisikligi fark degildir; bicim (bosluk) farki fark olur.
    yol.write_bytes(yol.read_bytes().replace(b'"dar":"b"', b'"dar": "b"'))
    denetim = calistir(kok, "--check")
    assert denetim.exit_code == 1
    assert "normalize/tr.jsonl (ilk farkli id: tr-0002)" in denetim.output
    assert "normalize/ar.jsonl" not in denetim.output
