# Deployment Guide - Best Hack 25

## Архитектура

React приложение и C# API работают на **одном домене** (besthack25.ru):
- C# API обслуживает как API эндпоинты, так и статические файлы React
- React собирается в `api/wwwroot` и обслуживается ASP.NET Core
- SignalR использует относительный путь `/hubs/geocode`

```
https://besthack25.ru/
├── /                         → React приложение (index.html)
├── /assets/                  → JS, CSS файлы React
├── /hubs/geocode             → SignalR Hub
├── /api/*                    → REST API эндпоинты (если есть)
└── /health                   → Health check
```

## Предварительные требования

### Микросервисы
Перед деплоем убедитесь, что запущены оба микросервиса:

1. **Python Geocode Service** (порт 50051)
   ```bash
   cd python-search
   python grpc_server.py
   ```

2. **Address Parser Service** (порт 50052)
   ```bash
   cd address-parser
   docker-compose up -d
   ```

## Production Build

### Шаг 1: Сборка React приложения

```bash
cd react-app

# Production build (публикуется в ../api/wwwroot)
npm run build:prod
```

Это создаст оптимизированную сборку:
- **Минификация**: Все JS/CSS минифицированы через Terser
- **Code Splitting**: Разделение на chunks (vendor, redux, signalr)
- **Console.log удалены**: Только `console.error` остается
- **Source maps**: Генерируются для отладки (можно отключить)

### Шаг 2: Публикация C# API

```bash
cd api

# Production publish
dotnet publish -c Release -o ./publish
```

### Шаг 3: Конфигурация

Убедитесь, что `appsettings.Production.json` настроен:

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
  "AllowedHosts": "besthack25.ru"
}
```

## Deployment Options

### Option 1: Systemd Service (Linux)

Создайте systemd service:

```bash
sudo nano /etc/systemd/system/besthack25.service
```

```ini
[Unit]
Description=Best Hack 25 API
After=network.target

[Service]
Type=notify
WorkingDirectory=/var/www/besthack25
ExecStart=/usr/bin/dotnet /var/www/besthack25/api.dll
Restart=always
RestartSec=10
KillSignal=SIGINT
SyslogIdentifier=besthack25
User=www-data
Environment=ASPNETCORE_ENVIRONMENT=Production
Environment=DOTNET_PRINT_TELEMETRY_MESSAGE=false

[Install]
WantedBy=multi-user.target
```

Запуск:
```bash
sudo systemctl enable besthack25
sudo systemctl start besthack25
sudo systemctl status besthack25
```

### Option 2: Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name besthack25.ru;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name besthack25.ru;

    ssl_certificate /etc/letsencrypt/live/besthack25.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/besthack25.ru/privkey.pem;

    # Kestrel proxy
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection keep-alive;
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # SignalR WebSocket support
    location /hubs/ {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Кэширование статических файлов
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        proxy_pass http://localhost:5000;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Option 3: Docker

```dockerfile
# Dockerfile
FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build
WORKDIR /src

# Copy React app
COPY react-app/package*.json ./react-app/
RUN cd react-app && npm ci

COPY react-app/ ./react-app/
RUN cd react-app && npm run build:prod

# Copy API
COPY api/*.csproj ./api/
RUN cd api && dotnet restore

COPY api/ ./api/
RUN cd api && dotnet publish -c Release -o /app/publish

# Runtime
FROM mcr.microsoft.com/dotnet/aspnet:9.0
WORKDIR /app
COPY --from=build /app/publish .
EXPOSE 5000
ENV ASPNETCORE_URLS=http://+:5000
ENTRYPOINT ["dotnet", "api.dll"]
```

## Проверка деплоя

После деплоя проверьте:

1. **Основная страница**: `https://besthack25.ru/`
   - Должна загрузиться React приложение

2. **Health Check**: `https://besthack25.ru/health`
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-11-15T12:34:56.789Z"
   }
   ```

3. **SignalR подключение**: Откройте DevTools в браузере
   - Должно появиться: `SignalR подключен`
   - Проверьте статусы сервисов в UI

4. **Тестовый поиск**: Введите адрес
   - Должно быть: `Найдено: N результатов`

## Мониторинг

### Логи

```bash
# Systemd logs
sudo journalctl -u besthack25 -f

# Проверка ошибок
sudo journalctl -u besthack25 --since "1 hour ago" | grep ERROR
```

### Метрики

C# API логирует:
- ✅/⚠️/❌ Статус микросервисов при старте
- Все поисковые запросы с RequestId
- Время выполнения запросов
- Ошибки подключения к микросервисам

## Troubleshooting

### React приложение не загружается

1. Проверьте, что `wwwroot` содержит файлы:
   ```bash
   ls -la api/wwwroot/
   ```

2. Проверьте, что `UseStaticFiles()` включен в `Program.cs`

### SignalR не подключается

1. Проверьте WebSocket поддержку в Nginx:
   ```nginx
   proxy_set_header Upgrade $http_upgrade;
   proxy_set_header Connection "upgrade";
   ```

2. Проверьте CORS настройки в production

### Микросервисы недоступны

1. Проверьте, что порты 50051 и 50052 открыты:
   ```bash
   netstat -tulpn | grep -E ':(50051|50052)'
   ```

2. Проверьте логи микросервисов:
   ```bash
   # Python Geocode Service
   python python-search/grpc_server.py

   # Address Parser Service
   docker-compose logs address-parser
   ```

## SSL/TLS (Let's Encrypt)

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx

# Получение сертификата
sudo certbot --nginx -d besthack25.ru

# Автоматическое обновление
sudo certbot renew --dry-run
```

## Performance Optimization

### Настройки Kestrel

В `appsettings.Production.json`:

```json
{
  "Kestrel": {
    "Limits": {
      "MaxConcurrentConnections": 100,
      "MaxConcurrentUpgradedConnections": 100
    }
  }
}
```

### Gzip Compression

Nginx уже включает gzip для текстовых файлов. Для Kestrel:

```csharp
builder.Services.AddResponseCompression(options =>
{
    options.EnableForHttps = true;
});
```

## Security Checklist

- [ ] HTTPS настроен (Let's Encrypt)
- [ ] Source maps отключены (или защищены)
- [ ] API keys не в frontend коде
- [ ] CORS настроен только для production домена
- [ ] Rate limiting настроен
- [ ] Firewall настроен (только 80, 443, SSH)

## CI/CD Example (GitHub Actions)

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: react-app/package-lock.json

      - name: Build React
        run: |
          cd react-app
          npm ci
          npm run build:prod

      - name: Setup .NET
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '9.0.x'

      - name: Publish API
        run: |
          cd api
          dotnet publish -c Release -o ./publish

      - name: Deploy to Server
        run: |
          # rsync или SSH deploy
          scp -r api/publish/* user@besthack25.ru:/var/www/besthack25/
          ssh user@besthack25.ru 'sudo systemctl restart besthack25'
```

---

**Готово к production! 🚀**

URL: https://besthack25.ru
