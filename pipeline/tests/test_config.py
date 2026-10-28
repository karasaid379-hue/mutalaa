"""`config.Ayarlar`: oncelik sirasi, veri koku, gizli deger, test veritabani adresi (SENTETIK)."""

from pathlib import Path

import pytest
from hat_yardimci import PAROLA, SAHTE_DSN
from psycopg import conninfo

from mutalaa_pipeline.config import (
    PIPELINE_KOK,
    VARSAYILAN_ENV,
    Ayarlar,
    ayarlar_yukle,
)
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku


def toml_yaz(yol: Path, veri_kok: str | None, duzey: str | None = None) -> Path:
    satirlar = ["[genel]"]
    if veri_kok is not None:
        satirlar.append(f'veri_kok = "{veri_kok}"')
    if duzey is not None:
        satirlar.append(f'log_duzeyi = "{duzey}"')
    yol.write_bytes(("\n".join(satirlar) + "\n").encode("utf-8"))
    return yol


def test_env_dosyasi_paketin_konumundan_cozulur() -> None:
    assert Ayarlar.model_config["env_file"] == PIPELINE_KOK / ".env"
    assert VARSAYILAN_ENV == PIPELINE_KOK / ".env"
    assert VARSAYILAN_ENV.is_absolute()
    assert Ayarlar.model_config["env_file_encoding"] == "utf-8"
    assert (PIPELINE_KOK / "mutalaa.toml").is_file()


