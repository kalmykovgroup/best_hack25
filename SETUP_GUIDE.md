# Руководство по настройке проекта

Полное руководство по настройке и запуску проекта с микросервисами.

## Структура проекта

```
best_hack25/
├── api/                      # C# Web API (ASP.NET Core)
├── geocode-service/          # Python сервис поиска адресов (gRPC)
├── address-parser/           # Python сервис парсинга адресов (libpostal + gRPC)
├── docker-compose.yaml       # Оркестрация сервисов
└── .env                      # Переменные окружения
```

## Быстрый старт (5 минут)

### 1. Проверьте настройки в .env

Файл `.env` уже настроен с правильными портами:

```env
# Порты сервисов
API_HTTP_PORT=5000
API_HTTPS_PORT=5001
GEOCODE_SERVICE_PORT=50051
ADDRESS_PARSER_PORT=50052

# URLs для Docker (внутренняя коммуникация)
PYTHON_SERVICE_URL=http://geocode-service:50051
ADDRESS_PARSER_URL=http://address-parser:50052
```

**Не нужно ничего менять**, если используете стандартные порты.

### 2. Запустите все сервисы

```bash
# Windows PowerShell или CMD
cd "C:\Users\Apolon 1\RiderProjects\best_hack25"
docker-compose up --build
```

**Важно:** Первый запуск address-parser займет ~10-15 минут (загрузка данных libpostal).

### 3. Проверьте, что сервисы запущены

Откройте новый терминал:

```bash
# Проверка статуса
docker-compose ps

# Должны быть запущены:
# - api (port 5000, 5001)
# - geocode-service (port 50051)
# - address-parser (port 50052)
```

### 4. Тестируйте API

```bash
# Проверка health
curl http://localhost:5000/health

# Парсинг адреса (когда контроллер создан)
curl -X POST http://localhost:5000/api/address/parse \
  -H "Content-Type: application/json" \
  -d "{\"address\":\"Москва, ул. Тверская, д. 10\"}"
```

## Настройка для разных сценариев

### Сценарий 1: Все в Docker (Рекомендуется)

**Используется для:** Production, полное тестирование

```bash
docker-compose up --build
```

**Настройки:**
- API использует `appsettings.Docker.json`
- URLs: `http://geocode-service:50051`, `http://address-parser:50052`

### Сценарий 2: C# локально, Python в Docker

**Используется для:** Разработка C# кода

**1. Запустите только Python сервисы:**

```bash
docker-compose up geocode-service address-parser
```

**2. В Rider/Visual Studio:**
- Запустите API проект (F5)
- Используется `appsettings.json` с `localhost:50051`, `localhost:50052`

**3. Проверка:**
```bash
# API на localhost:5000
curl http://localhost:5000/health

# Python сервисы на localhost
curl http://localhost:50051  # Geocode
curl http://localhost:50052  # Address Parser
```

### Сценарий 3: Все локально (Только для WSL2/Linux)

**На Windows НЕ рекомендуется** - используйте Docker.

Для WSL2:
```bash
# В трех разных терминалах:

# Terminal 1: Geocode Service
cd geocode-service
python server.py

# Terminal 2: Address Parser
cd address-parser
python server.py

# Terminal 3: C# API
cd api
dotnet run
```

## Конфигурация подключений

### В C# API

**appsettings.json** (для локальной разработки):
```json
{
  "PythonService": {
    "Url": "http://localhost:50051"
  },
  "AddressParserService": {
    "Url": "http://localhost:50052"
  }
}
```

**appsettings.Docker.json** (для Docker):
```json
{
  "PythonService": {
    "Url": "http://geocode-service:50051"
  },
  "AddressParserService": {
    "Url": "http://address-parser:50052"
  }
}
```

### В Program.cs

Клиенты автоматически подключаются по URLs из конфигурации:

```csharp
// Geocode Service
var pythonServiceUrl = builder.Configuration.GetValue<string>("PythonService:Url")
                       ?? "http://localhost:50051";

builder.Services.AddGrpcClient<GeocodeService.GeocodeServiceClient>(options =>
{
    options.Address = new Uri(pythonServiceUrl);
});

// Address Parser Service
var addressParserUrl = builder.Configuration.GetValue<string>("AddressParserService:Url")
                       ?? "http://localhost:50052";

builder.Services.AddGrpcClient<AddressParserService.AddressParserServiceClient>(options =>
{
    options.Address = new Uri(addressParserUrl);
});
```

## Переменные окружения (.env)

### Для API сервиса

```env
# Окружение (Development, Staging, Production)
ASPNETCORE_ENVIRONMENT=Development

# Порты
API_HTTP_PORT=5000
API_HTTPS_PORT=5001
```

### Для Python сервисов

```env
# Geocode Service
GEOCODE_SERVICE_PORT=50051
GEOCODE_SERVICE_GRPC_PORT=50051

# Address Parser
ADDRESS_PARSER_PORT=50052
ADDRESS_PARSER_GRPC_PORT=50052

# Python настройки
PYTHONUNBUFFERED=1  # Логи в реальном времени
```

### Для Docker Compose

```env
# URLs для внутренней коммуникации (между контейнерами)
PYTHON_SERVICE_URL=http://geocode-service:50051
ADDRESS_PARSER_URL=http://address-parser:50052
```

## Интеграция Address Parser в C# проект

### Шаг 1: Добавьте proto файл

Скопируйте `address-parser/protos/address_parser.proto` в `api/Protos/`:

