using System.Reflection;
using Mutalaa.Domain;

namespace Mutalaa.Domain.Tests;

/// <summary>
/// Proje yapisi 2, kural 5: Mutalaa.Domain baska projeye ve altyapi paketine (EF Core, Npgsql, AWS) baglanmaz.
/// </summary>
public class ArchitectureTests
{
    private static readonly string[] ForbiddenPrefixes =
    [
        "Microsoft.EntityFrameworkCore",
        "Npgsql",
        "AWSSDK",
        "Amazon",
        "Mutalaa.",
    ];

    [Fact]
    public void Domain_assembly_has_at_least_one_type()
    {
        Assembly domain = typeof(DomainAssembly).Assembly;

        Assert.Equal(DomainAssembly.Name, domain.GetName().Name);
        Assert.NotEmpty(domain.GetTypes());
    }

    [Fact]
    public void Domain_assembly_references_no_infrastructure_or_project_assemblies()
    {
        Assembly domain = typeof(DomainAssembly).Assembly;

        string[] violations = domain
            .GetReferencedAssemblies()
            .Select(a => a.Name ?? string.Empty)
            .Where(name => ForbiddenPrefixes.Any(p => name.StartsWith(p, StringComparison.Ordinal)))
            .ToArray();

        Assert.Empty(violations);
    }

    [Fact]
    public void Domain_project_file_declares_no_package_or_project_references()
    {
        // Kullanilmayan bir basvuru derleme meta verisine yazilmaz; bu yuzden proje dosyasi da okunur.
        string csproj = FindUpwards("Mutalaa.Domain", "Mutalaa.Domain.csproj");
        string xml = File.ReadAllText(csproj);

        Assert.DoesNotContain("<PackageReference", xml, StringComparison.Ordinal);
        Assert.DoesNotContain("<ProjectReference", xml, StringComparison.Ordinal);
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
