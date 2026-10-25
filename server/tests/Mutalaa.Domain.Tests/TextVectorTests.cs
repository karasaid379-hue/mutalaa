using System.Text;
using System.Text.Json.Nodes;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Tests.Support;
using Mutalaa.Domain.Text;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// offsets ve content-hash ortak vektorleri. Her Theory Invariant ve tr-TR kulturunde ayri kosar.
/// </summary>
public class TextVectorTests
{
    private const string OffsetsFile = "offsets/offsets.jsonl";
    private const string HashFile = "content-hash/hash.jsonl";

    public static TheoryData<string> OffsetIds => VectorFile.Ids(OffsetsFile);

    public static TheoryData<string> HashIds => VectorFile.Ids(HashFile);

    // ---- offsets ----

    [Theory]
    [MemberData(nameof(OffsetIds))]
    public void Offsets_Invariant(string id) => CultureScope.Invariant(() => CheckOffsets(id));

    [Theory]
    [MemberData(nameof(OffsetIds))]
    public void Offsets_trTR(string id) => CultureScope.Turkish(() => CheckOffsets(id));

    private static void CheckOffsets(string id)
    {
        VectorCase v = VectorFile.Get(OffsetsFile, id);
        string text = v.Input!.GetValue<string>();
        JsonObject expected = v.Expected!.AsObject();

        int codepoints = expected["codepoints"]!.GetValue<int>();
        Assert.Equal(codepoints, text.EnumerateRunes().Count());
        Assert.Equal(codepoints, CodePointOffsets.CodePointCount(text));
        Assert.Equal(expected["utf16"]!.GetValue<int>(), text.Length);

        foreach (JsonNode? pair in expected["cp_to_utf16"]!.AsArray())
        {
            int cp = pair![0]!.GetValue<int>();
            int utf16 = pair[1]!.GetValue<int>();
            Assert.Equal(utf16, CodePointOffsets.CpToUtf16(text, cp));
            Assert.Equal(cp, CodePointOffsets.Utf16ToCp(text, utf16));
        }

        // Gecersiz konumlar hata verir.
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.CpToUtf16(text, -1));
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.CpToUtf16(text, codepoints + 1));
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.Utf16ToCp(text, -1));
        Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.Utf16ToCp(text, text.Length + 1));

        // Vekil ciftin ortasi hata verir.
        for (int i = 1; i < text.Length; i++)
        {
            if (char.IsHighSurrogate(text[i - 1]) && char.IsLowSurrogate(text[i]))
            {
                int middle = i;
                Assert.Throws<ArgumentOutOfRangeException>(() => CodePointOffsets.Utf16ToCp(text, middle));
            }
        }

        if (expected.TryGetPropertyValue("snap", out JsonNode? snap) && snap is not null)
        {
            foreach (JsonNode? item in snap.AsArray())
            {
                JsonArray inRange = item!["in"]!.AsArray();
                JsonArray outRange = item["out"]!.AsArray();
                AnchorSpan actual = CodePointOffsets.SnapSpan(text, new AnchorSpan(inRange[0]!.GetValue<int>(), inRange[1]!.GetValue<int>()));
                Assert.Equal(new AnchorSpan(outRange[0]!.GetValue<int>(), outRange[1]!.GetValue<int>()), actual);
            }
        }
    }

    // ---- content-hash ----

    [Theory]
    [MemberData(nameof(HashIds))]
    public void ContentHash_Invariant(string id) => CultureScope.Invariant(() => CheckHash(id));

    [Theory]
    [MemberData(nameof(HashIds))]
    public void ContentHash_trTR(string id) => CultureScope.Turkish(() => CheckHash(id));

    private static void CheckHash(string id)
    {
        VectorCase v = VectorFile.Get(HashFile, id);
        JsonObject input = v.Input!.AsObject();
        JsonObject expected = v.Expected!.AsObject();
        string text = input["text"]!.GetValue<string>();
        string op = input["op"]!.GetValue<string>();
        string sha256 = expected["sha256"]!.GetValue<string>();

        switch (op)
        {
            case "ham":
                Assert.Equal(sha256, ContentHash.Compute(text));
                break;
            case "kanonik":
                string canonical = expected["text"]!.GetValue<string>();
                Assert.Equal(canonical, TextCanonicalizer.Canonicalize(text));
                Assert.Equal(canonical, TextCanonicalizer.Canonicalize(canonical));
                Assert.Equal(sha256, ContentHash.Compute(canonical));
                break;
            default:
                throw new InvalidOperationException("Bilinmeyen op: " + op);
        }
    }
}
