# React Integration Guide

Руководство по интеграции React приложения с C# API для системы геокодирования адресов.

## Обзор системы

Система состоит из трех микросервисов:

1. **C# API** (`api`) - Основной сервер, предоставляющий WebSocket (SignalR) и SSE интерфейсы
2. **Python Geocode Service** (`python-search`) - Сервис поиска адресов (порт 50051)
3. **Address Parser Service** (`address-parser`) - Сервис нормализации адресов на основе libpostal (порт 50052)

```
┌─────────────┐                  ┌──────────────┐
│             │   WebSocket/SSE  │              │
│  React App  │ ◄───────────────►│   C# API     │
│             │                  │              │
└─────────────┘                  └───────┬──────┘
                                         │
                          ┌──────────────┼──────────────┐
                          │              │              │
                          ▼              ▼              ▼
                    ┌──────────┐  ┌──────────┐  ┌──────────┐
                    │  Python  │  │ Address  │  │          │
                    │ Geocode  │  │  Parser  │  │  Health  │
                    │ Service  │  │ Service  │  │  Check   │
                    │ :50051   │  │ :50052   │  │          │
                    └──────────┘  └──────────┘  └──────────┘
```

## 1. Health Check API

Перед выполнением поисковых запросов рекомендуется проверить доступность сервисов.

### Проверка статуса через SignalR Hub

```typescript
import * as signalR from "@microsoft/signalr";

// Создание подключения к SignalR Hub
const connection = new signalR.HubConnectionBuilder()
  .withUrl("https://localhost:7082/hubs/geocode")
  .withAutomaticReconnect()
  .build();

await connection.start();

// Проверка статуса Python Geocode Service (поиск адресов)
const isPythonServiceHealthy = await connection.invoke<boolean>(
  "CheckPythonServiceStatus"
);

// Проверка статуса Address Parser Service (нормализация адресов)
const isAddressParserHealthy = await connection.invoke<boolean>(
  "CheckAddressParserServiceStatus"
);

console.log("Python Geocode Service:", isPythonServiceHealthy ? "✓ Доступен" : "✗ Недоступен");
console.log("Address Parser Service:", isAddressParserHealthy ? "✓ Доступен" : "✗ Недоступен");
```

### Проверка через REST API

```typescript
// Health check для всего API
const apiHealth = await fetch("https://localhost:7082/health");
const apiStatus = await apiHealth.json();

console.log("API Status:", apiStatus);
// Ответ: { status: "healthy", timestamp: "2025-11-15T12:34:56Z" }
```

## 2. Поиск адресов через SignalR (рекомендуется)

SignalR обеспечивает двустороннюю связь с прогресс-индикаторами и поддержкой отмены запросов.

### Подключение к Hub

```typescript
import * as signalR from "@microsoft/signalr";

const connection = new signalR.HubConnectionBuilder()
  .withUrl("https://localhost:7082/hubs/geocode", {
    withCredentials: true // Важно для CORS
  })
  .withAutomaticReconnect([0, 1000, 3000, 5000]) // Автоматическое переподключение
  .configureLogging(signalR.LogLevel.Information)
  .build();

// Обработчики событий подключения
connection.onreconnecting((error) => {
  console.warn("SignalR переподключается...", error);
});

connection.onreconnected((connectionId) => {
  console.log("SignalR переподключен:", connectionId);
});

connection.onclose((error) => {
  console.error("SignalR соединение закрыто:", error);
});

// Запуск подключения
await connection.start();
console.log("SignalR подключен");
```

### Выполнение поиска

