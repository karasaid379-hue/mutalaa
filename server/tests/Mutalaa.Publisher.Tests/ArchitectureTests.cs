using System.Reflection;
using System.Xml.Linq;

namespace Mutalaa.Publisher.Tests;

/// <summary>
/// Proje yapisi 2: Api -> Infrastructure -> Domain, Publisher -> Infrastructure; Mutalaa.Api ile Mutalaa.Publisher birbirine baglanmaz.
/// </summary>
public class ArchitectureTests
{
    [Fact]
    public void Publisher_assembly_does_not_reference_api()
    {
        Assembly publisher = Assembly.Load("Mutalaa.Publisher");

        Assert.DoesNotContain(
            publisher.GetReferencedAssemblies(),
            a => string.Equals(a.Name, "Mutalaa.Api", StringComparison.Ordinal));
    }

    [Fact]
    public void Publisher_project_file_references_only_infrastructure()
    {
        // Kullanilmayan bir basvuru derleme meta verisine yazilmaz; bu yuzden proje dosyasi da okunur.
        string csproj = FindUpwards("Mutalaa.Publisher", "Mutalaa.Publisher.csproj");
        XDocument doc = XDocument.Load(csproj);

        string[] projectReferences = doc
            .Descendants("ProjectReference")
            .Select(e => (string?)e.Attribute("Include") ?? string.Empty)
            .ToArray();

        string reference = Assert.Single(projectReferences);
        Assert.EndsWith("Mutalaa.Infrastructure.csproj", reference, StringComparison.Ordinal);
        Assert.DoesNotContain("Mutalaa.Api", File.ReadAllText(csproj), StringComparison.Ordinal);
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
