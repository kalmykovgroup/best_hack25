#!/usr/bin/env python3
"""
Создание словарей для быстрой коррекции адресов
Извлекает уникальные названия улиц и городов из buildings и создает FTS5 индексы
"""
import sqlite3
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get('DB_PATH', '/data/db/moscow.db')


def create_street_dictionary(conn):
    """
    Создать словарь уникальных улиц с FTS5 индексом
    """
    logger.info("Creating street dictionary...")

    cursor = conn.cursor()

    # Создать таблицу словаря улиц
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS street_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            street_name TEXT NOT NULL UNIQUE,
            normalized_name TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0
        )
    """)

    # Создать FTS5 индекс для быстрого поиска
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS street_dictionary_fts
        USING fts5(street_name, normalized_name, content=street_dictionary, content_rowid=id)
    """)

    # Создать триггеры для автоматического обновления FTS5
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS street_dictionary_ai AFTER INSERT ON street_dictionary BEGIN
            INSERT INTO street_dictionary_fts(rowid, street_name, normalized_name)
            VALUES (new.id, new.street_name, new.normalized_name);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS street_dictionary_ad AFTER DELETE ON street_dictionary BEGIN
            DELETE FROM street_dictionary_fts WHERE rowid = old.id;
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS street_dictionary_au AFTER UPDATE ON street_dictionary BEGIN
            UPDATE street_dictionary_fts
            SET street_name = new.street_name, normalized_name = new.normalized_name
            WHERE rowid = new.id;
        END
    """)

    # Заполнить словарь из buildings
    logger.info("Extracting unique streets from buildings...")
    cursor.execute("""
        INSERT OR IGNORE INTO street_dictionary (street_name, normalized_name, usage_count)
        SELECT
            street,
            LOWER(TRIM(street)) as normalized_name,
            COUNT(*) as usage_count
        FROM buildings
        WHERE street IS NOT NULL AND street != ''
        GROUP BY LOWER(TRIM(street))
    """)

    count = cursor.execute("SELECT COUNT(*) FROM street_dictionary").fetchone()[0]
    logger.info(f"Street dictionary created: {count} unique streets")

    conn.commit()


def create_city_dictionary(conn):
    """
    Создать словарь уникальных городов с FTS5 индексом
    """
    logger.info("Creating city dictionary...")

    cursor = conn.cursor()

    # Создать таблицу словаря городов
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS city_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_name TEXT NOT NULL UNIQUE,
            normalized_name TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0
        )
    """)

    # Создать FTS5 индекс
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS city_dictionary_fts
        USING fts5(city_name, normalized_name, content=city_dictionary, content_rowid=id)
    """)

    # Триггеры
    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS city_dictionary_ai AFTER INSERT ON city_dictionary BEGIN
            INSERT INTO city_dictionary_fts(rowid, city_name, normalized_name)
            VALUES (new.id, new.city_name, new.normalized_name);
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS city_dictionary_ad AFTER DELETE ON city_dictionary BEGIN
            DELETE FROM city_dictionary_fts WHERE rowid = old.id;
        END
    """)

    cursor.execute("""
        CREATE TRIGGER IF NOT EXISTS city_dictionary_au AFTER UPDATE ON city_dictionary BEGIN
            UPDATE city_dictionary_fts
            SET city_name = new.city_name, normalized_name = new.normalized_name
            WHERE rowid = new.id;
        END
    """)

    # Заполнить словарь
    logger.info("Extracting unique cities from buildings...")
    cursor.execute("""
        INSERT OR IGNORE INTO city_dictionary (city_name, normalized_name, usage_count)
        SELECT
            city,
            LOWER(TRIM(city)) as normalized_name,
            COUNT(*) as usage_count
        FROM buildings
        WHERE city IS NOT NULL AND city != ''
        GROUP BY LOWER(TRIM(city))
    """)

    count = cursor.execute("SELECT COUNT(*) FROM city_dictionary").fetchone()[0]
    logger.info(f"City dictionary created: {count} unique cities")

    conn.commit()


def create_indexes(conn):
    """
    Создать дополнительные индексы для оптимизации
    """
    logger.info("Creating optimization indexes...")

    cursor = conn.cursor()

    # Индекс для быстрого подсчета usage_count
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_street_usage ON street_dictionary(usage_count DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_usage ON city_dictionary(usage_count DESC)")

    # Индекс для нормализованных названий
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_street_normalized ON street_dictionary(normalized_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_city_normalized ON city_dictionary(normalized_name)")

    conn.commit()
    logger.info("Optimization indexes created")


def main():
    """
    Создать все словари
    """
    if not os.path.exists(DB_PATH):
        logger.error(f"Database not found: {DB_PATH}")
        return

    logger.info(f"Opening database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        # Проверить существование таблицы buildings
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM buildings")
        buildings_count = cursor.fetchone()[0]
        logger.info(f"Found {buildings_count} buildings in database")

        if buildings_count == 0:
            logger.error("Buildings table is empty!")
            return

        # Создать словари
        create_street_dictionary(conn)
        create_city_dictionary(conn)
        create_indexes(conn)

        # Статистика
        logger.info("=" * 60)
        logger.info("Dictionary creation completed!")
        logger.info("=" * 60)

        stats = cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM street_dictionary) as streets,
                (SELECT COUNT(*) FROM city_dictionary) as cities,
                (SELECT COUNT(*) FROM buildings) as buildings
        """).fetchone()

        logger.info(f"Streets in dictionary: {stats['streets']}")
        logger.info(f"Cities in dictionary: {stats['cities']}")
        logger.info(f"Total buildings: {stats['buildings']}")

    except Exception as e:
        logger.error(f"Error creating dictionaries: {e}", exc_info=True)
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
