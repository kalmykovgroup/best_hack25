namespace Api.Models.WebSocket;

/// <summary>
/// Адресный объект (результат поиска) для клиента
/// </summary>
public class AddressObjectDto
{
    /// <summary>
    /// Наименование населенного пункта (город, село и т.д.)
    /// </summary>
    public string Locality { get; set; } = string.Empty;

    /// <summary>
    /// Наименование улицы
    /// </summary>
    public string Street { get; set; } = string.Empty;

    /// <summary>
    /// Номер дома (может содержать корпус, строение: "10к2с1")
    /// </summary>
    public string Number { get; set; } = string.Empty;

    /// <summary>
    /// Долгота (longitude)
    /// </summary>
    public double Lon { get; set; }

    /// <summary>
    /// Широта (latitude)
    /// </summary>
    public double Lat { get; set; }

    /// <summary>
    /// Оценка релевантности результата (0-1, где 1 - точное совпадение)
    /// </summary>
    public double Score { get; set; }

    /// <summary>
    /// Дополнительная информация (опционально)
    /// </summary>
    public AddressAdditionalInfo? AdditionalInfo { get; set; }
}

/// <summary>
/// Дополнительная информация об адресе
/// </summary>
public class AddressAdditionalInfo
{
    /// <summary>
    /// Почтовый индекс
    /// </summary>
    public string? PostalCode { get; set; }

    /// <summary>
    /// Район города
    /// </summary>
    public string? District { get; set; }

    /// <summary>
    /// Полный отформатированный адрес
    /// </summary>
    public string? FullAddress { get; set; }

    /// <summary>
    /// Уникальный идентификатор объекта в БД
    /// </summary>
    public string? ObjectId { get; set; }
}
