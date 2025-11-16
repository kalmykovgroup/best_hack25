#!/usr/bin/env python3
"""
OSM Importer - импорт зданий Москвы из OSM PBF в SQLite
Для хакатона "Геокодирование адресов"
"""
import sys
import os
import sqlite3
import logging
import osmium

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class MoscowBuildingsHandler(osmium.SimpleHandler):
    """Извлечение зданий Москвы с адресной информацией"""

    def __init__(self):
        super().__init__()
        self.buildings = []
        self.node_locations = {}
        self.count = 0

    def node(self, n):
        """Обработка nodes"""
        # Кэшируем координаты для ways
        self.node_locations[n.id] = (n.location.lat, n.location.lon)

        # Проверяем есть ли адресная информация
        tags = {tag.k: tag.v for tag in n.tags}
        if self._has_address_info(tags):
            self._extract_building(n.id, 'node', tags, n.location.lat, n.location.lon)

    def way(self, w):
        """Обработка ways (здания обычно ways)"""
        tags = {tag.k: tag.v for tag in w.tags}

        # Проверяем что это здание с адресом
        if not self._has_address_info(tags):
            return

        # Вычисляем центр way
        lats, lons = [], []
        for node_ref in w.nodes:
            if node_ref.ref in self.node_locations:
                lat, lon = self.node_locations[node_ref.ref]
                lats.append(lat)
                lons.append(lon)

        if lats:
            center_lat = sum(lats) / len(lats)
            center_lon = sum(lons) / len(lons)
            self._extract_building(w.id, 'way', tags, center_lat, center_lon)

    def _has_address_info(self, tags):
        """Проверка наличия адресной информации"""
        # Должен быть хотя бы город и улица, или полный адрес
        has_street = 'addr:street' in tags
        has_city = 'addr:city' in tags or tags.get('addr:city') == 'Москва'
        has_housenumber = 'addr:housenumber' in tags

        return (has_street or has_city) and len(tags) > 2

    def _extract_building(self, osm_id, osm_type, tags, lat, lon):
        """Извлечь данные здания"""
        city = tags.get('addr:city', 'Москва')
        street = tags.get('addr:street', '')
        housenumber = tags.get('addr:housenumber', '')
        suburb = tags.get('addr:suburb', '')
        postcode = tags.get('addr:postcode', '')

        # Формируем полный адрес для FTS поиска
        parts = []
        if city:
            parts.append(city)
        if suburb:
            parts.append(suburb)
        if street:
            parts.append(street)
        if housenumber:
            parts.append(housenumber)

        full_address = ' '.join(parts).lower()

        if full_address.strip():
            self.buildings.append({
                'osm_id': osm_id,
                'osm_type': osm_type,
                'city': city,
                'street': street,
                'housenumber': housenumber,
                'suburb': suburb,
                'postcode': postcode,
                'full_address': full_address,
                'lat': lat,
                'lon': lon
            })

            self.count += 1
            if self.count % 10000 == 0:
                logger.info("Processed %d buildings", self.count)


def create_database(db_path):
    """Создать структуру БД"""
    logger.info("Creating database at %s", db_path)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Таблица зданий
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            osm_id BIGINT NOT NULL,
            osm_type TEXT NOT NULL,
            city TEXT,
            street TEXT,
            housenumber TEXT,
            suburb TEXT,
            postcode TEXT,
            full_address TEXT NOT NULL,
            lat REAL NOT NULL,
            lon REAL NOT NULL
        )
    """)

    # Индексы для базового алгоритма
    logger.info("Creating indexes...")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city ON buildings(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_street ON buildings(street)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_housenumber ON buildings(housenumber)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_coordinates ON buildings(lat, lon)")

    # Составные индексы для ускорения сложных запросов
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_street ON buildings(city, street)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_street_house ON buildings(city, street, housenumber)")

    # FTS5 для улучшенного алгоритма
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS buildings_fts USING fts5(
            full_address,
            city,
            street,
            content='buildings',
            content_rowid='id'
        )
    """)

    # Триггеры для автоматического обновления FTS
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS buildings_ai AFTER INSERT ON buildings BEGIN
            INSERT INTO buildings_fts(rowid, full_address, city, street)
            VALUES (new.id, new.full_address, new.city, new.street);
        END
    """)

    conn.commit()
    logger.info("Database schema created")
    return conn


def import_osm(pbf_path, db_path):
    """Импорт OSM PBF в SQLite"""
    if not os.path.exists(pbf_path):
        raise FileNotFoundError(f"OSM file not found: {pbf_path}")

    logger.info("OSM file: %s (%.2f MB)", pbf_path, os.path.getsize(pbf_path) / 1024 / 1024)

    # Создать БД
    conn = create_database(db_path)

    # Парсинг OSM
    logger.info("Parsing OSM file...")
    handler = MoscowBuildingsHandler()
    handler.apply_file(pbf_path, locations=True)

    logger.info("Found %d buildings with addresses", len(handler.buildings))

    # Вставка данных
    logger.info("Inserting into database...")
    cursor = conn.cursor()

    batch_size = 1000
    for i in range(0, len(handler.buildings), batch_size):
        batch = handler.buildings[i:i + batch_size]
        cursor.executemany("""
            INSERT INTO buildings (osm_id, osm_type, city, street, housenumber,
                                   suburb, postcode, full_address, lat, lon)
            VALUES (:osm_id, :osm_type, :city, :street, :housenumber,
                    :suburb, :postcode, :full_address, :lat, :lon)
        """, batch)

        if (i // batch_size) % 10 == 0:
            logger.info("Inserted %d / %d", min(i + batch_size, len(handler.buildings)), len(handler.buildings))

    # Оптимизация FTS
    logger.info("Optimizing FTS index...")
    cursor.execute("INSERT INTO buildings_fts(buildings_fts) VALUES('optimize')")

    conn.commit()

    # Оптимизации SQLite для производительности
    logger.info("Applying SQLite optimizations...")

    # Обновление статистики для оптимизатора запросов
    logger.info("  Running ANALYZE...")
    cursor.execute("ANALYZE")

    # WAL режим (Write-Ahead Logging) для параллельного доступа
    logger.info("  Enabling WAL mode...")
    cursor.execute("PRAGMA journal_mode = WAL")

    # Увеличение cache для ускорения запросов
    logger.info("  Increasing cache size...")
    cursor.execute("PRAGMA cache_size = -64000")  # 64MB

    # Memory-mapped I/O для быстрого доступа
    logger.info("  Enabling memory-mapped I/O...")
    cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB

    conn.commit()

    # Статистика
    cursor.execute("SELECT COUNT(*) FROM buildings")
    total = cursor.fetchone()[0]

    logger.info("=" * 60)
    logger.info("Import completed!")
    logger.info("  Total buildings: %d", total)
    logger.info("  Database size: %.2f MB", os.path.getsize(db_path) / 1024 / 1024)
    logger.info("=" * 60)

    conn.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python osm_importer.py <osm_pbf> <output_db>")
        sys.exit(1)

    import_osm(sys.argv[1], sys.argv[2])
