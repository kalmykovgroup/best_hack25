#!/usr/bin/env python3
"""
gRPC сервис для коррекции адресов с использованием libpostal и SQLite базы OSM
Оптимизирован с FTS5 словарями для быстрого поиска (5-15ms вместо 700-1000ms)
"""
import os
import time
import logging
import sqlite3
from concurrent import futures

import grpc
from postal.expand import expand_address
from postal.parser import parse_address

import address_corrector_pb2
import address_corrector_pb2_grpc

# Импорт быстрого корректора на основе FTS5 словарей
from fast_corrector import FastAddressCorrector

# -----------------------------------------------------------------------------
# Basic logging
# -----------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Database helpers
# -----------------------------------------------------------------------------

DB_PATH = os.environ.get("DB_PATH", "/data/db/moscow.db")


def get_db_connection():
    """Получить подключение к SQLite базе данных"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return None


def check_database_health():
    """Проверить здоровье базы данных"""
    conn = get_db_connection()
    if not conn:
        return False, 0

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM nodes")
        count = cursor.fetchone()[0]
        conn.close()
        return True, count
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        if conn:
            conn.close()
        return False, 0


# -----------------------------------------------------------------------------
# Address correction helpers
# -----------------------------------------------------------------------------

def normalize_address_libpostal(address: str, language: str = "ru") -> list:
    """
    Нормализация адреса через libpostal.
    Возвращает список возможных вариантов нормализации.
    """
    try:
        expansions = expand_address(address, languages=[language])
        return expansions if expansions else [address]
    except Exception as e:
        logger.error(f"Libpostal normalization failed: {e}")
        return [address]


def parse_address_components(address: str) -> dict:
    """
    Парсинг адреса на компоненты через libpostal.
    Возвращает словарь с компонентами адреса.
    """
    try:
        parts = parse_address(address)
        components = {}
        for component, label in parts:
            components[label] = component
        return components
    except Exception as e:
        logger.error(f"Address parsing failed: {e}")
        return {}


def search_similar_addresses_DEPRECATED(query: str, limit: int = 10, min_similarity: float = 0.5):
    """
    DEPRECATED: Старый медленный поиск через LIKE "%query%" (700-1000ms)
    Заменен на FastAddressCorrector с FTS5 индексами (5-15ms)
    Оставлен для истории и возможного fallback
    """
    logger.warning("DEPRECATED: Using slow search_similar_addresses (700-1000ms). Use FastAddressCorrector instead!")
    return []


def correct_address(
    original_address: str,
    max_suggestions: int = 5,
    min_similarity: float = 0.6,
    options: dict = None,
    fast_corrector: FastAddressCorrector = None
) -> dict:
    """
    Основная функция коррекции адреса с использованием FTS5 словарей.

    Производительность:
    - Старый подход (LIKE "%query%"): 700-1000 ms
    - Новый подход (FTS5 словари): 5-15 ms

    Возвращает:
    - corrected_address: лучший вариант коррекции
    - suggestions: список альтернативных вариантов
    - was_corrected: был ли адрес исправлен
    """
    if not fast_corrector:
        logger.error("FastAddressCorrector not provided! Cannot correct address.")
        return {
            'corrected_address': original_address,
            'suggestions': [],
            'was_corrected': False,
            'variants_checked': 0
        }

    options = options or {}
    language = options.get('language', 'ru')

    # Парсинг адреса на компоненты через libpostal
    components = parse_address_components(original_address)

    # Получить альтернативные варианты для suggestions
    suggestions = []
    corrected_address = original_address
    was_corrected = False

    # Корректировать город
    city = components.get('city', '').strip()
    if city:
        city_corrections = fast_corrector.correct_city(city, limit=max_suggestions, min_similarity=min_similarity)
        for city_corr in city_corrections:
            suggestions.append({
                'corrected_address': city_corr['city_name'],
                'similarity_score': city_corr['similarity'],
                'components': {'city': city_corr['city_name']},
                'coordinates': {'lat': 0.0, 'lon': 0.0},
                'source': determine_correction_source(city_corr['similarity'])
            })

    # Корректировать улицу
    street = components.get('road', '').strip()
    if street:
        street_corrections = fast_corrector.correct_street(street, limit=max_suggestions, min_similarity=min_similarity)
        for street_corr in street_corrections:
            suggestions.append({
                'corrected_address': street_corr['street_name'],
                'similarity_score': street_corr['similarity'],
                'components': {'road': street_corr['street_name']},
                'coordinates': {'lat': 0.0, 'lon': 0.0},
                'source': determine_correction_source(street_corr['similarity'])
            })

    # Если libpostal не распарсил (нет ни города, ни улицы),
    # пробуем искать весь запрос как улицу И как город
    if not city and not street:
        logger.info(f"LibPostal didn't parse components, trying direct search for: '{original_address}'")

        # Поиск как улица
        street_corrections = fast_corrector.correct_street(original_address, limit=max_suggestions, min_similarity=min_similarity)
        for street_corr in street_corrections:
            suggestions.append({
                'corrected_address': street_corr['street_name'],
                'similarity_score': street_corr['similarity'],
                'components': {'road': street_corr['street_name']},
                'coordinates': {'lat': 0.0, 'lon': 0.0},
                'source': determine_correction_source(street_corr['similarity'])
            })

        # Поиск как город
        city_corrections = fast_corrector.correct_city(original_address, limit=max_suggestions, min_similarity=min_similarity)
        for city_corr in city_corrections:
            suggestions.append({
                'corrected_address': city_corr['city_name'],
                'similarity_score': city_corr['similarity'],
                'components': {'city': city_corr['city_name']},
                'coordinates': {'lat': 0.0, 'lon': 0.0},
                'source': determine_correction_source(city_corr['similarity'])
            })

    # Сортировать по similarity и взять лучшее
    if suggestions:
        suggestions.sort(key=lambda x: x['similarity_score'], reverse=True)
        corrected_address = suggestions[0]['corrected_address']
        was_corrected = corrected_address.lower() != original_address.lower()

    # Ограничить количество suggestions
    suggestions = suggestions[:max_suggestions]

    return {
        'corrected_address': corrected_address,
        'suggestions': suggestions,
        'was_corrected': was_corrected,
        'variants_checked': len(suggestions)
    }


def determine_correction_source(similarity: float):
    """Определить источник коррекции на основе схожести"""
    if similarity >= 0.95:
        return address_corrector_pb2.CorrectionSource.EXACT_MATCH
    elif similarity >= 0.7:
        return address_corrector_pb2.CorrectionSource.FUZZY_MATCH
    elif similarity >= 0.5:
        return address_corrector_pb2.CorrectionSource.SQLITE_DATABASE
    else:
        return address_corrector_pb2.CorrectionSource.LIBPOSTAL_NORMALIZATION


# -----------------------------------------------------------------------------
# gRPC servicer
# -----------------------------------------------------------------------------

class AddressCorrectorServicer(address_corrector_pb2_grpc.AddressCorrectorServiceServicer):
    """
    Сервис коррекции адресов с использованием libpostal и FTS5 словарей.

    Производительность:
    - Старый подход (LIKE "%query%"): 700-1000 ms
    - Новый подход (FTS5 словари): 5-15 ms
    """

    def __init__(self):
        self.start_time = time.time()
        logger.info("AddressCorrectorServicer initializing with FastAddressCorrector...")

        # Инициализация быстрого корректора на основе FTS5 словарей
        try:
            self.fast_corrector = FastAddressCorrector(DB_PATH)
            logger.info("FastAddressCorrector initialized successfully")

            # Статистика словарей
            stats = self.fast_corrector.get_statistics()
            logger.info(f"Dictionaries loaded: {stats['total_streets']} streets, {stats['total_cities']} cities")
        except Exception as e:
            logger.error(f"Failed to initialize FastAddressCorrector: {e}", exc_info=True)
            self.fast_corrector = None

        # Проверка подключения к базе данных
        db_connected, record_count = check_database_health()
        if db_connected:
            logger.info(f"Connected to database: {record_count} nodes")
        else:
            logger.warning("Failed to connect to database")

    def CorrectAddress(self, request, context):
        """Обработка запроса на коррекцию адреса"""
        start_time = time.time()

        original_address = request.original_address.strip()

        if not original_address:
            return address_corrector_pb2.CorrectAddressResponse(
                status=address_corrector_pb2.ResponseStatus(
                    code=address_corrector_pb2.StatusCode.INVALID_REQUEST,
                    message="Original address is empty"
                ),
                original_address="",
                corrected_address="",
                was_corrected=False
            )

        # Параметры коррекции
        max_suggestions = request.max_suggestions if request.max_suggestions > 0 else 5
        min_similarity = request.min_similarity if request.min_similarity > 0 else 0.5

        options = {}
        if request.options:
            options = {
                'language': request.options.language or 'ru',
                'country': request.options.country or 'RU',
                'strict_mode': request.options.strict_mode,
                'enable_normalization': request.options.enable_normalization
            }

        # Выполнение коррекции с использованием FastAddressCorrector
        try:
            result = correct_address(
                original_address,
                max_suggestions,
                min_similarity,
                options,
                fast_corrector=self.fast_corrector
            )

            # Формирование ответа
            suggestions = []
            for sugg in result['suggestions']:
                components = address_corrector_pb2.AddressComponents(
                    house_number=sugg['components'].get('house_number', ''),
                    road=sugg['components'].get('road', ''),
                    unit=sugg['components'].get('unit', ''),
                    postcode=sugg['components'].get('postcode', ''),
                    suburb=sugg['components'].get('suburb', ''),
                    city=sugg['components'].get('city', ''),
                    city_district=sugg['components'].get('city_district', ''),
                    state=sugg['components'].get('state', ''),
                    country=sugg['components'].get('country', '')
                )

                coordinates = address_corrector_pb2.Coordinates(
                    lat=sugg['coordinates']['lat'] or 0.0,
                    lon=sugg['coordinates']['lon'] or 0.0
                )

                suggestion = address_corrector_pb2.CorrectionSuggestion(
                    corrected_address=sugg['corrected_address'],
                    similarity_score=sugg['similarity_score'],
                    components=components,
                    coordinates=coordinates,
                    source=sugg['source']
                )
                suggestions.append(suggestion)

            exec_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"CorrectAddress '{original_address}' -> '{result['corrected_address']}' "
                f"({len(suggestions)} suggestions, {exec_ms}ms)"
            )

            return address_corrector_pb2.CorrectAddressResponse(
                status=address_corrector_pb2.ResponseStatus(
                    code=address_corrector_pb2.StatusCode.OK,
                    message="OK"
                ),
                original_address=original_address,
                corrected_address=result['corrected_address'],
                suggestions=suggestions,
                was_corrected=result['was_corrected'],
                metadata=address_corrector_pb2.ResponseMetadata(
                    execution_time_ms=exec_ms,
                    timestamp=int(time.time()),
                    corrector_version="1.0.0",
                    variants_checked=result['variants_checked']
                )
            )

        except Exception as e:
            logger.error(f"Error during address correction: {e}", exc_info=True)
            return address_corrector_pb2.CorrectAddressResponse(
                status=address_corrector_pb2.ResponseStatus(
                    code=address_corrector_pb2.StatusCode.INTERNAL_ERROR,
                    message="Internal error",
                    details=str(e)
                ),
                original_address=original_address,
                corrected_address=original_address,
                was_corrected=False
            )

    def HealthCheck(self, request, context):
        """Health check для мониторинга"""
        uptime = int(time.time() - self.start_time)

        db_connected, record_count = check_database_health()

        database_status = address_corrector_pb2.DatabaseStatus(
            connected=db_connected,
            total_records=record_count,
            database_path=DB_PATH
        )

        health_status = (
            address_corrector_pb2.HealthStatus.HEALTHY if db_connected
            else address_corrector_pb2.HealthStatus.DEGRADED
        )

        return address_corrector_pb2.HealthCheckResponse(
            status=health_status,
            version="1.0.0",
            uptime_seconds=uptime,
            libpostal_version="1.1.0",
            database_status=database_status
        )


# -----------------------------------------------------------------------------
# Server bootstrap
# -----------------------------------------------------------------------------

def serve():
    """Запуск gRPC сервера"""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
    address_corrector_pb2_grpc.add_AddressCorrectorServiceServicer_to_server(
        AddressCorrectorServicer(), server
    )

    port = os.environ.get("GRPC_PORT", "50053")
    server.add_insecure_port(f"[::]:{port}")
    server.start()

    logger.info(f"gRPC Address Corrector server started on port {port}")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        server.stop(0)


if __name__ == "__main__":
    serve()
