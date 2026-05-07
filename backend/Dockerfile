FROM python:3.11-slim-bullseye

# Inject proxy CA cert so pip SSL works
COPY proxy-ca.crt /tmp/proxy-ca.crt

ENV SSL_CERT_FILE=/tmp/proxy-ca.crt
ENV REQUESTS_CA_BUNDLE=/tmp/proxy-ca.crt

WORKDIR /app

# Install Python packages from pre-downloaded wheels (no network access needed)
COPY pip-cache /pip-cache
COPY requirements.txt .
RUN pip install --no-index --find-links /pip-cache -r requirements.txt && \
    rm -rf /pip-cache

# Install static ffmpeg/ffprobe binaries (no apt needed)
COPY ffmpeg-static /usr/local/bin/ffmpeg
COPY ffprobe-static /usr/local/bin/ffprobe
RUN chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe

COPY app ./app

RUN mkdir -p /app/hls /app/recordings

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
