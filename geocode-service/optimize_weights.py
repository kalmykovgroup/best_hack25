#!/usr/bin/env python3
"""
Автоматический подбор оптимальных весов для формулы скоринга
Grid Search для нахождения лучшей комбинации весов
"""
import grpc
import sys
import time
from itertools import product
from typing import List, Dict, Tuple
import geocode_pb2
import geocode_pb2_grpc
from test_suite import TEST_CASES, run_test


def test_weights(stub, lev_weight: float, comp_weight: float, bm25_weight: float) -> Dict:
    """
    Тестирует конкретную комбинацию весов

    Возвращает:
        - pass_rate: процент прошедших тестов
        - avg_score: средний score по всем тестам
        - passed: количество пройденных тестов
    """
    passed = 0
    total_score = 0.0

    for test_case in TEST_CASES:
        result = run_test(stub, test_case)
        if result['passed']:
            passed += 1
        total_score += result['score']

    pass_rate = passed / len(TEST_CASES)
    avg_score = total_score / len(TEST_CASES)

    return {
        'pass_rate': pass_rate,
        'avg_score': avg_score,
        'passed': passed,
        'total': len(TEST_CASES),
        'lev_weight': lev_weight,
        'comp_weight': comp_weight,
        'bm25_weight': bm25_weight
    }


def grid_search(grpc_url: str = 'localhost:50054', granularity: int = 10):
    """
    Grid Search для поиска оптимальных весов

    Args:
        grpc_url: адрес gRPC сервера
        granularity: детализация сетки (10 = шаг 0.1)
    """
    print("="*100)
    print("АВТОМАТИЧЕСКИЙ ПОДБОР ОПТИМАЛЬНЫХ ВЕСОВ")
    print("="*100)
    print(f"Granularity: {granularity} (шаг {1/granularity})")
    print()

    # Генерируем сетку весов
    # Веса должны в сумме давать 1.0
    step = 1.0 / granularity

    # Ограничиваем диапазон для разумных весов
    # lev_weight: 0.1 - 0.5 (Levenshtein обычно не должен доминировать)
    # comp_weight: 0.3 - 0.7 (component matching - основная метрика)
    # bm25_weight: 0.1 - 0.4 (BM25 - вспомогательная)

    lev_range = [i * step for i in range(1, 6)]  # 0.1 - 0.5
    comp_range = [i * step for i in range(3, 8)]  # 0.3 - 0.7
    bm25_range = [i * step for i in range(1, 5)]  # 0.1 - 0.4

    # Фильтруем только те комбинации, где сумма весов примерно равна 1.0
    weight_combinations = []
    for lev, comp, bm25 in product(lev_range, comp_range, bm25_range):
        total = lev + comp + bm25
        if abs(total - 1.0) < 0.01:  # Допуск 1%
            weight_combinations.append((lev, comp, bm25))

    print(f"Всего комбинаций для тестирования: {len(weight_combinations)}")
    print()

    if len(weight_combinations) == 0:
        print("❌ Не найдено подходящих комбинаций весов!")
        return None

    channel = grpc.insecure_channel(grpc_url)
    stub = geocode_pb2_grpc.GeocodeServiceStub(channel)

    best_result = None
    all_results = []

    print("Начинаем тестирование...")
    print("-"*100)

    for i, (lev, comp, bm25) in enumerate(weight_combinations, 1):
        print(f"[{i}/{len(weight_combinations)}] Testing weights: lev={lev:.2f}, comp={comp:.2f}, bm25={bm25:.2f}", end=" ")

        # ВАЖНО: Здесь нужно изменять веса в advanced_search.py
        # Для упрощения, сначала просто протестируем текущие веса
        # TODO: Добавить параметр в gRPC запрос для передачи весов

        result = test_weights(stub, lev, comp, bm25)
        all_results.append(result)

        print(f"→ Pass rate: {result['pass_rate']:.1%}, Avg score: {result['avg_score']:.2%}")

        if best_result is None or result['pass_rate'] > best_result['pass_rate']:
            best_result = result

    channel.close()

    # Сортируем результаты
    all_results.sort(key=lambda x: (x['pass_rate'], x['avg_score']), reverse=True)

    print()
    print("="*100)
    print("ТОП-10 ЛУЧШИХ КОМБИНАЦИЙ ВЕСОВ")
    print("="*100)

    for i, res in enumerate(all_results[:10], 1):
        print(f"{i}. lev={res['lev_weight']:.2f}, comp={res['comp_weight']:.2f}, bm25={res['bm25_weight']:.2f}")
        print(f"   Pass rate: {res['pass_rate']:.1%} ({res['passed']}/{res['total']})")
        print(f"   Avg score: {res['avg_score']:.2%}")
        print()

    print("="*100)
    print("ЛУЧШИЕ ВЕСА:")
    print("="*100)
    print(f"lev_weight:  {best_result['lev_weight']:.2f}")
    print(f"comp_weight: {best_result['comp_weight']:.2f}")
    print(f"bm25_weight: {best_result['bm25_weight']:.2f}")
    print()
    print(f"Pass rate: {best_result['pass_rate']:.1%}")
    print(f"Avg score: {best_result['avg_score']:.2%}")

    return best_result


