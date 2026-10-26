using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Infrastructure.Persistence.Converters;

/// <summary>
/// AnchorRef ile text capa sutunu arasindaki donusturucu (Editoryal veritabani 12). Sutunlar birim capasi tasir.
/// Donusturucu yalniz '@' araligini reddeder (aralik ayri int4range sutunundadir). Capanin birim duzeyinde olmasi
/// (xref uclari: q:2:255:3-7 -> q:2:255 + span) donusturucunun isi degildir; hat QA'si ve A10/A14 dogrulamasi denetler (K-35 toUnitSpan).
/// Okurken AnchorRef.Parse cagrilir; gecersiz dizgi AnchorException atar.
/// </summary>
public sealed class AnchorRefConverter()
    : ValueConverter<AnchorRef, string>(v => ToStore(v), s => AnchorRef.Parse(s))
{
    /// <summary>Yazma yolu; ifade agacinda throw olmadigi icin ayri yardimcidir.</summary>
    public static string ToStore(AnchorRef value)
    {
        ArgumentNullException.ThrowIfNull(value);
        if (value.Span is not null)
        {
            throw new InvalidOperationException(
                "Capa sutunu '@' araligi tasimaz; araligi ayri int4range sutununa yazin.");
        }

        return value.ToString();
    }
}
