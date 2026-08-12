FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SENTINEL_DNA_HOST=0.0.0.0 SENTINEL_DNA_PORT=5000
COPY requirements.txt pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir ".[postgres]"
RUN useradd --create-home --shell /usr/sbin/nologin sentinel && mkdir -p /var/lib/sentinel-dna && chown -R sentinel:sentinel /app /var/lib/sentinel-dna
USER sentinel
ENV SENTINEL_DNA_DATA_DIR=/var/lib/sentinel-dna
EXPOSE 5000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz')"
CMD ["python", "-m", "sentinel_dna.workspace.web_app"]
