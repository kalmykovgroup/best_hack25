# Спецификация API

## Поток данных

```
React App
  ↓ WebSocket/SSE: { requestId, query, limit }

C# Backend
  ↓ Валидация (IAddressNormalizer.IsValid)
  ↓ Нормализация (IAddressNormalizer.Normalize)
  ↓ gRPC: SearchAddressRequest { normalized_query, limit, request_id, options }

Python gRPC Service
  ↑ gRPC: SearchAddressResponse { status, searched_address, objects[], total_found, metadata }

C# Backend
  ↑ Маппинг в SearchResultData
  ↑ Оборачивание в ApiResponse<SearchResultData>
  ↑ WebSocket/SSE: ApiResponse<SearchResultData>

React App
```

---

## 1. Клиент → C# (WebSocket/SSE)

### Запрос от клиента

```typescript
interface GeocodeRequest {
  requestId: string;        // Уникальный ID запроса
  query: string;            // Поисковая строка от пользователя
  limit: number;            // Макс. количество результатов (по умолчанию 10)
}
```

### Ответ клиенту (обернут в ApiResponse)

```typescript
interface ApiResponse<T> {
  success: boolean;
  data?: T;                // Данные (если success: true)
  errorMessage?: string;   // Ошибка (если success: false)
  errorCode?: string;      // Код ошибки для обработки
  metadata?: {
    requestId: string;
    executionTimeMs: number;
    timestamp: string;
    wasCancelled: boolean;
  };
}

// Данные успешного ответа
interface SearchResultData {
  searchedAddress: string;  // Нормализованная строка поиска
  objects: AddressObject[]; // Найденные адреса
  totalFound: number;       // Общее количество
}

interface AddressObject {
  locality: string;         // Населенный пункт
  street: string;           // Улица
  number: string;           // Номер дома (может быть "10к2с1")
  lon: number;              // Долгота
  lat: number;              // Широта
  score: number;            // Релевантность (0-1)
  additionalInfo?: {
    postalCode?: string;
    district?: string;
    fullAddress?: string;
    objectId?: string;
  };
}
```

### Пример успешного ответа

```json
{
  "success": true,
  "data": {
    "searchedAddress": "Москва улица Тверская 7",
    "objects": [
      {
        "locality": "Москва",
        "street": "Тверская улица",
        "number": "7",
        "lon": 37.615560,
        "lat": 55.757814,
        "score": 0.95,
        "additionalInfo": {
          "postalCode": "125009",
          "district": "Тверской район",
          "fullAddress": "Москва, Тверская улица, 7",
          "objectId": "obj_1"
        }
      }
    ],
    "totalFound": 1
  },
  "metadata": {
    "requestId": "req_123",
    "executionTimeMs": 145,
    "timestamp": "2025-11-15T10:30:00Z",
    "wasCancelled": false
  }
}
```

### Пример ответа с ошибкой

```json
{
  "success": false,
  "errorMessage": "Поисковая строка некорректна",
  "errorCode": "INVALID_QUERY",
  "metadata": {
    "requestId": "req_124",
    "executionTimeMs": 5
  }
}
```

---

## 2. C# → Python (gRPC)

### Protobuf контракт

```protobuf
service GeocodeService {
  rpc SearchAddress (SearchAddressRequest) returns (SearchAddressResponse);
  rpc HealthCheck (HealthCheckRequest) returns (HealthCheckResponse);
}

message SearchAddressRequest {
  string normalized_query = 1;   // Нормализованная строка (обработана на C#)
  int32 limit = 2;
  string request_id = 3;
  SearchOptions options = 4;
}

message SearchOptions {
  double min_score_threshold = 1;  // Минимальная релевантность
  bool enable_fuzzy_search = 2;    // Нечеткий поиск
  string locality_filter = 3;      // Фильтр по городу
}

message SearchAddressResponse {
  ResponseStatus status = 1;
  string searched_address = 2;
  repeated AddressObject objects = 3;
  int32 total_found = 4;
  ResponseMetadata metadata = 5;
}

message AddressObject {
  string locality = 1;
  string street = 2;
  string number = 3;
  double lon = 4;
  double lat = 5;
  double score = 6;
  AdditionalInfo additional_info = 7;
}

enum StatusCode {
  OK = 0;
  INVALID_REQUEST = 1;
  NOT_FOUND = 2;
  INTERNAL_ERROR = 3;
  TIMEOUT = 4;
  DATABASE_ERROR = 5;
  CANCELLED = 6;
}
```

---

## 3. Endpoints

### WebSocket (SignalR)

**URL**: `ws://localhost:5000/hubs/geocode`

