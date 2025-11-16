namespace Api.Models.Geocode;

/// <summary>
/// Адресный объект
/// </summary>
public class AddressObject
{
    /// <summary>
    /// Наименование населенного пункта
    /// </summary>
    public string Locality { get; set; } = string.Empty;

    /// <summary>
    /// Наименование улицы
    /// </summary>
    public string Street { get; set; } = string.Empty;

    /// <summary>
    /// Номер дома
    /// </summary>
    public string Number { get; set; } = string.Empty;

    /// <summary>
    /// Долгота
    /// </summary>
    public double Lon { get; set; }

    /// <summary>
    /// Широта
    /// </summary>
    public double Lat { get; set; }

    /// <summary>
    /// Релевантность ответа (0-1, где 1 - точное совпадение)
    /// </summary>
    public double Score { get; set; }
}
