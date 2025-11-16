#!/usr/bin/env python3
"""
Тест производительности address-corrector с FTS5 словарями
"""
import time
import grpc
import address_corrector_pb2
import address_corrector_pb2_grpc

def test_correction(stub, address, description):
    """Тест коррекции одного адреса"""
    print(f"\n{'='*60}")
    print(f"Тест: {description}")
    print(f"Запрос: '{address}'")
    print(f"{'='*60}")

    start_time = time.time()

    request = address_corrector_pb2.CorrectAddressRequest(
        original_address=address,
        max_suggestions=5,
        min_similarity=0.6,
        options=address_corrector_pb2.CorrectionOptions(
            language="ru",
            country="RU",
            enable_normalization=True
        )
    )

    response = stub.CorrectAddress(request)

    exec_time_ms = int((time.time() - start_time) * 1000)

    print(f"Результат:")
    print(f"  Исправленный адрес: '{response.corrected_address}'")
    print(f"  Был исправлен: {response.was_corrected}")
    print(f"  Время выполнения: {exec_time_ms} ms (client-side)")
    print(f"  Время сервера: {response.metadata.execution_time_ms} ms")
    print(f"  Вариантов проверено: {response.metadata.variants_checked}")

    if response.suggestions:
        print(f"\n  Предложения ({len(response.suggestions)}):")
        for i, sugg in enumerate(response.suggestions[:3], 1):
            print(f"    {i}. '{sugg.corrected_address}' (similarity: {sugg.similarity_score:.2f})")

    return exec_time_ms

def main():
    """Запуск тестов производительности"""
    channel = grpc.insecure_channel('localhost:50053')
    stub = address_corrector_pb2_grpc.AddressCorrectorServiceStub(channel)

    print("="*60)
    print("ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ ADDRESS-CORRECTOR")
    print("="*60)
    print("Цель: 5-15ms (vs старый подход 700-1000ms)")
    print()

    # Тестовые запросы
    test_cases = [
        ("орбат", "Опечатка в слове 'Арбат'"),
        ("москво", "Незавершенное слово 'Москва'"),
        ("твирская", "Опечатка в слове 'Тверская'"),
        ("ленинскй", "Опечатка в слове 'Ленинский'"),
        ("арбатская", "Правильное слово"),
        ("мск тверская", "Город + улица"),
        ("а", "Очень короткий запрос (1 символ)"),
        ("ар", "Короткий запрос (2 символа)"),
        ("неизвестнаяулица", "Несуществующая улица"),
    ]

    times = []

    for address, description in test_cases:
        try:
            exec_time = test_correction(stub, address, description)
            times.append(exec_time)
            time.sleep(0.5)  # Небольшая пауза между запросами
        except grpc.RpcError as e:
            print(f"\n⚠️  gRPC Error: {e.code()}: {e.details()}")
            continue

    # Статистика
    if times:
        print(f"\n{'='*60}")
        print("СТАТИСТИКА ПРОИЗВОДИТЕЛЬНОСТИ")
        print(f"{'='*60}")
        print(f"Всего тестов: {len(times)}")
        print(f"Среднее время: {sum(times) / len(times):.1f} ms")
        print(f"Минимальное время: {min(times)} ms")
        print(f"Максимальное время: {max(times)} ms")

        avg_time = sum(times) / len(times)
        if avg_time < 20:
            print(f"\n✅ ОТЛИЧНО! Среднее время {avg_time:.1f}ms < 20ms")
            print(f"   Улучшение производительности: ~{700 / avg_time:.0f}x быстрее!")
        elif avg_time < 50:
            print(f"\n✓ ХОРОШО! Среднее время {avg_time:.1f}ms < 50ms")
            print(f"  Улучшение производительности: ~{700 / avg_time:.0f}x быстрее!")
        else:
            print(f"\n⚠️ Среднее время {avg_time:.1f}ms > 50ms (может требоваться оптимизация)")

    channel.close()

if __name__ == "__main__":
    main()
