FROM python:3.12-slim
ARG VCS_REF=unknown
ARG VCS_REF_FULL=unknown
ARG IMAGE_VERSION=unknown
ARG IMAGE_SOURCE=unknown
ARG IMAGE_CREATED=unknown
LABEL org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="${IMAGE_SOURCE}" \
      org.opencontainers.image.version="${IMAGE_VERSION}" \
      org.opencontainers.image.created="${IMAGE_CREATED}" \
      com.sentinel-dna.git.revision.full="${VCS_REF_FULL}"
# The deployment contract must provide the environment explicitly.  An
# invalid sentinel keeps an image started without a runtime contract from
# silently becoming development or production.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SENTINEL_DNA_ENV=__RUNTIME_ENV_REQUIRED__
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --create-home --uid 10001 sentinel && mkdir -p /var/lib/sentinel && chown -R sentinel:sentinel /app /var/lib/sentinel
USER sentinel
EXPOSE 5000
CMD ["gunicorn", "wsgi:application", "--bind", "0.0.0.0:5000", "--workers", "1", "--access-logfile", "-", "--error-logfile", "-"]
