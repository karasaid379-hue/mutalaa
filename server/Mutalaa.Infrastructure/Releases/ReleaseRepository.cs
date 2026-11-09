using System.Data;
using System.Globalization;
using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Storage;
using Microsoft.Extensions.DependencyInjection;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Persistence;
using Npgsql;

namespace Mutalaa.Infrastructure.Releases;

/// <summary>Yeni yayin satiri istegi. Surum null ise <see cref="ReleaseVersion.Next"/> ile atanir.</summary>
public sealed record NewRelease(
    BuildFlavor Flavor,
    string? Surum,
    string Talep,
    string DataVersion,
    string Olusturan,
    int? KaynakReleaseId = null,
    string[]? Paketler = null,
    string? Notlar = null);

/// <summary>Verilen (surum, derleme) icin basarisiz olmayan bir satir zaten var.</summary>
public sealed class ReleaseConflictException : Exception
{
    public ReleaseConflictException(string message)
        : base(message)
    {
    }
}

/// <summary>
/// <see cref="ReleaseRepository.CreateAsync(NewRelease, bool, CancellationToken)"/> <c>requireNoOpen</c> ile cagrildi ve derleme turunde acik
/// (hazirlaniyor ya da dogrulandi) bir satir var; yeni satir acilmadi. <see cref="OpenRelease"/> mevcut acik satirdir (API 409 ile bildirir).
/// </summary>
public sealed class ReleaseInProgressException : Exception
{
    public ReleaseInProgressException(Release openRelease)
        : base(FormatMessage(openRelease))
    {
        OpenRelease = openRelease;
    }

    /// <summary>Derleme turunde halen acik olan satir.</summary>
    public Release OpenRelease { get; }

    private static string FormatMessage(Release? row)
    {
        ArgumentNullException.ThrowIfNull(row);
        return string.Create(
            CultureInfo.InvariantCulture,
            $"Derleme turunde acik yayin var: {row.Derleme.ToLabel()} {row.Surum} (durum: {row.Durum.ToLabel()}, id: {row.Id}).");
    }
}

/// <summary>
/// icerik.release satiri erisimi (Backend API 10.6; Yayinlayici ve A14). Her yontem kisa omurlu kendi baglamini (DI kapsami) acar: uzun
/// derleme sirasinda acik islem ya da baglam tutulmaz. Durum gecisleri <see cref="ReleaseTransitions"/> kuralina baglidir; gecersiz gecis
/// InvalidOperationException atar. Donen satirlar izlenmez (kopya); degisiklik icin ilgili Mark yontemi cagrilir.
/// </summary>
public sealed class ReleaseRepository(IServiceScopeFactory scopes, TimeProvider? clock = null)
{
    /// <summary>
    /// <see cref="CreateAsync(NewRelease, bool, CancellationToken)"/> danisma kilidi anahtari: "MUTALAA2" (ASCII) 64 bit tam sayi olarak.
    /// Yayinlayici kilidinden ("MUTALAA1", 0x4D5554414C414131) ayridir: o oturum boyunca tutulur, bu yalniz satir acma islemi boyunca.
    /// </summary>
    public const long CreateLockKey = 0x4D5554414C414132L;

    private const int MaxAssignAttempts = 3;

    private readonly TimeProvider _clock = clock ?? TimeProvider.System;

    public async Task<Release?> GetAsync(int id, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        return await db.Releases.AsNoTracking().SingleOrDefaultAsync(r => r.Id == id, cancellationToken);
    }

    /// <summary>(surum, derleme) icin basarisiz olmayan satir (kismi tekil dizin en cok bir tane garanti eder).</summary>
    public async Task<Release?> FindAsync(BuildFlavor flavor, string surum, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        return await db.Releases.AsNoTracking()
            .SingleOrDefaultAsync(r => r.Derleme == flavor && r.Surum == surum && r.Durum != ReleaseStatus.Basarisiz, cancellationToken);
    }

    /// <summary>Derleme turunde, istenen talep turunde (null ise herhangi) en son acik (hazirlaniyor ya da dogrulandi) satir; yoksa null.</summary>
    public async Task<Release?> FindOpenAsync(BuildFlavor flavor, string? talep, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        return await db.Releases.AsNoTracking()
            .Where(r => r.Derleme == flavor && (talep == null || r.Talep == talep)
                && (r.Durum == ReleaseStatus.Hazirlaniyor || r.Durum == ReleaseStatus.Dogrulandi))
            .OrderByDescending(r => r.Id)
            .FirstOrDefaultAsync(cancellationToken);
    }

    /// <summary>Derleme turunun en son yayinlandi satiri (yayinlandi_at, sonra id azalan); yoksa null.</summary>
    public Task<Release?> LatestPublishedAsync(BuildFlavor flavor, CancellationToken cancellationToken) =>
        LatestPublishedAsync(flavor, null, cancellationToken);

