ARG BACKEND_URL_PLACEHOLDER=http://backend-url.invalid

FROM node:24.22.3-trixie-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM node:24.22.3-trixie-slim AS build
ARG BACKEND_URL_PLACEHOLDER
ENV NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=$BACKEND_URL_PLACEHOLDER
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN mkdir -p public \
    && npm run build \
    && cd .next/standalone \
    && grep -rlF --exclude-dir=node_modules "$BACKEND_URL_PLACEHOLDER" . > /tmp/backend-url-files \
    && grep -qxF ./.next/routes-manifest.json /tmp/backend-url-files \
    && mv /tmp/backend-url-files .backend-url-files

FROM node:24.22.3-trixie-slim
ARG BACKEND_URL_PLACEHOLDER
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000 \
    KEEP_ALIVE_TIMEOUT=65000 \
    BACKEND_URL_PLACEHOLDER=$BACKEND_URL_PLACEHOLDER
WORKDIR /app
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
COPY --from=build /app/public ./public
COPY docker-start.sh ./
RUN xargs chown 1000:1000 < .backend-url-files \
    && install -d -o 1000 -g 1000 .next/cache

USER 1000:1000
EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --start-interval=2s --retries=3 \
    CMD ["node", "-e", "fetch('http://127.0.0.1:3000/sign-in').then((response) => process.exit(response.ok ? 0 : 1), () => process.exit(1))"]

CMD ["sh", "docker-start.sh"]
