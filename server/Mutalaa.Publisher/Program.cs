using System.Globalization;
using Mutalaa.Publisher;

CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;
CultureInfo.CurrentCulture = CultureInfo.InvariantCulture;
CultureInfo.CurrentUICulture = CultureInfo.InvariantCulture;

using CancellationTokenSource cancellation = new();
Console.CancelKeyPress += (_, e) =>
{
    e.Cancel = true;
    cancellation.Cancel();
};

try
{
    return await PublisherApp.RunAsync(args, options: null, cancellation.Token);
}
catch (OperationCanceledException)
{
    return ExitCodes.Other;
}
catch (Exception ex)
{
    // Son savunma: yakalanmamis istisna -> 1. Ileti yazilir, yigin ve gizli deger yazilmaz.
    await Console.Error.WriteLineAsync($"Beklenmeyen hata: {ex.GetType().Name}: {ex.Message}");
    return ExitCodes.Other;
}
