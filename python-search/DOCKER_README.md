# Python Geocode Service - Docker

Этот сервис упакован в Docker контейнер и интегрирован в общий `docker-compose.yaml`.

## Быстрый запуск

### Через Docker Compose (рекомендуется)

Из корневой директории проекта:

```bash
# Запустить все сервисы
docker-compose up -d

# Посмотреть логи geocode-service
docker-compose logs -f geocode-service

# Остановить
docker-compose down
```

### Отдельный запуск контейнера

```bash
# Из директории python-search
cd python-search

# Собрать образ
docker build -t geocode-service .

# Запустить контейнер
docker run -d -p 50051:50051 --name geocode-service geocode-service

# Посмотреть логи
docker logs -f geocode-service

# Остановить
docker stop geocode-service
docker rm geocode-service
```

## Структура Docker

### Dockerfile

- Базовый образ: `python:3.11-slim`
- Установка зависимостей: `grpcio`, `grpcio-tools`, `protobuf`
- Автоматическая генерация gRPC кода из `.proto`
- Порт: `50051`

### Переменные окружения

Настраиваются в `.env` в корне проекта:

```env
GEOCODE_SERVICE_PORT=50051
GEOCODE_SERVICE_GRPC_PORT=50051
```

## Проверка работы

### Health Check

```bash
# Через Docker
docker-compose exec geocode-service python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); print('OK')"

# Статус контейнера
docker-compose ps geocode-service
```

### Тестовый запрос (если установлен grpcurl)

```bash
grpcurl -plaintext -d '{"normalized_query": "Москва", "limit": 5, "request_id": "test"}' localhost:50051 geocode.GeocodeService/SearchAddress
```

## Отладка

### Зайти в контейнер

```bash
docker-compose exec geocode-service /bin/bash
```

### Посмотреть логи

```bash
docker-compose logs --tail=100 geocode-service
```

### Перезапустить сервис

```bash
docker-compose restart geocode-service
```

### Пересобрать образ

```bash
docker-compose build geocode-service
docker-compose up -d geocode-service
```

## Интеграция с другими сервисами

Geocode Service автоматически доступен для других контейнеров по имени `geocode-service:50051`.

C# API подключается через:
```env
PYTHON_SERVICE_URL=http://geocode-service:50051
```

## Тестовые данные

Сервис возвращает 5 тестовых адресов:
1. Москва, Тверская улица, 7
2. Москва, Красная площадь, 1
3. Москва, проспект Мира, 119
4. Санкт-Петербург, Невский проспект, 28
5. Москва, улица Арбат, 10

## Производительность

- Thread pool: 10 workers
- Health check: каждые 30 секунд
- Startup period: 10 секунд

---

**Подробная документация**: См. `/DOCKER_GUIDE.md` в корне проекта
