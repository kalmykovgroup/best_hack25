# Быстрый старт

## Структура проекта

```
best_hack25/
├── api/                    # C# Backend (SignalR WebSocket + gRPC Client)
├── python-search/          # Python gRPC Service (тестовый)
├── react-app/              # React Frontend (будет подключаться позже)
├── INTEGRATION_GUIDE.md    # Полная документация по интеграции
└── QUICK_START.md         # Этот файл
```

## Запуск (3 простых шага)

### 1️⃣ Запустить Python gRPC сервис

```bash
cd python-search
pip install -r requirements.txt
python generate_grpc.py
python grpc_server.py
```

✅ Сервис запущен на `http://localhost:50051`

### 2️⃣ Запустить C# API

```bash
cd api
dotnet restore
dotnet run
```

✅ API запущен на `http://localhost:5000` (или `https://localhost:5001`)

### 3️⃣ Подключить React (позже)

SignalR WebSocket доступен по адресу: `ws://localhost:5000/hubs/geocode`

## Проверка работы

### Тест Python сервиса (grpcurl)

```bash
grpcurl -plaintext -d '{"query": "Москва", "limit": 5, "session_id": "test"}' localhost:50051 geocode.GeocodeService/SearchAddress
```

### Тест C# API

```bash
curl http://localhost:5000/health
```

Ответ: `{"status":"healthy","timestamp":"2025-..."}` ✅

## Что создано?

### C# API (api/)

**DTOs для WebSocket (Models/WebSocket/):**
- ✅ `GeocodeRequest.cs` - запрос от React
- ✅ `GeocodeResponse.cs` - ответ с результатами
- ✅ `GeoObjectResponse.cs` - геообъект (адрес)
- ✅ `SearchProgress.cs` - прогресс поиска

**SignalR Hub:**
- ✅ `Hubs/GeocodeHub.cs` - обработка WebSocket запросов

**gRPC Client:**
- ✅ `Services/Search/IPythonSearchClient.cs` - интерфейс
- ✅ `Services/Search/PythonSearchClient.cs` - клиент для Python

**Protobuf:**
- ✅ `Protos/geocode.proto` - контракт gRPC

**Конфигурация:**
- ✅ `Program.cs` - настроен SignalR, gRPC, CORS
- ✅ `appsettings.json` - URL Python сервиса

### Python gRPC Service (python-search/)

- ✅ `grpc_server.py` - тестовая реализация сервиса
- ✅ `generate_grpc.py` - скрипт генерации gRPC кода
- ✅ `geocode.proto` - копия protobuf контракта
- ✅ `requirements.txt` - зависимости
- ✅ Тестовые данные (5 адресов в Москве и Петербурге)

## Потоки данных

### React → C# → Python

```
React App
  ↓ (SignalR) connection.invoke("SearchAddress", { query: "Москва", limit: 10 })
C# GeocodeHub.SearchAddress()
  ↓ (gRPC) SearchAddressRequest
Python GeocodeServicer.SearchAddress()
  ↑ (gRPC) SearchAddressResponse
C# GeocodeHub
  ↑ (SignalR) Clients.Caller.SendAsync("SearchCompleted", response)
React App
```

### События SignalR

1. **SearchProgress** - промежуточные обновления
   - "processing" - начало обработки
   - "searching" - поиск в БД
   - "finalizing" - обработка результатов

2. **SearchCompleted** - финальный результат
   - `success: true` + массив результатов
   - `success: false` + сообщение об ошибке

## Следующие шаги

1. ✅ **C# и Python настроены** - можно тестировать
2. 🔄 **React интеграция** - подключите SignalR клиент (см. INTEGRATION_GUIDE.md)
3. 🔄 **Замена Python сервиса** - подключите вашу БД вместо тестовых данных

## Важные файлы

| Файл | Описание |
|------|----------|
| `INTEGRATION_GUIDE.md` | Полная документация по интеграции |
| `api/Protos/geocode.proto` | gRPC контракт (источник истины) |
| `api/Models/WebSocket/` | DTO для React ↔ C# |
| `api/Hubs/GeocodeHub.cs` | SignalR Hub |
| `python-search/grpc_server.py` | Python gRPC сервер |

## Порты

- **Python gRPC**: 50051
- **C# API HTTP**: 5000
- **C# API HTTPS**: 5001
- **React (vite)**: 5173

## Логи

- **Python**: выводятся в консоль (INFO level)
- **C# API**: выводятся в консоль (appsettings.json)

## Troubleshooting

**Ошибка подключения C# → Python:**
- Проверьте, что Python сервис запущен: `netstat -an | grep 50051`
- Проверьте URL в `appsettings.json`

**CORS ошибки:**
- Убедитесь, что React запущен на портах 3000 или 5173
- Для других портов добавьте их в `Program.cs` → `AddCors()`

**SignalR не подключается:**
- Проверьте URL: должен быть `http://localhost:5000/hubs/geocode`
- Включите логи: `.configureLogging(signalR.LogLevel.Debug)`
