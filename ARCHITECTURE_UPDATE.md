# Обновление архитектуры: Использование структурированных компонентов адреса

## Что было изменено

Система была переработана для использования **структурированных компонентов адреса** (из libpostal), вместо простых строк.

### До изменений

```
Пользователь → "Москва, ул. Тверская, 7"
    ↓
C# API → нормализация строки → "Москва улица Тверская 7"
    ↓
Python → поиск по строке
    ↓
Результаты
```

### После изменений

```
Пользователь → "Москва, ул. Тверская, д. 7"
    ↓
C# API → Address Parser (libpostal)
    ↓
Нормализация: "Москва улица Тверская дом 7"
    +
Компоненты: {city: "Москва", road: "Тверская", house_number: "7"}
    ↓
Python → поиск по компонентам (приоритет) + по строкам (fallback)
    ↓
Результаты (более точные)
```

---

## Технические изменения

### 1. Protocol Buffers (geocode.proto)

#### Добавлено сообщение `ParsedAddressComponents`

```protobuf
message ParsedAddressComponents {
  string house_number = 1;      // Номер дома
  string road = 2;              // Улица
  string unit = 3;              // Квартира/офис
  string level = 4;             // Этаж
  string staircase = 5;         // Подъезд
  string entrance = 6;          // Вход
  string postcode = 7;          // Почтовый индекс
  string suburb = 8;            // Район/микрорайон
  string city = 9;              // Город
  string city_district = 10;    // Округ города
  string county = 11;           // Округ
  string state = 12;            // Регион/область
  string state_district = 13;   // Округ региона
  string country = 14;          // Страна
  string country_region = 15;   // Регион страны
  string island = 16;           // Остров
  string world_region = 17;     // Мировой регион
  string near = 18;             // Ближайшая точка интереса
}
```

#### Обновлено `SearchAddressRequest`

```protobuf
message SearchAddressRequest {
  string normalized_query = 1;                          // Нормализованная строка
  int32 limit = 2;
  string request_id = 3;
  SearchOptions options = 4;
  string original_query = 5;                            // Оригинальный запрос
  ParsedAddressComponents parsed_components = 6;        // 🆕 Компоненты из libpostal
}
```

---

### 2. C# Backend

#### Новая модель: `NormalizedAddressResult`

**Файл:** `api/Models/Normalization/NormalizedAddressResult.cs`

```csharp
public class NormalizedAddressResult
{
    public string NormalizedAddress { get; set; }       // Нормализованная строка
    public AddressComponents? Components { get; set; }   // Компоненты из libpostal
    public bool Success { get; set; }
    public string? ErrorMessage { get; set; }
}
```

#### Обновлен `IAddressNormalizer`

**Файл:** `api/Services/Normalization/IAddressNormalizer.cs`

```csharp
public interface IAddressNormalizer
{
    // Было: string Normalize(string rawAddress);
    // Стало:
    Task<NormalizedAddressResult> NormalizeAndParseAsync(string rawAddress);

    bool IsValid(string address);
}
```

#### Обновлен `AddressNormalizer`

**Файл:** `api/Services/Normalization/AddressNormalizer.cs`

- Теперь **параллельно** вызывает `ParseAddress` и `NormalizeAddress` из Address Parser
- Возвращает и нормализованную строку, и компоненты
- Использует `Task.WhenAll` для оптимизации производительности

```csharp
public async Task<NormalizedAddressResult> NormalizeAndParseAsync(string rawAddress)
{
    // Параллельные вызовы к Address Parser
    var parseTask = _addressParserClient.ParseAddressAsync(...);
    var normalizeTask = _addressParserClient.NormalizeAddressAsync(...);

    await Task.WhenAll(parseTask, normalizeTask);

    return new NormalizedAddressResult
    {
        NormalizedAddress = normalizeResponse.NormalizedAddress,
        Components = parseResponse.Components
    };
}
```

#### Обновлен `PythonSearchClient`

**Файл:** `api/Services/Search/PythonSearchClient.cs`

- Принимает `AddressComponents` (из address_parser.proto)
- Конвертирует в `ParsedAddressComponents` (для geocode.proto)
- Передает компоненты в Python сервис

```csharp
public async Task<SearchAddressResponse> SearchAddressAsync(
    string normalizedQuery,
    string originalQuery,
    AddressComponents? parsedComponents,  // 🆕
    int limit,
    string requestId,
    CancellationToken cancellationToken = default)
{
    var request = new SearchAddressRequest
    {
        NormalizedQuery = normalizedQuery,
        OriginalQuery = originalQuery,
        ParsedComponents = ConvertToParsedAddressComponents(parsedComponents)  // 🆕
    };

    // ...
}
```

#### Обновлены `GeocodeHub` и `GeocodeController`

**Файлы:**
- `api/Hubs/GeocodeHub.cs`
- `api/Controllers/GeocodeController.cs`

Теперь используют `NormalizeAndParseAsync` и передают компоненты:

```csharp
// Парсинг и нормализация
var normalizeResult = await _addressNormalizer.NormalizeAndParseAsync(request.Query);

// Поиск с компонентами
var grpcResponse = await _pythonSearchClient.SearchAddressAsync(
    normalizeResult.NormalizedAddress,
    request.Query,
    normalizeResult.Components,  // 🆕
    request.Limit,
    requestId,
    cts.Token);
```

---

### 3. Python Backend

**Файл:** `python-search/grpc_server.py`

#### Двухуровневый поиск

