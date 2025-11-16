#!/usr/bin/env python3
"""
Миграция: добавляет колонку tags в таблицу buildings
"""
import sqlite3
import json
import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_add_tags(db_path):
    """Добавляет колонку tags и заполняет её из ways"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Проверить существует ли колонка tags
    cursor.execute("PRAGMA table_info(buildings)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'tags' in columns:
        logger.info("Column 'tags' already exists in buildings table")
        conn.close()
        return

    logger.info("Adding 'tags' column to buildings table...")
    cursor.execute("ALTER TABLE buildings ADD COLUMN tags TEXT")
    conn.commit()

    logger.info("Updating buildings with tags from ways...")

    # Получить все buildings
    cursor.execute("SELECT id FROM buildings")
    building_ids = [row[0] for row in cursor.fetchall()]

    logger.info(f"Found {len(building_ids)} buildings to update")

    updated_count = 0
    for building_id in building_ids:
        # Получить tags из ways
        cursor.execute("SELECT tags FROM ways WHERE id = ?", (building_id,))
        row = cursor.fetchone()

        if row and row[0]:
            cursor.execute("UPDATE buildings SET tags = ? WHERE id = ?", (row[0], building_id))
            updated_count += 1

        if updated_count % 1000 == 0:
            logger.info(f"Updated {updated_count} buildings...")
            conn.commit()

    conn.commit()
    conn.close()

    logger.info(f"Migration completed: updated {updated_count} buildings with tags")


if __name__ == "__main__":
    db_path = sys.argv[1] if len(sys.argv) > 1 else "/data/db/moscow.db"
    migrate_add_tags(db_path)
