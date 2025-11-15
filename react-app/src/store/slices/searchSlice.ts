import { createSlice, createAsyncThunk, PayloadAction } from '@reduxjs/toolkit';
import { SignalRService } from '../../services/signalr.service';
import { SearchCache } from '../../services/cache';
import { logger } from '../../utils/logger';
import {
  AddressObject,
  ApiResponse,
  SearchResultData,
  SearchProgress,
} from '../../types/api.types';

// Конфигурация
interface SearchConfig {
  hubUrl: string;
  debounceMs: number;
  throttleMs: number;
  cacheTTL: number;
  cacheSize: number;
  enableCache: boolean;
  enableThrottle: boolean;
  limit: number;
}

// Состояние
interface SearchState {
  // Результаты поиска
  results: AddressObject[];
  searchQuery: string;
  searchedAddress: string;
  totalFound: number;

  // Статусы
  isSearching: boolean;
  isConnected: boolean;
  isPythonServiceAvailable: boolean;
  isAddressParserAvailable: boolean;

  // Ошибки
  error: string | null;

  // Прогресс
  progress: SearchProgress | null;

  // Кэш
  cacheEnabled: boolean;
  cacheStats: {
    hits: number;
    misses: number;
  };
  showCacheHit: boolean;

  // Конфигурация
  config: SearchConfig;
}

const initialState: SearchState = {
  results: [],
  searchQuery: '',
  searchedAddress: '',
  totalFound: 0,

  isSearching: false,
  isConnected: false,
  isPythonServiceAvailable: true,
  isAddressParserAvailable: true,

  error: null,
  progress: null,

  cacheEnabled: false,
  cacheStats: {
    hits: 0,
    misses: 0,
  },
  showCacheHit: false,

  config: {
    hubUrl: import.meta.env.VITE_SIGNALR_HUB_URL || 'http://localhost:5034/hubs/geocode',
    debounceMs: parseInt(import.meta.env.VITE_SEARCH_DEBOUNCE || '300'),
    throttleMs: parseInt(import.meta.env.VITE_SEARCH_THROTTLE || '100'),
    cacheTTL: 5 * 60 * 1000,
    cacheSize: 100,
    enableCache: import.meta.env.VITE_CACHE_ENABLED === 'true',
    enableThrottle: import.meta.env.VITE_THROTTLE_ENABLED === 'true',
    limit: parseInt(import.meta.env.VITE_SEARCH_LIMIT || '10'),
  },
};

// SignalR сервис и кэш (singleton)
let signalRService: SignalRService | null = null;
let searchCache: SearchCache | null = null;
let latestRequestId: string | null = null;

// Получение или создание сервиса
const getSignalRService = (hubUrl: string): SignalRService => {
  if (!signalRService) {
    signalRService = new SignalRService(hubUrl);
  }
  return signalRService;
};

// Получение или создание кэша
const getSearchCache = (ttl: number, size: number): SearchCache => {
  if (!searchCache) {
    searchCache = new SearchCache(ttl, size);
  }
  return searchCache;
};

// Async thunk для инициализации подключения
export const initializeConnection = createAsyncThunk(
  'search/initializeConnection',
  async (_, { getState, dispatch }) => {
    const state = getState() as { search: SearchState };
    const service = getSignalRService(state.search.config.hubUrl);

    // Обработчики событий
    service.onMessage((response: ApiResponse<SearchResultData>) => {
      dispatch(handleSearchCompleted(response));
    });

    service.onProgress((progress: SearchProgress) => {
      dispatch(setProgress(progress));
    });

    service.onError((error: Error) => {
      dispatch(setError(error.message));
    });

    service.onConnected(() => {
      dispatch(setConnected(true));
      // Проверяем оба сервиса при подключении
      dispatch(checkPythonServiceStatus());
      dispatch(checkAddressParserServiceStatus());
    });

    service.onDisconnected(() => {
      dispatch(setConnected(false));
    });

    await service.connect();

    return true;
  }
);

// Async thunk для поиска адресов
export const searchAddress = createAsyncThunk(
  'search/searchAddress',
  async (query: string, { getState, dispatch }) => {
    const state = getState() as { search: SearchState };
    const { config, cacheEnabled } = state.search;

    // Проверка кэша
    if (cacheEnabled) {
      const cache = getSearchCache(config.cacheTTL, config.cacheSize);
      const cached = cache.get(query);

      if (cached) {
        logger.log(`[Redux] Найдено в кэше: "${query}"`);
        dispatch(setCacheHit(query));
        return {
          fromCache: true,
          data: {
            searchedAddress: query,
            objects: cached,
            totalFound: cached.length,
          } as SearchResultData,
        };
      } else {
        dispatch(incrementCacheMisses());
      }
    }

    // Отправка запроса
    const service = getSignalRService(config.hubUrl);
    const requestId = `search_${Date.now()}_${Math.random().toString(36).substring(7)}`;
    latestRequestId = requestId;

    await service.searchAddress({
      requestId,
      query,
      limit: config.limit,
    });

    return { fromCache: false };
  }
);

