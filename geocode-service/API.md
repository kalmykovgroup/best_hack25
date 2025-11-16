# API Документация

## Формат взаимодействия с C# WebAPI

### Входные данные

**HTTP POST** запрос в C# контроллер:

```csharp
[HttpPost("search")]
public async Task<IActionResult> SearchAddress([FromBody] string address)
{
    // address - это просто строка
    // Например: "Москва, ул. Тверская, д. 10"
}
```

**Тип:** `string`

**Примеры входных данных:**
```
"Москва, ул. Тверская, д. 10"
"Тверкая улиза 10" (с опечатками)
"Ленинский проспект, 15"
"г Москва ул Арбат д 5 кв 10"
"Красная площадь"
```

### Выходные данные

**Тип:** JSON массив

**Структура:**
```typescript
{
  searched_address: string,    // Исходный запрос
  objects: Array<{
    locality: string,          // Населенный пункт
    street: string,            // Улица
    number: string,            // Номер дома
    lon: number,               // Долгота
    lat: number,               // Широта
    score: number              // Релевантность 0-1
  }>
}
```

**Пример ответа:**
```json
{
  "searched_address": "Москва, ул. Тверская, д. 10",
  "objects": [
    {
      "locality": "Москва",
      "street": "улица Тверская",
      "number": "10",
      "lon": 37.612345,
      "lat": 55.756789,
      "score": 0.95
    },
    {
      "locality": "Москва",
      "street": "улица Тверская",
      "number": "10к1",
      "lon": 37.612445,
      "lat": 55.756889,
      "score": 0.85
    }
  ]
}
```

## C# Интеграция

### 1. Установка пакетов

```bash
dotnet add package Grpc.Net.Client
dotnet add package Google.Protobuf
dotnet add package Grpc.Tools
```

### 2. Копирование proto файла

Скопируйте `protos/geocode.proto` в ваш C# проект:
```
YourWebApi/
├── Protos/
│   └── geocode.proto
```

Обновите `.csproj`:
```xml
<ItemGroup>
  <Protobuf Include="Protos\geocode.proto" GrpcServices="Client" />
</ItemGroup>
```

### 3. Настройка в Program.cs

```csharp
using Grpc.Net.Client;
using GeocodeService.Grpc;

var builder = WebApplication.CreateBuilder(args);

// Регистрация gRPC клиента для geocode-service
var geocodeUrl = builder.Configuration.GetValue<string>("GeocodeService:Url")
                 ?? "http://geocode-service:50054";

builder.Services.AddGrpcClient<GeocodeService.GeocodeServiceClient>(options =>
{
    options.Address = new Uri(geocodeUrl);
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

var app = builder.Build();
app.Run();
```

### 4. Контроллер

```csharp
using Microsoft.AspNetCore.Mvc;
using GeocodeService.Grpc;

namespace YourWebApi.Controllers;

[ApiController]
[Route("api/[controller]")]
public class GeocodeController : ControllerBase
{
    private readonly GeocodeService.GeocodeServiceClient _geocodeClient;
    private readonly ILogger<GeocodeController> _logger;

    public GeocodeController(
        GeocodeService.GeocodeServiceClient geocodeClient,
        ILogger<GeocodeController> logger)
    {
        _geocodeClient = geocodeClient;
        _logger = logger;
    }

    [HttpPost("search")]
    public async Task<IActionResult> SearchAddress([FromBody] string address)
    {
        if (string.IsNullOrWhiteSpace(address))
            return BadRequest(new { error = "Address is required" });

        try
        {
            var request = new SearchAddressRequest
            {
                Address = address,
                Limit = 10,
                Algorithm = "advanced"  // "basic" или "advanced"
            };

            var response = await _geocodeClient.SearchAddressAsync(request);

            // Преобразование в формат хакатона
            var result = new
            {
                searched_address = response.SearchedAddress,
                objects = response.Objects.Select(obj => new
                {
                    locality = obj.Locality,
                    street = obj.Street,
                    number = obj.Number,
                    lon = obj.Lon,
                    lat = obj.Lat,
                    score = obj.Score
                }).ToArray()
            };

            _logger.LogInformation(
                "SearchAddress: '{Address}' -> {Count} results in {Ms}ms",
                address,
                response.Objects.Count,
                response.Metadata.ExecutionTimeMs
            );

            return Ok(result);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error searching address: {Address}", address);
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpGet("health")]
    public async Task<IActionResult> HealthCheck()
    {
        try
        {
            var response = await _geocodeClient.HealthCheckAsync(new HealthCheckRequest());

            return Ok(new
            {
                status = response.Status,
                database_size = response.DatabaseSize,
                corrector_available = response.CorrectorAvailable,
                parser_available = response.ParserAvailable
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Health check failed");
            return StatusCode(503, new { error = "Service unavailable" });
        }
    }
}
```

