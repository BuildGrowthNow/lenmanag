FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including Chromium and its required libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    wget \
    xdg-utils \
    xvfb \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright and Chromium browser
RUN pip install --no-cache-dir playwright==1.44.0 && \
    playwright install-deps chromium && \
    playwright install chromium

RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[gemini]"

RUN playwright install chromium --with-deps

COPY . .

RUN chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]