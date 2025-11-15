# Production Deployment Guide

## Обзор

В production режиме ASP.NET Core API обслуживает как backend endpoints, так и статические файлы React приложения из корня (`/`).

```
┌─────────────────────────────────────────────┐
│         ASP.NET Core API (порт 7082)        │
├─────────────────────────────────────────────┤
│  /                    → index.html (React)  │
│  /assets/*            → статика (JS/CSS)    │
│  /api/geocode/*       → REST API            │
│  /hubs/geocode        → SignalR Hub         │
│  /health              → Health Check        │
└─────────────────────────────────────────────┘
```

---

## Подготовка к deployment

### 1. Сборка React приложения

```bash
cd react-app
npm run build:prod
```

**Результат:**
- Файлы собираются в `api/wwwroot/`
- Применяется минификация (Terser)
- Удаляются `console.*` (кроме `console.error`)
- Генерируются source maps для отладки
- Код разделяется на chunks: vendor, redux, signalr

**Размеры бандлов:**
- `vendor.js` — ~14 KB (React, React-DOM, React-Redux)
- `redux.js` — ~23 KB (Redux Toolkit)
- `signalr.js` — ~56 KB (SignalR Client)
- `index.js` — ~193 KB (приложение)
- `index.css` — ~6 KB (стили)

### 2. Проверка wwwroot

```bash
ls api/wwwroot
```

Должны быть:
```
index.html
vite.svg
assets/
  ├── index-[hash].js
  ├── index-[hash].css
  ├── vendor-[hash].js
  ├── redux-[hash].js
  └── signalr-[hash].js
```

### 3. Запуск микросервисов

**Address Parser (libpostal):**
```bash
cd address-parser
docker-compose up -d
```

**Python Geocode Service:**
```bash
cd python-search
python grpc_server.py
```

### 4. Запуск ASP.NET Core API

```bash
cd api
dotnet run --configuration Release
```

---

## Конфигурация Production

### Program.cs

```csharp
// Статические файлы (React приложение)
app.UseDefaultFiles();  // Ищет index.html
app.UseStaticFiles();   // Обслуживает файлы из wwwroot

// SPA Fallback - все не-API запросы возвращают index.html
app.MapFallbackToFile("index.html");
```

### Vite.config.ts

```typescript
build: {
  outDir: '../api/wwwroot',
  emptyOutDir: true,

  // Минификация
  minify: 'terser',
  terserOptions: {
    compress: {
      drop_console: true,      // Удаляем console.*
      drop_debugger: true,
    },
  },

  // Chunk splitting
  rollupOptions: {
    output: {
      manualChunks: {
        vendor: ['react', 'react-dom', 'react-redux'],
        redux: ['@reduxjs/toolkit'],
        signalr: ['@microsoft/signalr'],
      },
    },
  },
}
```

---

## Тестирование Production

### 1. Запустите API

```bash
cd api
dotnet run --configuration Release
```

### 2. Проверка endpoints

**React приложение (корень):**
```
https://localhost:7082/
```

**API endpoints:**
```
https://localhost:7082/api/geocode/search-batch
https://localhost:7082/api/geocode/status
```

**SignalR Hub:**
```
wss://localhost:7082/hubs/geocode
```

**Health Check:**
```
https://localhost:7082/health
```

### 3. Проверка логов

При старте API должны появиться логи подключения к микросервисам:

```
╔═══════════════════════════════════════════════════════════════════╗
║  🔍 ПРОВЕРКА ПОДКЛЮЧЕНИЯ К МИКРОСЕРВИСАМ                         ║
╚═══════════════════════════════════════════════════════════════════╝
✅ Python Geocode Service (порт 50051):    ПОДКЛЮЧЕН
✅ Address Parser Service (порт 50052):    ПОДКЛЮЧЕН
═══════════════════════════════════════════════════════════════════
```

### 4. Проверка React приложения

Откройте браузер:
```
https://localhost:7082/
```

