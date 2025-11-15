namespace Api.Models.WebSocket;

/// <summary>
/// Запрос на геокодирование от клиента (React)
/// </summary>
public class GeocodeRequest
{
    /// <summary>
    /// Уникальный ID запроса для сопоставления запросов и ответов
    /// </summary>
    public string RequestId { get; set; } = Guid.NewGuid().ToString();

    /// <summary>
    /// Поисковая строка от пользователя
    /// </summary>
    public string Query { get; set; } = string.Empty;

    /// <summary>
    /// Максимальное количество результатов (по умолчанию 10)
    /// </summary>
    public int Limit { get; set; } = 10;
}
