# apps/web —— Next.js 前端（standalone 产物）
# 多阶段构建：deps → build → runtime

# -------- deps --------
FROM node:20-alpine AS deps
WORKDIR /app
# 国内镜像加速 npm（Docker Hub 配了镜像源，npmjs.org 本身可达但慢）
RUN npm config set registry https://registry.npmmirror.com
COPY apps/web/package.json apps/web/package-lock.json* apps/web/pnpm-lock.yaml* ./
# 优先 npm ci（若有 package-lock.json），否则 npm install
RUN if [ -f package-lock.json ]; then npm ci --prefer-offline --no-audit; \
    else npm install --no-audit; fi

# -------- build --------
FROM node:20-alpine AS builder
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web .
# 公开给客户端的 API 地址；编译期注入（前端 apiClient 会读取）
ARG NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build

# -------- runtime --------
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
RUN addgroup -S nextjs && adduser -S -G nextjs nextjs
# Next.js standalone 产物
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
# apps/web 当前没有 public/ 目录；建空目录避免 next 启动时 404
RUN mkdir -p public && chown -R nextjs:nextjs public
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
