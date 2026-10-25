using System.Collections.Immutable;
using System.Globalization;
using System.Text;

namespace Mutalaa.Domain.Anchors;

/// <summary>
/// Kalici adres (capa) ve isteye bagli kod noktasi araligi (Capa semasi, K-26, K-35).
/// Ornekler uretimi <see cref="Parse(string)"/> ve <see cref="TryParse(string?, out AnchorRef?)"/> yapar;
/// disaridan elle uretilemez, bu yuzden her ornek gecerli ve kanoniktir.
/// Sayisal alanlarda 0 "yok" demektir (gecerli capada hicbir sayi 0 olamaz; yalniz <see cref="Span"/> baslangici 0 olabilir).
/// </summary>
public sealed partial record AnchorRef : IComparable<AnchorRef>
{
    internal AnchorRef()
    {
    }

    public AnchorKind Kind { get; internal init; }

    /// <summary>q, qa, meal, tf: sure numarasi (1-114).</summary>
    public int Sure { get; internal init; }

    /// <summary>q ve meal: ayet numarasi.</summary>
    public int Ayet { get; internal init; }

    /// <summary>q: ilk kelime; qa ve tf: ilk ayet.</summary>
    public int Ilk { get; internal init; }

    /// <summary>q: son kelime (kelime araligi); qa ve tf: son ayet.</summary>
    public int Son { get; internal init; }

    /// <summary>konu: slug.</summary>
    public string Slug { get; internal init; } = string.Empty;

    /// <summary>meal: meal kimligi.</summary>
    public string Meal { get; internal init; } = string.Empty;

    /// <summary>tf ve tfb: eser kimligi.</summary>
    public string Eser { get; internal init; } = string.Empty;

    /// <summary>tfb: bolum adi.</summary>
    public string Bolum { get; internal init; } = string.Empty;

    /// <summary>h ve ht: koleksiyon.</summary>
    public string Koleksiyon { get; internal init; } = string.Empty;

    /// <summary>ht: ceviri kimligi.</summary>
    public string Ceviri { get; internal init; } = string.Empty;

    /// <summary>rn ve k: bolum yolu; ilk oge kitaptir.</summary>
    public ImmutableArray<string> Yol { get; internal init; } = ImmutableArray<string>.Empty;

    /// <summary>tf, tfb, rn, k: paragraf numarasi.</summary>
    public int P { get; internal init; }

    /// <summary>rn: cumle numarasi.</summary>
    public int S { get; internal init; }

    /// <summary>h ve ht: hadis numarasi.</summary>
    public int No { get; internal init; }

    /// <summary>Kesin aralik <c>[baslangic, bitis)</c> (kod noktasi); yoksa null.</summary>
    public AnchorSpan? Span { get; internal init; }

    /// <summary>Capa semasi 11'deki tur etiketi: q, qa, konu, meal, tf, tfb, rn, h, ht, k.</summary>
    public string Tag => Kind switch
    {
        AnchorKind.Q => "q",
        AnchorKind.Qa => "qa",
        AnchorKind.Konu => "konu",
        AnchorKind.Meal => "meal",
        AnchorKind.Tf => "tf",
        AnchorKind.Tfb => "tfb",
        AnchorKind.Rn => "rn",
        AnchorKind.H => "h",
        AnchorKind.Ht => "ht",
        AnchorKind.K => "k",
        _ => throw new InvalidOperationException(),
    };

    /// <summary>Kanonik dizgi (<c>Parse(x).ToString() == x</c>).</summary>
    public override string ToString() => Format(withSpan: true);

    /// <summary>
    /// Dizi alani (<see cref="Yol"/>) elemanlariyla karsilastirilir; <c>Parse(x) == Parse(x)</c> dogrudur.
    /// </summary>
    public bool Equals(AnchorRef? other)
    {
        if (other is null)
        {
            return false;
        }

        if (ReferenceEquals(this, other))
        {
            return true;
        }

        return Kind == other.Kind
            && Sure == other.Sure
            && Ayet == other.Ayet
            && Ilk == other.Ilk
            && Son == other.Son
            && P == other.P
            && S == other.S
            && No == other.No
            && Span == other.Span
            && string.Equals(Slug, other.Slug, StringComparison.Ordinal)
            && string.Equals(Meal, other.Meal, StringComparison.Ordinal)
            && string.Equals(Eser, other.Eser, StringComparison.Ordinal)
            && string.Equals(Bolum, other.Bolum, StringComparison.Ordinal)
            && string.Equals(Koleksiyon, other.Koleksiyon, StringComparison.Ordinal)
            && string.Equals(Ceviri, other.Ceviri, StringComparison.Ordinal)
            && SameYol(Yol, other.Yol);
    }

