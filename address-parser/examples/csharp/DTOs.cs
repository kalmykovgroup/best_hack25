// DTOs для работы с Address Parser сервисом

namespace Api.Models.AddressParser;

/// <summary>
/// DTO для запроса парсинга адреса
/// </summary>
public class ParseAddressDto
{
    /// <summary>
    /// Строка адреса для парсинга
    /// </summary>
    public string Address { get; set; } = string.Empty;

    /// <summary>
    /// Код страны (ISO 3166-1 alpha-2, например "RU", "US")
    /// </summary>
    public string? Country { get; set; }

    /// <summary>
    /// Язык адреса (ISO 639-1, например "ru", "en")
    /// </summary>
    public string? Language { get; set; }
}

/// <summary>
/// DTO для ответа парсинга адреса
/// </summary>
public class ParseAddressResultDto
{
    /// <summary>
    /// Исходный адрес
    /// </summary>
    public string OriginalAddress { get; set; } = string.Empty;

    /// <summary>
    /// Распарсенные компоненты
    /// </summary>
    public AddressComponentsDto Components { get; set; } = new();

    /// <summary>
    /// Время выполнения в миллисекундах
    /// </summary>
    public long ExecutionTimeMs { get; set; }
}

/// <summary>
/// Компоненты адреса
/// </summary>
public class AddressComponentsDto
{
    /// <summary>
    /// Номер дома
    /// </summary>
    public string? HouseNumber { get; set; }

    /// <summary>
    /// Улица
    /// </summary>
    public string? Road { get; set; }

    /// <summary>
    /// Квартира/офис
    /// </summary>
    public string? Unit { get; set; }

    /// <summary>
    /// Этаж
    /// </summary>
    public string? Level { get; set; }

    /// <summary>
    /// Подъезд
    /// </summary>
    public string? Staircase { get; set; }

    /// <summary>
    /// Вход
    /// </summary>
    public string? Entrance { get; set; }

    /// <summary>
    /// Почтовый индекс
    /// </summary>
    public string? Postcode { get; set; }

    /// <summary>
    /// Район/микрорайон
    /// </summary>
    public string? Suburb { get; set; }

    /// <summary>
    /// Город
    /// </summary>
    public string? City { get; set; }

    /// <summary>
    /// Округ города
    /// </summary>
    public string? CityDistrict { get; set; }

    /// <summary>
    /// Регион/область
    /// </summary>
    public string? State { get; set; }

    /// <summary>
    /// Страна
    /// </summary>
    public string? Country { get; set; }
}

/// <summary>
/// DTO для запроса нормализации адреса
/// </summary>
public class NormalizeAddressDto
{
    /// <summary>
    /// Строка адреса для нормализации
    /// </summary>
    public string Address { get; set; } = string.Empty;

    /// <summary>
    /// Код страны (ISO 3166-1 alpha-2)
    /// </summary>
    public string? Country { get; set; }

    /// <summary>
    /// Язык адреса (ISO 639-1)
    /// </summary>
    public string? Language { get; set; }

    /// <summary>
    /// Транслитерировать в латиницу
    /// </summary>
    public bool? Transliterate { get; set; }

    /// <summary>
    /// Привести к нижнему регистру
    /// </summary>
    public bool? Lowercase { get; set; }

    /// <summary>
    /// Удалить знаки препинания
    /// </summary>
    public bool? RemovePunctuation { get; set; }
}

/// <summary>
/// DTO для ответа нормализации адреса
/// </summary>
public class NormalizeAddressResultDto
{
    /// <summary>
    /// Исходный адрес
    /// </summary>
    public string OriginalAddress { get; set; } = string.Empty;

    /// <summary>
    /// Нормализованный адрес
    /// </summary>
    public string NormalizedAddress { get; set; } = string.Empty;

    /// <summary>
    /// Альтернативные варианты нормализации
    /// </summary>
    public List<string> Alternatives { get; set; } = new();

    /// <summary>
    /// Время выполнения в миллисекундах
    /// </summary>
    public long ExecutionTimeMs { get; set; }
}
