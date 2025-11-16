"""
Улучшенный алгоритм поиска (Эксперимент 2)
Использование FTS5, Левенштейна, нормализаций
"""
import sqlite3
import logging
import re
import Levenshtein

logger = logging.getLogger(__name__)


def escape_fts5_query(text):
    """
    Экранирует специальные символы FTS5

    FTS5 специальные символы: " * ( ) - + / ^ \\ : ; и другие
    Заменяем их на пробелы, чтобы избежать синтаксических ошибок
    """
    if not text:
        return text

    # Убираем специальные символы FTS5 и другие потенциально опасные символы
    # Оставляем только буквы, цифры, пробелы и базовые безопасные символы
    # Добавлены: : ; , ! ? @ # $ % & = ~
    text = re.sub(r'["\*\(\)\-\+/\^\\\[\]{}|<>.:;,!?@#$%&=~`\']', ' ', text)

    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


def normalize_address_for_comparison(address, remove_house_number=False):
    """
    Нормализует адрес для Levenshtein сравнения

    Args:
        address: строка адреса
        remove_house_number: удалить номера домов (полезно если в запросе нет номера)

    Returns:
        нормализованная строка
    """
    if not address:
        return ""

    # Приводим к нижнему регистру
    normalized = address.lower().strip()

    # Служебные слова для удаления (ФИАС стандарт)
    service_words = [
        # Улицы
        'улица', 'ул.', 'ул', 'проспект', 'пр-кт', 'пр.', 'пр',
        'переулок', 'пер.', 'пер', 'бульвар', 'б-р', 'бул.',
        'набережная', 'наб.', 'наб', 'шоссе', 'ш.', 'ш',
        'площадь', 'пл.', 'пл', 'проезд', 'пр-д', 'тупик', 'туп.',
        # Дома
        'дом', 'д.', 'д', 'здание', 'зд.', 'зд',
        'строение', 'стр.', 'стр', 'корпус', 'к.', 'к',
        'владение', 'влд.', 'влд',
        # Города
        'город', 'г.', 'г',
    ]

    # Удаляем запятые и другие знаки препинания
    normalized = re.sub(r'[,;:]', ' ', normalized)

    # Разбиваем на слова
    words = normalized.split()

    # Удаляем служебные слова
    filtered_words = []
    for word in words:
        # Пропускаем служебные слова
        if word in service_words:
            continue

        # Если нужно удалить номера домов
        if remove_house_number:
            # Пропускаем слова, которые выглядят как номера домов
            # Примеры: "10", "10а", "10/2", "10к1"
            if re.match(r'^\d+[а-я]?(/\d+)?(к\d+)?$', word):
                continue

        filtered_words.append(word)

    # Сортируем слова для устранения различий в порядке
    # Это помогает когда "алма-атинская улица" vs "улица алма-атинская"
    filtered_words.sort()

    return ' '.join(filtered_words)


