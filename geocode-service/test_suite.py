#!/usr/bin/env python3
"""
Комплексное тестирование системы геокодирования
Тестовые кейсы от простых к сложным для настройки весов
"""
import grpc
import sys
import geocode_pb2
import geocode_pb2_grpc
from typing import List, Dict, Tuple


class TestCase:
    """Тестовый кейс с ожидаемым результатом"""

    def __init__(self, query: str, expected_street: str, expected_house: str = None,
                 expected_city: str = "Москва", min_score: float = 0.5, description: str = ""):
        self.query = query
        self.expected_street = expected_street
        self.expected_house = expected_house
        self.expected_city = expected_city
        self.min_score = min_score
        self.description = description


# Тестовые наборы от простых к сложным
TEST_CASES = [
    # ===== УРОВЕНЬ 1: ТОЧНЫЕ ЗАПРОСЫ (должны давать 100% или близко) =====
    TestCase(
        query="Москва, улица Арбат, 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.95,
        description="Полный корректный адрес"
    ),
    TestCase(
        query="Москва, Тверская улица, 3",
        expected_street="Тверская улица",
        expected_house="3",
        min_score=0.95,
        description="Полный адрес с порядком слов"
    ),
    TestCase(
        query="Москва, Ленинский проспект, 1",
        expected_street="Ленинский проспект",
        expected_house="1",
        min_score=0.95,
        description="Проспект с номером"
    ),

    # ===== УРОВЕНЬ 2: ЗАПРОСЫ БЕЗ ГОРОДА =====
    TestCase(
        query="улица Арбат, 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.90,
        description="Без города, с номером дома"
    ),
    TestCase(
        query="Тверская улица, 3",
        expected_street="Тверская улица",
        expected_house="3",
        min_score=0.90,
        description="Без города"
    ),

    # ===== УРОВЕНЬ 3: ТОЛЬКО УЛИЦА + ДОМ (БЕЗ СЛОВА 'УЛИЦА') =====
    TestCase(
        query="Арбат 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.85,
        description="Краткая форма: улица + номер"
    ),
    TestCase(
        query="Тверская 3",
        expected_street="Тверская улица",
        expected_house="3",
        min_score=0.85,
        description="Краткая форма: название + номер"
    ),
    TestCase(
        query="Ленинский 1",
        expected_street="Ленинский проспект",
        expected_house="1",
        min_score=0.80,
        description="Проспект в краткой форме"
    ),

    # ===== УРОВЕНЬ 4: ОПЕЧАТКИ В НАЗВАНИИ УЛИЦЫ =====
    TestCase(
        query="арбат 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.80,
        description="Опечатка: строчные буквы"
    ),
    TestCase(
        query="орбат 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.75,
        description="Опечатка: о вместо а"
    ),
    TestCase(
        query="арбят 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.75,
        description="Опечатка: я вместо а"
    ),
    TestCase(
        query="твирская 3",
        expected_street="Тверская улица",
        expected_house="3",
        min_score=0.75,
        description="Опечатка: и вместо е"
    ),
    TestCase(
        query="ленинскй 1",
        expected_street="Ленинский проспект",
        expected_house="1",
        min_score=0.75,
        description="Опечатка: пропущена гласная"
    ),

    # ===== УРОВЕНЬ 5: ТОЛЬКО НАЗВАНИЕ УЛИЦЫ (БЕЗ НОМЕРА) =====
    TestCase(
        query="Арбат",
        expected_street="улица Арбат",
        expected_house=None,
        min_score=0.70,
        description="Только название улицы"
    ),
    TestCase(
        query="Тверская",
        expected_street="Тверская улица",
        expected_house=None,
        min_score=0.70,
        description="Только название"
    ),

    # ===== УРОВЕНЬ 6: СЛОЖНЫЕ ОПЕЧАТКИ =====
    TestCase(
        query="орбят 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.65,
        description="Две опечатки: о вместо а, я вместо а"
    ),
    TestCase(
        query="арботская 10",
        expected_street="Арбатская улица",
        expected_house="10",
        min_score=0.65,
        description="Опечатка в длинном названии"
    ),

    # ===== УРОВЕНЬ 7: АЛЬТЕРНАТИВНЫЕ НАПИСАНИЯ =====
    TestCase(
        query="Москва улица Арбат дом 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.85,
        description="Вербозный запрос со словом 'дом'"
    ),
    TestCase(
        query="Арбат д 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.80,
        description="С сокращением 'д'"
    ),
    TestCase(
        query="Арбат д. 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.80,
        description="С сокращением 'д.'"
    ),

    # ===== УРОВЕНЬ 8: ЧАСТИЧНЫЕ СОВПАДЕНИЯ =====
    TestCase(
        query="Арб 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.60,
        description="Сокращенное название"
    ),
    TestCase(
        query="Тве 3",
        expected_street="Тверская улица",
        expected_house="3",
        min_score=0.60,
        description="Очень короткое название"
    ),

    # ===== УРОВЕНЬ 9: ТРАНСЛИТ И ЛАТИНИЦА =====
    TestCase(
        query="arbat 10",
        expected_street="улица Арбат",
        expected_house="10",
        min_score=0.50,
        description="Латиница транслит"
    ),
]


