FROM python:3.12-slim

# system deps for psycopg2, builds, and locales
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev locales \
 && sed -i 's/# de_CH.UTF-8 UTF-8/de_CH.UTF-8 UTF-8/' /etc/locale.gen \
 && locale-gen \
 && rm -rf /var/lib/apt/lists/*

# set default locale
ENV LANG=de_CH.UTF-8 \
    LANGUAGE=de_CH:de \
    LC_ALL=de_CH.UTF-8

# non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# deps first (cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app with correct ownership
COPY --chown=appuser:appuser . .

# ensure sane permissions (dirs 755, files 644), and entrypoint executable
RUN find /app -type d -exec chmod 755 {} \; \
 && find /app -type f -exec chmod 644 {} \; \
 && chmod +x /app/entrypoint.sh

USER appuser
EXPOSE 5012
ENTRYPOINT ["/app/entrypoint.sh"]
