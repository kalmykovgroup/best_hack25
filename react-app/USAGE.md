# Руководство по использованию

## Быстрый старт

### 1. Запуск в обычном режиме (один WebSocket)

**Терминал 1 - Запустите сервер:**
```bash
node server-example.js
```

**Терминал 2 - React приложение уже запущено:**
```
http://localhost:5174/
```

### 2. Запуск в двухканальном режиме (два WebSocket)

**Терминал 1 - Запустите dual-сервер:**
```bash
node server-dual-example.js
```

**Обновите `.env`:**
```env
VITE_USE_DUAL_MODE=true
```

**Перезапустите приложение** (Ctrl+C и `npm run dev`)

## Конфигурация через .env

### Основные настройки

```env
# Режим работы
VITE_USE_DUAL_MODE=false  # false = обычный, true = dual WebSocket

# URL серверов
VITE_WS_URL=ws://localhost:8080                    # Обычный режим
VITE_WS_REQUEST_URL=ws://localhost:8080            # Dual: запросы
VITE_WS_RESPONSE_URL=ws://localhost:8081           # Dual: ответы
```

### Настройки производительности

```env
# Debouncing - задержка перед отправкой запроса (рекомендуется 200-500ms)
VITE_SEARCH_DEBOUNCE=300

# Throttling - минимальный интервал между запросами (рекомендуется 50-200ms)
VITE_SEARCH_THROTTLE=100

# Включение throttling
VITE_THROTTLE_ENABLED=true
```

### Настройки кэша

```env
# Включение кэширования
VITE_CACHE_ENABLED=true

# Время жизни записей в кэше (мс)
VITE_CACHE_TTL=300000  # 5 минут

# Максимальный размер кэша (количество запросов)
VITE_CACHE_SIZE=100
```

## Тестирование функций

### Кэширование

1. Введите запрос, например: "парк"
2. Дождитесь результатов
3. Очистите поле поиска
4. Введите тот же запрос снова
5. ⚡ Увидите индикатор "Из кэша" - результаты вернутся мгновенно!

**Статистика кэша:**
- **Попадания** - сколько раз результаты взяты из кэша
- **Промахи** - сколько раз отправлен запрос на сервер
- **Hit Rate** - процент попаданий (выше = лучше)
- **Записей** - количество сохраненных запросов

### Debouncing

1. Начните быстро печатать: "м", "му", "муз", "музе", "музей"
2. В консоли браузера (F12) увидите, что запрос отправлен только один раз
3. Это экономит трафик и нагрузку на сервер!

### Throttling

Попробуйте очень быстро вводить разные запросы - частота отправки будет ограничена.

## Примеры использования в коде

### Базовое использование

```tsx
import { MapSearch } from './components/MapSearch';

function App() {
  return (
    <MapSearch
      wsUrl="ws://localhost:8080"
      onSelectResult={(result) => console.log(result)}
    />
  );
}
```

### С настройками производительности

```tsx
<MapSearch
  wsUrl="ws://localhost:8080"
  debounceMs={500}              // Более долгая задержка
  throttleMs={200}              // Реже отправляем запросы
  enableCache={true}            // Включить кэш
  enableThrottle={true}         // Включить throttling
  showStats={true}              // Показать статистику
  onSelectResult={handleSelect}
/>
```

### Без кэша и throttling

```tsx
<MapSearch
  wsUrl="ws://localhost:8080"
  enableCache={false}           // Выключить кэш
  enableThrottle={false}        // Выключить throttling
  showStats={false}             // Скрыть статистику
  onSelectResult={handleSelect}
/>
```

### Использование хука напрямую

