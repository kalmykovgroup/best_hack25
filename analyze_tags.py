#!/usr/bin/env python3
"""
Анализ тегов в OSM файле для определения наиболее частых полей
"""
import json
from collections import Counter

# Подключаемся к уже созданной БД
import sqlite3

conn = sqlite3.connect('/data/db/moscow.db')
cursor = conn.cursor()

# Получаем все tags из ways с адресами
cursor.execute("SELECT tags FROM ways WHERE tags LIKE '%addr:street%' LIMIT 10000")

all_keys = Counter()
for row in cursor.fetchall():
    if row[0]:
        tags = json.loads(row[0])
        all_keys.update(tags.keys())

print("=== Топ-30 наиболее частых тегов в зданиях с адресами ===\n")
for key, count in all_keys.most_common(30):
    print(f"{key:40} : {count:6} раз")

conn.close()
