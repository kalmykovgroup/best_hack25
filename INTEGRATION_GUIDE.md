# Руководство по интеграции

## Обзор архитектуры

```
React App (Frontend)
    ↓ SignalR WebSocket
C# API (Backend)
    ↓ gRPC
Python Service (Search Engine)
```

## 1. Запуск сервисов

### Python gRPC Service

```bash
cd python-search

# Установить зависимости
pip install -r requirements.txt

# Сгенерировать gRPC код
python generate_grpc.py

# Запустить сервер (порт 50051)
python grpc_server.py
```

### C# API

```bash
cd api

# Восстановить пакеты
dotnet restore

# Запустить API (порт 5000/5001)
dotnet run
```

### React App

```bash
cd react-app

# Установить зависимости
npm install

# Запустить dev сервер (порт 5173)
npm run dev
```

## 2. Контракты

### SignalR WebSocket (React ↔ C#)

**Endpoint:** `ws://localhost:5000/hubs/geocode`

#### Отправка запроса от клиента:

```typescript
// Метод Hub: SearchAddress
{
  query: string;      // Поисковая строка
  limit: number;      // Макс. кол-во результатов (по умолчанию 10)
}
```

#### События от сервера:

**1. SearchProgress** - Прогресс выполнения
```typescript
{
  status: string;         // "processing" | "searching" | "finalizing"
  message: string;        // Текущее сообщение
  progressPercent: number; // 0-100
}
```

**2. SearchCompleted** - Финальный результат
```typescript
{
  success: boolean;
  errorMessage?: string;
  results: GeoObject[];
  totalFound: number;
}

interface GeoObject {
  id: string;
  formattedAddress: string;
  street?: string;
  houseNumber?: string;
  city?: string;
  district?: string;
  postalCode?: string;
  coordinates?: {
    latitude: number;
    longitude: number;
  };
  relevanceScore: number; // 0-1
}
```

### gRPC (C# ↔ Python)

**Endpoint:** `http://localhost:50051`
**Service:** `geocode.GeocodeService`

#### Метод: SearchAddress

**Request:**
```protobuf
message SearchAddressRequest {
  string query = 1;
  int32 limit = 2;
  string session_id = 3;
}
```

**Response:**
```protobuf
message SearchAddressResponse {
  bool success = 1;
  string error_message = 2;
  repeated GeoObject results = 3;
  int32 total_found = 4;
}
```

## 3. Пример использования в React

### Установка SignalR

```bash
npm install @microsoft/signalr
```

### Подключение к Hub

```typescript
import * as signalR from "@microsoft/signalr";

// Создание подключения
const connection = new signalR.HubConnectionBuilder()
  .withUrl("http://localhost:5000/hubs/geocode")
  .withAutomaticReconnect()
  .configureLogging(signalR.LogLevel.Information)
  .build();

// Подписка на события
connection.on("SearchProgress", (progress) => {
  console.log(`Прогресс: ${progress.progressPercent}%`, progress.message);
});

connection.on("SearchCompleted", (response) => {
  if (response.success) {
    console.log("Найдено результатов:", response.results);
  } else {
    console.error("Ошибка:", response.errorMessage);
  }
});

// Подключение
await connection.start();

// Отправка запроса
await connection.invoke("SearchAddress", {
  query: "Москва, Тверская",
  limit: 10
});

// Отключение
await connection.stop();
```

## 4. Настройка конфигурации

### appsettings.json (C# API)

```json
{
  "PythonService": {
    "Url": "http://localhost:50051"
  }
}
```

Для production можно переопределить через environment variables:
```bash
export PythonService__Url=http://python-service:50051
```

## 5. Замена тестового Python сервиса

Когда будете заменять тестовый Python сервис на реальный:

1. Оставьте файл `geocode.proto` без изменений
2. Регенерируйте gRPC код: `python generate_grpc.py`
3. Замените реализацию класса `GeocodeServicer` в `grpc_server.py`
4. Подключите вашу базу данных вместо `self.mock_data`

Пример подключения БД:

```python
class GeocodeServicer(geocode_pb2_grpc.GeocodeServiceServicer):
    def __init__(self, database_connection):
        self.db = database_connection

    def SearchAddress(self, request, context):
        # Ваша логика работы с БД
        results = self.db.search_addresses(request.query, request.limit)
        # ...
```

## 6. Тестирование

### Проверка Python gRPC сервиса

```bash
# С помощью grpcurl
grpcurl -plaintext -d '{"query": "Москва", "limit": 5, "session_id": "test"}' \
  localhost:50051 geocode.GeocodeService/SearchAddress
```

### Проверка C# API

```bash
# Health check
curl http://localhost:5000/health
```

### Проверка SignalR WebSocket

Используйте браузерные DevTools для мониторинга WebSocket соединения.

## 7. Типы для TypeScript

Создайте файл `src/types/geocode.types.ts`:

```typescript
export interface GeocodeRequest {
  query: string;
  limit: number;
}

export interface GeocodeResponse {
  success: boolean;
  errorMessage?: string;
  results: GeoObject[];
  totalFound: number;
}

export interface GeoObject {
  id: string;
  formattedAddress: string;
  street?: string;
  houseNumber?: string;
  city?: string;
  district?: string;
  postalCode?: string;
  coordinates?: Coordinates;
  relevanceScore: number;
}

export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface SearchProgress {
  status: "processing" | "searching" | "finalizing";
  message: string;
  progressPercent: number;
}
```

## 8. Обработка ошибок

### На стороне React

```typescript
connection.on("SearchCompleted", (response) => {
  if (!response.success) {
    // Показать ошибку пользователю
    showError(response.errorMessage);
  }
});

connection.onclose((error) => {
  console.error("Соединение закрыто:", error);
  // Попытаться переподключиться
});
```

### На стороне C#

Все ошибки логируются и возвращаются клиенту через `SearchCompleted` event с `success: false`.

## 9. CORS

CORS уже настроен для локальной разработки (порты 3000 и 5173).

Для production добавьте ваш домен в `Program.cs`:

```csharp
policy.WithOrigins("https://your-production-domain.com")
```

## 10. Docker (опционально)

Можно добавить `docker-compose.yml` для запуска всех сервисов:

```yaml
version: '3.8'

services:
  python-service:
    build: ./python-search
    ports:
      - "50051:50051"

  csharp-api:
    build: ./api
    ports:
      - "5000:80"
    environment:
      - PythonService__Url=http://python-service:50051
    depends_on:
      - python-service

  react-app:
    build: ./react-app
    ports:
      - "80:80"
    depends_on:
      - csharp-api
```
