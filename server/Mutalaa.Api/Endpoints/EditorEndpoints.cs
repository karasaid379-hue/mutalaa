using Mutalaa.Api.Auth;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Editor kipi uclari (<c>Mutalaa:Features:Editor</c>). <c>/api/v1</c> grubu editor, admin ya da uzman ister (<c>Reviewer</c>); yazan uclar ve
/// editore ozgu okumalar <c>Editor</c>, admin uclari <c>Admin</c> politikasini ayrica ekler (hepsi birlikte aranir); giris ucu anonimdir.
/// Yeni uc grubu (kaynaklar, birimler, incelemeler, yayinlar, taramalar) buraya bir <c>Map*</c> cagrisi olarak eklenir.
/// </summary>
public static class EditorEndpoints
{
    public static RouteGroupBuilder MapEditorEndpoints(this RouteGroupBuilder v1)
    {
        ArgumentNullException.ThrowIfNull(v1);

        RouteGroupBuilder editor = v1.MapGroup(string.Empty);
        editor.RequireAuthorization(AuthPolicies.Reviewer);
        editor.ProducesProblem(StatusCodes.Status401Unauthorized);

        editor.MapAuthEndpoints();
        editor.MapUserEndpoints();
        editor.MapSourceEndpoints();
        editor.MapUnitEndpoints();
        editor.MapScanEndpoints();
        editor.MapReviewEndpoints();
        editor.MapLemmaEndpoints();
        editor.MapWordFixEndpoints();
        editor.MapReleaseEndpoints();

        return editor;
    }
}