    /// <summary>Verilen kimlik haric (geri alma: yeni satir haric onceki guncel yayin).</summary>
    public async Task<Release?> LatestPublishedAsync(BuildFlavor flavor, int? excludingId, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        return await db.Releases.AsNoTracking()
            .Where(r => r.Derleme == flavor && r.Durum == ReleaseStatus.Yayinlandi && (excludingId == null || r.Id != excludingId))
            .OrderBy(r => r.YayinlandiAt == null)
            .ThenByDescending(r => r.YayinlandiAt)
            .ThenByDescending(r => r.Id)
            .FirstOrDefaultAsync(cancellationToken);
    }

    /// <summary>Bugunku ayin siradaki surumu: ayin basarisiz olmayan (butun derleme turlerinin) yayinlari uzerinden.</summary>
    public async Task<ReleaseVersion> NextVersionAsync(CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        return await NextVersionAsync(db, cancellationToken);
    }

    /// <summary>
    /// Satiri <c>hazirlaniyor</c> olarak acar (<see cref="CreateAsync(NewRelease, bool, CancellationToken)"/>, <c>requireNoOpen = false</c>).
    /// </summary>
    public Task<Release> CreateAsync(NewRelease request, CancellationToken cancellationToken) =>
        CreateAsync(request, requireNoOpen: false, cancellationToken);

    /// <summary>
    /// Satiri <c>hazirlaniyor</c> olarak acar. Surum verilmisse ve o (surum, derleme) icin basarisiz olmayan satir varsa
    /// <see cref="ReleaseConflictException"/>; verilmemisse atama yarisinda (tekil dizin ihlali) birkac kez yeniden dener.
    /// Her deneme kendi <c>ReadCommitted</c> isleminde <c>pg_advisory_xact_lock</c> alir (<see cref="CreateLockKey"/>; Yayinlayici kilidinden
    /// "MUTALAA1" Yayinlayici kilidinden farkli): satir acan cagrilar sirayla calisir. <paramref name="requireNoOpen"/> true ise ayni
    /// islemde derleme turunde acik (hazirlaniyor ya da dogrulandi) satir aranir; varsa <see cref="ReleaseInProgressException"/> atilir ve satir
    /// acilmaz.
    /// </summary>
    public async Task<Release> CreateAsync(NewRelease request, bool requireNoOpen, CancellationToken cancellationToken)
    {
        ArgumentNullException.ThrowIfNull(request);
        if (!ReleaseRequests.IsValid(request.Talep))
        {
            throw new ArgumentException($"Gecersiz talep: {request.Talep}", nameof(request));
        }

        if (request.Surum is not null && !ReleaseVersion.TryParse(request.Surum, out _))
        {
            throw new ArgumentException($"Gecersiz surum: {request.Surum}", nameof(request));
        }

        for (int attempt = 1; ; attempt++)
        {
            await using AsyncServiceScope scope = scopes.CreateAsyncScope();
            IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
            await using IDbContextTransaction transaction = await db.Database.BeginTransactionAsync(IsolationLevel.ReadCommitted, cancellationToken);
            await AcquireCreateLockAsync(db, transaction, cancellationToken);

            if (requireNoOpen)
            {
                Release? open = await db.Releases.AsNoTracking()
                    .Where(r => r.Derleme == request.Flavor && (r.Durum == ReleaseStatus.Hazirlaniyor || r.Durum == ReleaseStatus.Dogrulandi))
                    .OrderByDescending(r => r.Id)
                    .FirstOrDefaultAsync(cancellationToken);
                if (open is not null)
                {
                    throw new ReleaseInProgressException(open);
                }
            }

            string surum = request.Surum ?? (await NextVersionAsync(db, cancellationToken)).ToString();
            Release row = new()
            {
                Surum = surum,
                Derleme = request.Flavor,
                DataVersion = request.DataVersion,
                Olusturan = request.Olusturan,
                Talep = request.Talep,
                KaynakReleaseId = request.KaynakReleaseId,
                Paketler = request.Paketler,
                Notlar = request.Notlar,
            };
            db.Releases.Add(row);
            try
            {
                await db.SaveChangesAsync(cancellationToken);
                await transaction.CommitAsync(cancellationToken);
                return row;
            }
            catch (DbUpdateException ex) when (ex.InnerException is PostgresException { SqlState: PostgresErrorCodes.UniqueViolation })
            {
                // Islem geri alinir (using); yeniden denemede yeni islem ve yeni kapsam acilir.
                if (request.Surum is not null)
                {
                    throw new ReleaseConflictException($"Surum {request.Surum} ({request.Flavor.ToLabel()}) icin basarisiz olmayan bir yayin zaten var.");
                }

                if (attempt >= MaxAssignAttempts)
                {
                    throw;
                }
            }
        }
    }