### 5. appsettings.json

```json
{
  "GeocodeService": {
    "Url": "http://geocode-service:50054"
  }
}
```

## Типы данных (TypeScript)

```typescript
// Входные данные
type SearchRequest = string;

// Выходные данные
interface SearchResponse {
  searched_address: string;
  objects: AddressObject[];
}

interface AddressObject {
  locality: string;   // Наименование населенного пункта
  street: string;     // Наименование улицы
  number: string;     // Номер дома (может содержать корпус: "10к2")
  lon: number;        // Долгота (longitude)
  lat: number;        // Широта (latitude)
  score: number;      // Релевантность 0-1 (1 = точное совпадение)
}
```

## Типы данных (C#)

```csharp
// Входные данные
public class SearchRequest
{
    public string Address { get; set; }
}

// Выходные данные
public class SearchResponse
{
    public string SearchedAddress { get; set; }
    public List<AddressObject> Objects { get; set; }
}

public class AddressObject
{
    public string Locality { get; set; }  // Наименование населенного пункта
    public string Street { get; set; }    // Наименование улицы
    public string Number { get; set; }    // Номер дома
    public double Lon { get; set; }       // Долгота
    public double Lat { get; set; }       // Широта
    public double Score { get; set; }     // Релевантность 0-1
}
```

## Curl примеры

### Через WebAPI

```bash
# Поиск адреса
curl -X POST http://localhost:8080/api/geocode/search \
  -H "Content-Type: application/json" \
  -d '"Москва, ул. Тверская, д. 10"'

# Health check
curl http://localhost:8080/api/geocode/health
```

### Напрямую через gRPC (grpcurl)

```bash
# Поиск
grpcurl -plaintext \
  -d '{"address": "Москва, ул. Тверская, д. 10", "limit": 5}' \
  localhost:50054 \
  geocode.GeocodeService/SearchAddress

# Health
grpcurl -plaintext \
  localhost:50054 \
  geocode.GeocodeService/HealthCheck
```

## Обработка ошибок

```csharp
try
{
    var response = await _geocodeClient.SearchAddressAsync(request);
    return Ok(response);
}
catch (RpcException ex) when (ex.StatusCode == StatusCode.Unavailable)
{
    // Сервис недоступен
    return StatusCode(503, new { error = "Geocode service unavailable" });
}
catch (RpcException ex) when (ex.StatusCode == StatusCode.DeadlineExceeded)
{
    // Таймаут
    return StatusCode(504, new { error = "Request timeout" });
}
catch (RpcException ex)
{
    // Другие gRPC ошибки
    _logger.LogError(ex, "gRPC error: {Status}", ex.StatusCode);
    return StatusCode(500, new { error = ex.Status.Detail });
}
```

## Особенности score

Поле `score` представляет собой комбинированную метрику:

```python
score = 0.4 * levenshtein_similarity +
        0.4 * component_match_ratio +
        0.2 * fts5_bm25_normalized
```

**Интерпретация:**
- `score >= 0.9` - очень точное совпадение
- `score >= 0.7` - хорошее совпадение
- `score >= 0.5` - приемлемое совпадение
- `score < 0.5` - низкая релевантность
