"""`mutalaa sources list` ve `sources check` testleri (A06.1, G-LIS).

Fiksturler `tmp_path` altinda kodla uretilir: her senaryo kendi sahte kokunu
(`pnpm-workspace.yaml` + `pipeline/sources/licenses/`) kurar ve `--kok` ile verir. Tum kayitlar
`test-` onekli SENTETIK kayittir; gercek kaynak metni yoktur.
"""

import hashlib
import json
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner, Result

from mutalaa_pipeline import cli, sources
from mutalaa_pipeline.enums import LicenseStatus, SourceKind
from mutalaa_pipeline.export.ortak import depo_koku

runner = CliRunner()

LISANS_ICERIGI = b"Deneme lisans metni 1\nDeneme lisans metni 2\n"
ATIF = "Deneme atif metni."
GECMIS = date(2000, 1, 1)
GELECEK = date(2999, 1, 1)


# --- Yardimcilar -------------------------------------------------------------------------


def kok_kur(tmp_path: Path) -> Path:
    kok = tmp_path / "kok"
    (kok / "pipeline" / "sources" / "licenses").mkdir(parents=True)
    (kok / "pnpm-workspace.yaml").write_bytes(b"")
    return kok


def kaynaklar(kok: Path) -> Path:
    return kok / "pipeline" / "sources"


def deger_yaz(deger: object) -> str:
    if isinstance(deger, bool):
        return "true" if deger else "false"
    if isinstance(deger, date):
        return deger.isoformat()
    if isinstance(deger, int):
        return str(deger)
    if isinstance(deger, str):
        return json.dumps(deger)
    if isinstance(deger, dict):
        ic = ", ".join(f"{ad} = {deger_yaz(v)}" for ad, v in deger.items())
        return "{ " + ic + " }"
    raise TypeError(type(deger))


def toml_metni(alanlar: dict[str, object]) -> str:
    return "".join(f"{ad} = {deger_yaz(v)}\n" for ad, v in alanlar.items())


def lisans_yaz(kok: Path, slug: str, icerik: bytes = LISANS_ICERIGI) -> tuple[str, str]:
    """Lisans kopyasini yazar; (goreli yol, sha256) dondurur."""
    goreli = f"licenses/{slug}-2026-10-19.txt"
    (kaynaklar(kok) / goreli).write_bytes(icerik)
    return goreli, hashlib.sha256(icerik).hexdigest()


def alanlar_kur(slug: str, /, kok: Path | None = None, **degisim: object) -> dict[str, object]:
    """Gecerli bir `serbest` kayit; `kok` verilirse lisans kopyasi da yazilir."""
    alanlar: dict[str, object] = {
        "slug": slug,
        "tur": "kuran_metni",
        "baslik": "Deneme kaynak",
        "license_name": "Deneme lisansi",
        "license_status": "serbest",
        "atif_metni": ATIF,
        "kurul_gerekli": False,
        "embed_ok": True,
        "yeniden_kontrol": GELECEK,
    }
    if kok is not None:
        kopya, ozet = lisans_yaz(kok, slug)
        alanlar["lisans_kopyasi"] = kopya
        alanlar["lisans_sha256"] = ozet
    alanlar.update(degisim)
    return {ad: v for ad, v in alanlar.items() if v is not None}


def kayit_yaz(kok: Path, alanlar: dict[str, object], dosya: str | None = None) -> None:
    ad = dosya if dosya is not None else f"{alanlar['slug']}.toml"
    (kaynaklar(kok) / ad).write_bytes(toml_metni(alanlar).encode("utf-8"))


def calistir(kok: Path, *argumanlar: str) -> Result:
    return runner.invoke(cli.app, ["sources", *argumanlar, "--kok", str(kok)])


def check(kok: Path) -> Result:
    return calistir(kok, "check")


# --- check: gecerli ve bos ---------------------------------------------------------------


