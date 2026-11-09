using Mutalaa.Api.Auth;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Editor kipi uclari (<c>Mutalaa:Features:Editor</c>). <c>/api/v1</c> grubu editor ya da admin ister; admin uclari kendi
/// gruplarinda <c>Admin</c> politikasini ekler (ikisi birlikte aranir); giris ucu anonimdir.
/// Yeni uc grubu (kaynaklar, birimler, incelemeler, yayinlar, taramalar) buraya bir <c>Map*</c> cagrisi olarak eklenir.
/// </summary>
public static class EditorEndpoints
{
    public static RouteGroupBuilder MapEditorEndpoints(this RouteGroupBuilder v1)
    {
        ArgumentNullException.ThrowIfNull(v1);

        RouteGroupBuilder editor = v1.MapGroup(string.Empty);
        editor.RequireAuthorization(AuthPolicies.Editor);
        editor.ProducesProblem(StatusCodes.Status401Unauthorized);

        editor.MapAuthEndpoints();
        editor.MapUserEndpoints();
        editor.MapSourceEndpoints();
        editor.MapUnitEndpoints();
        editor.MapScanEndpoints();
        editor.MapReviewEndpoints();

        return editor;
    }
}
