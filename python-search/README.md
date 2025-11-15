# Python gRPC Service для геокодирования

Тестовый Python gRPC сервис для обработки запросов на поиск адресов.

## Варианты запуска

### Вариант 1: Docker (рекомендуется)

Из корневой директории проекта:
```bash
docker-compose up -d
```

См. **[DOCKER_README.md](DOCKER_README.md)** для подробностей.

### Вариант 2: Локально в PyCharm

См. **[PYCHARM_GUIDE.md](PYCHARM_GUIDE.md)** или **[QUICK_START_PYCHARM.md](QUICK_START_PYCHARM.md)**.

### Вариант 3: Локальный запуск (командная строка)

## Установка (для локального запуска)

1. Активируйте виртуальное окружение (если есть):
```bash
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac
```

2. Установите зависимости:
```bash
pip install grpcio grpcio-tools protobuf
```

**Важно**: Если у вас Python 3.13, используйте команду выше вместо `pip install -r requirements.txt`

3. Сгенерируйте gRPC код из .proto файла:
```bash
python generate_grpc.py
```

## Запуск

Запустите сервер:
```bash
python grpc_server.py
```

Сервер будет слушать на порту **50051**.

## Тестирование

Вы можете протестировать сервис с помощью grpcurl:

```bash
# Поиск адреса
grpcurl -plaintext -d '{"normalized_query": "Москва", "limit": 5, "request_id": "test"}' localhost:50051 geocode.GeocodeService/SearchAddress

# Health check
grpcurl -plaintext localhost:50051 geocode.GeocodeService/HealthCheck
```

## Структура файлов

- `geocode.proto` - Protobuf контракт (скопирован из C# проекта)
- `generate_grpc.py` - Скрипт для генерации Python кода из .proto
- `grpc_server.py` - Реализация gRPC сервера
- `geocode_pb2.py` - Сгенерированный Protobuf код (создается автоматически)
- `geocode_pb2_grpc.py` - Сгенерированный gRPC код (создается автоматически)
- `Dockerfile` - Конфигурация Docker образа
- `.dockerignore` - Исключения для Docker build

## Документация

- **[DOCKER_README.md](DOCKER_README.md)** - Запуск в Docker
- **[PYCHARM_GUIDE.md](PYCHARM_GUIDE.md)** - Полное руководство по PyCharm
- **[QUICK_START_PYCHARM.md](QUICK_START_PYCHARM.md)** - Быстрый старт в PyCharm

## Тестовые данные

Сервис возвращает тестовые данные с адресами:
- Москва, Тверская улица, 7
- Москва, Красная площадь, 1
- Москва, проспект Мира, 119
- Санкт-Петербург, Невский проспект, 28
- Москва, улица Арбат, 10

В реальной версии тестовые данные будут заменены на подключение к базе данных.
