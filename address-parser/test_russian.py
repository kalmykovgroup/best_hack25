#!/usr/bin/env python3
"""
Тест Address Parser с русскими адресами
"""

import grpc
import sys
sys.path.insert(0, './generated')

import address_parser_pb2
import address_parser_pb2_grpc

def test_parse_address(stub, address, country='RU'):
    """Тест парсинга адреса"""
    print(f"\n{'='*80}")
    print(f"Тест парсинга: {address}")
    print(f"{'='*80}")

    request = address_parser_pb2.ParseAddressRequest(
        address=address,
        country=country,
        language='ru'
    )

    response = stub.ParseAddress(request)

    status_name = address_parser_pb2.StatusCode.Name(response.status.code)
    print(f"\nСтатус: {status_name} - {response.status.message}")
    print(f"Оригинал: {response.original_address}")
    print(f"\nКомпоненты:")

    components = response.components
    if components.house_number:
        print(f"  Номер дома: {components.house_number}")
    if components.road:
        print(f"  Улица: {components.road}")
    if components.city:
        print(f"  Город: {components.city}")
    if components.state:
        print(f"  Область/Регион: {components.state}")
    if components.country:
        print(f"  Страна: {components.country}")
    if components.postcode:
        print(f"  Индекс: {components.postcode}")
    if components.unit:
        print(f"  Квартира: {components.unit}")
    if components.suburb:
        print(f"  Район: {components.suburb}")
    if components.city_district:
        print(f"  Район города: {components.city_district}")

    print(f"\nВремя выполнения: {response.metadata.execution_time_ms:.2f} ms")

    return response

def test_normalize_address(stub, address):
    """Тест нормализации адреса"""
    print(f"\n{'='*80}")
    print(f"Тест нормализации: {address}")
    print(f"{'='*80}")

    request = address_parser_pb2.NormalizeAddressRequest(
        address=address,
        options=address_parser_pb2.NormalizeOptions(
            transliterate=False,
            lowercase=True,
            strip_punctuation=False
        )
    )

    response = stub.NormalizeAddress(request)

    status_name = address_parser_pb2.StatusCode.Name(response.status.code)
    print(f"\nСтатус: {status_name} - {response.status.message}")
    print(f"Оригинал: {response.original_address}")
    print(f"\nВарианты нормализации ({len(response.expansions)}):")
    for i, variant in enumerate(response.expansions[:10], 1):
        print(f"  {i}. {variant}")

    print(f"\nВремя выполнения: {response.metadata.execution_time_ms:.2f} ms")

    return response

def main():
    # Подключение к серверу
    channel = grpc.insecure_channel('localhost:50052')
    stub = address_parser_pb2_grpc.AddressParserServiceStub(channel)

    # Тестовые адреса
    test_addresses = [
        # Полный адрес с квартирой
        "Россия, Москва, ул. Тверская, д. 10, кв. 5",

        # Адрес без квартиры
        "Санкт-Петербург, Невский проспект, дом 28",

        # Адрес с областью
        "Московская область, г. Мытищи, ул. Мира, д. 12",

        # Короткий адрес
        "Москва, Ленинский проспект, 15",

        # Адрес с корпусом
        "Москва, ул. Арбат, д. 5, корп. 2",

        # Адрес с индексом
        "119019, Москва, ул. Новый Арбат, 10",

        # Реальный адрес с ошибками
        "г Москва ул Тверская д 10 кв 5",

        # Адрес латиницей (транслитерация)
        "Moskva, ul. Tverskaya, d. 10",
    ]

    for address in test_addresses:
        try:
            # Парсинг
            test_parse_address(stub, address)

            # Нормализация
            test_normalize_address(stub, address)

        except grpc.RpcError as e:
            print(f"\n❌ Ошибка gRPC: {e.code()}: {e.details()}")
        except Exception as e:
            print(f"\n❌ Ошибка: {type(e).__name__}: {e}")

    print(f"\n{'='*80}")
    print("Тесты завершены")
    print(f"{'='*80}\n")

if __name__ == '__main__':
    main()
