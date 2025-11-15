# Руководство по интеграции React клиента

## Доступные каналы связи

Реализовано **2 канала** для максимальной гибкости:

### 1️⃣ WebSocket (SignalR) - **Рекомендуется**
- **Двунаправленная связь**
- Отправка запросов + получение результатов
- Поддержка отмены запросов
- Auto-reconnect

### 2️⃣ SSE (Server-Sent Events)
- Получение результатов в режиме реального времени
- Более простая интеграция
- Односторонняя связь (только от сервера к клиенту)

---

## Вариант 1: WebSocket (SignalR) - Полнофункциональный

### Установка

```bash
npm install @microsoft/signalr
```

### TypeScript типы

```typescript
// src/types/geocode.types.ts

export interface GeocodeRequest {
  requestId: string;
  query: string;
  limit: number;
}

export interface GeocodeResponse {
  requestId: string;
  success: boolean;
  errorMessage?: string;
  results: GeoObject[];
  totalFound: number;
  executionTimeMs: number;
  wasCancelled: boolean;
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
  requestId: string;
  status: "processing" | "searching" | "finalizing";
  message: string;
  progressPercent: number;
}

export interface CancelSearchRequest {
  requestId: string;
}
```

### Реализация хука с Debouncing и Cancellation

```typescript
// src/hooks/useGeocode.ts

import { useState, useEffect, useRef, useCallback } from 'react';
import * as signalR from '@microsoft/signalr';
import { GeocodeRequest, GeocodeResponse, SearchProgress } from '../types/geocode.types';

export function useGeocode(apiUrl: string = 'http://localhost:5000') {
  const [connection, setConnection] = useState<signalR.HubConnection | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [results, setResults] = useState<GeocodeResponse | null>(null);
  const [progress, setProgress] = useState<SearchProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Хранилище активных запросов для отмены
  const activeRequestRef = useRef<string | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Инициализация подключения
  useEffect(() => {
    const newConnection = new signalR.HubConnectionBuilder()
      .withUrl(`${apiUrl}/hubs/geocode`)
      .withAutomaticReconnect({
        nextRetryDelayInMilliseconds: (retryContext) => {
          // Exponential backoff: 2s, 4s, 8s, 16s, 30s (max)
          const delay = Math.min(2000 * Math.pow(2, retryContext.previousRetryCount), 30000);
          console.log(`Переподключение через ${delay}ms...`);
          return delay;
        }
      })
      .configureLogging(signalR.LogLevel.Information)
      .build();

    // Обработчики событий
    newConnection.on('SearchProgress', (progressData: SearchProgress) => {
      console.log('Прогресс:', progressData);
      setProgress(progressData);
    });

    newConnection.on('SearchCompleted', (response: GeocodeResponse) => {
      console.log('Результаты:', response);
      setResults(response);
      setIsLoading(false);
      setProgress(null);

      // Очищаем активный запрос
      if (activeRequestRef.current === response.requestId) {
        activeRequestRef.current = null;
      }
    });

    // Обработчики переподключения
    newConnection.onreconnecting((error) => {
      console.warn('Переподключение...', error);
      setIsConnected(false);
    });

    newConnection.onreconnected((connectionId) => {
      console.log('Переподключено:', connectionId);
      setIsConnected(true);
    });

    newConnection.onclose((error) => {
      console.error('Соединение закрыто:', error);
      setIsConnected(false);
    });

    setConnection(newConnection);

    // Подключение
    newConnection.start()
      .then(() => {
        console.log('✅ SignalR подключен');
        setIsConnected(true);
      })
      .catch((err) => {
        console.error('❌ Ошибка подключения SignalR:', err);
      });

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      newConnection.stop();
    };
  }, [apiUrl]);

  /**
   * Поиск с debouncing (300ms задержка)
   */
  const search = useCallback((query: string, limit: number = 10) => {
    if (!connection || !isConnected) {
      console.warn('SignalR не подключен');
      return;
    }

    // Очищаем предыдущий таймер
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Отменяем предыдущий запрос
    if (activeRequestRef.current) {
      cancelSearch(activeRequestRef.current);
    }

    // Debouncing: ждем 300ms перед отправкой
    debounceTimerRef.current = setTimeout(async () => {
      const requestId = generateRequestId();
      activeRequestRef.current = requestId;

      const request: GeocodeRequest = {
        requestId,
        query,
        limit
      };

      setIsLoading(true);
      setProgress(null);
      setResults(null);

      try {
        await connection.invoke('SearchAddress', request);
        console.log('Запрос отправлен:', requestId);
      } catch (error) {
        console.error('Ошибка при отправке запроса:', error);
        setIsLoading(false);
      }
    }, 300);
  }, [connection, isConnected]);

  /**
   * Отмена активного запроса
   */
  const cancelSearch = useCallback(async (requestId: string) => {
    if (!connection || !isConnected) return;

    try {
      await connection.invoke('CancelSearch', { requestId });
      console.log('Запрос отменен:', requestId);

      if (activeRequestRef.current === requestId) {
        activeRequestRef.current = null;
        setIsLoading(false);
        setProgress(null);
      }
    } catch (error) {
      console.error('Ошибка при отмене запроса:', error);
    }
  }, [connection, isConnected]);

  return {
    isConnected,
    isLoading,
    results,
    progress,
    search,
    cancelSearch: () => activeRequestRef.current && cancelSearch(activeRequestRef.current)
  };
}

// Генерация уникального Request ID
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}
```

