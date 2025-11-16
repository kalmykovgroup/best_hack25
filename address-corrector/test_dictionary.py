#!/usr/bin/env python3
"""
Тест FTS5 словарей напрямую
"""
import sqlite3

DB_PATH = "/data/db/moscow.db"

def test_dictionaries():
    """Проверка содержимого словарей"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    print("="*60)
    print("ПРОВЕРКА FTS5 СЛОВАРЕЙ")
    print("="*60)

    # Статистика
    cursor.execute("SELECT COUNT(*) as cnt FROM street_dictionary")
    street_count = cursor.fetchone()['cnt']
    print(f"\nУлиц в словаре: {street_count}")

    cursor.execute("SELECT COUNT(*) as cnt FROM city_dictionary")
    city_count = cursor.fetchone()['cnt']
    print(f"Городов в словаре: {city_count}")

    # Примеры улиц
    print("\n" + "="*60)
    print("ПРИМЕРЫ УЛИЦ (первые 20):")
    print("="*60)
    cursor.execute("SELECT street_name, usage_count FROM street_dictionary ORDER BY usage_count DESC LIMIT 20")
    for row in cursor.fetchall():
        print(f"  {row['street_name']:<40} (usage: {row['usage_count']})")

    # Примеры городов
    print("\n" + "="*60)
    print("ПРИМЕРЫ ГОРОДОВ (первые 10):")
    print("="*60)
    cursor.execute("SELECT city_name, usage_count FROM city_dictionary ORDER BY usage_count DESC LIMIT 10")
    for row in cursor.fetchall():
        print(f"  {row['city_name']:<40} (usage: {row['usage_count']})")

    # Поиск улиц начинающихся на "Арбат"
    print("\n" + "="*60)
    print("ПОИСК УЛИЦ начинающихся на 'Арбат' или 'арбат':")
    print("="*60)
    cursor.execute("""
        SELECT street_name, normalized_name, usage_count
        FROM street_dictionary
        WHERE normalized_name LIKE 'арбат%'
        ORDER BY usage_count DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row['street_name']:<40} (normalized: {row['normalized_name']}, usage: {row['usage_count']})")
    else:
        print("  Не найдено!")

    # FTS5 поиск "арбат"
    print("\n" + "="*60)
    print("FTS5 ПОИСК 'арбат*':")
    print("="*60)
    cursor.execute("""
        SELECT
            d.street_name,
            d.normalized_name,
            d.usage_count,
            bm25(street_dictionary_fts) as bm25_score
        FROM street_dictionary d
        JOIN street_dictionary_fts fts ON d.id = fts.rowid
        WHERE street_dictionary_fts MATCH 'арбат*'
        ORDER BY bm25(street_dictionary_fts)
        LIMIT 10
    """)
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row['street_name']:<40} (bm25: {row['bm25_score']:.2f}, usage: {row['usage_count']})")
    else:
        print("  Не найдено!")

    # Поиск с опечаткой "орбат"
    print("\n" + "="*60)
    print("ПОИСК с опечаткой 'орбат' (LIKE):")
    print("="*60)
    cursor.execute("""
        SELECT street_name, normalized_name, usage_count
        FROM street_dictionary
        WHERE normalized_name LIKE '%орбат%'
        LIMIT 5
    """)
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row['street_name']:<40} (normalized: {row['normalized_name']})")
    else:
        print("  Не найдено!")

    # FTS5 поиск "орбат" (должно вернуть пусто, т.к. это опечатка)
    print("\n" + "="*60)
    print("FTS5 ПОИСК 'орбат*':")
    print("="*60)
    cursor.execute("""
        SELECT
            d.street_name,
            d.normalized_name
        FROM street_dictionary d
        JOIN street_dictionary_fts fts ON d.id = fts.rowid
        WHERE street_dictionary_fts MATCH 'орбат*'
        LIMIT 5
    """)
    results = cursor.fetchall()
    if results:
        for row in results:
            print(f"  {row['street_name']}")
    else:
        print("  Не найдено! (ожидаемо для опечатки)")

    conn.close()

if __name__ == "__main__":
    test_dictionaries()
