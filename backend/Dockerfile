FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements
COPY backend/requirements.txt /app/requirements.txt

# Harden pip installs
ENV PIP_DEFAULT_TIMEOUT=120
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt --timeout 120

# Copy entire repo
COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 5001

# Start Flask app
CMD ["python", "backend/app.py"]
