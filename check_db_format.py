#!/usr/bin/env python3
"""Проверка формата данных в БД на соответствие требованиям хакатона"""
import sqlite3
import sys

db_path = "/data/db/moscow.db"

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Проверяем структуру таблицы
    print("=" * 80)
    print("СТРУКТУРА ТАБЛИЦЫ buildings")
    print("=" * 80)
    cursor.execute("PRAGMA table_info(buildings)")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]:20s} {col[2]:10s}")

    # Проверяем примеры данных
    print("\n" + "=" * 80)
    print("ПРИМЕРЫ ДАННЫХ (5 записей)")
    print("=" * 80)
    cursor.execute("""
        SELECT city, street, housenumber, full_address
        FROM buildings
        WHERE street IS NOT NULL AND housenumber IS NOT NULL
        LIMIT 5
    """)
    rows = cursor.fetchall()
    for i, row in enumerate(rows, 1):
        print(f"\n{i}. city: {row[0]}")
        print(f"   street: {row[1]}")
        print(f"   housenumber: {row[2]}")
        print(f"   full_address: {row[3]}")

    # Проверка на сокращения в названиях улиц
    print("\n" + "=" * 80)
    print("ПРОВЕРКА НА СОКРАЩЕНИЯ (первые 10 с 'ул.' или 'пер.')")
    print("=" * 80)
    cursor.execute("""
        SELECT DISTINCT street
        FROM buildings
        WHERE street LIKE '%ул.%' OR street LIKE '%пер.%'
           OR street LIKE '%пр.%' OR street LIKE '%наб.%'
        LIMIT 10
    """)
    abbrev_rows = cursor.fetchall()
    if abbrev_rows:
        print("❌ НАЙДЕНЫ СОКРАЩЕНИЯ (требуется исправление):")
        for row in abbrev_rows:
            print(f"  - {row[0]}")
    else:
        print("✅ Сокращений не найдено")

    # Проверка формата full_address
    print("\n" + "=" * 80)
    print("ПРОВЕРКА ФОРМАТА full_address")
    print("=" * 80)
    print("Требование хакатона: '{город}, {улица}, {номер дома} {корпус} {строение}'")
    print("Пример: 'Москва, Дорожная улица, 50 к1 с15'\n")

    cursor.execute("""
        SELECT full_address
        FROM buildings
        WHERE street IS NOT NULL AND housenumber IS NOT NULL
        LIMIT 3
    """)
    addr_rows = cursor.fetchall()
    for row in addr_rows:
        addr = row[0]
        has_commas = ',' in addr
        is_lowercase = addr == addr.lower()

        print(f"Адрес: {addr}")
        print(f"  - Использует запятые: {'✅' if has_commas else '❌'}")
        print(f"  - В нижнем регистре: {'❌ (должен быть с заглавными)' if is_lowercase else '✅'}")
        print()

    # Статистика
    print("=" * 80)
    print("СТАТИСТИКА")
    print("=" * 80)
    cursor.execute("SELECT COUNT(*) FROM buildings")
    total = cursor.fetchone()[0]
    print(f"Всего зданий в БД: {total:,}")

    cursor.execute("SELECT COUNT(*) FROM buildings WHERE street IS NOT NULL")
    with_street = cursor.fetchone()[0]
    print(f"С названием улицы: {with_street:,} ({with_street/total*100:.1f}%)")

    cursor.execute("SELECT COUNT(*) FROM buildings WHERE housenumber IS NOT NULL")
    with_house = cursor.fetchone()[0]
    print(f"С номером дома: {with_house:,} ({with_house/total*100:.1f}%)")

    conn.close()
    print("\n" + "=" * 80)

except Exception as e:
    print(f"❌ ОШИБКА: {e}")
    sys.exit(1)
