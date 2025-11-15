// Сервис кэширования результатов поиска

import { AddressObject } from '../types/api.types';

interface CacheEntry {
  results: AddressObject[];
  timestamp: number;
  hits: number; // Количество обращений к этому запросу
}

export class SearchCache {
  private cache = new Map<string, CacheEntry>();
  private readonly TTL: number; // Time To Live в миллисекундах
  private readonly maxSize: number; // Максимальный размер кэша

  constructor(ttl: number = 5 * 60 * 1000, maxSize: number = 100) {
    this.TTL = ttl;
    this.maxSize = maxSize;
  }

  /**
   * Получить результаты из кэша
   */
  get(query: string): AddressObject[] | null {
    const normalizedQuery = this.normalizeQuery(query);
    const cached = this.cache.get(normalizedQuery);

    if (!cached) {
      return null;
    }

    // Проверка TTL
    if (Date.now() - cached.timestamp > this.TTL) {
      this.cache.delete(normalizedQuery);
      return null;
    }

    // Увеличиваем счетчик обращений
    cached.hits++;

    return cached.results;
  }

  /**
   * Сохранить результаты в кэш
   */
  set(query: string, results: AddressObject[]): void {
    const normalizedQuery = this.normalizeQuery(query);

    // Проверка размера кэша
    if (this.cache.size >= this.maxSize && !this.cache.has(normalizedQuery)) {
      this.evictLeastUsed();
    }

    this.cache.set(normalizedQuery, {
      results,
      timestamp: Date.now(),
      hits: 0,
    });
  }

  /**
   * Проверить наличие в кэше
   */
  has(query: string): boolean {
    const normalizedQuery = this.normalizeQuery(query);
    const cached = this.cache.get(normalizedQuery);

    if (!cached) {
      return false;
    }

    // Проверка TTL
    if (Date.now() - cached.timestamp > this.TTL) {
      this.cache.delete(normalizedQuery);
      return false;
    }

    return true;
  }

  /**
   * Очистить весь кэш
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Удалить устаревшие записи
   */
  clearExpired(): void {
    const now = Date.now();
    const toDelete: string[] = [];

    this.cache.forEach((entry, key) => {
      if (now - entry.timestamp > this.TTL) {
        toDelete.push(key);
      }
    });

    toDelete.forEach(key => this.cache.delete(key));
  }

  /**
   * Получить статистику кэша
   */
  getStats() {
    const now = Date.now();
    let validEntries = 0;
    let expiredEntries = 0;
    let totalHits = 0;

    this.cache.forEach((entry) => {
      if (now - entry.timestamp <= this.TTL) {
        validEntries++;
        totalHits += entry.hits;
      } else {
        expiredEntries++;
      }
    });

    return {
      size: this.cache.size,
      validEntries,
      expiredEntries,
      totalHits,
      hitRate: validEntries > 0 ? totalHits / validEntries : 0,
    };
  }

  /**
   * Предзагрузка популярных запросов
   */
  prefetch(queries: string[], fetchFn: (query: string) => Promise<AddressObject[]>): void {
    queries.forEach(async (query) => {
      if (!this.has(query)) {
        try {
          const results = await fetchFn(query);
          this.set(query, results);
        } catch (error) {
          // Ошибки prefetch не критичны
        }
      }
    });
  }

  /**
   * Удалить наименее используемую запись (LRU)
   */
  private evictLeastUsed(): void {
    let minHits = Infinity;
    let oldestKey: string | null = null;
    let oldestTimestamp = Infinity;

    this.cache.forEach((entry, key) => {
      // Удаляем записи с наименьшим количеством обращений
      // При равенстве - самую старую
      if (entry.hits < minHits || (entry.hits === minHits && entry.timestamp < oldestTimestamp)) {
        minHits = entry.hits;
        oldestKey = key;
        oldestTimestamp = entry.timestamp;
      }
    });

    if (oldestKey) {
      this.cache.delete(oldestKey);
    }
  }

  /**
   * Нормализация запроса для единообразного ключа
   */
  private normalizeQuery(query: string): string {
    return query.toLowerCase().trim();
  }
}
