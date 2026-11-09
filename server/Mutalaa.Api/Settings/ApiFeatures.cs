namespace Mutalaa.Api.Settings;

/// <summary>Ozellik bayraklari (Mutalaa:Features:*). Build() sonrasi app.Configuration uzerinden okunur.</summary>
public sealed record ApiFeatures(bool Editor, bool Public)
{
    public const string EditorKey = "Mutalaa:Features:Editor";
    public const string PublicKey = "Mutalaa:Features:Public";

    public static ApiFeatures From(IConfiguration configuration)
    {
        ArgumentNullException.ThrowIfNull(configuration);

        return new ApiFeatures(
            Editor: configuration.GetValue(EditorKey, true),
            Public: configuration.GetValue(PublicKey, false));
    }
}
