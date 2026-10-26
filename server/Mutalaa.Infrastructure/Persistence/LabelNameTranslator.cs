using Npgsql;

namespace Mutalaa.Infrastructure.Persistence;

/// <summary>
/// C# enum uyesi adini ortak enum JSON etiketine ceviren Npgsql ad cevirmeni. Etiketler Domain'deki ToLabel eslemesinden gelir;
/// kurucuda kurulan ordinal sozluk kulturden bagimsizdir. [PgName] kullanilmaz. Ornekler statiktir (bkz. PostgresEnums).
/// </summary>
public sealed class LabelNameTranslator<T> : INpgsqlNameTranslator
    where T : struct, Enum
{
    private readonly Dictionary<string, string> _labels = new(StringComparer.Ordinal);

    public LabelNameTranslator(Func<T, string> toLabel)
    {
        ArgumentNullException.ThrowIfNull(toLabel);
        foreach (T value in Enum.GetValues<T>())
        {
            string name = Enum.GetName(value)
                ?? throw new InvalidOperationException($"{typeof(T).Name}: adsiz sayisal deger.");
            _labels.Add(name, toLabel(value));
        }
    }

    public string TranslateTypeName(string clrName) =>
        throw new NotSupportedException(
            $"{typeof(T).Name}: PostgreSQL tur adi acikca verilir (PostgresEnums); TranslateTypeName cagrilmamali.");

    public string TranslateMemberName(string clrName) =>
        _labels.TryGetValue(clrName, out string? label)
            ? label
            : throw new InvalidOperationException($"{typeof(T).Name}: '{clrName}' adli uye yok.");
}
