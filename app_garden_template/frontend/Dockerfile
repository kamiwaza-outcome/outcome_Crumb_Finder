# Multi-stage build
FROM node:20-slim AS deps
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .

# Build with standalone output
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production stage
FROM node:20-slim AS runner
WORKDIR /app

# Create non-root user
RUN useradd -m -u 1001 nextjs

# Copy built application
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static
COPY --from=builder --chown=nextjs:nextjs /app/public ./public

USER nextjs

# Standard Next.js port
EXPOSE 3000

ENV NODE_ENV=production
ENV PORT=3000

CMD ["node", "server.js"]