"""Calistirma baglami: UUIDv7 run_id, kaynak kaydi denetimi, rapor, komut sarmalayici.

`require_sources`: `--source` alan her komut, okudugu ve yazdigi butun kaynaklar icin giriste
cagirir. Kayit yoksa ya da kayit gecersizse `GirdiHatasi` (cikis 2); kaydi olmayan kaynak
hatta alinmaz (K-42 madde 4).
"""

import os
import secrets
import sys
import threading
import uuid
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Final

from mutalaa_pipeline import cikis, lineage, sources
from mutalaa_pipeline.config import Ayarlar
from mutalaa_pipeline.export.ortak import GirdiHatasi, depo_koku
from mutalaa_pipeline.logs import (
    Gunluk,
    Saat,
    guvenli_deger,
    ileti_temizle,
    json_baytlari,
    simdi,
    zaman_metni,
)
from mutalaa_pipeline.sources.kayit import Kaynak, Sonuc

if TYPE_CHECKING:
    from mutalaa_pipeline.ingest.base import StagedUnit

GUNLUK_KLASORU: Final = "logs"
RAPOR_KLASORU: Final = "reports"
STAGED_KLASORU: Final = "staged"
RAW_KLASORU: Final = "raw"
SAYAC_BITI: Final = 12
RASTGELE_ALAN: Final = 11  # sayac baslangici 2**11'in altinda: tasma payi birakir


class QaKaldi(Exception):
    """QA kapisi kaldi; komut 1 ile cikar."""


def cikis_kodu(hata: BaseException) -> int:
    """Istisna turunden cikis kodu (Icerik hatti §4): QA kapisi 1, oteki her hata 2."""
    if isinstance(hata, QaKaldi):
        return cikis.QA_KALDI
    return cikis.GIRDI_HATASI


class Uuid7Uretici:
    """RFC 9562 §6.2 yontem 1: 12 bitlik sayac `rand_a` alaninda; ayni milisaniyede monoton.

    Saat geri giderse son zaman damgasi korunur ve sayac artar. Sayac tasarsa zaman damgasi
    bir milisaniye ilerletilir. `saat_ms` ve `rastgele` testler icin disaridan verilebilir.
    """

    def __init__(
        self,
        saat_ms: Callable[[], int] | None = None,
        rastgele: Callable[[int], int] | None = None,
    ) -> None:
        self._saat_ms = saat_ms if saat_ms is not None else _simdi_ms
        self._rastgele = rastgele if rastgele is not None else secrets.randbits
        self._son_ms = -1
        self._sayac = 0
        self._kilit = threading.Lock()

    def uret(self) -> uuid.UUID:
        with self._kilit:
            ms = self._saat_ms()
            if ms > self._son_ms:
                self._son_ms = ms
                self._sayac = self._rastgele(RASTGELE_ALAN)
            else:
                self._sayac += 1
                if self._sayac >= 1 << SAYAC_BITI:
                    self._son_ms += 1
                    self._sayac = self._rastgele(RASTGELE_ALAN)
            ms_son, sayac = self._son_ms, self._sayac
        rand_b = self._rastgele(62)
        deger = (
            (ms_son & ((1 << 48) - 1)) << 80
            | 0x7 << 76
            | (sayac & 0xFFF) << 64
            | 0b10 << 62
            | rand_b
        )
        return uuid.UUID(int=deger)


def _simdi_ms() -> int:
    return int(simdi().timestamp() * 1000)


_VARSAYILAN_URETICI: Final = Uuid7Uretici()


def uuid7() -> uuid.UUID:
    """Surec boyunca monoton UUIDv7."""
    return _VARSAYILAN_URETICI.uret()


def _guvenli_slug(slug: str) -> str:
    return ascii(slug)[1:-1][:64]


