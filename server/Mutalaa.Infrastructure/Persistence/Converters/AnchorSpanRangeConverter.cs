using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using Mutalaa.Domain.Anchors;
using NpgsqlTypes;

namespace Mutalaa.Infrastructure.Persistence.Converters;

/// <summary>
/// AnchorSpan [Start, End) ile int4range arasindaki donusturucu. PostgreSQL int4range'i her zaman '[)' kanonik
/// bicimine cevirir; bu bicimden baska aralik (bos, sonsuz, '(]' ...) okunurken hata verir.
/// </summary>
public sealed class AnchorSpanRangeConverter()
    : ValueConverter<AnchorSpan, NpgsqlRange<int>>(v => ToRange(v), r => FromRange(r))
{
    public static NpgsqlRange<int> ToRange(AnchorSpan span)
    {
        if (span.Start < 0 || span.Start >= span.End)
        {
            throw new InvalidOperationException("Aralik 0 <= Start < End olmali.");
        }

        return new NpgsqlRange<int>(span.Start, lowerBoundIsInclusive: true, span.End, upperBoundIsInclusive: false);
    }

    public static AnchorSpan FromRange(NpgsqlRange<int> range)
    {
        if (range.IsEmpty
            || range.LowerBoundInfinite
            || range.UpperBoundInfinite
            || !range.LowerBoundIsInclusive
            || range.UpperBoundIsInclusive)
        {
            throw new InvalidOperationException("Veritabanindan '[)' bicimli, bos ve sonsuz olmayan bir int4range beklenir.");
        }

        if (range.LowerBound < 0 || range.LowerBound >= range.UpperBound)
        {
            throw new InvalidOperationException("Aralik 0 <= Start < End olmali.");
        }

        return new AnchorSpan(range.LowerBound, range.UpperBound);
    }
}
