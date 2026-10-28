"""Hat yapilandirmasi (Icerik hatti §3): pydantic-settings, oncelik bayrak > ortam > .env > toml.

Gizli deger (`MUTALAA_DB_URL`) `SecretStr` ile tutulur; `repr` ve `str` onu gostermez. Hata
iletilerine baglanti dizesi ya da girdi degeri yazilmaz: yalniz alan adi.
"""

import tomllib
from pathlib import Path
from typing import Any, Final

import psycopg
from psycopg import conninfo
from pydantic import SecretStr, ValidationError, field_validator
from pydantic.fields import FieldInfo
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from mutalaa_pipeline.export.ortak import GirdiHatasi

# src/mutalaa_pipeline/config.py -> pipeline/
PIPELINE_KOK: Final = Path(__file__).resolve().parents[2]
VARSAYILAN_TOML: Final = PIPELINE_KOK / "mutalaa.toml"
VARSAYILAN_ENV: Final = PIPELINE_KOK / ".env"
VARSAYILAN_VERI_KOK: Final = "../data"
TEST_EKI: Final = "_test"
TOML_BOLUMU: Final = "genel"
TOML_ALANLARI: Final = ("veri_kok", "log_duzeyi")
LOG_DUZEYLERI: Final = frozenset({"DEBUG", "INFO", "WARNING", "ERROR"})


class _TomlKaynagi(PydanticBaseSettingsSource):
    """`mutalaa.toml` `[genel]` bolumunu okur; en dusuk oncelikli kaynak."""

    def __init__(self, settings_cls: type[BaseSettings], yol: Path | None) -> None:
        super().__init__(settings_cls)
        self._yol = yol

    def get_field_value(self, field: FieldInfo, field_name: str) -> tuple[Any, str, bool]:
        return None, field_name, False

    def __call__(self) -> dict[str, Any]:
        acik = self._yol is not None
        yol = self._yol if self._yol is not None else VARSAYILAN_TOML
        if not yol.is_file():
            if acik:
                raise GirdiHatasi("--config dosyasi yok")
            return {}
        try:
            veri = tomllib.loads(yol.read_bytes().decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as hata:
            raise GirdiHatasi("mutalaa.toml okunamadi (UTF-8 TOML degil)") from hata
        genel = veri.get(TOML_BOLUMU, {})
        if not isinstance(genel, dict):
            raise GirdiHatasi(f"mutalaa.toml: [{TOML_BOLUMU}] bir tablo olmali")
        return {ad: genel[ad] for ad in TOML_ALANLARI if ad in genel}


class Ayarlar(BaseSettings):
    """Hat ayarlari. `veri_kok` goreli verilirse `pipeline/` klasorune gore cozulur."""

    model_config = SettingsConfigDict(
        env_file=VARSAYILAN_ENV,
        env_file_encoding="utf-8",
        env_prefix="MUTALAA_",
        extra="ignore",
        validate_default=True,
    )

    db_url: SecretStr | None = None
    veri_kok: Path = Path(VARSAYILAN_VERI_KOK)
    log_duzeyi: str = "INFO"
    # `--config` bayragi icindir; toml kaynagi yalniz bayrak (init) degerine bakar.
    config_dosyasi: Path | None = None

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        bayrak = getattr(init_settings, "init_kwargs", {}).get("config_dosyasi")
        toml = _TomlKaynagi(settings_cls, Path(bayrak) if bayrak is not None else None)
        return (init_settings, env_settings, dotenv_settings, toml)

    @field_validator("veri_kok", mode="after")
    @classmethod
    def _veri_kok_coz(cls, deger: Path) -> Path:
        yol = deger if deger.is_absolute() else PIPELINE_KOK / deger
        return yol.resolve()

    @field_validator("log_duzeyi", mode="after")
    @classmethod
    def _log_duzeyi_denetle(cls, deger: str) -> str:
        buyuk = deger.upper() if deger.isascii() else ""
        if buyuk not in LOG_DUZEYLERI:
            raise ValueError("log_duzeyi DEBUG, INFO, WARNING ya da ERROR olmali")
        return buyuk

    @property
    def config_yolu(self) -> Path:
        """Kullanilan `mutalaa.toml` yolu (`config_sha256` bu dosyanin baytlarindandir)."""
        return self.config_dosyasi if self.config_dosyasi is not None else VARSAYILAN_TOML

    def db_adresi(self) -> str:
        """Ana veritabani adresi; tanimsizsa girdi hatasi (deger iletide yer almaz)."""
        if self.db_url is None:
            raise GirdiHatasi("MUTALAA_DB_URL tanimli degil")
        return self.db_url.get_secret_value()

    def gizli_degerler(self) -> tuple[str, ...]:
        """Gunluge, rapora ve iletilere yazilmamasi gereken degerler (maskeleme icin)."""
        if self.db_url is None:
            return ()
        ana = self.db_url.get_secret_value()
        degerler = [ana]
        try:
            parola = conninfo.conninfo_to_dict(ana).get("password")
            if isinstance(parola, str) and parola:
                degerler.append(parola)
            degerler.append(self.test_db_adresi().get_secret_value())
        except (psycopg.Error, GirdiHatasi):
            pass
        return tuple(dict.fromkeys(degerler))

    def test_db_adresi(self) -> SecretStr:
        """Ana adresten turetilen test veritabani adresi (veritabani adina `_test` eklenir).

        Ad zaten `_test` ile bitiyorsa turetilen adres ana adresle aynidir ve reddedilir.
        """
        ana = self.db_adresi()
        try:
            parcalar = conninfo.conninfo_to_dict(ana)
        except psycopg.Error:
            raise GirdiHatasi("MUTALAA_DB_URL ayristirilamadi") from None
        ad = parcalar.get("dbname")
        if not isinstance(ad, str) or ad == "":
            raise GirdiHatasi("MUTALAA_DB_URL veritabani adi icermiyor")
        if ad.endswith(TEST_EKI):
            raise GirdiHatasi(
                "test veritabani adresi ana adresle ayni (ad zaten _test ile bitiyor)"
            )
        return SecretStr(conninfo.make_conninfo(ana, dbname=ad + TEST_EKI))


def ayarlar_yukle(config: Path | None = None, **bayraklar: object) -> Ayarlar:
    """Ayarlari yukler; dogrulama hatasi yalniz alan adlariyla `GirdiHatasi` olur.

    `bayraklar` komut satiri bayraklaridir (en yuksek oncelik); `None` degerler atlanir.
    """
    degerler = {ad: deger for ad, deger in bayraklar.items() if deger is not None}
    if config is not None:
        degerler["config_dosyasi"] = config
    try:
        return Ayarlar(**degerler)  # type: ignore[arg-type]
    except ValidationError as hata:
        alanlar = ", ".join(sorted({str(e["loc"][0]) for e in hata.errors() if e["loc"]}))
        raise GirdiHatasi(f"yapilandirma gecersiz: {alanlar}") from None
