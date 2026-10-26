FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci  # exact versions from package-lock.json (never drifts between builds)
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
# headless Chromium for the recap picture (recap_image.py)
RUN python -m playwright install --with-deps chromium
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY --from=builder /app/dist ./frontend/dist
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]