using System.Text.Json.Nodes;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>Nesnelerimizi vektorlerin "expected" JSON bicimine cevirir (Capa semasi 11 tipleri).</summary>
internal static class AnchorJson
{
    public static JsonObject Ref(AnchorRef r)
    {
        JsonObject anchor = new() { ["t"] = r.Tag };
        switch (r.Kind)
        {
            case AnchorKind.Q:
                anchor["sure"] = r.Sure;
                anchor["ayet"] = r.Ayet;
                if (r.Ilk > 0)
                {
                    anchor["ilk"] = r.Ilk;
                }

                if (r.Son > 0)
                {
                    anchor["son"] = r.Son;
                }

                break;
            case AnchorKind.Qa:
                anchor["sure"] = r.Sure;
                anchor["ilk"] = r.Ilk;
                anchor["son"] = r.Son;
                break;
            case AnchorKind.Konu:
                anchor["slug"] = r.Slug;
                break;
            case AnchorKind.Meal:
                anchor["meal"] = r.Meal;
                anchor["sure"] = r.Sure;
                anchor["ayet"] = r.Ayet;
                break;
            case AnchorKind.Tf:
                anchor["eser"] = r.Eser;
                anchor["sure"] = r.Sure;
                anchor["ilk"] = r.Ilk;
                anchor["son"] = r.Son;
                anchor["p"] = r.P;
                break;
            case AnchorKind.Tfb:
                anchor["eser"] = r.Eser;
                anchor["bolum"] = r.Bolum;
                anchor["p"] = r.P;
                break;
            case AnchorKind.Rn:
                anchor["yol"] = YolArray(r);
                anchor["p"] = r.P;
                if (r.S > 0)
                {
                    anchor["s"] = r.S;
                }

                break;
            case AnchorKind.H:
                anchor["koleksiyon"] = r.Koleksiyon;
                anchor["no"] = r.No;
                break;
            case AnchorKind.Ht:
                anchor["ceviri"] = r.Ceviri;
                anchor["koleksiyon"] = r.Koleksiyon;
                anchor["no"] = r.No;
                break;
            case AnchorKind.K:
                anchor["yol"] = YolArray(r);
                anchor["p"] = r.P;
                break;
            default:
                throw new InvalidOperationException();
        }

        JsonObject result = new() { ["anchor"] = anchor };
        if (r.Span is { } span)
        {
            result["span"] = new JsonObject { ["start"] = span.Start, ["end"] = span.End };
        }

        return result;
    }

    public static JsonObject UnitSpanJson(UnitSpan us)
    {
        JsonObject o = new() { ["unit"] = us.Unit.ToString() };
        if (us.Span is { } s)
        {
            o["span"] = new JsonArray(s.Start, s.End);
        }

        return o;
    }

    public static JsonArray Ayahs(IEnumerable<AyahRef> ayahs)
    {
        JsonArray arr = [];
        foreach (AyahRef a in ayahs)
        {
            arr.Add(new JsonObject { ["sure"] = a.Sure, ["ayet"] = a.Ayet });
        }

        return arr;
    }

    private static JsonArray YolArray(AnchorRef r)
    {
        JsonArray arr = [];
        foreach (string part in r.Yol)
        {
            arr.Add(part);
        }

        return arr;
    }

    public static void AssertSame(string id, JsonNode? expected, JsonNode? actual)
    {
        Assert.True(
            JsonNode.DeepEquals(expected, actual),
            $"[{id}] beklenen: {expected?.ToJsonString() ?? "null"}{Environment.NewLine}gercek:  {actual?.ToJsonString() ?? "null"}");
    }
}
