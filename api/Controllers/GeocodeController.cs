using System.Diagnostics;
using System.Text.Json;
using Api.Models.Common;
using Api.Models.WebSocket;
using Api.Services.Normalization;
using Api.Services.RequestManagement;
using Api.Services.Search;
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
    private readonly IAddressNormalizer _addressNormalizer;
    private readonly ILogger<GeocodeController> _logger;

    public GeocodeController(
        IPythonSearchClient pythonSearchClient,
        IActiveRequestsManager requestsManager,
        IAddressNormalizer addressNormalizer,
        ILogger<GeocodeController> logger)
    {
        _pythonSearchClient = pythonSearchClient;
        _requestsManager = requestsManager;
        _addressNormalizer = addressNormalizer;
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

            if (!_addressNormalizer.IsValid(query))
            {
                var errorResponse = ApiResponse<SearchResultData>.Error(
                    "Поисковая строка некорректна",
                    "INVALID_QUERY",
                    new ResponseMetadata
                    {
                        RequestId = requestId,
                        ExecutionTimeMs = stopwatch.ElapsedMilliseconds
                    });

                await SendSseEvent("completed", errorResponse);
                return;
            }

            // Парсинг и нормализация через Address Parser
            await SendSseEvent("progress", new SearchProgress
            {
                RequestId = requestId,
                Status = "normalizing",
                Message = "Парсинг и нормализация адреса...",
                ProgressPercent = 25
            });

            var normalizeResult = await _addressNormalizer.NormalizeAndParseAsync(query);

            // Прогресс: поиск
            await SendSseEvent("progress", new SearchProgress
            {
                RequestId = requestId,
                Status = "searching",
                Message = "Поиск в базе данных...",
                ProgressPercent = 50
            });

            // Вызов Python gRPC сервиса с компонентами
            var grpcResponse = await _pythonSearchClient.SearchAddressAsync(
                normalizeResult.NormalizedAddress,
                query, // Оригинальный запрос пользователя
                normalizeResult.Components, // Структурированные компоненты
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

            // Проверяем статус ответа
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

                await SendSseEvent("completed", errorResponse);
                return;
            }

            // Преобразуем в DTO
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
        catch (Exception ex)
        {
            _logger.LogError(ex, "Ошибка в SSE потоке. RequestId: {RequestId}", requestId);

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
