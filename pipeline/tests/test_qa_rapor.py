"""`qa.rapor`: `qa run` raporlarindan kabul karari (SENTETIK raporlar; zincir ve veritabani yok).

Bir anchor calismasinin kabulu o calismaya ait raporlarin EN YENISINDEN okunur: tam ve gecen rapor
kabul eder; kapisi kalan ya da tamamlanamayan sonraki kosu eski bir `gecti` raporunu gecersiz
kilar; basarili bir kismi (`--gate`) kosu karari degistirmez.
"""

import json
from pathlib import Path

import pytest

from mutalaa_pipeline.qa import KAPILAR
from mutalaa_pipeline.qa.rapor import QaRaporlari
from mutalaa_pipeline.runctx import QaKaldi, Uuid7Uretici

KAYNAK = "test-kaynak"
ANCHOR = "01a1a103-0cb8-7798-b9c2-59126655b631"
OZET = "a" * 64
TUM_GECTI = dict.fromkeys(KAPILAR, "gecti")


class Depo:
    """`<veri_kok>/reports` altina zaman sirasinda rapor yazar (dosya adi UUIDv7)."""

    def __init__(self, veri_kok: Path) -> None:
        self.veri_kok = veri_kok
        self.uretici = Uuid7Uretici()

    def yaz(self, **alanlar: object) -> str:
        """Varsayilan: gecen tam rapor. `None` verilen alan rapordan cikar."""
        rapor: dict[str, object] = {
            "komut": "qa run",
            "kaynak": KAYNAK,
            "anchor_run_id": ANCHOR,
            "units_sha256": OZET,
            "cikis_kodu": 0,
            "kapilar": TUM_GECTI,
        }
        rapor.update(alanlar)
        return self._yaz(json.dumps({k: v for k, v in rapor.items() if v is not None}))

    def _yaz(self, metin: str, uzanti: str = "json") -> str:
        rapor_id = str(self.uretici.uret())
        klasor = self.veri_kok / "reports"
        klasor.mkdir(parents=True, exist_ok=True)
        (klasor / f"{rapor_id}.{uzanti}").write_text(metin, encoding="utf-8", newline="\n")
        return rapor_id

    def onayla(self) -> str:
        return QaRaporlari(self.veri_kok).onayla(KAYNAK, ANCHOR, OZET)

    def onayli_mi(self) -> bool:
        return QaRaporlari(self.veri_kok).onayli_mi(KAYNAK, ANCHOR, OZET)


@pytest.fixture
def depo(tmp_path: Path) -> Depo:
    return Depo(tmp_path)


def test_rapor_klasoru_yoksa_rapor_yok(depo: Depo) -> None:
    with pytest.raises(QaKaldi, match="QA raporu yok"):
        depo.onayla()
    assert depo.onayli_mi() is False


def test_baska_kaynak_anchor_ya_da_ozet_sayilmaz(depo: Depo) -> None:
    depo.yaz(kaynak="test-baska")
    depo.yaz(anchor_run_id="01a1a103-0cb8-7798-b9c2-59126655b632")
    depo.yaz(units_sha256="b" * 64)
    depo.yaz(komut="export pg")
    with pytest.raises(QaKaldi, match="QA raporu yok"):
        depo.onayla()


def test_gecen_tam_rapor_kabul_eder(depo: Depo) -> None:
    rapor_id = depo.yaz()
    assert depo.onayla() == rapor_id
    assert depo.onayli_mi() is True


def test_cikis_kodu_yazilmamis_elle_rapor_da_kabul_eder(depo: Depo) -> None:
    rapor_id = depo.yaz(cikis_kodu=None)
    assert depo.onayla() == rapor_id


@pytest.mark.parametrize("deger", ['"0"', "0.0", "true", "null", "[]"])
def test_cikis_kodu_int_degilse_tamamlandi_sayilmaz(depo: Depo, deger: str) -> None:
    """Alan varsa int 0 olmali: bicimsiz deger eski `gecti` raporunu gecersiz kilar."""
    eski = depo.yaz()
    assert depo.onayla() == eski
    depo._yaz(
        json.dumps({"komut": "qa run", "kaynak": KAYNAK, "anchor_run_id": ANCHOR})[:-1]
        + f', "units_sha256": "{OZET}", "cikis_kodu": {deger}}}'
    )
    with pytest.raises(QaKaldi, match="son QA kosusu tamamlanmadi"):
        depo.onayla()
    assert depo.onayli_mi() is False


