# Настройка Docker завершена

## Что было сделано

### 1. Python gRPC сервис (python-search)

Создан Dockerfile для запуска в контейнере:
- Базовый образ: Python 3.11
- Автоматическая генерация gRPC кода
- Порт: 50051
- Health checks

**Файлы:**
- `python-search/Dockerfile`
- `python-search/.dockerignore`

### 2. Docker Compose

Обновлен `docker-compose.yaml`:
- Python Geocode Service настроен на `./python-search`
- Все порты вынесены в переменные окружения
- Health checks для всех сервисов
- Правильные зависимости между сервисами

**Сервисы:**
1. **api** (C# Web API) - порты 5000, 5001
2. **geocode-service** (Python gRPC) - порт 50051
3. **address-parser** (Python + libpostal) - порт 50052

### 3. Переменные окружения

Создан `.env` файл с конфигурацией:

```env
# API
API_HTTP_PORT=5000
API_HTTPS_PORT=5001
ASPNETCORE_ENVIRONMENT=Development

# Geocode Service
GEOCODE_SERVICE_PORT=50051
GEOCODE_SERVICE_GRPC_PORT=50051

# Address Parser
ADDRESS_PARSER_PORT=50052
ADDRESS_PARSER_GRPC_PORT=50052

# Service URLs
PYTHON_SERVICE_URL=http://geocode-service:50051
ADDRESS_PARSER_URL=http://address-parser:50052
```

**Файлы:**
- `.env` - рабочая конфигурация
- `.env.example` - пример для репозитория
- `.gitignore` - защита от коммита .env

### 4. Документация

Создана полная документация:

**Общая:**
- `DOCKER_QUICK_START.md` - Быстрый старт для всего проекта
- `DOCKER_GUIDE.md` - Подробное руководство по Docker

**Python сервис:**
- `python-search/DOCKER_README.md` - Docker для Python сервиса
- `python-search/PYCHARM_GUIDE.md` - Запуск в PyCharm
- `python-search/QUICK_START_PYCHARM.md` - Краткая шпаргалка
- `python-search/README.md` - Обновлен с вариантами запуска

### 5. Исправления

**Проблемы Python 3.13:**
- Обновлен `requirements.txt` (гибкие версии)
- Исправлена кодировка UTF-8 в Windows
- Обновлены скрипты `generate_grpc.py` и `grpc_server.py`

## Как запустить

### Вариант 1: Docker (рекомендуется)

```bash
# Из корня проекта
docker-compose up -d

# Проверить статус
docker-compose ps

# Логи
docker-compose logs -f

# Остановить
docker-compose down
```

### Вариант 2: Локально (PyCharm)

См. `python-search/QUICK_START_PYCHARM.md`

## Проверка работы

После запуска Docker:

```bash
# Статус контейнеров
docker-compose ps

# Все сервисы должны быть "Up (healthy)"

# Проверка портов
curl http://localhost:5000/health        # C# API
# Python gRPC доступен на localhost:50051
# Address Parser на localhost:50052
```

## Структура проекта

```
best_hack25/
├── .env                        # Переменные окружения
├── .env.example               # Пример конфигурации
├── .gitignore                 # Исключения Git
├── docker-compose.yaml        # Docker Compose конфигурация
├── DOCKER_QUICK_START.md      # Быстрый старт
├── DOCKER_GUIDE.md            # Подробное руководство
├── SETUP_COMPLETE.md          # Этот файл
│
├── api/                       # C# Web API
│   └── Dockerfile
│
├── python-search/             # Python Geocode Service
│   ├── Dockerfile
│   ├── .dockerignore
│   ├── geocode.proto
│   ├── generate_grpc.py
│   ├── grpc_server.py
│   ├── requirements.txt
│   ├── README.md              # Обновлен
│   ├── DOCKER_README.md       # Docker руководство
│   ├── PYCHARM_GUIDE.md       # PyCharm полное
│   └── QUICK_START_PYCHARM.md # PyCharm краткое
│
└── address-parser/            # Address Parser Service
    └── Dockerfile
```

## Следующие шаги

1. **Запустите проект:**
   ```bash
   docker-compose up -d
   ```

2. **Проверьте работу:**
   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

3. **Подключите фронтенд** (React) к API на localhost:5000

4. **Замените тестовые данные** в `grpc_server.py` на реальную БД

## Полезные команды

```bash
# Перезапустить один сервис
docker-compose restart geocode-service

# Пересобрать и запустить
docker-compose up -d --build

# Посмотреть логи
docker-compose logs -f geocode-service

# Зайти в контейнер
docker-compose exec geocode-service /bin/bash

# Очистить всё
docker-compose down -v
```

## Troubleshooting

### Порт занят
```bash
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Пересборка
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Логи
```bash
docker-compose logs --tail=100 geocode-service
```

---

## Готово к работе!

Все сервисы настроены и готовы к запуску в Docker.

**Быстрый старт:** См. `DOCKER_QUICK_START.md`
