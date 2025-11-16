# OSM SQLite Геокодер

Сервис для конвертации OpenStreetMap данных в SQLite базу и предоставления REST API для поиска географических объектов.

## Описание

Сервис автоматически конвертирует файл `10-moscow.osm.pbf` (OSM данные Москвы) в SQLite базу данных при первом запуске. База данных кэшируется в Docker volume, поэтому повторная конвертация не требуется.

## Структура базы данных

База содержит 3 основные таблицы:

### Таблица `nodes` (узлы)
- `id` - уникальный ID узла
- `lat` - широта
- `lon` - долгота
- `tags` - JSON строка с тегами (название, тип объекта и т.д.)

### Таблица `ways` (пути)
- `id` - уникальный ID пути
- `tags` - JSON строка с тегами
- `nodes` - JSON массив ID узлов, составляющих путь

### Таблица `relations` (отношения)
- `id` - уникальный ID отношения
- `tags` - JSON строка с тегами
- `members` - JSON массив членов отношения

## Запуск

### Через Docker Compose
```bash
# Из корневой директории проекта
docker-compose up osm-db

# Или вместе со всеми сервисами
docker-compose up
```

### Переменные окружения
- `OSM_DB_PORT` - порт API (по умолчанию: 8091)

## REST API

Сервис предоставляет REST API на порту 8091.

### Базовые эндпоинты

#### GET /health
Проверка состояния сервиса и подключения к БД.

**Пример запроса:**
```bash
curl http://localhost:8091/health
```

**Ответ:**
```json
{
  "status": "healthy",
  "database": "connected",
  "nodes_count": 150000
}
```

#### GET /stats
Статистика по базе данных.

**Пример запроса:**
```bash
curl http://localhost:8091/stats
```

**Ответ:**
```json
{
  "nodes": 150000,
  "ways": 25000,
  "relations": 500,
  "total": 175500
}
```

### Работа с узлами (nodes)

#### GET /nodes
Получить список узлов с фильтрацией по координатам.

**Параметры запроса:**
- `limit` - количество результатов (по умолчанию: 100)
- `offset` - смещение для пагинации (по умолчанию: 0)
- `min_lat` - минимальная широта
- `max_lat` - максимальная широта
- `min_lon` - минимальная долгота
- `max_lon` - максимальная долгота

**Пример запроса:**
```bash
# Все узлы (первые 100)
curl http://localhost:8091/nodes

# Узлы в заданной области
curl "http://localhost:8091/nodes?min_lat=55.7&max_lat=55.8&min_lon=37.5&max_lon=37.6&limit=50"
```

**Ответ:**
```json
{
  "count": 50,
  "limit": 50,
  "offset": 0,
  "nodes": [
    {
      "id": 12345,
      "lat": 55.7558,
      "lon": 37.6173,
      "tags": {
        "name": "Красная площадь",
        "tourism": "attraction"
      }
    }
  ]
}
```

#### GET /nodes/:id
Получить конкретный узел по ID.

**Пример запроса:**
```bash
curl http://localhost:8091/nodes/12345
```

**Ответ:**
```json
{
  "id": 12345,
  "lat": 55.7558,
  "lon": 37.6173,
  "tags": {
    "name": "Красная площадь",
    "tourism": "attraction"
  }
}
```

### Работа с путями (ways)

#### GET /ways
Получить список путей.

**Параметры запроса:**
- `limit` - количество результатов (по умолчанию: 100)
- `offset` - смещение для пагинации (по умолчанию: 0)

**Пример запроса:**
```bash
curl http://localhost:8091/ways?limit=10
```

**Ответ:**
```json
{
  "count": 10,
  "limit": 10,
  "offset": 0,
  "ways": [
    {
      "id": 67890,
      "tags": {
        "name": "Тверская улица",
        "highway": "primary"
      },
      "nodes": [123, 456, 789]
    }
  ]
}
```

#### GET /ways/:id
Получить конкретный путь по ID.

**Пример запроса:**
```bash
curl http://localhost:8091/ways/67890
```

### Поиск

#### GET /search
Поиск объектов по тегам (название, тип и т.д.).

**Параметры запроса:**
- `q` - поисковый запрос (обязательный)
- `limit` - количество результатов (по умолчанию: 50)

