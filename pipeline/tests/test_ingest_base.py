"""`ingest.base`: `run_ingest`, `staged` yazimi, atlama, kaynak kaydi (SENTETIK "Deneme" metni)."""

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from hat_yardimci import ctx_kur, depo_kur
from test_sources import alanlar_kur, kayit_yaz

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.ingest.base import RawFile, StagedUnit, run_ingest
from mutalaa_pipeline.runctx import RunContext

KAYNAK = "test-kaynak"
HAM = b"Deneme satiri 2\nDeneme satiri 1\n"


class SahteBagdastirici:
    """`SourceAdapter` uygulamasi; ham dosya tmp altinda, metin sentetik."""

    def __init__(self, source_id: str = KAYNAK, anchors: tuple[str, ...] = ("q:1:2", "q:1:1")):
        self.source_id = source_id
        self.anchors = anchors
        self.fetch_sayisi = 0
        self.parse_sayisi = 0
        self.parse_hatasi = False

    def fetch(self, ctx: RunContext) -> list[RawFile]:
        self.fetch_sayisi += 1
        yol = ctx.raw_dizin(self.source_id) / "2026-10-28" / "deneme.txt"
        yol.parent.mkdir(parents=True, exist_ok=True)
        yol.write_bytes(HAM)
        return [RawFile(yol, hashlib.sha256(HAM).hexdigest(), None)]

    def parse(self, ctx: RunContext, files: list[RawFile]) -> Iterator[StagedUnit]:
        self.parse_sayisi += 1
        satirlar = HAM.split(b"\n")
        for sira, capa in enumerate(self.anchors):
            yield StagedUnit(
                anchor=capa,
                text=satirlar[sira].decode("utf-8"),
                attrs={"sira": sira},
                provenance={"file": "deneme.txt", "line": sira + 1, "steps": []},
            )
            if self.parse_hatasi and sira == 0:
                raise GirdiHatasi("parse yarida kesildi")
        if not ctx.dry_run:  # bagdastirici da dry-run kuralina uyar
            ctx.staged_dizin(self.source_id).mkdir(parents=True, exist_ok=True)
            (ctx.staged_dizin(self.source_id) / "notice.txt").write_bytes(b"Deneme bildirimi\n")


def kur(tmp_path: Path, **kw: object) -> tuple[Path, RunContext]:
    kok = depo_kur(tmp_path, KAYNAK)
    return kok, ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True, **kw)


def test_run_ingest_staged_siralidir_ve_manifest_en_son(tmp_path: Path) -> None:
    _, ctx = kur(tmp_path)
    sonuc = run_ingest(SahteBagdastirici(), ctx)
    assert sonuc.atlandi is False
    assert sonuc.birim_sayisi == 2
    assert sonuc.klasor == tmp_path / "data" / "staged" / KAYNAK / ctx.run_id
    satirlar = (sonuc.klasor / "units.jsonl").read_bytes().split(b"\n")
    assert satirlar[-1] == b""
    birimler = [json.loads(s) for s in satirlar[:-1]]
    assert [b["anchor"] for b in birimler] == ["q:1:1", "q:1:2"]  # capaya gore sirali
    assert birimler[0]["text"] == "Deneme satiri 1"
    assert birimler[0]["source_id"] == KAYNAK
    assert set(birimler[0]) == {"anchor", "source_id", "text", "attrs", "provenance"}
    manifest = json.loads((sonuc.klasor / "manifest.json").read_bytes())
    yollar = [c["yol"] for c in manifest["ciktilar"]]
    assert yollar == [
        f"staged/{KAYNAK}/{ctx.run_id}/notice.txt",
        f"staged/{KAYNAK}/{ctx.run_id}/units.jsonl",
    ]
    units = next(c for c in manifest["ciktilar"] if c["yol"].endswith("units.jsonl"))
    assert units["satir"] == 2
    assert (
        units["sha256"] == hashlib.sha256((sonuc.klasor / "units.jsonl").read_bytes()).hexdigest()
    )
    assert manifest["girdiler"][0]["yol"] == f"raw/{KAYNAK}/2026-10-28/deneme.txt"
    assert "lisans_kopyasi" not in manifest  # K-42: manifest lisans kopyasi tasimaz
    assert manifest["llm"] is None
    assert lineage.ciktilar_saglam(tmp_path / "data", manifest)


def test_units_zaman_damgasi_icermez_ve_ascii_kacislidir(tmp_path: Path) -> None:
    _, ctx = kur(tmp_path)
    ad = SahteBagdastirici()
    ad_parse = ad.parse

    def parse(c: RunContext, f: list[RawFile]) -> Iterator[StagedUnit]:
        for b in ad_parse(c, f):
            yield StagedUnit(b.anchor, "Deneme ḉ", b.attrs, b.provenance)

    ad.parse = parse  # type: ignore[method-assign]
    sonuc = run_ingest(ad, ctx)
    assert sonuc.klasor is not None
    ham = (sonuc.klasor / "units.jsonl").read_bytes()
    assert ham.isascii()
    assert b"run_id" not in ham
    assert json.loads(ham.split(b"\n")[0])["text"] == "Deneme ḉ"  # NFC uygulanmaz


