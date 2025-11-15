# BEST HACK

Система поиска и геокодирования адресов с real-time коммуникацией.

## Требования

- Docker и Docker Compose
- Node.js 18+ (для разработки фронтенда)
- .NET 9.0 SDK (для разработки API)

## Быстрый старт

1. **Клонирование репозитория:**
```bash
git clone <repository-url>
cd best_hack25
```

2. **Запуск всех сервисов:**
```bash
docker compose up -d
```

3. **Открыть приложение:**
   - Фронтенд: http://localhost:5174
   - API: http://localhost:5034

## Структура проекта

- `api/` - ASP.NET Core API с SignalR
- `react-app/` - React + TypeScript фронтенд
- `python-search/` - Python сервис геокодирования
- `address-parser/` - Сервис парсинга адресов

## Использование

1. Откройте http://localhost:5174 в браузере
2. Введите адрес в поле поиска
3. Результаты появятся автоматически
4. Нажмите на результат для выбора

## Разработка

### Запуск React приложения:
```bash
cd react-app
npm install
npm run dev
```

### Запуск .NET API:
```bash
cd api
dotnet run
```

### Просмотр логов Docker:
```bash
docker compose logs -f
```

## Технологии

- **Frontend:** React 18, TypeScript, Redux Toolkit, SignalR Client
- **Backend:** ASP.NET Core 9.0, SignalR, gRPC
- **Services:** Python 3.11, gRPC, libpostal
- **Infrastructure:** Docker, Docker Compose

## Основные возможности

- Real-time поиск через WebSocket (SignalR)
- Кэширование результатов поиска
- Автоматическое переподключение
- Геокодирование адресов
- Парсинг и нормализация адресов

## Порты

| Сервис           | Порт  | Описание                    |
|------------------|-------|-----------------------------|
| React Frontend   | 5174  | Веб-интерфейс               |
| .NET API         | 5034  | REST API + SignalR Hub      |
| Python Search    | 50051 | gRPC сервис геокодирования  |
| Address Parser   | 50052 | gRPC сервис парсинга        |

## Лицензия

Проект разработан в рамках хакатона BEST HACK 2025.
