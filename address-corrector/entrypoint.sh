#!/bin/bash
set -e

echo "Starting Address Corrector gRPC service with FTS5 dictionaries..."

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

# Проверка и создание FTS5 словарей для быстрой коррекции
echo "Checking FTS5 dictionaries..."

# Проверяем существование таблицы street_dictionary
TABLE_EXISTS=$(sqlite3 /data/db/moscow.db "SELECT name FROM sqlite_master WHERE type='table' AND name='street_dictionary';" 2>/dev/null || echo "")

if [ -z "$TABLE_EXISTS" ]; then
    echo "FTS5 dictionaries not found. Creating dictionaries..."
    echo "This may take 1-2 minutes on first run..."

    python create_dictionaries.py

    if [ $? -eq 0 ]; then
        echo "✓ FTS5 dictionaries created successfully!"
        echo "  Expected performance: 5-15ms (vs old 700-1000ms)"
    else
        echo "✗ Failed to create FTS5 dictionaries"
        echo "  Service will start but correction may be slower"
    fi
else
    echo "✓ FTS5 dictionaries already exist"

    # Показываем статистику
    STREET_COUNT=$(sqlite3 /data/db/moscow.db "SELECT COUNT(*) FROM street_dictionary;" 2>/dev/null || echo "0")
    CITY_COUNT=$(sqlite3 /data/db/moscow.db "SELECT COUNT(*) FROM city_dictionary;" 2>/dev/null || echo "0")

    echo "  Streets in dictionary: $STREET_COUNT"
    echo "  Cities in dictionary: $CITY_COUNT"
fi

# Запуск gRPC сервера
echo "Starting gRPC server on port ${GRPC_PORT:-50053}..."
exec python grpc_server.py
