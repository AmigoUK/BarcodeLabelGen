# syntax=docker/dockerfile:1.7

# ---- Builder stage: build static frontend ----
# Build context is the repo root (see compose.yml) so we can reach docs/
# for HelpPage's `?raw` markdown imports. The frontend itself lives in
# /app/frontend inside the builder.
FROM node:22-alpine AS builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY frontend/tsconfig.json frontend/tsconfig.app.json frontend/tsconfig.node.json ./
COPY frontend/vite.config.ts frontend/tailwind.config.js frontend/postcss.config.js ./
COPY frontend/index.html ./
COPY frontend/src ./src
COPY docs /app/docs

RUN npm run build

# ---- Runtime stage: nginx serving SPA + proxy /api -> web:8000 ----
FROM nginx:1.27-alpine AS runtime

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static assets
COPY --from=builder /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
