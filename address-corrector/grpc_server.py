#!/usr/bin/env python3
"""
gRPC сервис для коррекции адресов с использованием libpostal и SQLite базы OSM
"""
import os
import time
import logging
import sqlite3
from concurrent import futures
from fuzzywuzzy import fuzz

import grpc
from postal.expand import expand_address
from postal.parser import parse_address

import address_corrector_pb2
import address_corrector_pb2_grpc

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


def search_similar_addresses(query: str, limit: int = 10, min_similarity: float = 0.5):
    """
    Поиск похожих адресов в SQLite базе.
    Использует FTS (Full-Text Search) и fuzzy matching.
    """
    conn = get_db_connection()
    if not conn:
        return []

    try:
        cursor = conn.cursor()

        # Поиск в узлах (nodes) по тегам
        cursor.execute(
            "SELECT id, lat, lon, tags FROM nodes WHERE tags LIKE ? LIMIT ?",
            (f"%{query}%", limit * 2)
        )
        node_rows = cursor.fetchall()

        # Поиск в путях (ways) по тегам
        cursor.execute(
            "SELECT id, tags FROM ways WHERE tags LIKE ? LIMIT ?",
            (f"%{query}%", limit * 2)
        )
        way_rows = cursor.fetchall()

        conn.close()

        # Обработка результатов и подсчет схожести
        results = []

        for row in node_rows:
            import json
            tags = json.loads(row['tags']) if row['tags'] else {}

            # Собираем строку адреса из тегов
            address_parts = []
            for key in ['addr:full', 'addr:street', 'addr:housenumber', 'addr:city', 'name']:
                if key in tags:
                    address_parts.append(tags[key])

            if not address_parts:
                continue

            address_str = ", ".join(address_parts)

            # Вычисляем схожесть
            similarity = fuzz.ratio(query.lower(), address_str.lower()) / 100.0

            if similarity >= min_similarity:
                results.append({
                    'address': address_str,
                    'similarity': similarity,
                    'lat': row['lat'],
                    'lon': row['lon'],
                    'tags': tags,
                    'source': 'nodes'
                })

        for row in way_rows:
            import json
            tags = json.loads(row['tags']) if row['tags'] else {}

            address_parts = []
            for key in ['addr:full', 'addr:street', 'addr:housenumber', 'addr:city', 'name']:
                if key in tags:
                    address_parts.append(tags[key])

            if not address_parts:
                continue

            address_str = ", ".join(address_parts)
            similarity = fuzz.ratio(query.lower(), address_str.lower()) / 100.0

            if similarity >= min_similarity:
                results.append({
                    'address': address_str,
                    'similarity': similarity,
                    'lat': None,
                    'lon': None,
                    'tags': tags,
                    'source': 'ways'
                })

        # Сортировка по убыванию схожести
        results.sort(key=lambda x: x['similarity'], reverse=True)

        return results[:limit]

    except Exception as e:
        logger.error(f"Search failed: {e}")
        if conn:
            conn.close()
        return []


def correct_address(
    original_address: str,
    max_suggestions: int = 5,
    min_similarity: float = 0.5,
    options: dict = None
) -> dict:
    """
    Основная функция коррекции адреса.

    Возвращает:
    - corrected_address: лучший вариант коррекции
    - suggestions: список альтернативных вариантов
    - was_corrected: был ли адрес исправлен
    """
    options = options or {}
    language = options.get('language', 'ru')
    enable_normalization = options.get('enable_normalization', True)

    # Шаг 1: Нормализация через libpostal
    normalized_variants = []
    if enable_normalization:
        normalized_variants = normalize_address_libpostal(original_address, language)
    else:
        normalized_variants = [original_address]

    # Шаг 2: Парсинг адреса на компоненты
    components = parse_address_components(original_address)

    # Шаг 3: Поиск похожих адресов в базе
    all_matches = []
    for variant in normalized_variants[:3]:  # Берем первые 3 варианта нормализации
        matches = search_similar_addresses(variant, max_suggestions, min_similarity)
        all_matches.extend(matches)

    # Убираем дубликаты и сортируем
    unique_matches = {}
    for match in all_matches:
        addr = match['address']
        if addr not in unique_matches or match['similarity'] > unique_matches[addr]['similarity']:
            unique_matches[addr] = match

    sorted_matches = sorted(unique_matches.values(), key=lambda x: x['similarity'], reverse=True)

    # Формируем результат
    suggestions = []
    for match in sorted_matches[:max_suggestions]:
        match_components = parse_address_components(match['address'])

        suggestion = {
            'corrected_address': match['address'],
            'similarity_score': match['similarity'],
            'components': match_components,
            'coordinates': {
                'lat': match.get('lat', 0.0),
                'lon': match.get('lon', 0.0)
            },
            'source': determine_correction_source(match['similarity'])
        }
        suggestions.append(suggestion)

    # Определяем лучший вариант коррекции
    if suggestions:
        best_match = suggestions[0]
        corrected_address = best_match['corrected_address']
        was_corrected = corrected_address.lower() != original_address.lower()
    else:
        # Если ничего не найдено, используем нормализованный вариант
        corrected_address = normalized_variants[0] if normalized_variants else original_address
        was_corrected = corrected_address.lower() != original_address.lower()

    return {
        'corrected_address': corrected_address,
        'suggestions': suggestions,
        'was_corrected': was_corrected,
        'variants_checked': len(normalized_variants) + len(all_matches)
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
    Сервис коррекции адресов с использованием libpostal и SQLite базы OSM.
    """

    def __init__(self):
        self.start_time = time.time()
        logger.info("AddressCorrectorServicer initialized")

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

        # Выполнение коррекции
        try:
            result = correct_address(
                original_address,
                max_suggestions,
                min_similarity,
                options
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
