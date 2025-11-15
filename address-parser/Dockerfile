FROM python:3.11-slim

# Устанавливаем необходимые системные зависимости для сборки libpostal
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    autoconf \
    automake \
    libtool \
    pkg-config \
    git \
    && rm -rf /var/lib/apt/lists/*

# Скачиваем и устанавливаем libpostal
RUN git clone https://github.com/openvenues/libpostal /libpostal && \
    cd /libpostal && \
    ./bootstrap.sh && \
    ./configure --datadir=/usr/local/share/libpostal && \
    make -j4 && \
    make install && \
    ldconfig && \
    cd / && \
    rm -rf /libpostal

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем proto файлы и генерируем код
COPY protos/ ./protos/
RUN python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/address_parser.proto

# Копируем код сервера
COPY server.py .

# Открываем порт для gRPC
EXPOSE 50052

# Запускаем сервер
CMD ["python", "server.py"]
