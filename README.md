# Best Hack 2025 - Address Geocoding System

Система геокодирования адресов с микросервисной архитектурой на базе C# Web API и Python gRPC сервисов.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                       Frontend (React)                      │
│                     localhost:5173/3000                     │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   C# Web API (ASP.NET Core)                 │
│                      localhost:5000/5001                    │
│  • REST API endpoints                                       │
│  • SignalR Hub для реального времени                        │
│  • gRPC клиенты для Python сервисов                        │
└──────────────┬───────────────────────────┬──────────────────┘
               │ gRPC                      │ gRPC
               ▼                           ▼
┌──────────────────────────┐  ┌───────────────────────────────┐
│  Geocode Service         │  │  Address Parser Service       │
│  (Python + gRPC)         │  │  (Python + libpostal + gRPC)  │
│  localhost:50051         │  │  localhost:50052              │
│                          │  │                               │
│  • Поиск адресов         │  │  • Парсинг адресов            │
│  • Геокодирование        │  │  • Нормализация адресов       │
│  • Работа с БД           │  │  • Поддержка 100+ языков      │
└──────────────────────────┘  └───────────────────────────────┘
```

## Структура проекта

```
best_hack25/
├── api/                          # C# Web API (ASP.NET Core 9.0)
│   ├── Controllers/              # REST API контроллеры
│   ├── Services/                 # Бизнес-логика и gRPC клиенты
│   │   ├── Search/               # Клиент для Geocode Service
│   │   └── AddressParser/        # Клиент для Address Parser
│   ├── Models/                   # DTOs и модели
│   ├── Hubs/                     # SignalR Hubs
│   ├── Protos/                   # Protocol Buffers definitions
│   │   ├── geocode.proto         # Geocode Service API
│   │   └── address_parser.proto  # Address Parser API
│   └── Program.cs                # Точка входа и конфигурация
│
├── geocode-service/              # Python сервис поиска адресов
│   ├── server.py                 # gRPC сервер
│   └── Dockerfile                # Docker образ
│
├── address-parser/               # Python сервис парсинга адресов
│   ├── protos/                   # Proto файлы
│   │   └── address_parser.proto  # API определение
│   ├── examples/                 # Примеры интеграции
│   │   └── csharp/               # C# примеры
│   ├── server.py                 # gRPC сервер с libpostal
│   ├── Dockerfile                # Docker образ
│   ├── README.md                 # Документация сервиса
│   ├── INTEGRATION.md            # Руководство по интеграции
│   ├── QUICKSTART.md             # Быстрый старт
│   └── WINDOWS_SETUP.md          # Настройка для Windows
│
├── docker-compose.yaml           # Оркестрация всех сервисов
├── .env                          # Переменные окружения
├── .env.example                  # Пример конфигурации
└── SETUP_GUIDE.md               # Руководство по настройке

```

## Технологии

### Backend
- **C# API:** ASP.NET Core 9.0, SignalR, gRPC Client
- **Geocode Service:** Python 3.11, gRPC, PostgreSQL/SQLite
- **Address Parser:** Python 3.11, gRPC, libpostal

### Коммуникация
- **REST API:** HTTP/HTTPS для frontend
- **WebSocket:** SignalR для real-time обновлений
- **gRPC:** Для межсервисной коммуникации

### Infrastructure
- **Docker & Docker Compose:** Контейнеризация
- **Protocol Buffers:** Определение API
- **Environment Variables:** Конфигурация через .env

## Быстрый старт

### Предварительные требования

- Docker Desktop для Windows
- .NET 9.0 SDK (для локальной разработки C#)
- Rider или Visual Studio (опционально)

### 1. Клонируйте проект

```bash
cd "C:\Users\Apolon 1\RiderProjects\best_hack25"
```

### 2. Проверьте .env файл

Файл уже настроен с правильными портами и URLs:

```env
# Порты
API_HTTP_PORT=5000
GEOCODE_SERVICE_PORT=50051
ADDRESS_PARSER_PORT=50052

