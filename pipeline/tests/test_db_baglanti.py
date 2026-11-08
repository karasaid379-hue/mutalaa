"""`db.ipv4_tercih`: `localhost` once IPv6 denenip her baglantiyi 10 sn bekletmesin (SENTETIK)."""

import pytest
from psycopg import conninfo

from mutalaa_pipeline.db import ipv4_tercih

ADRES = "postgresql://kullanici:GIZLI-DENEME@{host}:5432/veritabani"


def sozluk(adres: str) -> dict[str, str | None]:
    return {k: v for k, v in conninfo.conninfo_to_dict(adres).items() if isinstance(v, str)}


def test_localhost_ipv4_adresine_baglanir_baska_alan_degismez() -> None:
    adres = ipv4_tercih(ADRES.format(host="localhost"))
    sonuc = sozluk(adres)
    assert sonuc["hostaddr"] == "127.0.0.1"
    assert sonuc["host"] == "localhost"  # ad korunur (hata iletileri ve TLS icin)
    assert (sonuc["user"], sonuc["password"], sonuc["dbname"], sonuc["port"]) == (
        "kullanici",
        "GIZLI-DENEME",
        "veritabani",
        "5432",
    )


@pytest.mark.parametrize("host", ["127.0.0.1", "db.invalid", "::1", "localhost.invalid"])
def test_baska_hostlar_degismez(host: str) -> None:
    adres = ADRES.format(host=f"[{host}]" if ":" in host else host)
    assert ipv4_tercih(adres) == adres


def test_hostaddr_verilmisse_ve_adres_bozuksa_degismez() -> None:
    verilmis = ADRES.format(host="localhost") + "?hostaddr=10.0.0.5"
    assert ipv4_tercih(verilmis) == verilmis
    assert ipv4_tercih("bu bir adres degil =") == "bu bir adres degil ="


def test_buyuk_harfli_localhost_de_taninir() -> None:
    assert sozluk(ipv4_tercih(ADRES.format(host="LOCALHOST")))["hostaddr"] == "127.0.0.1"