### Использование в компоненте

```typescript
// src/components/AddressSearch.tsx

import React, { useState } from 'react';
import { useGeocode } from '../hooks/useGeocode';

export function AddressSearch() {
  const [query, setQuery] = useState('');
  const { isConnected, isLoading, results, progress, search, cancelSearch } = useGeocode();

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);

    // Автоматический поиск с debouncing
    if (value.length >= 3) {
      search(value, 10);
    }
  };

  return (
    <div className="address-search">
      <div className="connection-status">
        {isConnected ? '🟢 Подключено' : '🔴 Отключено'}
      </div>

      <input
        type="text"
        value={query}
        onChange={handleInputChange}
        placeholder="Введите адрес..."
        disabled={!isConnected}
      />

      {isLoading && (
        <div className="loading">
          <div>Поиск... {progress?.progressPercent}%</div>
          <div>{progress?.message}</div>
          <button onClick={cancelSearch}>Отменить</button>
        </div>
      )}

      {results && (
        <div className="results">
          <h3>Найдено: {results.totalFound} (за {results.executionTimeMs}ms)</h3>
          {results.success ? (
            <ul>
              {results.results.map((item) => (
                <li key={item.id}>
                  <strong>{item.formattedAddress}</strong>
                  <span>Релевантность: {(item.relevanceScore * 100).toFixed(0)}%</span>
                  {item.coordinates && (
                    <span>
                      ({item.coordinates.latitude.toFixed(6)}, {item.coordinates.longitude.toFixed(6)})
                    </span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div className="error">{results.errorMessage}</div>
          )}
        </div>
      )}
    </div>
  );
}
```

---

## Вариант 2: Server-Sent Events (SSE) - Упрощенный

### Реализация SSE клиента

```typescript
// src/services/geocodeSSE.ts

import { GeocodeResponse, SearchProgress } from '../types/geocode.types';

export class GeocodeSSEClient {
  private apiUrl: string;
  private eventSource: EventSource | null = null;

  constructor(apiUrl: string = 'http://localhost:5000') {
    this.apiUrl = apiUrl;
  }

  /**
   * Начать поток поиска
   */
  search(
    query: string,
    onProgress: (progress: SearchProgress) => void,
    onCompleted: (response: GeocodeResponse) => void,
    onError: (error: Error) => void,
    limit: number = 10
  ): { requestId: string; close: () => void } {
    const requestId = this.generateRequestId();
    const url = `${this.apiUrl}/api/geocode/stream?query=${encodeURIComponent(query)}&limit=${limit}&requestId=${requestId}`;

    this.eventSource = new EventSource(url);

    // Событие прогресса
    this.eventSource.addEventListener('progress', (event) => {
      const progress: SearchProgress = JSON.parse(event.data);
      onProgress(progress);
    });

    // Событие завершения
    this.eventSource.addEventListener('completed', (event) => {
      const response: GeocodeResponse = JSON.parse(event.data);
      onCompleted(response);
      this.eventSource?.close();
    });

    // Ошибки
    this.eventSource.onerror = (error) => {
      console.error('SSE ошибка:', error);
      onError(new Error('SSE connection error'));
      this.eventSource?.close();
    };

    return {
      requestId,
      close: () => this.close()
    };
  }

  /**
   * Отменить запрос
   */
  async cancel(requestId: string): Promise<boolean> {
    try {
      const response = await fetch(`${this.apiUrl}/api/geocode/cancel/${requestId}`, {
        method: 'POST'
      });
      return response.ok;
    } catch (error) {
      console.error('Ошибка при отмене:', error);
      return false;
    }
  }

  /**
   * Закрыть соединение
   */
  close() {
    this.eventSource?.close();
    this.eventSource = null;
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}
```