@dataclass
class RunContext:
    run_id: str
    depo_kok: Path
    veri_kok: Path
    ayarlar: Ayarlar
    komut: str
    adim: str
    saat: Saat
    baslangic: datetime
    kaynak_idleri: tuple[str, ...] = ()
    parametreler: dict[str, object] = field(default_factory=dict)
    force: bool = False
    dry_run: bool = False
    limit: int | None = None
    sayilar: dict[str, int] = field(default_factory=dict)
    uyarilar: list[str] = field(default_factory=list)
    # Rapora eklenen alanlar (ornegin `qa run` kapilari); temel rapor alanlarini ezemez.
    rapor_ek: dict[str, object] = field(default_factory=dict)
    gunluk: Gunluk = field(init=False)
    _sonuclar: dict[str, Sonuc] | None = field(default=None, init=False, repr=False)
    _git: lineage.GitDurumu | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.gunluk = Gunluk(
            self.veri_kok / GUNLUK_KLASORU,
            self.run_id,
            self.adim,
            duzey=self.ayarlar.log_duzeyi,
            saat=self.saat,
            gizliler=self.ayarlar.gizli_degerler(),
        )

    @classmethod
    def olustur(
        cls,
        ayarlar: Ayarlar,
        *,
        komut: str,
        adim: str,
        depo_kok: Path | None = None,
        kaynaklar: Iterable[str] = (),
        parametreler: Mapping[str, object] | None = None,
        force: bool = False,
        dry_run: bool = False,
        limit: int | None = None,
        saat: Saat = simdi,
        uretici: Uuid7Uretici | None = None,
    ) -> "RunContext":
        run_id = str((uretici if uretici is not None else _VARSAYILAN_URETICI).uret())
        return cls(
            run_id=run_id,
            depo_kok=(depo_kok if depo_kok is not None else depo_koku()).resolve(),
            veri_kok=ayarlar.veri_kok,
            ayarlar=ayarlar,
            komut=komut,
            adim=adim,
            saat=saat,
            baslangic=saat(),
            kaynak_idleri=tuple(kaynaklar),
            parametreler=dict(parametreler or {}),
            force=force,
            dry_run=dry_run,
            limit=limit,
        )

    # --- yollar -----------------------------------------------------------------------

    def staged_dizin(self, source_id: str) -> Path:
        return self.veri_kok / STAGED_KLASORU / source_id / self.run_id

    def staged_kaynak_dizini(self, source_id: str) -> Path:
        return self.veri_kok / STAGED_KLASORU / source_id

    def raw_dizin(self, source_id: str) -> Path:
        return self.veri_kok / RAW_KLASORU / source_id

    # --- kaynak kaydi ---------------------------------------------------------------

    def _kayitlar(self) -> dict[str, Sonuc]:
        if self._sonuclar is None:
            sonuclar = sources.yukle(self.depo_kok)
            self._sonuclar = {s.dosya.removesuffix(".toml"): s for s in sonuclar}
        return self._sonuclar

    def require_sources(self, kaynaklar: str | Iterable[str]) -> dict[str, Kaynak]:
        """Her kaynagin kaydini denetler; biri bile kayitsiz ya da gecersizse `GirdiHatasi`.

        Gecerli kayit, `sources check` denetiminden hatasiz gecen kayittir (G-KAY: sema,
        zorunlu alanlar, dolu `atif_metni`). Donus: `{slug: Kaynak}`, ilk gorulme sirasinda.
        """
        slugs = [kaynaklar] if isinstance(kaynaklar, str) else list(kaynaklar)
        if not slugs:
            raise GirdiHatasi("kaynak verilmedi")
        kayitlar = self._kayitlar()
        gecenler: dict[str, Kaynak] = {}
        nedenler: list[str] = []
        for slug in dict.fromkeys(slugs):
            ad = _guvenli_slug(slug)
            sonuc = kayitlar.get(slug)
            if sonuc is None:
                nedenler.append(f"{ad}: kayitsiz")
                continue
            if sonuc.kaynak is None:
                nedenler.append(f"{ad}: kayit gecersiz ({len(sonuc.hatalar)} hata)")
                continue
            gecenler[slug] = sonuc.kaynak
        if nedenler:
            self.gunluk.hata(
                "kaynak_kaydi_gecersiz", kaynak_sayisi=len(slugs), reddedilen=len(nedenler)
            )
            raise GirdiHatasi(
                "kaynak kaydi: " + "; ".join(nedenler) + " (ayrinti: mutalaa sources check)"
            )
        return gecenler

    # --- veri soyu --------------------------------------------------------------------

    def git(self) -> lineage.GitDurumu:
        if self._git is None:
            self._git = lineage.git_durumu(self.depo_kok)
        return self._git

    def parmak_izi(self, girdiler: list[lineage.Girdi]) -> str:
        """Calistirmanin parmak izi. Ortam ve `.env` degerleri girmez."""
        return lineage.parmak_izi(
            adim=self.adim,
            parametreler=self.parametreler,
            girdiler=girdiler,
            config_sha=lineage.config_sha256(self.ayarlar.config_yolu),
            git_commit=self.git().commit,
            araclar=lineage.arac_surumleri(),
        )

    def manifest_yaz(
        self,
        klasor: Path,
        *,
        girdiler: list[lineage.Girdi],
        ciktilar: list[lineage.Cikti],
        parmak: str,
        ayrintilar: Mapping[str, object] | None = None,
    ) -> Path:
        manifest = lineage.manifest_kur(
            run_id=self.run_id,
            adim=self.adim,
            komut=self.komut,
            git=self.git(),
            uv_lock=lineage.uv_lock_sha256(self.depo_kok),
            config_sha=lineage.config_sha256(self.ayarlar.config_yolu),
            girdiler=girdiler,
            araclar=lineage.arac_surumleri(),
            ciktilar=ciktilar,
            parmak=parmak,
            ayrintilar=ayrintilar,
        )
        return lineage.manifest_yaz(klasor, manifest)

    def write_staged(self, source_id: str, birimler: Iterable["StagedUnit"]) -> lineage.Cikti:
        """`units.jsonl` dosyasini yazar (capaya gore sirali); manifest yazmaz."""
        from mutalaa_pipeline.ingest.base import staged_yaz

        return staged_yaz(self, source_id, birimler)

    # --- rapor ------------------------------------------------------------------------

    def sayi(self, ad: str, deger: int) -> None:
        self.sayilar[ad] = deger

    def uyar(self, mesaj: str) -> None:
        self.uyarilar.append(ileti_temizle(mesaj, self.ayarlar.gizli_degerler()))

    def rapor_yaz(self, durum: str, cikis_kodu_: int) -> Path:
        """`data/reports/{run_id}.json`: yalniz sayilar, uyarilar ve sure.

        `rapor_ek` alanlari (ornegin `qa run` icin `kaynak`, `anchor_run_id`, `units_sha256`,
        `kapilar`) temel alanlarin yanina eklenir; temel bir alanin adi kullanilamaz.
        """
        bitis = self.saat()
        gizliler = self.ayarlar.gizli_degerler()
        rapor: dict[str, object] = {
            "run_id": self.run_id,
            "komut": self.komut,
            "adim": self.adim,
            "kaynaklar": list(self.kaynak_idleri),
            "durum": durum,
            "cikis_kodu": cikis_kodu_,
            "dry_run": self.dry_run,
            "baslangic": zaman_metni(self.baslangic),
            "bitis": zaman_metni(bitis),
            "sure_sn": round((bitis - self.baslangic).total_seconds(), 3),
            "sayilar": self.sayilar,
            "uyarilar": self.uyarilar,
            "parametreler": self.parametreler,
        }
        for ad, deger in self.rapor_ek.items():
            if ad in rapor:
                raise ValueError("rapor_ek temel bir rapor alanini ezemez")
            rapor[ad] = deger
        veri = json_baytlari(guvenli_deger(rapor, gizliler))
        klasor = self.veri_kok / RAPOR_KLASORU
        klasor.mkdir(parents=True, exist_ok=True)
        hedef = klasor / f"{self.run_id}.json"
        gecici = klasor / f"{self.run_id}.json.tmp"
        with gecici.open("wb") as dosya:  # guc kesilirse sifir uzunluklu rapor kalmasin
            dosya.write(veri)
            dosya.flush()
            os.fsync(dosya.fileno())
        lineage.atomik_degistir(gecici, hedef)
        return hedef


