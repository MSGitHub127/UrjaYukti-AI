# ── Stage 1: Build ────────────────────────────────────────────────────────────
# Install ALL deps (including devDeps) so next binary has correct permissions.
# Splitting into a "prod-only deps" stage doesn't work reliably on Cloud Build
# because Windows uploads strip executable bits from node_modules binaries.
FROM node:20-alpine AS builder
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ── Stage 2: Production runner ────────────────────────────────────────────────
# Only copies the standalone output — final image is ~120MB.
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080

RUN addgroup --system --gid 1001 nodejs && \
    adduser  --system --uid 1001 nextjs

COPY --from=builder /app/public                                ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static    ./.next/static

USER nextjs
EXPOSE 8080

CMD ["node", "server.js"]