# URLs для Docker
PYTHON_SERVICE_URL=http://geocode-service:50051
ADDRESS_PARSER_URL=http://address-parser:50052
```

### 3. Запустите все сервисы

```bash
docker-compose up --build
```

**Важно:** Первый запуск address-parser займет 10-15 минут из-за загрузки данных libpostal.

### 4. Проверьте работу

```bash
# Проверка статуса
docker-compose ps

# Должны быть запущены:
# api, geocode-service, address-parser

# Проверка API
curl http://localhost:5000/health
```

## Сервисы и порты

| Сервис          | Порт    | Протокол | Описание                        |
|-----------------|---------|----------|---------------------------------|
| C# API          | 5000    | HTTP     | REST API                        |
| C# API          | 5001    | HTTPS    | REST API (secure)               |
| Geocode Service | 50051   | gRPC     | Поиск и геокодирование адресов  |
| Address Parser  | 50052   | gRPC     | Парсинг и нормализация адресов  |

## Документация

### Общая документация
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Полное руководство по настройке проекта
- **[.env.example](.env.example)** - Пример конфигурации

### Address Parser сервис
- **[address-parser/START_HERE.md](address-parser/START_HERE.md)** - С чего начать
- **[address-parser/README.md](address-parser/README.md)** - Полная документация
- **[address-parser/QUICKSTART.md](address-parser/QUICKSTART.md)** - Быстрый старт за 5 минут
- **[address-parser/INTEGRATION.md](address-parser/INTEGRATION.md)** - Интеграция с C#
- **[address-parser/WINDOWS_SETUP.md](address-parser/WINDOWS_SETUP.md)** - Настройка для Windows
- **[address-parser/PROJECT_STRUCTURE.md](address-parser/PROJECT_STRUCTURE.md)** - Структура проекта

### C# API
- **[api/Protos/geocode.proto](api/Protos/geocode.proto)** - Geocode Service API
- **[api/Protos/address_parser.proto](api/Protos/address_parser.proto)** - Address Parser API

## Примеры использования

### 1. Парсинг адреса

**Запрос:**
```bash
curl -X POST http://localhost:5000/api/address/parse \
  -H "Content-Type: application/json" \
  -d '{
    "address": "Москва, ул. Тверская, д. 10, кв. 5",
    "country": "RU"
  }'
```

**Ответ:**
```json
{
  "original": "Москва, ул. Тверская, д. 10, кв. 5",
  "components": {
    "city": "Москва",
    "street": "Тверская",
    "houseNumber": "10",
    "unit": "5"
  },
  "executionTimeMs": 15
}
```

### 2. Нормализация адреса

**Запрос:**
```bash
curl -X POST http://localhost:5000/api/address/normalize \
  -H "Content-Type: application/json" \
  -d '{
    "address": "г Москва ул Тверская д 10",
    "lowercase": true
  }'
```

**Ответ:**
```json
{
  "original": "г Москва ул Тверская д 10",
  "normalized": "москва улица тверская дом 10",
  "alternatives": [
    "москва тверская 10",
    "москва ул тверская 10"
  ]
}
```

### 3. Поиск адреса (Geocode)

**Запрос:**
```bash
curl -X POST http://localhost:5000/api/geocode/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Москва, Тверская, 10",
    "limit": 5
  }'
```

## Разработка

### Сценарий 1: Все в Docker (Production-like)

```bash
docker-compose up --build
```

### Сценарий 2: C# локально, Python в Docker

```bash
# Запустите Python сервисы
docker-compose up geocode-service address-parser

# В другом терминале запустите C# API
cd api
dotnet run
```

### Сценарий 3: Только один сервис

```bash
# Только Address Parser
docker-compose up address-parser

# Только Geocode Service
docker-compose up geocode-service
```

## Управление сервисами

### Запуск

```bash
# Все сервисы
docker-compose up -d

# С пересборкой
docker-compose up --build

# Только один сервис
docker-compose up address-parser
```

### Остановка

```bash
# Остановить все
docker-compose down

# Остановить с удалением volumes
docker-compose down -v

# Остановить один сервис
docker-compose stop address-parser
```

### Логи

```bash
# Все логи
docker-compose logs -f

# Логи одного сервиса
docker-compose logs -f address-parser

