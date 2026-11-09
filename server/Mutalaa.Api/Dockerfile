# Mutalaa API (editor kipi). Baglam depo kokudur: docker compose --profile app build api
# Derleme: sdk, kilit dosyalariyla --locked-mode geri yukleme; calisma: aspnet (Debian, ICU var: InvariantGlobalization acik degil).
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src

# Geri yukleme katmani: yalniz proje ve kilit dosyalari (kaynak degisince katman yeniden kullanilir).
COPY global.json .editorconfig ./
COPY server/Directory.Build.props server/Directory.Packages.props server/
COPY server/Mutalaa.Domain/Mutalaa.Domain.csproj server/Mutalaa.Domain/packages.lock.json server/Mutalaa.Domain/
COPY server/Mutalaa.Infrastructure/Mutalaa.Infrastructure.csproj server/Mutalaa.Infrastructure/packages.lock.json server/Mutalaa.Infrastructure/
COPY server/Mutalaa.Api/Mutalaa.Api.csproj server/Mutalaa.Api/packages.lock.json server/Mutalaa.Api/
RUN dotnet restore server/Mutalaa.Api/Mutalaa.Api.csproj --locked-mode

COPY server/Mutalaa.Domain server/Mutalaa.Domain
COPY server/Mutalaa.Infrastructure server/Mutalaa.Infrastructure
COPY server/Mutalaa.Api server/Mutalaa.Api
# OpenAPI belgesi depoda durur ve CI'da Release derlemesiyle denetlenir; imaj derlemesi belge uretmez.
RUN dotnet publish server/Mutalaa.Api/Mutalaa.Api.csproj -c Release --no-restore \
    -p:OpenApiGenerateDocumentsOnBuild=false -o /out

FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS runtime
# Goreli data/..., pipeline/... ve .tmp/... yollari /repo altinda cozulur; compose bu klasorleri baglar.
WORKDIR /repo
RUN mkdir -p /repo/.tmp && chown -R app:app /repo
COPY --from=build /out /app
USER app
ENV ASPNETCORE_HTTP_PORTS=8080
EXPOSE 8080
ENTRYPOINT ["dotnet", "/app/Mutalaa.Api.dll"]
