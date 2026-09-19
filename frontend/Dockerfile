# syntax=docker/dockerfile:1

# --- Stage 1: dependencies ---
FROM node:22-alpine AS deps
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci

# --- Stage 2: build the standalone production bundle ---
FROM node:22-alpine AS builder
WORKDIR /build
COPY --from=deps /build/node_modules ./node_modules
COPY . .

# API URL is a build-time variable (the browser calls the API directly;
# server components do not proxy requests at runtime).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# --- Stage 3: minimal production runtime ---
FROM node:22-alpine AS runner
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

WORKDIR /app
RUN addgroup -S app && adduser -S app -G app

# Standalone output: server.js plus only the traced node_modules.
COPY --from=builder /build/.next/standalone ./
COPY --from=builder /build/.next/static ./.next/static

USER app
EXPOSE 3000

HEALTHCHECK --interval=10s --timeout=5s --start-period=15s --retries=5 \
    CMD node -e "fetch('http://127.0.0.1:'+(process.env.PORT||3000)+'/api-health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server.js"]
