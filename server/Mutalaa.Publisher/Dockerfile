# Mutalaa Yayinlayici (komut: watch). Baglam depo kokudur: docker compose --profile app build publisher
# Calisma: runtime (Debian: NSec/libsodium ve e_sqlite3 yerel kitapliklari linux-x64 altinda gelir; ICU var).
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

COPY global.json .editorconfig ./
COPY server/Directory.Build.props server/Directory.Packages.props server/
COPY server/Mutalaa.Domain/Mutalaa.Domain.csproj server/Mutalaa.Domain/packages.lock.json server/Mutalaa.Domain/
COPY server/Mutalaa.Infrastructure/Mutalaa.Infrastructure.csproj server/Mutalaa.Infrastructure/packages.lock.json server/Mutalaa.Infrastructure/
COPY server/Mutalaa.Publisher/Mutalaa.Publisher.csproj server/Mutalaa.Publisher/packages.lock.json server/Mutalaa.Publisher/
RUN dotnet restore server/Mutalaa.Publisher/Mutalaa.Publisher.csproj --locked-mode

COPY server/Mutalaa.Domain server/Mutalaa.Domain
COPY server/Mutalaa.Infrastructure server/Mutalaa.Infrastructure
COPY server/Mutalaa.Publisher server/Mutalaa.Publisher
RUN dotnet publish server/Mutalaa.Publisher/Mutalaa.Publisher.csproj -c Release --no-restore -o /out

FROM mcr.microsoft.com/dotnet/runtime:10.0 AS runtime
WORKDIR /repo
# Paket DDL'i ve manifest semasi calisma dizinine gore okunur (Publisher:SchemaDir varsayilani packages/content-schema/sql).
COPY packages/content-schema/sql packages/content-schema/sql
COPY packages/content-schema/manifest.schema.json packages/content-schema/manifest.schema.json
RUN mkdir -p /repo/.tmp /repo/data/packs /repo/data/reports && chown -R app:app /repo
COPY --from=build /out /app
USER app
ENTRYPOINT ["dotnet", "/app/Mutalaa.Publisher.dll"]
CMD ["watch"]
