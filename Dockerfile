FROM python:3.12-slim
ARG VCS_REF
ARG VCS_REF_FULL
ARG IMAGE_VERSION
ARG IMAGE_SOURCE
ARG IMAGE_CREATED
RUN set -eu; \
    test "$VCS_REF" = "$VCS_REF_FULL"; \
    printf '%s\n' "$VCS_REF_FULL" | grep -Eq '^[0-9a-f]{40}$'; \
    test "$IMAGE_VERSION" = "$VCS_REF_FULL"; \
    test "$IMAGE_SOURCE" = "https://github.com/uwakwechukwuebukapaul-ai/SENTINEL-DNA"; \
    test "$IMAGE_CREATED" != ""; \
    test "$IMAGE_CREATED" != "unknown"; \
    printf '%s\n' "$IMAGE_CREATED" | grep -Eq '^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$'
LABEL org.opencontainers.image.revision="${VCS_REF_FULL}" \
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