```tsx
import { useMapSearch } from './hooks/useMapSearch';

function MyComponent() {
  const {
    search,
    results,
    isSearching,
    isConnected,
    cacheStats,
    clearCache,
    getCacheStats
  } = useMapSearch({
    wsUrl: 'ws://localhost:8080',
    debounceMs: 300,
    throttleMs: 100,
    enableCache: true,
    enableThrottle: true,
    onError: (err) => console.error(err),
    onCacheHit: (query) => console.log('Cache hit:', query),
  });

  return (
    <div>
      <input onChange={(e) => search(e.target.value)} />
      {results.map(r => <div key={r.id}>{r.name}</div>)}
      <button onClick={clearCache}>Очистить кэш</button>
    </div>
  );
}
```

### Dual WebSocket режим

```tsx
import { useMapSearchDual } from './hooks/useMapSearchDual';

function MyComponent() {
  const {
    search,
    results,
    clientId,
    // ... остальное аналогично useMapSearch
  } = useMapSearchDual({
    requestUrl: 'ws://localhost:8080',
    responseUrl: 'ws://localhost:8081',
    debounceMs: 300,
    enableCache: true,
  });

  return (
    <div>
      <p>Client ID: {clientId}</p>
      <input onChange={(e) => search(e.target.value)} />
      {results.map(r => <div key={r.id}>{r.name}</div>)}
    </div>
  );
}
```

## Рекомендуемые настройки

### Для быстрого отклика (интерактивность)

```env
VITE_SEARCH_DEBOUNCE=200
VITE_SEARCH_THROTTLE=50
VITE_CACHE_ENABLED=true
VITE_THROTTLE_ENABLED=true
```

### Для экономии трафика (мобильные сети)

```env
VITE_SEARCH_DEBOUNCE=500
VITE_SEARCH_THROTTLE=200
VITE_CACHE_ENABLED=true
VITE_THROTTLE_ENABLED=true
VITE_CACHE_TTL=600000  # 10 минут
```

### Для максимальной производительности

```env
VITE_USE_DUAL_MODE=true
VITE_SEARCH_DEBOUNCE=200
VITE_SEARCH_THROTTLE=50
VITE_CACHE_ENABLED=true
VITE_CACHE_SIZE=200
```

## Метрики производительности

При правильной настройке вы получите:

- **Первый запрос:** ~50-150ms (сеть + сервер)
- **Повторный запрос (кэш):** ~1-5ms ⚡
- **Улучшение:** до 99% быстрее!

**Пример:**
1. Поиск "музей" → 120ms
2. Поиск "парк" → 95ms
3. Поиск "музей" снова → 2ms (кэш!) 🚀

## Отладка

### Включение логов в консоли

Откройте консоль браузера (F12), вы увидите:
- `[Cache] Найдено в кэше: "запрос"` - попадание в кэш
- `WebSocket подключен` - соединение установлено
- Статистику запросов и ответов

### Проблемы и решения

**WebSocket не подключается:**
- Проверьте, что сервер запущен
- Проверьте URL в `.env`
- Посмотрите ошибки в консоли сервера

**Кэш не работает:**
- Убедитесь, что `VITE_CACHE_ENABLED=true`
- Проверьте, что вводите одинаковые запросы
- Очистите кэш кнопкой "Очистить кэш"

**Запросы отправляются слишком часто:**
- Увеличьте `VITE_SEARCH_DEBOUNCE`
- Увеличьте `VITE_SEARCH_THROTTLE`
- Включите `VITE_THROTTLE_ENABLED=true`

## Интеграция с картой

Пример с Leaflet:

```tsx
import { MapContainer, TileLayer, Marker } from 'react-leaflet';
import { MapSearch } from './components/MapSearch';

function App() {
  const [position, setPosition] = useState<[number, number]>([55.75, 37.62]);

  const handleSelectResult = (result: MapObject) => {
    setPosition([result.coordinates.lat, result.coordinates.lng]);
  };

  return (
    <>
      <MapSearch
        wsUrl="ws://localhost:8080"
        onSelectResult={handleSelectResult}
      />
      <MapContainer center={position} zoom={13}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <Marker position={position} />
      </MapContainer>
    </>
  );
}
```