```typescript
interface GeocodeRequest {
  query: string;      // Поисковый запрос
  limit?: number;     // Максимальное количество результатов (по умолчанию 10)
  requestId: string;  // Уникальный ID запроса для отмены
}

interface SearchProgress {
  requestId: string;
  status: "processing" | "normalizing" | "searching" | "finalizing";
  message: string;
  progressPercent: number;
}

interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  errorMessage: string | null;
  errorCode: string | null;
  metadata: {
    requestId: string;
    executionTimeMs: number;
    wasCancelled: boolean;
  };
}

interface SearchResultData {
  searchedAddress: string;
  totalFound: number;
  objects: AddressObject[];
}

interface AddressObject {
  locality: string;     // Населенный пункт
  street: string;       // Улица
  number: string;       // Номер дома
  lon: number;          // Долгота
  lat: number;          // Широта
  score: number;        // Релевантность (0.0-1.0)
  additionalInfo?: {
    postalCode?: string;
    district?: string;
    fullAddress?: string;
    objectId?: string;
  };
}

// Подписка на события
connection.on("SearchProgress", (progress: SearchProgress) => {
  console.log(`Прогресс [${progress.requestId}]: ${progress.message} (${progress.progressPercent}%)`);
  // Обновите UI: прогресс-бар, статус и т.д.
});

connection.on("SearchCompleted", (response: ApiResponse<SearchResultData>) => {
  if (response.success) {
    console.log(`Найдено адресов: ${response.data!.totalFound}`);
    console.log("Результаты:", response.data!.objects);
    // Обновите UI с результатами
  } else {
    console.error(`Ошибка: ${response.errorMessage} (${response.errorCode})`);
    // Покажите ошибку пользователю
  }
});

// Отправка запроса на поиск
const requestId = crypto.randomUUID();

await connection.invoke("SearchAddress", {
  query: "Москва, Тверская улица, 7",
  limit: 10,
  requestId: requestId
});
```

### Отмена запроса

```typescript
interface CancelSearchRequest {
  requestId: string;
}

// Отмена активного запроса
await connection.invoke("CancelSearch", {
  requestId: requestId
});
```

### Пример React компонента

```tsx
import React, { useState, useEffect, useRef } from "react";
import * as signalR from "@microsoft/signalr";

interface SearchResult {
  searchedAddress: string;
  totalFound: number;
  objects: AddressObject[];
}

export const AddressSearch: React.FC = () => {
  const [connection, setConnection] = useState<signalR.HubConnection | null>(null);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult | null>(null);
  const [progress, setProgress] = useState<string>("");
  const [isLoading, setIsLoading] = useState(false);
  const [servicesStatus, setServicesStatus] = useState({
    pythonService: false,
    addressParser: false
  });

  const currentRequestId = useRef<string | null>(null);

  // Подключение к SignalR при монтировании
  useEffect(() => {
    const connect = async () => {
      const conn = new signalR.HubConnectionBuilder()
        .withUrl("https://localhost:7082/hubs/geocode")
        .withAutomaticReconnect()
        .build();

      conn.on("SearchProgress", (progress) => {
        setProgress(progress.message);
      });

      conn.on("SearchCompleted", (response) => {
        setIsLoading(false);
        if (response.success) {
          setResults(response.data);
        } else {
          alert(`Ошибка: ${response.errorMessage}`);
        }
        currentRequestId.current = null;
      });

      await conn.start();
      setConnection(conn);

      // Проверка статуса сервисов
      const pythonStatus = await conn.invoke("CheckPythonServiceStatus");
      const addressParserStatus = await conn.invoke("CheckAddressParserServiceStatus");

      setServicesStatus({
        pythonService: pythonStatus,
        addressParser: addressParserStatus
      });
    };

    connect();

    return () => {
      connection?.stop();
    };
  }, []);

  const handleSearch = async () => {
    if (!connection || !query.trim()) return;

    const requestId = crypto.randomUUID();
    currentRequestId.current = requestId;

    setIsLoading(true);
    setResults(null);
    setProgress("");

    await connection.invoke("SearchAddress", {
      query: query,
      limit: 10,
      requestId: requestId
    });
  };

  const handleCancel = async () => {
    if (!connection || !currentRequestId.current) return;

    await connection.invoke("CancelSearch", {
      requestId: currentRequestId.current
    });

    setIsLoading(false);
    currentRequestId.current = null;
  };

  return (
    <div>
      <div>
        Статус сервисов:
        <span style={{ color: servicesStatus.pythonService ? "green" : "red" }}>
          ● Поиск
        </span>
        <span style={{ color: servicesStatus.addressParser ? "green" : "red" }}>
          ● Нормализация
        </span>
      </div>

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Введите адрес..."
        disabled={isLoading}
      />

      {!isLoading ? (
        <button onClick={handleSearch}>Поиск</button>
      ) : (
        <button onClick={handleCancel}>Отменить</button>
      )}

      {progress && <div>Статус: {progress}</div>}

      {results && (
        <div>
          <h3>Найдено: {results.totalFound}</h3>
          {results.objects.map((obj, idx) => (
            <div key={idx}>
              {obj.locality}, {obj.street}, {obj.number}
              <br />
              Координаты: {obj.lat}, {obj.lon} (релевантность: {obj.score})
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
```

