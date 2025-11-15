using Api.Grpc.AddressParser;
using Api.Models.Normalization;
using Api.Services.AddressParser;

namespace Api.Services.Normalization;

/// <summary>
/// Сервис парсинга и нормализации адресов с использованием gRPC Address Parser (libpostal)
/// </summary>
public class AddressNormalizer : IAddressNormalizer
{
    private readonly IAddressParserClient _addressParserClient;
    private readonly ILogger<AddressNormalizer> _logger;

    public AddressNormalizer(
        IAddressParserClient addressParserClient,
        ILogger<AddressNormalizer> logger)
    {
        _addressParserClient = addressParserClient;
        _logger = logger;
    }

    /// <summary>
    /// Парсит и нормализует адрес через Address Parser (libpostal)
    /// Возвращает и структурированные компоненты, и нормализованную строку
    /// </summary>
    public async Task<NormalizedAddressResult> NormalizeAndParseAsync(string rawAddress)
    {
        if (string.IsNullOrWhiteSpace(rawAddress))
        {
            return new NormalizedAddressResult
            {
                Success = false,
                NormalizedAddress = string.Empty,
                ErrorMessage = "Адрес пустой"
            };
        }

        try
        {
            _logger.LogDebug("Парсинг и нормализация адреса: {RawAddress}", rawAddress);

            var requestId = Guid.NewGuid().ToString();

            // Параллельно вызываем ParseAddress и NormalizeAddress
            var parseTask = _addressParserClient.ParseAddressAsync(
                address: rawAddress,
                country: "RU",
                language: "ru",
                requestId: requestId,
                cancellationToken: default);

            var normalizeTask = _addressParserClient.NormalizeAddressAsync(
                address: rawAddress,
                country: "RU",
                language: "ru",
                transliterate: false,
                lowercase: false,
                removePunctuation: false,
                requestId: requestId,
                cancellationToken: default);

            // Ждем оба результата
            await Task.WhenAll(parseTask, normalizeTask);

            var parseResponse = await parseTask;
            var normalizeResponse = await normalizeTask;

            // Проверяем успешность обоих запросов
            if (parseResponse.Status?.Code == Api.Grpc.AddressParser.StatusCode.Ok &&
                normalizeResponse.Status?.Code == Api.Grpc.AddressParser.StatusCode.Ok)
            {
                _logger.LogInformation("═══════════════════════════════════════════════════════════");
                _logger.LogInformation("📋 РЕЗУЛЬТАТ ОТ ADDRESS PARSER (libpostal)");
                _logger.LogInformation("───────────────────────────────────────────────────────────");
                _logger.LogInformation("🔤 Оригинальный:     '{Original}'", rawAddress);
                _logger.LogInformation("✨ Нормализованный:  '{Normalized}'", normalizeResponse.NormalizedAddress);
                _logger.LogInformation("📦 Альтернативы:     {Count}", normalizeResponse.Alternatives?.Count ?? 0);

                if (normalizeResponse.Alternatives?.Count > 0)
                {
                    for (int i = 0; i < Math.Min(3, normalizeResponse.Alternatives.Count); i++)
                    {
                        _logger.LogInformation("   {Index}. '{Alternative}'", i + 1, normalizeResponse.Alternatives[i]);
                    }
                }

                _logger.LogInformation("🏗️  Компоненты:");
                if (parseResponse.Components != null)
                {
                    var c = parseResponse.Components;
                    if (!string.IsNullOrEmpty(c.Country)) _logger.LogInformation("   • Country:        '{Value}'", c.Country);
                    if (!string.IsNullOrEmpty(c.State)) _logger.LogInformation("   • State:          '{Value}'", c.State);
                    if (!string.IsNullOrEmpty(c.City)) _logger.LogInformation("   • City:           '{Value}'", c.City);
                    if (!string.IsNullOrEmpty(c.CityDistrict)) _logger.LogInformation("   • CityDistrict:   '{Value}'", c.CityDistrict);
                    if (!string.IsNullOrEmpty(c.Suburb)) _logger.LogInformation("   • Suburb:         '{Value}'", c.Suburb);
                    if (!string.IsNullOrEmpty(c.Road)) _logger.LogInformation("   • Road:           '{Value}'", c.Road);
                    if (!string.IsNullOrEmpty(c.HouseNumber)) _logger.LogInformation("   • HouseNumber:    '{Value}'", c.HouseNumber);
                    if (!string.IsNullOrEmpty(c.Unit)) _logger.LogInformation("   • Unit:           '{Value}'", c.Unit);
                    if (!string.IsNullOrEmpty(c.Postcode)) _logger.LogInformation("   • Postcode:       '{Value}'", c.Postcode);
                }
                else
                {
                    _logger.LogWarning("   ⚠️ Компоненты отсутствуют!");
                }
                _logger.LogInformation("═══════════════════════════════════════════════════════════");

                return new NormalizedAddressResult
                {
                    Success = true,
                    NormalizedAddress = normalizeResponse.NormalizedAddress,
                    Components = parseResponse.Components
                };
            }
            else
            {
                _logger.LogWarning(
                    "Ошибка обработки адреса. ParseStatus: {ParseStatus}, NormalizeStatus: {NormalizeStatus}",
                    parseResponse.Status?.Code, normalizeResponse.Status?.Code);

                // Возвращаем хотя бы то, что получилось
                return new NormalizedAddressResult
                {
                    Success = false,
                    NormalizedAddress = normalizeResponse.NormalizedAddress ?? rawAddress,
                    Components = parseResponse.Components,
                    ErrorMessage = parseResponse.Status?.Message ?? normalizeResponse.Status?.Message
                };
            }
        }
        catch (OperationCanceledException)
        {
            _logger.LogWarning("Запрос на обработку адреса был отменен");
            return new NormalizedAddressResult
            {
                Success = false,
                NormalizedAddress = rawAddress,
                ErrorMessage = "Запрос отменен"
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка при обработке адреса: {Address}", rawAddress);

            // В случае любой ошибки возвращаем исходный адрес
            return new NormalizedAddressResult
            {
                Success = false,
                NormalizedAddress = rawAddress,
                ErrorMessage = ex.Message
            };
        }
    }

    /// <summary>
    /// Проверяет валидность адреса
    /// </summary>
    public bool IsValid(string address)
    {
        // Принимаем абсолютно любую не-null строку
        // Address Parser и Python сервис сами решат, что с ней делать
        if (address == null)
        {
            return false;
        }

        return true;
    }
}
