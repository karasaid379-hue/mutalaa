using System.Globalization;

namespace Mutalaa.Api.Tests.Support;

/// <summary>
/// Async eylemi tr-TR kulturunde calistirir (CultureScope.Turkish yalniz senkron eylem alir; async testte engelleme xUnit1031'dir).
/// Kultur yalniz bu mantiksal akista degisir ve finally ile geri alinir; DefaultThreadCurrentCulture dokunulmaz.
/// </summary>
internal static class AsyncCultureScope
{
    public static async Task TurkishAsync(Func<Task> action)
    {
        CultureInfo previous = CultureInfo.CurrentCulture;
        CultureInfo previousUi = CultureInfo.CurrentUICulture;
        CultureInfo turkish = CultureInfo.GetCultureInfo("tr-TR");
        try
        {
            CultureInfo.CurrentCulture = turkish;
            CultureInfo.CurrentUICulture = turkish;
            Assert.Equal("tr-TR", CultureInfo.CurrentCulture.Name);
            await action();
        }
        finally
        {
            CultureInfo.CurrentCulture = previous;
            CultureInfo.CurrentUICulture = previousUi;
        }
    }
}
