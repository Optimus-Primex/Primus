FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PRIMUS_ENV=production \
    PRIMUS_DATABASE_URL=sqlite:////data/primus.db

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 primus \
    && mkdir -p /data \
    && chown -R primus:primus /app /data

USER primus

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).status == 200 else sys.exit(1)"

# Single worker with threads so the in-process scheduler runs exactly once.
# Scale out by running a dedicated worker service and disabling the
# in-process scheduler (PRIMUS_ENABLE_SCHEDULER=0).
CMD ["gunicorn", "--workers", "1", "--threads", "8", "--bind", "0.0.0.0:8000", "wsgi:app"]
