using Api.Grpc;
using Api.Hubs;
using Api.Services.RequestManagement;
using Api.Services.Search;

namespace api;

public class Program
{
    public static async Task Main(string[] args)
    {
        var builder = WebApplication.CreateBuilder(args);

        // Add services to the container.
        builder.Services.AddControllers();
        builder.Services.AddAuthorization();

        // Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
        builder.Services.AddOpenApi();

        // Настройка CORS для React приложения
        var allowedOrigins = builder.Configuration.GetValue<string>("ALLOWED_ORIGINS")
            ?? "http://localhost:5175,http://localhost:5174,http://localhost:3000";

        builder.Services.AddCors(options =>
        {
            options.AddPolicy("ReactApp", policy =>
            {
                policy.WithOrigins(allowedOrigins.Split(',', StringSplitOptions.RemoveEmptyEntries))
                    .AllowAnyHeader()
                    .AllowAnyMethod()
                    .AllowCredentials(); // Важно для SignalR
            });
        });

        // Настройка SignalR
        var enableDetailedErrors = builder.Configuration.GetValue<bool?>("SIGNALR_ENABLE_DETAILED_ERRORS")
            ?? builder.Environment.IsDevelopment();
        var maxMessageSize = builder.Configuration.GetValue<int?>("SIGNALR_MAX_MESSAGE_SIZE") ?? 102400;

        builder.Services.AddSignalR(options =>
        {
            options.EnableDetailedErrors = enableDetailedErrors;
            options.MaximumReceiveMessageSize = maxMessageSize; // 100KB
        });

        // Настройка gRPC клиента для Geocode сервиса (python-search с BM25 + встроенным libpostal)
        var pythonServiceUrl = builder.Configuration.GetValue<string>("PYTHON_SERVICE_URL")
                               ?? "http://localhost:50054";

        builder.Services.AddGrpcClient<GeocodeService.GeocodeServiceClient>(options =>
        {
            options.Address = new Uri(pythonServiceUrl);
        })
        .ConfigurePrimaryHttpMessageHandler(() =>
        {
            // Настройка HTTP/2 для gRPC
            var handler = new HttpClientHandler();

            // В dev режиме разрешаем самоподписанные сертификаты
            if (builder.Environment.IsDevelopment())
            {
                handler.ServerCertificateCustomValidationCallback =
                    HttpClientHandler.DangerousAcceptAnyServerCertificateValidator;
            }

            return handler;
        });

        // Регистрация сервисов
        builder.Services.AddScoped<IPythonSearchClient, PythonSearchClient>();
        builder.Services.AddSingleton<IActiveRequestsManager, ActiveRequestsManager>();

        var app = builder.Build();

        // Проверка подключения к микросервисам при старте
        await CheckMicroservicesHealthAsync(app);

        // Configure the HTTP request pipeline.
        if (app.Environment.IsDevelopment())
        {
            app.MapOpenApi();
        }

        // HTTPS редирект только в production
        if (!app.Environment.IsDevelopment())
        {
            app.UseHttpsRedirection();
        }

        // Применяем CORS перед авторизацией
        app.UseCors("ReactApp");

        // Поддержка статических файлов (React приложение)
        app.UseDefaultFiles(); // Ищет index.html
        app.UseStaticFiles();  // Обслуживает файлы из wwwroot

        app.UseAuthorization();

        // Маппинг Controllers
        app.MapControllers();

        // Маппинг SignalR Hub
        app.MapHub<GeocodeHub>("/hubs/geocode");

        // Health check endpoint
        app.MapGet("/health", () => Results.Ok(new { status = "healthy", timestamp = DateTime.UtcNow }))
            .WithName("HealthCheck");

        // SPA Fallback - все не-API запросы возвращают index.html (для React Router)
        app.MapFallbackToFile("index.html");

        app.Run();
    }

    /// <summary>
    /// Проверяет подключение к микросервисам при старте приложения
    /// </summary>
    private static async Task CheckMicroservicesHealthAsync(WebApplication app)
    {
        var logger = app.Services.GetRequiredService<ILogger<Program>>();

        logger.LogInformation("╔═══════════════════════════════════════════════════════════════════╗");
        logger.LogInformation("║  🔍 ПРОВЕРКА ПОДКЛЮЧЕНИЯ К МИКРОСЕРВИСАМ                         ║");
        logger.LogInformation("╚═══════════════════════════════════════════════════════════════════╝");

        using var scope = app.Services.CreateScope();

        // Проверка Geocode Service (python-search с BM25 + встроенным libpostal)
        try
        {
            var pythonClient = scope.ServiceProvider.GetRequiredService<IPythonSearchClient>();
            var isPythonHealthy = await pythonClient.CheckHealthAsync();

            if (isPythonHealthy)
            {
                logger.LogInformation("✅ Geocode Service (порт 50054):    ПОДКЛЮЧЕН");
                logger.LogInformation("    (BM25 поиск + встроенный libpostal)");
            }
            else
            {
                logger.LogWarning("⚠️  Geocode Service (порт 50054):    НЕДОСТУПЕН");
                logger.LogWarning("    Проверьте, что сервис запущен: docker-compose up geocode-service");
            }
        }
        catch (Exception ex)
        {
            logger.LogError("❌ Geocode Service (порт 50054):    ОШИБКА ПОДКЛЮЧЕНИЯ");
            logger.LogError("    {Message}", ex.Message);
        }

        logger.LogInformation("═══════════════════════════════════════════════════════════════════");
        logger.LogInformation("");
    }
}