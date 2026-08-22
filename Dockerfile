FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SENTINEL_DNA_ENV=production
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 sentinel && mkdir -p /var/lib/sentinel && chown -R sentinel:sentinel /app /var/lib/sentinel
USER sentinel
EXPOSE 5000
STOPSIGNAL SIGTERM
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=3)"
CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--timeout", "60", "--graceful-timeout", "30", "--keep-alive", "5", "--max-requests", "1000", "--max-requests-jitter", "100", "--access-logfile", "-", "--error-logfile", "-"]
