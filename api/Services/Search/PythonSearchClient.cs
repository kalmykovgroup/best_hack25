using Api.Grpc;
using Api.Grpc.AddressParser;
using Grpc.Core;

namespace Api.Services.Search;

/// <summary>
/// gRPC клиент для общения с Python сервисом поиска
/// </summary>
public class PythonSearchClient : IPythonSearchClient
{
    private readonly GeocodeService.GeocodeServiceClient _grpcClient;
    private readonly ILogger<PythonSearchClient> _logger;

    public PythonSearchClient(
        GeocodeService.GeocodeServiceClient grpcClient,
        ILogger<PythonSearchClient> logger)
    {
        _grpcClient = grpcClient;
        _logger = logger;
    }

    /// <summary>
    /// Выполняет поиск адреса через Python gRPC сервис
    /// </summary>
    public async Task<SearchAddressResponse> SearchAddressAsync(
        string normalizedQuery,
        string originalQuery,
        AddressComponents? parsedComponents,
        int limit,
        string requestId,
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation(
                "Отправка gRPC запроса в Python сервис. Original: {Original}, Normalized: {Normalized}, " +
                "Components: City={City}, Road={Road}, House={House}, Limit: {Limit}, RequestId: {RequestId}",
                originalQuery, normalizedQuery,
                parsedComponents?.City, parsedComponents?.Road, parsedComponents?.HouseNumber,
                limit, requestId);

            var request = new SearchAddressRequest
            {
                NormalizedQuery = normalizedQuery,
                OriginalQuery = originalQuery,
                Limit = limit,
                RequestId = requestId,
                Options = new SearchOptions
                {
                    MinScoreThreshold = 0.3, // TODO: Вынести в настройки
                    EnableFuzzySearch = true
                }
            };

            // Конвертируем компоненты Address Parser в формат для Python сервиса
            if (parsedComponents != null)
            {
                request.ParsedComponents = ConvertToParsedAddressComponents(parsedComponents);
            }

            // Устанавливаем таймаут и CancellationToken для запроса
            var deadline = DateTime.UtcNow.AddSeconds(30);
            var callOptions = new CallOptions(
                deadline: deadline,
                cancellationToken: cancellationToken);

            // Выполняем gRPC вызов
            var response = await _grpcClient.SearchAddressAsync(request, callOptions);

            _logger.LogInformation(
                "Получен ответ от Python сервиса. StatusCode: {StatusCode}, ObjectsCount: {Count}",
                response.Status.Code, response.Objects.Count);

            return response;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.Cancelled)
        {
            _logger.LogInformation("gRPC запрос был отменен. RequestId: {RequestId}", requestId);
            throw new OperationCanceledException("Запрос был отменен", ex);
        }
        catch (RpcException ex)
        {
            _logger.LogError(
                "Ошибка gRPC при вызове Python сервиса. StatusCode: {StatusCode}, Detail: {Detail}",
                ex.StatusCode, ex.Status.Detail);

            // Определяем понятное сообщение для пользователя
            string userMessage = ex.StatusCode switch
            {
                global::Grpc.Core.StatusCode.Unavailable =>
                    "Сервис поиска временно недоступен. Проверьте, что Python сервис запущен.",
                global::Grpc.Core.StatusCode.DeadlineExceeded =>
                    "Превышено время ожидания ответа от сервиса поиска.",
                global::Grpc.Core.StatusCode.Internal =>
                    "Внутренняя ошибка сервиса поиска.",
                _ =>
                    "Ошибка при обращении к сервису поиска."
            };

            // Возвращаем ответ с ошибкой
            return new SearchAddressResponse
            {
                Status = new Api.Grpc.ResponseStatus
                {
                    Code = Api.Grpc.StatusCode.ServiceUnavailable,
                    Message = userMessage
                },
                SearchedAddress = normalizedQuery,
                TotalFound = 0
            };
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка при вызове Python сервиса");

            return new SearchAddressResponse
            {
                Status = new Api.Grpc.ResponseStatus
                {
                    Code = Api.Grpc.StatusCode.InternalError,
                    Message = "Произошла неожиданная ошибка при поиске. Попробуйте позже."
                },
                SearchedAddress = normalizedQuery,
                TotalFound = 0
            };
        }
    }

    /// <summary>
    /// Проверяет доступность Python gRPC сервиса через HealthCheck
    /// </summary>
    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var request = new Api.Grpc.HealthCheckRequest();
            var deadline = DateTime.UtcNow.AddSeconds(3); // Короткий таймаут для health check
            var callOptions = new CallOptions(deadline: deadline);

            var response = await _grpcClient.HealthCheckAsync(request, callOptions);

            var isHealthy = response.Status == Api.Grpc.HealthStatus.Healthy;

            _logger.LogDebug(
                "Health check Python сервиса: {Status} (Version: {Version}, Uptime: {Uptime}s)",
                response.Status, response.Version, response.UptimeSeconds);

            return isHealthy;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.Unavailable)
        {
            _logger.LogWarning("Python gRPC сервис недоступен");
            return false;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.DeadlineExceeded)
        {
            _logger.LogWarning("Python gRPC сервис не отвечает (timeout)");
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Ошибка при проверке health check Python сервиса");
            return false;
        }
    }

    // =========================================================================
    // Вспомогательные методы
    // =========================================================================

    /// <summary>
    /// Конвертирует AddressComponents (из Address Parser) в ParsedAddressComponents (для Python сервиса)
    /// </summary>
    private ParsedAddressComponents ConvertToParsedAddressComponents(AddressComponents source)
    {
        return new ParsedAddressComponents
        {
            HouseNumber = source.HouseNumber ?? string.Empty,
            Road = source.Road ?? string.Empty,
            Unit = source.Unit ?? string.Empty,
            Level = source.Level ?? string.Empty,
            Staircase = source.Staircase ?? string.Empty,
            Entrance = source.Entrance ?? string.Empty,
            Postcode = source.Postcode ?? string.Empty,
            Suburb = source.Suburb ?? string.Empty,
            City = source.City ?? string.Empty,
            CityDistrict = source.CityDistrict ?? string.Empty,
            County = source.County ?? string.Empty,
            State = source.State ?? string.Empty,
            StateDistrict = source.StateDistrict ?? string.Empty,
            Country = source.Country ?? string.Empty,
            CountryRegion = source.CountryRegion ?? string.Empty,
            Island = source.Island ?? string.Empty,
            WorldRegion = source.WorldRegion ?? string.Empty,
            Near = source.Near ?? string.Empty
        };
    }
}
