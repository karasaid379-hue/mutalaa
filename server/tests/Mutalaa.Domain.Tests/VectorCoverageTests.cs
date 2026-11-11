namespace Mutalaa.Domain.Tests;

/// <summary>
/// Her vektor dosyasi ya bir C# kosucusu tarafindan yuklenir ya da burada acikca atlanir (A12.6).
/// Yeni, bilinmeyen bir .jsonl dosyasi sessizce atlanmaz; bu test kirilir ve dosya ya kosucuya baglanir
/// ya da asagidaki atlama listesine gerekceyle eklenir.
/// </summary>
public class VectorCoverageTests
{
    // C# kosucularinin yukledigi dosyalar (Support/VectorFile.cs kullanimlari).
    private static readonly string[] Loaded =
    [
        "anchors/valid.jsonl",       // AnchorVectorTests
        "anchors/invalid.jsonl",     // AnchorVectorTests
        "anchors/compare.jsonl",     // AnchorVectorTests
        "anchors/contains.jsonl",    // AnchorVectorTests
        "anchors/route.jsonl",       // AnchorVectorTests
        "content-hash/hash.jsonl",   // TextVectorTests
        "normalize/ar.jsonl",        // NormalizeVectorTests
        "normalize/tr.jsonl",        // NormalizeVectorTests
        "offsets/offsets.jsonl",     // TextVectorTests
    ];

    // Acikca atlanan dosyalar (tek yer). Dosya adi -> gerekce.
    private static readonly Dictionary<string, string> SkippedFiles = new(StringComparer.Ordinal)
    {
        // FTS5 sorgu kurucusu yalniz TypeScript'te (packages/search); C#'ta sorgu kurucusu yok.
        ["fts-query/query.jsonl"] = "yalniz TypeScript kosar",
        // Turkce govdeleyici (stemTr) yalniz TypeScript'te; C#'ta govdeleyici yok (K-44 madde 1).
        ["normalize/tr-govde.jsonl"] = "C#'ta govdeleyici yok",
        // Cikarilmis metin (Elmalili meali) donusumunu yalniz hat yapar; vektoru yalniz Python kosar (K-49 madde 13).
        ["extract/meal.jsonl"] = "yalniz Python kosar (cikarim yalniz hatta)",
    };

    // Acikca atlanan klasorler (on ek). arama/ olcum kumesidir (basari olcusu); dosyalari henuz yok, kural ileriye donuktur.
    private static readonly string[] SkippedFolders = ["arama/"];

    private static string VectorsRoot => Path.Combine(AppContext.BaseDirectory, "vectors");

    private static string[] DiskFiles()
    {
        string root = VectorsRoot;
        Assert.True(Directory.Exists(root), "vectors\\ klasoru cikti klasorune kopyalanmamis: " + root);
        string[] files = [.. Directory.GetFiles(root, "*.jsonl", SearchOption.AllDirectories)
            .Select(p => Path.GetRelativePath(root, p).Replace('\\', '/'))];
        Array.Sort(files, StringComparer.Ordinal);
        return files;
    }

    [Fact]
    public void Every_vector_file_on_disk_is_loaded_by_a_runner_or_explicitly_skipped()
    {
        string[] unknown = [.. DiskFiles().Where(f =>
            !Loaded.Contains(f, StringComparer.Ordinal)
            && !SkippedFiles.ContainsKey(f)
            && !SkippedFolders.Any(prefix => f.StartsWith(prefix, StringComparison.Ordinal)))];

        Assert.True(unknown.Length == 0,
            "Kosucusu ya da acik atlamasi olmayan vektor dosyalari: " + string.Join(", ", unknown));
    }

    [Fact]
    public void Loaded_and_skipped_lists_name_only_files_that_exist()
    {
        string[] disk = DiskFiles();

        foreach (string f in Loaded.Concat(SkippedFiles.Keys))
        {
            Assert.True(disk.Contains(f, StringComparer.Ordinal), "Listede olup diskte olmayan vektor dosyasi: " + f);
        }
    }

    [Fact]
    public void Loaded_and_skipped_lists_do_not_overlap()
    {
        foreach (string f in Loaded)
        {
            Assert.DoesNotContain(f, SkippedFiles.Keys);
        }
    }
}
