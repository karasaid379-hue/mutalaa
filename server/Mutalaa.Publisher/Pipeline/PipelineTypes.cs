using Mutalaa.Domain.Releases;

namespace Mutalaa.Publisher.Pipeline;

/// <summary>Bir pakette yapilan is: yeni yazildi ya da onceki surumden tasindi (ozet ayniydi).</summary>
public sealed record PackBuild(string PackId, string Version, string Sha256, long SizeBytes, bool Carried, string ContentDigest);

/// <summary>Bir komutun sonucu: cikis kodu, ilgili yayin ve kullaniciya yazilacak kisa ileti. Iletide gizli deger bulunmaz.</summary>
public sealed record ReleaseResult(int ExitCode, string? Surum, ReleaseStatus? Status, string Message, IReadOnlyList<PackBuild>? Packs = null)
{
    public bool Success => ExitCode == ExitCodes.Success;

    public static ReleaseResult Ok(string? surum, ReleaseStatus? status, string message, IReadOnlyList<PackBuild>? packs = null) =>
        new(ExitCodes.Success, surum, status, message, packs);

    public static ReleaseResult Fail(int exitCode, string message, string? surum = null, ReleaseStatus? status = null) =>
        new(exitCode, surum, status, message);
}

/// <summary>publish ve build istegi. ReleaseId verilirse (watch) o satir surdurulur.</summary>
public sealed record PublishRequest(
    BuildFlavor Flavor,
    IReadOnlyList<string> Packs,
    bool DryRun = false,
    string? Version = null,
    string? OutDir = null,
    bool StopAtVerified = false,
    int? ReleaseId = null,
    string? Notes = null);

public sealed record UploadRequest(BuildFlavor Flavor, string? Surum = null, string? OutDir = null);

/// <summary>promote istegi: Surum verilmezse en son yayinlandi internal yayin; ReleaseId verilirse (watch) o terfi satiri surdurulur.</summary>
public sealed record PromoteRequest(
    string? Surum = null,
    IReadOnlyList<string>? Packs = null,
    bool DryRun = false,
    string? OutDir = null,
    int? ReleaseId = null,
    string? Notes = null);

public sealed record RollbackRequest(BuildFlavor Flavor, string To, string? OutDir = null, int? ReleaseId = null, string? Notes = null);
