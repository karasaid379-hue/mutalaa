using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Content;

/// <summary>icerik.audio_timing satiri (Editoryal veritabani 9.1): hafiz sesinde ayet zamanlamasi.</summary>
public sealed class AudioTiming
{
    public required string SourceId { get; set; }

    /// <summary>Ayet capasi: 'q:{sure}:{ayet}'.</summary>
    public required AnchorRef Anchor { get; set; }

    /// <summary>Paket ici yol: '002/255.mp3'.</summary>
    public required string File { get; set; }

    public required string FileSha256 { get; set; }

    public int StartMs { get; set; }

    public int EndMs { get; set; }

    /// <summary>jsonb: [[kelime, start_ms, end_ms], ...].</summary>
    public string? Words { get; set; }

    /// <summary>
    /// Zamanlama kaynagi (K-41 madde 3): 'qud' (QUD v4.0.0; ayet ve kelime), 'mp3quran' (MP3Quran ayat_timing; yedek ayet zamanlamasi)
    /// ya da 'editor'.
    /// </summary>
    public required string TimingSource { get; set; }

    public required string DataVersion { get; set; }
}
