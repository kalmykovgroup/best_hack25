#!/bin/bash
set -e

DB_FILE="/data/db/moscow.db"

# Проверяем, существует ли уже база данных
if [ -f "$DB_FILE" ]; then
    echo "База данных уже существует: $DB_FILE"
    echo "Пропускаю конвертацию..."
else
    echo "База данных не найдена. Начинаю конвертацию OSM..."
    python3 /app/convert_osm.py

    if [ $? -ne 0 ]; then
        echo "Ошибка при конвертации OSM файла"
        exit 1
    fi
fi

# Запускаем API сервер
echo "Запуск API сервера на порту 8091..."
exec python3 /app/api_server.py
