"""Turkce kelime -> Arapca kok hatti (A18.2, K-51 madde 9): saf islevler.

Modullerin sorumlulugu:

* `bolme`: belirtec ve on bolme (izafet, harf-i tarif, el- on eki, kesme ayrimi);
* `lemmatize`: zeyrek sarmalayici arayuzu (testlerde sahte lemmatizer verilir);
* `etimoloji`: kaikki dokumlerinden yapisal kanit (root sablonu, ar kaynakli sablonlar, ety agaci);
* `eslesme`: kanitin QAC kok ve lemma envanterine kesin eslesmesi;
* `politika`: K-51 madde 9 (a)-(e) kosullari; karar ve denetlenebilir kanit;
* `uret`: iki mealin birlesik sayimi, tur duzeyi karar tablosu, staged satirlari ve istatistik.

Dil modeli ve ag cagrisi yoktur (K-50). Bu paket dosya, veritabani ve zincire dokunmaz; adim
`adimlar/enrich_tr_roots.py`, yukleme `export/pg_tr_roots.py` icindedir. Hicbir sozluk metni
saklanmaz: kanitta yalniz madde basligi, alan adi ve alan degeri (kok harfleri, etimon bicimi)
bulunur.
"""
