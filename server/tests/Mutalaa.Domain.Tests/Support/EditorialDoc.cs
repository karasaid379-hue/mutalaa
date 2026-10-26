using System.Globalization;
using System.Text;
using System.Text.RegularExpressions;

namespace Mutalaa.Domain.Tests.Support;

/// <summary>DDL'deki bir sutun. Default ham SQL ifadesidir ('govde', 0, false, now()); yoksa null.</summary>
internal sealed record DdlColumn(string Name, string Type, bool NotNull, string? Default, bool Identity, bool Generated);

/// <summary>DDL'deki bir tablo; sutunlar bildirim sirasiyla.</summary>
internal sealed record DdlTable(string Name, IReadOnlyList<DdlColumn> Columns);

/// <summary>Tablodaki bir CHECK; Name yalniz "CONSTRAINT ad CHECK (...)" yazildiysa dolu, Expression bosluklari teke indirilmis ham ifadedir.</summary>
internal sealed record DdlCheck(string Table, string? Name, string Expression);

/// <summary>Tek sutunlu yabanci anahtar: Table.Column -> ReferencedTable.ReferencedColumn.</summary>
internal sealed record DdlReference(string Table, string Column, string ReferencedTable, string ReferencedColumn);

/// <summary>Belge DDL'inden ayristirilan CHECK ve yabanci anahtar listesi.</summary>
internal sealed record DdlConstraints(IReadOnlyList<DdlCheck> Checks, IReadOnlyList<DdlReference> References);

/// <summary>
/// docs/03-veri/02-editoryal-veritabani.md (DDL'in tek dogruluk kaynagi) okuyucusu ve kucuk bir DDL ayristiricisi.
/// Yalniz belgede kullanilan bicimleri tanir; tanimadigi bicimde acik hata verir, sessizce atlamaz.
/// </summary>
internal static partial class EditorialDoc
{
    public const string RelativePath = "docs/03-veri/02-editoryal-veritabani.md";

    private static readonly string[] TableConstraintKeywords = ["UNIQUE", "CHECK", "PRIMARY KEY", "CONSTRAINT", "FOREIGN KEY", "EXCLUDE"];

    /// <summary>Belgeyi depo kokunden bulur ve okur (kati UTF-8, BOM'suz; satir sonu LF'ye cevrilir).</summary>
    public static string Read()
    {
        string path = FindUpwards(RelativePath);
        string text = new UTF8Encoding(encoderShouldEmitUTF8Identifier: false, throwOnInvalidBytes: true)
            .GetString(File.ReadAllBytes(path));
        if (text.Length > 0 && text[0] == (char)0xFEFF)
        {
            throw new InvalidDataException($"Belgede BOM var: {path}");
        }

        return text.Replace("\r\n", "\n", StringComparison.Ordinal);
    }

    /// <summary>"## {no}. " ile baslayan bolumu bir sonraki "## " basligina kadar dondurur.</summary>
    public static string Section(string markdown, int number)
    {
        string prefix = "## " + number.ToString(CultureInfo.InvariantCulture) + ". ";
        string[] lines = markdown.Split('\n');
        int start = Array.FindIndex(lines, l => l.StartsWith(prefix, StringComparison.Ordinal));
        if (start < 0)
        {
            throw new InvalidDataException($"Belgede '{prefix}' basligi yok.");
        }

        int end = Array.FindIndex(lines, start + 1, l => l.StartsWith("## ", StringComparison.Ordinal));
        return string.Join('\n', lines[start..(end < 0 ? lines.Length : end)]);
    }

    /// <summary>Markdown icindeki ```sql bloklarinin birlesimi.</summary>
    public static string SqlBlocks(string markdown)
    {
        StringBuilder sql = new();
        bool inside = false;
        int blocks = 0;
        foreach (string line in markdown.Split('\n'))
        {
            if (!inside && string.Equals(line.TrimEnd(), "```sql", StringComparison.Ordinal))
            {
                inside = true;
                blocks++;
            }
            else if (inside && string.Equals(line.TrimEnd(), "```", StringComparison.Ordinal))
            {
                inside = false;
            }
            else if (inside)
            {
                sql.Append(line).Append('\n');
            }
        }

        if (inside)
        {
            throw new InvalidDataException("Kapanmamis ```sql blogu.");
        }

        if (blocks == 0)
        {
            throw new InvalidDataException("```sql blogu yok.");
        }

        return sql.ToString();
    }