### Использование SSE в компоненте

```typescript
// src/components/AddressSearchSSE.tsx

import React, { useState, useRef } from 'react';
import { GeocodeSSEClient } from '../services/geocodeSSE';
import { GeocodeResponse, SearchProgress } from '../types/geocode.types';

export function AddressSearchSSE() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<GeocodeResponse | null>(null);
  const [progress, setProgress] = useState<SearchProgress | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const clientRef = useRef(new GeocodeSSEClient('http://localhost:5000'));
  const activeSearchRef = useRef<{ requestId: string; close: () => void } | null>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  const handleSearch = (searchQuery: string) => {
    // Очищаем debounce таймер
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    // Отменяем предыдущий поиск
    if (activeSearchRef.current) {
      activeSearchRef.current.close();
      clientRef.current.cancel(activeSearchRef.current.requestId);
    }

    // Debouncing
    debounceTimerRef.current = setTimeout(() => {
      setIsLoading(true);
      setProgress(null);
      setResults(null);

      activeSearchRef.current = clientRef.current.search(
        searchQuery,
        (progress) => setProgress(progress),
        (response) => {
          setResults(response);
          setIsLoading(false);
          activeSearchRef.current = null;
        },
        (error) => {
          console.error('Ошибка:', error);
          setIsLoading(false);
          activeSearchRef.current = null;
        },
        10
      );
    }, 300);
  };

  const handleCancel = () => {
    if (activeSearchRef.current) {
      activeSearchRef.current.close();
      clientRef.current.cancel(activeSearchRef.current.requestId);
      activeSearchRef.current = null;
      setIsLoading(false);
    }
  };

  return (
    <div className="address-search-sse">
      <input
        type="text"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          if (e.target.value.length >= 3) {
            handleSearch(e.target.value);
          }
        }}
        placeholder="Введите адрес..."
      />

      {isLoading && (
        <div className="loading">
          <div>Поиск... {progress?.progressPercent}%</div>
          <button onClick={handleCancel}>Отменить</button>
        </div>
      )}

      {results && (
        <div className="results">
          <h3>Найдено: {results.totalFound}</h3>
          {/* Отображение результатов */}
        </div>
      )}
    </div>
  );
}
```

---

## Сравнение подходов

| Функция | WebSocket (SignalR) | SSE |
|---------|---------------------|-----|
| Двунаправленная связь | ✅ | ❌ |
| Auto-reconnect | ✅ | ❌ |
| Отмена запросов | ✅ (через WebSocket) | ✅ (через REST) |
| Простота интеграции | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Производительность | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| Поддержка браузеров | Все современные | Все (кроме IE) |

---

## Рекомендации

### Для продакшена:
- ✅ Используйте **WebSocket (SignalR)** для полнофункционального решения
- ✅ Debouncing: 300-500ms
- ✅ Показывайте прогресс пользователю
- ✅ Реализуйте локальное кэширование результатов

### Для быстрого прототипа:
- ✅ Используйте **SSE** для упрощенной интеграции
- ✅ Отмена через REST API

---

## Endpoints

### WebSocket
- **URL**: `ws://localhost:5000/hubs/geocode`
- **Методы**:
  - `SearchAddress(GeocodeRequest)` - поиск
  - `CancelSearch(CancelSearchRequest)` - отмена
- **События**:
  - `SearchProgress` - прогресс
  - `SearchCompleted` - результат

### SSE
- **GET** `/api/geocode/stream?query=...&limit=10&requestId=...` - поток результатов
- **POST** `/api/geocode/cancel/{requestId}` - отмена запроса

### Health Check
- **GET** `/health` - проверка работоспособности API
