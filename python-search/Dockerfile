# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir grpcio grpcio-tools protobuf

# Копируем все файлы проекта
COPY . .

# Генерируем gRPC код из proto файла
RUN python generate_grpc.py

# Открываем порт для gRPC
EXPOSE 50051

# Устанавливаем переменные окружения
ENV PYTHONUNBUFFERED=1
ENV GRPC_PORT=50051

# Запускаем gRPC сервер
CMD ["python", "grpc_server.py"]
