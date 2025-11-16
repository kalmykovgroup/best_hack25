import { useEffect, useRef, useCallback, useState } from 'react';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import {
  initializeConnection,
  searchAddress,
  checkPythonServiceStatus,
  checkAddressParserServiceStatus,
  setSearchQuery,
  toggleCache,
  clearCache,
} from '../store/slices/searchSlice';
import { logger } from '../utils/logger';
import { AddressObject } from '../types/api.types';
import './MapSearch.css';

interface AddressSearchReduxProps {
  onSelectResult?: (result: AddressObject) => void;
}

export const AddressSearchRedux = ({ onSelectResult }: AddressSearchReduxProps) => {
  const dispatch = useAppDispatch();

  // Получаем состояние из Redux
  const {
    results,
    searchQuery,
    searchedAddress,
    totalFound,
    isSearching,
    isConnected,
    isPythonServiceAvailable,
    isAddressParserAvailable,
    error,
    cacheEnabled,
    showCacheHit,
    lastExecutionTimeMs,
  } = useAppSelector((state) => state.search);

  // Локальное состояние для задержки показа загрузчика
  const [showLoader, setShowLoader] = useState(false);

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const healthCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const loaderDelayTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Инициализация подключения при монтировании
  useEffect(() => {
    dispatch(initializeConnection());

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      if (healthCheckIntervalRef.current) {
        clearInterval(healthCheckIntervalRef.current);
      }
      if (loaderDelayTimerRef.current) {
        clearTimeout(loaderDelayTimerRef.current);
      }
    };
  }, [dispatch]);

  // Задержка показа загрузчика (1 секунда)
  useEffect(() => {
    const shouldShowLoader = !isConnected || !isPythonServiceAvailable || !isAddressParserAvailable;

    if (shouldShowLoader) {
      // Если уже не подключены, запускаем таймер на 1 секунду
      if (loaderDelayTimerRef.current) {
        clearTimeout(loaderDelayTimerRef.current);
      }

      loaderDelayTimerRef.current = setTimeout(() => {
        setShowLoader(true);
      }, 1000); // Задержка 1 секунда
    } else {
      // Если подключение восстановилось, сразу скрываем загрузчик
      if (loaderDelayTimerRef.current) {
        clearTimeout(loaderDelayTimerRef.current);
        loaderDelayTimerRef.current = null;
      }
      setShowLoader(false);
    }

    return () => {
      if (loaderDelayTimerRef.current) {
        clearTimeout(loaderDelayTimerRef.current);
      }
    };
  }, [isConnected, isPythonServiceAvailable, isAddressParserAvailable]);

  // Периодическая проверка сервисов если недоступны
  useEffect(() => {
    if (healthCheckIntervalRef.current) {
      clearInterval(healthCheckIntervalRef.current);
      healthCheckIntervalRef.current = null;
    }

    const needsHealthCheck = (!isPythonServiceAvailable || !isAddressParserAvailable) && isConnected;

    if (needsHealthCheck) {
      logger.log('[AddressSearchRedux] Запуск проверки сервисов (каждые 3 сек)');

      healthCheckIntervalRef.current = setInterval(() => {
        if (!isPythonServiceAvailable) {
          dispatch(checkPythonServiceStatus());
        }
        if (!isAddressParserAvailable) {
          dispatch(checkAddressParserServiceStatus());
        }
      }, 3000);
    }

    return () => {
      if (healthCheckIntervalRef.current) {
        clearInterval(healthCheckIntervalRef.current);
        healthCheckIntervalRef.current = null;
      }
    };
  }, [isPythonServiceAvailable, isAddressParserAvailable, isConnected, dispatch]);

  // Обработка ввода с debounce
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const query = e.target.value;
      dispatch(setSearchQuery(query));

      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      if (!query) {
        return;
      }

      debounceTimerRef.current = setTimeout(() => {
        dispatch(searchAddress(query));
      }, 300); // Debounce delay
    },
    [dispatch]
  );

  const handleResultClick = (result: AddressObject) => {
    onSelectResult?.(result);
  };

  const handleToggleCache = () => {
    // При отключении кеша - очищаем его
    if (cacheEnabled) {
      dispatch(clearCache());
    }
    dispatch(toggleCache());
  };

  // Определяем сообщение загрузчика
  const getLoaderMessage = () => {
    if (!isConnected) {
      return 'Подключение к серверу...';
    }
    if (!isPythonServiceAvailable && !isAddressParserAvailable) {
      return 'Подключение к сервисам поиска и нормализации...';
    }
    if (!isPythonServiceAvailable) {
      return 'Подключение к сервису поиска...';
    }
    if (!isAddressParserAvailable) {
      return 'Подключение к сервису нормализации адресов...';
    }
    return 'Подключение...';
  };

  return (
    <>
      {showLoader && (
        <div className="connection-loader">
          <div className="loader-overlay" />
          <div className="loader-content">
            <div className="loader-spinner" />
            <p>{getLoaderMessage()}</p>
          </div>
        </div>
      )}

      <div className="map-search">
        <div className="search-header">
          <div className="search-input-wrapper">
            <input
              type="text"
              className="search-input"
              placeholder="Поиск адреса (город, улица, дом)..."
              value={searchQuery}
              onChange={handleInputChange}
              disabled={!isConnected}
            />
            {isSearching && <div className="search-spinner" />}
            {lastExecutionTimeMs !== null && !isSearching && (
              <div className="execution-time">
                {lastExecutionTimeMs}ms
              </div>
            )}
          </div>

          <label className="cache-checkbox">
            <input
              type="checkbox"
              checked={cacheEnabled}
              onChange={handleToggleCache}
            />
            <span>Кэш</span>
          </label>
        </div>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {searchedAddress && results.length === 0 && !isSearching && !error && (
          <div className="no-results">
            Ничего не найдено по запросу "{searchedAddress}"
          </div>
        )}

        {results.length > 0 && (
          <div className="search-results">
            {results.map((result, index) => (
              <div
                key={`${result.locality}-${result.street}-${result.number}-${index}`}
                className="search-result-item"
                onClick={() => handleResultClick(result)}
              >
                <div className="result-name">
                  Адрес: {result.locality}, {result.street} {result.number}
                </div>
                <div className="result-coordinates">
                  Координаты: {result.lat.toFixed(6)}, {result.lon.toFixed(6)}
                </div>
                {result.score > 0 && (
                  <div className="result-score">
                    Релевантность: {(result.score * 100).toFixed(0)}%
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {results.length > 0 && (
          <div className="search-info">
            <span>
              Найдено: {results.length}
              {totalFound > results.length && ` из ${totalFound}`}
            </span>
            {showCacheHit && cacheEnabled && (
              <span className="cache-hit-indicator">⚡ Из кэша</span>
            )}
          </div>
        )}
      </div>
    </>
  );
};
