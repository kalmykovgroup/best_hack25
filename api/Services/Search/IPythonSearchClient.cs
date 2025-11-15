using Api.Grpc;
using Api.Grpc.AddressParser;

namespace Api.Services.Search;

/// <summary>
/// Интерфейс для gRPC клиента Python сервиса поиска
/// </summary>
public interface IPythonSearchClient
{
    /// <summary>
    /// Выполняет поиск адреса через Python gRPC сервис
    /// </summary>
    /// <param name="normalizedQuery">Нормализованный поисковый запрос</param>
    /// <param name="originalQuery">Оригинальный запрос пользователя</param>
    /// <param name="parsedComponents">Структурированные компоненты адреса (из libpostal)</param>
    /// <param name="limit">Максимальное количество результатов</param>
    /// <param name="requestId">ID запроса</param>
    /// <param name="cancellationToken">Токен отмены</param>
    /// <returns>Результаты поиска</returns>
    Task<SearchAddressResponse> SearchAddressAsync(
        string normalizedQuery,
        string originalQuery,
        AddressComponents? parsedComponents,
        int limit,
        string requestId,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Проверяет доступность Python gRPC сервиса
    /// </summary>
    /// <returns>True если сервис доступен, иначе False</returns>
    Task<bool> CheckHealthAsync();
}
