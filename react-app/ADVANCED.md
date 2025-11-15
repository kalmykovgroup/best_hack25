# Продвинутые архитектуры для максимальной производительности

## 1. Архитектура с двумя каналами

### Вариант A: Два отдельных WebSocket соединения

**Преимущества:**
- Полное разделение трафика запросов и ответов
- Меньше конкуренции за bandwidth
- Можно использовать разные приоритеты

**Недостатки:**
- Двойное потребление ресурсов (порты, память)
- Сложнее синхронизация

```typescript
// dual-websocket.service.ts
export class DualWebSocketService {
  private requestWs: WebSocket;
  private responseWs: WebSocket;

  constructor(requestUrl: string, responseUrl: string) {
    this.requestWs = new WebSocket(requestUrl);
    this.responseWs = new WebSocket(responseUrl);

    this.setupHandlers();
  }

  send(data: any) {
    this.requestWs.send(JSON.stringify(data));
  }

  onMessage(handler: (data: any) => void) {
    this.responseWs.onmessage = (event) => {
      handler(JSON.parse(event.data));
    };
  }
}
```

**Серверная реализация (Node.js):**
```javascript
const WebSocket = require('ws');

// Канал для запросов
const requestWss = new WebSocket.Server({ port: 8080 });
// Канал для ответов
const responseWss = new WebSocket.Server({ port: 8081 });

const connections = new Map(); // clientId -> responseWs

requestWss.on('connection', (ws) => {
  ws.on('message', (message) => {
    const data = JSON.parse(message);
    const clientId = data.clientId;

    // Обработка запроса
    const results = performSearch(data.query);

    // Отправка через канал ответов
    const responseWs = connections.get(clientId);
    if (responseWs) {
      responseWs.send(JSON.stringify({
        type: 'search_result',
        requestId: data.requestId,
        results
      }));
    }
  });
});

responseWss.on('connection', (ws, req) => {
  const clientId = getClientId(req); // Из cookie/header
  connections.set(clientId, ws);

  ws.on('close', () => {
    connections.delete(clientId);
  });
});
```

### Вариант B: WebSocket + Server-Sent Events (SSE)

**Преимущества:**
- SSE проще для односторонней связи (сервер -> клиент)
- Автоматический reconnect в SSE
- Меньше overhead для получения данных
- Работает через HTTP/2

**Недостатки:**
- SSE не поддерживает бинарные данные
- Только текст

```typescript
// hybrid-search.service.ts
export class HybridSearchService {
  private ws: WebSocket;
  private eventSource: EventSource;

  constructor(wsUrl: string, sseUrl: string) {
    // WebSocket для отправки запросов
    this.ws = new WebSocket(wsUrl);

    // SSE для получения результатов
    this.eventSource = new EventSource(sseUrl);
    this.eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleResponse(data);
    };
  }

  search(query: string, requestId: string) {
    this.ws.send(JSON.stringify({
      type: 'search',
      query,
      requestId
    }));
  }
}
```

**Серверная реализация (Express + SSE):**
```javascript
const express = require('express');
const WebSocket = require('ws');

const app = express();
const wss = new WebSocket.Server({ port: 8080 });

// SSE клиенты
const sseClients = new Map();

// WebSocket для запросов
wss.on('connection', (ws) => {
  ws.on('message', (message) => {
    const data = JSON.parse(message);
    const results = performSearch(data.query);

    // Отправка через SSE
    const client = sseClients.get(data.clientId);
    if (client) {
      client.write(`data: ${JSON.stringify({
        type: 'search_result',
        requestId: data.requestId,
        results
      })}\\n\\n`);
    }
  });
});

// SSE endpoint
app.get('/search-results', (req, res) => {
  const clientId = req.query.clientId;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  sseClients.set(clientId, res);

  req.on('close', () => {
    sseClients.delete(clientId);
  });
});

app.listen(3000);
```

## 2. Оптимизация с WebWorkers

Обработка больших объемов данных в фоновом потоке:

```typescript
// search.worker.ts
self.onmessage = (e) => {
  const { type, data } = e.data;

  if (type === 'PROCESS_RESULTS') {
    // Обработка результатов (сортировка, фильтрация)
    const processed = processResults(data.results, data.query);
    self.postMessage({ type: 'RESULTS_PROCESSED', results: processed });
  }
};

// useMapSearch.ts (с worker)
const worker = new Worker(new URL('./search.worker.ts', import.meta.url));

worker.onmessage = (e) => {
  if (e.data.type === 'RESULTS_PROCESSED') {
    setResults(e.data.results);
  }
};

// Отправка в worker
worker.postMessage({
  type: 'PROCESS_RESULTS',
  data: { results: rawResults, query }
});
```

