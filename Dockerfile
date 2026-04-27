FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git git-lfs ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git lfs install --system

WORKDIR /app
COPY . /app
RUN git lfs pull

RUN pip install --no-cache-dir -r requirements.txt

CMD gunicorn main:app --bind 0.0.0.0:$PORT --workers 1 --timeout 120