    public override int GetHashCode()
    {
        HashCode h = default;
        h.Add(Kind);
        h.Add(Sure);
        h.Add(Ayet);
        h.Add(Ilk);
        h.Add(Son);
        h.Add(P);
        h.Add(S);
        h.Add(No);
        h.Add(Span);
        h.Add(Slug, StringComparer.Ordinal);
        h.Add(Meal, StringComparer.Ordinal);
        h.Add(Eser, StringComparer.Ordinal);
        h.Add(Bolum, StringComparer.Ordinal);
        h.Add(Koleksiyon, StringComparer.Ordinal);
        h.Add(Ceviri, StringComparer.Ordinal);
        foreach (string part in Yol)
        {
            h.Add(part, StringComparer.Ordinal);
        }

        return h.ToHashCode();
    }

    private static bool SameYol(ImmutableArray<string> a, ImmutableArray<string> b)
    {
        int la = a.IsDefault ? 0 : a.Length;
        int lb = b.IsDefault ? 0 : b.Length;
        if (la != lb)
        {
            return false;
        }

        for (int i = 0; i < la; i++)
        {
            if (!string.Equals(a[i], b[i], StringComparison.Ordinal))
            {
                return false;
            }
        }

        return true;
    }

    private static string Num(int value) => value.ToString(CultureInfo.InvariantCulture);

    private string Format(bool withSpan)
    {
        StringBuilder sb = new();
        switch (Kind)
        {
            case AnchorKind.Q:
                sb.Append("q:").Append(Num(Sure)).Append(':').Append(Num(Ayet));
                if (Ilk > 0)
                {
                    sb.Append(':').Append(Num(Ilk));
                    if (Son > 0)
                    {
                        sb.Append('-').Append(Num(Son));
                    }
                }

                break;
            case AnchorKind.Qa:
                sb.Append("q:").Append(Num(Sure)).Append(':').Append(Num(Ilk)).Append('-').Append(Num(Son));
                break;
            case AnchorKind.Konu:
                sb.Append("konu:").Append(Slug);
                break;
            case AnchorKind.Meal:
                sb.Append("meal:").Append(Meal).Append(':').Append(Num(Sure)).Append(':').Append(Num(Ayet));
                break;
            case AnchorKind.Tf:
                sb.Append("tf:").Append(Eser).Append(':').Append(Num(Sure)).Append('-').Append(Num(Ilk)).Append('-').Append(Num(Son))
                    .Append(":p").Append(Num(P));
                break;
            case AnchorKind.Tfb:
                sb.Append("tf:").Append(Eser).Append(':').Append(Bolum).Append(":p").Append(Num(P));
                break;
            case AnchorKind.Rn:
                sb.Append("rn:");
                AppendYol(sb);
                sb.Append(":p").Append(Num(P));
                if (S > 0)
                {
                    sb.Append(":s").Append(Num(S));
                }

                break;
            case AnchorKind.H:
                sb.Append("h:").Append(Koleksiyon).Append(':').Append(Num(No));
                break;
            case AnchorKind.Ht:
                sb.Append("ht:").Append(Ceviri).Append(':').Append(Koleksiyon).Append(':').Append(Num(No));
                break;
            case AnchorKind.K:
                sb.Append("k:");
                AppendYol(sb);
                sb.Append(":p").Append(Num(P));
                break;
            default:
                throw new InvalidOperationException();
        }

        if (withSpan && Span is { } span)
        {
            sb.Append('@').Append(Num(span.Start)).Append('-').Append(Num(span.End));
        }

        return sb.ToString();
    }

    private void AppendYol(StringBuilder sb)
    {
        for (int i = 0; i < Yol.Length; i++)
        {
            if (i > 0)
            {
                sb.Append(':');
            }

            sb.Append(Yol[i]);
        }
    }

    // ---- Birim islevleri (K-35 madde 5) ----

    /// <summary>
    /// Kelime ve kelime araligi ayete, cumle paragrafa iner; <c>@</c> araligi atilir.
    /// Ayet araligi, konu ve diger capalar aynen kalir.
    /// </summary>
    public AnchorRef UnitOf()
    {
        return Kind switch
        {
            AnchorKind.Q when Ilk > 0 => new AnchorRef { Kind = AnchorKind.Q, Sure = Sure, Ayet = Ayet },
            AnchorKind.Rn when S > 0 => this with { S = 0, Span = null },
            _ when Span is not null => this with { Span = null },
            _ => this,
        };
    }

