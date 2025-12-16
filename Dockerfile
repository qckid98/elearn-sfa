# Gunakan base image Python yang ringan
FROM python:3.10-slim

# Set folder kerja di dalam container
WORKDIR /app

# Copy requirements dulu agar caching docker efisien
COPY requirements.txt .

# Install dependencies sistem (dibutuhkan untuk psycopg2/Postgres)
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install library Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy seluruh kode proyek ke dalam container
COPY . .

# Expose port flask
EXPOSE 5000

# Command default (akan ditimpa oleh docker-compose, tapi bagus untuk fallback)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "run:app"]