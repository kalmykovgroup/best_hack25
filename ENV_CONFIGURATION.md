# Environment Configuration Guide

## Обзор

Проект использует файлы `.env` для конфигурации как React приложения, так и C# API.

## Структура конфигурации

```
best_hack25/
├── react-app/
│   ├── .env                    # Development (React)
│   └── .env.production         # Production (React)
└── api/
    ├── .env.development        # Development (C# API)
    └── .env.production         # Production (C# API)
```

---

## React App Configuration

### Development (.env)

```env
# SignalR Hub URL (C# Backend)
VITE_SIGNALR_HUB_URL=http://localhost:5034/hubs/geocode

# Search settings
VITE_SEARCH_DEBOUNCE=300
VITE_SEARCH_THROTTLE=100
VITE_SEARCH_LIMIT=10

# Cache settings
VITE_CACHE_ENABLED=true
VITE_CACHE_TTL=300000
VITE_CACHE_SIZE=100

# Throttle settings
VITE_THROTTLE_ENABLED=true
```

### Production (.env.production)

```env
# SignalR Hub URL (C# Backend)
# Вариант 1: Относительный путь (если React и API на одном домене)
VITE_SIGNALR_HUB_URL=/hubs/geocode

# Вариант 2: Абсолютный URL (если React и API на разных доменах)
# VITE_SIGNALR_HUB_URL=https://besthack25.ru/hubs/geocode

# Search settings
VITE_SEARCH_DEBOUNCE=300
VITE_SEARCH_THROTTLE=100
VITE_SEARCH_LIMIT=10

# Cache settings
VITE_CACHE_ENABLED=true
VITE_CACHE_TTL=300000
VITE_CACHE_SIZE=100

# Throttle settings
VITE_THROTTLE_ENABLED=true
```

**Важно:** Vite читает только переменные с префиксом `VITE_*`

---

## C# API Configuration

### Development (.env.development)

```env
# Domain settings
ASPNETCORE_URLS=http://localhost:5034
ASPNETCORE_ENVIRONMENT=Development

# Allowed Origins for CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000

# Python Geocode Service
PYTHON_SERVICE_URL=http://localhost:50051

# Address Parser Service
ADDRESS_PARSER_SERVICE_URL=http://localhost:50052

# SignalR Settings
SIGNALR_MAX_MESSAGE_SIZE=102400
SIGNALR_ENABLE_DETAILED_ERRORS=true

# Logging
LOGGING__LOGLEVEL__DEFAULT=Debug
LOGGING__LOGLEVEL__MICROSOFT_ASPNETCORE=Information
```

### Production (.env.production)

```env
# Domain settings
ASPNETCORE_URLS=http://0.0.0.0:5000
ASPNETCORE_ENVIRONMENT=Production
DOMAIN=besthack25.ru

# Allowed Origins for CORS (comma-separated)
ALLOWED_ORIGINS=https://besthack25.ru,https://www.besthack25.ru

# Python Geocode Service
PYTHON_SERVICE_URL=http://localhost:50051

# Address Parser Service
ADDRESS_PARSER_SERVICE_URL=http://localhost:50052

# SignalR Settings
SIGNALR_MAX_MESSAGE_SIZE=102400
SIGNALR_ENABLE_DETAILED_ERRORS=false

# Logging
LOGGING__LOGLEVEL__DEFAULT=Information
LOGGING__LOGLEVEL__MICROSOFT_ASPNETCORE=Warning
```

---

## Использование

### Development

```bash
# React
cd react-app
npm run dev

# C# API (автоматически загружает .env.development)
cd api
dotnet run
```

### Production Build

```bash
# React (использует .env.production)
cd react-app
npm run build:prod

# C# API
cd api
# Установите переменные окружения:
export $(cat .env.production | xargs)
dotnet run --environment Production
```

---

## Переменные окружения

