FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN curl -fsSL https://github.com/bbang-bbang/today_tatics/releases/download/db-v1/players.db \
        -o players.db \
    && [ "$(stat -c%s players.db)" -gt 50000000 ]

RUN pip install --no-cache-dir -r requirements.txt

CMD gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
