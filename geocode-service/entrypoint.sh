#!/bin/bash
set -e

OSM_FILE="${OSM_FILE:-/app/data/moscow.pbf}"
DB_FILE="${DB_PATH:-/app/db/moscow.db}"

echo "========================================="
echo "Geocode Service Initializing..."
echo "========================================="

# Проверить существование БД
if [ -f "$DB_FILE" ]; then
    echo "✅ Database exists: $DB_FILE"
    echo "Size: $(du -h $DB_FILE 2>/dev/null || echo 'unknown')"
else
    echo "❌ Database not found"

    # Проверить OSM файл
    if [ ! -f "$OSM_FILE" ]; then
        echo "ERROR: OSM file not found: $OSM_FILE"
        echo "Please mount OSM PBF file to /app/data/"
        exit 1
    fi

    echo "OSM file: $OSM_FILE"
    echo "Size: $(du -h $OSM_FILE)"

    # Создать директорию для БД
    mkdir -p "$(dirname $DB_FILE)"

    # Импортировать OSM данные
    echo "⏳ Importing OSM data (this may take 5-10 minutes)..."
    python /app/osm_importer.py "$OSM_FILE" "$DB_FILE"

    echo "✅ Import completed"
fi

# Proto код уже сгенерирован во время build
echo "Proto files already generated during build"
cd /app

# Запустить gRPC сервер
echo "🚀 Starting gRPC server on port 50054..."
echo ""
exec python /app/server.py
