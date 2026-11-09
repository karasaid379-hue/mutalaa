namespace Mutalaa.Domain;

/// <summary>
/// Domain kural ihlali. <see cref="Code"/> Backend API hata kodudur (<see cref="DomainErrorCodes"/>); HTTP durumuna cevirme
/// Api katmaninin isidir, Domain HTTP bilmez.
/// </summary>
public sealed class DomainException : Exception
{
    public DomainException(string code, string message)
        : base(message)
    {
        ArgumentException.ThrowIfNullOrEmpty(code);
        Code = code;
    }

    public DomainException(string code, string message, Exception innerException)
        : base(message, innerException)
    {
        ArgumentException.ThrowIfNullOrEmpty(code);
        Code = code;
    }

    /// <summary>Kebab-case hata kodu (<see cref="DomainErrorCodes"/>).</summary>
    public string Code { get; }
}
