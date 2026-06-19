FROM python:3.13

# SQLite CLI (debug) + system deps richieste da Chromium di Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    # Chromium runtime deps (minimal set)
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libatspi2.0-0 \
    libx11-6 libxcomposite1 libxdamage1 libxext6 libxfixes3 \
    libxrandr2 libgbm1 libpango-1.0-0 libcairo2 libasound2 \
    libwayland-client0 fonts-liberation libu2f-udev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r src/requirements.txt

# Installa Chromium per Playwright (browsers vanno in /root/.cache/ms-playwright)
RUN python -m playwright install chromium

ENV PYTHONPATH="${PYTHONPATH}:/app/src"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
