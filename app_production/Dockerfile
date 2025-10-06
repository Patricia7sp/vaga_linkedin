# syntax=docker/dockerfile:1

FROM python:3.10-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CHROME_BIN=/usr/bin/chromium \
    CHROMEDRIVER_PATH=/usr/bin/chromedriver \
    DISPLAY=:99

RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    chromium \
    chromium-driver \
    python3-pip \
    libxrandr2 \
    libgbm1 \
    libgtk-3-0 \
    && curl https://sdk.cloud.google.com | bash \
    && rm -rf /var/lib/apt/lists/*

# Configurar gsutil path
ENV PATH=/root/google-cloud-sdk/bin:$PATH

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/scripts/docker-entrypoint.sh

ENV PYTHONPATH=/app

ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["run"]
