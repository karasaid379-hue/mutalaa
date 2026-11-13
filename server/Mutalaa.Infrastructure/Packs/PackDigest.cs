using System.Security.Cryptography;
using Mutalaa.Domain.Releases;
using Mutalaa.Domain.Text;

namespace Mutalaa.Infrastructure.Packs;

/// <summary>
/// Paket ozeti (K-46 madde 1; pack_meta.content_digest, release.ozetler.paketler). SHA-256 girdisi, her biri LF ile biten RFC 8785 JSON dizileridir:
/// once basliklar <c>["meta","schema_version",1]</c>, <c>["meta","normalizer_version","1.0"]</c>, <c>["meta","flavor","dev"]</c>, <c>["meta","pack_id","core"]</c>
/// (ve kapi ozeti olan paketlerde <c>["meta","gate_summary","{...}"]</c>);
/// sonra <see cref="PackRows"/> satirlari <c>[tablo, degerler...]</c> (sabit tablo sirasi, anahtar bayt sirasi). version, built_at, data_version ve
/// content_digest ozete girmez. Yazma yapmaz: cagiran onceki yayinin ozetiyle karsilastirip paketi yazmaktan vazgecebilir. Sonuc 64 kucuk harf onaltilik.
/// </summary>
public static class PackDigest
{
    private static readonly byte[] Lf = [(byte)'\n'];

    public static string Compute(PackContent content)
    {
        ArgumentNullException.ThrowIfNull(content);

        using IncrementalHash hash = IncrementalHash.CreateHash(HashAlgorithmName.SHA256);
        Append(hash, "schema_version", (long)content.SchemaVersion);
        Append(hash, "normalizer_version", SearchNormalizer.NormalizerVersion);
        Append(hash, "flavor", content.Flavor.ToLabel());
        Append(hash, "pack_id", content.PackId);
        if (content.GateSummary is { } gateSummary)
        {
            // K-51 madde 5 ve 11: tur kapisi sinifi ve sonucu paket icerigidir; kapi degisirse paket ozeti degisir.
            Append(hash, PackMetaKeys.GateSummary, gateSummary);
        }

        foreach (PackRow row in PackRows.Enumerate(content))
        {
            hash.AppendData(PackRows.Canonical(row));
            hash.AppendData(Lf);
        }

        return Convert.ToHexStringLower(hash.GetHashAndReset());
    }

    private static void Append(IncrementalHash hash, string key, object value)
    {
        hash.AppendData(PackRows.CanonicalArray("meta", [key, value]));
        hash.AppendData(Lf);
    }
}
