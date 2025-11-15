"""
Тестовый Python gRPC сервис для геокодирования
Обновлено под новую структуру API
"""
import logging
import time
from concurrent import futures
import sys
import io
import grpc
import geocode_pb2
import geocode_pb2_grpc

# Исправляем кодировку для Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GeocodeServicer(geocode_pb2_grpc.GeocodeServiceServicer):
    """
    Реализация gRPC сервиса геокодирования
    """

    def __init__(self):
        self.start_time = time.time()
        # Тестовые данные (в реальной версии будет база данных)
        self.mock_data = [
            {
                "locality": "Москва",
                "street": "Тверская улица",
                "number": "7",
                "lon": 37.615560,
                "lat": 55.757814,
                "score": 0.95,
                "postal_code": "125009",
                "district": "Тверской район",
                "full_address": "Москва, Тверская улица, 7"
            },
            {
                "locality": "Москва",
                "street": "Красная площадь",
                "number": "1",
                "lon": 37.621211,
                "lat": 55.753544,
                "score": 0.98,
                "postal_code": "109012",
                "district": "Тверской район",
                "full_address": "Москва, Красная площадь, 1"
            },
            {
                "locality": "Москва",
                "street": "проспект Мира",
                "number": "119",
                "lon": 37.639600,
                "lat": 55.822144,
                "score": 0.92,
                "postal_code": "129223",
                "district": "Останкинский район",
                "full_address": "Москва, проспект Мира, 119"
            },
            {
                "locality": "Санкт-Петербург",
                "street": "Невский проспект",
                "number": "28",
                "lon": 30.324116,
                "lat": 59.935493,
                "score": 0.90,
                "postal_code": "191186",
                "district": "Центральный район",
                "full_address": "Санкт-Петербург, Невский проспект, 28"
            },
            {
                "locality": "Москва",
                "street": "улица Арбат",
                "number": "10",
                "lon": 37.593434,
                "lat": 55.750446,
                "score": 0.88,
                "postal_code": "119019",
                "district": "Арбат",
                "full_address": "Москва, улица Арбат, 10"
            },
        ]

    def SearchAddress(self, request, context):
        """
        Обработка запроса на поиск адреса
        """
        start_time = time.time()

        # Детальное логирование входящего запроса
        logger.info("=" * 80)
        logger.info(f"📨 ВХОДЯЩИЙ ЗАПРОС [request_id={request.request_id}]")
        logger.info("-" * 80)
        logger.info(f"🔤 Оригинальный запрос:     '{request.original_query}'")
        logger.info(f"✨ Нормализованный запрос:  '{request.normalized_query}'")
        logger.info(f"📊 Лимит результатов:       {request.limit}")

        # Логирование опций поиска
        if request.options:
            logger.info(f"⚙️  Опции поиска:")
            logger.info(f"   • min_score_threshold:  {request.options.min_score_threshold}")
            logger.info(f"   • enable_fuzzy_search:  {request.options.enable_fuzzy_search}")
            if request.options.locality_filter:
                logger.info(f"   • locality_filter:      '{request.options.locality_filter}'")

        # Логирование структурированных компонентов адреса
        if request.parsed_components:
            components = request.parsed_components
            logger.info(f"🏗️  Структурированные компоненты (libpostal):")

            # Основные компоненты
            if components.city:
                logger.info(f"   • Город:                '{components.city}'")
            if components.road:
                logger.info(f"   • Улица:                '{components.road}'")
            if components.house_number:
                logger.info(f"   • Номер дома:           '{components.house_number}'")

            # Дополнительные компоненты
            if components.unit:
                logger.info(f"   • Квартира/Офис:        '{components.unit}'")
            if components.level:
                logger.info(f"   • Этаж:                 '{components.level}'")
            if components.staircase:
                logger.info(f"   • Подъезд:              '{components.staircase}'")
            if components.entrance:
                logger.info(f"   • Вход:                 '{components.entrance}'")

            # Административные компоненты
            if components.suburb:
                logger.info(f"   • Район/Микрорайон:     '{components.suburb}'")
            if components.city_district:
                logger.info(f"   • Округ города:         '{components.city_district}'")
            if components.state:
                logger.info(f"   • Регион/Область:       '{components.state}'")
            if components.country:
                logger.info(f"   • Страна:               '{components.country}'")

            # Почтовый индекс
            if components.postcode:
                logger.info(f"   • Почтовый индекс:      '{components.postcode}'")
        else:
            logger.info(f"⚠️  Структурированные компоненты отсутствуют (fallback на строковый поиск)")

        logger.info("=" * 80)

        try:
            # Логика поиска с использованием структурированных компонентов
            components = request.parsed_components
            query_lower = request.normalized_query.lower()
            original_lower = request.original_query.lower() if request.original_query else query_lower
            results = []

            # Извлекаем компоненты адреса для более точного поиска
            search_city = components.city.lower() if components and components.city else ""
            search_road = components.road.lower() if components and components.road else ""
            search_house = components.house_number.lower() if components and components.house_number else ""

            logger.debug(
                f"Поиск по компонентам: city='{search_city}', road='{search_road}', house='{search_house}'"
            )

            for item in self.mock_data:
                # Приоритет 1: Поиск по структурированным компонентам (если есть)
                if components and (search_city or search_road or search_house):
                    # Точное совпадение по компонентам дает высокий score
                    city_match = search_city and search_city in item["locality"].lower()
                    road_match = search_road and search_road in item["street"].lower()
                    house_match = search_house and search_house in item["number"].lower()

                    if city_match or road_match or house_match:
                        # Повышаем score при совпадении компонентов
                        adjusted_score = item["score"]
                        if city_match and road_match and house_match:
                            adjusted_score = min(1.0, item["score"] + 0.1)  # Все 3 компонента
                        elif (city_match and road_match) or (city_match and house_match):
                            adjusted_score = min(1.0, item["score"] + 0.05)  # 2 компонента

                        # Создаем дополнительную информацию
                        additional_info = geocode_pb2.AdditionalInfo(
                            postal_code=item.get("postal_code", ""),
                            district=item.get("district", ""),
                            full_address=item["full_address"],
                            object_id=f"obj_{len(results) + 1}"
                        )

                        # Создаем адресный объект
                        address_object = geocode_pb2.AddressObject(
                            locality=item["locality"],
                            street=item["street"],
                            number=item["number"],
                            lon=item["lon"],
                            lat=item["lat"],
                            score=adjusted_score,
                            additional_info=additional_info
                        )

                        results.append(address_object)
                        continue

                # Приоритет 2: Fallback на поиск по строкам (если компоненты не дали результатов)
                if (query_lower in item["locality"].lower() or
                    query_lower in item["street"].lower() or
                    query_lower in item["full_address"].lower() or
                    original_lower in item["locality"].lower() or
                    original_lower in item["street"].lower() or
                    original_lower in item["full_address"].lower()):

                    # Создаем дополнительную информацию
                    additional_info = geocode_pb2.AdditionalInfo(
                        postal_code=item.get("postal_code", ""),
                        district=item.get("district", ""),
                        full_address=item["full_address"],
                        object_id=f"obj_{len(results) + 1}"
                    )

                    # Создаем адресный объект
                    address_object = geocode_pb2.AddressObject(
                        locality=item["locality"],
                        street=item["street"],
                        number=item["number"],
                        lon=item["lon"],
                        lat=item["lat"],
                        score=item["score"],
                        additional_info=additional_info
                    )

                    results.append(address_object)

            # Сортируем по релевантности
            results.sort(key=lambda x: x.score, reverse=True)

            # Применяем фильтр по минимальному score (если указан)
            if request.options and request.options.min_score_threshold > 0:
                results = [r for r in results if r.score >= request.options.min_score_threshold]

            # Ограничиваем количество результатов
            if request.limit > 0:
                results = results[:request.limit]

            execution_time_ms = int((time.time() - start_time) * 1000)

            # Детальное логирование результатов
            logger.info("-" * 80)
            logger.info(f"✅ РЕЗУЛЬТАТЫ ПОИСКА [request_id={request.request_id}]")
            logger.info(f"   • Найдено результатов:  {len(results)}")
            logger.info(f"   • Время выполнения:     {execution_time_ms}ms")

            if results:
                logger.info(f"   • Топ результатов:")
                for idx, result in enumerate(results[:3], 1):  # Показываем топ-3
                    logger.info(
                        f"     {idx}. {result.locality}, {result.street}, {result.number} "
                        f"(score: {result.score:.2f})"
                    )
            else:
                logger.warning(f"   ⚠️ Ничего не найдено!")

            logger.info("=" * 80)

            # Возвращаем ответ (searched_address содержит нормализованный запрос)
            return geocode_pb2.SearchAddressResponse(
                status=geocode_pb2.ResponseStatus(
                    code=geocode_pb2.StatusCode.OK,
                    message="Поиск выполнен успешно"
                ),
                searched_address=request.normalized_query,
                objects=results,
                total_found=len(results),
                metadata=geocode_pb2.ResponseMetadata(
                    execution_time_ms=execution_time_ms,
                    timestamp=int(time.time()),
                    engine_version="1.0.0-mock"
                )
            )

        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ ОШИБКА ПРИ ОБРАБОТКЕ ЗАПРОСА [request_id={request.request_id}]")
            logger.error(f"   • Тип ошибки: {type(e).__name__}")
            logger.error(f"   • Сообщение:  {str(e)}")
            logger.error("=" * 80, exc_info=True)
            return geocode_pb2.SearchAddressResponse(
                status=geocode_pb2.ResponseStatus(
                    code=geocode_pb2.StatusCode.INTERNAL_ERROR,
                    message=f"Внутренняя ошибка сервера",
                    details=str(e)
                ),
                searched_address=request.normalized_query,
                objects=[],
                total_found=0
            )

    def HealthCheck(self, request, context):
        """
        Health check для мониторинга
        """
        uptime = int(time.time() - self.start_time)

        return geocode_pb2.HealthCheckResponse(
            status=geocode_pb2.HealthStatus.HEALTHY,
            version="1.0.0",
            uptime_seconds=uptime
        )


def serve():
    """
    Запуск gRPC сервера
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    geocode_pb2_grpc.add_GeocodeServiceServicer_to_server(
        GeocodeServicer(), server
    )

    # Слушаем на порту 50051
    server.add_insecure_port('[::]:50051')
    server.start()

    logger.info("✅ Python gRPC сервер запущен на порту 50051")
    logger.info("📡 Endpoints:")
    logger.info("   - SearchAddress (поиск адресов)")
    logger.info("   - HealthCheck (проверка здоровья)")
    logger.info("Ожидание запросов...")

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Остановка сервера...")
        server.stop(0)


if __name__ == '__main__':
    serve()