1. **Приоритет 1: Поиск по компонентам**
   - Проверяет совпадение по `city`, `road`, `house_number`
   - Повышает score при совпадении нескольких компонентов
   - Все 3 компонента → +0.1 к score
   - 2 компонента → +0.05 к score

2. **Приоритет 2: Fallback на поиск по строкам**
   - Если компоненты не дали результатов
   - Поиск по `normalized_query` и `original_query`

```python
def SearchAddress(self, request, context):
    components = request.parsed_components

    # Извлекаем компоненты
    search_city = components.city.lower() if components and components.city else ""
    search_road = components.road.lower() if components and components.road else ""
    search_house = components.house_number.lower() if components and components.house_number else ""

    for item in self.mock_data:
        # Приоритет 1: Поиск по компонентам
        if components and (search_city or search_road or search_house):
            city_match = search_city and search_city in item["locality"].lower()
            road_match = search_road and search_road in item["street"].lower()
            house_match = search_house and search_house in item["number"].lower()

            if city_match or road_match or house_match:
                # Повышаем score
                adjusted_score = calculate_score(city_match, road_match, house_match)
                # Добавляем результат
                continue

        # Приоритет 2: Fallback на строки
        if query_lower in item["full_address"].lower():
            # Добавляем результат с базовым score
```

---

## Преимущества новой архитектуры

### 1. **Более точный поиск**
- Структурированные компоненты позволяют искать по конкретным полям (город, улица, дом)
- Меньше ложных срабатываний

### 2. **Лучшее ранжирование**
- Score зависит от количества совпавших компонентов
- Результаты упорядочены по релевантности

### 3. **Гибкость**
- Если libpostal не смог распарсить → fallback на строковый поиск
- Система работает даже при недоступности Address Parser

### 4. **Производительность**
- Параллельные вызовы `ParseAddress` и `NormalizeAddress`
- Использование `Task.WhenAll` в C#

### 5. **Масштабируемость**
- В будущем можно добавить поиск по индексу, району, региону
- Легко расширить логику ранжирования

---

## Пример работы

### Входные данные

**Запрос пользователя:** `"Москва, ул. Тверская, д. 7"`

### Обработка в Address Parser (libpostal)

**ParseAddress:**
```json
{
  "city": "Москва",
  "road": "Тверская",
  "house_number": "7"
}
```

**NormalizeAddress:**
```
"Москва улица Тверская дом 7"
```

### Отправка в Python

```json
{
  "original_query": "Москва, ул. Тверская, д. 7",
  "normalized_query": "Москва улица Тверская дом 7",
  "parsed_components": {
    "city": "Москва",
    "road": "Тверская",
    "house_number": "7"
  }
}
```

### Поиск в Python

1. Проверка по компонентам:
   - `city == "Москва"` ✅
   - `road == "Тверская"` ✅
   - `house_number == "7"` ✅
   - **Score: 0.95 + 0.1 = 1.0** (все 3 компонента совпали)

2. Результат:
```json
{
  "locality": "Москва",
  "street": "Тверская улица",
  "number": "7",
  "lon": 37.615560,
  "lat": 55.757814,
  "score": 1.0
}
```

---

## Что нужно сделать для запуска

### 1. Перегенерировать gRPC код

```bash
cd python-search
python generate_grpc.py
```

### 2. Пересобрать C# API

```bash
cd api
dotnet build
```

### 3. Запустить все сервисы

```bash
# 1. Address Parser (libpostal) - порт 50052
cd address-parser
docker-compose up -d

# 2. Python Geocode Service - порт 50051
cd python-search
python grpc_server.py

# 3. C# API - порт 7082
cd api
dotnet run
```

### 4. Тестирование

```bash
# Проверка health check
curl https://localhost:7082/health

# Через SignalR (React)
# см. api/REACT_INTEGRATION_GUIDE.md
```

---

## Файлы, которые изменились

### Proto файлы
- ✅ `api/Protos/geocode.proto` - добавлено `ParsedAddressComponents`
- ✅ `python-search/geocode.proto` - скопировано из api

### C# Backend
- ✅ `api/Models/Normalization/NormalizedAddressResult.cs` - новая модель
- ✅ `api/Services/Normalization/IAddressNormalizer.cs` - обновлен интерфейс
- ✅ `api/Services/Normalization/AddressNormalizer.cs` - переработана логика
- ✅ `api/Services/Search/IPythonSearchClient.cs` - добавлен параметр компонентов
- ✅ `api/Services/Search/PythonSearchClient.cs` - конвертация компонентов
- ✅ `api/Hubs/GeocodeHub.cs` - использование `NormalizeAndParseAsync`
- ✅ `api/Controllers/GeocodeController.cs` - использование `NormalizeAndParseAsync`

### Python Backend
- ✅ `python-search/grpc_server.py` - двухуровневый поиск

### Документация
- ✅ `python-search/REGENERATE_GRPC.md` - обновлена инструкция
- ✅ `ARCHITECTURE_UPDATE.md` - этот файл

---

## Миграция с предыдущей версии

Если у вас уже запущена старая версия:

1. **Остановите все сервисы**
2. **Удалите старые сгенерированные файлы:**
   ```bash
   rm python-search/geocode_pb2.py
   rm python-search/geocode_pb2_grpc.py
   ```
3. **Перегенерируйте gRPC код** (см. выше)
4. **Пересоберите C# проект**
5. **Запустите сервисы в правильном порядке:**
   - Address Parser → Python Geocode → C# API

---

**Версия:** 2.0
**Дата:** 2025-11-15
**Автор:** Claude Code
