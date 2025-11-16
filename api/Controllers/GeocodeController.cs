using System.Diagnostics;
using System.Text.Json;
using Api.Models.Common;
using Api.Models.WebSocket;
using Api.Services.RequestManagement;
using Api.Services.Search;
using Grpc.Core;
using Microsoft.AspNetCore.Mvc;

namespace Api.Controllers;

/// <summary>
/// REST/SSE контроллер для геокодирования (альтернатива SignalR)
/// </summary>
[ApiController]
[Route("api/[controller]")]
public class GeocodeController : ControllerBase
{
    private readonly IPythonSearchClient _pythonSearchClient;
    private readonly IActiveRequestsManager _requestsManager;
    private readonly ILogger<GeocodeController> _logger;

    public GeocodeController(
        IPythonSearchClient pythonSearchClient,
        IActiveRequestsManager requestsManager,
        ILogger<GeocodeController> logger)
    {
        _pythonSearchClient = pythonSearchClient;
        _requestsManager = requestsManager;
        _logger = logger;
    }

    /// <summary>
    /// SSE endpoint для получения результатов поиска в реальном времени
    /// Использует Server-Sent Events для потоковой передачи данных
    /// </summary>
    /// <param name="query">Поисковая строка</param>
    /// <param name="limit">Максимальное количество результатов</param>
    /// <param name="requestId">Уникальный ID запроса</param>
    [HttpGet("stream")]
    [Produces("text/event-stream")]
    public async Task StreamSearch(
        [FromQuery] string query,
        [FromQuery] int limit = 10,
        [FromQuery] string? requestId = null)
    {
        requestId ??= Guid.NewGuid().ToString();
        var stopwatch = Stopwatch.StartNew();

        // Настройка SSE
        Response.Headers.Append("Content-Type", "text/event-stream");
        Response.Headers.Append("Cache-Control", "no-cache");
        Response.Headers.Append("Connection", "keep-alive");

        _logger.LogInformation(
            "SSE поток открыт. RequestId: {RequestId}, Query: {Query}",
            requestId, query);

        // Создаем CancellationToken для этого запроса
        var cts = _requestsManager.CreateRequest(requestId);

        try
        {
            // Отправляем прогресс: начало
            await SendSseEvent("progress", new SearchProgress
            {
                RequestId = requestId,
                Status = "processing",
                Message = "Обработка запроса...",
                ProgressPercent = 10
            });

            // Простая валидация запроса
            if (string.IsNullOrWhiteSpace(query))
            {
                var errorResponse = ApiResponse<SearchResultData>.Error(
                    "Поисковая строка пустая",
                    "INVALID_QUERY",
                    new ResponseMetadata
                    {
                        RequestId = requestId,
                        ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                    });

                await SendSseEvent("completed", errorResponse);
                return;
            }

            // Прогресс: поиск (geocode-service сам выполняет нормализацию + поиск)
            await SendSseEvent("progress", new SearchProgress
            {
                RequestId = requestId,
                Status = "searching",
                Message = "Поиск адреса...",
                ProgressPercent = 30
            });

            // Прямой вызов geocode-service (встроенная нормализация + BM25 поиск)
            var grpcResponse = await _pythonSearchClient.SearchAddressAsync(
                query,
                limit,
                requestId,
                cts.Token);

            if (cts.Token.IsCancellationRequested)
            {
                _logger.LogInformation("SSE поток отменен. RequestId: {RequestId}", requestId);
                return;
            }

            // Прогресс: финализация
            await SendSseEvent("progress", new SearchProgress
            {
                RequestId = requestId,
                Status = "finalizing",
                Message = "Обработка результатов...",
                ProgressPercent = 90
            });

            // Проверяем, есть ли результаты (нет Status в новом контракте)
            if (grpcResponse.Objects == null || grpcResponse.Objects.Count == 0)
            {
                var notFoundResponse = ApiResponse<SearchResultData>.Error(
                    "Адрес не найден",
                    "NOT_FOUND",
                    new ResponseMetadata
                    {
                        RequestId = requestId,
                        ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                    });

                await SendSseEvent("completed", notFoundResponse);
                return;
            }

            // Преобразуем в DTO
            var searchResultData = new SearchResultData
            {
                SearchedAddress = grpcResponse.SearchedAddress,
                TotalFound = grpcResponse.Metadata?.TotalFound ?? grpcResponse.Objects.Count,
                Objects = grpcResponse.Objects.Select(obj => new AddressObjectDto
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
                }).ToList()
            };

            // Оборачиваем в ApiResponse
            var successResponse = ApiResponse<SearchResultData>.Ok(
                searchResultData,
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                });

            await SendSseEvent("completed", successResponse);

            _logger.LogInformation(
                "SSE поток завершен. RequestId: {RequestId}, Результатов: {Count}, Время: {Ms}ms",
                requestId, searchResultData.Objects.Count, stopwatch.ElapsedMilliseconds);
        }
        catch (OperationCanceledException)
        {
            _logger.LogInformation("SSE поток отменен пользователем. RequestId: {RequestId}", requestId);

            var cancelledResponse = ApiResponse<SearchResultData>.Error(
                "Запрос был отменен",
                "CANCELLED",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds,
                    WasCancelled = true
                });

            await SendSseEvent("completed", cancelledResponse);
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.Unavailable)
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

            await SendSseEvent("completed", serviceUnavailableResponse);
        }
        catch (RpcException ex) when (ex.StatusCode == global::Grpc.Core.StatusCode.DeadlineExceeded)
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

            await SendSseEvent("completed", timeoutResponse);
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

            await SendSseEvent("completed", grpcErrorResponse);
        }
        catch (Exception ex)
        {
            _logger.LogError(ex, "Неожиданная ошибка в SSE потоке. RequestId: {RequestId}", requestId);

            var errorResponse = ApiResponse<SearchResultData>.Error(
                $"Ошибка: {ex.Message}",
                "INTERNAL_ERROR",
                new ResponseMetadata
                {
                    RequestId = requestId,
                    ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                });

            await SendSseEvent("completed", errorResponse);
        }
        finally
        {
            stopwatch.Stop();
            _requestsManager.CompleteRequest(requestId);
        }
    }

    /// <summary>
    /// REST endpoint для отмены активного запроса
    /// </summary>
    [HttpPost("cancel/{requestId}")]
    public IActionResult CancelSearch(string requestId)
    {
        _logger.LogInformation("Запрос на отмену. RequestId: {RequestId}", requestId);

        var cancelled = _requestsManager.CancelRequest(requestId);

        if (cancelled)
        {
            return Ok(new { success = true, message = "Запрос отменен" });
        }

        return NotFound(new { success = false, message = "Запрос не найден или уже завершен" });
    }

    /// <summary>
    /// Вспомогательный метод для отправки SSE событий
    /// </summary>
    private async Task SendSseEvent<T>(string eventType, T data)
    {
        var json = JsonSerializer.Serialize(data, new JsonSerializerOptions
        {
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase
        });

        await Response.WriteAsync($"event: {eventType}\n");
        await Response.WriteAsync($"data: {json}\n\n");
        await Response.Body.FlushAsync();
    }
}
