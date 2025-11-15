using Api.Models.Normalization;

namespace Api.Services.Normalization;

/// <summary>
/// Интерфейс для нормализации и парсинга адресов через libpostal
/// </summary>
public interface IAddressNormalizer
{
    /// <summary>
    /// Парсит и нормализует строку адреса через Address Parser (libpostal)
    /// Возвращает нормализованную строку и структурированные компоненты
    /// </summary>
    /// <param name="rawAddress">Исходная строка адреса от пользователя</param>
    /// <returns>Результат нормализации с компонентами адреса</returns>
    Task<NormalizedAddressResult> NormalizeAndParseAsync(string rawAddress);

    /// <summary>
    /// Проверяет валидность адреса
    /// </summary>
    /// <param name="address">Строка адреса</param>
    /// <returns>true если адрес валиден</returns>
    bool IsValid(string address);
}
