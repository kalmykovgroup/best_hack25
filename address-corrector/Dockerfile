# Базовый образ Python
FROM python:3.11-slim

# Установка системных зависимостей для libpostal
RUN apt-get update && apt-get install -y \
    curl \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Установка libpostal
RUN git clone https://github.com/openvenues/libpostal /tmp/libpostal && \
    cd /tmp/libpostal && \
    ./bootstrap.sh && \
    ./configure --datadir=/usr/local/share/libpostal && \
    make -j4 && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /tmp/libpostal

# Создание рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка Python зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование proto файла и генерация gRPC кода
COPY address_corrector.proto .
RUN python -m grpc_tools.protoc \
    -I. \
    --python_out=. \
    --grpc_python_out=. \
    address_corrector.proto

# Копирование основного кода
COPY grpc_server.py .
COPY entrypoint.sh .

# Делаем entrypoint исполняемым
RUN chmod +x entrypoint.sh

# Создание директории для базы данных
RUN mkdir -p /data/db

# Открываем порт для gRPC
EXPOSE 50053

# Запуск сервиса
ENTRYPOINT ["./entrypoint.sh"]
