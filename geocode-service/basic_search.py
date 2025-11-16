"""
Базовый алгоритм поиска (Эксперимент 1)
Простой подход без продвинутой обработки текста
"""
import sqlite3
import logging

logger = logging.getLogger(__name__)


class BasicSearchEngine:
    """Базовый алгоритм: точное совпадение по компонентам"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        logger.info("BasicSearchEngine initialized")

    def search(self, components, limit=10):
        """
        Поиск по точному совпадению компонентов

        Args:
            components: dict с полями city, road, house_number
            limit: максимальное количество результатов

        Returns:
            list of dict
        """
        city = components.get('city', '').strip()
        street = components.get('road', '').strip()
        house_number = components.get('house_number', '').strip()

        # Строим WHERE условие
        conditions = []
        params = []

        if city:
            conditions.append("LOWER(city) = LOWER(?)")
            params.append(city)

        if street:
            conditions.append("LOWER(street) = LOWER(?)")
            params.append(street)

        if house_number:
            conditions.append("housenumber = ?")
            params.append(house_number)

        if not conditions:
            logger.warning("No search criteria provided")
            return []

        where_clause = " AND ".join(conditions)

        # Простой запрос с точным совпадением
        sql = f"""
            SELECT
                city,
                street,
                housenumber,
                lat,
                lon,
                1.0 as score
            FROM buildings
            WHERE {where_clause}
            LIMIT ?
        """

        params.append(limit)

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

        results = []
        for row in rows:
            results.append({
                'locality': row['city'] or '',
                'street': row['street'] or '',
                'number': row['housenumber'] or '',
                'lat': row['lat'],
                'lon': row['lon'],
                'score': row['score']
            })

        logger.info("BasicSearch: found %d results for components %s", len(results), components)
        return results

    def close(self):
        if self.conn:
            self.conn.close()
