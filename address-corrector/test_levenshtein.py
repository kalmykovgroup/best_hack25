#!/usr/bin/env python3
"""
Тест Levenshtein similarity для проверки порогов
"""
import Levenshtein

test_pairs = [
    ("орбат", "арбат"),
    ("орбат", "улица арбат"),
    ("твирская", "тверская"),
    ("твирская", "тверская улица"),
    ("ленинскй", "ленинский"),
    ("ленинскй", "ленинский проспект"),
    ("москво", "москва"),
    ("арбатская", "арбатецкая улица"),
    ("арбатская", "арбатская площадь"),
]

print("="*60)
print("ТЕСТ LEVENSHTEIN SIMILARITY")
print("="*60)
print()

for query, target in test_pairs:
    distance = Levenshtein.distance(query.lower(), target.lower())
    max_len = max(len(query), len(target), 1)
    similarity = 1.0 - (distance / max_len)

    status = "✓" if similarity >= 0.6 else "✗"

    print(f"{status} '{query}' → '{target}'")
    print(f"   Distance: {distance}, Similarity: {similarity:.2f}")
    if similarity < 0.6:
        print(f"   ⚠️  Below threshold 0.6!")
    print()
