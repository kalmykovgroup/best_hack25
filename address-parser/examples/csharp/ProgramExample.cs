// Пример настройки AddressParserService в Program.cs

using Api.Grpc.AddressParser;
using Api.Services.AddressParser;

// В методе Main или при настройке WebApplicationBuilder

var builder = WebApplication.CreateBuilder(args);

// ... другие сервисы ...

// ============================================================================
// Настройка gRPC клиента для Address Parser сервиса
// ============================================================================

var addressParserUrl = builder.Configuration.GetValue<string>("AddressParserService:Url")
                       ?? "http://localhost:50052";

builder.Services.AddGrpcClient<AddressParserService.AddressParserServiceClient>(options =>
{
    options.Address = new Uri(addressParserUrl);
})
.ConfigurePrimaryHttpMessageHandler(() =>
{
    // Настройка HTTP/2 для gRPC
    var handler = new HttpClientHandler();

    // В dev режиме разрешаем самоподписанные сертификаты
    if (builder.Environment.IsDevelopment())
    {
        handler.ServerCertificateCustomValidationCallback =
            HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
    }

    return handler;
});

// Регистрация клиента как сервиса
builder.Services.AddScoped<IAddressParserClient, AddressParserClient>();

// ============================================================================
// Использование в контроллерах или сервисах
// ============================================================================

/*
public class AddressController : ControllerBase
{
    private readonly IAddressParserClient _addressParser;
    private readonly ILogger<AddressController> _logger;

    public AddressController(
        IAddressParserClient addressParser,
        ILogger<AddressController> logger)
    {
        _addressParser = addressParser;
        _logger = logger;
    }

    [HttpPost("parse")]
    public async Task<IActionResult> ParseAddress([FromBody] ParseAddressDto dto)
    {
        try
        {
            // Парсим адрес
            var response = await _addressParser.ParseAddressAsync(
                address: dto.Address,
                country: dto.Country ?? "RU",
                language: dto.Language ?? "ru",
                requestId: Guid.NewGuid().ToString()
            );

            if (response.Status.Code != StatusCode.Ok)
            {
                return BadRequest(new { error = response.Status.Message });
            }

            // Возвращаем распарсенные компоненты
            return Ok(new
            {
                original = response.OriginalAddress,
                components = new
                {
                    city = response.Components.City,
                    street = response.Components.Road,
                    houseNumber = response.Components.HouseNumber,
                    postcode = response.Components.Postcode,
                    // ... другие поля
                },
                metadata = new
                {
                    executionTimeMs = response.Metadata.ExecutionTimeMs
                }
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error parsing address");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }

    [HttpPost("normalize")]
    public async Task<IActionResult> NormalizeAddress([FromBody] NormalizeAddressDto dto)
    {
        try
        {
            // Нормализуем адрес
            var response = await _addressParser.NormalizeAddressAsync(
                address: dto.Address,
                country: dto.Country ?? "RU",
                transliterate: dto.Transliterate ?? false,
                lowercase: dto.Lowercase ?? false,
                removePunctuation: dto.RemovePunctuation ?? false,
                requestId: Guid.NewGuid().ToString()
            );

            if (response.Status.Code != StatusCode.Ok)
            {
                return BadRequest(new { error = response.Status.Message });
            }

            return Ok(new
            {
                original = response.OriginalAddress,
                normalized = response.NormalizedAddress,
                alternatives = response.Alternatives.ToList()
            });
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Error normalizing address");
            return StatusCode(500, new { error = "Internal server error" });
        }
    }
}
*/