// Async thunk для проверки статуса Python сервиса
export const checkPythonServiceStatus = createAsyncThunk(
  'search/checkPythonServiceStatus',
  async (_, { getState }) => {
    const state = getState() as { search: SearchState };
    const service = getSignalRService(state.search.config.hubUrl);

    const isAvailable = await service.checkPythonServiceStatus();
    return isAvailable;
  }
);

// Async thunk для проверки статуса Address Parser сервиса
export const checkAddressParserServiceStatus = createAsyncThunk(
  'search/checkAddressParserServiceStatus',
  async (_, { getState }) => {
    const state = getState() as { search: SearchState };
    const service = getSignalRService(state.search.config.hubUrl);

    const isAvailable = await service.checkAddressParserServiceStatus();
    return isAvailable;
  }
);

// Slice
const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setSearchQuery: (state, action: PayloadAction<string>) => {
      state.searchQuery = action.payload;
    },

    setConnected: (state, action: PayloadAction<boolean>) => {
      state.isConnected = action.payload;
    },

    setError: (state, action: PayloadAction<string | null>) => {
      state.error = action.payload;
      if (action.payload) {
        state.isSearching = false;
      }
    },

    clearError: (state) => {
      state.error = null;
    },

    setProgress: (state, action: PayloadAction<SearchProgress>) => {
      state.progress = action.payload;
    },

    handleSearchCompleted: (state, action: PayloadAction<ApiResponse<SearchResultData>>) => {
      const response = action.payload;

      if (!response.success) {
        state.error = response.errorMessage || 'Неизвестная ошибка';
        state.isSearching = false;
        state.results = [];

        // Проверяем недоступность Python сервиса
        if (
          response.errorMessage?.includes('временно недоступен') ||
          response.errorMessage?.includes('не отвечает')
        ) {
          state.isPythonServiceAvailable = false;
        }
        return;
      }

      if (response.data && response.metadata?.requestId === latestRequestId) {
        state.results = response.data.objects;
        state.searchedAddress = response.data.searchedAddress;
        state.totalFound = response.data.totalFound;
        state.isSearching = false;
        state.error = null;
        state.isPythonServiceAvailable = true;

        // Сохраняем в кэш
        if (state.cacheEnabled && state.searchQuery) {
          const cache = getSearchCache(state.config.cacheTTL, state.config.cacheSize);
          cache.set(state.searchQuery, response.data.objects);
        }
      }
    },

    setCacheHit: (state, action: PayloadAction<string>) => {
      const query = action.payload;
      const cache = getSearchCache(state.config.cacheTTL, state.config.cacheSize);
      const cached = cache.get(query);

      if (cached) {
        state.results = cached;
        state.searchedAddress = query;
        state.totalFound = cached.length;
        state.isSearching = false;
        state.error = null;
        state.isPythonServiceAvailable = true;
        state.cacheStats.hits += 1;
        state.showCacheHit = true;

        // Скрываем индикатор через 1.5 сек
        setTimeout(() => {
          searchSlice.caseReducers.hideCacheHit(state);
        }, 1500);
      }
    },

    hideCacheHit: (state) => {
      state.showCacheHit = false;
    },

    incrementCacheMisses: (state) => {
      state.cacheStats.misses += 1;
    },

    toggleCache: (state) => {
      state.cacheEnabled = !state.cacheEnabled;
    },

    clearCache: (state) => {
      const cache = getSearchCache(state.config.cacheTTL, state.config.cacheSize);
      cache.clear();
      state.cacheStats = { hits: 0, misses: 0 };
    },

    clearResults: (state) => {
      state.results = [];
      state.searchedAddress = '';
      state.totalFound = 0;
      state.searchQuery = '';
    },
  },

  extraReducers: (builder) => {
    // initializeConnection
    builder.addCase(initializeConnection.pending, (state) => {
      state.isConnected = false;
    });
    builder.addCase(initializeConnection.fulfilled, (state) => {
      state.isConnected = true;
    });
    builder.addCase(initializeConnection.rejected, (state, action) => {
      state.isConnected = false;
      state.error = action.error.message || 'Ошибка подключения';
    });

    // searchAddress
    builder.addCase(searchAddress.pending, (state) => {
      state.isSearching = true;
    });
    builder.addCase(searchAddress.fulfilled, (_state, action) => {
      if (action.payload.fromCache) {
        // Обработано в setCacheHit
      } else {
        // Ждем ответа через SearchCompleted event
      }
    });
    builder.addCase(searchAddress.rejected, (state, action) => {
      state.isSearching = false;
      state.error = action.error.message || 'Ошибка поиска';
    });

    // checkPythonServiceStatus
    builder.addCase(checkPythonServiceStatus.fulfilled, (state, action) => {
      state.isPythonServiceAvailable = action.payload;
    });

    // checkAddressParserServiceStatus
    builder.addCase(checkAddressParserServiceStatus.fulfilled, (state, action) => {
      state.isAddressParserAvailable = action.payload;
    });
  },
});

export const {
  setSearchQuery,
  setConnected,
  setError,
  clearError,
  setProgress,
  handleSearchCompleted,
  setCacheHit,
  hideCacheHit,
  incrementCacheMisses,
  toggleCache,
  clearCache,
  clearResults,
} = searchSlice.actions;

export default searchSlice.reducer;
