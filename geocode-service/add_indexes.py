#!/usr/bin/env python3
"""Добавление индексов для ускорения работы SQLite"""
import sqlite3
import os
import time

db_path = os.environ.get('DB_PATH', '/data/db/moscow.db')

print(f"Добавляем индексы в БД: {db_path}")
if not os.path.exists(db_path):
    print(f"❌ БД не найдена: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "=" * 80)
print("ДОБАВЛЕНИЕ ИНДЕКСОВ")
print("=" * 80)

indexes_to_create = [
    ("idx_city", "CREATE INDEX IF NOT EXISTS idx_city ON buildings(city)"),
    ("idx_street", "CREATE INDEX IF NOT EXISTS idx_street ON buildings(street)"),
    ("idx_housenumber", "CREATE INDEX IF NOT EXISTS idx_housenumber ON buildings(housenumber)"),
    ("idx_city_street", "CREATE INDEX IF NOT EXISTS idx_city_street ON buildings(city, street)"),
    ("idx_city_street_house", "CREATE INDEX IF NOT EXISTS idx_city_street_house ON buildings(city, street, housenumber)"),
    ("idx_coordinates", "CREATE INDEX IF NOT EXISTS idx_coordinates ON buildings(lat, lon)"),
]

for idx_name, sql in indexes_to_create:
    print(f"\nСоздание индекса: {idx_name}...")
    start = time.time()
    try:
        cursor.execute(sql)
        conn.commit()
        elapsed = time.time() - start
        print(f"  ✅ Создан за {elapsed:.2f} сек")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}")

print("\n" + "=" * 80)
print("ОПТИМИЗАЦИЯ SQLITE")
print("=" * 80)

# 1. Оптимизация FTS5
print("\n1. Оптимизация FTS5...")
start = time.time()
cursor.execute("INSERT INTO buildings_fts(buildings_fts) VALUES('optimize')")
conn.commit()
elapsed = time.time() - start
print(f"  ✅ Завершено за {elapsed:.2f} сек")

# 2. Обновление статистики для оптимизатора
print("\n2. Обновление статистики (ANALYZE)...")
start = time.time()
cursor.execute("ANALYZE")
conn.commit()
elapsed = time.time() - start
print(f"  ✅ Завершено за {elapsed:.2f} сек")

# 3. WAL режим (Write-Ahead Logging)
print("\n3. Включение WAL режима...")
cursor.execute("PRAGMA journal_mode = WAL")
result = cursor.fetchone()[0]
print(f"  ✅ Режим: {result}")

# 4. Увеличение cache_size
print("\n4. Увеличение cache_size...")
cursor.execute("PRAGMA cache_size = -64000")  # 64MB
cursor.execute("PRAGMA cache_size")
cache_size = cursor.fetchone()[0]
print(f"  ✅ Cache size: {abs(cache_size)} KB ({abs(cache_size)/1024:.1f} MB)")

# 5. Memory-mapped I/O
print("\n5. Включение memory-mapped I/O...")
cursor.execute("PRAGMA mmap_size = 268435456")  # 256MB
cursor.execute("PRAGMA mmap_size")
mmap_size = cursor.fetchone()[0]
print(f"  ✅ MMAP size: {mmap_size / 1024 / 1024:.0f} MB")

# 6. VACUUM для очистки и дефрагментации
print("\n6. VACUUM (дефрагментация БД)...")
db_size_before = os.path.getsize(db_path) / 1024 / 1024
print(f"  Размер до: {db_size_before:.2f} MB")
start = time.time()
cursor.execute("VACUUM")
elapsed = time.time() - start
db_size_after = os.path.getsize(db_path) / 1024 / 1024
print(f"  Размер после: {db_size_after:.2f} MB")
print(f"  Сэкономлено: {db_size_before - db_size_after:.2f} MB")
print(f"  ✅ Завершено за {elapsed:.2f} сек")

print("\n" + "=" * 80)
print("ПРОВЕРКА РЕЗУЛЬТАТОВ")
print("=" * 80)

# Проверяем индексы
cursor.execute("""
    SELECT name, tbl_name
    FROM sqlite_master
    WHERE type = 'index' AND tbl_name = 'buildings'
    ORDER BY name
""")
indexes = cursor.fetchall()
print(f"\nВсего индексов: {len(indexes)}")
for idx in indexes:
    print(f"  - {idx[0]}")

# Проверяем статистику
cursor.execute("SELECT * FROM sqlite_stat1 WHERE tbl = 'buildings' LIMIT 1")
has_stats = cursor.fetchone()
if has_stats:
    print("\n✅ Статистика для оптимизатора обновлена")
else:
    print("\n⚠️  Статистика не создана")

print("\n" + "=" * 80)
print("ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ (ПОСЛЕ ОПТИМИЗАЦИИ)")
print("=" * 80)

test_queries = [
    ("FTS5: 'арбат*'", "SELECT COUNT(*) FROM buildings_fts WHERE buildings_fts MATCH 'арбат*'"),
    ("SQL: city = 'Москва'", "SELECT COUNT(*) FROM buildings WHERE city = 'Москва'"),
    ("SQL: street LIKE 'улица Арбат'", "SELECT COUNT(*) FROM buildings WHERE street = 'улица Арбат'"),
    ("SQL: city + street", "SELECT COUNT(*) FROM buildings WHERE city = 'Москва' AND street = 'улица Арбат'"),
    ("SQL: city + street + house", "SELECT COUNT(*) FROM buildings WHERE city = 'Москва' AND street = 'улица Арбат' AND housenumber = '10'"),
]

for name, query in test_queries:
    start = time.time()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    elapsed_ms = (time.time() - start) * 1000

    # EXPLAIN QUERY PLAN
    cursor.execute(f"EXPLAIN QUERY PLAN {query}")
    plan = cursor.fetchall()
    uses_index = any('INDEX' in str(row[3]) and 'SCAN' not in str(row[3]) for row in plan)

    status = "✅" if uses_index or 'FTS5' in name else "⚠️"
    print(f"\n{status} {name}")
    print(f"  Результатов: {result}")
    print(f"  Время: {elapsed_ms:.2f} ms")
    print(f"  План: {plan[0][3]}")

print("\n" + "=" * 80)
print("ГОТОВО!")
print("=" * 80)

conn.close()