def test_oncelik_sirasi(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    toml = toml_yaz(tmp_path / "mutalaa.toml", "toml-veri")
    env_dosyasi = tmp_path / "ayar.env"
    env_dosyasi.write_bytes(b"MUTALAA_VERI_KOK=dosya-veri\nANTHROPIC_API_KEY=\nPYTHONUTF8=1\n")

    # 1) yalniz mutalaa.toml
    a = Ayarlar(_env_file=tmp_path / "yok.env", config_dosyasi=toml)
    assert a.veri_kok == (PIPELINE_KOK / "toml-veri").resolve()
    # 2) .env > mutalaa.toml
    a = Ayarlar(_env_file=env_dosyasi, config_dosyasi=toml)
    assert a.veri_kok == (PIPELINE_KOK / "dosya-veri").resolve()
    # 3) ortam > .env
    monkeypatch.setenv("MUTALAA_VERI_KOK", "ortam-veri")
    a = Ayarlar(_env_file=env_dosyasi, config_dosyasi=toml)
    assert a.veri_kok == (PIPELINE_KOK / "ortam-veri").resolve()
    # 4) bayrak > ortam
    a = Ayarlar(_env_file=env_dosyasi, config_dosyasi=toml, veri_kok=tmp_path / "bayrak-veri")
    assert a.veri_kok == (tmp_path / "bayrak-veri").resolve()


def test_log_duzeyi_oncelikleri_ve_dogrulama(tmp_path: Path) -> None:
    toml = toml_yaz(tmp_path / "mutalaa.toml", None, "debug")
    assert Ayarlar(_env_file=None, config_dosyasi=toml).log_duzeyi == "DEBUG"
    assert Ayarlar(_env_file=None, config_dosyasi=toml, log_duzeyi="ERROR").log_duzeyi == "ERROR"
    with pytest.raises(GirdiHatasi) as hata:
        ayarlar_yukle(None, log_duzeyi="GIZLI-DENEME")
    assert "log_duzeyi" in str(hata.value)
    assert "GIZLI-DENEME" not in str(hata.value)


def test_varsayilan_veri_koku_depo_kokunun_data_klasoru(tmp_path: Path) -> None:
    toml = toml_yaz(tmp_path / "mutalaa.toml", None)
    a = Ayarlar(_env_file=None, config_dosyasi=toml)
    assert a.veri_kok == (PIPELINE_KOK.parent / "data").resolve()


@pytest.mark.parametrize("calisma", ["pipeline", "kok", "baska"])
def test_cwd_ne_olursa_olsun_veri_yolu_kok_data(
    calisma: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kok = depo_koku()
    cwd = {"pipeline": kok / "pipeline", "kok": kok, "baska": tmp_path}[calisma]
    monkeypatch.chdir(cwd)
    a = Ayarlar(_env_file=None)  # gercek mutalaa.toml: veri_kok = "../data"
    assert a.veri_kok == (kok / "data").resolve()
    assert a.veri_kok.is_absolute()


def test_config_dosyasi_yoksa_girdi_hatasi(tmp_path: Path) -> None:
    with pytest.raises(GirdiHatasi):
        Ayarlar(_env_file=None, config_dosyasi=tmp_path / "yok.toml")


def test_bozuk_toml_girdi_hatasi_icerik_yazmaz(tmp_path: Path) -> None:
    yol = tmp_path / "bozuk.toml"
    yol.write_bytes(b"[genel\nGIZLI-DENEME = = \n")
    with pytest.raises(GirdiHatasi) as hata:
        Ayarlar(_env_file=None, config_dosyasi=yol)
    assert "GIZLI-DENEME" not in str(hata.value)


def test_db_url_ortamdan_ve_env_dosyasindan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_dosyasi = tmp_path / "ayar.env"
    env_dosyasi.write_bytes(f"MUTALAA_DB_URL={SAHTE_DSN}\n".encode())
    assert Ayarlar(_env_file=env_dosyasi).db_adresi() == SAHTE_DSN
    assert Ayarlar(_env_file=tmp_path / "yok.env").db_url is None
    monkeypatch.setenv("MUTALAA_DB_URL", "postgresql://u:BASKA@h/y")
    assert Ayarlar(_env_file=env_dosyasi).db_adresi() == "postgresql://u:BASKA@h/y"


def test_secretstr_repr_str_ve_dokum_gizli(tmp_path: Path) -> None:
    a = Ayarlar(_env_file=None, db_url=SAHTE_DSN)
    for metin in (repr(a), str(a), repr(a.db_url), str(a.db_url), a.model_dump_json()):
        assert PAROLA not in metin
        assert SAHTE_DSN not in metin
    assert PAROLA not in repr(a.model_dump())


def test_db_adresi_tanimsizsa_girdi_hatasi() -> None:
    with pytest.raises(GirdiHatasi):
        Ayarlar(_env_file=None).db_adresi()
    with pytest.raises(GirdiHatasi):
        Ayarlar(_env_file=None).test_db_adresi()


def test_test_db_adresi_ada_test_ekler() -> None:
    a = Ayarlar(_env_file=None, db_url=SAHTE_DSN)
    test = a.test_db_adresi().get_secret_value()
    ana = conninfo.conninfo_to_dict(SAHTE_DSN)
    turetilen = conninfo.conninfo_to_dict(test)
    assert turetilen["dbname"] == "x_test"
    assert ana["dbname"] == "x"
    for ad in ("user", "password", "host", "port"):
        assert turetilen[ad] == ana[ad]
    assert PAROLA not in repr(a.test_db_adresi())


def test_test_db_adresi_ana_adresle_ayniysa_reddedilir() -> None:
    a = Ayarlar(_env_file=None, db_url="postgresql://u:GIZLI-DENEME@127.0.0.1:1/x_test")
    with pytest.raises(GirdiHatasi) as hata:
        a.test_db_adresi()
    assert PAROLA not in str(hata.value)


def test_test_db_adresi_ayristirilamazsa_iletide_deger_yok() -> None:
    a = Ayarlar(_env_file=None, db_url="postgresql://u:GIZLI-DENEME@127.0.0.1:yanlis/x y=z=")
    with pytest.raises(GirdiHatasi) as hata:
        a.test_db_adresi()
    assert PAROLA not in str(hata.value)
    assert hata.value.__cause__ is None


def test_test_db_adresi_veritabani_adi_yoksa_hata() -> None:
    a = Ayarlar(_env_file=None, db_url="host=127.0.0.1 port=1 user=u password=GIZLI-DENEME")
    with pytest.raises(GirdiHatasi) as hata:
        a.test_db_adresi()
    assert PAROLA not in str(hata.value)


def test_gizli_degerler_parola_ve_adresleri_icerir() -> None:
    gizliler = Ayarlar(_env_file=None, db_url=SAHTE_DSN).gizli_degerler()
    assert SAHTE_DSN in gizliler
    assert PAROLA in gizliler
    assert Ayarlar(_env_file=None).gizli_degerler() == ()
