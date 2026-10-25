using System.Text.Json.Nodes;
using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Tests.Support;

namespace Mutalaa.Domain.Tests;

public class AyetSayilariTests
{
    [Fact]
    public void Has_114_surahs_and_6236_ayahs()
    {
        Assert.Equal(114, AyetSayilari.Sayilar.Length);
        Assert.Equal(6236, AyetSayilari.Sayilar.Sum());
        Assert.Equal(286, AyetSayilari.Sayilar[1]);
    }

    [Fact]
    public void Embedded_copy_equals_shared_json()
    {
        string path = Path.Combine(AppContext.BaseDirectory, "data", "ayet-sayilari.json");
        Assert.True(File.Exists(path), "shared/data/ayet-sayilari.json cikti klasorune kopyalanmamis.");

        JsonArray sayilar = JsonNode.Parse(File.ReadAllText(path))!.AsObject()["sayilar"]!.AsArray();
        int[] expected = [.. sayilar.Select(n => n!.GetValue<int>())];

        Assert.Equal(expected, AyetSayilari.Sayilar.ToArray());
    }

    [Fact]
    public void Missing_vector_file_fails_loudly()
    {
        Assert.Throws<FileNotFoundException>(() => VectorFile.Load("anchors/yok.jsonl"));
    }
}
