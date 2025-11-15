# Address Parser Service

Микросервис для парсинга и нормализации адресов на базе libpostal с поддержкой стандартов ФИАС.

## Возможности

- **Парсинг адресов** - разбор адреса на компоненты (город, улица, дом, квартира и т.д.)
- **Нормализация адресов** - расширение аббревиатур и приведение к стандартному виду
- **Поддержка ФИАС** - распознавание стандартных российских сокращений
- **100+ языков** - международная поддержка через libpostal

## Быстрый старт

### Запуск сервиса

```bash
# Из корня проекта
docker-compose up -d address-parser

# Проверка статуса
docker-compose ps address-parser

# Логи
docker-compose logs -f address-parser
```

Сервис доступен на `localhost:50052` (gRPC)

## API

### 1. ParseAddress - Парсинг адреса

**Что отправлять:**
```python
{
  "address": "Москва, ул. Тверская, д. 10, кв. 5",
  "country": "RU",      # опционально
  "language": "ru"      # опционально
}
```

**Что получите:**
```json
{
  "status": {
    "code": "OK",
    "message": "Address parsed successfully"
  },
  "original_address": "Москва, ул. Тверская, д. 10, кв. 5",
  "components": {
    "city": "москва",
    "road": "тверская",           // ✅ без "ул."
    "house_number": "10",          // ✅ без "д."
    "unit": "5",                   // ✅ без "кв."
    "country": "россия"
  },
  "metadata": {
    "execution_time_ms": 15,
    "timestamp": 1700000000000
  }
}
```

**Пример запроса (Python):**
```python
import grpc
import address_parser_pb2
import address_parser_pb2_grpc

channel = grpc.insecure_channel('localhost:50052')
stub = address_parser_pb2_grpc.AddressParserServiceStub(channel)

request = address_parser_pb2.ParseAddressRequest(
    address="Москва, ул. Тверская, д. 10, кв. 5",
    country="RU",
    language="ru"
)

response = stub.ParseAddress(request)

print(f"Город: {response.components.city}")
print(f"Улица: {response.components.road}")
print(f"Дом: {response.components.house_number}")
print(f"Квартира: {response.components.unit}")
```

### 2. NormalizeAddress - Нормализация адреса

**Что отправлять:**
```python
{
  "address": "г Москва ул Тверская д 10 кв 5",
  "country": "RU",
  "language": "ru",
  "options": {
    "lowercase": true,           # опционально
    "transliterate": false       # опционально
  }
}
```

**Что получите:**
```json
{
  "status": {
    "code": "OK",
    "message": "Address normalized successfully"
  },
  "original_address": "г Москва ул Тверская д 10 кв 5",
  "normalized_address": "город москва улица тверская дом 10 квартал 5",
  "alternatives": [
    "город москва улица тверская дом 10 квартира 5",
    "gorod moskva ulitsa tverskaya dom 10 kvartal 5",
    "gorod moskva ulitsa tverskaya dom 10 kvartira 5"
  ],
  "metadata": {
    "execution_time_ms": 8
  }
}
```

**Пример запроса (Python):**
```python
request = address_parser_pb2.NormalizeAddressRequest(
    address="г Москва ул Тверская д 10 кв 5",
    country="RU",
    language="ru"
)

response = stub.NormalizeAddress(request)

print(f"Исходный: {response.original_address}")
print(f"Нормализованный: {response.normalized_address}")
print(f"Варианты: {response.alternatives}")
```

### 3. HealthCheck - Проверка состояния

**Что отправлять:**
```python
{}  # пустой запрос
```

**Что получите:**
```json
{
  "status": "HEALTHY",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "libpostal_version": "1.1.0"
}
```

## Компоненты адреса

Сервис распознаёт следующие компоненты:

| Поле | Описание | Пример |
|------|----------|--------|
| `house_number` | Номер дома | "10", "5А" |
| `road` | Улица | "тверская", "невский проспект" |
| `unit` | Квартира/офис | "5", "12А" |
| `city` | Город | "москва", "санкт-петербург" |
| `state` | Область/регион | "московская область" |
| `country` | Страна | "россия" |
| `postcode` | Индекс | "119019" |
| `staircase` | Корпус/строение | "2", "А" |
| `level` | Этаж | "3" |
| `entrance` | Подъезд | "1" |