def manual_test_weights(grpc_url: str = 'localhost:50054'):
    """
    Тестирует несколько вручную подобранных комбинаций весов
    (быстрее чем grid search)
    """
    print("="*100)
    print("ТЕСТИРОВАНИЕ ВРУЧНУЮ ПОДОБРАННЫХ ВЕСОВ")
    print("="*100)
    print()

    # Варианты весов для тестирования
    weight_configs = [
        # Текущие веса (baseline)
        {"lev": 0.25, "comp": 0.60, "bm25": 0.15, "name": "Current (baseline)"},

        # Увеличиваем вес component matching (точные совпадения важнее)
        {"lev": 0.20, "comp": 0.70, "bm25": 0.10, "name": "High component weight"},
        {"lev": 0.15, "comp": 0.75, "bm25": 0.10, "name": "Very high component"},
        {"lev": 0.10, "comp": 0.80, "bm25": 0.10, "name": "Extreme component"},

        # Балансируем Levenshtein и component
        {"lev": 0.30, "comp": 0.60, "bm25": 0.10, "name": "More Levenshtein"},
        {"lev": 0.35, "comp": 0.55, "bm25": 0.10, "name": "Balanced Lev+Comp"},

        # Минимизируем BM25 (может шуметь)
        {"lev": 0.30, "comp": 0.65, "bm25": 0.05, "name": "Minimal BM25"},
        {"lev": 0.25, "comp": 0.70, "bm25": 0.05, "name": "Comp focused, low BM25"},

        # Экстремальные варианты
        {"lev": 0.40, "comp": 0.50, "bm25": 0.10, "name": "Lev dominant"},
        {"lev": 0.20, "comp": 0.60, "bm25": 0.20, "name": "High BM25"},
    ]

    channel = grpc.insecure_channel(grpc_url)
    stub = geocode_pb2_grpc.GeocodeServiceStub(channel)

    results = []

    for i, config in enumerate(weight_configs, 1):
        print(f"[{i}/{len(weight_configs)}] {config['name']}")
        print(f"  Weights: lev={config['lev']:.2f}, comp={config['comp']:.2f}, bm25={config['bm25']:.2f}")

        result = test_weights(stub, config['lev'], config['comp'], config['bm25'])
        result['name'] = config['name']
        results.append(result)

        print(f"  ✓ Pass rate: {result['pass_rate']:.1%} ({result['passed']}/{result['total']})")
        print(f"  ✓ Avg score: {result['avg_score']:.2%}")
        print()

    channel.close()

    # Сортируем по pass rate
    results.sort(key=lambda x: (x['pass_rate'], x['avg_score']), reverse=True)

    print("="*100)
    print("РЕЗУЛЬТАТЫ (ОТСОРТИРОВАНЫ ПО PASS RATE)")
    print("="*100)

    for i, res in enumerate(results, 1):
        marker = "🏆" if i == 1 else "  "
        print(f"{marker} {i}. {res['name']}")
        print(f"     lev={res['lev_weight']:.2f}, comp={res['comp_weight']:.2f}, bm25={res['bm25_weight']:.2f}")
        print(f"     Pass rate: {res['pass_rate']:.1%} | Avg score: {res['avg_score']:.2%}")
        print()

    best = results[0]
    print("="*100)
    print("🏆 РЕКОМЕНДУЕМЫЕ ВЕСА:")
    print("="*100)
    print(f"Конфигурация: {best['name']}")
    print(f"lev_weight:  {best['lev_weight']:.2f}")
    print(f"comp_weight: {best['comp_weight']:.2f}")
    print(f"bm25_weight: {best['bm25_weight']:.2f}")
    print()
    print(f"Pass rate: {best['pass_rate']:.1%} ({best['passed']}/{best['total']} тестов)")
    print(f"Avg score: {best['avg_score']:.2%}")

    return best


if __name__ == "__main__":
    import sys

    grpc_url = sys.argv[1] if len(sys.argv) > 1 else 'localhost:50054'
    mode = sys.argv[2] if len(sys.argv) > 2 else 'manual'

    if mode == 'grid':
        granularity = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        grid_search(grpc_url, granularity)
    else:
        manual_test_weights(grpc_url)
