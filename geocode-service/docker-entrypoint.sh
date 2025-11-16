#!/bin/bash
set -e

DB_PATH="${DB_PATH:-/data/db/moscow.db}"

echo "========================================="
echo "Geocode Service Starting..."
echo "========================================="

# Проверить доступность БД
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found at $DB_PATH"
    echo "Waiting for osm-db to create database..."
    sleep 10
fi

# Инициализировать таблицу buildings если нужно
echo "Initializing buildings table..."
python /app/init_db.py "$DB_PATH"

# Запустить gRPC сервер
echo "Starting gRPC server on port 50054..."
exec python /app/server.py
