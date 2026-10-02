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

# Portları aç (8501: Streamlit Frontend, 8000: FastAPI Backend)
EXPOSE 8501
EXPOSE 8000

# Sağlık kontrolü
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Başlangıç komutu (Şimdilik sadece Streamlit. İleride gunicorn ile API ayağa kalkacak)
CMD ["python", "server.py"]