    /// <summary>Tirnak disindaki "--" yorumlarini satir sonuna kadar siler.</summary>
    public static string StripComments(string sql)
    {
        StringBuilder result = new(sql.Length);
        foreach (string line in sql.Split('\n'))
        {
            bool quoted = false;
            int cut = line.Length;
            for (int i = 0; i < line.Length; i++)
            {
                if (line[i] == '\'')
                {
                    quoted = !quoted;
                }
                else if (!quoted && line[i] == '-' && i + 1 < line.Length && line[i + 1] == '-')
                {
                    cut = i;
                    break;
                }
            }

            result.Append(line, 0, cut).Append('\n');
        }

        return result.ToString();
    }

    /// <summary>
    /// CREATE TYPE ad AS ENUM ('a','b', ...); ifadelerini (cok satirli) bildirim sirasiyla ayristirir.
    /// Etiket listesinde tirnakli etiketten baska bir sey varsa ya da ayristirilamayan bir CREATE TYPE kalirsa hata verir.
    /// </summary>
    public static IReadOnlyList<KeyValuePair<string, string[]>> ParseEnumTypes(string sql)
    {
        string clean = StripComments(sql);
        List<KeyValuePair<string, string[]>> result = [];
        foreach (Match m in EnumTypeRegex().Matches(clean))
        {
            string[] labels = [.. m.Groups["labels"].Value.Split(',').Select(item =>
            {
                Match label = EnumLabelRegex().Match(item.Trim());
                return label.Success
                    ? label.Groups["label"].Value
                    : throw new InvalidDataException($"{m.Groups["name"].Value}: etiket ayristirilamadi: '{item.Trim()}'");
            })];
            result.Add(new(m.Groups["name"].Value, labels));
        }

        int declared = CreateTypeRegex().Count(clean);
        if (declared != result.Count)
        {
            throw new InvalidDataException($"{declared} CREATE TYPE var, {result.Count} tanesi ayristirildi.");
        }

        return result;
    }

    /// <summary>CREATE TABLE ifadelerini (sutun adi, tur, NOT NULL, DEFAULT, kimlik, uretilen) bildirim sirasiyla ayristirir.</summary>
    public static IReadOnlyList<DdlTable> ParseTables(string sql)
    {
        string clean = StripComments(sql);
        List<DdlTable> tables = [];
        foreach (Match m in CreateTableRegex().Matches(clean))
        {
            string name = m.Groups["name"].Value;
            string body = ReadParenthesized(clean, m.Index + m.Length - 1, name);
            List<DdlColumn> columns = [];
            HashSet<string> primaryKey = new(StringComparer.Ordinal);
            foreach (string raw in SplitTopLevel(body))
            {
                string item = WhitespaceRegex().Replace(raw, " ").Trim();
                if (item.Length == 0)
                {
                    throw new InvalidDataException($"{name}: bos tanim (fazladan virgul).");
                }

                if (TableConstraintKeywords.Any(k => item.StartsWith(k + " ", StringComparison.Ordinal) || item.StartsWith(k + "(", StringComparison.Ordinal)))
                {
                    Match pk = TablePrimaryKeyRegex().Match(item);
                    if (pk.Success)
                    {
                        foreach (string col in pk.Groups["cols"].Value.Split(','))
                        {
                            primaryKey.Add(col.Trim());
                        }
                    }

                    continue;
                }

                columns.Add(ParseColumn(name, item));
            }

            foreach (string col in primaryKey)
            {
                if (!columns.Any(c => string.Equals(c.Name, col, StringComparison.Ordinal)))
                {
                    throw new InvalidDataException($"{name}: PRIMARY KEY sutunu yok: {col}");
                }
            }

            tables.Add(new DdlTable(
                name,
                [.. columns.Select(c => primaryKey.Contains(c.Name) ? c with { NotNull = true } : c)]));
        }

        int declared = CreateTableKeywordRegex().Count(clean);
        if (declared != tables.Count)
        {
            throw new InvalidDataException($"{declared} CREATE TABLE var, {tables.Count} tanesi ayristirildi.");
        }

        return tables;
    }

