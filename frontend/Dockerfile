# syntax=docker/dockerfile:1.7

# ---- Builder stage: build static frontend ----
FROM node:22-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN --mount=type=cache,target=/root/.npm \
    if [ -f package-lock.json ]; then npm ci; else npm install; fi

COPY tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY vite.config.ts tailwind.config.js postcss.config.js ./
COPY index.html ./
COPY src ./src

RUN npm run build

# ---- Runtime stage: nginx serving SPA + proxy /api -> web:8000 ----
FROM nginx:1.27-alpine AS runtime

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy built static assets
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null 2>&1 || exit 1