```bash
cp address-parser/protos/address_parser.proto api/Protos/
```

### Шаг 2: Обновите api.csproj

Добавьте:
```xml
<ItemGroup>
    <Protobuf Include="Protos\address_parser.proto" GrpcServices="Client" />
</ItemGroup>
```

### Шаг 3: Создайте папки для клиента

```bash
mkdir api/Services/AddressParser
mkdir api/Models/AddressParser
```

### Шаг 4: Скопируйте клиент и DTOs

```bash
cp address-parser/examples/csharp/IAddressParserClient.cs api/Services/AddressParser/
cp address-parser/examples/csharp/AddressParserClient.cs api/Services/AddressParser/
cp address-parser/examples/csharp/DTOs.cs api/Models/AddressParser/
```

### Шаг 5: Зарегистрируйте в Program.cs

```csharp
using Api.Services.AddressParser;

// После регистрации других gRPC клиентов:
builder.Services.AddScoped<IAddressParserClient, AddressParserClient>();
```

### Шаг 6: Используйте в контроллерах

```csharp
using Api.Services.AddressParser;
using Api.Models.AddressParser;

[ApiController]
[Route("api/[controller]")]
public class AddressController : ControllerBase
{
    private readonly IAddressParserClient _addressParser;

    public AddressController(IAddressParserClient addressParser)
    {
        _addressParser = addressParser;
    }

    [HttpPost("parse")]
    public async Task<IActionResult> Parse([FromBody] ParseAddressDto dto)
    {
        var response = await _addressParser.ParseAddressAsync(
            address: dto.Address,
            country: dto.Country ?? "RU"
        );

        if (response.Status.Code != StatusCode.Ok)
        {
            return BadRequest(new { error = response.Status.Message });
        }

        return Ok(new
        {
            city = response.Components.City,
            street = response.Components.Road,
            house = response.Components.HouseNumber
        });
    }
}
```

## Порты и эндпоинты

| Сервис          | Порт (Host) | Порт (Docker) | Протокол | Эндпоинт              |
|-----------------|-------------|---------------|----------|-----------------------|
| C# API          | 5000        | 8080          | HTTP     | http://localhost:5000 |
| C# API          | 5001        | 8081          | HTTPS    | https://localhost:5001|
| Geocode Service | 50051       | 50051         | gRPC     | localhost:50051       |
| Address Parser  | 50052       | 50052         | gRPC     | localhost:50052       |

## Проверка работоспособности

### Health Checks

```bash
# API
curl http://localhost:5000/health

# C# код для проверки сервисов
var geocodeHealthy = await _pythonSearchClient.CheckHealthAsync();
var parserHealthy = await _addressParser.CheckHealthAsync();
```

### Логи

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f address-parser
docker-compose logs -f geocode-service
docker-compose logs -f api
```

### Мониторинг портов

```bash
# Windows
netstat -an | findstr "5000 5001 50051 50052"

# Linux/WSL
netstat -tulpn | grep -E "5000|5001|50051|50052"
```

## Troubleshooting

### Проблема: "Connection refused" при обращении к gRPC сервису

**Решение:**
1. Проверьте, что сервис запущен: `docker-compose ps`
2. Проверьте логи: `docker-compose logs address-parser`
3. Проверьте URL в настройках:
   - В Docker: `http://address-parser:50052`
   - Локально: `http://localhost:50052`

### Проблема: "No module named 'grpc'" на Windows

**Решение:** Используйте Docker вместо локальной установки.

См. `address-parser/WINDOWS_SETUP.md` для деталей.

### Проблема: Address Parser долго запускается

**Причина:** Первый запуск загружает данные libpostal (~1.5GB)

**Решение:**
- Дождитесь окончания загрузки (10-15 минут)
- При следующих запусках данные будут в кэше

### Проблема: Порт уже занят

```bash
# Найдите процесс на порту
netstat -ano | findstr "50052"

# Остановите Docker контейнеры
docker-compose down

# Или убейте процесс
taskkill /PID <PID> /F
```

## Полезные команды

```bash
# Запуск
docker-compose up -d                    # В фоне
docker-compose up --build              # С пересборкой
docker-compose up address-parser       # Только один сервис

# Остановка
docker-compose down                    # Остановить все
docker-compose stop address-parser     # Остановить один сервис

# Логи
docker-compose logs -f                 # Все логи
docker-compose logs -f address-parser  # Логи одного сервиса

# Статус
docker-compose ps                      # Статус всех сервисов

# Очистка
docker-compose down -v                 # С удалением volumes
docker system prune -a                 # Полная очистка Docker
```

## Следующие шаги

1. **Прочитайте документацию:**
   - `address-parser/README.md` - Полная документация
   - `address-parser/INTEGRATION.md` - Детальное руководство по интеграции
   - `address-parser/QUICKSTART.md` - Быстрый старт

2. **Создайте контроллеры:**
   - Используйте примеры из `address-parser/examples/csharp/`

3. **Добавьте тесты:**
   - Unit тесты для клиентов
   - Integration тесты для сервисов

4. **Настройте CI/CD:**
   - Автоматическая сборка Docker образов
   - Автотесты

## Дополнительные ресурсы

- [gRPC .NET](https://docs.microsoft.com/en-us/aspnet/core/grpc/)
- [Docker Compose](https://docs.docker.com/compose/)
- [libpostal](https://github.com/openvenues/libpostal)
- [Environment Variables in .NET](https://docs.microsoft.com/en-us/aspnet/core/fundamentals/configuration/)
