using Mutalaa.Api.Lemmas;
using Mutalaa.Api.Problems;
using Mutalaa.Infrastructure.Persistence;

namespace Mutalaa.Api.Endpoints;

/// <summary>Lemmanin kendisi: kimlik, yazi, dil, durum, koken, sikligi ve kok baglantisi.</summary>
public sealed record LemmaInfo(
    int Id,
    string Text,
    string Lang,
    string Status,
    string? Origin,
    int Occurrences,
    int? RootId,
    string? QacRef,
    bool EtymologicalOnly);

/// <summary>Lemmanin koku (root satiri); kokusuz lemmada yanitta <c>kok</c> null'dir.</summary>
public sealed record LemmaRootInfo(
    int Id,
    string Letters,
    string? LettersBw,
    int Occurrences,
    int AyahCount,
    float? IdfQ,
    string? KokAnlami);

/// <summary>Sozcuk turu (quran_word.pos) basina kelime sayisi; pos bos olan kelimeler tek grup olarak <c>pos = null</c> doner.</summary>
public sealed record LemmaPosCount(string? Pos, int Sayi);

/// <summary>Gercek siklik (quran_word.lemma_id uzerinden): kelime sayisi ve gectigi ayet sayisi.</summary>
public sealed record LemmaFrequency(int Kelime, int Ayet);

/// <summary>lemma_dalga satiri (K-50 madde 7): dalga 0..4 ve dalga icindeki sira.</summary>
public sealed record LemmaWaveInfo(int Dalga, int Sira);

/// <summary>Ayni kokten baska bir lemmanin onayli kisa anlami.</summary>
public sealed record LemmaSiblingGloss(int LemmaId, string Text, string AnlamKisa, int Occurrences);

/// <summary>meal:elmalili birimi: metin ve metin_durumu (taslak, incelemede, onayli ...).</summary>
public sealed record LemmaKwicMeal(string Capa, string Metin, string MetinDurumu);

/// <summary>
/// Bir gecis ornegi. <c>sol</c>, <c>kelime</c> ve <c>sag</c> Tanzil ayet metninden kod noktasi ofsetiyle (quran_word.char_start ve
/// char_end) dilimlenir; ayet metni yoksa ya da ofset metne uymuyorsa uc alan da null'dir. <c>meal</c> yalniz Elmalili birimi varsa dolu.
/// </summary>
public sealed record LemmaKwicItem(string KelimeCapa, string AyetCapa, string? Sol, string? Kelime, string? Sag, LemmaKwicMeal? Meal);

/// <summary>Salt okunur lemma karti (BC-56 A17 yarisi): kok, tur dagilimi, siklik, dalga, ayni kokun onayli anlamlari ve KWIC.</summary>
public sealed record LemmaDetailResponse(
    LemmaInfo Lemma,
    LemmaRootInfo? Kok,
    IReadOnlyList<LemmaPosCount> TurDagilimi,
    LemmaFrequency Siklik,
    LemmaWaveInfo? Dalga,
    IReadOnlyList<LemmaSiblingGloss> AyniKokAnlamlari,
    IReadOnlyList<LemmaKwicItem> Kwic);

/// <summary>Lemma ucu (K-50, BC-56): salt okunur; yetki editor ya da admin. GET disindaki yontemler eslesmez (405).</summary>
public static class LemmaEndpoints
{
    public static RouteGroupBuilder MapLemmaEndpoints(this RouteGroupBuilder editor)
    {
        ArgumentNullException.ThrowIfNull(editor);

        RouteGroupBuilder lemmas = editor.MapGroup("/lemmas").WithTags("lemmas");

        lemmas.MapGet("/{id:int}", GetAsync)
            .WithName("getLemma")
            .WithSummary("Lemma kartı: kök, sözcük türü dağılımı, sıklık, dalga ve sıra, aynı kökün onaylı anlamları ve KWIC örnekleri.")
            .Produces<LemmaDetailResponse>()
            .ProducesProblem(StatusCodes.Status404NotFound);

        return editor;
    }

    private static async Task<IResult> GetAsync(int id, IcerikDbContext db, CancellationToken cancellationToken)
    {
        LemmaDetailResponse? response = await LemmaQueries.GetAsync(db, id, cancellationToken);
        return response is null
            ? ApiProblem.Create(StatusCodes.Status404NotFound, ProblemCodes.Bulunamadi, "Lemma bulunamadı.")
            : TypedResults.Ok(response);
    }
}
