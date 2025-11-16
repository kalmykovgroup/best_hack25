#!/usr/bin/env python3
"""
Инициализация БД: создание таблицы buildings из OSM данных
"""
import sqlite3
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def init_buildings_table(db_path):
    """Создает таблицу buildings из ways с адресами"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    logger.info("Creating buildings table from OSM ways...")

    # Создать таблицу buildings
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS buildings (
            id INTEGER PRIMARY KEY,
            city TEXT,
            street TEXT,
            housenumber TEXT,
            postcode TEXT,
            lat REAL,
            lon REAL,
            full_address TEXT,
            tags TEXT
        )
    ''')

    # Проверить есть ли уже данные
    cursor.execute("SELECT COUNT(*) FROM buildings")
    count = cursor.fetchone()[0]

    if count > 0:
        logger.info(f"Buildings table already has {count} records")
        conn.close()
        return

    logger.info("Extracting buildings from OSM ways...")

    # Извлечь ways с адресами
    cursor.execute("SELECT id, tags, nodes FROM ways")
    ways_processed = 0
    buildings_created = 0

    for way_id, tags_json, nodes_json in cursor.fetchall():
        try:
            tags = json.loads(tags_json) if tags_json else {}
            nodes_list = json.loads(nodes_json) if nodes_json else []

            # Проверить наличие адресных тегов
            if 'addr:street' in tags or 'addr:housenumber' in tags:
                # Получить координаты (центр way)
                if nodes_list:
                    # Получить координаты узлов
                    lats, lons = [], []
                    for node_id in nodes_list[:10]:  # Берем первые 10 узлов
                        cursor.execute("SELECT lat, lon FROM nodes WHERE id = ?", (node_id,))
                        node = cursor.fetchone()
                        if node:
                            lats.append(node[0])
                            lons.append(node[1])

                    if lats and lons:
                        center_lat = sum(lats) / len(lats)
                        center_lon = sum(lons) / len(lons)

                        city = tags.get('addr:city', tags.get('addr:town', 'Москва'))
                        street = tags.get('addr:street', '')
                        housenumber = tags.get('addr:housenumber', '')
                        postcode = tags.get('addr:postcode', '')

                        full_address = f"{city}, {street}, {housenumber}".strip(', ')

                        # Сохраняем все tags как JSON для дополнительной информации
                        cursor.execute('''
                            INSERT INTO buildings (id, city, street, housenumber, postcode, lat, lon, full_address, tags)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (way_id, city, street, housenumber, postcode, center_lat, center_lon, full_address, tags_json))

                        buildings_created += 1

            ways_processed += 1
            if ways_processed % 10000 == 0:
                logger.info(f"Processed {ways_processed} ways, created {buildings_created} buildings")
                conn.commit()

        except Exception as e:
            logger.warning(f"Error processing way {way_id}: {e}")
            continue

    # Создать FTS5 индекс
    logger.info("Creating FTS5 index...")
    cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS buildings_fts USING fts5(
            city, street, housenumber, full_address,
            content='buildings',
            content_rowid='id'
        )
    ''')

    cursor.execute('''
        INSERT INTO buildings_fts(rowid, city, street, housenumber, full_address)
        SELECT id, city, street, housenumber, full_address FROM buildings
    ''')

    conn.commit()
    conn.close()

    logger.info(f"Buildings table created: {buildings_created} buildings from {ways_processed} ways")


if __name__ == "__main__":
    import sys
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/data/db/moscow.db"
    init_buildings_table(db_path)
