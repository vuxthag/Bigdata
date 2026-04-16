FROM python:3.11-slim

WORKDIR /app

# System deps required by pdfplumber / asyncpg / torch / psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first (Docker cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code (includes alembic/ directory and entrypoint.sh)
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Pre-download SBERT model at build time to avoid cold start delay
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')" || true

EXPOSE 8000

# entrypoint.sh runs `alembic upgrade head` then starts uvicorn
ENTRYPOINT ["./entrypoint.sh"]
