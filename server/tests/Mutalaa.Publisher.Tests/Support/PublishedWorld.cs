using Mutalaa.Api.Tests.Support;
using Mutalaa.Domain.Releases;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Tests.Support;

/// <summary>
/// Sinif fiksturu: fikstur veritabani uc derleme turuyle (dev, internal, public) gercek PostgreSQL ve gercek SeaweedFS uzerinde bir kez yayimlanir.
/// Buna dayanan testler YALNIZ OKUR (yayini degistiren testler kendi <see cref="EndToEndHarness"/> nesnesini acar).
/// </summary>
public sealed class PublishedWorld(PostgresFixture postgres, SeaweedFixture seaweed) : IAsyncLifetime
{
    internal EndToEndHarness Harness { get; private set; } = null!;

    internal Dictionary<BuildFlavor, ReleaseResult> Results { get; } = [];

    public async ValueTask InitializeAsync()
    {
        Harness = await EndToEndHarness.CreateAsync(postgres, seaweed);
        foreach (BuildFlavor flavor in new[] { BuildFlavor.Dev, BuildFlavor.Internal, BuildFlavor.Public })
        {
            ReleaseResult result = await Harness.PublishAsync(flavor);
            Results[flavor] = result;
            if (result.ExitCode != ExitCodes.Success)
            {
                throw new InvalidOperationException($"Fikstur yayini basarisiz ({flavor.ToLabel()}): {result.Message}\n{Harness.Out}\n{Harness.Error}");
            }
        }
    }

    public async ValueTask DisposeAsync()
    {
        if (Harness is not null)
        {
            await Harness.DisposeAsync();
        }
    }
}
