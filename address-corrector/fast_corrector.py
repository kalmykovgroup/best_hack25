#!/usr/bin/env python3
"""
Быстрый корректор адресов на основе SQLite FTS5 словарей
Вместо медленного поиска по всей БД использует индексированные словари
"""
import sqlite3
import logging
import Levenshtein
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)


class FastAddressCorrector:
    """
    Быстрый корректор с использованием FTS5 словарей

    Производительность:
    - Старый подход (LIKE "%query%"): 700-1000 ms
    - Новый подход (FTS5 словари): 5-15 ms
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info("FastAddressCorrector initialized")

    def correct_street(self, query: str, limit: int = 5, min_similarity: float = 0.6) -> List[Dict]:
        """
        Быстрая коррекция названия улицы через FTS5 словарь

        Args:
            query: запрос для поиска (например "арбат", "орбат")
            limit: максимум результатов
            min_similarity: минимальная схожесть (0-1)

        Returns:
            список словарей с полями: street_name, similarity, usage_count
        """
        if not query or len(query) < 2:
            return []

        cursor = self.conn.cursor()

        # FTS5 поиск с prefix matching (очень быстро!)
        fts_query = self._escape_fts5(query) + "*"

        sql = """
            SELECT
                d.street_name,
                d.normalized_name,
                d.usage_count,
                bm25(street_dictionary_fts) as bm25_score
            FROM street_dictionary d
            JOIN street_dictionary_fts fts ON d.id = fts.rowid
            WHERE street_dictionary_fts MATCH ?
            ORDER BY bm25(street_dictionary_fts)
            LIMIT ?
        """

        cursor.execute(sql, [fts_query, limit * 3])  # Берём больше для Levenshtein фильтрации
        candidates = cursor.fetchall()

        # Если FTS5 ничего не нашел, fallback на Levenshtein со ВСЕМИ улицами + early exit
        if not candidates:
            logger.info(f"FTS5 found nothing for '{query}', trying Levenshtein on ALL streets (with early exit)")

            # Берем ВСЕ улицы, отсортированные по популярности
            # Early exit остановит поиск при нахождении достаточного количества совпадений
            cursor.execute("""
                SELECT street_name, normalized_name, usage_count
                FROM street_dictionary
                ORDER BY usage_count DESC
            """)
            candidates = cursor.fetchall()
            logger.info(f"Loaded {len(candidates)} street candidates for Levenshtein matching")

        # Вычислить Levenshtein только для топ-кандидатов (не для всей БД!)
        results = []
        query_lower = query.lower()

        # Список префиксов для удаления
        street_prefixes = ['улица', 'проспект', 'пр-кт', 'пр', 'переулок', 'пер', 'бульвар', 'б-р',
                          'набережная', 'наб', 'шоссе', 'ш', 'площадь', 'пл', 'проезд', 'тупик', 'туп']

        # Early exit счетчик
        good_matches = 0

        for row in candidates:
            normalized = row['normalized_name']

            # Levenshtein distance с полным названием
            distance = Levenshtein.distance(query_lower, normalized)
            max_len = max(len(query_lower), len(normalized), 1)
            similarity = 1.0 - (distance / max_len)

            # Также попробовать без префикса (для случаев "орбат" → "улица арбат")
            normalized_parts = normalized.split()
            best_similarity = similarity

            if len(normalized_parts) > 1:
                # Проверить similarity с каждой частью
                for part in normalized_parts:
                    if part not in street_prefixes:
                        part_distance = Levenshtein.distance(query_lower, part)
                        part_max_len = max(len(query_lower), len(part), 1)
                        part_similarity = 1.0 - (part_distance / part_max_len)
                        best_similarity = max(best_similarity, part_similarity)

            if best_similarity >= min_similarity:
                results.append({
                    'street_name': row['street_name'],
                    'normalized_name': normalized,
                    'similarity': best_similarity,
                    'usage_count': row['usage_count'],
                    'bm25_score': 0.0  # BM25 не применимо для Levenshtein fallback
                })

                # Early exit: если нашли достаточно хороших совпадений (>= 0.8), останавливаемся
                if best_similarity >= 0.8:
                    good_matches += 1
                    if good_matches >= limit * 2:  # limit * 2 чтобы было из чего выбрать
                        logger.info(f"Early exit: found {good_matches} good matches (>= 0.8)")
                        break

        # Сортировать по комбинированному score
        results.sort(key=lambda x: (x['similarity'] * 0.7 + min(x['usage_count'] / 1000, 1.0) * 0.3), reverse=True)

        return results[:limit]

    def correct_city(self, query: str, limit: int = 5, min_similarity: float = 0.6) -> List[Dict]:
        """
        Быстрая коррекция названия города через FTS5 словарь
        """
        if not query or len(query) < 2:
            return []

        cursor = self.conn.cursor()

        fts_query = self._escape_fts5(query) + "*"

        sql = """
            SELECT
                d.city_name,
                d.normalized_name,
                d.usage_count,
                bm25(city_dictionary_fts) as bm25_score
            FROM city_dictionary d
            JOIN city_dictionary_fts fts ON d.id = fts.rowid
            WHERE city_dictionary_fts MATCH ?
            ORDER BY bm25(city_dictionary_fts)
            LIMIT ?
        """

        cursor.execute(sql, [fts_query, limit * 3])
        candidates = cursor.fetchall()

        # Если FTS5 ничего не нашел, fallback на Levenshtein по топ-30 популярным городам
        if not candidates:
            logger.info(f"FTS5 found nothing for '{query}', trying Levenshtein on top-30 cities")
            cursor.execute("""
                SELECT city_name, normalized_name, usage_count
                FROM city_dictionary
                ORDER BY usage_count DESC
                LIMIT 30
            """)
            candidates = cursor.fetchall()

        results = []
        query_lower = query.lower()

        for row in candidates:
            normalized = row['normalized_name']
            distance = Levenshtein.distance(query_lower, normalized)
            max_len = max(len(query_lower), len(normalized), 1)
            similarity = 1.0 - (distance / max_len)

            if similarity >= min_similarity:
                results.append({
                    'city_name': row['city_name'],
                    'normalized_name': normalized,
                    'similarity': similarity,
                    'usage_count': row['usage_count'],
                    'bm25_score': 0.0  # BM25 не применимо для Levenshtein fallback
                })

        results.sort(key=lambda x: (x['similarity'] * 0.7 + min(x['usage_count'] / 1000, 1.0) * 0.3), reverse=True)

        return results[:limit]

    def correct_full_address(self, address: str, components: Dict) -> Tuple[str, bool]:
        """
        Коррекция полного адреса на основе компонентов

        Args:
            address: исходный адрес
            components: распарсенные компоненты (city, road, house_number)

        Returns:
            (corrected_address, was_corrected)
        """
        city = components.get('city', '').strip()
        street = components.get('road', '').strip()
        house = components.get('house_number', '').strip()

        was_corrected = False
        corrected_parts = []

        # Корректировать город
        if city:
            city_corrections = self.correct_city(city, limit=1, min_similarity=0.7)
            if city_corrections and city_corrections[0]['similarity'] < 1.0:
                corrected_city = city_corrections[0]['city_name']
                corrected_parts.append(corrected_city)
                was_corrected = True
                logger.info(f"City corrected: '{city}' -> '{corrected_city}' (similarity: {city_corrections[0]['similarity']:.2f})")
            else:
                corrected_parts.append(city)

        # Корректировать улицу
        if street:
            street_corrections = self.correct_street(street, limit=1, min_similarity=0.7)
            if street_corrections and street_corrections[0]['similarity'] < 1.0:
                corrected_street = street_corrections[0]['street_name']
                corrected_parts.append(corrected_street)
                was_corrected = True
                logger.info(f"Street corrected: '{street}' -> '{corrected_street}' (similarity: {street_corrections[0]['similarity']:.2f})")
            else:
                corrected_parts.append(street)

        # Добавить номер дома
        if house:
            corrected_parts.append(house)

        corrected_address = ', '.join(corrected_parts) if corrected_parts else address

        return corrected_address, was_corrected

    def _escape_fts5(self, text: str) -> str:
        """
        Экранировать специальные символы FTS5
        """
        if not text:
            return text

        # Убираем специальные символы
        import re
        text = re.sub(r'["\*\(\)\-\+/\^\\\[\]{}|<>.:;,!?@#$%&=~`\']', ' ', text)
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def get_statistics(self) -> Dict:
        """
        Получить статистику словарей
        """
        cursor = self.conn.cursor()

        stats = cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM street_dictionary) as total_streets,
                (SELECT COUNT(*) FROM city_dictionary) as total_cities,
                (SELECT AVG(usage_count) FROM street_dictionary) as avg_street_usage,
                (SELECT AVG(usage_count) FROM city_dictionary) as avg_city_usage
        """).fetchone()

        return {
            'total_streets': stats['total_streets'],
            'total_cities': stats['total_cities'],
            'avg_street_usage': stats['avg_street_usage'],
            'avg_city_usage': stats['avg_city_usage']
        }

    def close(self):
        if self.conn:
            self.conn.close()
