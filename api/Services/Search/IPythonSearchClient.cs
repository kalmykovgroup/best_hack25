using Api.Grpc;

namespace Api.Services.Search;

/// <summary>
/// Интерфейс для gRPC клиента geocode-service
/// Сервис выполняет нормализацию и парсинг самостоятельно через встроенный libpostal
/// </summary>
public interface IPythonSearchClient
{
    /// <summary>
    /// Выполняет поиск адреса через geocode-service
    /// Сервис сам выполняет нормализацию (libpostal) и поиск (BM25 + FTS5)
    /// </summary>
    /// <param name="query">Поисковая строка адреса (как ввел пользователь)</param>
    /// <param name="limit">Максимальное количество результатов</param>
    /// <param name="requestId">ID запроса для логирования</param>
    /// <param name="cancellationToken">Токен отмены</param>
    /// <returns>Результаты поиска</returns>
    Task<SearchAddressResponse> SearchAddressAsync(
        string query,
        int limit,
        string requestId,
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Проверяет доступность geocode-service
    /// </summary>
    /// <returns>True если сервис доступен, иначе False</returns>
    Task<bool> CheckHealthAsync();
}
