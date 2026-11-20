FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    gocryptfs fuse3 ca-certificates && \
    printf '\\nuser_allow_other\\n' >> /etc/fuse.conf && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .

ENV PYTHONUNBUFFERED=1
EXPOSE 8088
CMD ["python", "app.py"]
