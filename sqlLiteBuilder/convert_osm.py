#!/usr/bin/env python3
"""
Конвертирует OSM PBF файл в SQLite базу данных
"""
import sqlite3
import osmium
import sys
from pathlib import Path

class OSMHandler(osmium.SimpleHandler):
    def __init__(self, db_path):
        osmium.SimpleHandler.__init__(self)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self._create_tables()
        self.node_count = 0
        self.way_count = 0
        self.relation_count = 0

    def _create_tables(self):
        """Создает таблицы для хранения OSM данных"""
        # Таблица для узлов (nodes)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id INTEGER PRIMARY KEY,
                lat REAL,
                lon REAL,
                tags TEXT
            )
        ''')

        # Таблица для путей (ways)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ways (
                id INTEGER PRIMARY KEY,
                tags TEXT,
                nodes TEXT
            )
        ''')

        # Таблица для отношений (relations)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS relations (
                id INTEGER PRIMARY KEY,
                tags TEXT,
                members TEXT
            )
        ''')

        # Индексы для быстрого поиска
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_location ON nodes(lat, lon)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_ways_id ON ways(id)')

        self.conn.commit()

    def _tags_to_json(self, tags):
        """Конвертирует теги OSM в JSON строку"""
        import json
        return json.dumps({tag.k: tag.v for tag in tags})

    def node(self, n):
        """Обработка узлов"""
        tags = self._tags_to_json(n.tags)
        self.cursor.execute(
            'INSERT OR REPLACE INTO nodes (id, lat, lon, tags) VALUES (?, ?, ?, ?)',
            (n.id, n.location.lat, n.location.lon, tags)
        )
        self.node_count += 1

        if self.node_count % 10000 == 0:
            print(f"Обработано узлов: {self.node_count}")
            self.conn.commit()

    def way(self, w):
        """Обработка путей"""
        import json
        tags = self._tags_to_json(w.tags)
        nodes = json.dumps([n.ref for n in w.nodes])

        self.cursor.execute(
            'INSERT OR REPLACE INTO ways (id, tags, nodes) VALUES (?, ?, ?)',
            (w.id, tags, nodes)
        )
        self.way_count += 1

        if self.way_count % 10000 == 0:
            print(f"Обработано путей: {self.way_count}")
            self.conn.commit()

    def relation(self, r):
        """Обработка отношений"""
        import json
        tags = self._tags_to_json(r.tags)
        members = json.dumps([
            {'type': m.type, 'ref': m.ref, 'role': m.role}
            for m in r.members
        ])

        self.cursor.execute(
            'INSERT OR REPLACE INTO relations (id, tags, members) VALUES (?, ?, ?)',
            (r.id, tags, members)
        )
        self.relation_count += 1

        if self.relation_count % 1000 == 0:
            print(f"Обработано отношений: {self.relation_count}")
            self.conn.commit()

    def finalize(self):
        """Финализация и сохранение данных"""
        self.conn.commit()

        # Создаем дополнительные индексы
        print("Создание индексов...")
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_nodes_tags ON nodes(tags)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_ways_tags ON ways(tags)')
        self.cursor.execute('CREATE INDEX IF NOT EXISTS idx_relations_tags ON relations(tags)')

        self.conn.commit()
        self.conn.close()

        print(f"\nКонвертация завершена!")
        print(f"Узлов: {self.node_count}")
        print(f"Путей: {self.way_count}")
        print(f"Отношений: {self.relation_count}")


def convert_osm_to_sqlite(osm_file, db_file):
    """Конвертирует OSM PBF файл в SQLite базу"""
    print(f"Начинаю конвертацию {osm_file} -> {db_file}")

    if not Path(osm_file).exists():
        print(f"Ошибка: файл {osm_file} не найден")
        return False

    handler = OSMHandler(db_file)

    try:
        handler.apply_file(osm_file)
        handler.finalize()
        return True
    except Exception as e:
        print(f"Ошибка при конвертации: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    osm_file = '/data/moscow.osm.pbf'
    db_file = '/data/db/moscow.db'

    if convert_osm_to_sqlite(osm_file, db_file):
        print(f"База данных создана: {db_file}")
        sys.exit(0)
    else:
        print("Ошибка при создании базы данных")
        sys.exit(1)
