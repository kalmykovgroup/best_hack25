namespace Api.Models.Common;

/// <summary>
/// Стандартная обертка для всех API ответов
/// </summary>
/// <typeparam name="T">Тип данных ответа</typeparam>
public class ApiResponse<T>
{
    /// <summary>
    /// Успешность выполнения запроса
    /// </summary>
    public bool Success { get; set; }

    /// <summary>
    /// Данные ответа (null если ошибка)
    /// </summary>
    public T? Data { get; set; }

    /// <summary>
    /// Сообщение об ошибке (null если успех)
    /// </summary>
    public string? ErrorMessage { get; set; }

    /// <summary>
    /// Код ошибки для клиентской обработки
    /// </summary>
    public string? ErrorCode { get; set; }

    /// <summary>
    /// Метаданные запроса
    /// </summary>
    public ResponseMetadata? Metadata { get; set; }

    /// <summary>
    /// Создать успешный ответ
    /// </summary>
    public static ApiResponse<T> Ok(T data, ResponseMetadata? metadata = null)
    {
        return new ApiResponse<T>
        {
            Success = true,
            Data = data,
            Metadata = metadata
        };
    }

    /// <summary>
    /// Создать ответ с ошибкой
    /// </summary>
    public static ApiResponse<T> Error(string errorMessage, string? errorCode = null, ResponseMetadata? metadata = null)
    {
        return new ApiResponse<T>
        {
            Success = false,
            ErrorMessage = errorMessage,
            ErrorCode = errorCode,
            Metadata = metadata
        };
    }
}

/// <summary>
/// Метаданные ответа
/// </summary>
public class ResponseMetadata
{
    /// <summary>
    /// ID запроса для трекинга
    /// </summary>
    public string RequestId { get; set; } = string.Empty;

    /// <summary>
    /// Время выполнения в миллисекундах
    /// </summary>
    public long ExecutionTimeMs { get; set; }

    /// <summary>
    /// Timestamp ответа
    /// </summary>
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;

    /// <summary>
    /// Был ли запрос отменен
    /// </summary>
    public bool WasCancelled { get; set; }
}
