namespace Api.Models.WebSocket;

/// <summary>
/// Запрос на отмену текущего поиска
/// </summary>
public class CancelSearchRequest
{
    /// <summary>
    /// ID запроса, который нужно отменить
    /// </summary>
    public string RequestId { get; set; } = string.Empty;
}