    /// <summary>
    /// CREATE TABLE govdelerindeki CHECK ifadelerini ve REFERENCES ciftlerini, ayrica "ALTER TABLE t ADD FOREIGN KEY (c) REFERENCES r (k)"
    /// bildirimlerini ayristirir. Sayilar belgeden turetilir: belgede gecen CHECK, REFERENCES ve FOREIGN KEY sayisi ayristirilanla ayni degilse hata verir.
    /// </summary>
    public static DdlConstraints ParseConstraints(string sql)
    {
        string clean = StripComments(sql);
        List<DdlCheck> checks = [];
        List<DdlReference> references = [];
        foreach (Match m in CreateTableRegex().Matches(clean))
        {
            string name = m.Groups["name"].Value;
            string body = ReadParenthesized(clean, m.Index + m.Length - 1, name);
            foreach (string raw in SplitTopLevel(body))
            {
                string item = WhitespaceRegex().Replace(raw, " ").Trim();
                Match check = CheckClauseRegex().Match(item);
                if (check.Success)
                {
                    int open = check.Index + check.Length - 1;
                    string expression = ReadParenthesized(item, open, name);
                    checks.Add(new DdlCheck(name, check.Groups["name"].Success ? check.Groups["name"].Value : null, expression.Trim()));
                }

                foreach (Match reference in ReferencesRegex().Matches(item))
                {
                    Match column = ColumnRegex().Match(item);
                    if (!column.Success)
                    {
                        throw new InvalidDataException($"{name}: REFERENCES satirinda sutun adi ayristirilamadi: '{item}'");
                    }

                    references.Add(new DdlReference(name, column.Groups["name"].Value, reference.Groups["table"].Value, reference.Groups["column"].Value));
                }
            }
        }

        foreach (Match alter in AlterForeignKeyRegex().Matches(clean))
        {
            references.Add(new DdlReference(alter.Groups["table"].Value, alter.Groups["column"].Value, alter.Groups["rtable"].Value, alter.Groups["rcolumn"].Value));
        }

        int declaredChecks = CheckKeywordRegex().Count(clean);
        if (declaredChecks != checks.Count)
        {
            throw new InvalidDataException($"{declaredChecks} CHECK var, {checks.Count} tanesi ayristirildi.");
        }

        int declaredReferences = ReferencesKeywordRegex().Count(clean);
        if (declaredReferences != references.Count)
        {
            throw new InvalidDataException($"{declaredReferences} REFERENCES var, {references.Count} tanesi ayristirildi.");
        }

        return new DdlConstraints(checks, references);
    }

    private static DdlColumn ParseColumn(string table, string item)
    {
        Match column = ColumnRegex().Match(item);
        if (!column.Success)
        {
            throw new InvalidDataException($"{table}: sutun ayristirilamadi: '{item}'");
        }

        string rest = column.Groups["rest"].Value;

        // Satir ici CHECK ifadesi NOT NULL ve DEFAULT aramasina karismasin.
        int check = rest.IndexOf(" CHECK", StringComparison.Ordinal);
        string head = check >= 0 ? rest[..check] : rest;

        Match type = ColumnTypeRegex().Match(head);
        if (!type.Success)
        {
            throw new InvalidDataException($"{table}.{column.Groups["name"].Value}: tur ayristirilamadi: '{rest}'");
        }

        Match def = DefaultRegex().Match(head);
        if (!def.Success && head.Contains("DEFAULT", StringComparison.Ordinal))
        {
            throw new InvalidDataException($"{table}.{column.Groups["name"].Value}: DEFAULT ayristirilamadi: '{rest}'");
        }

        return new DdlColumn(
            column.Groups["name"].Value,
            type.Value,
            NotNull: head.Contains("NOT NULL", StringComparison.Ordinal) || head.Contains("PRIMARY KEY", StringComparison.Ordinal),
            Default: def.Success ? def.Groups["value"].Value : null,
            Identity: head.Contains("GENERATED ALWAYS AS IDENTITY", StringComparison.Ordinal),
            Generated: head.Contains("GENERATED ALWAYS AS (", StringComparison.Ordinal));
    }

    /// <summary>openIndex'teki '(' ile eslesen ')' arasini dondurur; tirnak ici parantezler sayilmaz.</summary>
    private static string ReadParenthesized(string text, int openIndex, string table)
    {
        int depth = 0;
        bool quoted = false;
        for (int i = openIndex; i < text.Length; i++)
        {
            char c = text[i];
            if (c == '\'')
            {
                quoted = !quoted;
            }
            else if (!quoted && c == '(')
            {
                depth++;
            }
            else if (!quoted && c == ')' && --depth == 0)
            {
                return text[(openIndex + 1)..i];
            }
        }

        throw new InvalidDataException($"{table}: kapanmayan parantez.");
    }

