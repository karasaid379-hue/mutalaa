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

    /// <summary>Capa sureklilik ihlalinin gerekcesi (K-47 madde 2). Rapordaki dizgi "capa-kayboldu:{alt-neden}" bicimindedir.</summary>
    public const string CapaKayboldu = "capa-kayboldu";
    public const string CapaSatirYok = "satir-yok";
    public const string CapaYonlendirmesiz = "yonlendirmesiz";
    public const string CapaKapsamDisi = "kapsam-disi";
}
