using System.Collections.Concurrent;

namespace Api.Services.RequestManagement;

/// <summary>
/// Менеджер для управления активными запросами с поддержкой отмены
/// </summary>
public class ActiveRequestsManager : IActiveRequestsManager, IDisposable
{
    private readonly ConcurrentDictionary<string, CancellationTokenSource> _activeRequests = new();
    private readonly ILogger<ActiveRequestsManager> _logger;

    public ActiveRequestsManager(ILogger<ActiveRequestsManager> logger)
    {
        _logger = logger;
    }

    public CancellationTokenSource CreateRequest(string requestId)
    {
        var cts = new CancellationTokenSource();

        if (_activeRequests.TryAdd(requestId, cts))
        {
            _logger.LogDebug("Создан запрос {RequestId}. Активных запросов: {Count}",
                requestId, _activeRequests.Count);
            return cts;
        }

        // Если запрос с таким ID уже существует, отменяем старый
        _logger.LogWarning("Запрос {RequestId} уже существует, отменяем старый", requestId);
        CancelRequest(requestId);

        // Создаем новый
        var newCts = new CancellationTokenSource();
        _activeRequests[requestId] = newCts;
        return newCts;
    }

    public bool CancelRequest(string requestId)
    {
        if (_activeRequests.TryRemove(requestId, out var cts))
        {
            _logger.LogInformation("Отменяем запрос {RequestId}", requestId);

            try
            {
                cts.Cancel();
                cts.Dispose();
                return true;
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ошибка при отмене запроса {RequestId}", requestId);
            }
        }

        return false;
    }

    public void CompleteRequest(string requestId)
    {
        if (_activeRequests.TryRemove(requestId, out var cts))
        {
            _logger.LogDebug("Завершен запрос {RequestId}. Активных запросов: {Count}",
                requestId, _activeRequests.Count);

            cts.Dispose();
        }
    }

    public bool IsRequestActive(string requestId)
    {
        return _activeRequests.ContainsKey(requestId);
    }

    public int GetActiveRequestsCount()
    {
        return _activeRequests.Count;
    }

    public void Dispose()
    {
        foreach (var kvp in _activeRequests)
        {
            try
            {
                kvp.Value.Cancel();
                kvp.Value.Dispose();
            }
            catch (Exception ex)
            {
                _logger.LogError(ex, "Ошибка при освобождении ресурсов для запроса {RequestId}", kvp.Key);
            }
        }

        _activeRequests.Clear();
    }
}
