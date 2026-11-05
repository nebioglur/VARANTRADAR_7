#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "🚀 VarantRadar Pro - PythonAnywhere Otomatik Kurulum"
echo "=========================================================="

echo "[1/3] Gereksinimler yukleniyor (pip install --user)..."
pip install --user -r requirements.txt

echo "[2/3] Dizin yapisi ve veritabanlari hazirlaniyor..."
mkdir -p data logs scratch
python -c "import server; print('Veritabani tablolari dogrulandi.')"

echo "[3/3] Kurulum tamamlandi!"
echo "Simdi PythonAnywhere 'Web' sekmesine gidip 'Reload' butonuna basabilirsiniz."
echo "=========================================================="