    /// <summary>
    /// Depolama bicimi. Kelime ya da kelime araligi: ayet + <c>[ilk, son + 1)</c>; <c>@a-b</c>: taban capa + <c>[a, b)</c>;
    /// araliksiz birim: yalniz birim. Ayet araligi ve cumle capasinda <see cref="InvalidOperationException"/>.
    /// </summary>
    public UnitSpan ToUnitSpan()
    {
        if (Kind == AnchorKind.Qa)
        {
            throw new InvalidOperationException("Ayet araligi depolamada ayetlere bolunur (CoveredAyahs).");
        }

        if (Kind == AnchorKind.Rn && S > 0)
        {
            throw new InvalidOperationException("Cumle sinirini icerik verisi belirler.");
        }

        if (Kind == AnchorKind.Q && Ilk > 0)
        {
            int last = Son > 0 ? Son : Ilk;
            return new UnitSpan(UnitOf(), new AnchorSpan(Ilk, last + 1));
        }

        return new UnitSpan(UnitOf(), Span);
    }

    /// <summary>
    /// q, qa, tf ve meal icin kapsanan ayetler; diger turlerde bos.
    /// </summary>
    public ImmutableArray<AyahRef> CoveredAyahs()
    {
        switch (Kind)
        {
            case AnchorKind.Q:
            case AnchorKind.Meal:
                return [new AyahRef(Sure, Ayet)];
            case AnchorKind.Qa:
            case AnchorKind.Tf:
                ImmutableArray<AyahRef>.Builder builder = ImmutableArray.CreateBuilder<AyahRef>(Son - Ilk + 1);
                for (int a = Ilk; a <= Son; a++)
                {
                    builder.Add(new AyahRef(Sure, a));
                }

                return builder.MoveToImmutable();
            default:
                return [];
        }
    }

    // ---- Rota (K-35 madde 6) ----

    private static readonly string[] Schemes = ["mutalaa", "mutalaa-internal", "mutalaa-dev"];

    /// <summary>
    /// Yerel rota her turde mekaniktir (<c>{sema}://</c>, <c>:</c> yerine <c>/</c>, aralik <c>?aralik=</c>).
    /// Web rotasi yalniz Capa semasi 11 tablosundaki bicimler icin uretilir; digerlerinde <see cref="NotSupportedException"/>.
    /// </summary>
    /// <param name="target">Yerel ya da web.</param>
    /// <param name="scheme">mutalaa (varsayilan), mutalaa-internal ya da mutalaa-dev; yalniz yerel rotayi etkiler.</param>
    public string ToRoute(RouteTarget target, string? scheme = null)
    {
        switch (target)
        {
            case RouteTarget.Native:
                return NativeRoute(scheme ?? "mutalaa");
            case RouteTarget.Web:
                return WebRoute();
            default:
                throw new ArgumentOutOfRangeException(nameof(target));
        }
    }

    private string NativeRoute(string scheme)
    {
        if (Array.IndexOf(Schemes, scheme) < 0)
        {
            throw new ArgumentException("Bilinmeyen sema: yalniz mutalaa, mutalaa-internal ve mutalaa-dev.", nameof(scheme));
        }

        StringBuilder sb = new();
        sb.Append(scheme).Append("://").Append(Format(withSpan: false).Replace(':', '/'));
        if (Span is { } span)
        {
            sb.Append("?aralik=").Append(Num(span.Start)).Append('-').Append(Num(span.End));
        }

        return sb.ToString();
    }

    private string WebRoute()
    {
        switch (Kind)
        {
            case AnchorKind.Q when Ilk == 0:
                return "/kuran/" + Num(Sure) + "/" + Num(Ayet);
            case AnchorKind.Q when Son > 0:
                return "/kuran/" + Num(Sure) + "/" + Num(Ayet) + "?k=" + Num(Ilk) + "-" + Num(Son);
            case AnchorKind.Qa:
                return "/kuran/" + Num(Sure) + "/" + Num(Ilk) + "-" + Num(Son);
            case AnchorKind.Konu:
                return "/konu/" + Slug;
            case AnchorKind.Meal when Span is null:
                return "/meal/" + Meal + "/" + Num(Sure) + "#" + Num(Ayet);
            case AnchorKind.Tf when Span is null:
                return "/tefsir/" + Eser + "/" + Num(Sure) + "/" + Num(Ilk) + "#p" + Num(P);
            case AnchorKind.Rn when S == 0:
                return "/risale/" + string.Join('/', Yol) + "#p" + Num(P);
            case AnchorKind.H when Span is null:
                return "/hadis/" + Koleksiyon + "/" + Num(No);
            default:
                throw new NotSupportedException("Bu capa icin web rotasi tanimli degil (K-35 madde 6).");
        }
    }
}
