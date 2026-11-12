namespace Mutalaa.Infrastructure.Identity;

/// <summary>Editor paneli rolleri (Backend API 6).</summary>
public static class Roles
{
    public const string Editor = "editor";
    public const string Admin = "admin";

    /// <summary>Uzmana gonderilen incelemelerin karar vericisi (K-51 madde 2); editorden ayri denetim izi.</summary>
    public const string Uzman = "uzman";
}
