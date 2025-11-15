using System.Diagnostics;
using Api.Models.Common;
using Api.Models.WebSocket;
using Api.Services.AddressParser;
using Api.Services.Normalization;
using Api.Services.RequestManagement;
using Api.Services.Search;
using Microsoft.AspNetCore.SignalR;

namespace Api.Hubs;

/// <summary>
/// SignalR Hub для обработки запросов геокодирования от React клиента
/// </summary>
public class GeocodeHub : Hub
{
    private readonly IPythonSearchClient _pythonSearchClient;
    private readonly IAddressParserClient _addressParserClient;
    private readonly IActiveRequestsManager _requestsManager;
    private readonly IAddressNormalizer _addressNormalizer;
    private readonly ILogger<GeocodeHub> _logger;

    public GeocodeHub(
        IPythonSearchClient pythonSearchClient,
        IAddressParserClient addressParserClient,
        IActiveRequestsManager requestsManager,
        IAddressNormalizer addressNormalizer,
        ILogger<GeocodeHub> logger)
    {
        _pythonSearchClient = pythonSearchClient;
        _addressParserClient = addressParserClient;
        _requestsManager = requestsManager;
        _addressNormalizer = addressNormalizer;
        _logger = logger;
    }

    /// <summary>
    /// Обрабатывает запрос на поиск адреса от клиента (с поддержкой отмены)
    /// </summary>
    /// <param name="request">Запрос с поисковой строкой</param>
    public async Task SearchAddress(GeocodeRequest request)
    {
        var connectionId = Context.ConnectionId;
        var requestId = request.RequestId;
        var stopwatch = Stopwatch.StartNew();

        _logger.LogInformation(
            "Получен запрос на поиск. ConnectionId: {ConnectionId}, RequestId: {RequestId}, Query: {Query}",
            connectionId, requestId, request.Query);

        // Создаем CancellationTokenSource для этого запроса
        var cts = _requestsManager.CreateRequest(requestId);

        try
        {
            // Отправляем прогресс: начало обработки
            await Clients.Caller.SendAsync("SearchProgress", new SearchProgress
            {
                RequestId = requestId,
                Status = "processing",
                Message = "Обработка запроса...",
                ProgressPercent = 10
            }, cts.Token);

            // Валидация запроса
            if (!_addressNormalizer.IsValid(request.Query))
            {
                var errorResponse = ApiResponse<SearchResultData>.Error(
                    "Поисковая строка некорректна",
                    "INVALID_QUERY",
                    new ResponseMetadata
                    {
                        RequestId = requestId,
                        ExecutionTimeMs = stopwatch.ElapsedMilliseconds,
                        WasCancelled = false
                    });

                await Clients.Caller.SendAsync("SearchCompleted", errorResponse, cts.Token);
                return;
            }

            // Парсинг и нормализация адреса через Address Parser (libpostal)
            await Clients.Caller.SendAsync("SearchProgress", new SearchProgress
            {
                RequestId = requestId,
                Status = "normalizing",
                Message = "Парсинг и нормализация адреса...",
                ProgressPercent = 25
            }, cts.Token);

            var normalizeResult = await _addressNormalizer.NormalizeAndParseAsync(request.Query);
            _logger.LogDebug(
                "Результат обработки адреса: Normalized={Normalized}, City={City}, Road={Road}, House={House}",
                normalizeResult.NormalizedAddress,
                normalizeResult.Components?.City,
                normalizeResult.Components?.Road,
                normalizeResult.Components?.HouseNumber);

            // Отправляем прогресс: отправка в Python сервис
            await Clients.Caller.SendAsync("SearchProgress", new SearchProgress
            {
                RequestId = requestId,
                Status = "searching",
                Message = "Поиск в базе данных...",
                ProgressPercent = 50
            }, cts.Token);

            // Вызов Python gRPC сервиса с CancellationToken и структурированными компонентами
            var grpcResponse = await _pythonSearchClient.SearchAddressAsync(
                normalizeResult.NormalizedAddress,
                request.Query, // Оригинальный запрос пользователя
                normalizeResult.Components, // 🆕 Структурированные компоненты из libpostal
                request.Limit,
                requestId,
                cts.Token);

            // Проверяем, не был ли запрос отменен
            if (cts.Token.IsCancellationRequested)
            {
                _logger.LogInformation("Запрос {RequestId} был отменен", requestId);
                return;
            }

            // Отправляем прогресс: обработка результатов
            await Clients.Caller.SendAsync("SearchProgress", new SearchProgress
            {
                RequestId = requestId,
                Status = "finalizing",
                Message = "Обработка результатов...",
                ProgressPercent = 90
            }, cts.Token);

            // Проверяем статус ответа от Python
            if (grpcResponse.Status.Code != Grpc.StatusCode.Ok)
            {
                var errorResponse = ApiResponse<SearchResultData>.Error(
                    grpcResponse.Status.Message,
                    grpcResponse.Status.Code.ToString(),
                    new ResponseMetadata
                    {
                        RequestId = requestId,
                        ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                    });

                await Clients.Caller.SendAsync("SearchCompleted", errorResponse, cts.Token);
                return;
            }

            // Преобразуем результаты gRPC в DTO для клиента
            var searchResultData = new SearchResultData
            {
                SearchedAddress = grpcResponse.SearchedAddress,
                TotalFound = grpcResponse.TotalFound,
                Objects = grpcResponse.Objects.Select(obj => new AddressObjectDto
                {
                    Locality = obj.Locality,
                    Street = obj.Street,
                    Number = obj.Number,
                    Lon = obj.Lon,
                    Lat = obj.Lat,
                    Score = obj.Score,
                    AdditionalInfo = obj.AdditionalInfo != null
                        ? new AddressAdditionalInfo
                        {
                            PostalCode = obj.AdditionalInfo.PostalCode,
                            District = obj.AdditionalInfo.District,
                            FullAddress = obj.AdditionalInfo.FullAddress,
                            ObjectId = obj.AdditionalInfo.ObjectId
                        }
                        : null
                }).ToList()
            };

            // Оборачиваем в ApiResponse
            var successResponse = ApiResponse<SearchResultData>.Ok(
                searchResultData,
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds,
                    WasCancelled = false
                });

            // Отправляем финальные результаты клиенту
            await Clients.Caller.SendAsync("SearchCompleted", successResponse, cts.Token);

            _logger.LogInformation(
                "Поиск завершен. RequestId: {RequestId}, Найдено: {Count}, Время: {Ms}ms",
                requestId, searchResultData.Objects.Count, stopwatch.ElapsedMilliseconds);
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("Запрос {RequestId} был отменен пользователем", requestId);

            var cancelledResponse = ApiResponse<SearchResultData>.Error(
                "Запрос был отменен",
                "CANCELLED",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds,
                    WasCancelled = true
                });

