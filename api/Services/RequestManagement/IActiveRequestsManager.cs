namespace Api.Services.RequestManagement;

/// <summary>
/// Интерфейс для управления активными запросами (отмена, трекинг)
/// </summary>
public interface IActiveRequestsManager
{
    /// <summary>
    /// Создает новый CancellationTokenSource для запроса
    /// </summary>
    CancellationTokenSource CreateRequest(string requestId);

    /// <summary>
    /// Отменяет запрос по ID
    /// </summary>
    bool CancelRequest(string requestId);

    /// <summary>
    /// Завершает запрос и удаляет его из активных
    /// </summary>
    void CompleteRequest(string requestId);

    /// <summary>
    /// Проверяет, активен ли запрос
    /// </summary>
    bool IsRequestActive(string requestId);

    /// <summary>
    /// Получает количество активных запросов
    /// </summary>
    int GetActiveRequestsCount();
}
