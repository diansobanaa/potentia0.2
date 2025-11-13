# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Set folder kerja di dalam kontainer
WORKDIR /app

# Salin file requirements
COPY requirements.txt .

# --- PERBAIKAN v3.3: Instal Build Dependencies & Manajemen Cache ---
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip dan install dependensi dalam satu layer dengan cache yang bersih
RUN pip install --no-cache-dir --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt --use-deprecated=legacy-resolver
# --- AKHIR PERBAIKAN ---

# Salin sisa kode aplikasi Anda
COPY . .

# Beri tahu Docker port berapa yang akan diekspos
EXPOSE 8000

# Perintah untuk menjalankan aplikasi saat kontainer dimulai
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]