#!/usr/bin/env python3
"""Анализ производительности SQLite и индексов"""
import sqlite3
import os
import time

db_path = os.environ.get('DB_PATH', '/data/db/moscow.db')

print(f"Анализируем БД: {db_path}")
if not os.path.exists(db_path):
    print(f"❌ БД не найдена: {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n" + "=" * 80)
print("1. ТЕКУЩИЕ ИНДЕКСЫ")
print("=" * 80)
cursor.execute("""
    SELECT name, tbl_name, sql
    FROM sqlite_master
    WHERE type = 'index' AND tbl_name = 'buildings'
    ORDER BY name
""")
indexes = cursor.fetchall()
if indexes:
    for idx in indexes:
        print(f"\nИндекс: {idx[0]}")
        print(f"  Таблица: {idx[1]}")
        if idx[2]:
            print(f"  SQL: {idx[2]}")
else:
    print("❌ НЕТ ИНДЕКСОВ!")

print("\n" + "=" * 80)
print("2. СТАТИСТИКА БД")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM buildings")
total = cursor.fetchone()[0]
print(f"Всего записей: {total:,}")

# Размер БД
db_size_mb = os.path.getsize(db_path) / 1024 / 1024
print(f"Размер БД: {db_size_mb:.2f} MB")

# Статистика по полям
cursor.execute("SELECT COUNT(DISTINCT city) FROM buildings")
print(f"Уникальных городов: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(DISTINCT street) FROM buildings")
print(f"Уникальных улиц: {cursor.fetchone()[0]}")

print("\n" + "=" * 80)
print("3. АНАЛИЗ ПРОИЗВОДИТЕЛЬНОСТИ ЗАПРОСОВ")
print("=" * 80)

# Тест 1: Поиск по FTS5 (основной запрос advanced_search)
test_queries = [
    ("FTS5: 'арбат*'", "SELECT COUNT(*) FROM buildings_fts WHERE buildings_fts MATCH 'арбат*'"),
    ("FTS5: 'арбат* 10*'", "SELECT COUNT(*) FROM buildings_fts WHERE buildings_fts MATCH 'арбат* 10*'"),
    ("SQL: city = 'Москва'", "SELECT COUNT(*) FROM buildings WHERE city = 'Москва'"),
    ("SQL: street LIKE '%Арбат%'", "SELECT COUNT(*) FROM buildings WHERE street LIKE '%Арбат%'"),
    ("SQL: city + street", "SELECT COUNT(*) FROM buildings WHERE city = 'Москва' AND street = 'улица Арбат'"),
]

for name, query in test_queries:
    start = time.time()
    cursor.execute(query)
    result = cursor.fetchone()[0]
    elapsed_ms = (time.time() - start) * 1000
    print(f"\n{name}")
    print(f"  Результатов: {result}")
    print(f"  Время: {elapsed_ms:.2f} ms")

    # EXPLAIN QUERY PLAN
    cursor.execute(f"EXPLAIN QUERY PLAN {query}")
    plan = cursor.fetchall()
    print(f"  План:")
    for row in plan:
        print(f"    {row[3]}")

print("\n" + "=" * 80)
print("4. АНАЛИЗ FTS5")
print("=" * 80)
cursor.execute("SELECT COUNT(*) FROM buildings_fts")
fts_count = cursor.fetchone()[0]
print(f"Записей в FTS5: {fts_count:,}")

# Проверяем что FTS5 синхронизирован с buildings
if fts_count != total:
    print(f"⚠️  ВНИМАНИЕ: FTS5 не синхронизирован!")
    print(f"  buildings: {total:,}, buildings_fts: {fts_count:,}")
else:
    print("✅ FTS5 синхронизирован")

print("\n" + "=" * 80)
print("5. РЕКОМЕНДАЦИИ ПО ОПТИМИЗАЦИИ")
print("=" * 80)

recommendations = []

# Проверяем наличие составных индексов
has_city_street_idx = any('city' in str(idx[2]) and 'street' in str(idx[2]) for idx in indexes if idx[2])
if not has_city_street_idx:
    recommendations.append("❌ Отсутствует составной индекс (city, street)")

# Проверяем индекс на housenumber
has_housenumber_idx = any('housenumber' in str(idx[2]) for idx in indexes if idx[2])
if not has_housenumber_idx:
    recommendations.append("❌ Отсутствует индекс на housenumber")

# Проверяем ANALYZE
cursor.execute("SELECT * FROM sqlite_stat1 WHERE tbl = 'buildings' LIMIT 1")
has_stats = cursor.fetchone()
if not has_stats:
    recommendations.append("❌ Не выполнен ANALYZE (нет статистики для оптимизатора)")

if recommendations:
    print("\nНайдены проблемы:")
    for rec in recommendations:
        print(f"  {rec}")
else:
    print("✅ Все основные оптимизации применены")

print("\n" + "=" * 80)
print("6. ПРЕДЛОЖЕНИЯ ПО УСКОРЕНИЮ")
print("=" * 80)
print("""
1. Составной индекс для поиска по городу + улице:
   CREATE INDEX idx_city_street ON buildings(city, street);

2. Индекс на housenumber для фильтрации:
   CREATE INDEX idx_housenumber ON buildings(housenumber);

3. Составной индекс для полного адреса:
   CREATE INDEX idx_city_street_house ON buildings(city, street, housenumber);

4. Обновить статистику для оптимизатора:
   ANALYZE;

5. Оптимизировать FTS5:
   INSERT INTO buildings_fts(buildings_fts) VALUES('optimize');

6. Включить WAL режим для параллельного доступа:
   PRAGMA journal_mode = WAL;

7. Увеличить cache_size (по умолчанию ~2MB):
   PRAGMA cache_size = -64000;  -- 64MB

8. Включить memory-mapped I/O:
   PRAGMA mmap_size = 268435456;  -- 256MB
""")

print("\n" + "=" * 80)

conn.close()
