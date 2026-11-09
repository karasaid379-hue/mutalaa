namespace Mutalaa.Infrastructure.Packs;

/// <summary>Paket yazimi basarisiz (FTS5 yok, DDL hatasi, user_version uyusmazligi, oz denetim kirmizi, dosya tasinamadi).</summary>
public sealed class PackWriteException : Exception
{
    public PackWriteException(string message)
        : base(message)
    {
    }

    /// <summary>Oz denetimi kirmizi biten yazim: rapor ekte.</summary>
    public PackWriteException(string message, PackSelfCheckReport report)
        : base(message)
    {
        Report = report;
    }

    public PackWriteException(string message, Exception innerException)
        : base(message, innerException)
    {
    }

    /// <summary>Oz denetim raporu (oz denetim kirmizi bittiyse; aksi hâlde null).</summary>
    public PackSelfCheckReport? Report { get; }
}

/// <summary>Paket icerigi toplanamadi (paket kapidan girmemis, katalogda yok ya da girdi tutarsiz).</summary>
public sealed class PackAssemblyException : Exception
{
    public PackAssemblyException(string message)
        : base(message)
    {
    }
}

/// <summary>paketler.json okunamadi ya da bir paket kimligi tam bir ture eslesmedi.</summary>
public sealed class PackDefinitionException : Exception
{
    public PackDefinitionException(string message)
        : base(message)
    {
    }

    public PackDefinitionException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}
