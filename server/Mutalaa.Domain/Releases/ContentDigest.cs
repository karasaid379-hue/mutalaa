using System.Security.Cryptography;
using System.Text;

namespace Mutalaa.Domain.Releases;

/// <summary>Kaynak ozeti girdisi: birim capasi ve content_hash (64 kucuk harf onaltilik).</summary>
public readonly record struct ContentDigestEntry(string Anchor, string ContentHash);

/// <summary>
/// Kaynak icerik ozeti (BC-03, Yayin sureci 2.2): kaynagin etkin birimleri capa BAYT sirasiyla, her biri
/// <c>anchor + "\t" + content_hash + "\n"</c> satiri olarak SHA-256'ya verilir; sonuc 64 kucuk harf onaltilik.
/// Siralama UTF-8 baytlari uzerindedir (PostgreSQL COLLATE "C" ile ayni; StringComparer.Ordinal UTF-16 birim sirasidir ve
/// vekil ciftlerde UTF-8 sirasindan ayrilir). Bos kaynak: girdisiz SHA-256, yani
/// e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855. Paket ozeti Infrastructure'dadir; burada degildir.
/// </summary>
public static class ContentDigest
{
    private static readonly UTF8Encoding StrictUtf8 = new(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true);

    /// <summary>Girdi sirasindan bagimsizdir. Ayni capa iki kez verilirse ya da capa/hash sekme ya da satir sonu iceriyorsa ArgumentException atar.</summary>
    /// <exception cref="EncoderFallbackException">Capa ya da hash gecerli Unicode degilse.</exception>
    public static string Compute(IEnumerable<ContentDigestEntry> entries)
    {
        ArgumentNullException.ThrowIfNull(entries);

        List<(byte[] Anchor, byte[] Hash)> items = [];
        foreach (ContentDigestEntry entry in entries)
        {
            ArgumentNullException.ThrowIfNull(entry.Anchor);
            ArgumentNullException.ThrowIfNull(entry.ContentHash);
            if (HasSeparator(entry.Anchor) || HasSeparator(entry.ContentHash))
            {
                throw new ArgumentException($"Capa ya da hash sekme/satir sonu iceremez: {entry.Anchor}", nameof(entries));
            }

            items.Add((StrictUtf8.GetBytes(entry.Anchor), StrictUtf8.GetBytes(entry.ContentHash)));
        }

        items.Sort((a, b) => a.Anchor.AsSpan().SequenceCompareTo(b.Anchor.AsSpan()));
        for (int i = 1; i < items.Count; i++)
        {
            if (items[i - 1].Anchor.AsSpan().SequenceEqual(items[i].Anchor))
            {
                throw new ArgumentException($"Yinelenen capa: {StrictUtf8.GetString(items[i].Anchor)}", nameof(entries));
            }
        }

        using IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        byte[] tab = [(byte)'\t'];
        byte[] lf = [(byte)'\n'];
        foreach ((byte[] anchor, byte[] contentHash) in items)
        {
            hash.AppendData(anchor);
            hash.AppendData(tab);
            hash.AppendData(contentHash);
            hash.AppendData(lf);
        }

        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    private static bool HasSeparator(string text) =>
        text.Contains('\t', StringComparison.Ordinal) || text.Contains('\n', StringComparison.Ordinal);
}