**Методы**:
- `SearchAddress(GeocodeRequest)` - Поиск адреса
- `CancelSearch(CancelSearchRequest)` - Отмена запроса

**События**:
- `SearchProgress` - Прогресс выполнения
- `SearchCompleted` - Финальный результат (ApiResponse<SearchResultData>)

### SSE (Server-Sent Events)

**GET** `/api/geocode/stream`
- Query params: `query`, `limit`, `requestId`
- Events: `progress`, `completed`

**POST** `/api/geocode/cancel/{requestId}`
- Отмена активного запроса

### REST

**GET** `/health`
- Health check API

---

## 4. Нормализация адреса (C#)

### Интерфейс

```csharp
public interface IAddressNormalizer
{
    string Normalize(string rawAddress);
    bool IsValid(string address);
}
```

### Что делает нормализатор (базовая версия)

1. Убирает лишние пробелы
2. Заменяет сокращения (ул. → улица, д. → дом)
3. Удаляет префиксы ("Россия", "РФ")

**TODO**: Дополните своей логикой в `AddressNormalizer.cs`!

### Пример нормализации

```
Вход:  "Россия, г. Москва, ул. Тверская, д. 7"
Выход: "Москва улица Тверская дом 7"
```

---

## 5. Коды ошибок

| Код | Описание |
|-----|----------|
| `INVALID_QUERY` | Некорректный запрос |
| `NOT_FOUND` | Ничего не найдено |
| `INTERNAL_ERROR` | Внутренняя ошибка |
| `TIMEOUT` | Таймаут |
| `DATABASE_ERROR` | Ошибка БД |
| `CANCELLED` | Запрос отменен |

---

## 6. Статусы прогресса

1. **processing** (10%) - Валидация запроса
2. **normalizing** (25%) - Нормализация адреса
3. **searching** (50%) - Поиск в Python
4. **finalizing** (90%) - Обработка результатов

---

## 7. Запуск и тестирование

### Python gRPC

```bash
cd python-search
pip install -r requirements.txt
python generate_grpc.py
python grpc_server.py
```

### C# API

```bash
cd api
dotnet restore
dotnet run
```

### Тестирование

```bash
# Health check Python
grpcurl -plaintext localhost:50051 geocode.GeocodeService/HealthCheck

# Поиск адреса
grpcurl -plaintext -d '{"normalized_query": "Москва Тверская", "limit": 5, "request_id": "test"}' \
  localhost:50051 geocode.GeocodeService/SearchAddress

# Health check C#
curl http://localhost:5000/health
```

---

## 8. Типы для React (TypeScript)

Создайте файл `src/types/api.types.ts`:

```typescript
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  errorMessage?: string;
  errorCode?: string;
  metadata?: ResponseMetadata;
}

export interface ResponseMetadata {
  requestId: string;
  executionTimeMs: number;
  timestamp: string;
  wasCancelled: boolean;
}

export interface SearchResultData {
  searchedAddress: string;
  objects: AddressObject[];
  totalFound: number;
}

export interface AddressObject {
  locality: string;
  street: string;
  number: string;
  lon: number;
  lat: number;
  score: number;
  additionalInfo?: AddressAdditionalInfo;
}

export interface AddressAdditionalInfo {
  postalCode?: string;
  district?: string;
  fullAddress?: string;
  objectId?: string;
}

export interface GeocodeRequest {
  requestId: string;
  query: string;
  limit: number;
}

export interface SearchProgress {
  requestId: string;
  status: "processing" | "normalizing" | "searching" | "finalizing";
  message: string;
  progressPercent: number;
}
```

---

## 9. Важные замечания

### Для C# разработчика:
1. Дополните логику нормализации в `AddressNormalizer.cs`
2. Все ответы клиенту обернуты в `ApiResponse<T>`
3. Нормализация происходит ПЕРЕД отправкой в Python

### Для Python разработчика:
1. Замените `self.mock_data` на реальную БД
2. Реализуйте полнотекстовый поиск
3. Учитывайте `SearchOptions` (min_score_threshold, fuzzy_search)
4. Возвращайте правильные StatusCode

### Для React разработчика:
1. Все ответы имеют единый формат `ApiResponse<T>`
2. Проверяйте `success` перед обработкой `data`
3. Обрабатывайте `errorCode` для специфичных ошибок
4. Используйте `metadata.requestId` для трекинга

---

## 10. Производительность

- gRPC timeout: 30 секунд
- SignalR MaxReceiveMessageSize: 100KB
- Python: ThreadPoolExecutor (10 workers)
- C#: ActiveRequestsManager (thread-safe)

Все готово к работе! 🚀
