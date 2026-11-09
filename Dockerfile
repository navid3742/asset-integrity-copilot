# Stage 1: Build React/TypeScript assets
FROM node:22-alpine AS frontend-builder
WORKDIR /build/frontend
COPY frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html ./
COPY frontend/public ./public
COPY frontend/src ./src
RUN npm install --no-audit --no-fund && npm run build

# Stage 2: Minimal Python runtime with single-origin API + UI
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend
WORKDIR /app
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
COPY backend/app /app/backend/app
COPY backend/data/documents.json backend/data/asset_integrity_seed.json /app/backend/data/
COPY --from=frontend-builder /build/frontend/dist /app/frontend/dist
RUN useradd -m demo && mkdir -p /app/backend/data && chown -R demo:demo /app/backend/data
USER demo
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