# Последние 100 строк
docker-compose logs --tail=100 address-parser
```

### Статус

```bash
# Проверка статуса
docker-compose ps

# Детальная информация
docker inspect <container_id>
```

## Интеграция Address Parser в C# API

Подробное руководство см. в [address-parser/INTEGRATION.md](address-parser/INTEGRATION.md)

### Краткая версия:

1. **Добавьте proto файл** в `api/Protos/address_parser.proto`

2. **Обновите api.csproj:**
   ```xml
   <Protobuf Include="Protos\address_parser.proto" GrpcServices="Client" />
   ```

3. **Скопируйте клиент:**
   ```bash
   cp address-parser/examples/csharp/* api/Services/AddressParser/
   ```

4. **Зарегистрируйте в Program.cs:**
   ```csharp
   builder.Services.AddScoped<IAddressParserClient, AddressParserClient>();
   ```

5. **Используйте в контроллерах:**
   ```csharp
   var response = await _addressParser.ParseAddressAsync(address);
   ```

## Troubleshooting

### Проблема: Сервис не запускается

**Решение:**
```bash
# Проверьте логи
docker-compose logs address-parser

# Пересоберите образ
docker-compose build --no-cache address-parser

# Перезапустите
docker-compose restart address-parser
```

### Проблема: "Connection refused"

**Причины и решения:**
1. Сервис не запущен: `docker-compose ps`
2. Неправильный URL в конфигурации
3. Firewall блокирует порты

### Проблема: Address Parser долго запускается

**Это нормально!** Первый запуск загружает ~1.5GB данных libpostal (10-15 минут).

При следующих запусках данные будут в кэше Docker volume.

### Проблема: Ошибки на Windows при локальной установке

**Решение:** Используйте Docker. См. [address-parser/WINDOWS_SETUP.md](address-parser/WINDOWS_SETUP.md)

## Environment Variables

Все переменные окружения настраиваются в `.env` файле:

```env
# API Ports
API_HTTP_PORT=5000
API_HTTPS_PORT=5001

# Service Ports
GEOCODE_SERVICE_PORT=50051
ADDRESS_PARSER_PORT=50052

# Service URLs (для Docker)
PYTHON_SERVICE_URL=http://geocode-service:50051
ADDRESS_PARSER_URL=http://address-parser:50052

# Settings
ASPNETCORE_ENVIRONMENT=Development
PYTHONUNBUFFERED=1
GRPC_TIMEOUT_SECONDS=30
```

## Contributing

### Добавление нового микросервиса

1. Создайте папку для сервиса
2. Добавьте `Dockerfile`
3. Добавьте сервис в `docker-compose.yaml`
4. Обновите `.env` с новыми переменными
5. Обновите документацию

### Добавление нового API endpoint

1. Создайте/обновите proto файл
2. Сгенерируйте код: `dotnet build`
3. Создайте клиент в `Services/`
4. Создайте контроллер в `Controllers/`
5. Зарегистрируйте в `Program.cs`

## Performance

### Address Parser
- **Парсинг:** 10-50ms
- **Нормализация:** 5-30ms
- **Пропускная способность:** ~1000 req/sec

### Geocode Service
- **Поиск:** зависит от БД и индексов
- **Рекомендуется:** добавить кэширование

## Security

### Production настройки:

1. Используйте HTTPS для API
2. Включите TLS для gRPC
3. Добавьте authentication/authorization
4. Настройте rate limiting
5. Используйте secrets для sensitive data

## Roadmap

- [ ] Добавить кэширование для частых запросов
- [ ] Prometheus metrics для мониторинга
- [ ] Grafana dashboards
- [ ] CI/CD pipeline
- [ ] Unit и Integration тесты
- [ ] Kubernetes deployment
- [ ] API documentation (Swagger/OpenAPI)

## License

MIT

## Контакты

- **GitHub:** [best_hack25](https://github.com/your-repo)
- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)

---

**Для начала работы:** См. [SETUP_GUIDE.md](SETUP_GUIDE.md) или [address-parser/START_HERE.md](address-parser/START_HERE.md)
