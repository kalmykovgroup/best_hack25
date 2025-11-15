using Api.Grpc.AddressParser;

namespace Api.Services.AddressParser;

/// <summary>
/// Интерфейс для gRPC клиента сервиса парсинга адресов (libpostal)
/// </summary>
public interface IAddressParserClient
{
    /// <summary>
    /// Парсит адрес на компоненты с использованием libpostal
    /// </summary>
    /// <param name="address">Строка адреса для парсинга</param>
    /// <param name="country">Код страны (ISO 3166-1 alpha-2, например "RU")</param>
    /// <param name="language">Язык адреса (ISO 639-1, например "ru")</param>
    /// <param name="requestId">ID запроса для трекинга</param>
    /// <param name="cancellationToken">Токен отмены</param>
    /// <returns>Результат парсинга адреса</returns>
    Task<ParseAddressResponse> ParseAddressAsync(
        string address,
        string country = "RU",
        string language = "ru",
        string requestId = "",
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Нормализует адрес (приводит к стандартному виду)
    /// </summary>
    /// <param name="address">Строка адреса для нормализации</param>
    /// <param name="country">Код страны</param>
    /// <param name="language">Язык адреса</param>
    /// <param name="transliterate">Транслитерировать в латиницу</param>
    /// <param name="lowercase">Привести к нижнему регистру</param>
    /// <param name="removePunctuation">Удалить знаки препинания</param>
    /// <param name="requestId">ID запроса</param>
    /// <param name="cancellationToken">Токен отмены</param>
    /// <returns>Нормализованный адрес и альтернативы</returns>
    Task<NormalizeAddressResponse> NormalizeAddressAsync(
        string address,
        string country = "RU",
        string language = "ru",
        bool transliterate = false,
        bool lowercase = false,
        bool removePunctuation = false,
        string requestId = "",
        CancellationToken cancellationToken = default);

    /// <summary>
    /// Проверяет доступность сервиса парсинга адресов
    /// </summary>
    /// <returns>True если сервис доступен, иначе False</returns>
    Task<bool> CheckHealthAsync();
}
