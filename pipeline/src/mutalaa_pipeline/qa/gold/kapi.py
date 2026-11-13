"""Kapi raporu, onceki kabul edilmis kosu ve `icerik.xref_gate` yazimi (A18.5, K-51 madde 5 ve 11).

Rapor `data/reports/{data_version}-gold-{tur}.json`: tur, set surumu, sinif, ornek sayisi, olculer,
esik, sonuc, referans kapsam notlari, kaynaklar, `rapor_sha256`. Icerik metni YOKTUR (yalniz sayi,
capa, kimlik ve kaynak adi). `data_version = gold1-{set surumu}-{tahmin ozeti ilk 8 hane}`:
tahmin ozeti, olculen uretimin ciktisinin (veritabani ya da motor) ozetidir; uretim degisince yeni
rapor dosyasi acilir, onceki kabul edilmis rapor ezilmez.

`rapor_sha256`: raporun kendi alani HARIC kanonik JSON'unun (`logs.json_baytlari`) SHA-256 degeri;
`xref_gate.rapor_sha256` ayni degerdir. Dogrulama: dosyayi oku, `rapor_sha256` anahtarini at,
yeniden serilestir ve ozeti al.

ONCEKI KABUL EDILMIS KOSU: ayni `tur` icin `sonuc = gecti` olan en son rapor (`olculdu_utc`);
gerileme kurali yalniz bununla karsilastirir. `kaldi` raporlar ve `--dry-run` (rapor yazmaz)
referans olmaz.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

import psycopg

from mutalaa_pipeline import lineage
from mutalaa_pipeline.export.ortak import GirdiHatasi
from mutalaa_pipeline.logs import json_baytlari, zaman_metni
from mutalaa_pipeline.qa.gold.olcum import GECTI, KALDI
from mutalaa_pipeline.runctx import RAPOR_KLASORU

VERSIYON: Final = "gold1"
GATE_TURLERI: Final = ("kok", "lemma", "benzer_ayet", "atif", "iktibas")
CLI_TURLERI: Final = ("kok", "lemma", "benzer-ayet", "atif", "iktibas")
RAPOR_SURUMU: Final = 1


@dataclass
class TurSonucu:
    """Bir turun olcum sonucu (rapor ve `xref_gate` satiri bundan kurulur)."""

    cli_tur: str  # kok | lemma | benzer-ayet | atif | iktibas
    manifest: Mapping[str, object]
    sonuc: str  # gecti | kaldi
    olculer: dict[str, float]
    esikler: dict[str, float]
    esik_sonuclari: dict[str, bool]
    tahmin_ozeti: str
    olculen_ornek: int
    ayrintilar: dict[str, object] = field(default_factory=dict)
    notlar: list[str] = field(default_factory=list)
    referans_kapsami: dict[str, object] = field(default_factory=dict)
    alt_sonuclar: dict[str, str] = field(default_factory=dict)
    uretim_kaynaklari: list[str] = field(default_factory=list)

    @property
    def gate_tur(self) -> str:
        return self.cli_tur.replace("-", "_")

    @property
    def set_sinifi(self) -> str:
        return str(self.manifest["sinif"])

    @property
    def set_surumu(self) -> str:
        return str(self.manifest["surum"])

    @property
    def data_version(self) -> str:
        return f"{VERSIYON}-{self.set_surumu}-{self.tahmin_ozeti[:8]}"

    def set_kaynaklari(self) -> list[str]:
        kaynaklar = self.manifest["kaynak"]
        assert isinstance(kaynaklar, list)
        return sorted({str(k["source_id"]) for k in kaynaklar})


def tahmin_ozeti(parcalar: Sequence[str]) -> str:
    """Olculen uretim ciktisinin (sirali, metinsiz satirlar) SHA-256 ozeti."""
    h = hashlib.sha256()
    for p in parcalar:
        h.update(p.encode("utf-8"))
        h.update(b"\n")
    return h.hexdigest()


def rapor_govdesi(
    s: TurSonucu, olculdu: datetime, gerileme: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    return {
        "rapor_surumu": RAPOR_SURUMU,
        "tur": s.cli_tur,
        "xref_gate_tur": s.gate_tur,
        "set": str(s.manifest["set"]),
        "set_surumu": s.set_surumu,
        "sinif": s.set_sinifi,
        "olcum_turu": str(s.manifest["olcum_turu"]),
        "data_version": s.data_version,
        "olculdu_utc": zaman_metni(olculdu),
        "ornek_sayisi": int(str(s.manifest["ornek_sayisi"])),
        "olculen_ornek_sayisi": s.olculen_ornek,
        "olculer": {k: round(v, 6) for k, v in sorted(s.olculer.items())},
        "esik": dict(sorted(s.esikler.items())),
        "esik_sonuclari": dict(sorted(s.esik_sonuclari.items())),
        "sonuc": s.sonuc,
        "alt_sonuclar": dict(sorted(s.alt_sonuclar.items())),
        "ayrintilar": s.ayrintilar,
        "referans_kapsami": s.referans_kapsami,
        "notlar": s.notlar,
        "set_kaynaklari": s.manifest["kaynak"],
        "uretim_kaynaklari": sorted(s.uretim_kaynaklari),
        "dogrulama_yontemi": s.manifest["dogrulama_yontemi"],
        "uretim_komutu": s.manifest["uretim_komutu"],
        "gerileme": list(gerileme),
    }


def govde_ozeti(govde: Mapping[str, object]) -> str:
    """`rapor_sha256` alani HARIC kanonik JSON ozeti."""
    temiz = {k: v for k, v in govde.items() if k != "rapor_sha256"}
    return hashlib.sha256(json_baytlari(temiz)).hexdigest()


def rapor_yolu(veri_kok: Path, data_version: str, cli_tur: str) -> Path:
    return veri_kok / RAPOR_KLASORU / f"{data_version}-gold-{cli_tur}.json"


def rapor_yaz(veri_kok: Path, s: TurSonucu, govde: dict[str, object]) -> tuple[Path, str]:
    """Raporu atomik yazar; `(yol, rapor_sha256)` dondurur."""
    ozet = govde_ozeti(govde)
    govde["rapor_sha256"] = ozet
    yol = rapor_yolu(veri_kok, s.data_version, s.cli_tur)
    yol.parent.mkdir(parents=True, exist_ok=True)
    gecici = yol.with_name(yol.name + ".tmp")
    gecici.write_bytes(json_baytlari(govde))
    lineage.atomik_degistir(gecici, yol)
    return yol, ozet


def rapor_oku(yol: Path) -> dict[str, object]:
    """Raporu okur ve `rapor_sha256` degerini dogrular; bozuksa `GirdiHatasi`."""
    try:
        veri = json.loads(yol.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise GirdiHatasi("gold raporu okunamadi") from None
    if not isinstance(veri, dict) or veri.get("rapor_sha256") != govde_ozeti(veri):
        raise GirdiHatasi("gold raporu ozeti tutmuyor")
    return veri


def onceki_kabul_edilmis(veri_kok: Path, cli_tur: str) -> dict[str, object] | None:
    """Ayni tur icin son `gecti` rapor (`olculdu_utc`); yoksa `None` (ilk kosu).

    Bozuk bir rapor sessizce atlanmaz: `GirdiHatasi` (cikis 2).
    """
    klasor = veri_kok / RAPOR_KLASORU
    if not klasor.is_dir():
        return None
    adaylar: list[dict[str, object]] = []
    for yol in sorted(klasor.glob(f"*-gold-{cli_tur}.json")):
        rapor = rapor_oku(yol)
        if rapor.get("tur") == cli_tur and rapor.get("sonuc") == GECTI:
            adaylar.append(rapor)
    if not adaylar:
        return None
    return max(adaylar, key=lambda r: str(r.get("olculdu_utc")))


def onceki_olculer(rapor: Mapping[str, object] | None) -> dict[str, float] | None:
    if rapor is None:
        return None
    olculer = rapor.get("olculer")
    if not isinstance(olculer, dict):
        raise GirdiHatasi("onceki rapor olculer tasimiyor")
    return {str(k): float(v) for k, v in olculer.items() if isinstance(v, int | float)}


# --- xref_gate ---------------------------------------------------------------------------

UPSERT: Final = (
    "INSERT INTO icerik.xref_gate"
    " (tur, set_sinifi, set_surumu, sonuc, set_kaynaklari, rapor_sha256, data_version, olculdu_at)"
    " VALUES (%s::icerik.xref_type, %s, %s, %s, %s, %s, %s, now())"
    " ON CONFLICT (tur, set_sinifi) DO UPDATE SET"
    " set_surumu = EXCLUDED.set_surumu, sonuc = EXCLUDED.sonuc,"
    " set_kaynaklari = EXCLUDED.set_kaynaklari, rapor_sha256 = EXCLUDED.rapor_sha256,"
    " data_version = EXCLUDED.data_version, olculdu_at = now()"
)


def xref_gate_yaz(
    conn: psycopg.Connection,
    *,
    tur: str,
    set_sinifi: str,
    set_surumu: str,
    sonuc: str,
    set_kaynaklari: Sequence[str],
    rapor_sha256: str,
    data_version: str,
) -> None:
    """`icerik.xref_gate` satirini (tur, set_sinifi) anahtariyla upsert eder (commit cagirana)."""
    if tur not in GATE_TURLERI:
        raise GirdiHatasi(f"xref_gate turu gecersiz: {tur}")
    if sonuc not in (GECTI, KALDI):
        raise GirdiHatasi("xref_gate sonucu gecti ya da kaldi olmali")
    conn.execute(
        UPSERT,
        (tur, set_sinifi, set_surumu, sonuc, list(set_kaynaklari), rapor_sha256, data_version),
    )
