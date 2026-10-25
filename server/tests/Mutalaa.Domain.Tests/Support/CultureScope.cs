using System.Globalization;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>
/// Testin kulturunu gecici olarak degistirir ve finally ile geri alir.
/// DefaultThreadCurrentCulture kullanilmaz: paralel testlerde yaris olur.
/// </summary>
internal static class CultureScope
{
    public static void Invariant(Action action) => Run(CultureInfo.InvariantCulture, action);

    public static void Turkish(Action action)
    {
        CultureInfo tr = CultureInfo.GetCultureInfo("tr-TR");
        Run(tr, () =>
        {
            Assert.Equal("tr-TR", CultureInfo.CurrentCulture.Name);
            action();
        });
    }

    private static void Run(CultureInfo culture, Action action)
    {
        CultureInfo previous = CultureInfo.CurrentCulture;
        CultureInfo previousUi = CultureInfo.CurrentUICulture;
        try
        {
            CultureInfo.CurrentCulture = culture;
            CultureInfo.CurrentUICulture = culture;
            action();
        }
        finally
        {
            CultureInfo.CurrentCulture = previous;
            CultureInfo.CurrentUICulture = previousUi;
        }
    }
}
