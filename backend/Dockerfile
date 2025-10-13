FROM python:3.11-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
# Harden pip installs against transient network issues
ENV PIP_DEFAULT_TIMEOUT=120
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt --timeout 120

COPY . /app

ENV PYTHONUNBUFFERED=1
EXPOSE 5001

CMD ["python", "backend/app.py"]