    /// <summary>hazirlaniyor -> dogrulandi: imzali manifest, kapi raporu, ozetler ve paket listesi yazilir.</summary>
    public Task MarkVerifiedAsync(int id, string manifestJson, string gateReportJson, string digestsJson, string[]? packs, CancellationToken cancellationToken) =>
        UpdateAsync(
            id,
            ReleaseStatus.Dogrulandi,
            row =>
            {
                row.Manifest = manifestJson;
                row.KapiRaporu = gateReportJson;
                row.Ozetler = digestsJson;
                row.Paketler = packs;
            },
            cancellationToken);

    /// <summary>dogrulandi -> yayinlandi: yayinlandi_at saat damgasi yazilir.</summary>
    public Task MarkPublishedAsync(int id, CancellationToken cancellationToken) =>
        UpdateAsync(id, ReleaseStatus.Yayinlandi, row => row.YayinlandiAt = _clock.GetUtcNow().UtcDateTime, cancellationToken);

    /// <summary>Acik satiri basarisiz isaretler; kapi raporu (hata ayrintisi dahil) yazilir.</summary>
    public Task MarkFailedAsync(int id, string gateReportJson, CancellationToken cancellationToken) =>
        UpdateAsync(id, ReleaseStatus.Basarisiz, row => row.KapiRaporu = gateReportJson, cancellationToken);

    /// <summary>yayinlandi -> geri_cekildi (geri alma: onceki guncel yayin).</summary>
    public Task MarkWithdrawnAsync(int id, CancellationToken cancellationToken) =>
        UpdateAsync(id, ReleaseStatus.GeriCekildi, _ => { }, cancellationToken);

    /// <summary>
    /// watch: bekleyen (hazirlaniyor) en eski satiri kisa bir islemde <c>FOR UPDATE SKIP LOCKED</c> ile alir ve islemi hemen kapatir; asil
    /// dislama danisma kilididir (PublisherLock). <paramref name="excluding"/> bu turda zaten denenen satirlari atlar. Satir yoksa null.
    /// </summary>
    public async Task<Release?> ClaimNextPendingAsync(IReadOnlyCollection<int>? excluding, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        await using IDbContextTransaction transaction = await db.Database.BeginTransactionAsync(cancellationToken);

        int? id;
        await using (NpgsqlCommand command = (NpgsqlCommand)db.Database.GetDbConnection().CreateCommand())
        {
            command.Transaction = (NpgsqlTransaction)transaction.GetDbTransaction();
            command.CommandText =
                "SELECT id FROM icerik.release WHERE durum = 'hazirlaniyor' AND id <> ALL(@skip) ORDER BY id LIMIT 1 FOR UPDATE SKIP LOCKED";
            command.Parameters.AddWithValue("skip", excluding is null ? Array.Empty<int>() : excluding.ToArray());
            object? scalar = await command.ExecuteScalarAsync(cancellationToken);
            id = scalar is null or DBNull ? null : Convert.ToInt32(scalar, CultureInfo.InvariantCulture);
        }

        Release? row = id is null ? null : await db.Releases.AsNoTracking().SingleOrDefaultAsync(r => r.Id == id.Value, cancellationToken);
        await transaction.CommitAsync(cancellationToken);
        return row;
    }

    private static async Task AcquireCreateLockAsync(IcerikDbContext db, IDbContextTransaction transaction, CancellationToken cancellationToken)
    {
        await using NpgsqlCommand command = (NpgsqlCommand)db.Database.GetDbConnection().CreateCommand();
        command.Transaction = (NpgsqlTransaction)transaction.GetDbTransaction();
        command.CommandText = "SELECT pg_advisory_xact_lock(@key)";
        command.Parameters.AddWithValue("key", CreateLockKey);
        await command.ExecuteNonQueryAsync(cancellationToken);
    }

    private async Task UpdateAsync(int id, ReleaseStatus target, Action<Release> mutate, CancellationToken cancellationToken)
    {
        await using AsyncServiceScope scope = scopes.CreateAsyncScope();
        IcerikDbContext db = scope.ServiceProvider.GetRequiredService<IcerikDbContext>();
        Release row = await db.Releases.SingleOrDefaultAsync(r => r.Id == id, cancellationToken)
            ?? throw new InvalidOperationException($"Yayin satiri yok: {id.ToString(CultureInfo.InvariantCulture)}.");

        ReleaseTransitions.Require(row.Durum, target);
        row.Durum = target;
        mutate(row);
        await db.SaveChangesAsync(cancellationToken);
    }

    private async Task<ReleaseVersion> NextVersionAsync(IcerikDbContext db, CancellationToken cancellationToken)
    {
        DateOnly today = DateOnly.FromDateTime(_clock.GetUtcNow().UtcDateTime);
        string pattern = string.Create(CultureInfo.InvariantCulture, $"{today.Year:D4}.{today.Month}.%");
        List<string> existing = await db.Releases.AsNoTracking()
            .Where(r => r.Durum != ReleaseStatus.Basarisiz && EF.Functions.Like(r.Surum, pattern))
            .Select(r => r.Surum)
            .ToListAsync(cancellationToken);
        return ReleaseVersion.Next(today, existing);
    }
}