## 3. Поиск адресов через SSE (альтернатива)

Server-Sent Events - односторонний поток данных от сервера к клиенту.

### Выполнение поиска

```typescript
interface SseSearchParams {
  query: string;
  limit?: number;
  requestId: string;
}

const searchWithSSE = (params: SseSearchParams) => {
  const url = new URL("https://localhost:7082/api/geocode/search-stream");
  url.searchParams.append("query", params.query);
  url.searchParams.append("limit", String(params.limit || 10));
  url.searchParams.append("requestId", params.requestId);

  const eventSource = new EventSource(url.toString());

  eventSource.addEventListener("progress", (event) => {
    const progress = JSON.parse(event.data);
    console.log(`Прогресс: ${progress.message} (${progress.progressPercent}%)`);
  });

  eventSource.addEventListener("result", (event) => {
    const response: ApiResponse<SearchResultData> = JSON.parse(event.data);

    if (response.success) {
      console.log("Результаты:", response.data);
    } else {
      console.error("Ошибка:", response.errorMessage);
    }

    eventSource.close();
  });

  eventSource.addEventListener("error", (error) => {
    console.error("SSE ошибка:", error);
    eventSource.close();
  });

  // Возвращаем функцию для отмены
  return () => {
    eventSource.close();
  };
};

// Использование
const cancelSearch = searchWithSSE({
  query: "Москва, Красная площадь, 1",
  limit: 5,
  requestId: crypto.randomUUID()
});

// Отмена при необходимости
// cancelSearch();
```

## 4. Обработка ошибок

### Типичные коды ошибок

| Код ошибки | Описание | Действие |
|-----------|----------|----------|
| `INVALID_QUERY` | Некорректный поисковый запрос | Проверьте формат адреса |
| `CANCELLED` | Запрос был отменен пользователем | Информационное сообщение |
| `INTERNAL_ERROR` | Внутренняя ошибка сервера | Повторите попытку позже |
| `SERVICE_UNAVAILABLE` | Один из микросервисов недоступен | Проверьте статус сервисов |

### Обработка ошибок в React

```typescript
const handleSearchError = (response: ApiResponse<SearchResultData>) => {
  switch (response.errorCode) {
    case "INVALID_QUERY":
      showNotification("Пожалуйста, введите корректный адрес", "warning");
      break;

    case "CANCELLED":
      showNotification("Поиск отменен", "info");
      break;

    case "SERVICE_UNAVAILABLE":
      showNotification(
        "Сервис временно недоступен. Проверьте статус сервисов.",
        "error"
      );
      // Обновите статус сервисов
      checkServicesHealth();
      break;

    case "INTERNAL_ERROR":
    default:
      showNotification(
        `Произошла ошибка: ${response.errorMessage}`,
        "error"
      );
      break;
  }
};
```

## 5. Оптимизация производительности

### Debouncing для живого поиска

```typescript
import { debounce } from "lodash";

const debouncedSearch = debounce(async (query: string) => {
  if (!connection || query.length < 3) return;

  const requestId = crypto.randomUUID();
  await connection.invoke("SearchAddress", {
    query: query,
    limit: 5,
    requestId: requestId
  });
}, 500); // 500ms задержка

// В onChange input'а
<input
  onChange={(e) => {
    setQuery(e.target.value);
    debouncedSearch(e.target.value);
  }}
/>
```

### Отмена предыдущих запросов

```typescript
const searchWithAutoCancel = async (query: string) => {
  // Отменяем предыдущий запрос, если он активен
  if (currentRequestId.current) {
    await connection!.invoke("CancelSearch", {
      requestId: currentRequestId.current
    });
  }

  // Создаем новый запрос
  const requestId = crypto.randomUUID();
  currentRequestId.current = requestId;

  await connection!.invoke("SearchAddress", {
    query: query,
    limit: 10,
    requestId: requestId
  });
};
```

