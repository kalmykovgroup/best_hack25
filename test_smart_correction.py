#!/usr/bin/env python3
"""
Тест умной коррекции в geocode-service
Проверяет, что corrector вызывается только при score < 28%
"""
import grpc
import sys
import os

# Add protos to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'geocode-service'))

import geocode_pb2
import geocode_pb2_grpc


def test_geocode(address, expected_corrector_usage=None):
    """Тест геокодирования с проверкой использования corrector"""
    print(f"\n{'='*80}")
    print(f"Testing: '{address}'")
    print('='*80)

    # Подключение к geocode-service
    channel = grpc.insecure_channel('localhost:50054')
    stub = geocode_pb2_grpc.GeocodeServiceStub(channel)

    # Запрос
    request = geocode_pb2.SearchAddressRequest(
        address=address,
        limit=5,
        algorithm="advanced"
    )

    try:
        response = stub.SearchAddress(request)

        # Результаты
        print(f"\nResults found: {response.metadata.total_found}")
        print(f"Execution time: {response.metadata.execution_time_ms} ms")
        print(f"Algorithm: {response.metadata.algorithm_used}")

        # Debug info
        debug = response.metadata.debug_info
        print(f"\nOriginal address: '{response.searched_address}'")
        print(f"Corrected address: '{debug.corrected_address}'")
        print(f"Normalization method: {debug.normalization_method}")

        # Проверка использования corrector
        corrector_used = "corrector+" in debug.normalization_method
        print(f"\n{'🔧 CORRECTOR USED' if corrector_used else '⚡ FAST MODE (no corrector)'}")

        # Топ результаты
        print(f"\nTop results:")
        for i, obj in enumerate(response.objects[:3], 1):
            print(f"{i}. {obj.locality}, {obj.street} {obj.number}")
            print(f"   Score: {obj.score:.2%} | Lat: {obj.lat:.6f}, Lon: {obj.lon:.6f}")

        # Проверка ожиданий
        if expected_corrector_usage is not None:
            if corrector_used == expected_corrector_usage:
                print(f"\n✅ PASS: Corrector usage matches expectation ({expected_corrector_usage})")
            else:
                print(f"\n❌ FAIL: Expected corrector={expected_corrector_usage}, got {corrector_used}")

        # Проверка логики score < 28%
        if response.objects:
            best_score = response.objects[0].score
            print(f"\nBest score: {best_score:.2%}")

            if best_score < 0.28:
                print(f"⚠️  Low score detected! Corrector should have been triggered.")
                if not corrector_used:
                    print("❌ ERROR: Corrector was NOT used despite low score!")
            else:
                print(f"✓ Good score, corrector not needed")

        return response

    except grpc.RpcError as e:
        print(f"❌ gRPC Error: {e.code()}: {e.details()}")
        return None
    finally:
        channel.close()


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SMART TWO-LEVEL CORRECTION TEST")
    print("Testing: corrector is triggered only when initial score < 28%")
    print("="*80)

    # Test 1: Query with typo (should trigger corrector)
    print("\n[TEST 1] Typo query - should trigger corrector")
    test_geocode("орбат", expected_corrector_usage=True)

    # Test 2: Clear query (should NOT trigger corrector)
    print("\n[TEST 2] Clear query - should use fast mode")
    test_geocode("Москва, улица Арбат, 10", expected_corrector_usage=False)

    # Test 3: Another typo
    print("\n[TEST 3] Another typo - should trigger corrector")
    test_geocode("твирская", expected_corrector_usage=True)

    # Test 4: Partial address (may or may not trigger corrector)
    print("\n[TEST 4] Partial address - depends on score")
    test_geocode("Арбат 10")

    print("\n" + "="*80)
    print("TEST COMPLETED")
    print("="*80)
