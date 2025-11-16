# Address Parser Service

Микросервис для парсинга и нормализации адресов на базе libpostal с поддержкой стандартов ФИАС.

## Возможности

- **Парсинг адресов** - разбор адреса на компоненты (город, улица, дом, квартира)
- **Нормализация адресов** - расширение аббревиатур и приведение к стандартному виду
- **Поддержка ФИАС** - распознавание стандартных российских сокращений
- **100+ языков** - международная поддержка через libpostal

## Быстрый старт

### Вариант 1: Запуск через docker-compose (рекомендуется)

```bash
# Из корня проекта best_hack25
cd "C:\Users\Apolon 1\RiderProjects\best_hack25"

# Запуск сервиса
docker-compose up -d address-parser

# Проверка логов
docker-compose logs -f address-parser
```

Сервис доступен на `localhost:50052` (gRPC)

### Вариант 2: Standalone запуск (без docker-compose)

```bash
# Переход в папку сервиса
cd "C:\Users\Apolon 1\RiderProjects\best_hack25\address-parser"

# Сборка образа
docker build -t address-parser:standalone .

# Запуск контейнера
docker run -d \
  --name address-parser-standalone \
  -p 50053:50052 \
  -v libpostal-data:/usr/local/share/libpostal \
  address-parser:standalone

# Проверка логов
docker logs -f address-parser-standalone
```

Сервис доступен на `localhost:50053` (gRPC)

**Примечание:** Первый запуск занимает ~10-15 минут (загрузка данных libpostal)

## API

### 1. ParseAddress - Парсинг адреса

Разбирает адрес на структурированные компоненты.

**Что отправлять:**
```protobuf
{
  "address": "Россия, Москва, ул. Тверская, д. 10, кв. 5",
  "country": "RU",      // опционально
  "language": "ru"      // опционально
}
```

**Что получите:**
```json
{
  "status": {
    "code": "OK",
    "message": "Address parsed successfully"
  },
  "original_address": "Россия, Москва, ул. Тверская, д. 10, кв. 5",
  "components": {
    "country": "россия",
    "city": "москва",
    "road": "тверская",        // без "ул."
    "house_number": "10",       // без "д."
    "unit": "5"                 // без "кв."
  },
  "metadata": {
    "execution_time_ms": 15,
    "timestamp": 1700000000000,
    "parser_version": "1.0.0"
  }
}
```

**Пример использования (Python):**
```python
import grpc
import address_parser_pb2
import address_parser_pb2_grpc

# Подключение к сервису
channel = grpc.insecure_channel('localhost:50052')
stub = address_parser_pb2_grpc.AddressParserServiceStub(channel)

# Запрос
request = address_parser_pb2.ParseAddressRequest(
    address="Россия, Москва, ул. Тверская, д. 10, кв. 5",
    country="RU",
    language="ru"
)

# Ответ
response = stub.ParseAddress(request)

print(f"Город: {response.components.city}")
print(f"Улица: {response.components.road}")
print(f"Дом: {response.components.house_number}")
print(f"Квартира: {response.components.unit}")
```

### 2. NormalizeAddress - Нормализация адреса

Расширяет аббревиатуры и приводит адрес к стандартному виду.

**Что отправлять:**
```protobuf
{
  "address": "г Москва ул Тверская д 10 кв 5",
  "country": "RU",
  "language": "ru",
  "options": {
    "lowercase": true,           // опционально
    "transliterate": false       // опционально
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
    "gorod moskva ulitsa tverskaya dom 10 kvartal 5"
  ]
}
```

### 3. HealthCheck - Проверка состояния

**Что отправлять:**
```protobuf
{}  // пустой запрос
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

Сервис распознаёт и удаляет стандартные сокращения согласно классификатору ФИАС:
https://www.alta.ru/fias/socrname/

**Элементы улично-дорожной сети:**
- ул., пр-кт, пер., б-р, наб., ш., пл., пр-д, туп., ал.

**Идентификационные элементы:**
- д., к., стр., влд., кв., ком., помещ., оф.

**Населенные пункты:**
- г., п., пгт., рп., д., с., ст-ца, х.

**Субъекты РФ:**
- обл., край, респ., а.окр., р-н

**Важно:** Сервис удаляет только стандартные ФИАС сокращения. Неправильные формы (например, "улиц" вместо "ул.") - ответственность libpostal и качества входных данных.

## Примеры использования

### Пример 1: Простой адрес
```
Вход: "Москва, ул. Арбат, 10"
Результат:
  city: "москва"
  road: "арбат"
  house_number: "10"
```

### Пример 2: Полный адрес с индексом
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
Вход: "Санкт-Петербург, пр-кт Невский, д. 28"
Результат:
  city: "санкт-петербург"
  road: "невский"
  house_number: "28"
```

