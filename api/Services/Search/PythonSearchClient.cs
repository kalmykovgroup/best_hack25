using Api.Grpc;
using Grpc.Core;

namespace Api.Services.Search;

/// <summary>
/// gRPC клиент для общения с Python сервисом поиска (geocode-service)
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
    /// Выполняет поиск адреса через geocode-service
    /// Сервис сам выполняет нормализацию через встроенный libpostal + BM25 поиск
    /// </summary>
    public async Task<SearchAddressResponse> SearchAddressAsync(
        string query,
        int limit,
        string requestId,
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation(
                "Отправка gRPC запроса в geocode-service. Query: {Query}, Limit: {Limit}, RequestId: {RequestId}",
                query, limit, requestId);

            var request = new SearchAddressRequest
            {
                Address = query,
                Limit = limit,
                Algorithm = "advanced",        // Используем улучшенный алгоритм (FTS5 + Levenshtein)
                RequestId = requestId
            };

            // Устанавливаем таймаут и CancellationToken для запроса
            var deadline = DateTime.UtcNow.AddSeconds(30);
            var callOptions = new CallOptions(
                deadline: deadline,
                cancellationToken: cancellationToken);

            // Выполняем gRPC вызов
            var response = await _grpcClient.SearchAddressAsync(request, callOptions);

            _logger.LogInformation(
                "Получен ответ от geocode-service. ObjectsCount: {Count}, ExecutionTime: {Ms}ms, Algorithm: {Algo}",
                response.Objects.Count,
                response.Metadata?.ExecutionTimeMs ?? 0,
                response.Metadata?.AlgorithmUsed ?? "unknown");

            return response;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.Cancelled)
        {
            _logger.LogInformation("gRPC запрос был отменен. RequestId: {RequestId}", requestId);
            throw new OperationCanceledException("Запрос был отменен", ex);
        }
        catch (RpcException ex)
        {
            _logger.LogError(
                "Ошибка gRPC при вызове geocode-service. StatusCode: {StatusCode}, Detail: {Detail}",
                ex.StatusCode, ex.Status.Detail);

            // Пробрасываем исключение дальше, чтобы контроллер/хаб могли обработать его
            // и вернуть клиенту корректное сообщение об ошибке
            throw;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка при вызове geocode-service");
            throw;
        }
    }

    /// <summary>
    /// Проверяет доступность geocode-service через HealthCheck
    /// </summary>
    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var request = new HealthCheckRequest();
            var deadline = DateTime.UtcNow.AddSeconds(3); // Короткий таймаут для health check
            var callOptions = new CallOptions(deadline: deadline);

            var response = await _grpcClient.HealthCheckAsync(request, callOptions);

            var isHealthy = response.Status == "ok";

            _logger.LogDebug(
                "Health check geocode-service: {Status} (DB size: {DbSize}, Corrector: {Corrector}, Parser: {Parser})",
                response.Status, response.DatabaseSize, response.CorrectorAvailable, response.ParserAvailable);

            return isHealthy;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.Unavailable)
        {
            _logger.LogWarning("geocode-service недоступен");
            return false;
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.DeadlineExceeded)
        {
            _logger.LogWarning("geocode-service не отвечает (timeout)");
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Ошибка при проверке health check geocode-service");
            return false;
        }
    }
}
