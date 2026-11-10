# Mutalaa editor panel (A15). Baglam depo kokudur: docker compose --profile app build editor
# Derleme: node:24-alpine + pnpm (kilit dosyasiyla --frozen-lockfile); sunum: nginx (SPA + /api/ vekili).
FROM node:24-alpine AS build
# pnpm surumu kok package.json devEngines.packageManager ile ayni olmali.
RUN npm install --global pnpm@12.14.0
WORKDIR /repo

# Bagimlilik katmani: yalniz kilit dosyasi ve calisma alani tanimi (kaynak degisince katman yeniden kullanilir).
COPY pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm fetch

COPY package.json tsconfig.base.json ./
COPY apps/ apps/
COPY packages/ packages/
COPY shared/ shared/
RUN pnpm install --offline --frozen-lockfile
# "..." soneki: editor ve bagimliliklari (anchors, search) topolojik sirayla derlenir.
RUN pnpm --filter "@mutalaa/editor..." build

FROM nginx:1.30-alpine AS runtime
COPY apps/editor/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/apps/editor/dist /usr/share/nginx/html
# Yapilandirma sozdizimi imaj derlenirken denetlenir (api adi degiskenli proxy_pass ile calisma aninda cozulur).
RUN nginx -t
EXPOSE 80
