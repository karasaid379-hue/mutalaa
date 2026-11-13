using System.Text;
using System.Text.Json;
using Mutalaa.Domain.Anchors;

namespace Mutalaa.Domain.Links;

/// <summary>
/// Editorun duzenledigi baglanti degeri (<c>review.duzenlenen</c>): hedef capa, hedef araligi ve tur. Hepsi istege bagli, en az biri dolu.
/// <see cref="DstAnchor"/> birim capasi ya da <c>toUnitSpan</c>'in kabul ettigi capa olabilir (<c>q:2:255:3-7</c>, <c>meal:x:2:255@10-48</c>);
/// capanin kendi araligi varsa <see cref="DstSpan"/> verilemez. <see cref="DstSpan"/> yari acik <c>[bas, son)</c>dir.
/// </summary>
public readonly record struct LinkEditValue(string? DstAnchor, AnchorSpan? DstSpan, XrefType? Type);

/// <summary>Duzenlemenin uygulanmis hali: son tur, hedef birim, hedef araligi ve neyin degistigi.</summary>
public readonly record struct ResolvedLinkEdit(XrefType Type, AnchorRef DstAnchor, AnchorSpan? DstSpan, bool TypeChanged, bool DstUnitChanged, bool DstSpanChanged)
{
    public bool Changed => TypeChanged || DstUnitChanged || DstSpanChanged;
}

/// <summary>Hedef ucun karar anindaki olgulari (Domain veritabanina bakmaz; Api yukler).</summary>
/// <param name="UnitExists"><c>unit</c> satiri var mi.</param>
/// <param name="CodePointLength">Birim metninin kod noktasi sayisi (metin birimlerinde aralik siniri).</param>
/// <param name="WordCount">Ayetin <c>quran_word</c> sayisi (Kur'an ucunda kelime konumu siniri); bilinmiyorsa 0.</param>
/// <param name="ContentHash">Birimin <c>content_hash</c> degeri (kanit <c>dst_hash</c> onekini yenilemek icin).</param>
public readonly record struct LinkDstFacts(bool UnitExists, int CodePointLength, int WordCount, string? ContentHash);

/// <summary>Baglanti satirinin karar anindaki degerleri (duzeltme hesabi icin).</summary>
public readonly record struct LinkRowState(XrefType Type, AnchorRef SrcAnchor, AnchorSpan? SrcSpan, AnchorRef DstAnchor, AnchorSpan? DstSpan, XrefOrigin Origin, string Evidence);

/// <summary>Onaydan sonra xref satirina yazilacak duzeltilmis alanlar.</summary>
public readonly record struct LinkUpdate(XrefType Type, AnchorRef DstAnchor, AnchorSpan? DstSpan, XrefOrigin Origin, string Evidence);

/// <summary>Tur gecisleri (K-48 madde 2): yalniz <c>iktibas</c>, <c>atif</c> ve <c>ima</c> kendi aralarinda degisir.</summary>
public static class LinkTypeTransitions
{
    /// <summary>Editorun degistirebildigi turler (insan onayi isteyen, metin kaynakli turler).</summary>
    public static bool IsEditable(XrefType type) => type is XrefType.Atif or XrefType.Iktibas or XrefType.Ima;

    /// <summary>Gecis serbest mi: iki tur de duzenlenebilir olmali; ayni turde kalmak her zaman serbesttir. kok, lemma ve benzer_ayet degismez.</summary>
    public static bool IsAllowed(XrefType from, XrefType to) => from == to || (IsEditable(from) && IsEditable(to));
}

/// <summary>Duzenlenen baglanti degeri jsonb'si: <c>{dst_anchor?, dst_span?: [bas, son], type?}</c>; bilinmeyen alan ve yanlis tur 400.</summary>
public static class LinkEditPayload
{
    public const string DstAnchorKey = "dst_anchor";
    public const string DstSpanKey = "dst_span";
    public const string TypeKey = "type";

    /// <summary>Degeri okur; deger yoksa (null, JSON null) null. Bozuk deger <c>dogrulama</c> hatasidir.</summary>
    public static LinkEditValue? Read(string? json, string name)
    {
        if (string.IsNullOrWhiteSpace(json))
        {
            return null;
        }

        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(json);
        }
        catch (JsonException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli bir JSON degil.", e);
        }

        using (document)
        {
            JsonElement root = document.RootElement;
            if (root.ValueKind == JsonValueKind.Null)
            {
                return null;
            }

            if (root.ValueKind != JsonValueKind.Object)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bir JSON nesnesi olmali.");
            }

