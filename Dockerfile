FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (curl for healthcheck, libpq for postgres)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Ensure logs directory exists and agent_activity.log file is created
RUN mkdir -p logs && touch logs/agent_activity.log

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
