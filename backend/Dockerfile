FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt /app/requirements.txt
ENV PIP_DEFAULT_TIMEOUT=120
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt --timeout 120

# Copy entire repo
COPY . /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
EXPOSE 5001

# Start Flask app
CMD ["python", "backend/app.py"]
