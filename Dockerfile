# SPDX-License-Identifier: GPL-3.0-only
FROM python:3.12-alpine
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apk add --no-cache docker-cli docker-cli-compose ca-certificates
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
COPY static/ ./static/
RUN addgroup -S monitor && adduser -S -G monitor monitor
# Docker socket access depends on the NAS daemon socket permissions. Root is required
# for the initial host Docker inventory; the web application requires authentication.
EXPOSE 9012
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9012/api/session', timeout=3).read()" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9012", "--no-server-header", "--no-access-log"]