def test_en_yeni_rapor_karar_verir_yeni_gecen_eski_kalani_ortmez(depo: Depo) -> None:
    depo.yaz(kapilar={**TUM_GECTI, "G-CAP": "kaldi"}, cikis_kodu=1)
    yeni = depo.yaz()
    assert depo.onayla() == yeni


def test_sonraki_kalan_tam_kosu_eski_gecen_raporu_gecersiz_kilar(depo: Depo) -> None:
    depo.yaz()
    depo.yaz(kapilar={**TUM_GECTI, "G-CAP": "kaldi"}, cikis_kodu=1)
    with pytest.raises(QaKaldi, match="QA kapisi gecmedi: G-CAP"):
        depo.onayla()
    assert depo.onayli_mi() is False


def test_basarili_kismi_kosu_karari_degistirmez(depo: Depo) -> None:
    tam = depo.yaz()
    depo.yaz(kapilar={"G-CAP": "gecti"})
    depo.yaz(kapilar={"G-KAY": "gecti", "G-NOR": "gecti"})
    assert depo.onayla() == tam


def test_sonraki_kalan_kismi_kosu_eski_gecen_raporu_gecersiz_kilar(depo: Depo) -> None:
    depo.yaz()
    depo.yaz(kapilar={"G-KAY": "kaldi"}, cikis_kodu=1)
    with pytest.raises(QaKaldi, match="QA kapisi gecmedi: G-KAY"):
        depo.onayla()


def test_sonraki_tamamlanamayan_kosu_eski_gecen_raporu_gecersiz_kilar(depo: Depo) -> None:
    """Zincir ya da girdi hatasiyla biten kosu kapi iddia etmez (`kapilar` yok), cikis kodu 2."""
    depo.yaz()
    depo.yaz(kapilar=None, cikis_kodu=2)
    with pytest.raises(QaKaldi, match=r"son QA kosusu tamamlanmadi \(cikis 2\)"):
        depo.onayla()


def test_kapilari_gecen_ama_cikis_kodu_sifir_olmayan_rapor_kabul_etmez(depo: Depo) -> None:
    """Kapilar hesaplandiktan sonra kosu cokmus olabilir: tam gorunen rapor yine de kabul degil."""
    depo.yaz(cikis_kodu=2)
    with pytest.raises(QaKaldi, match="son QA kosusu tamamlanmadi"):
        depo.onayla()


def test_basarili_kismi_kosu_cikis_kodu_sifir_degilse_gecersiz_kilar(depo: Depo) -> None:
    depo.yaz()
    depo.yaz(kapilar={"G-CAP": "gecti"}, cikis_kodu=2)
    with pytest.raises(QaKaldi, match="son QA kosusu tamamlanmadi"):
        depo.onayla()


def test_yalniz_kismi_rapor_dort_kapiyi_icermiyor(depo: Depo) -> None:
    depo.yaz(kapilar={"G-CAP": "gecti"})
    with pytest.raises(QaKaldi, match="dort kapiyi da icermiyor"):
        depo.onayla()


def test_eski_kapi_adli_rapor_dort_kapiyi_icermiyor(depo: Depo) -> None:
    depo.yaz(kapilar=dict.fromkeys(("G-LIS", "G-BUT", "G-CAP", "G-NOR"), "gecti"))
    with pytest.raises(QaKaldi, match="dort kapiyi da icermiyor"):
        depo.onayla()


def test_kapi_iddia_etmeyen_sifir_kodlu_rapor_yok_sayilir(depo: Depo) -> None:
    tam = depo.yaz()
    depo.yaz(kapilar=None, cikis_kodu=0)
    assert depo.onayla() == tam


def test_bozuk_ve_yabanci_dosyalar_yok_sayilir(depo: Depo) -> None:
    tam = depo.yaz()
    depo._yaz("{bozuk json")
    depo._yaz('["liste", "nesne degil"]')
    depo._yaz(json.dumps({"komut": "export pg", "kaynak": KAYNAK}))
    depo._yaz("{}", uzanti="json.tmp")  # yarim yazilmis gecici dosya
    assert depo.onayla() == tam


def test_rapor_klasorundeki_ascii_disi_bayt_hata_vermez(depo: Depo) -> None:
    tam = depo.yaz()
    klasor = depo.veri_kok / "reports"
    (klasor / f"{depo.uretici.uret()}.json").write_bytes(b"\xff\xfe{}")
    assert depo.onayla() == tam