**Пример запроса:**
```bash
# Поиск по названию
curl "http://localhost:8091/search?q=Красная+площадь"

# Поиск по типу объекта
curl "http://localhost:8091/search?q=restaurant"
```

**Ответ:**
```json
{
  "nodes": [
    {
      "id": 12345,
      "lat": 55.7558,
      "lon": 37.6173,
      "tags": {
        "name": "Красная площадь",
        "tourism": "attraction"
      }
    }
  ],
  "ways": [
    {
      "id": 67890,
      "tags": {
        "name": "Красная площадь",
        "place": "square"
      },
      "nodes": [123, 456, 789]
    }
  ]
}
```

## Использование в других сервисах

### Python
```python
import requests

# Поиск объекта
response = requests.get('http://osm-db:8091/search', params={'q': 'Кремль'})
results = response.json()

# Получение узлов в области
response = requests.get('http://osm-db:8091/nodes', params={
    'min_lat': 55.7,
    'max_lat': 55.8,
    'min_lon': 37.5,
    'max_lon': 37.6,
    'limit': 100
})
nodes = response.json()['nodes']
```

### C# (.NET)
```csharp
using System.Net.Http;
using System.Text.Json;

var client = new HttpClient();
client.BaseAddress = new Uri("http://osm-db:8091");

// Поиск объекта
var response = await client.GetAsync("/search?q=Кремль");
var content = await response.Content.ReadAsStringAsync();
var results = JsonSerializer.Deserialize<SearchResults>(content);

// Получение узла по ID
response = await client.GetAsync("/nodes/12345");
content = await response.Content.ReadAsStringAsync();
var node = JsonSerializer.Deserialize<Node>(content);
```

### JavaScript/TypeScript
```javascript
// Поиск объекта
const response = await fetch('http://localhost:8091/search?q=Кремль');
const results = await response.json();

// Получение узлов в области
const params = new URLSearchParams({
  min_lat: '55.7',
  max_lat: '55.8',
  min_lon: '37.5',
  max_lon: '37.6',
  limit: '100'
});
const nodesResponse = await fetch(`http://localhost:8091/nodes?${params}`);
const nodes = await nodesResponse.json();
```

## Примеры использования для геокодинга

### Поиск адреса
```bash
curl "http://localhost:8091/search?q=Тверская+улица"
```

### Поиск объектов по типу
```bash
# Рестораны
curl "http://localhost:8091/search?q=restaurant"

# Станции метро
curl "http://localhost:8091/search?q=subway"

# Парки
curl "http://localhost:8091/search?q=park"
```

### Поиск объектов в радиусе (bounding box)
```bash
# Центр Москвы
curl "http://localhost:8091/nodes?min_lat=55.74&max_lat=55.76&min_lon=37.61&max_lon=37.63&limit=1000"
```

## Производительность

- **Первый запуск**: 3-5 минут (конвертация OSM в SQLite)
- **Последующие запуски**: ~10-30 секунд (база кэширована)
- **Размер базы**: зависит от размера OSM файла (~200-500 MB для Москвы)
- **Потребление памяти**: 1-4 GB

## Troubleshooting

### Сервис не запускается
```bash
# Проверить логи
docker-compose logs osm-db

# Пересоздать контейнер
docker-compose down
docker-compose up osm-db
```

### База не создается
```bash
# Очистить volume и пересоздать
docker-compose down -v
docker-compose up osm-db
```

### Долгая конвертация
При первом запуске конвертация может занять несколько минут. Следите за логами:
```bash
docker-compose logs -f osm-db
```

## Архитектура

```
10-moscow.osm.pbf → convert_osm.py → moscow.db (SQLite)
                                           ↓
                                    api_server.py
                                           ↓
                                    REST API :8091
```

## Файлы

- `Dockerfile` - образ Docker
- `convert_osm.py` - скрипт конвертации OSM → SQLite
- `api_server.py` - REST API сервер (Flask)
- `entrypoint.sh` - скрипт запуска (конвертация + API)
- `requirements.txt` - зависимости Python
- `10-moscow.osm.pbf` - исходные OSM данные

## Лицензия

OSM данные распространяются под лицензией ODbL.
