using System.Diagnostics;
using Api.Models.Common;
using Api.Models.WebSocket;
using Api.Services.RequestManagement;
using Api.Services.Search;
using Grpc.Core;
using Microsoft.AspNetCore.SignalR;

namespace Api.Hubs;

/// <summary>
/// SignalR Hub для обработки запросов геокодирования от React клиента
/// </summary>
public class GeocodeHub : Hub
{
    private readonly IPythonSearchClient _pythonSearchClient;
    private readonly IActiveRequestsManager _requestsManager;
    private readonly ILogger<GeocodeHub> _logger;

    public GeocodeHub(
        IPythonSearchClient pythonSearchClient,
        IActiveRequestsManager requestsManager,
        ILogger<GeocodeHub> logger)
    {
        _pythonSearchClient = pythonSearchClient;
        _requestsManager = requestsManager;
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

            // Простая валидация запроса
            if (string.IsNullOrWhiteSpace(request.Query))
            {
                var errorResponse = ApiResponse<SearchResultData>.Error(
                    "Поисковая строка пустая",
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

            // Отправляем прогресс: отправка в геокодер (встроенная нормализация + поиск)
            await Clients.Caller.SendAsync("SearchProgress", new SearchProgress
            {
                RequestId = requestId,
                Status = "searching",
                Message = "Поиск адреса...",
                ProgressPercent = 30
            }, cts.Token);

            // Прямой вызов geocode-service
            // Сервис сам выполняет нормализацию через встроенный libpostal + BM25 поиск
            var grpcResponse = await _pythonSearchClient.SearchAddressAsync(
                request.Query,
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

            // Преобразуем результаты gRPC в DTO для клиента (даже если результатов нет)
            var searchResultData = new SearchResultData
            {
                SearchedAddress = grpcResponse.SearchedAddress ?? request.Query,
                TotalFound = grpcResponse.Objects?.Count ?? 0,
                Objects = grpcResponse.Objects?.Select(obj => new AddressObjectDto
                {
                    Locality = obj.Locality,
                    Street = obj.Street,
                    Number = obj.Number,
                    Lon = obj.Lon,
                    Lat = obj.Lat,
                    Score = obj.Score,
                    AdditionalInfo = obj.Tags?.Count > 0 ? new AddressAdditionalInfo
                    {
                        Tags = obj.Tags.ToDictionary(kvp => kvp.Key, kvp => kvp.Value)
                    } : null
                }).ToList() ?? new List<AddressObjectDto>()
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
        catch (RpcException ex) when (ex.StatusCode == StatusCode.Unavailable)
        {
            _logger.LogWarning("geocode-service недоступен для запроса {RequestId}", requestId);

            var serviceUnavailableResponse = ApiResponse<SearchResultData>.Error(
                "Сервис геокодирования временно недоступен. Пожалуйста, подождите...",
                "SERVICE_UNAVAILABLE",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                });

            await Clients.Caller.SendAsync("SearchCompleted", serviceUnavailableResponse);
        }
        catch (RpcException ex) when (ex.StatusCode == StatusCode.DeadlineExceeded)
        {
            _logger.LogWarning("Таймаут при вызове geocode-service для запроса {RequestId}", requestId);

            var timeoutResponse = ApiResponse<SearchResultData>.Error(
                "Превышено время ожидания ответа от сервиса геокодирования",
                "TIMEOUT",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                });

            await Clients.Caller.SendAsync("SearchCompleted", timeoutResponse);
        }
        catch (RpcException ex)
        {
            _logger.LogError(ex, "Ошибка gRPC при обработке запроса {RequestId}: {StatusCode}", requestId, ex.StatusCode);

            var grpcErrorResponse = ApiResponse<SearchResultData>.Error(
                $"Ошибка при обращении к сервису геокодирования: {ex.Status.Detail}",
                "GRPC_ERROR",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                });

            await Clients.Caller.SendAsync("SearchCompleted", grpcErrorResponse);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка при обработке запроса {RequestId}", requestId);

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
    /// Проверяет статус Address Parser (не используется, geocode-service делает нормализацию сам)
    /// </summary>
    /// <returns>Всегда возвращает true (заглушка для совместимости с клиентом)</returns>
    public Task<bool> CheckAddressParserServiceStatus()
    {
        _logger.LogDebug("Проверка статуса Address Parser от клиента {ConnectionId} (заглушка)", Context.ConnectionId);

        // Address Parser не используется - geocode-service сам выполняет нормализацию
        // Возвращаем true чтобы клиент не показывал ошибку
        return Task.FromResult(true);
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
