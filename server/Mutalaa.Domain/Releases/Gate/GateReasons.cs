namespace Mutalaa.Domain.Releases.Gate;

/// <summary>Kapi raporundaki gerekce dizgileri (ASCII, kararli). Rapor JSON'unun parcasidir; degistirilirse tuketiciler etkilenir.</summary>
public static class GateReasons
{
    public const string Uygun = "uygun";
    public const string Dogrulanmamis = "dogrulanmamis";
    public const string Aday = "aday";
    public const string IcerikYok = "icerik-yok";
    public const string TestKaynagi = "test-oneki";
    public const string KaynakKaydiYok = "kaynak-kaydi-yok";
    public const string AtifMetniBos = "atif-metni-bos";
    public const string KaynakGirmedi = "kaynak-girmedi:";
    public const string KullanimDisi = "kullanim-disi";
    public const string YapayZekaTaslagi = "yapay-zeka-taslagi-onaysiz";
    public const string OnaysizBirim = "onaysiz-birim";
    public const string Red = "red";
    public const string DurumBilinmiyor = "durum-bilinmiyor";
    public const string TurBilinmiyor = "tur-bilinmiyor";
    public const string KaynakEserGorunmez = "kaynak-eser-gorunmez";
    public const string HedefEserGorunmez = "hedef-eser-gorunmez";
    public const string AdayPublic = "aday-public";
    public const string DusukGuven = "dusuk-guven";
    public const string AnlamsalPublic = "anlamsal-public";
    public const string AcikInceleme = "acik-inceleme";
    public const string SozlukOnaysiz = "sozluk-onaysiz";
    public const string OnaysizSatir = "onaysiz-satir";
    public const string LemmaOnaysiz = "lemma-onaysiz";
    public const string UcBirimGirmedi = "uc-birim-girmedi";

    /// <summary>P-07 (K-51 madde 1): satirin evidence.src_hash ya da dst_hash degeri ucun birimin guncel content_hash ilk 16 haneyle tutmuyor.</summary>
    public const string UcOzetiTutmadi = "uc-ozeti-tutmadi";

    /// <summary>P-07 ve P-09 (K-51 madde 5 ve 11): otomatik turun tur kapisi hic olculmedi (ya da yalniz sentetik sette olculdu); public'e girmez.</summary>
    public const string KapiOlculmedi = "kapi-olculmedi";

    /// <summary>P-07 ve P-09: otomatik turun tur kapisi olculdu ve kaldi; public'e girmez.</summary>
    public const string KapiGecmedi = "kapi-gecmedi";

    /// <summary>P-09 (K-51 madde 9): onay_yolu otomatik ama kanit nesnesi yok ya da nesne degil.</summary>
    public const string KanitsizOtomatikOnay = "kanitsiz-otomatik-onay";

    /// <summary>P-09 (K-51 madde 1): tr_root_index satirinin unit_hash degeri birimin guncel content_hash ilk 16 haneyle tutmuyor.</summary>
    public const string OzetTutmadi = "ozet-tutmadi";

    /// <summary>P-09: tr_root_index satirinin birimi bu derlemenin kapsaminda degil (birim satiri yok, kullanim disi ya da suzulmus).</summary>
    public const string BirimGirmedi = "birim-girmedi";

    /// <summary>Turkce lemma onay yolu degerleri (lemma.onay_yolu; K-51 madde 9) ve otomatik onayli lemmanin kapidan gecen satir gerekcesi.</summary>
    public const string OnayYoluEditor = "editor";
    public const string OnayYoluOtomatik = "otomatik";
    public const string OtomatikOnay = "otomatik-onay";

    /// <summary>Kapi raporu "kapi" satiri gerekcesinin soneki: "{sinif}-ile-olculdu" (ornegin "silver-ile-olculdu").</summary>
    public const string OlculduSoneki = "-ile-olculdu";

    /// <summary>Onayli quran_word_fix uygulanamiyor (yayin reddi, kural kodu yok): "duzeltme-uygulanamaz:{neden}" (K-50 madde 9).</summary>
    public const string DuzeltmeUygulanamaz = "duzeltme-uygulanamaz";

    /// <summary>Capa sureklilik ihlalinin gerekcesi (K-47 madde 2). Rapordaki dizgi "capa-kayboldu:{alt-neden}" bicimindedir.</summary>
    public const string CapaKayboldu = "capa-kayboldu";
    public const string CapaSatirYok = "satir-yok";
    public const string CapaYonlendirmesiz = "yonlendirmesiz";
    public const string CapaKapsamDisi = "kapsam-disi";
}