def komut_calistir(ctx: RunContext, govde: Callable[[RunContext], int | None]) -> int:
    """Komut govdesini calistirir; istisnayi cikis koduna cevirir, rapor ve gunluk yazar.

    Hata iletisi stderr'e temizlenmis olarak yazilir (baglanti dizesi ve ASCII disi metin yok).
    Beklenmeyen istisnada yalniz tur adi yazilir; iz (traceback) yazilmaz.
    """
    kod = cikis.BASARILI
    gizliler = ctx.ayarlar.gizli_degerler()
    ctx.gunluk.bilgi("basla", kaynak_sayisi=len(ctx.kaynak_idleri))
    try:
        sonuc = govde(ctx)
        kod = sonuc if sonuc is not None else cikis.BASARILI
    except (GirdiHatasi, QaKaldi) as hata:
        kod = cikis_kodu(hata)
        sys.stderr.write(f"hata: {ileti_temizle(str(hata), gizliler)}\n")
    except Exception as hata:
        kod = cikis.GIRDI_HATASI
        sys.stderr.write(f"hata: beklenmeyen hata ({type(hata).__name__})\n")
    durum = "tamam" if kod == cikis.BASARILI else "basarisiz"
    ctx.gunluk.yaz(
        "INFO" if kod == cikis.BASARILI else "ERROR", "bitti", sayilar={"cikis_kodu": kod}
    )
    ctx.rapor_yaz(durum, kod)
    return kod