def run_test(stub, test_case: TestCase, algorithm: str = "advanced") -> Dict:
    """Запуск одного теста"""
    request = geocode_pb2.SearchAddressRequest(
        address=test_case.query,
        limit=5,
        algorithm=algorithm
    )

    try:
        response = stub.SearchAddress(request)

        if not response.objects:
            return {
                'passed': False,
                'reason': 'No results',
                'score': 0.0,
                'actual_address': 'N/A'
            }

        top_result = response.objects[0]

        # Проверка совпадения улицы (нормализованное сравнение)
        actual_street = top_result.street.lower().strip()
        expected_street = test_case.expected_street.lower().strip()

        street_match = expected_street in actual_street or actual_street in expected_street

        # Проверка номера дома (если указан)
        house_match = True
        if test_case.expected_house:
            actual_house = top_result.number.strip()
            expected_house = test_case.expected_house.strip()
            house_match = actual_house == expected_house

        # Проверка минимального score
        score_ok = top_result.score >= test_case.min_score

        passed = street_match and house_match and score_ok

        reason = []
        if not street_match:
            reason.append(f"Street mismatch: expected '{test_case.expected_street}', got '{top_result.street}'")
        if not house_match:
            reason.append(f"House mismatch: expected '{test_case.expected_house}', got '{top_result.number}'")
        if not score_ok:
            reason.append(f"Low score: {top_result.score:.2%} < {test_case.min_score:.2%}")

        return {
            'passed': passed,
            'reason': ' | '.join(reason) if reason else 'OK',
            'score': top_result.score,
            'actual_address': f"{top_result.locality}, {top_result.street} {top_result.number}".strip()
        }

    except grpc.RpcError as e:
        return {
            'passed': False,
            'reason': f'gRPC Error: {e.code()}',
            'score': 0.0,
            'actual_address': 'ERROR'
        }


def run_test_suite(grpc_url: str = 'localhost:50054'):
    """Запуск всего набора тестов"""
    print("="*100)
    print("КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ СИСТЕМЫ ГЕОКОДИРОВАНИЯ")
    print("="*100)
    print()

    channel = grpc.insecure_channel(grpc_url)
    stub = geocode_pb2_grpc.GeocodeServiceStub(channel)

    total_tests = len(TEST_CASES)
    passed_tests = 0
    failed_tests = []

    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"[{i}/{total_tests}] {test_case.description}")
        print(f"  Query: '{test_case.query}'")
        print(f"  Expected: {test_case.expected_city}, {test_case.expected_street}", end="")
        if test_case.expected_house:
            print(f" {test_case.expected_house}", end="")
        print(f" (min_score: {test_case.min_score:.0%})")

        result = run_test(stub, test_case)

        if result['passed']:
            print(f"  ✅ PASS - Score: {result['score']:.2%}")
            print(f"  Actual: {result['actual_address']}")
            passed_tests += 1
        else:
            print(f"  ❌ FAIL - Score: {result['score']:.2%}")
            print(f"  Actual: {result['actual_address']}")
            print(f"  Reason: {result['reason']}")
            failed_tests.append({
                'test_case': test_case,
                'result': result
            })

        print()

    channel.close()

    # Итоговая статистика
    print("="*100)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("="*100)
    print(f"Всего тестов: {total_tests}")
    print(f"✅ Passed: {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"❌ Failed: {len(failed_tests)} ({len(failed_tests)/total_tests*100:.1f}%)")
    print()

    if failed_tests:
        print("ПРОВАЛИВШИЕСЯ ТЕСТЫ:")
        print("-"*100)
        for i, fail in enumerate(failed_tests, 1):
            tc = fail['test_case']
            res = fail['result']
            print(f"{i}. Query: '{tc.query}' - {tc.description}")
            print(f"   Expected: {tc.expected_street} {tc.expected_house or ''}")
            print(f"   Actual: {res['actual_address']}")
            print(f"   Score: {res['score']:.2%} (min: {tc.min_score:.2%})")
            print(f"   Reason: {res['reason']}")
            print()

    return {
        'total': total_tests,
        'passed': passed_tests,
        'failed': len(failed_tests),
        'pass_rate': passed_tests / total_tests,
        'failed_tests': failed_tests
    }


if __name__ == "__main__":
    import sys
    grpc_url = sys.argv[1] if len(sys.argv) > 1 else 'localhost:50054'
    results = run_test_suite(grpc_url)

    # Exit code: 0 если все тесты прошли, 1 если есть провалы
    sys.exit(0 if results['failed'] == 0 else 1)