def test_gecerli_kayit_sifir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-gecerli", kok))
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "1 kayit, 0 hata, 0 uyari" in sonuc.stdout
    assert sonuc.stderr == ""


def test_gecerli_kayit_tum_istege_bagli_alanlarla(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(
        kok,
        alanlar_kur(
            "test-tam",
            kok,
            yazar="Deneme Yazar",
            yazar_vefat_yili=1900,
            surum="1",
            provider="deneme",
            kaynak_url="https://example.invalid/kaynak",
            license_url="https://example.invalid/lisans",
            kisitlar={
                "degistirme_yasak": True,
                "hazir_vt_yasak": True,
                "onbellek_gun": 7,
                "yalniz_eslesen_ses": True,
            },
            notice_text="Deneme bildirim.",
            atif_url="https://example.invalid/atif",
            kamu_mali_tarihi=date(2030, 1, 1),
            baski_bilgisi={"yil": 1935, "yayinevi": "Deneme"},
            notlar="Deneme notu.",
        ),
    )
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert sonuc.stderr == ""


def test_bos_dizin_sifir_ve_not(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    sonuc = check(kok)
    assert sonuc.exit_code == 0
    assert "kayit yok" in sonuc.stdout


def test_toml_olmayan_dosyalar_yok_sayilir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    (kaynaklar(kok) / "README.txt").write_bytes(b"not\n")
    sonuc = check(kok)
    assert sonuc.exit_code == 0
    assert "kayit yok" in sonuc.stdout


def test_kaynak_klasoru_yoksa_iki(tmp_path: Path) -> None:
    kok = tmp_path / "kok"
    kok.mkdir()
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata:" in sonuc.stderr


def test_gercek_depoda_check_sifir() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "check"])
    assert sonuc.exit_code == 0, sonuc.stderr


# --- check: hata senaryolari -------------------------------------------------------------