            string? dst = null;
            AnchorSpan? span = null;
            XrefType? type = null;
            foreach (JsonProperty property in root.EnumerateObject())
            {
                switch (property.Name)
                {
                    case DstAnchorKey:
                        dst = ReadString(property.Value, $"{name}.{DstAnchorKey}");
                        break;
                    case DstSpanKey:
                        span = ReadSpan(property.Value, $"{name}.{DstSpanKey}");
                        break;
                    case TypeKey:
                        type = ReadType(property.Value, $"{name}.{TypeKey}");
                        break;
                    default:
                        throw new DomainException(DomainErrorCodes.Dogrulama, $"{name}.{property.Name} bilinmeyen alan.");
                }
            }

            if (dst is null && span is null && type is null)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} en az bir alan icermeli (dst_anchor, dst_span ya da type).");
            }

            return new LinkEditValue(dst, span, type);
        }
    }

    /// <summary>Okunabilir mi (Api hedef olgularini yuklemeden once kullanir); bozuk deger false.</summary>
    public static bool TryRead(string? json, out LinkEditValue value)
    {
        try
        {
            LinkEditValue? read = Read(json, "duzenlenen");
            value = read ?? default;
            return read is not null;
        }
        catch (DomainException)
        {
            value = default;
            return false;
        }
    }

    public static string ToPayload(LinkEditValue value)
    {
        using MemoryStream stream = new();
        using (Utf8JsonWriter writer = new(stream))
        {
            writer.WriteStartObject();
            if (value.DstAnchor is not null)
            {
                writer.WriteString(DstAnchorKey, value.DstAnchor);
            }

            if (value.DstSpan is { } span)
            {
                writer.WriteStartArray(DstSpanKey);
                writer.WriteNumberValue(span.Start);
                writer.WriteNumberValue(span.End);
                writer.WriteEndArray();
            }

            if (value.Type is { } type)
            {
                writer.WriteString(TypeKey, type.ToLabel());
            }

            writer.WriteEndObject();
        }

        return Encoding.UTF8.GetString(stream.ToArray());
    }

    private static string ReadString(JsonElement element, string name)
    {
        if (element.ValueKind != JsonValueKind.String)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bir dizgi olmali.");
        }

        try
        {
            string? text = element.GetString();
            if (string.IsNullOrEmpty(text))
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} bos olamaz.");
            }

            return text;
        }
        catch (InvalidOperationException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli Unicode degil.", e);
        }
    }

    private static AnchorSpan? ReadSpan(JsonElement element, string name)
    {
        if (element.ValueKind == JsonValueKind.Null)
        {
            return null;
        }

        if (element.ValueKind != JsonValueKind.Array || element.GetArrayLength() != 2)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} iki tamsayidan olusan [bas, son) dizisi olmali.");
        }

        int[] parts = new int[2];
        int i = 0;
        foreach (JsonElement item in element.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.Number || !item.TryGetInt32(out parts[i]))
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} iki tamsayidan olusan [bas, son) dizisi olmali.");
            }

            i++;
        }

        return new AnchorSpan(parts[0], parts[1]);
    }

    private static XrefType ReadType(JsonElement element, string name)
    {
        if (element.ValueKind != JsonValueKind.String || !XrefTypeLabels.TryParseLabel(element.GetString(), out XrefType type))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, $"{name} gecerli bir baglanti turu olmali.");
        }

        return type;
    }
}

