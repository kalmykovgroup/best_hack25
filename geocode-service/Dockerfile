FROM python:3.11-slim

WORKDIR /app

# Установить системные зависимости
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Установить Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копировать proto файлы
COPY protos/ ./protos/

# Генерировать gRPC код для всех proto файлов
RUN python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/geocode.proto && \
    python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/address_corrector.proto && \
    python -m grpc_tools.protoc \
    -I./protos \
    --python_out=. \
    --grpc_python_out=. \
    ./protos/address_parser.proto

# Копировать код приложения
COPY init_db.py basic_search.py advanced_search.py server.py ./
COPY docker-entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

ENV DB_PATH=/data/db/moscow.db
ENV PYTHONUNBUFFERED=1

EXPOSE 50054

ENTRYPOINT ["/entrypoint.sh"]