### React (Vite)

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|----------------------|
| `VITE_SIGNALR_HUB_URL` | URL SignalR Hub | `http://localhost:5034/hubs/geocode` |
| `VITE_SEARCH_DEBOUNCE` | Debounce для поиска (ms) | `300` |
| `VITE_SEARCH_THROTTLE` | Throttle для поиска (ms) | `100` |
| `VITE_SEARCH_LIMIT` | Макс. результатов поиска | `10` |
| `VITE_CACHE_ENABLED` | Включить кэш | `true` |
| `VITE_CACHE_TTL` | Время жизни кэша (ms) | `300000` (5 мин) |
| `VITE_CACHE_SIZE` | Размер кэша | `100` |
| `VITE_THROTTLE_ENABLED` | Включить throttling | `true` |

### C# API

| Переменная | Описание | Значение по умолчанию |
|-----------|----------|----------------------|
| `ASPNETCORE_URLS` | URL сервера | `http://localhost:5034` |
| `ASPNETCORE_ENVIRONMENT` | Режим окружения | `Development` |
| `ALLOWED_ORIGINS` | CORS origins (через запятую) | `http://localhost:5173,...` |
| `PYTHON_SERVICE_URL` | URL Python gRPC сервиса | `http://localhost:50051` |
| `ADDRESS_PARSER_SERVICE_URL` | URL Address Parser сервиса | `http://localhost:50052` |
| `SIGNALR_MAX_MESSAGE_SIZE` | Макс. размер сообщения SignalR | `102400` (100KB) |
| `SIGNALR_ENABLE_DETAILED_ERRORS` | Детальные ошибки SignalR | `true` (dev) / `false` (prod) |
| `LOGGING__LOGLEVEL__DEFAULT` | Уровень логирования | `Debug` (dev) / `Information` (prod) |

---

## Deployment

### Option 1: Переменные окружения системы (Linux)

```bash
# Создайте systemd service файл
sudo nano /etc/systemd/system/besthack25.service

[Service]
...
EnvironmentFile=/var/www/besthack25/api/.env.production
```

### Option 2: Docker Compose

```yaml
version: '3.8'
services:
  api:
    build: ./api
    env_file:
      - ./api/.env.production
    ports:
      - "5000:5000"
```

### Option 3: Docker Run

```bash
docker run --env-file ./api/.env.production -p 5000:5000 besthack25-api
```

---

## Безопасность

**НЕ коммитьте файлы .env в git!**

`.gitignore` уже настроен:
```gitignore
.env
.env.local
.env.*.local
.env.production
```

**Для production:**
1. Создайте `.env.production` на сервере
2. Установите правильные права доступа:
   ```bash
   chmod 600 .env.production
   ```
3. Используйте секреты для чувствительных данных (Azure Key Vault, AWS Secrets Manager, etc.)

---

## Проверка конфигурации

### React

```bash
cd react-app
npm run build:prod

# Проверьте, какой URL используется
cat dist/assets/index-*.js | grep -o 'hubUrl:"[^"]*"'
```

### C# API

```bash
cd api
dotnet run --environment Production

# В логах должно быть:
# CORS configured for: https://besthack25.ru, ...
# Python Service URL: http://localhost:50051
# Address Parser Service URL: http://localhost:50052
```

---

## Troubleshooting

### React не подключается к API

1. Проверьте `VITE_SIGNALR_HUB_URL` в `.env.production`
2. Убедитесь, что используете относительный путь для одного домена
3. Проверьте CORS на сервере

### API не принимает запросы

1. Проверьте `ASPNETCORE_URLS` - должен быть `http://0.0.0.0:5000` для production
2. Проверьте `ALLOWED_ORIGINS` - должен содержать ваш домен
3. Убедитесь, что `.env.production` загружен:
   ```bash
   export $(cat .env.production | xargs)
   dotnet run
   ```

### Микросервисы недоступны

1. Проверьте `PYTHON_SERVICE_URL` и `ADDRESS_PARSER_SERVICE_URL`
2. Убедитесь, что сервисы запущены:
   ```bash
   # Python Geocode
   python python-search/grpc_server.py

   # Address Parser
   docker-compose up address-parser
   ```

---

**Готово! Конфигурация настроена правильно. 🚀**
