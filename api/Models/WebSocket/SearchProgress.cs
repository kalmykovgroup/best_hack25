namespace Api.Models.WebSocket;

/// <summary>
/// Прогресс выполнения поиска (для отправки промежуточных обновлений)
/// </summary>
public class SearchProgress
{
    /// <summary>
    /// ID запроса, к которому относится этот прогресс
    /// </summary>
    public string RequestId { get; set; } = string.Empty;

    /// <summary>
    /// Статус выполнения
    /// </summary>
    public string Status { get; set; } = string.Empty;

    /// <summary>
    /// Сообщение о текущем этапе
    /// </summary>
    public string Message { get; set; } = string.Empty;

    /// <summary>
    /// Прогресс в процентах (0-100)
    /// </summary>
    public int ProgressPercent { get; set; }
}
