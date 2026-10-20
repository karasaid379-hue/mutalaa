using System.Reflection;
using System.Xml.Linq;

namespace Mutalaa.Api.Tests;

/// <summary>
/// Proje yapisi 2: Api -> Infrastructure -> Domain, Publisher -> Infrastructure; Mutalaa.Api ile Mutalaa.Publisher birbirine baglanmaz.
/// </summary>
public class ArchitectureTests
{
    [Fact]
    public void Api_assembly_does_not_reference_publisher()
    {
        Assembly api = typeof(Program).Assembly;

        Assert.Equal("Mutalaa.Api", api.GetName().Name);
        Assert.DoesNotContain(
            api.GetReferencedAssemblies(),
            a => string.Equals(a.Name, "Mutalaa.Publisher", StringComparison.Ordinal));
    }

    [Fact]
    public void Api_project_file_references_only_infrastructure()
    {
        // Kullanilmayan bir basvuru derleme meta verisine yazilmaz; bu yuzden proje dosyasi da okunur.
        string csproj = FindUpwards("Mutalaa.Api", "Mutalaa.Api.csproj");
        XDocument doc = XDocument.Load(csproj);

        string[] projectReferences = doc
            .Descendants("ProjectReference")
            .Select(e => (string?)e.Attribute("Include") ?? string.Empty)
            .ToArray();

        string reference = Assert.Single(projectReferences);
        Assert.EndsWith("Mutalaa.Infrastructure.csproj", reference, StringComparison.Ordinal);
        Assert.DoesNotContain("Mutalaa.Publisher", File.ReadAllText(csproj), StringComparison.Ordinal);
    }

    private static string FindUpwards(string folder, string file)
    {
        DirectoryInfo? dir = new(AppContext.BaseDirectory);
        while (dir is not null)
        {
            string candidate = Path.Combine(dir.FullName, folder, file);
            if (File.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        throw new FileNotFoundException($"{file} bulunamadi.");
    }
}
