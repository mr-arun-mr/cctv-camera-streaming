FROM python:3.11-slim

WORKDIR /app

# Trust proxy CA so apt-get and pip can reach the internet
COPY proxy-ca.crt /usr/local/share/ca-certificates/proxy-ca.crt
RUN update-ca-certificates

ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY app ./app

RUN mkdir -p /app/hls /app/recordings /app/data

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
