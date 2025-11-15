"""
gRPC сервер для парсинга адресов с использованием libpostal
"""
import grpc
from concurrent import futures
import time
import logging
from typing import List, Dict
import postal.parser
import postal.expand
import address_parser_pb2
import address_parser_pb2_grpc

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Версия сервиса
SERVICE_VERSION = "1.0.0"

# Время запуска сервиса
START_TIME = time.time()


class AddressParserServicer(address_parser_pb2_grpc.AddressParserServiceServicer):
    """
    Реализация gRPC сервиса парсинга адресов
    """

    def ParseAddress(self, request, context):
        """
        Парсит адрес на компоненты с использованием libpostal
        """
        start_time = time.time()

        try:
            logger.info(
                f"ParseAddress request. Address: '{request.address}', "
                f"Country: '{request.country}', RequestId: '{request.request_id}'"
            )

            # Валидация входных данных
            if not request.address or request.address.strip() == "":
                return self._create_error_response(
                    address_parser_pb2.StatusCode.INVALID_REQUEST,
                    "Address cannot be empty",
                    request.address,
                    start_time
                )

            # Подготовка параметров для libpostal
            parse_options = {}
            if request.country:
                parse_options['country'] = request.country.lower()
            if request.language:
                parse_options['language'] = request.language.lower()

            # Парсинг адреса с помощью libpostal
            parsed = postal.parser.parse_address(request.address, **parse_options)

            logger.info(f"libpostal raw parse result: {parsed}")

            # Очистка компонентов от служебных слов
            cleaned_parsed = self._clean_parsed_components(parsed, request.language or 'ru')

            logger.info(f"Cleaned parsed components: {cleaned_parsed}")

            # Преобразование результата в компоненты
            components = self._build_components(cleaned_parsed)

            # Формирование успешного ответа
            execution_time_ms = int((time.time() - start_time) * 1000)

            return address_parser_pb2.ParseAddressResponse(
                status=address_parser_pb2.ResponseStatus(
                    code=address_parser_pb2.StatusCode.OK,
                    message="Address parsed successfully"
                ),
                original_address=request.address,
                components=components,
                metadata=address_parser_pb2.ResponseMetadata(
                    execution_time_ms=execution_time_ms,
                    timestamp=int(time.time() * 1000),
                    parser_version=SERVICE_VERSION
                )
            )

        except Exception as e:
            logger.error(f"Error parsing address: {str(e)}", exc_info=True)
            return self._create_error_response(
                address_parser_pb2.StatusCode.INTERNAL_ERROR,
                f"Internal error while parsing address: {str(e)}",
                request.address,
                start_time
            )

    def NormalizeAddress(self, request, context):
        """
        Нормализует адрес с использованием libpostal
        """
        start_time = time.time()

        try:
            logger.info(
                f"NormalizeAddress request. Address: '{request.address}', "
                f"Country: '{request.country}', RequestId: '{request.request_id}'"
            )

            # Валидация входных данных
            if not request.address or request.address.strip() == "":
                return address_parser_pb2.NormalizeAddressResponse(
                    status=address_parser_pb2.ResponseStatus(
                        code=address_parser_pb2.StatusCode.INVALID_REQUEST,
                        message="Address cannot be empty"
                    ),
                    original_address=request.address,
                    normalized_address="",
                    alternatives=[]
                )

            # Подготовка параметров для libpostal expand
            expand_options = {
                'strip_accents': False,
                'transliterate': False,
                'replace_word_hyphens': False,
            }

            # Определяем язык
            if request.language:
                expand_options['languages'] = [request.language.lower()]
            elif request.country:
                # Маппинг стран на языки
                country_to_lang = {
                    'ru': 'ru',
                    'us': 'en',
                    'gb': 'en',
                    'de': 'de',
                    'fr': 'fr',
                }
                lang = country_to_lang.get(request.country.lower(), 'en')
                expand_options['languages'] = [lang]

            logger.info(f"Expand options: {expand_options}")

            # Нормализация с помощью libpostal expand
            normalized_variants = postal.expand.expand_address(
                request.address,
                **expand_options
            )

            logger.info(f"libpostal expand result: {len(normalized_variants)} variants")
            if normalized_variants:
                logger.info(f"First 3 variants: {normalized_variants[:3]}")

            # Первый вариант - основной, остальные - альтернативы
            primary_normalized = normalized_variants[0] if normalized_variants else request.address
            alternatives = normalized_variants[1:6] if len(normalized_variants) > 1 else []

            # Применение дополнительных опций нормализации
            if request.options:
                primary_normalized = self._apply_normalize_options(
                    primary_normalized,
                    request.options
                )
                alternatives = [
                    self._apply_normalize_options(alt, request.options)
                    for alt in alternatives
                ]

            # Формирование ответа
            execution_time_ms = int((time.time() - start_time) * 1000)

            return address_parser_pb2.NormalizeAddressResponse(
                status=address_parser_pb2.ResponseStatus(
                    code=address_parser_pb2.StatusCode.OK,
                    message="Address normalized successfully"
                ),
                original_address=request.address,
                normalized_address=primary_normalized,
                alternatives=alternatives,
                metadata=address_parser_pb2.ResponseMetadata(
                    execution_time_ms=execution_time_ms,
                    timestamp=int(time.time() * 1000),
                    parser_version=SERVICE_VERSION
                )
            )

        except Exception as e:
            logger.error(f"Error normalizing address: {str(e)}", exc_info=True)
            return address_parser_pb2.NormalizeAddressResponse(
                status=address_parser_pb2.ResponseStatus(
                    code=address_parser_pb2.StatusCode.INTERNAL_ERROR,
                    message=f"Internal error while normalizing address: {str(e)}"
                ),
                original_address=request.address,
                normalized_address="",
                alternatives=[]
            )

    def HealthCheck(self, request, context):
        """
        Health check endpoint
        """
        try:
            uptime = int(time.time() - START_TIME)

            # Проверяем, что libpostal работает
            test_parse = postal.parser.parse_address("test")

            return address_parser_pb2.HealthCheckResponse(
                status=address_parser_pb2.HealthStatus.HEALTHY,
                version=SERVICE_VERSION,
                uptime_seconds=uptime,
                libpostal_version="1.1.0"  # Версия libpostal
            )
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return address_parser_pb2.HealthCheckResponse(
                status=address_parser_pb2.HealthStatus.UNHEALTHY,
                version=SERVICE_VERSION,
                uptime_seconds=int(time.time() - START_TIME),
                libpostal_version="unknown"
            )

    # =========================================================================
    # Вспомогательные методы
    # =========================================================================

    def _clean_parsed_components(self, parsed: List[tuple], language: str = 'ru') -> List[tuple]:
        """
        Очищает распарсенные компоненты от служебных слов
        Использует стандарты ФИАС для российских адресов

        Args:
            parsed: Список кортежей (value, label) от libpostal
            language: Код языка (ru, en, и т.д.)

        Returns:
            Очищенный список кортежей
        """
        # Служебные слова согласно классификатору ФИАС
        # См. https://www.alta.ru/fias/socrname/
        service_words = {
            'house_number': [
                # Идентификационные элементы объекта адресации (ФИАС)
                'дом', 'д', 'д.', 'владение', 'влд', 'влд.', 'домовладение', 'двлд', 'двлд.',
                'здание', 'зд', 'зд.', 'строение', 'стр', 'стр.', 'корпус', 'к', 'к.',
                'литер', 'лит', 'лит.',
                # English
                'building', 'bldg', 'house', 'h', 'no', 'number', '#',
                # Transliteration
                'dom', 'd', 'd.', 'zdanie', 'zd', 'zd.'
            ],
            'unit': [
                # Идентификационные элементы - помещения (ФИАС)
                'квартира', 'кв', 'кв.', 'комната', 'ком', 'ком.',
                'помещение', 'помещ', 'помещ.', 'офис', 'оф', 'оф.',
                'подвал', 'подв', 'подв.', 'погреб', 'п-б',
                # English
                'apartment', 'apt', 'apt.', 'unit', 'suite', 'ste', 'room', 'rm', 'office',
                # Transliteration
                'kvartira', 'kv', 'kv.', 'komnata', 'kom', 'kom.'
            ],
            'road': [
                # Элементы улично-дорожной сети (ФИАС)
                # Строго по классификатору https://www.alta.ru/fias/socrname/
                'ул.', 'пр-кт', 'пер.', 'б-р', 'наб.', 'ш.', 'пл.', 'пр-д', 'туп.',
                'ал.', 'взв.', 'взд.', 'дор.', 'лн.', 'мгстр.', 'тракт',
                # Варианты написания (без точки)
                'ул', 'пр', 'пер', 'наб', 'ш', 'пл', 'туп', 'ал', 'взв', 'взд', 'дор', 'лн', 'мгстр',
                # English
                'st', 'st.', 'ave', 'ave.', 'rd', 'rd.', 'blvd', 'blvd.', 'ln', 'dr', 'dr.'
            ],
            'level': [
                # Уровни в зданиях
                'этаж', 'эт', 'эт.',
                # English
                'floor', 'fl', 'fl.', 'level', 'lvl',
                # Transliteration
                'etazh', 'et', 'et.'
            ],
            'entrance': [
                # Элементы зданий
                'подъезд', 'под', 'под.', 'вход', 'парадная', 'пар', 'пар.',
                # English
                'entrance', 'ent', 'ent.',
                # Transliteration
                'pod', 'pod.', 'podyezd'
            ],
            'staircase': [
                # Структурные элементы зданий
                'корпус', 'корп', 'корп.', 'к', 'к.', 'секция', 'сек', 'сек.',
                # English
                'building', 'bldg', 'bldg.', 'block', 'blk', 'section',
                # Transliteration
                'korpus', 'korp', 'korp.', 'k', 'k.'
            ],
            'city': [
                # Населенные пункты (ФИАС)
                'город', 'г', 'г.', 'поселок', 'п', 'п.', 'пгт', 'пгт.',
                'рп', 'рп.', 'кп', 'кп.', 'гп', 'гп.', 'деревня', 'д', 'д.',
                'село', 'с', 'с.', 'станица', 'ст-ца', 'хутор', 'х', 'х.',
                'слобода', 'сл', 'сл.', 'аул', 'выселки', 'в-ки',
                # English
                'city', 'town', 'village',
                # Transliteration
                'gorod', 'g', 'g.', 'poselok', 'p', 'p.', 'derevnya', 'selo', 's', 's.'
            ],
            'state': [
                # Субъекты РФ и административные единицы (ФИАС)
                'область', 'обл', 'обл.', 'край', 'республика', 'респ', 'респ.',
                'автономный округ', 'а.окр', 'а.окр.', 'автономная область', 'а.обл', 'а.обл.',
                'район', 'р-н', 'муниципальный район', 'м.р-н',
                # English
                'region', 'oblast', 'krai', 'republic',
                # Transliteration
                'oblast', 'obl', 'obl.', 'raion', 'r-n'
            ],
            'postcode': [
                # Индекс
                'индекс',
                # English
                'zip', 'postal', 'code'
            ],
        }

        cleaned = []
        for value, label in parsed:
            cleaned_value = value.strip()

            # Получаем список служебных слов для данного типа компонента
            words_to_remove = service_words.get(label, [])

            # Разбиваем значение на слова
            words = cleaned_value.split()

            # Удаляем служебные слова (без учета регистра)
            filtered_words = [
                word for word in words
                if word.lower() not in words_to_remove
            ]

            # Собираем обратно
            cleaned_value = ' '.join(filtered_words).strip()

            # Добавляем только если осталось что-то после очистки
            if cleaned_value:
                cleaned.append((cleaned_value, label))

        return cleaned

    def _format_to_fias_standard(self, components: address_parser_pb2.AddressComponents) -> str:
        """
        Формирует адрес в стандартном формате ФИАС с правильными сокращениями

        Args:
            components: Объект AddressComponents

        Returns:
            Отформатированный адрес в формате ФИАС
        """
        # Стандартные сокращения ФИАС
        fias_abbreviations = {
            'country': '',  # Страна обычно не включается в адрес
            'state': 'обл.',  # Область
            'city': 'г.',  # Город
            'road': 'ул.',  # Улица (по умолчанию)
            'house_number': 'д.',
            'staircase': 'к.',  # Корпус
            'unit': 'кв.',
            'level': 'эт.',
            'entrance': 'под.',
            'postcode': '',  # Индекс идет в начале без сокращения
        }

        parts = []

        # Порядок компонентов в ФИАС адресе
        # Индекс, Субъект РФ, Город, Улица, Дом, Корпус, Квартира

        if components.postcode:
            parts.append(components.postcode)

        if components.state:
            # Для области, края используем стандартное сокращение
            parts.append(f"{fias_abbreviations['state']} {components.state.title()}")

        if components.city:
            parts.append(f"{fias_abbreviations['city']} {components.city.title()}")

        if components.road:
            # Определяем тип улицы для правильного сокращения
            road_name = components.road.title()
            # Проверяем, есть ли уже тип улицы в названии
            if any(word in road_name.lower() for word in ['проспект', 'переулок', 'бульвар', 'набережная', 'площадь', 'шоссе']):
                # Если полное название типа есть, заменяем на сокращение
                road_name = road_name.replace('Проспект', 'пр-кт').replace('проспект', 'пр-кт')
                road_name = road_name.replace('Переулок', 'пер.').replace('переулок', 'пер.')
                road_name = road_name.replace('Бульвар', 'б-р').replace('бульвар', 'б-р')
                road_name = road_name.replace('Набережная', 'наб.').replace('набережная', 'наб.')
                road_name = road_name.replace('Площадь', 'пл.').replace('площадь', 'пл.')
                road_name = road_name.replace('Шоссе', 'ш.').replace('шоссе', 'ш.')
                parts.append(road_name)
            else:
                # Иначе добавляем стандартное "ул."
                parts.append(f"{fias_abbreviations['road']} {road_name}")

        if components.house_number:
            parts.append(f"{fias_abbreviations['house_number']} {components.house_number}")

        if components.staircase:
            parts.append(f"{fias_abbreviations['staircase']} {components.staircase}")

        if components.unit:
            parts.append(f"{fias_abbreviations['unit']} {components.unit}")

        return ', '.join(parts)

    def _build_components(self, parsed: List[tuple]) -> address_parser_pb2.AddressComponents:
        """
        Создает объект AddressComponents из результата парсинга libpostal

        Args:
            parsed: Список кортежей (value, label) от libpostal

        Returns:
            AddressComponents объект
        """
        # Создаем словарь для удобного доступа
        components_dict = {}
        for value, label in parsed:
            # libpostal может вернуть несколько значений для одной метки
            # берем первое или объединяем
            if label not in components_dict:
                components_dict[label] = value
            else:
                # Если уже есть значение, добавляем через пробел
                components_dict[label] = f"{components_dict[label]} {value}"

        # Маппинг меток libpostal на поля proto
        return address_parser_pb2.AddressComponents(
            house_number=components_dict.get('house_number', ''),
            road=components_dict.get('road', ''),
            unit=components_dict.get('unit', ''),
            level=components_dict.get('level', ''),
            staircase=components_dict.get('staircase', ''),
            entrance=components_dict.get('entrance', ''),
            po_box=components_dict.get('po_box', ''),
            postcode=components_dict.get('postcode', ''),
            suburb=components_dict.get('suburb', ''),
            city=components_dict.get('city', ''),
            city_district=components_dict.get('city_district', ''),
            county=components_dict.get('county', ''),
            state=components_dict.get('state', ''),
            state_district=components_dict.get('state_district', ''),
            country=components_dict.get('country', ''),
            country_region=components_dict.get('country_region', ''),
            island=components_dict.get('island', ''),
            world_region=components_dict.get('world_region', ''),
            near=components_dict.get('near', '')
        )

    def _apply_normalize_options(self, address: str, options) -> str:
        """
        Применяет дополнительные опции нормализации к адресу
        """
        result = address

        if options.lowercase:
            result = result.lower()

        if options.remove_punctuation:
            # Удаляем основные знаки препинания
            punctuation = ',.;:!?'
            for p in punctuation:
                result = result.replace(p, '')

        if options.transliterate:
            # Простая транслитерация кириллицы
            result = self._transliterate_cyrillic(result)

        return result.strip()

    def _transliterate_cyrillic(self, text: str) -> str:
        """
        Простая транслитерация кириллицы в латиницу
        """
        cyrillic_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya'
        }

        result = []
        for char in text:
            result.append(cyrillic_to_latin.get(char, char))

        return ''.join(result)

    def _create_error_response(
        self,
        code: address_parser_pb2.StatusCode,
        message: str,
        original_address: str,
        start_time: float
    ) -> address_parser_pb2.ParseAddressResponse:
        """
        Создает ответ с ошибкой
        """
        execution_time_ms = int((time.time() - start_time) * 1000)

        return address_parser_pb2.ParseAddressResponse(
            status=address_parser_pb2.ResponseStatus(
                code=code,
                message=message
            ),
            original_address=original_address,
            components=address_parser_pb2.AddressComponents(),
            metadata=address_parser_pb2.ResponseMetadata(
                execution_time_ms=execution_time_ms,
                timestamp=int(time.time() * 1000),
                parser_version=SERVICE_VERSION
            )
        )


def serve(port: int = 50052):
    """
    Запуск gRPC сервера
    """
    # Создаем gRPC сервер с пулом потоков
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Регистрируем наш сервис
    address_parser_pb2_grpc.add_AddressParserServiceServicer_to_server(
        AddressParserServicer(),
        server
    )

    # Привязываем к порту
    server.add_insecure_port(f'[::]:{port}')

    # Запускаем сервер
    server.start()
    logger.info(f"Address Parser gRPC server started on port {port}")

    try:
        # Ожидаем завершения
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        server.stop(0)


if __name__ == '__main__':
    serve()
