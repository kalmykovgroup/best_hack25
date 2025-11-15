# Python gRPC Geocode Service

Сервис для поиска адресов на основе данных OpenStreetMap с использованием BM25 поиска.

## Технологии

- **gRPC** - API протокол
- **BM25** - алгоритм поиска
- **libpostal** - парсинг и нормализация адресов
- **PyOSM** - работа с OSM данными
- **Pandas/GeoPandas** - обработка данных

## Структура

- `geocode.proto` - Protobuf контракт
- `grpc_server.py` - Реализация gRPC сервера
- `generate_grpc.py` - Генерация Python кода из .proto
- `Dockerfile` - Docker образ
- `10-moscow.osm.pbf` - Данные OpenStreetMap для Москвы

## Запуск в Docker

```bash
# Собрать образ
docker build -t geocode-service .

# Запустить контейнер
docker run -d -p 50051:50051 --name geocode-service geocode-service

# Логи
docker logs -f geocode-service
```

## Запуск локально

```bash
# Установить зависимости
pip install grpcio grpcio-tools protobuf pandas geopandas pyrosm bm25s postal autocorrect

# Сгенерировать gRPC код
python generate_grpc.py

# Запустить сервер
python grpc_server.py
```

**Примечание:** Для локального запуска требуется установленный libpostal.

## API

### SearchAddress
Поиск адресов по нормализованной строке.

**Запрос:**
```protobuf
message SearchAddressRequest {
  string normalized_query = 1;
  int32 limit = 2;
  string request_id = 3;
  SearchOptions options = 4;
}
```

**Ответ:**
```protobuf
message SearchAddressResponse {
  ResponseStatus status = 1;
  string searched_address = 2;
  repeated AddressObject objects = 3;
  int32 total_found = 4;
  ResponseMetadata metadata = 5;
}
```

### HealthCheck
Проверка работоспособности сервиса.

## Переменные окружения

- `PBF_PATH` - путь к OSM PBF файлу (по умолчанию: `/data/10-moscow.osm.pbf`)
- `GRPC_PORT` - порт gRPC сервера (по умолчанию: `50051`)

## Интеграция

Сервис интегрирован в `docker-compose.yaml` как `geocode-service` и доступен по адресу `geocode-service:50051` для других контейнеров.