## 3. Кэширование и Prefetching

```typescript
// cache.service.ts
export class SearchCache {
  private cache = new Map<string, { results: MapObject[], timestamp: number }>();
  private readonly TTL = 5 * 60 * 1000; // 5 минут

  set(query: string, results: MapObject[]) {
    this.cache.set(query.toLowerCase(), {
      results,
      timestamp: Date.now()
    });
  }

  get(query: string): MapObject[] | null {
    const cached = this.cache.get(query.toLowerCase());

    if (!cached) return null;

    // Проверка TTL
    if (Date.now() - cached.timestamp > this.TTL) {
      this.cache.delete(query.toLowerCase());
      return null;
    }

    return cached.results;
  }

  // Prefetch популярных запросов
  async prefetch(queries: string[]) {
    for (const query of queries) {
      if (!this.cache.has(query)) {
        // Запрос в фоне
        this.fetchAndCache(query);
      }
    }
  }
}

// useMapSearch.ts
const cache = new SearchCache();

const performSearch = (query: string) => {
  // Проверка кэша
  const cached = cache.get(query);
  if (cached) {
    setResults(cached);
    setIsSearching(false);
    return;
  }

  // Запрос к серверу
  // ...
};
```

## 4. Throttling и Rate Limiting

```typescript
// throttle.hook.ts
export const useThrottle = <T extends (...args: any[]) => any>(
  callback: T,
  delay: number
) => {
  const lastRun = useRef(Date.now());

  return useCallback((...args: Parameters<T>) => {
    const now = Date.now();

    if (now - lastRun.current >= delay) {
      callback(...args);
      lastRun.current = now;
    }
  }, [callback, delay]);
};

// useMapSearch.ts
const throttledSearch = useThrottle(performSearch, 100); // Макс 10 req/sec
```

## 5. Incremental Loading (Streaming)

```typescript
// Сервер отправляет результаты частями
{
  "type": "search_result_chunk",
  "requestId": "123",
  "chunk": 1,
  "totalChunks": 5,
  "results": [...], // Первые 20 результатов
  "hasMore": true
}

// Клиент накапливает результаты
const [results, setResults] = useState<MapObject[]>([]);

const handleMessage = (data: any) => {
  if (data.type === 'search_result_chunk') {
    if (data.chunk === 1) {
      setResults(data.results);
    } else {
      setResults(prev => [...prev, ...data.results]);
    }
  }
};
```

## 6. Сравнение производительности

| Метод | Latency | Throughput | Сложность | Рекомендация |
|-------|---------|------------|-----------|--------------|
| Один WebSocket | ~50ms | Средний | Низкая | **Рекомендуется для большинства случаев** |
| Два WebSocket | ~45ms | Высокий | Средняя | Для высоконагруженных систем |
| WS + SSE | ~40ms | Очень высокий | Средняя | Для streaming данных |
| С кэшированием | ~5ms | Очень высокий | Низкая | **Обязательно добавить** |
| С WebWorkers | ~50ms | Высокий | Высокая | Для сложной обработки данных |

## Рекомендуемая архитектура

Для вашего случая (поиск по карте) рекомендую:

1. **Один WebSocket** с debouncing (уже реализовано)
2. **+ Локальное кэширование** (простое, большой прирост)
3. **+ Throttling** (защита от спама)
4. **Опционально:** SSE для streaming, если результатов очень много

Эта комбинация даст отличную производительность без излишней сложности.

## Пример финальной реализации

```typescript
// Улучшенный useMapSearch с кэшированием и throttling
export const useMapSearch = (options: UseMapSearchOptions) => {
  const cache = useRef(new SearchCache());

  const performSearch = useCallback((query: string) => {
    // 1. Проверка кэша
    const cached = cache.current.get(query);
    if (cached) {
      setResults(cached);
      return;
    }

    // 2. Запрос к серверу
    const requestId = generateId();
    send({ type: 'search', requestId, query });

    // 3. При получении ответа - сохранить в кэш
  }, []);

  // Throttling: макс 10 запросов в секунду
  const throttledSearch = useThrottle(performSearch, 100);

  // Debouncing: задержка 300ms
  const debouncedSearch = useDebounce(throttledSearch, 300);

  return { search: debouncedSearch, ... };
};
```