Должно загрузиться React приложение с геокодированием.

---

## Deployment на сервер

### Вариант 1: Docker

TODO: Добавить Dockerfile для API + React

### Вариант 2: Systemd (Linux)

**1. Скопируйте файлы на сервер:**
```bash
scp -r api/ user@server:/var/www/geocode-api
```

**2. Создайте systemd сервис:**
```bash
sudo nano /etc/systemd/system/geocode-api.service
```

```ini
[Unit]
Description=Geocode API
After=network.target

[Service]
WorkingDirectory=/var/www/geocode-api
ExecStart=/usr/bin/dotnet api.dll
Restart=always
RestartSec=10
KillSignal=SIGINT
SyslogIdentifier=geocode-api
User=www-data
Environment=ASPNETCORE_ENVIRONMENT=Production
Environment=DOTNET_PRINT_TELEMETRY_MESSAGE=false

[Install]
WantedBy=multi-user.target
```

**3. Запустите сервис:**
```bash
sudo systemctl enable geocode-api
sudo systemctl start geocode-api
sudo systemctl status geocode-api
```

### Вариант 3: IIS (Windows)

**1. Установите .NET Hosting Bundle:**
- https://dotnet.microsoft.com/download/dotnet/9.0

**2. Опубликуйте приложение:**
```bash
cd api
dotnet publish -c Release -o publish
```

**3. Создайте сайт в IIS:**
- Physical path: `C:\path\to\api\publish`
- Application Pool: No Managed Code
- Bindings: HTTPS на порту 443

**4. Настройте web.config** (создается автоматически при publish).

---

## CORS Configuration

В production измените CORS policy в `Program.cs`:

```csharp
builder.Services.AddCors(options =>
{
    options.AddPolicy("ReactApp", policy =>
    {
        policy.WithOrigins("https://yourdomain.com")  // ← Замените на ваш домен
            .AllowAnyHeader()
            .AllowAnyMethod()
            .AllowCredentials();
    });
});
```

---

## Переменные окружения

Создайте `appsettings.Production.json`:

```json
{
  "Logging": {
    "LogLevel": {
      "Default": "Information",
      "Microsoft.AspNetCore": "Warning"
    }
  },
  "PythonService": {
    "Url": "http://localhost:50051"
  },
  "AddressParserService": {
    "Url": "http://localhost:50052"
  },
  "AllowedHosts": "*"
}
```

---

## Мониторинг

### Health Check

```bash
curl https://yourdomain.com/health
```

Ответ:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-15T10:30:00Z"
}
```

### Логи

**ASP.NET Core:**
```bash
journalctl -u geocode-api -f
```

**Python Geocode:**
```bash
tail -f python-search/logs/grpc_server.log
```

**Address Parser:**
```bash
docker logs -f address-parser
```

---

## Troubleshooting

### ❌ 404 на корне (`/`)

**Причина:** React приложение не собрано или не в `api/wwwroot/`

**Решение:**
```bash
cd react-app
npm run build:prod
ls ../api/wwwroot  # Проверьте наличие index.html
```

### ❌ SignalR не подключается

**Причина:** CORS или HTTPS проблемы

**Решение:**
- Проверьте CORS policy
- Убедитесь, что SignalR использует правильный протокол (wss:// для HTTPS)

### ❌ API возвращает 503 Service Unavailable

**Причина:** Микросервисы не запущены

**Решение:**
```bash
# Проверьте Python Geocode Service
curl http://localhost:50051

# Проверьте Address Parser
curl http://localhost:50052
```

---

## Команды для быстрого деплоя

```bash
# 1. Сборка React
cd react-app && npm run build:prod && cd ..

# 2. Запуск микросервисов
cd address-parser && docker-compose up -d && cd ..
cd python-search && python grpc_server.py &

# 3. Запуск API
cd api && dotnet run --configuration Release
```

---

**Версия:** 1.0
**Дата:** 2025-11-15
**Автор:** Claude Code
