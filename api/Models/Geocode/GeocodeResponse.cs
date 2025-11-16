namespace Api.Models.Geocode;

/// <summary>
/// Формат ответа для геокодирования
/// </summary>
public class GeocodeResponse
{
    /// <summary>
    /// Запрашиваемый адрес
    /// </summary>
    public string SearchedAddress { get; set; } = string.Empty;

    /// <summary>
    /// Найденные объекты
    /// </summary>
    public List<AddressObject> Objects { get; set; } = new();
}
