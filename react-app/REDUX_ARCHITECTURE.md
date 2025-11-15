# Redux Architecture

## Обзор

Приложение использует **Redux Toolkit** для профессионального управления состоянием.

## Структура

```
src/
├── store/
│   ├── index.ts                    # Redux store
│   ├── hooks.ts                    # Типизированные хуки
│   └── slices/
│       └── searchSlice.ts          # Slice для поиска адресов
├── components/
│   └── AddressSearchRedux.tsx      # Компонент с Redux
└── main.tsx                        # Provider подключен здесь
```

## Redux Store

**`src/store/index.ts`**

```typescript
export const store = configureStore({
  reducer: {
    search: searchReducer,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
```

## Search Slice

**`src/store/slices/searchSlice.ts`**

### Состояние (State)

```typescript
interface SearchState {
  // Результаты
  results: AddressObject[];
  searchQuery: string;
  searchedAddress: string;
  totalFound: number;

  // Статусы подключения
  isSearching: boolean;
  isConnected: boolean;
  isPythonServiceAvailable: boolean;

  // Ошибки
  error: string | null;
  progress: SearchProgress | null;

  // Кэш
  cacheEnabled: boolean;
  cacheStats: { hits: number; misses: number };
  showCacheHit: boolean;

  // Конфигурация
  config: SearchConfig;
}
```

### Actions (Синхронные)

| Action | Описание |
|--------|----------|
| `setSearchQuery(query)` | Установить текст запроса |
| `setConnected(bool)` | Статус SignalR подключения |
| `setError(message)` | Установить ошибку |
| `clearError()` | Очистить ошибку |
| `setProgress(progress)` | Обновить прогресс поиска |
| `handleSearchCompleted(response)` | Обработать результат поиска |
| `toggleCache()` | Включить/выключить кэш |
| `clearCache()` | Очистить кэш |
| `clearResults()` | Очистить результаты |

### Async Thunks

| Thunk | Описание |
|-------|----------|
| `initializeConnection()` | Подключение к SignalR Hub |
| `searchAddress(query)` | Поиск адресов (с кэшированием) |
| `checkPythonServiceStatus()` | Проверка статуса Python сервиса |

## Типизированные Хуки

**`src/store/hooks.ts`**

```typescript
// Вместо стандартных useDispatch/useSelector
import { useAppDispatch, useAppSelector } from '../store/hooks';

const dispatch = useAppDispatch();
const results = useAppSelector((state) => state.search.results);
```

## Использование в компонентах

**`src/components/AddressSearchRedux.tsx`**

```typescript
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { searchAddress, toggleCache } from '../store/slices/searchSlice';

export const AddressSearchRedux = () => {
  const dispatch = useAppDispatch();

  // Получение состояния
  const { results, isSearching, error } = useAppSelector((state) => state.search);

  // Инициализация при монтировании
  useEffect(() => {
    dispatch(initializeConnection());
  }, [dispatch]);

  // Поиск с debounce
  const handleSearch = (query: string) => {
    dispatch(searchAddress(query));
  };

  // Управление кэшем
  const handleToggleCache = () => {
    dispatch(toggleCache());
  };
};
```

## Архитектурные преимущества

### ✅ Что улучшено:

1. **Централизованное состояние**
   - Все состояние в одном месте (Redux store)
   - Легко отслеживать изменения через Redux DevTools

2. **Типизация**
   - Полная TypeScript типизация
   - Автодополнение для actions и state

3. **Разделение ответственности**
   - Slice: бизнес-логика
   - Components: только UI
   - Services: работа с API

4. **Async логика**
   - createAsyncThunk для асинхронных операций
   - Автоматическое управление pending/fulfilled/rejected

5. **Мемоизация**
   - useAppSelector автоматически мемоизирует выборки
   - Компоненты перерисовываются только при изменении нужных данных

6. **Middleware**
   - Redux Toolkit включает redux-thunk из коробки
   - Легко добавить logger, saga и другие

### 🗑️ Что удалено:

- ❌ `useWebSocket.ts` - старый WebSocket хук
- ❌ `useMapSearch.ts` - старая логика поиска
- ❌ `useDualWebSocket.ts` - двухканальный WebSocket
- ❌ `useMapSearchDual.ts` - поиск для dual mode
- ❌ `websocket.ts` - старый WebSocket сервис
- ❌ `dual-websocket.ts` - dual WebSocket сервис

### 📦 Что осталось:

- ✅ `useSignalR.ts` - обертка над SignalR (используется в slice)
- ✅ `useThrottle.ts` - throttling утилита
- ✅ `signalr.service.ts` - SignalR клиент
- ✅ `cache.ts` - LRU кэш

## Сравнение: До и После

### До (useState + custom hooks)

```typescript
const [results, setResults] = useState([]);
const [isSearching, setIsSearching] = useState(false);
const [error, setError] = useState(null);
const [isConnected, setIsConnected] = useState(false);
// ... еще 10 useState

const { search, ... } = useAddressSearch({
  hubUrl,
  debounceMs,
  // ... куча параметров
});
```

**Проблемы:**
- Дублирование состояния
- Сложно отследить изменения
- Prop drilling
- Сложно тестировать

### После (Redux Toolkit)

```typescript
const dispatch = useAppDispatch();
const { results, isSearching, error, isConnected } = useAppSelector(
  (state) => state.search
);

dispatch(searchAddress(query));
```

**Преимущества:**
- Одно место для состояния
- Redux DevTools
- Легко тестировать
- Легко расширять

## Тестирование

### Тест actions

```typescript
import { searchSlice, setSearchQuery } from './searchSlice';

test('setSearchQuery updates query', () => {
  const state = searchSlice.reducer(
    undefined,
    setSearchQuery('Москва')
  );

  expect(state.searchQuery).toBe('Москва');
});
```

### Тест async thunks

```typescript
import { searchAddress } from './searchSlice';
import { configureStore } from '@reduxjs/toolkit';

test('searchAddress fetches results', async () => {
  const store = configureStore({ reducer: { search: searchSlice.reducer } });

  await store.dispatch(searchAddress('Москва'));

  const state = store.getState().search;
  expect(state.results.length).toBeGreaterThan(0);
});
```

## Redux DevTools

Установите расширение [Redux DevTools](https://github.com/reduxjs/redux-devtools) для Chrome/Firefox.

### Функции:

- ⏱️ **Time Travel** - перемещение между состояниями
- 📊 **Action Log** - история всех actions
- 📈 **State Diff** - сравнение состояний
- 🔍 **State Inspector** - просмотр текущего состояния

## Будущие улучшения

- [ ] RTK Query для автоматического кэширования API
- [ ] Middleware для логирования
- [ ] Персистентность состояния (localStorage)
- [ ] Optimistic updates
- [ ] Undo/Redo функциональность

## Ресурсы

- [Redux Toolkit Docs](https://redux-toolkit.js.org/)
- [Redux DevTools](https://github.com/reduxjs/redux-devtools)
- [Best Practices](https://redux.js.org/style-guide/style-guide)
