using Api.Grpc.AddressParser;
using Grpc.Core;

namespace Api.Services.AddressParser;

/// <summary>
/// gRPC клиент для общения с сервисом парсинга адресов (libpostal)
/// </summary>
public class AddressParserClient : IAddressParserClient
{
    private readonly AddressParserService.AddressParserServiceClient _grpcClient;
    private readonly ILogger<AddressParserClient> _logger;

    public AddressParserClient(
        AddressParserService.AddressParserServiceClient grpcClient,
        ILogger<AddressParserClient> logger)
    {
        _grpcClient = grpcClient;
        _logger = logger;
    }

    /// <summary>
    /// Парсит адрес на компоненты
    /// </summary>
    public async Task<ParseAddressResponse> ParseAddressAsync(
        string address,
        string country = "RU",
        string language = "ru",
        string requestId = "",
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation(
                "Отправка запроса на парсинг адреса. Address: {Address}, Country: {Country}, RequestId: {RequestId}",
                address, country, requestId);

            var request = new ParseAddressRequest
            {
                Address = address,
                Country = country,
                Language = language,
                RequestId = requestId
            };

            // Устанавливаем таймаут и CancellationToken
            var deadline = DateTime.UtcNow.AddSeconds(30);
            var callOptions = new CallOptions(
                deadline: deadline,
                cancellationToken: cancellationToken);

            // Выполняем gRPC вызов
            var response = await _grpcClient.ParseAddressAsync(request, callOptions);

            _logger.LogInformation(
                "Получен ответ от Address Parser. StatusCode: {StatusCode}",
                response.Status.Code);

            return response;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.Cancelled)
        {
            _logger.LogInformation("Запрос на парсинг адреса был отменен. RequestId: {RequestId}", requestId);
            throw new OperationCanceledException("Запрос был отменен", ex);
        }
        catch (RpcException ex)
        {
            _logger.LogError(
                "Ошибка gRPC при вызове Address Parser. StatusCode: {StatusCode}, Detail: {Detail}",
                ex.StatusCode, ex.Status.Detail);

            return CreateErrorParseResponse(ex, address);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка при вызове Address Parser");

            return new ParseAddressResponse
            {
                Status = new Api.Grpc.AddressParser.ResponseStatus
                {
                    Code = Api.Grpc.AddressParser.StatusCode.InternalError,
                    Message = "Произошла неожиданная ошибка при парсинге адреса"
                },
                OriginalAddress = address,
                Components = new AddressComponents()
            };
        }
    }

    /// <summary>
    /// Нормализует адрес
    /// </summary>
    public async Task<NormalizeAddressResponse> NormalizeAddressAsync(
        string address,
        string country = "RU",
        string language = "ru",
        bool transliterate = false,
        bool lowercase = false,
        bool removePunctuation = false,
        string requestId = "",
        CancellationToken cancellationToken = default)
    {
        try
        {
            _logger.LogInformation(
                "Отправка запроса на нормализацию адреса. Address: {Address}, RequestId: {RequestId}",
                address, requestId);

            var request = new NormalizeAddressRequest
            {
                Address = address,
                Country = country,
                Language = language,
                RequestId = requestId,
                Options = new NormalizeOptions
                {
                    Transliterate = transliterate,
                    Lowercase = lowercase,
                    RemovePunctuation = removePunctuation
                }
            };

            var deadline = DateTime.UtcNow.AddSeconds(30);
            var callOptions = new CallOptions(
                deadline: deadline,
                cancellationToken: cancellationToken);

            var response = await _grpcClient.NormalizeAddressAsync(request, callOptions);

            _logger.LogInformation(
                "Получен ответ от Address Parser. StatusCode: {StatusCode}, Alternatives: {Count}",
                response.Status.Code, response.Alternatives.Count);

            return response;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.Cancelled)
        {
            _logger.LogInformation("Запрос на нормализацию адреса был отменен. RequestId: {RequestId}", requestId);
            throw new OperationCanceledException("Запрос был отменен", ex);
        }
        catch (RpcException ex)
        {
            _logger.LogError(
                "Ошибка gRPC при вызове Address Parser. StatusCode: {StatusCode}, Detail: {Detail}",
                ex.StatusCode, ex.Status.Detail);

            return CreateErrorNormalizeResponse(ex, address);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка при вызове Address Parser");

            return new NormalizeAddressResponse
            {
                Status = new Api.Grpc.AddressParser.ResponseStatus
                {
                    Code = Api.Grpc.AddressParser.StatusCode.InternalError,
                    Message = "Произошла неожиданная ошибка при нормализации адреса"
                },
                OriginalAddress = address,
                NormalizedAddress = address
            };
        }
    }

    /// <summary>
    /// Проверяет доступность сервиса через HealthCheck
    /// </summary>
    public async Task<bool> CheckHealthAsync()
    {
        try
        {
            var request = new HealthCheckRequest();
            var deadline = DateTime.UtcNow.AddSeconds(3);
            var callOptions = new CallOptions(deadline: deadline);

            var response = await _grpcClient.HealthCheckAsync(request, callOptions);

            var isHealthy = response.Status == Api.Grpc.AddressParser.HealthStatus.Healthy;

            _logger.LogDebug(
                "Health check Address Parser: {Status} (Version: {Version}, LibpostalVersion: {LibpostalVersion})",
                response.Status, response.Version, response.LibpostalVersion);

            return isHealthy;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.Unavailable)
        {
            _logger.LogWarning("Address Parser сервис недоступен");
            return false;
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.DeadlineExceeded)
        {
            _logger.LogWarning("Address Parser сервис не отвечает (timeout)");
            return false;
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Ошибка при проверке health check Address Parser");
            return false;
        }
    }

    // =========================================================================
    // Вспомогательные методы
    // =========================================================================

    private ParseAddressResponse CreateErrorParseResponse(RpcException ex, string address)
    {
        string userMessage = ex.StatusCode switch
        {
            global::Grpc.Core.StatusCode.Unavailable =>
                "Сервис парсинга адресов временно недоступен",
            global::Grpc.Core.StatusCode.DeadlineExceeded =>
                "Превышено время ожидания ответа от сервиса парсинга",
            global::Grpc.Core.StatusCode.Internal =>
                "Внутренняя ошибка сервиса парсинга адресов",
            _ =>
                "Ошибка при обращении к сервису парсинга адресов"
        };

        return new ParseAddressResponse
        {
            Status = new Api.Grpc.AddressParser.ResponseStatus
            {
                Code = Api.Grpc.AddressParser.StatusCode.ServiceUnavailable,
                Message = userMessage,
                Details = ex.Status.Detail
            },
            OriginalAddress = address,
            Components = new AddressComponents()
        };
    }

    private NormalizeAddressResponse CreateErrorNormalizeResponse(RpcException ex, string address)
    {
        string userMessage = ex.StatusCode switch
        {
            global::Grpc.Core.StatusCode.Unavailable =>
                "Сервис нормализации адресов временно недоступен",
            global::Grpc.Core.StatusCode.DeadlineExceeded =>
                "Превышено время ожидания ответа от сервиса нормализации",
            global::Grpc.Core.StatusCode.Internal =>
                "Внутренняя ошибка сервиса нормализации адресов",
            _ =>
                "Ошибка при обращении к сервису нормализации адресов"
        };

        return new NormalizeAddressResponse
        {
            Status = new Api.Grpc.AddressParser.ResponseStatus
            {
                Code = Api.Grpc.AddressParser.StatusCode.ServiceUnavailable,
                Message = userMessage,
                Details = ex.Status.Detail
            },
            OriginalAddress = address,
            NormalizedAddress = address
        };
    }
}
