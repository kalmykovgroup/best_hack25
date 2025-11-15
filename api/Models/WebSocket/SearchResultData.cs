namespace Api.Models.WebSocket;

/// <summary>
/// Данные ответа с результатами геокодирования
/// (будет обернут в ApiResponse<SearchResultData>)
/// </summary>
public class SearchResultData
{
    /// <summary>
    /// Строка, по которой производился поиск (нормализованная)
    /// </summary>
    public string SearchedAddress { get; set; } = string.Empty;

    /// <summary>
    /// Найденные адресные объекты
    /// </summary>
    public List<AddressObjectDto> Objects { get; set; } = new();

    /// <summary>
    /// Общее количество найденных результатов (может быть больше чем objects.length)
    /// </summary>
    public int TotalFound { get; set; }
}
