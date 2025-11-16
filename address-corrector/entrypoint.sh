#!/bin/bash
set -e

echo "Starting Address Corrector gRPC service..."

# Проверка наличия базы данных
if [ ! -f "/data/db/moscow.db" ]; then
    echo "WARNING: Database not found at /data/db/moscow.db"
    echo "Waiting for database to be available..."

    # Ждем появления базы данных (максимум 5 минут)
    for i in {1..60}; do
        if [ -f "/data/db/moscow.db" ]; then
            echo "Database found!"
            break
        fi
        echo "Waiting for database... ($i/60)"
        sleep 5
    done

    if [ ! -f "/data/db/moscow.db" ]; then
        echo "ERROR: Database still not available after 5 minutes"
        echo "Service will start but may not work correctly"
    fi
else
    echo "Database found at /data/db/moscow.db"
fi

# Проверка наличия данных libpostal
if [ ! -d "/usr/local/share/libpostal" ]; then
    echo "WARNING: Libpostal data directory not found"
    echo "Downloading libpostal data (this may take a while on first run)..."
fi

# Запуск gRPC сервера
echo "Starting gRPC server on port ${GRPC_PORT:-50053}..."
exec python grpc_server.py
