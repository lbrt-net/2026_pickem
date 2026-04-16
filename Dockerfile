FROM python:3.11

# Install Node
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install -r requirements.txt

# Build React
COPY frontend/ ./frontend/
RUN cd frontend && npm install && npm run build

# Copy the rest
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]