"""Acik atif ve iktibas motoru (A18.4; Iktibas tespiti §2-§8, K-51 madde 4, 8 ve 10).

Moduller: `gramer` (acik Turkce atif grameri), `diziler` (Arapca dizi cikarma),
`normalizasyon` (esleme anahtari), `indeks` (3-4 gram indeksi uzerinde kelime konumu eslemesi),
`hizala` (tohum ve kelime duzeyinde Smith-Waterman), `kalip` (kalip listesi), `kurallar`
(baglam sinyalleri, puan ve guven), `iktibas` (birim basina motor), `uret` (staged satirlari),
`girdi` (veritabani okuyucusu). Dil modeli ve ag cagrisi yoktur (K-50); gri bolge adaylari
`aday` kalir ve editor kuyruguna gider.
"""
