FROM python:3.11-slim

# Аргумент для имени OSM файла
ARG OSM_FILE_NAME=10-moscow.osm.pbf

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    sqlite3 \
    libsqlite3-dev \
    osmium-tool \
    spatialite-bin \
    libspatialite-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем requirements
COPY sqlLiteBuilder/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем OSM файл из директории source и скрипты
COPY source/${OSM_FILE_NAME} /data/moscow.osm.pbf
COPY sqlLiteBuilder/convert_osm.py .
COPY sqlLiteBuilder/api_server.py .
COPY sqlLiteBuilder/entrypoint.sh .

# Делаем entrypoint исполняемым
RUN chmod +x entrypoint.sh

# Создаем директорию для базы данных
RUN mkdir -p /data/db

# Открываем порт для API
EXPOSE 8091

# Запускаем entrypoint скрипт
ENTRYPOINT ["/app/entrypoint.sh"]