def test_ayni_girdi_ayni_staged_ozeti(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ozetler = []
    for _ in range(2):
        ctx = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True, force=True)
        sonuc = run_ingest(SahteBagdastirici(), ctx)
        assert sonuc.klasor is not None
        ozetler.append(hashlib.sha256((sonuc.klasor / "units.jsonl").read_bytes()).hexdigest())
    assert ozetler[0] == ozetler[1]


def test_ikinci_kosu_atlanir_force_ve_kirli_agac_atlamaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ad = SahteBagdastirici()

    def kos(**kw: object) -> bool:
        ctx = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], **kw)
        return run_ingest(ad, ctx).atlandi

    assert kos(temiz_git=True) is False
    parse_sonra_ilk = ad.parse_sayisi
    assert kos(temiz_git=True) is True  # parmak izi ayni
    assert ad.parse_sayisi == parse_sonra_ilk  # parse calismadi
    assert kos(temiz_git=True, force=True) is False  # --force
    assert kos(temiz_git=False) is False  # kirli agac (tmp deposu git degil)
    # kirli calistirmanin manifesti onceki sayilmaz; ayni parmak izi olsa bile atlanmaz
    assert kos(temiz_git=True) is False
    assert kos(temiz_git=True) is True


def test_parametre_degisirse_atlanmaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ad = SahteBagdastirici()
    ilk = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True, parametreler={"variant": "a"})
    assert run_ingest(ad, ilk).atlandi is False
    ikinci = ctx_kur(
        tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True, parametreler={"variant": "b"}
    )
    assert run_ingest(ad, ikinci).atlandi is False


def test_cikti_bozulmussa_atlanmaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ad = SahteBagdastirici()
    ilk = run_ingest(ad, ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True))
    assert ilk.klasor is not None
    (ilk.klasor / "units.jsonl").write_bytes(b"bozuk\n")
    assert (
        run_ingest(ad, ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True)).atlandi is False
    )


def test_gecersiz_kayitli_kaynakta_fetch_calismaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-atifsiz", atif_metni=None))
    ctx = ctx_kur(tmp_path, kok, kaynaklar=["test-atifsiz"])
    ad = SahteBagdastirici("test-atifsiz")
    with pytest.raises(GirdiHatasi) as hata:
        run_ingest(ad, ctx)
    assert "gecersiz" in str(hata.value)
    assert ad.fetch_sayisi == 0
    assert not (tmp_path / "data" / "raw").exists()
    assert not (tmp_path / "data" / "staged").exists()


def test_eski_lisans_alanli_kayitta_fetch_calismaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path)
    kayit_yaz(kok, alanlar_kur("test-eski", embed_ok=True))
    ad = SahteBagdastirici("test-eski")
    with pytest.raises(GirdiHatasi):
        run_ingest(ad, ctx_kur(tmp_path, kok, kaynaklar=["test-eski"]))
    assert ad.fetch_sayisi == 0


def test_kayitsiz_kaynakta_fetch_calismaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ad = SahteBagdastirici("test-yok")
    with pytest.raises(GirdiHatasi) as hata:
        run_ingest(ad, ctx_kur(tmp_path, kok, kaynaklar=["test-yok"]))
    assert "kayitsiz" in str(hata.value)
    assert ad.fetch_sayisi == 0


def test_parse_yarida_kesilirse_manifest_olmaz_ve_klasor_yok_sayilir(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ad = SahteBagdastirici()
    ad.parse_hatasi = True
    ctx = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True)
    with pytest.raises(GirdiHatasi):
        run_ingest(ad, ctx)
    kaynak_klasoru = tmp_path / "data" / "staged" / KAYNAK
    assert not (kaynak_klasoru / ctx.run_id / "manifest.json").exists()
    assert lineage.son_basarili(kaynak_klasoru) is None


def test_dry_run_staged_ve_manifest_yazmaz(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ctx = ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK], temiz_git=True, dry_run=True)
    sonuc = run_ingest(SahteBagdastirici(), ctx)
    assert sonuc.birim_sayisi == 2
    assert sonuc.klasor is None
    assert not (tmp_path / "data" / "staged").exists()


def test_yinelenen_ve_gecersiz_capa(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    with pytest.raises(GirdiHatasi) as yinelenen:
        run_ingest(
            SahteBagdastirici(anchors=("q:1:1", "q:1:1")),
            ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK]),
        )
    assert "q:1:1" in str(yinelenen.value)
    with pytest.raises(GirdiHatasi) as gecersiz:
        run_ingest(
            SahteBagdastirici(anchors=("Q:1:1", "q:1:2")),
            ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK]),
        )
    assert "Q:1:1" not in str(gecersiz.value)


def test_ham_dosya_ozeti_tutmuyorsa_durur(tmp_path: Path) -> None:
    kok = depo_kur(tmp_path, KAYNAK)
    ad = SahteBagdastirici()
    fetch = ad.fetch

    def kotu_fetch(ctx: RunContext) -> list[RawFile]:
        dosya = fetch(ctx)[0]
        return [RawFile(dosya.path, "0" * 64, None)]

    ad.fetch = kotu_fetch  # type: ignore[method-assign]
    with pytest.raises(GirdiHatasi):
        run_ingest(ad, ctx_kur(tmp_path, kok, kaynaklar=[KAYNAK]))
