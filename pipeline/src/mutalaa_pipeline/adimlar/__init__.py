"""Kaynaga ozgu hat adimlari: `normalize --source` ve `anchor --source` (A10.4).

`normalize/` ve `anchor/` paketleri yaprak kitapliktir: ayni kurallar TypeScript ve C#'ta da
yazilidir ve ayni test vektorlerine baglidir (Proje yapisi §3). Bu yuzden `export` ve `cli`
paketlerini, calisma baglamini (`runctx`), `staged` ve `zincir` modullerini iceri aktaramazlar
(`tests/test_normalize_unit.py` normalize paketi icin bunu sinar). Adim kodu, yani staged
okuma-yazma, parmak izi, manifest ve komut govdesi, burada durur ve kitapliklari kullanir.
"""
