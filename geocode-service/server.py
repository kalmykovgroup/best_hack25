#!/usr/bin/env python3
"""
gRPC Server для геокодирования (хакатон)
Интегрированный режим: использует address-corrector и address-parser
"""
import os
import time
import logging
from concurrent import futures

import grpc
import geocode_pb2
import geocode_pb2_grpc
import address_corrector_pb2
import address_corrector_pb2_grpc
import address_parser_pb2
import address_parser_pb2_grpc

from basic_search import BasicSearchEngine
from advanced_search import AdvancedSearchEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


class GeocodeServicer(geocode_pb2_grpc.GeocodeServiceServicer):
    """Сервис геокодирования для хакатона"""

    def __init__(self, db_path, corrector_url=None, parser_url=None):
        self.db_path = db_path
        self.basic_engine = BasicSearchEngine(db_path)
        self.advanced_engine = AdvancedSearchEngine(db_path)

        # Подключение к внешним сервисам
        self.use_external_services = corrector_url and parser_url

        # Кешируем список городов для парсинга (используется в _simple_parse)
        cursor = self.basic_engine.conn.cursor()
        cursor.execute("SELECT DISTINCT city FROM buildings WHERE city IS NOT NULL AND city != ''")
        self.db_cities = {row[0].lower(): row[0] for row in cursor.fetchall()}
        logger.info("Cached %d cities from database", len(self.db_cities))

        if self.use_external_services:
            logger.info("Initializing with external services: parser=%s (corrector disabled)", parser_url)

            # gRPC канал только для address-parser (corrector отключен из-за низкой производительности)
            self.parser_channel = grpc.insecure_channel(parser_url)
            self.parser_stub = address_parser_pb2_grpc.AddressParserServiceStub(self.parser_channel)

            # address-corrector отключен (слишком медленный для real-time геокодирования)
            self.corrector_stub = None

            logger.info("Geocode service initialized with address-parser (corrector disabled for performance)")
        else:
            logger.warning("External services not configured, using fallback simple parsing")
            logger.info("Geocode service initialized in fallback mode")

    def SearchAddress(self, request, context):
        """Основной метод поиска адреса"""
        start_time = time.time()

        address = request.address.strip()
        limit = request.limit if request.limit > 0 else 10
        algorithm = request.algorithm or "advanced"

        logger.info("SearchAddress: address='%s' algorithm='%s' limit=%d",
                    address, algorithm, limit)

        # Парсинг адреса (без коррекции опечаток)
        components = {}

        # ВАЖНО: address-corrector ОТКЛЮЧЕН для геокодирования (слишком медленный: 700-1000ms)
        # Причина: LIKE "%query%" без индекса сканирует миллионы записей nodes/ways
        # Используем ТОЛЬКО address-parser (libpostal) для парсинга - быстро (18ms)
        # FTS5+BM25 в geocode-service уже находит похожие адреса с нечетким поиском

        # Для коротких запросов (автодополнение) используем простой парсинг
        use_parser = self.use_external_services and self.parser_stub and len(address) >= 3

        if use_parser:
            try:
                # Парсинг адреса через libpostal (БЕЗ коррекции опечаток)
                parser_start = time.time()
                logger.info("Step 1: Calling address-parser for address parsing (corrector disabled)")
                parse_request = address_parser_pb2.ParseAddressRequest(
                    address=address,
                    country="RU",
                    language="ru"
                )
                parse_response = self.parser_stub.ParseAddress(parse_request)
                parser_time_ms = int((time.time() - parser_start) * 1000)

                if parse_response.status.code == address_parser_pb2.OK:
                    parsed_components = parse_response.components
                    components = {
                        'city': parsed_components.city or '',
                        'road': parsed_components.road or '',
                        'house_number': parsed_components.house_number or '',
                        'postcode': parsed_components.postcode or '',
                        'suburb': parsed_components.suburb or ''
                    }
                    logger.info("Address parsed in %d ms: %s", parser_time_ms, components)
                else:
                    logger.warning("Address parsing failed in %d ms: %s", parser_time_ms, parse_response.status.message)
                    # Fallback to simple parsing
                    components = self._simple_parse(address)

            except grpc.RpcError as e:
                logger.error("gRPC error during address parsing: %s", e)
                # Fallback to simple parsing
                components = self._simple_parse(address)
        else:
            # Fallback режим: используем простой парсинг для коротких запросов или если сервисы недоступны
            if len(address) < 3:
                logger.info("Using simple parsing for short query (len=%d): fast autocomplete mode", len(address))
            else:
                logger.info("Using fallback simple parsing (external services not available)")
            components = self._simple_parse(address)

        logger.info("Final components for search: %s", components)

        # Шаг 2: Поиск в БД по выбранному алгоритму
        search_start = time.time()
        if algorithm == "basic":
            results = self.basic_engine.search(components, limit)
        else:
            results = self.advanced_engine.search(components, address, limit)
        search_time_ms = int((time.time() - search_start) * 1000)
        logger.info("Database search completed in %d ms", search_time_ms)

        # Формирование ответа в формате хакатона
        objects = []
        for r in results:
            # Преобразуем tags dict в map<string, string>
            tags_map = {}
            if 'tags' in r and isinstance(r['tags'], dict):
                # Конвертируем все значения в строки
                tags_map = {k: str(v) for k, v in r['tags'].items()}

            obj = geocode_pb2.AddressObject(
                locality=r['locality'],
                street=r['street'],
                number=r['number'],
                lon=r['lon'],
                lat=r['lat'],
                score=r['score'],
                tags=tags_map
            )
            objects.append(obj)

        exec_ms = int((time.time() - start_time) * 1000)

        # Debug info
        normalization_method = "libpostal+fts5" if use_parser else "simple_parse+fts5"
        debug_info = geocode_pb2.DebugInfo(
            corrected_address=address,  # corrector disabled, using original address
            parsed=geocode_pb2.AddressComponents(
                city=components.get('city', ''),
                road=components.get('road', ''),
                house_number=components.get('house_number', ''),
                postcode=components.get('postcode', ''),
                suburb=components.get('suburb', '')
            ),
            normalization_method=normalization_method,
            levenstein_score=results[0].get('lev_score', 0.0) if results else 0.0
        )

        metadata = geocode_pb2.ResponseMetadata(
            execution_time_ms=exec_ms,
            timestamp=int(time.time()),
            algorithm_used=algorithm,
            total_found=len(objects),
            debug_info=debug_info
        )

        response = geocode_pb2.SearchAddressResponse(
            searched_address=address,
            objects=objects,
            metadata=metadata
        )

        logger.info("SearchAddress completed: %d results in %d ms", len(objects), exec_ms)

        return response

    def HealthCheck(self, request, context):
        """Проверка состояния сервиса"""
        # Проверка БД
        try:
            cursor = self.basic_engine.conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM buildings")
            db_size = cursor.fetchone()[0]
            status = "ok"
        except Exception as e:
            logger.error("Database error: %s", e)
            db_size = 0
            status = "error"

        response = geocode_pb2.HealthCheckResponse(
            status=status,
            database_size=db_size,
            corrector_available=False,
            parser_available=False
        )

        logger.info("HealthCheck: status=%s db_size=%d", status, db_size)

        return response

    def _simple_parse(self, address):
        """Простой парсинг адреса с проверкой по БД"""
        # Убираем все специальные символы и приводим к нижнему регистру
        parts = address.lower().replace(',', ' ').replace(':', ' ').replace(';', ' ').split()

        components = {
            'city': '',
            'road': '',
            'house_number': '',
            'postcode': '',
            'suburb': ''
        }

        # Служебные слова для удаления (расширенный список)
        street_prefixes = {
            # Типы улиц
            'улица', 'ул', 'ул.', 'проспект', 'пр-кт', 'пр', 'пр.',
            'переулок', 'пер', 'пер.', 'бульвар', 'б-р', 'бул', 'бул.',
            'набережная', 'наб', 'наб.', 'шоссе', 'ш', 'ш.',
            'площадь', 'пл', 'пл.', 'проезд', 'пр-д', 'тупик', 'туп', 'туп.',
            # Типы домов
            'дом', 'д', 'д.', 'здание', 'зд', 'зд.',
            'строение', 'стр', 'стр.', 'корпус', 'к', 'к.',
            # Служебные слова
            'адрес', 'адрес:', 'address', 'address:',
            'город', 'г', 'г.', 'city',
            # Короткие бессмысленные слова
            'в', 'на', 'по', 'из', 'для', 'от', 'до', 'и', 'a', 'an', 'the'
        }

        # Находим город, номер дома и улицу
        found_city = ''
        found_house = ''
        street_parts = []

        for part in parts:
            # Пропускаем пустые и очень короткие слова
            if len(part) < 2:
                continue

            # Проверяем город (используем кеш)
            if part in self.db_cities:
                found_city = self.db_cities[part]
                continue

            # Проверяем номер дома (цифры с возможными буквами)
            if part.isdigit() or (len(part) > 0 and part[0].isdigit()):
                found_house = part
                continue

            # Пропускаем служебные слова
            if part in street_prefixes:
                continue

            # Пропускаем слова содержащие только спецсимволы
            if not any(c.isalnum() for c in part):
                continue

            # Остальное - часть улицы
            street_parts.append(part)

        components['city'] = found_city
        components['house_number'] = found_house
        components['road'] = ' '.join(street_parts) if street_parts else ''

        return components


def serve():
    """Запуск gRPC сервера"""
    db_path = os.environ.get('DB_PATH', '/app/db/moscow.db')
    corrector_url = os.environ.get('ADDRESS_CORRECTOR_URL')
    parser_url = os.environ.get('ADDRESS_PARSER_URL')

    if not os.path.exists(db_path):
        logger.error("Database not found: %s", db_path)
        logger.error("Please run osm_importer.py first")
        raise FileNotFoundError(f"Database not found: {db_path}")

    logger.info("Starting gRPC server with database: %s", db_path)
    logger.info("Address Corrector URL: %s", corrector_url or "Not configured")
    logger.info("Address Parser URL: %s", parser_url or "Not configured")

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    geocode_pb2_grpc.add_GeocodeServiceServicer_to_server(
        GeocodeServicer(db_path, corrector_url, parser_url), server
    )

    server.add_insecure_port('[::]:50054')
    server.start()

    logger.info("=" * 60)
    logger.info("Geocode gRPC Server is running on port 50054")
    logger.info("=" * 60)

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.stop(0)


if __name__ == "__main__":
    serve()
