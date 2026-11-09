using System.CommandLine;
using System.Globalization;
using System.Reflection;
using System.Text;
using System.Text.Encodings.Web;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.Extensions.Configuration.UserSecrets;
using Mutalaa.Domain.Releases;
using Mutalaa.Infrastructure.Manifests;
using Mutalaa.Publisher.Pipeline;

namespace Mutalaa.Publisher.Commands;

/// <summary>
/// keys generate --flavor f [--force] (K-45): Ed25519 anahtar cifti uretir; tohum, kid ve acik anahtar kullanici sirlari dosyasina
/// (Signing:{f}:PrivateKey, Kid, PublicKey) yazilir. Ekrana yalniz acik anahtar ve kid basilir. Var olan anahtarin ustune --force olmadan yazilmaz.
/// Dosya yolu <c>dotnet user-secrets</c> ile ayni kuraldan gelir (UserSecretsId + PathHelper); diger anahtarlar korunur.
/// </summary>
public sealed class KeysCommand(PublisherContext context)
{
    private static readonly JsonSerializerOptions WriteOptions = new()
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
    };

    public Command Create()
    {
        Option<string> flavor = CommandSupport.FlavorOption();
        Option<bool> force = new("--force") { Description = "Var olan anahtarin ustune yaz (kid numarasi artar)." };

        Command generate = new("generate", "Ed25519 anahtar cifti uretir; tohum kullanici sirlarina, acik anahtar ekrana yazilir.");
        generate.Options.Add(flavor);
        generate.Options.Add(force);
        generate.SetAction((parse, cancellationToken) => RunAsync(
            CommandSupport.ParseFlavor(parse.GetValue(flavor)),
            parse.GetValue(force),
            cancellationToken));

        Command keys = new("keys", "Imza anahtari islemleri.");
        keys.Subcommands.Add(generate);
        return keys;
    }

    public Task<int> RunAsync(BuildFlavor flavor, bool force, CancellationToken cancellationToken) =>
        CommandSupport.ExecuteAsync(context, useLock: false, ct => GenerateAsync(flavor, force, ct), cancellationToken);

    public async Task<ReleaseResult> GenerateAsync(BuildFlavor flavor, bool force, CancellationToken cancellationToken)
    {
        string label = flavor.ToLabel();
        string path = ResolveSecretsPath();

        JsonObject secrets = await ReadSecretsAsync(path, cancellationToken);
        string privateKeyName = $"Signing:{label}:PrivateKey";
        string kidName = $"Signing:{label}:Kid";
        string publicKeyName = $"Signing:{label}:PublicKey";

        string? existingKid = ReadString(secrets, kidName);
        bool exists = ReadString(secrets, privateKeyName) is not null;
        if (exists && !force)
        {
            return ReleaseResult.Fail(
                ExitCodes.Other,
                $"Signing:{label}:PrivateKey zaten var; ustune yazmak icin --force verin (eski anahtarla imzali manifestler dogrulanamaz).");
        }

        int year = context.Clock.GetUtcNow().Year;
        int n = NextNumber(label, year, existingKid);
        SigningKey key = SigningKeys.Generate(label, year, n);

        // Var olan anahtar ic ice bicimdeyse once o bicim temizlenir; yoksa ayni anahtar hem ic ice hem duz bulunur (yapilandirma yukleme hatasi) ve
        // eski tohum dosyada kalirdi.
        foreach (string name in new[] { privateKeyName, kidName, publicKeyName })
        {
            RemoveNested(secrets, name);
        }

        secrets[privateKeyName] = key.SeedBase64();
        secrets[kidName] = key.Kid;
        string publicKey = Base64Strict.Encode(key.GetPublicKey());
        secrets[publicKeyName] = publicKey;
        await WriteSecretsAsync(path, secrets, cancellationToken);

        context.Out.WriteLine($"kid: {key.Kid}");
        context.Out.WriteLine($"acik anahtar (base64): {publicKey}");
        return ReleaseResult.Ok(null, null, "Ozel anahtar kullanici sirlarina yazildi (ekrana basilmaz).");
    }

    private string ResolveSecretsPath()
    {
        if (!string.IsNullOrWhiteSpace(context.SecretsPathOverride))
        {
            return context.SecretsPathOverride;
        }

        string? id = typeof(KeysCommand).Assembly.GetCustomAttribute<UserSecretsIdAttribute>()?.UserSecretsId;
        if (string.IsNullOrWhiteSpace(id))
        {
            throw new PublisherException(ExitCodes.Other, "Publisher projesinde UserSecretsId tanimli degil.");
        }

        return PathHelper.GetSecretsPathFromSecretsId(id);
    }

    private static int NextNumber(string label, int year, string? existingKid)
    {
        string prefix = string.Create(CultureInfo.InvariantCulture, $"{label}-{year}-");
        if (existingKid is not null
            && existingKid.StartsWith(prefix, StringComparison.Ordinal)
            && int.TryParse(existingKid.AsSpan(prefix.Length), NumberStyles.None, CultureInfo.InvariantCulture, out int previous)
            && previous < int.MaxValue)
        {
            return previous + 1;
        }

        return 1;
    }

    private static string? ReadString(JsonObject secrets, string flatKey)
    {
        if (secrets.TryGetPropertyValue(flatKey, out JsonNode? flat) && flat is JsonValue value && value.TryGetValue(out string? text) && !string.IsNullOrEmpty(text))
        {
            return text;
        }

        // Elle yazilmis ic ice bicim: {"Signing": {"dev": {"PrivateKey": ...}}}
        JsonNode? node = secrets;
        foreach (string part in flatKey.Split(':'))
        {
            node = node is JsonObject obj && obj.TryGetPropertyValue(part, out JsonNode? child) ? child : null;
            if (node is null)
            {
                return null;
            }
        }

        return node is JsonValue leaf && leaf.TryGetValue(out string? nested) && !string.IsNullOrEmpty(nested) ? nested : null;
    }

    private static async Task<JsonObject> ReadSecretsAsync(string path, CancellationToken cancellationToken)
    {
        if (!File.Exists(path))
        {
            return [];
        }

        string text = await File.ReadAllTextAsync(path, Encoding.UTF8, cancellationToken);
        if (string.IsNullOrWhiteSpace(text))
        {
            return [];
        }

        try
        {
            return JsonNode.Parse(text) as JsonObject
                ?? throw new PublisherException(ExitCodes.Other, "Kullanici sirlari dosyasinin koku bir JSON nesnesi degil; dosyaya dokunulmadi.");
        }
        catch (JsonException ex)
        {
            throw new PublisherException(ExitCodes.Other, "Kullanici sirlari dosyasi okunamadi (gecersiz JSON); dosyaya dokunulmadi.", ex);
        }
    }

    // Gecici dosyaya yaz, sonra tasi: yarim yazilmis secrets.json olusmaz. Tohum iceren gecici dosya, olusturuldugu anda kisitlidir:
    // Unix'te yalniz sahibi okur/yazar (UnixCreateMode; olusturmadan sonra chmod penceresi yok). Windows'ta dosya, kullanici sirlari klasorunun
    // (%APPDATA%\Microsoft\UserSecrets, yalniz kullanici/SYSTEM/Administrators) erisim listesini miras alir; ek izin verilmez. Tasima basarisiz
    // olursa (ya da yazma yarida kesilirse) gecici dosya silinir: tohum arkada kalmaz.
    private static async Task WriteSecretsAsync(string path, JsonObject secrets, CancellationToken cancellationToken)
    {
        string? directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        string temp = path + ".tmp";
        File.Delete(temp);
        bool moved = false;
        try
        {
            FileStreamOptions options = new()
            {
                Mode = FileMode.CreateNew,
                Access = FileAccess.Write,
                Share = FileShare.None,
                Options = FileOptions.Asynchronous,
            };
            if (!OperatingSystem.IsWindows())
            {
                options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
            }

            await using (FileStream stream = new(temp, options))
            {
                await stream.WriteAsync(new UTF8Encoding(encoderShouldEmitUTF8Identifier: false).GetBytes(secrets.ToJsonString(WriteOptions)), cancellationToken);
            }

            File.Move(temp, path, overwrite: true);
            moved = true;
        }
        finally
        {
            if (!moved)
            {
                File.Delete(temp);
            }
        }
    }

    // Anahtarin ic ice bicimini (elle yazilmis {"Signing": {"dev": {"PrivateKey": ...}}}) siler ve bosalan ust nesneleri temizler. Duz ve ic ice bicim ayni
    // dosyada bulunursa yapilandirma saglayicisi ayni anahtari iki kez gordugu icin acilista hata verir.
    private static void RemoveNested(JsonObject secrets, string flatKey)
    {
        string[] parts = flatKey.Split(':');
        List<JsonObject> chain = [secrets];
        JsonObject current = secrets;
        for (int i = 0; i < parts.Length - 1; i++)
        {
            if (!current.TryGetPropertyValue(parts[i], out JsonNode? child) || child is not JsonObject next)
            {
                return;
            }

            chain.Add(next);
            current = next;
        }

        if (!current.Remove(parts[^1]))
        {
            return;
        }

        for (int i = chain.Count - 1; i > 0; i--)
        {
            if (chain[i].Count > 0)
            {
                break;
            }

            chain[i - 1].Remove(parts[i - 1]);
        }
    }
}
