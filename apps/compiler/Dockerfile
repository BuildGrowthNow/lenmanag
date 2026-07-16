FROM node:20-alpine AS base

# Install dependencies only when needed
FROM base AS deps
WORKDIR /app

COPY package.json ./
RUN npm install --production=false

# Build the application
FROM base AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

RUN npm run build

# Production image
FROM base AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV PORT=3001

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 compiler

COPY --from=builder --chown=compiler:nodejs /app/dist ./dist
COPY --from=builder --chown=compiler:nodejs /app/node_modules ./node_modules
COPY --from=builder --chown=compiler:nodejs /app/package.json ./package.json

USER compiler

EXPOSE 3001

CMD ["node", "dist/server.js"]
