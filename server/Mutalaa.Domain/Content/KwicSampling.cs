namespace Mutalaa.Domain.Content;

/// <summary>Lemma kartindaki KWIC orneklemi (K-50, BC-56): sik lemmada belirlenimli, tum listeye yayilan secim.</summary>
public static class KwicSampling
{
    /// <summary>Kartta gosterilen en cok ornek sayisi.</summary>
    public const int MaxSamples = 8;

    /// <summary>
    /// <paramref name="total"/> sirali gecisten en cok <paramref name="max"/> tanesinin dizinleri (artan, benzersiz).
    /// <paramref name="total"/> en cok <paramref name="max"/> ise hepsi; degilse <c>i * total / max</c> (i = 0..max-1): ilk gecis her zaman
    /// vardir ve ornekler okuma sirasina esit yayilir. Ayni girdi her zaman ayni diziyi verir (rastgelelik yok).
    /// </summary>
    public static IReadOnlyList<int> SampleIndices(int total, int max = MaxSamples)
    {
        ArgumentOutOfRangeException.ThrowIfNegative(total);
        ArgumentOutOfRangeException.ThrowIfNegativeOrZero(max);

        if (total <= max)
        {
            return [.. Enumerable.Range(0, total)];
        }

        int[] picks = new int[max];
        for (int i = 0; i < max; i++)
        {
            picks[i] = (int)((long)i * total / max);
        }

        return picks;
    }
}
