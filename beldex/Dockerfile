FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 TZ=Asia/Kolkata PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl libatomic1 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
 && python -m playwright install --with-deps chromium

COPY . .
RUN chmod +x start.sh && mkdir -p data

EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD curl -sf http://127.0.0.1:8501/health || exit 1
CMD ["bash", "start.sh"]
