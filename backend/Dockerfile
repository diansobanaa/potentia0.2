# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Set folder kerja di dalam kontainer
WORKDIR /app

# Salin file requirements dan install dependensi
# Ini dipisah agar Docker bisa cache, build lebih cepat
COPY requirements.txt .

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt --use-deprecated=legacy-resolver

# Salin sisa kode aplikasi Anda
COPY . .

# Beri tahu Docker port berapa yang akan diekspos
EXPOSE 8000

# Perintah untuk menjalankan aplikasi saat kontainer dimulai
# --host 0.0.0.0 penting untuk diakses dari luar kontainer
# --reload bagus untuk development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]# File: Dockerfile

# Gunakan base image Python yang ringan
FROM python:3.11-slim

# Set folder kerja di dalam kontainer
WORKDIR /app

# Salin file requirements
COPY requirements.txt .

# --- PERBAIKAN: Instal Build Dependencies ---
# Diperlukan untuk meng-kompilasi 'tiktoken' dan 'regex'
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
# --- AKHIR PERBAIKAN ---

RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt --use-deprecated=legacy-resolver

# Salin sisa kode aplikasi Anda
COPY . .

# Beri tahu Docker port berapa yang akan diekspos
EXPOSE 8000

# Perintah untuk menjalankan aplikasi saat kontainer dimulai
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]