/// <summary>Baglanti duzeltmesi kurallari (saf islevler): tur gecisi, hedef capa ve hedef araligi.</summary>
public static class LinkEdits
{
    /// <summary>
    /// Duzenlemeyi mevcut satira uygular. Tur gecisi izinli degilse 422 <c>inceleme-desteklenmiyor</c>; hedef capa gecersiz, ayet araligi ya da cumle,
    /// capanin kendi araligiyla <c>dst_span</c> birlikte verilmis ya da yeni hedef insan onayi isteyen turde ayet ya da hadis degilse 400 <c>dogrulama</c>.
    /// Aralik sinirlari burada denetlenmez (<see cref="ValidateDstSpan"/>).
    /// </summary>
    public static ResolvedLinkEdit Resolve(XrefType currentType, AnchorRef currentDst, AnchorSpan? currentSpan, LinkEditValue edit)
    {
        ArgumentNullException.ThrowIfNull(currentDst);

        XrefType type = edit.Type ?? currentType;
        if (!LinkTypeTransitions.IsAllowed(currentType, type))
        {
            throw new DomainException(
                DomainErrorCodes.IncelemeDesteklenmiyor,
                $"'{currentType.ToLabel()}' turu '{type.ToLabel()}' turune degistirilemez; yalniz iktibas, atif ve ima kendi aralarinda degisir.");
        }

        AnchorRef unit = currentDst;
        AnchorSpan? span = edit.DstSpan ?? currentSpan;
        if (edit.DstAnchor is { } text)
        {
            (unit, span) = ResolveDstAnchor(text, edit.DstSpan);
        }

        // Yeni hedef verildiyse insan onayi isteyen turun hedefi ayet ya da hadis olmali (mevcut hedefe dokunulmayan duzeltmede sorulmaz).
        if (edit.DstAnchor is not null && LinkTypeTransitions.IsEditable(type) && unit.Kind is not (AnchorKind.Q or AnchorKind.H))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "atif, iktibas ve ima baglantisinin hedefi bir ayet ya da hadis olmali.");
        }

        return new ResolvedLinkEdit(type, unit, span, type != currentType, !unit.Equals(currentDst), span != currentSpan);
    }

    /// <summary>
    /// Hedef birim ucu: <c>dst_anchor</c> capasi birime ve (varsa) capanin kendi araligina cozulur. Kelime ve <c>@</c> araligi birim capasina
    /// gomulebilir (<c>toUnitSpan</c>); ayet araligi (<c>q:2:255-257</c>) ve cumle capasi uc olamaz.
    /// </summary>
    private static (AnchorRef Unit, AnchorSpan? Span) ResolveDstAnchor(string text, AnchorSpan? givenSpan)
    {
        if (!AnchorRef.TryParse(text, out AnchorRef? anchor))
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "dst_anchor gecerli bir capa degil.");
        }

        if (anchor.Kind == AnchorKind.Qa)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "dst_anchor bir ayet araligi olamaz; ayet baglantisi ayet basina kurulur.");
        }

        UnitSpan unitSpan;
        try
        {
            unitSpan = anchor.ToUnitSpan();
        }
        catch (InvalidOperationException e)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "dst_anchor cumle capasi olamaz; paragraf capasi ve aralik verilmeli.", e);
        }

        if (unitSpan.Span is not null && givenSpan is not null)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "dst_anchor kendi araligini tasiyorsa dst_span da verilemez.");
        }

        return (unitSpan.Unit, unitSpan.Span ?? givenSpan);
    }

    /// <summary>
    /// Hedef araligini hedef birimin olgularina gore denetler (yari acik, <c>bas &lt; son</c>): Kur'an ucunda kelime konumu
    /// <c>1 &lt;= bas &lt; son &lt;= kelime sayisi + 1</c>; metin biriminde kod noktasi <c>0 &lt;= bas &lt; son &lt;= metin uzunlugu</c>;
    /// konu ucunda aralik olamaz. Aralik varsa birim satiri bulunmali (400 <c>dogrulama</c>).
    /// </summary>
    public static void ValidateDstSpan(AnchorRef unit, AnchorSpan? span, LinkDstFacts facts)
    {
        ArgumentNullException.ThrowIfNull(unit);

        if (span is not { } range)
        {
            return;
        }

        if (unit.Kind == AnchorKind.Konu)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "konu ucunun araligi olamaz.");
        }

        if (range.Start >= range.End)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "aralik yari aciktir [bas, son) ve bas < son olmali.");
        }

        if (unit.Kind == AnchorKind.Q)
        {
            if (facts.WordCount <= 0)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "Ayetin kelime sayisi bilinmiyor (quran_word satiri yok); kelime araligi dogrulanamaz.");
            }

            if (range.Start < 1 || range.End > facts.WordCount + 1)
            {
                throw new DomainException(DomainErrorCodes.Dogrulama, "kelime araligi ayetin kelime sinirlari disinda (1 <= bas < son <= kelime sayisi + 1).");
            }

            return;
        }

        if (!facts.UnitExists)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "Hedef birim bulunamadi; metin araligi dogrulanamaz.");
        }

        if (range.Start < 0 || range.End > facts.CodePointLength)
        {
            throw new DomainException(DomainErrorCodes.Dogrulama, "aralik birim metninin kod noktasi sinirlari disinda (0 <= bas < son <= uzunluk).");
        }
    }
}
