using Mutalaa.Domain.Content;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Reviews;

/// <summary>
/// <c>dogrulanmis</c> ve <c>ikinci_onay_bekliyor</c> turetimleri (Editoryal veritabani 8, K-37): ikisi de saklanmaz.
/// </summary>
public static class ReviewVerification
{
    /// <summary>
    /// Hedef onayli mi. Durum sutunlu hedeflerde <c>status = onayli</c> (unit'te <c>metin_durumu = onayli</c>);
    /// durum sutunu olmayan hedeflerde (source, root, tr_root_index, tr_form, page_map, ayah_box, audio_timing) ilgili
    /// review satirinin durumu <c>onaylandi</c> ise.
    /// </summary>
    /// <exception cref="DomainException"><c>dogrulama</c>: bilinmeyen hedef_tablo.</exception>
    public static bool IsVerified(string? hedefTablo, XrefStatus? status, TextStatus? metinDurumu, ReviewStatus reviewDurum)
    {
        if (!ReviewTargets.IsKnown(hedefTablo))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Bilinmeyen hedef_tablo.");
        }

        if (string.Equals(hedefTablo, ReviewTargets.Unit, StringComparison.Ordinal))
        {
            return metinDurumu == TextStatus.Onayli;
        }

        return ReviewTargets.HasStatusColumn(hedefTablo)
            ? status == XrefStatus.Onayli
            : reviewDurum == ReviewStatus.Onaylandi;
    }

    /// <summary>Meal ya da tefsir metni, ilk onay verilmis (Inceleyen dolu), ikinci onay yok ve kayit acik.</summary>
    public static bool IsSecondApprovalPending(Review review, UnitKind kind)
    {
        ArgumentNullException.ThrowIfNull(review);
        return ReviewDecisions.RequiresSecondApproval(review.HedefTablo, review.Alan, kind)
            && !string.IsNullOrEmpty(review.Inceleyen)
            && string.IsNullOrEmpty(review.IkinciInceleyen)
            && review.Durum == ReviewStatus.Acik;
    }
}
