using Mutalaa.Api.Problems;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Api.Endpoints;

/// <summary>
/// Yol parcasindaki capayi birim duzeyinde dogrular (K-26): gramer hatasi 400 <c>capa-gecersiz</c> (hata kodu adi
/// <c>capa_hata_kodu</c> uzantisinda), kelime, '@' araligi, cumle, ayet araligi ve konu capasi birim degildir (yine 400).
/// </summary>
internal static class UnitAnchors
{
    public const string ErrorCodeKey = "capa_hata_kodu";

    public static (AnchorRef? Anchor, IResult? Problem) Parse(string? text)
    {
        AnchorRef anchor;
        try
        {
            anchor = AnchorRef.Parse(text ?? string.Empty);
        }
        catch (AnchorException e)
        {
            return (null, ApiProblem.Create(
                StatusCodes.Status400BadRequest,
                ProblemCodes.CapaGecersiz,
                "Çapa geçersiz.",
                new Dictionary<string, object?> { [ErrorCodeKey] = e.CodeName }));
        }

        // Birim duzeyi: '@' araligi, kelime, cumle, ayet araligi ve konu capasi birim degildir.
        bool unitLevel = anchor.Span is null
            && anchor.Kind is not (AnchorKind.Qa or AnchorKind.Konu)
            && anchor.UnitOf().Equals(anchor);
        if (!unitLevel)
        {
            return (null, ApiProblem.Create(
                StatusCodes.Status400BadRequest,
                ProblemCodes.CapaGecersiz,
                "Çapa birim düzeyinde olmalı (kelime, aralık, cümle ve konu çapası birim değildir)."));
        }

        return (anchor, null);
    }
}