def test_bozuk_toml(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    (kaynaklar(kok) / "test-bozuk.toml").write_bytes(b'slug = "test-bozuk\nbaslik = =\n')
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-bozuk.toml: TOML ayristirilamadi" in sonuc.stderr


def test_bom_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    veri = toml_metni(alanlar_kur("test-bom", kok)).encode("utf-8")
    (kaynaklar(kok) / "test-bom.toml").write_bytes(b"\xef\xbb\xbf" + veri)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-bom.toml: BOM var" in sonuc.stderr


def test_crlf_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    veri = toml_metni(alanlar_kur("test-crlf", kok)).replace("\n", "\r\n").encode("utf-8")
    (kaynaklar(kok) / "test-crlf.toml").write_bytes(veri)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-crlf.toml: CR/CRLF" in sonuc.stderr


def test_utf8_degil_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    (kaynaklar(kok) / "test-latin.toml").write_bytes(b'baslik = "\xe7"\n')
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-latin.toml: UTF-8 degil" in sonuc.stderr


def test_eksik_lisans_kopyasi_dosyasi(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    alanlar = alanlar_kur("test-eksik", kok)
    (kaynaklar(kok) / str(alanlar["lisans_kopyasi"])).unlink()
    kayit_yaz(kok, alanlar)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-eksik.toml: lisans_kopyasi dosyasi yok" in sonuc.stderr


def test_eksik_lisans_alanlari(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-alansiz"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "lisans_kopyasi zorunlu" in sonuc.stderr
    assert "lisans_sha256 zorunlu" in sonuc.stderr


def test_yanlis_ozet(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    gercek = hashlib.sha256(LISANS_ICERIGI).hexdigest()
    kayit_yaz(kok, alanlar_kur("test-ozet", kok, lisans_sha256="0" * 64))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-ozet.toml: lisans_sha256 dosya ozetiyle ayni degil" in sonuc.stderr
    assert f"hesaplanan: {gercek}" in sonuc.stderr


@pytest.mark.parametrize("ozet", ["ABC", "A" * 64, "g" * 64, "0" * 63])
def test_ozet_bicimi(tmp_path: Path, ozet: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bicim", kok, lisans_sha256=ozet))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "lisans_sha256 64 haneli kucuk harfli" in sonuc.stderr


def test_bilinmeyen_durum(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-durum", kok, license_status="acik"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-durum.toml: license_status: bilinmeyen deger" in sonuc.stderr


def test_bilinmeyen_tur(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-tur", kok, tur="roman"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-tur.toml: tur: bilinmeyen deger" in sonuc.stderr


def test_dosya_adi_slug_ile_ayni_degil(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-slug", kok), dosya="test-baska.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-baska.toml: slug (test-slug) dosya adiyla (test-baska) ayni degil" in (
        sonuc.stderr
    )


@pytest.mark.parametrize("dosya", ["Test-Buyuk.toml", "test_alt.toml", "test--cift.toml"])
def test_dosya_adi_deseni(tmp_path: Path, dosya: str) -> None:
    kok = kok_kur(tmp_path)
    slug = dosya[: -len(".toml")]
    kayit_yaz(kok, alanlar_kur(slug), dosya=dosya)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "desenine uymuyor" in sonuc.stderr


def test_ascii_olmayan_dosya_adi(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-\u0131"), dosya="test-\u0131.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "desenine uymuyor" in sonuc.stderr
    assert sonuc.stderr.isascii()


def test_bilinmeyen_alan(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-alan", kok, fazladan="x"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-alan.toml: bilinmeyen alan: fazladan" in sonuc.stderr


@pytest.mark.parametrize(
    "eksik", ["slug", "tur", "baslik", "license_name", "license_status", "atif_metni"]
)
def test_zorunlu_alan_eksik(tmp_path: Path, eksik: str) -> None:
    kok = kok_kur(tmp_path)
    alanlar = alanlar_kur("test-zorunlu", kok)
    del alanlar[eksik]
    kayit_yaz(kok, alanlar, dosya="test-zorunlu.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"zorunlu alan eksik: {eksik}" in sonuc.stderr


@pytest.mark.parametrize("eksik", ["kurul_gerekli", "embed_ok", "yeniden_kontrol"])
def test_zorunlu_bool_ve_tarih_eksik(tmp_path: Path, eksik: str) -> None:
    kok = kok_kur(tmp_path)
    alanlar = alanlar_kur("test-zorunlu", kok)
    del alanlar[eksik]
    kayit_yaz(kok, alanlar)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"zorunlu alan eksik: {eksik}" in sonuc.stderr


@pytest.mark.parametrize("metin", ["", "   ", " \t\n"])
def test_atif_metni_bos(tmp_path: Path, metin: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-atif", kok, atif_metni=metin))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "atif_metni bos olamaz" in sonuc.stderr


@pytest.mark.parametrize(
    ("alan", "deger", "beklenen"),
    [
        ("embed_ok", "true", "embed_ok: bool olmali"),
        ("kurul_gerekli", 1, "kurul_gerekli: bool olmali"),
        ("yazar_vefat_yili", True, "yazar_vefat_yili: tam sayi olmali"),
        ("yazar_vefat_yili", "1900", "yazar_vefat_yili: tam sayi olmali"),
        ("yeniden_kontrol", "2999-01-01", "yeniden_kontrol: TOML tarihi olmali"),
        ("kisitlar", "x", "kisitlar: tablo olmali"),
        ("kamu_mali_tarihi", "2030", "kamu_mali_tarihi: TOML tarihi olmali"),
        ("baski_bilgisi", "x", "baski_bilgisi: tablo olmali"),
        ("slug", 5, "slug: metin olmali"),
    ],
)
def test_tip_hatalari(tmp_path: Path, alan: str, deger: object, beklenen: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-tip", kok, **{alan: deger}), dosya="test-tip.toml")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert beklenen in sonuc.stderr


def test_tarih_saatli_deger_tarih_degil(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    alanlar = alanlar_kur("test-saat", kok)
    metin = toml_metni(alanlar).replace("2999-01-01", "2999-01-01T00:00:00")
    (kaynaklar(kok) / "test-saat.toml").write_bytes(metin.encode("utf-8"))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "yeniden_kontrol: TOML tarihi olmali" in sonuc.stderr


# --- check: kapali ve embed_ok kurallari -------------------------------------------------


def test_kapali_embed_ok_true_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-kapali", license_status="kapali", embed_ok=True))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-kapali.toml: license_status kapali iken embed_ok true olamaz" in (
        sonuc.stderr
    )


def test_kapali_lisans_kopyasiz_gecerli(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-kapali", license_status="kapali", embed_ok=False))
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "0 hata" in sonuc.stdout


def test_kapali_kaynakta_lisans_dosyasi_okunmaz(tmp_path: Path) -> None:
    """Kapali kayitta kopya alani verilse bile dosya aranmaz ve ozet karsilastirilmaz."""
    kok = kok_kur(tmp_path)
    kopya, _ = lisans_yaz(kok, "test-kapali")
    alanlar = alanlar_kur(
        "test-kapali",
        license_status="kapali",
        embed_ok=False,
        lisans_kopyasi=kopya,
        lisans_sha256="0" * 64,
    )
    kayit_yaz(kok, alanlar)
    kayit_yaz(
        kok,
        alanlar_kur(
            "test-kapali-yok",
            license_status="kapali",
            embed_ok=False,
            lisans_kopyasi="licenses/test-kapali-yok-2026-10-19.txt",
            lisans_sha256="1" * 64,
        ),
    )
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr


def test_quran_foundation_embed_ok_true_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-qf", kok, provider="quran_foundation", embed_ok=True))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "provider quran_foundation iken embed_ok true olamaz" in sonuc.stderr


def test_quran_foundation_embed_ok_false_gecerli(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-qf", kok, provider="quran_foundation", embed_ok=False))
    assert check(kok).exit_code == 0


@pytest.mark.parametrize("durum", ["bekliyor", "ic_kullanim"])
def test_kapali_disindaki_durumlar_lisans_kopyasi_ister(tmp_path: Path, durum: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-durum", license_status=durum))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "lisans_kopyasi zorunlu" in sonuc.stderr


# --- check: yol kacisi -------------------------------------------------------------------


@pytest.mark.parametrize(
    "yol",
    [
        "../x",
        "licenses/../x-2026-10-19.txt",
        "licenses\\test-yol-2026-10-19.txt",
        "/etc/test-yol-2026-10-19.txt",
        "C:/test-yol-2026-10-19.txt",
        "licenses/test-yol.txt",
        "licenses/test-baska-2026-10-19.txt",
        "licenses/test-yol-2026-13-40.txt",
        "test-yol-2026-10-19.txt",
        "licenses/alt/test-yol-2026-10-19.txt",
    ],
)
def test_lisans_kopyasi_yolu_gecersiz(tmp_path: Path, yol: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-yol", kok, lisans_kopyasi=yol))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-yol.toml: lisans_kopyasi" in sonuc.stderr


def test_yol_kacisi_dis_dosyayi_okumaz(tmp_path: Path) -> None:
    """`../x` ile dis dosya gosterilse bile ozet dis dosyadan hesaplanmaz."""
    kok = kok_kur(tmp_path)
    dis = kok / "pipeline" / "dis.txt"
    dis.write_bytes(LISANS_ICERIGI)
    kayit_yaz(
        kok,
        alanlar_kur(
            "test-yol",
            lisans_kopyasi="../dis.txt",
            lisans_sha256=hashlib.sha256(LISANS_ICERIGI).hexdigest(),
        ),
    )
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "'..' iceremez" in sonuc.stderr


# --- check: kisitlar ---------------------------------------------------------------------


def test_bilinmeyen_kisit_uyari_cikis_sifir(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-kisit", kok, kisitlar={"yeni_kisit": True}))
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "uyari: test-kisit.toml: kisitlar: bilinmeyen anahtar yeni_kisit" in sonuc.stderr
    assert "0 hata, 1 uyari" in sonuc.stdout


@pytest.mark.parametrize(
    ("anahtar", "deger"),
    [
        ("degistirme_yasak", "evet"),
        ("hazir_vt_yasak", 1),
        ("onbellek_gun", True),
        ("onbellek_gun", "7"),
        ("yalniz_eslesen_ses", 0),
    ],
)
def test_kisit_tipi_hata(tmp_path: Path, anahtar: str, deger: object) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-kisit", kok, kisitlar={anahtar: deger}))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"kisitlar.{anahtar}:" in sonuc.stderr


# --- check: toplama ve gizlilik ----------------------------------------------------------


def test_hatalar_toplanir_ilkinde_durmaz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-a", kok, tur="roman", license_status="acik", fazladan=1))
    kayit_yaz(kok, alanlar_kur("test-b", kok, lisans_sha256="0" * 64))
    (kaynaklar(kok) / "test-c.toml").write_bytes(b"=\n")
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-a.toml: tur:" in sonuc.stderr
    assert "hata: test-a.toml: license_status:" in sonuc.stderr
    assert "hata: test-a.toml: bilinmeyen alan: fazladan" in sonuc.stderr
    assert "hata: test-b.toml: lisans_sha256 dosya ozetiyle" in sonuc.stderr
    assert "hata: test-c.toml: TOML ayristirilamadi" in sonuc.stderr
    assert "3 kayit, 5 hata" in sonuc.stdout


def test_cikti_icerik_metni_tasimaz(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    gizli = "GIZLI-ATIF-ICERIGI-XYZ"
    kayit_yaz(kok, alanlar_kur("test-gizli", kok, atif_metni=gizli, tur="roman"))
    kayit_yaz(kok, alanlar_kur("test-gizli-iki", kok, atif_metni=gizli))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert gizli not in sonuc.stdout
    assert gizli not in sonuc.stderr
    listeleme = calistir(kok, "list", "--format", "json")
    assert gizli not in listeleme.stdout


# --- list --------------------------------------------------------------------------------


def test_list_json_siralama_ve_alanlar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "bugun", lambda: date(2026, 10, 26))
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-z", kok, yeniden_kontrol=date(2026, 10, 25)))
    kayit_yaz(
        kok,
        alanlar_kur(
            "test-a",
            license_status="kapali",
            embed_ok=False,
            kurul_gerekli=True,
            tur="risale",
            yeniden_kontrol=date(2026, 10, 26),
        ),
    )
    kayit_yaz(kok, alanlar_kur("test-m", kok, yeniden_kontrol=date(2027, 4, 1), embed_ok=False))
    sonuc = calistir(kok, "list", "--format", "json")
    assert sonuc.exit_code == 0, sonuc.stderr
    veri = json.loads(sonuc.stdout)
    assert [s["slug"] for s in veri] == ["test-a", "test-m", "test-z"]
    assert veri[0] == {
        "slug": "test-a",
        "tur": "risale",
        "license_status": "kapali",
        "kurul_gerekli": True,
        "embed_ok": False,
        "yeniden_kontrol": "2026-10-26",
        "yeniden_kontrol_gecmis": False,
    }
    assert [s["yeniden_kontrol_gecmis"] for s in veri] == [False, False, True]


def test_list_varsayilan_bicim_tablo_ve_isaret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "bugun", lambda: date(2026, 10, 26))
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", kok, yeniden_kontrol=GECMIS))
    kayit_yaz(kok, alanlar_kur("test-yeni", kok, yeniden_kontrol=GELECEK))
    sonuc = calistir(kok, "list")
    assert sonuc.exit_code == 0, sonuc.stderr
    satirlar = sonuc.stdout.splitlines()
    assert satirlar[0].split() == [
        "slug",
        "tur",
        "license_status",
        "kurul_gerekli",
        "embed_ok",
        "yeniden_kontrol",
    ]
    eski = next(s for s in satirlar if s.startswith("test-eski"))
    yeni = next(s for s in satirlar if s.startswith("test-yeni"))
    assert eski.endswith("2000-01-01 !")
    assert yeni.endswith("2999-01-01")
    assert "!" not in yeni
    assert eski.split()[:5] == ["test-eski", "kuran_metni", "serbest", "hayir", "evet"]


def test_list_gercek_bugunle_cok_eski_ve_cok_ileri(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", kok, yeniden_kontrol=GECMIS))
    kayit_yaz(kok, alanlar_kur("test-ileri", kok, yeniden_kontrol=GELECEK))
    veri = json.loads(calistir(kok, "list", "--format", "json").stdout)
    assert {s["slug"]: s["yeniden_kontrol_gecmis"] for s in veri} == {
        "test-eski": True,
        "test-ileri": False,
    }


def test_list_bos_dizin(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    tablo = calistir(kok, "list")
    assert tablo.exit_code == 0
    assert "kayit yok" in tablo.stdout
    bicim_json = calistir(kok, "list", "--format", "json")
    assert bicim_json.exit_code == 0
    assert json.loads(bicim_json.stdout) == []


def test_list_bozuk_toml_iki(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-iyi", kok))
    (kaynaklar(kok) / "test-bozuk.toml").write_bytes(b"slug = \n")
    sonuc = calistir(kok, "list", "--format", "json")
    assert sonuc.exit_code == 2
    assert "hata: test-bozuk.toml: TOML ayristirilamadi" in sonuc.stderr


def test_list_gecersiz_sema_iki(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-durum", kok, license_status="acik"))
    sonuc = calistir(kok, "list")
    assert sonuc.exit_code == 2
    assert "license_status: bilinmeyen deger" in sonuc.stderr


def test_list_lisans_dosyasini_denetlemez(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-ozet", kok, lisans_sha256="0" * 64))
    assert calistir(kok, "list").exit_code == 0
    assert check(kok).exit_code == 2


def test_list_gecersiz_format() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "list", "--format", "xml"])
    assert sonuc.exit_code == 2


def test_gercek_depoda_list_calisir() -> None:
    sonuc = runner.invoke(cli.app, ["sources", "list", "--format", "json"])
    assert sonuc.exit_code == 0, sonuc.stderr
    assert isinstance(json.loads(sonuc.stdout), list)


# --- Kutuphane katmani -------------------------------------------------------------------


def test_satirlar_bugunu_enjekte_eder(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-sinir", kok, yeniden_kontrol=date(2026, 10, 26)))
    kayit = sources.yukle(kok, lisans_dosyalari=True)[0].kaynak
    assert kayit is not None
    assert kayit.slug == "test-sinir"
    assert kayit.tur is SourceKind.KURAN_METNI
    assert kayit.license_status is LicenseStatus.SERBEST
    assert sources.gecmis_mi(kayit, date(2026, 10, 26)) is False
    assert sources.gecmis_mi(kayit, date(2026, 10, 27)) is True
    assert sources.satirlar([kayit], date(2026, 10, 27))[0]["yeniden_kontrol_gecmis"] is True


def test_gercek_kaynak_dizini_depo_icinde() -> None:
    assert sources.kaynak_dizini(depo_koku()).is_dir()


# --- check: saglamlastirma (A06 inceleme duzeltmeleri) -----------------------------------


def test_lisans_kopyasi_okunamazsa_iki_izleme_yok(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-izin", kok))
    gercek_okuma = Path.read_bytes

    def okuma(self: Path) -> bytes:
        if self.suffix == ".txt":
            raise PermissionError
        return gercek_okuma(self)

    monkeypatch.setattr(Path, "read_bytes", okuma)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-izin.toml: lisans_kopyasi okunamadi" in sonuc.stderr
    assert "Traceback" not in sonuc.stderr
    assert isinstance(sonuc.exception, SystemExit)


def test_lisans_kopyasi_cozumlenemezse_iki(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Sembolik bag dongusu `resolve()` icinde RuntimeError verebilir."""
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-dongu", kok))
    gercek_cozum = Path.resolve

    def cozum(self: Path, strict: bool = False) -> Path:
        if self.suffix == ".txt":
            raise RuntimeError
        return gercek_cozum(self, strict=strict)

    monkeypatch.setattr(Path, "resolve", cozum)
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "lisans_kopyasi okunamadi" in sonuc.stderr
    assert isinstance(sonuc.exception, SystemExit)


@pytest.mark.parametrize("alan", ["baslik", "license_name"])
@pytest.mark.parametrize("metin", ["", "   ", " \t\n"])
def test_zorunlu_metin_alani_bos(tmp_path: Path, alan: str, metin: str) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bosalan", kok, **{alan: metin}))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert f"hata: test-bosalan.toml: {alan} bos olamaz" in sonuc.stderr


def test_bos_lisans_kopyasi_hata(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kopya, _ = lisans_yaz(kok, "test-bos", b"")
    kayit_yaz(
        kok,
        alanlar_kur(
            "test-bos",
            lisans_kopyasi=kopya,
            lisans_sha256=hashlib.sha256(b"").hexdigest(),
        ),
    )
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "hata: test-bos.toml: lisans_kopyasi bos dosya" in sonuc.stderr


@pytest.mark.parametrize("gun", [0, -1])
def test_onbellek_gun_birden_kucuk_hata(tmp_path: Path, gun: int) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-onbellek", kok, kisitlar={"onbellek_gun": gun}))
    sonuc = check(kok)
    assert sonuc.exit_code == 2
    assert "kisitlar.onbellek_gun 1 veya daha buyuk olmali" in sonuc.stderr


def test_onbellek_gun_bir_gecerli(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-onbellek", kok, kisitlar={"onbellek_gun": 1}))
    assert check(kok).exit_code == 0


def test_yetim_lisans_dosyasi_uyari(tmp_path: Path) -> None:
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-bagli", kok))
    (kaynaklar(kok) / "licenses" / "test-yetim-2026-10-19.txt").write_bytes(b"x\n")
    (kaynaklar(kok) / "licenses" / ".gitkeep").write_bytes(b"")
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "uyari: licenses/test-yetim-2026-10-19.txt:" in sonuc.stderr
    assert ".gitkeep" not in sonuc.stderr
    assert "test-bagli-2026-10-19.txt" not in sonuc.stderr
    assert "0 hata, 1 uyari" in sonuc.stdout


def test_yeniden_kontrol_gecmis_uyari(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "bugun", lambda: date(2026, 10, 26))
    kok = kok_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", kok, yeniden_kontrol=date(2026, 10, 25)))
    kayit_yaz(kok, alanlar_kur("test-bugun", kok, yeniden_kontrol=date(2026, 10, 26)))
    sonuc = check(kok)
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "yeniden kontrol tarihi gecti: test-eski" in sonuc.stderr
    assert "test-bugun" not in sonuc.stderr
    assert "0 hata, 1 uyari" in sonuc.stdout


def test_bugun_tarih_dondurur() -> None:
    assert type(cli.bugun()) is date


# --- Gercek depo: kalici sabitleme -------------------------------------------------------

BEKLENEN_SLUGLAR = frozenset(
    {
        "tanzil-uthmani",
        "tanzil-simple-clean",
        "kfgqpc-hafs-font",
        "qpc-v1-font",
        "qpc-v2-font",
        "qpc-v4-font",
        "medine-604-duzen",
        "amiri-quran-font",
        "qac-morfoloji",
        "elmalili-meal",
        "elmalili-tefsir",
        "tefsir-quranpedia",
        "tecrid-ar",
        "tecrid-naim",
        "tecrid-miras",
        "hadis-fawaz-ar",
        "hadis-sunnah-api",
        "risale-1956-1960",
        "risale-asil-nusha",
        "risale-atif-dizini",
        "risale-kelime-frekans",
        "lugat-redhouse-1890",
        "lugat-kamus-i-turki",
        "lugat-naci",
        "ses-everyayah",
        "ses-quranicaudio",
        "ses-qf-api",
        "ses-kfgqpc-meal",
        "quran-align",
        "kaikki-tr",
    }
)
BEKLENEN_KAPALI = frozenset(
    {
        "tecrid-miras",
        "risale-1956-1960",
        "risale-asil-nusha",
        "risale-atif-dizini",
        "ses-everyayah",
        "ses-quranicaudio",
    }
)


def gercek_kayitlar() -> dict[str, sources.Kaynak]:
    sonuclar = sources.yukle(depo_koku(), lisans_dosyalari=True)
    return {s.kaynak.slug: s.kaynak for s in sonuclar if s.kaynak is not None}


def test_gercek_depo_tam_otuz_slug() -> None:
    assert len(BEKLENEN_SLUGLAR) == 30
    assert set(gercek_kayitlar()) == BEKLENEN_SLUGLAR
    assert len(list(sources.kaynak_dizini(depo_koku()).glob("*.toml"))) == 30


def test_gercek_depo_kapali_kume_ve_kopyasizlik() -> None:
    kayitlar = gercek_kayitlar()
    kapali = {s for s, k in kayitlar.items() if k.license_status is LicenseStatus.KAPALI}
    assert kapali == BEKLENEN_KAPALI
    for slug in kapali:
        assert kayitlar[slug].lisans_kopyasi is None, slug
        assert kayitlar[slug].lisans_sha256 is None, slug
        assert kayitlar[slug].embed_ok is False, slug


def test_gercek_depo_kalip_kimlik_dosyasi_yok() -> None:
    adlar = [p.name for p in sources.kaynak_dizini(depo_koku()).glob("*.toml")]
    for onek in ("qul-", "ses-turk-hafiz-", "mushaf-b-"):
        assert not [a for a in adlar if a.startswith(onek)], onek


def test_gercek_depo_quran_foundation_embed_kapali() -> None:
    saglayici = [k for k in gercek_kayitlar().values() if k.provider == "quran_foundation"]
    assert saglayici
    assert all(k.embed_ok is False for k in saglayici)


def test_gercek_depoda_check_sifir_uyari(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "bugun", lambda: date(2026, 10, 26))
    sonuc = runner.invoke(cli.app, ["sources", "check"])
    assert sonuc.exit_code == 0, sonuc.stderr
    assert "30 kayit, 0 hata, 0 uyari" in sonuc.stdout


def _satirlar_duzle(metin: str) -> list[str]:
    return [satir.rstrip(" \t") for satir in metin.split("\n")]


@pytest.mark.parametrize("slug", ["tanzil-uthmani", "tanzil-simple-clean"])
def test_tanzil_notice_text_lisans_kopyasindaki_bildirimle_ayni(slug: str) -> None:
    kayit = gercek_kayitlar()[slug]
    assert kayit.notice_text is not None
    assert kayit.lisans_kopyasi is not None
    kopya = (sources.kaynak_dizini(depo_koku()) / kayit.lisans_kopyasi).read_bytes()
    kopya_satirlari = _satirlar_duzle(kopya.decode("utf-8"))
    bildirim = _satirlar_duzle(kayit.notice_text)
    while bildirim and bildirim[0] == "":
        bildirim.pop(0)
    while bildirim and bildirim[-1] == "":
        bildirim.pop()
    assert bildirim
    bulundu = any(
        kopya_satirlari[i : i + len(bildirim)] == bildirim
        for i in range(len(kopya_satirlari) - len(bildirim) + 1)
    )
    assert bulundu
