"""Vektor dosyasi envanteri ve `unit_search` sutun uyumu (A12.6).

* Bilinen dosyalar: `shared/test-vectors` altindaki her `.jsonl` dosyasi ya bir Python kosucusunun
  yukledigi listede (`vektor_dosyalari.KOSULAN`) ya da gerekceli atlama listesinde olmali; yeni
  bir dosya listeye yazilmadan eklenirse test kirilir (sessizce kosulmayan vektor olmaz).
* `unit_search` uyumu: `packages/content-schema/sql/20-arama.sql` icindeki sutunlar hattin urettigi
  arama anahtarlariyla (`SearchKeys`) eslesir. DDL bu testte okunur, degistirilmez.
"""

import re
from pathlib import Path

import vektor_dosyalari as vd

from mutalaa_pipeline.normalize import SearchKeys

DDL_YOLU = vd.depo_koku() / "packages" / "content-schema" / "sql" / "20-arama.sql"
_TABLO: re.Pattern[str] = re.compile(
    r"CREATE\s+TABLE\s+unit_search\s*\((?P<govde>[^;]*?)\)\s*;", re.IGNORECASE
)
_SUTUN_ADI: re.Pattern[str] = re.compile(r"[a-z_][a-z_0-9]*")


def vektor_dosyalarini_tara(kok: Path) -> list[str]:
    """`kok` altindaki `.jsonl` dosyalari (goreli, `/` ayiricili, sirali); tarama disi atlanir."""
    bulunan: list[str] = []
    for yol in kok.rglob("*.jsonl"):
        goreli = yol.relative_to(kok)
        if any(parca in vd.TARAMA_DISI for parca in goreli.parts[:-1]):
            continue
        bulunan.append(goreli.as_posix())
    return sorted(bulunan)


def bilinmeyenler(dosyalar: list[str]) -> list[str]:
    """Ne kosucu listesinde ne atlama listesinde ne atlanan klasorde olan dosyalar."""
    return [
        d
        for d in dosyalar
        if d not in vd.KOSULAN_DOSYALAR
        and d not in vd.ATLANAN
        and not any(d.startswith(onek) for onek in vd.ATLANAN_KLASORLER)
    ]


def test_her_vektor_dosyasi_kosulan_ya_da_acikca_atlanan() -> None:
    dosyalar = vektor_dosyalarini_tara(vd.VEKTOR_KOKU)
    assert dosyalar, "shared/test-vectors altinda .jsonl bulunamadi"
    assert bilinmeyenler(dosyalar) == [], (
        "Python kosucusu ya da acik atlama gerekcesi olmayan vektor dosyasi:"
        " tests/vektor_dosyalari.py KOSULAN ya da ATLANAN listesine yaz"
    )


def test_listelerdeki_her_dosya_vardir() -> None:
    """Silinmis ya da yeniden adlandirilmis dosya listede eskimis girdi birakmaz."""
    dosyalar = set(vektor_dosyalarini_tara(vd.VEKTOR_KOKU))
    for dosya in (*vd.KOSULAN_DOSYALAR, *vd.ATLANAN):
        assert dosya in dosyalar, f"listede olan dosya yok: {dosya}"


def test_kosulan_ve_atlanan_kesismez() -> None:
    assert not vd.KOSULAN_DOSYALAR & set(vd.ATLANAN)
    assert all(gerekce for gerekce in (*vd.ATLANAN.values(), *vd.ATLANAN_KLASORLER.values()))


def test_yeni_bilinmeyen_dosya_testi_kirar(tmp_path: Path) -> None:
    (tmp_path / "anchors").mkdir()
    (tmp_path / "anchors" / "valid.jsonl").write_bytes(b"{}\n")
    (tmp_path / "fts-query").mkdir()
    (tmp_path / "fts-query" / "query.jsonl").write_bytes(b"{}\n")
    (tmp_path / "arama").mkdir()
    (tmp_path / "arama" / "olcum.jsonl").write_bytes(b"{}\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.jsonl").write_bytes(b"{}\n")
    assert bilinmeyenler(vektor_dosyalarini_tara(tmp_path)) == []

    (tmp_path / "normalize").mkdir()
    (tmp_path / "normalize" / "yeni.jsonl").write_bytes(b"{}\n")
    (tmp_path / "ek.jsonl").write_bytes(b"{}\n")
    assert bilinmeyenler(vektor_dosyalarini_tara(tmp_path)) == ["ek.jsonl", "normalize/yeni.jsonl"]


def test_kosucu_testleri_ortak_listeyi_kullanir() -> None:
    testler = Path(__file__).resolve().parent
    for kosucu, dosyalar in vd.KOSULAN.items():
        kaynak = (testler / kosucu).read_text(encoding="utf-8")
        assert "vektor_dosyalari" in kaynak, f"{kosucu} ortak listeyi kullanmiyor"
        assert dosyalar


# --- unit_search sutun uyumu -----------------------------------------------------------------


def unit_search_sutunlari(sql: str) -> list[str]:
    """`CREATE TABLE unit_search (...)` sutun adlari, yazim sirasiyla."""
    eslesme = _TABLO.search(re.sub(r"--[^\n]*", "", sql))
    assert eslesme is not None, "CREATE TABLE unit_search bulunamadi"
    sutunlar: list[str] = []
    for parca in eslesme.group("govde").split(","):
        ad = _SUTUN_ADI.match(parca.strip())
        assert ad is not None, f"sutun adi okunamadi: {parca.strip()!r}"
        sutunlar.append(ad.group(0))
    return sutunlar


def test_unit_search_sutunlari_search_keys_ile_eslesir() -> None:
    sql = DDL_YOLU.read_bytes().decode("utf-8")
    sutunlar = unit_search_sutunlari(sql)
    assert sutunlar[0] == "rowid"
    arama = sutunlar[1:]
    assert len(arama) == len(set(arama))
    # tr_narrow pakete girmez (yalniz PostgreSQL `unit` tablosunda ve dar suzgecte kullanilir).
    beklenen = set(SearchKeys._fields) - {"tr_narrow"}
    assert beklenen == {"tr_wide", "tr_stem", "ar_norm"}
    assert set(arama) == beklenen


def test_unit_search_ayristirici_ornekleri() -> None:
    sql = "-- aciklama\nCREATE TABLE unit_search (rowid INTEGER PRIMARY KEY, a TEXT, b2 TEXT);"
    assert unit_search_sutunlari(sql) == ["rowid", "a", "b2"]
