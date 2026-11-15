"""`enrich/tr_roots/ozellik.py`: kanit ozellik havuzu (politika surumu 3; SENTETIK kanit)."""

from mutalaa_pipeline.enrich.tr_roots.ozellik import OZELLIK_ADLARI, ozellikler


def _kanit(
    alanlar: list[str], eslesme: str = "kok_harfleri", ar: str | None = None
) -> dict[str, object]:
    return {
        "kaynaklar": [
            {"source_id": "kaikki-tr", "surum": "1", "madde": "m", "alan": a, "deger": "d"}
            for a in alanlar
        ],
        "qac": {"eslesme": eslesme, "ar_lemma_qac_ref": ar},
    }


def test_havuz_yedi_ozellik_ve_hepsi_dolu() -> None:
    oz = ozellikler(_kanit(["tr:noun:etymology_templates.root"]))
    assert tuple(oz) == OZELLIK_ADLARI and len(OZELLIK_ADLARI) == 7
    assert oz == {
        "kaikki_dilleri": "tr",
        "kok_sablonu": "var",
        "sablon_ailesi": "root",
        "qac_eslesme": "kok_harfleri",
        "kaikki_pos": "noun",
        "kaynak_sayisi": "1",
        "ar_lemma": "yok",
    }


def test_dil_pos_aile_ve_kaynak_sayisi_bandi() -> None:
    oz = ozellikler(
        _kanit(
            [
                "tr:noun:etymology_templates.bor",
                "tr:noun:etymology_templates.lbor",
                "ota:adj:etymology_templates.inh+",
                "ota:adj:etymology_templates.etymon",
            ],
            eslesme="ikisi",
            ar="qac-ref",
        )
    )
    assert oz["kaikki_dilleri"] == "ota+tr" and oz["kaikki_pos"] == "adj+noun"
    assert oz["sablon_ailesi"] == "agac+bor+soy" and oz["kok_sablonu"] == "yok"
    assert oz["kaynak_sayisi"] == "4+" and oz["qac_eslesme"] == "ikisi" and oz["ar_lemma"] == "var"
    assert ozellikler(_kanit(["tr:noun:etymology_templates.ety"] * 2))["kaynak_sayisi"] == "2-3"


def test_bozuk_ya_da_bos_kanit_sessizce_yok_degeri_verir() -> None:
    oz = ozellikler({})
    assert oz["kaikki_dilleri"] == "yok" and oz["kaikki_pos"] == "yok"
    assert oz["qac_eslesme"] == "bilinmiyor" and oz["kaynak_sayisi"] == "1"
    assert (
        ozellikler({"kaynaklar": [{"alan": 3}, "x", {"alan": "bozuk"}], "qac": 5})["kaikki_dilleri"]
        == "yok"
    )