class AdvancedSearchEngine:
    """Улучшенный алгоритм с нечетким поиском и метриками"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info("AdvancedSearchEngine initialized")

    def search(self, components, original_address, limit=10):
        """
        Улучшенный поиск с FTS5 и метриками

        Args:
            components: dict с полями city, road, house_number
            original_address: исходная строка адреса
            limit: максимальное количество результатов

        Returns:
            list of dict
        """
        city = components.get('city', '').strip()
        street = components.get('road', '').strip()
        house_number = components.get('house_number', '').strip()

        # Экранируем специальные символы FTS5
        city = escape_fts5_query(city)
        street = escape_fts5_query(street)
        house_number = escape_fts5_query(house_number)

        # Формируем запрос для FTS5 с prefix matching
        fts_query_parts = []
        if city:
            fts_query_parts.append(f"{city}*")
        if street:
            fts_query_parts.append(f"{street}*")
        if house_number:
            fts_query_parts.append(f"{house_number}*")

        if not fts_query_parts:
            # Если компонентов нет, пробуем по полному адресу
            escaped_address = escape_fts5_query(original_address.lower())
            words = escaped_address.split()
            fts_query_parts = [f"{w}*" for w in words if len(w) > 2]

        if not fts_query_parts:
            logger.warning("No query parts for FTS search")
            return []

        fts_query = " ".join(fts_query_parts)

        # FTS5 поиск с BM25 ранжированием
        sql = """
            SELECT
                b.city,
                b.street,
                b.housenumber,
                b.lat,
                b.lon,
                b.full_address,
                b.tags,
                bm25(buildings_fts) as bm25_score
            FROM buildings b
            JOIN buildings_fts fts ON b.id = fts.rowid
            WHERE buildings_fts MATCH ?
            ORDER BY bm25(buildings_fts)
            LIMIT ?
        """

        cursor = self.conn.cursor()
        cursor.execute(sql, [fts_query, limit * 2])
        rows = cursor.fetchall()

        if not rows:
            logger.info("AdvancedSearch: no FTS results")
            return []

        # Вычисляем комбинированный score
        results = []
        for row in rows:
            # 1. BM25 score (нормализуем в 0-1)
            bm25_score = abs(row['bm25_score'])
            max_bm25 = abs(rows[0]['bm25_score']) if rows else 1.0
            normalized_bm25 = min(bm25_score / max_bm25, 1.0) if max_bm25 > 0 else 0.0

            # 2. Левенштейн для текстового сходства
            # Нормализуем адреса для корректного сравнения
            predicted_addr_normalized = normalize_address_for_comparison(
                row['full_address'],
                remove_house_number=False
            )
            original_addr_normalized = normalize_address_for_comparison(
                original_address,
                remove_house_number=False
            )

            lev_distance = Levenshtein.distance(predicted_addr_normalized, original_addr_normalized)
            max_len = max(len(predicted_addr_normalized), len(original_addr_normalized), 1)
            lev_score = 1.0 - (lev_distance / max_len) if max_len > 0 else 0.0

            # 3. Совпадение компонентов (строгое совпадение)
            component_matches = 0
            total_components = 0

            if city:
                total_components += 1
                if row['city'] and city.lower() == row['city'].lower():
                    component_matches += 1
                elif row['city'] and city.lower() in row['city'].lower():
                    component_matches += 0.5

            if street:
                total_components += 1
                street_normalized = normalize_address_for_comparison(street)
                db_street_normalized = normalize_address_for_comparison(row['street'] or '')

                if street_normalized == db_street_normalized:
                    component_matches += 1
                elif street_normalized and db_street_normalized and street_normalized in db_street_normalized:
                    component_matches += 0.7

            if house_number:
                total_components += 1
                if row['housenumber'] and house_number == row['housenumber']:
                    component_matches += 1
                elif row['housenumber'] and house_number in row['housenumber']:
                    component_matches += 0.5
                elif not row['housenumber']:
                    component_matches -= 0.3  # Штраф за отсутствие номера

            component_score = component_matches / total_components if total_components > 0 else 0.0

            # Комбинированный score (взвешенная сумма для максимальной продуктивности)
            final_score = (
                0.25 * lev_score +
                0.60 * component_score +
                0.15 * normalized_bm25
            )

            # Детальное логирование для первого результата
            if len(results) == 0:
                logger.info(
                    "Score calculation details:\n"
                    "  Input city='%s', street='%s', house='%s'\n"
                    "  DB city='%s', street='%s', house='%s'\n"
                    "  Original address: '%s'\n"
                    "  DB full_address: '%s'\n"
                    "  Normalized input: '%s'\n"
                    "  Normalized DB: '%s'\n"
                    "  Component score: %.3f (matches: %.1f / total: %d)\n"
                    "  Levenshtein score: %.3f (distance: %d / max_len: %d)\n"
                    "  BM25 score: %.3f\n"
                    "  FINAL SCORE: %.3f",
                    city, street, house_number,
                    row['city'], row['street'], row['housenumber'],
                    original_address,
                    row['full_address'],
                    original_addr_normalized,
                    predicted_addr_normalized,
                    component_score, component_matches, total_components,
                    lev_score, lev_distance, max_len,
                    normalized_bm25,
                    final_score
                )

            # Парсим tags из JSON
            import json
            tags_data = {}
            try:
                if row['tags']:
                    tags_data = json.loads(row['tags'])
            except:
                pass

            results.append({
                'locality': row['city'] or '',
                'street': row['street'] or '',
                'number': row['housenumber'] or '',
                'lat': row['lat'],
                'lon': row['lon'],
                'score': final_score,
                'full_address': row['full_address'],
                'lev_score': lev_score,
                'tags': tags_data
            })

        # Сортируем по score и берем топ-N
        results.sort(key=lambda x: x['score'], reverse=True)
        results = results[:limit]

        logger.info("AdvancedSearch: found %d results (top score: %.3f)",
                    len(results), results[0]['score'] if results else 0.0)

        return results

    def close(self):
        if self.conn:
            self.conn.close()
