FROM node:20-alpine AS builder
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY main.py .
COPY --from=builder /app/dist ./frontend/dist
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port $PORT"]