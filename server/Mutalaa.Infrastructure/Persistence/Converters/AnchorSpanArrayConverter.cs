using Microsoft.EntityFrameworkCore.ChangeTracking;
using Microsoft.EntityFrameworkCore.Storage.ValueConversion;
using Mutalaa.Domain.Anchors;
using NpgsqlTypes;

namespace Mutalaa.Infrastructure.Persistence.Converters;

/// <summary>AnchorSpan[] ile int4range[] arasindaki donusturucu (unit.sentences). Eleman kurallari AnchorSpanRangeConverter ile aynidir.</summary>
public sealed class AnchorSpanArrayConverter()
    : ValueConverter<AnchorSpan[], NpgsqlRange<int>[]>(v => ToRanges(v), r => FromRanges(r))
{
    public static NpgsqlRange<int>[] ToRanges(AnchorSpan[] spans)
    {
        ArgumentNullException.ThrowIfNull(spans);
        NpgsqlRange<int>[] result = new NpgsqlRange<int>[spans.Length];
        for (int i = 0; i < spans.Length; i++)
        {
            result[i] = AnchorSpanRangeConverter.ToRange(spans[i]);
        }

        return result;
    }

    public static AnchorSpan[] FromRanges(NpgsqlRange<int>[] ranges)
    {
        ArgumentNullException.ThrowIfNull(ranges);
        AnchorSpan[] result = new AnchorSpan[ranges.Length];
        for (int i = 0; i < ranges.Length; i++)
        {
            result[i] = AnchorSpanRangeConverter.FromRange(ranges[i]);
        }

        return result;
    }
}

/// <summary>AnchorSpan[] icin eleman eleman (SequenceEqual) karsilastirici; anlik kopya yeni dizidir.</summary>
public sealed class AnchorSpanArrayComparer()
    : ValueComparer<AnchorSpan[]>(
        (a, b) => AreEqual(a, b),
        a => Hash(a),
        a => Copy(a))
{
    public static bool AreEqual(AnchorSpan[]? a, AnchorSpan[]? b) =>
        ReferenceEquals(a, b) || (a is not null && b is not null && a.AsSpan().SequenceEqual(b));

    public static int Hash(AnchorSpan[]? value)
    {
        HashCode hash = default;
        if (value is not null)
        {
            foreach (AnchorSpan span in value)
            {
                hash.Add(span);
            }
        }

        return hash.ToHashCode();
    }

    public static AnchorSpan[] Copy(AnchorSpan[] value) => [.. value];
}
