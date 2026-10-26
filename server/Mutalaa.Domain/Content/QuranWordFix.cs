using Mutalaa.Domain.Anchors;
using Mutalaa.Domain.Links;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.quran_word_fix satiri (Editoryal veritabani 5): QAC uzerine Mutalaa duzeltmesi.</summary>
public sealed class QuranWordFix
{
    /// <summary>Veritabani uuidv7() yazar.</summary>
    public Guid Id { get; set; }

    public required AnchorRef Anchor { get; set; }

    /// <summary>root_id, lemma_id, pos, features.</summary>
    public required string Field { get; set; }

    public string? QacValue { get; set; }

    public required string NewValue { get; set; }

    public required string Reason { get; set; }

    public XrefStatus Status { get; set; } = XrefStatus.Aday;

    public string? Editor { get; set; }

    /// <summary>UTC; veritabani now() yazar.</summary>
    public DateTime CreatedAt { get; set; }
}
