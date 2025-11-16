FROM python:3.11-slim

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
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем OSM файл и скрипты
COPY 10-moscow.osm.pbf /data/moscow.osm.pbf
COPY convert_osm.py .
COPY api_server.py .
COPY entrypoint.sh .

# Делаем entrypoint исполняемым
RUN chmod +x entrypoint.sh

# Создаем директорию для базы данных
RUN mkdir -p /data/db

# Открываем порт для API
EXPOSE 8091

# Запускаем entrypoint скрипт
ENTRYPOINT ["/app/entrypoint.sh"]