            await Clients.Caller.SendAsync("SearchCompleted", cancelledResponse);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Ошибка при обработке запроса {RequestId}", requestId);

            var errorResponse = ApiResponse<SearchResultData>.Error(
                $"Ошибка при выполнении поиска: {ex.Message}",
                "INTERNAL_ERROR",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                });

            await Clients.Caller.SendAsync("SearchCompleted", errorResponse);
        }
        finally
        {
            stopwatch.Stop();
            _requestsManager.CompleteRequest(requestId);
        }
    }

    /// <summary>
    /// Отменяет активный запрос по ID
    /// </summary>
    /// <param name="request">Запрос с ID для отмены</param>
    public Task CancelSearch(CancelSearchRequest request)
    {
        _logger.LogInformation("Получен запрос на отмену. RequestId: {RequestId}", request.RequestId);

        var cancelled = _requestsManager.CancelRequest(request.RequestId);

        if (cancelled)
        {
            _logger.LogInformation("Запрос {RequestId} успешно отменен", request.RequestId);
        }
        else
        {
            _logger.LogWarning("Запрос {RequestId} не найден или уже завершен", request.RequestId);
        }

        return Task.CompletedTask;
    }

    /// <summary>
    /// Проверяет статус подключения к Python gRPC сервису (геокодирование)
    /// </summary>
    /// <returns>True если Python сервис доступен, иначе False</returns>
    public async Task<bool> CheckPythonServiceStatus()
    {
        _logger.LogDebug("Проверка статуса Python сервиса от клиента {ConnectionId}", Context.ConnectionId);

        var isAvailable = await _pythonSearchClient.CheckHealthAsync();

        _logger.LogDebug("Статус Python сервиса: {Status}", isAvailable ? "Доступен" : "Недоступен");

        return isAvailable;
    }

    /// <summary>
    /// Проверяет статус подключения к Address Parser gRPC сервису (нормализация адресов)
    /// </summary>
    /// <returns>True если Address Parser сервис доступен, иначе False</returns>
    public async Task<bool> CheckAddressParserServiceStatus()
    {
        _logger.LogDebug("Проверка статуса Address Parser сервиса от клиента {ConnectionId}", Context.ConnectionId);

        var isAvailable = await _addressParserClient.CheckHealthAsync();

        _logger.LogDebug("Статус Address Parser сервиса: {Status}", isAvailable ? "Доступен" : "Недоступен");

        return isAvailable;
    }

    /// <summary>
    /// Вызывается при подключении клиента
    /// </summary>
    public override async Task OnConnectedAsync()
    {
        _logger.LogInformation("Клиент подключен: {ConnectionId}", Context.ConnectionId);
        await base.OnConnectedAsync();
    }

    /// <summary>
    /// Вызывается при отключении клиента
    /// </summary>
    public override async Task OnDisconnectedAsync(Exception? exception)
    {
        if (exception != null)
        {
            _logger.LogError(exception, "Клиент отключился с ошибкой: {ConnectionId}", Context.ConnectionId);
        }
        else
        {
            _logger.LogInformation("Клиент отключился: {ConnectionId}", Context.ConnectionId);
        }

        await base.OnDisconnectedAsync(exception);
    }
}