    /// <summary>Parantez ve tirnak disindaki virgullerden boler.</summary>
    private static List<string> SplitTopLevel(string body)
    {
        List<string> parts = [];
        int depth = 0;
        bool quoted = false;
        int start = 0;
        for (int i = 0; i < body.Length; i++)
        {
            char c = body[i];
            if (c == '\'')
            {
                quoted = !quoted;
            }
            else if (!quoted && c == '(')
            {
                depth++;
            }
            else if (!quoted && c == ')')
            {
                depth--;
            }
            else if (!quoted && depth == 0 && c == ',')
            {
                parts.Add(body[start..i]);
                start = i + 1;
            }
        }

        parts.Add(body[start..]);
        return parts;
    }

    private static string FindUpwards(string relative)
    {
        DirectoryInfo? dir = new(AppContext.BaseDirectory);
        while (dir is not null)
        {
            string candidate = Path.Combine([dir.FullName, .. relative.Split('/')]);
            if (File.Exists(candidate))
            {
                return candidate;
            }

            dir = dir.Parent;
        }

        throw new FileNotFoundException($"{relative} depo kokunde bulunamadi.");
    }

    [GeneratedRegex(@"CREATE\s+TYPE\s+(?<name>[a-z0-9_]+)\s+AS\s+ENUM\s*\((?<labels>[^)]*)\)\s*;", RegexOptions.CultureInvariant)]
    private static partial Regex EnumTypeRegex();

    [GeneratedRegex(@"^'(?<label>[a-z0-9_]+)'$", RegexOptions.CultureInvariant)]
    private static partial Regex EnumLabelRegex();

    [GeneratedRegex(@"CREATE\s+TYPE\b", RegexOptions.CultureInvariant)]
    private static partial Regex CreateTypeRegex();

    [GeneratedRegex(@"CREATE\s+TABLE\s+(?<name>[a-z0-9_]+)\s*\(", RegexOptions.CultureInvariant)]
    private static partial Regex CreateTableRegex();

    [GeneratedRegex(@"CREATE\s+TABLE\b", RegexOptions.CultureInvariant)]
    private static partial Regex CreateTableKeywordRegex();

    [GeneratedRegex(@"^PRIMARY KEY ?\((?<cols>[a-z0-9_, ]+)\)$", RegexOptions.CultureInvariant)]
    private static partial Regex TablePrimaryKeyRegex();

    [GeneratedRegex(@"^(?<name>[a-z0-9_]+) (?<rest>.+)$", RegexOptions.CultureInvariant)]
    private static partial Regex ColumnRegex();

    [GeneratedRegex(@"^(char\([0-9]+\)|halfvec\([0-9]+\)|[a-z0-9_]+(\[\])?)(?=$| )", RegexOptions.CultureInvariant)]
    private static partial Regex ColumnTypeRegex();

    [GeneratedRegex(@"\bDEFAULT (?<value>'(?:[^']|'')*'|[a-z0-9_]+\(\)|-?[0-9]+|true|false)(?=$| )", RegexOptions.CultureInvariant)]
    private static partial Regex DefaultRegex();

    [GeneratedRegex(@"(?:^| )(?:CONSTRAINT (?<name>[a-z0-9_]+) )?CHECK ?\(", RegexOptions.CultureInvariant)]
    private static partial Regex CheckClauseRegex();

    [GeneratedRegex(@"\bCHECK\b", RegexOptions.CultureInvariant)]
    private static partial Regex CheckKeywordRegex();

    [GeneratedRegex(@"\bREFERENCES (?<table>[a-z0-9_]+) ?\((?<column>[a-z0-9_]+)\)", RegexOptions.CultureInvariant)]
    private static partial Regex ReferencesRegex();

    [GeneratedRegex(@"\bREFERENCES\b", RegexOptions.CultureInvariant)]
    private static partial Regex ReferencesKeywordRegex();

    [GeneratedRegex(@"ALTER TABLE (?<table>[a-z0-9_]+) ADD FOREIGN KEY ?\((?<column>[a-z0-9_]+)\) REFERENCES (?<rtable>[a-z0-9_]+) ?\((?<rcolumn>[a-z0-9_]+)\)", RegexOptions.CultureInvariant)]
    private static partial Regex AlterForeignKeyRegex();

    [GeneratedRegex(@"\s+", RegexOptions.CultureInvariant)]
    private static partial Regex WhitespaceRegex();
}
