using Api.Grpc.AddressParser;

namespace Api.Models.Normalization;

/// <summary>
/// Результат нормализации и парсинга адреса
/// </summary>
public class NormalizedAddressResult
{
    /// <summary>
    /// Нормализованная строка адреса
    /// </summary>
    public string NormalizedAddress { get; set; } = string.Empty;

    /// <summary>
    /// Структурированные компоненты адреса (результат libpostal)
    /// </summary>
    public AddressComponents? Components { get; set; }

    /// <summary>
    /// Успешно ли прошла нормализация
    /// </summary>
    public bool Success { get; set; }

    /// <summary>
    /// Сообщение об ошибке (если есть)
    /// </summary>
    public string? ErrorMessage { get; set; }
}
