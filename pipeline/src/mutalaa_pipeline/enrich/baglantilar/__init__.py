"""Kur'an ici baglantilar (A18.3, K-51 madde 6, 10, 12): `kok`, `lemma` ve `benzer_ayet`.

Modullerin sorumlulugu:

* `girdi`: bellekteki girdi tipleri (ayet, kelime, kok) ve veritabani okuyucusu (salt okuma);
* `kok_lemma`: IDF ve birim-birim komsuluk (`kok` ve `lemma`; Baglanti modeli §6);
* `benzer`: sozluksel `benzer_ayet` (Uthmani ve imlai n-gram indeksi) ve QurSim birlestirmesi;
* `qursim`: QurSim CSV okuyucusu (yalniz `SS`, `SV`, `TS`, `TV` ve `Label`);
* `uret`: uc turun satirlarini ve istatistigi uretir.

Hesap modulleri saftir: veritabani, dosya ve ag yoktur; Arapca metin yalniz bellekte tutulur.
"""
