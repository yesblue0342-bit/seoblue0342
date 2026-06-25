# seoblue0342 — 이후 소설가 네이버 SEO 웹 (OCI / ARM64)
FROM python:3.12-slim

# lxml 등 빌드 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxslt1-dev curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

# 런타임 데이터 디렉토리
ENV SEO_DATA_DIR=/app/data
RUN mkdir -p /app/data

EXPOSE 8842

# 컨테이너 내부 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -fsS http://127.0.0.1:8842/healthz || exit 1

# gunicorn으로 서비스 (컨테이너 내부는 0.0.0.0 바인딩)
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8842", "webapp:app", "--timeout", "120"]