## Поддержка ФИАС

Сервис автоматически распознаёт и обрабатывает стандартные российские сокращения:

**Улично-дорожная сеть:**
- ул., пр-кт, пер., б-р, наб., ш., пл., пр-д, туп., ал.

**Идентификационные элементы:**
- д., к., стр., влд., кв., ком., помещ., оф.

**Населенные пункты:**
- г., п., пгт., рп., д., с., ст-ца, х.

**Субъекты РФ:**
- обл., край, респ., а.окр., р-н

## Рекомендуемые форматы адресов

**✅ Хорошие форматы:**
```
Москва, ул. Тверская, д. 10, кв. 5
Санкт-Петербург, Невский проспект, 28
г. Мытищи, ул. Мира, д. 12
Московская обл., г. Химки, ул. Ленина, 5
```

**❌ Проблемные форматы:**
```
Московская область город Мытищи улица Мира дом 12
обл. Московская, с. Ивановское, ул. Центральная
```

## Примеры использования

### Пример 1: Простой адрес
```
Вход: "Москва, ул. Арбат, 10"
Результат:
  city: "москва"
  road: "арбат"
  house_number: "10"
```

### Пример 2: Полный адрес
```
Вход: "119019, Москва, ул. Новый Арбат, д. 10, кв. 5"
Результат:
  postcode: "119019"
  city: "москва"
  road: "новый арбат"
  house_number: "10"
  unit: "5"
```

### Пример 3: Адрес с проспектом
```
Вход: "Санкт-Петербург, Невский пр-кт, 28"
Результат:
  city: "санкт-петербург"
  road: "невский"
  house_number: "28"
```

### Пример 4: Нормализация
```
Вход: "г Москва ул Тверская д 10"
Нормализованный: "город москва улица тверская дом 10"
Варианты:
  - "gorod moskva ulitsa tverskaya dom 10"
  - "g moskva ul tverskaya d 10"
```

## Интеграция с C# API

### 1. Добавьте proto файл

Скопируйте `protos/address_parser.proto` в `api/Protos/`

### 2. Обновите .csproj

```xml
<Protobuf Include="Protos\address_parser.proto" GrpcServices="Client" />
```

### 3. Добавьте клиент в Program.cs

```csharp
using Api.Grpc.AddressParser;

builder.Services.AddGrpcClient<AddressParserService.AddressParserServiceClient>(options =>
{
    options.Address = new Uri("http://localhost:50052");
});
```

### 4. Используйте в контроллере

```csharp
public class AddressController : ControllerBase
{
    private readonly AddressParserService.AddressParserServiceClient _client;

    public AddressController(AddressParserService.AddressParserServiceClient client)
    {
        _client = client;
    }

    [HttpPost("parse")]
    public async Task<IActionResult> Parse([FromBody] string address)
    {
        var request = new ParseAddressRequest
        {
            Address = address,
            Country = "RU",
            Language = "ru"
        };

        var response = await _client.ParseAddressAsync(request);

        return Ok(new
        {
            city = response.Components.City,
            road = response.Components.Road,
            houseNumber = response.Components.HouseNumber,
            unit = response.Components.Unit
        });
    }
}
```

## Производительность

- **Парсинг:** 10-50ms
- **Нормализация:** 5-30ms
- **Пропускная способность:** ~1000 req/sec

## Полезные команды

```bash
# Запуск
docker-compose up -d address-parser

# Пересборка
docker-compose up --build address-parser

# Логи
docker-compose logs -f address-parser

# Статус
docker-compose ps address-parser

# Перезапуск
docker-compose restart address-parser

# Остановка
docker-compose stop address-parser
```

## Конфигурация

Настройки в `.env`:
```env
ADDRESS_PARSER_PORT=50052
ADDRESS_PARSER_URL=http://address-parser:50052
```

## Технические детали

- **Язык:** Python 3.11
- **Библиотека:** libpostal 1.1.0
- **Протокол:** gRPC (HTTP/2)
- **Формат данных:** Protocol Buffers
- **Порт:** 50052
- **Docker образ:** best_hack25-address-parser

## Версия

**1.0.0** - Полная поддержка ФИАС стандартов, очистка компонентов от служебных слов