## 6. Настройка CORS

API уже настроен для работы с React приложениями на портах:
- `http://localhost:5173` (Vite по умолчанию)
- `http://localhost:5174`
- `http://localhost:3000` (Create React App)

Если ваше приложение использует другой порт, необходимо обновить `Program.cs` в API проекте.

## 7. TypeScript типы

Рекомендуется создать файл `types/api.ts` с определениями всех типов:

```typescript
// types/api.ts
export interface GeocodeRequest {
  query: string;
  limit?: number;
  requestId: string;
}

export interface CancelSearchRequest {
  requestId: string;
}

export interface SearchProgress {
  requestId: string;
  status: "processing" | "normalizing" | "searching" | "finalizing";
  message: string;
  progressPercent: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  errorMessage: string | null;
  errorCode: string | null;
  metadata: ResponseMetadata;
}

export interface ResponseMetadata {
  requestId: string;
  executionTimeMs: number;
  wasCancelled: boolean;
}

export interface SearchResultData {
  searchedAddress: string;
  totalFound: number;
  objects: AddressObject[];
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
```

## 8. Запуск микросервисов

Перед использованием убедитесь, что все сервисы запущены:

### C# API

```bash
cd api
dotnet run
```

Или через Docker:
```bash
docker-compose up api
```

### Python Geocode Service

```bash
cd python-search
python grpc_server.py
```

Или через Docker:
```bash
docker-compose up python-search
```

### Address Parser Service

```bash
cd address-parser
# См. address-parser/DOCKER_README.md для инструкций
docker-compose up address-parser
```

### Все сервисы одновременно

```bash
docker-compose up -d
```

## 9. Мониторинг статуса сервисов

Рекомендуется периодически проверять статус микросервисов:

```typescript
const checkServicesHealth = async () => {
  if (!connection) return;

  try {
    const [pythonHealthy, addressParserHealthy] = await Promise.all([
      connection.invoke<boolean>("CheckPythonServiceStatus"),
      connection.invoke<boolean>("CheckAddressParserServiceStatus")
    ]);

    setServicesStatus({
      pythonService: pythonHealthy,
      addressParser: addressParserHealthy
    });

    // Если какой-то сервис недоступен, показываем предупреждение
    if (!pythonHealthy || !addressParserHealthy) {
      showWarning("Некоторые сервисы недоступны. Функциональность может быть ограничена.");
    }
  } catch (error) {
    console.error("Ошибка проверки статуса сервисов:", error);
  }
};

// Проверяем статус каждые 30 секунд
useEffect(() => {
  const interval = setInterval(checkServicesHealth, 30000);
  return () => clearInterval(interval);
}, [connection]);
```

## 10. Дополнительная информация

### Процесс работы системы

1. **Пользователь вводит адрес** в React приложении
2. **React отправляет запрос** в C# API через SignalR или SSE
3. **C# API валидирует** запрос
4. **C# API отправляет адрес** в Address Parser Service (порт 50052) для нормализации
5. **Address Parser** использует libpostal для нормализации адреса
6. **C# API получает нормализованный адрес** и отправляет его в Python Geocode Service (порт 50051)
7. **Python Geocode Service** ищет адрес в базе данных
8. **Результаты возвращаются** через C# API в React приложение

### Метаданные запроса

Каждый ответ содержит метаданные:

```typescript
{
  requestId: "uuid-v4",           // ID запроса для отслеживания
  executionTimeMs: 245,           // Время выполнения в миллисекундах
  wasCancelled: false             // Был ли запрос отменен
}
```

### Логирование

Все запросы логируются на стороне сервера. RequestId используется для корреляции логов между микросервисами.

Рекомендуется также логировать запросы на клиенте:

```typescript
console.log(`[${requestId}] Начат поиск: ${query}`);
console.log(`[${requestId}] Завершен за ${metadata.executionTimeMs}ms`);
```

---

**Версия документа:** 1.0
**Дата:** 2025-11-15
**Совместимость:** .NET 9.0, React 18+
