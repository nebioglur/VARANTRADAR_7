FROM python:3.10-slim

# Çalışma dizinini oluştur
WORKDIR /app

# Gerekli sistem paketlerini yükle
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Gereksinimleri kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# Flask sunucusu enjekte edilen PORT'u dinler (Render/Verdent override eder)
ENV PORT=8080
EXPOSE 8080

# Sağlık kontrolü
HEALTHCHECK CMD curl --fail http://localhost:8080/api/ping || exit 1

# Başlangıç komutu
CMD ["python", "server.py"]