### Пример 4: Нормализация с расширением
```
Вход: "г Москва ул Тверская д 10"
Нормализованный: "город москва улица тверская дом 10"
Варианты:
  - "gorod moskva ulitsa tverskaya dom 10"
  - "g moskva ul tverskaya d 10"
```

## Рекомендуемые форматы

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
улиц шмидта дом 3  (неправильная форма "улиц")
```

## Тестирование

### Запуск тестов

```bash
# Внутри Docker контейнера
docker exec address-parser-standalone python3 test_russian.py

# Или через docker-compose
docker-compose exec address-parser python3 test_russian.py
```

### Ручное тестирование

```python
import grpc
import address_parser_pb2
import address_parser_pb2_grpc

channel = grpc.insecure_channel('localhost:50052')
stub = address_parser_pb2_grpc.AddressParserServiceStub(channel)

# Тест парсинга
request = address_parser_pb2.ParseAddressRequest(
    address="Москва, ул. Тверская, д. 10, кв. 5",
    country="RU",
    language="ru"
)

response = stub.ParseAddress(request)
print(response.components)
```

## Управление сервисом

### Docker Compose

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

### Standalone Docker

```bash
# Сборка
docker build -t address-parser:standalone .

# Запуск
docker run -d --name address-parser-standalone \
  -p 50053:50052 \
  -v libpostal-data:/usr/local/share/libpostal \
  address-parser:standalone

# Логи
docker logs -f address-parser-standalone

# Остановка
docker stop address-parser-standalone

# Удаление
docker rm address-parser-standalone
```

## Интеграция с C# API

### 1. Добавьте proto файл

```bash
# Скопируйте proto файл в проект API
cp protos/address_parser.proto ../api/Protos/
```

### 2. Обновите .csproj

```xml
<ItemGroup>
  <Protobuf Include="Protos\address_parser.proto" GrpcServices="Client" />
</ItemGroup>
```

### 3. Зарегистрируйте клиент в Program.cs

```csharp
using Api.Grpc.AddressParser;

// Добавьте gRPC клиент
builder.Services.AddGrpcClient<AddressParserService.AddressParserServiceClient>(options =>
{
    options.Address = new Uri("http://localhost:50052");
})
.ConfigurePrimaryHttpMessageHandler(() =>
{
    var handler = new HttpClientHandler();
    if (builder.Environment.IsDevelopment())
    {
        handler.ServerCertificateCustomValidationCallback =
            HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
    }
    return handler;
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

## Конфигурация

### Environment Variables

```env
# .env файл
ADDRESS_PARSER_PORT=50052
ADDRESS_PARSER_URL=http://address-parser:50052
GRPC_TIMEOUT_SECONDS=30
```

### Docker Compose

```yaml
address-parser:
  build:
    context: ./address-parser
    dockerfile: Dockerfile
  ports:
    - "50052:50052"
  environment:
    - GRPC_PORT=50052
  volumes:
    - libpostal-data:/usr/local/share/libpostal
  networks:
    - app-network
```

## Технические детали

- **Язык:** Python 3.11
- **Библиотека:** libpostal 1.1.0
- **Протокол:** gRPC (HTTP/2)
- **Формат данных:** Protocol Buffers
- **Порт:** 50052 (docker-compose) / 50053 (standalone)
- **Docker образ:** best_hack25-address-parser

## Структура проекта

```
address-parser/
├── protos/
│   └── address_parser.proto    # gRPC API определение
├── server.py                   # Python gRPC сервер
├── test_russian.py             # Тесты для русских адресов
├── requirements.txt            # Python зависимости
├── Dockerfile                  # Docker образ
├── .dockerignore              # Исключения для Docker
└── README.md                  # Эта документация
```

## Troubleshooting

### Проблема: Сервис не запускается

```bash
# Проверьте логи
docker logs address-parser-standalone

# Пересоберите образ
docker build --no-cache -t address-parser:standalone .
```

### Проблема: Порт 50052 занят

```bash
# Найдите процесс
docker ps --filter "publish=50052"

# Остановите контейнер
docker stop <container_id>

# Или используйте другой порт
docker run -p 50053:50052 ...
```

### Проблема: "Connection refused"

**Причины:**
1. Сервис не запущен
2. Неправильный порт
3. Firewall блокирует соединение

**Решение:**
```bash
# Проверьте статус
docker ps | grep address-parser

# Проверьте логи
docker logs address-parser-standalone

# Проверьте порты
netstat -an | findstr "50052"
```

### Проблема: Долгая загрузка при первом запуске

Это **нормально**! libpostal загружает ~1.5GB языковых данных при первом запуске (~10-15 минут). При следующих запусках данные берутся из Docker volume и запуск происходит за ~30 секунд.

## Версия

**1.0.0** - Полная поддержка ФИАС стандартов, очистка компонентов от служебных слов

## Лицензия

MIT
