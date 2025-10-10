# syntax=docker/dockerfile:1

FROM python:3.10-slim AS base

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install system dependencies for Playwright and GCloud SDK
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    ca-certificates \
    fonts-liberation \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libwayland-client0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxkbcommon0 \
    libxrandr2 \
    libxcb1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && curl https://sdk.cloud.google.com | bash \
    && rm -rf /var/lib/apt/lists/*

# Configurar gsutil path
ENV PATH=/root/google-cloud-sdk/bin:$PATH

COPY requirements.txt ./

RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install chromium

COPY . .

RUN chmod +x /app/scripts/docker-entrypoint.sh

ENV PYTHONPATH=/app

ENV PORT=8080

EXPOSE 8080

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["run"]
