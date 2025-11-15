# Руководство по запуску с Docker

## Быстрый старт

### 1. Подготовка

Убедитесь, что установлены:
- Docker Desktop (для Windows)
- Docker Compose

### 2. Настройка переменных окружения

Файл `.env` уже создан с базовыми настройками. При необходимости отредактируйте его:

```bash
# Просмотреть переменные
cat .env

# Или скопировать из примера
cp .env.example .env
```

### 3. Запуск всех сервисов

```bash
# Запустить все сервисы
docker-compose up -d

# Посмотреть логи
docker-compose logs -f

# Посмотреть логи конкретного сервиса
docker-compose logs -f geocode-service
```

### 4. Проверка работы

```bash
# Проверить статус контейнеров
docker-compose ps

# Проверить здоровье сервисов
docker-compose ps
```

## Структура сервисов

### 1. API (C# ASP.NET Core)
- **Порты**: 5000 (HTTP), 5001 (HTTPS)
- **Эндпоинт**: http://localhost:5000
- **Зависимости**: geocode-service, address-parser

### 2. Geocode Service (Python gRPC)
- **Порт**: 50051
- **Назначение**: Поиск адресов по нормализованной строке
- **Тестовые данные**: 5 адресов (Москва, СПб)

### 3. Address Parser (Python + libpostal)
- **Порт**: 50052
- **Назначение**: Парсинг и нормализация адресов

## Команды Docker Compose

### Запуск и остановка

```bash
# Запустить все сервисы
docker-compose up -d

# Запустить конкретный сервис
docker-compose up -d geocode-service

# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes
docker-compose down -v
```

### Перезапуск

```bash
# Перезапустить все сервисы
docker-compose restart

# Перезапустить конкретный сервис
docker-compose restart geocode-service
```

### Пересборка

```bash
# Пересобрать все образы
docker-compose build

# Пересобрать конкретный сервис
docker-compose build geocode-service

# Пересобрать и запустить
docker-compose up -d --build
```

### Логи

```bash
# Все логи в реальном времени
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f geocode-service

# Последние 100 строк
docker-compose logs --tail=100 geocode-service
```

### Отладка

```bash
# Зайти внутрь контейнера
docker-compose exec geocode-service /bin/bash

# Или для Alpine-based образов
docker-compose exec geocode-service /bin/sh

# Выполнить команду в контейнере
docker-compose exec geocode-service python --version
```

## Конфигурация портов

Порты настраиваются в `.env` файле:

```env
# C# API
API_HTTP_PORT=5000
API_HTTPS_PORT=5001

# Python Geocode Service
GEOCODE_SERVICE_PORT=50051

# Address Parser Service
ADDRESS_PARSER_PORT=50052
```

Чтобы изменить порты:
1. Отредактируйте `.env`
2. Перезапустите: `docker-compose up -d`

## Health Checks

Все сервисы имеют health checks:

```bash
# Проверить статус
docker-compose ps

# Вывод покажет:
# - healthy - сервис работает
# - unhealthy - сервис не работает
# - starting - сервис стартует
```

## Volumes

Проект использует volume для кэширования данных libpostal:

```bash
# Посмотреть volumes
docker volume ls

# Удалить все volumes
docker-compose down -v
```

## Сети

Все сервисы находятся в одной сети `app-network`:

```bash
# Посмотреть сети
docker network ls

# Информация о сети
docker network inspect best_hack25_app-network
```

## Troubleshooting

### Порт уже занят

```bash
# Найти процесс на порту (Windows)
netstat -ano | findstr :5000

# Убить процесс
taskkill /PID <PID> /F

# Или изменить порт в .env
```

### Контейнер не запускается

```bash
# Посмотреть логи
docker-compose logs geocode-service

# Пересобрать образ
docker-compose build --no-cache geocode-service
docker-compose up -d geocode-service
```

### Проблемы с сетью между контейнерами

```bash
# Проверить сеть
docker network inspect best_hack25_app-network

# Перезапустить все сервисы
docker-compose down
docker-compose up -d
```

### Очистить все

```bash
# Остановить и удалить всё
docker-compose down -v --remove-orphans

# Удалить неиспользуемые образы
docker image prune -a

# Полная очистка Docker
docker system prune -a --volumes
```

## Production режим

Для production измените `.env`:

```env
ASPNETCORE_ENVIRONMENT=Production
ENABLE_VERBOSE_LOGGING=0
```

И пересоберите:

```bash
docker-compose down
docker-compose build
docker-compose up -d
```

## Мониторинг

### Статистика использования ресурсов

```bash
# Посмотреть использование CPU/Memory
docker stats

# Для конкретного контейнера
docker stats best_hack25-geocode-service-1
```

### Проверка работоспособности

```bash
# Health check Python Geocode Service
curl http://localhost:50051

# Health check C# API
curl http://localhost:5000/health
```

## Интеграция с CI/CD

Пример для GitHub Actions:

```yaml
- name: Build and run services
  run: |
    cp .env.example .env
    docker-compose up -d
    docker-compose ps
```

## Полезные ссылки

- [Docker Compose документация](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
