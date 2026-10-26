using System.Text;

namespace Mutalaa.Api.Tests.Support;

/// <summary>Depo koku (server/Mutalaa.slnx'in bulundugu ust klasor) ve depodaki dosyalar.</summary>
internal static class RepoFiles
{
    private const string RootMarker = "server/Mutalaa.slnx";

    /// <summary>Derleme klasorunden yukari dogru depo kokunu bulur.</summary>
    public static string Root()
    {
        DirectoryInfo? dir = new(AppContext.BaseDirectory);
        while (dir is not null)
        {
            if (File.Exists(Path.Combine([dir.FullName, .. RootMarker.Split('/')])))
            {
                return dir.FullName;
            }

            dir = dir.Parent;
        }

        throw new DirectoryNotFoundException($"Depo koku bulunamadi ({RootMarker} yukari dogru aranirken).");
    }

    /// <summary>Depo kokune gore '/' ayracli yolun tam yolu (dosya yoksa da).</summary>
    public static string PathOf(string relative) => Path.Combine([Root(), .. relative.Split('/')]);

    /// <summary>Kati UTF-8, BOM'suz okur; BOM varsa hata verir. Satir sonu LF'ye cevrilir.</summary>
    public static string ReadUtf8(string path)
    {
        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true).GetString(File.ReadAllBytes(path));
        if (text.Length > 0 && text[0] == (char)0xFEFF)
        {
            throw new InvalidDataException($"Dosyada BOM var: {path}");
        }

        return text.Replace("\r\n", "\n", StringComparison.Ordinal);
    }
}
