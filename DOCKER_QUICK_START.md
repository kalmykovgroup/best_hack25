# Docker - Быстрый старт

## Одна команда для запуска всего проекта

```bash
docker-compose up -d
```

## Что запустится?

1. **API** (C# ASP.NET Core) - http://localhost:5000
2. **Geocode Service** (Python gRPC) - localhost:50051
3. **Address Parser** (Python + libpostal) - localhost:50052

## Основные команды

```bash
# Запустить
docker-compose up -d

# Посмотреть статус
docker-compose ps

# Логи всех сервисов
docker-compose logs -f

# Логи конкретного сервиса
docker-compose logs -f geocode-service

# Остановить
docker-compose down

# Перезапустить
docker-compose restart

# Пересобрать и запустить
docker-compose up -d --build
```

## Проверка работы

После запуска проверьте:

```bash
# Статус контейнеров
docker-compose ps

# Должны быть все 3 сервиса со статусом "Up (healthy)"
```

## Настройка

Все настройки в файле `.env`:

```env
# Порты
API_HTTP_PORT=5000
GEOCODE_SERVICE_PORT=50051
ADDRESS_PARSER_PORT=50052

# Окружение
ASPNETCORE_ENVIRONMENT=Development
```

## Остановка

```bash
# Остановить все сервисы
docker-compose down

# Остановить и удалить volumes
docker-compose down -v
```

## Troubleshooting

### Порт занят

```bash
# Windows: найти и убить процесс
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Пересборка

```bash
# Пересобрать все образы
docker-compose build --no-cache

# Запустить заново
docker-compose up -d
```

---

**Подробная документация**: См. `DOCKER_GUIDE.md`
