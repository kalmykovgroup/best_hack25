#!/bin/bash
# =============================================================================
# SSL Certificate Setup Script
# =============================================================================
# Этот скрипт автоматически получает SSL сертификат от Let's Encrypt
# и настраивает nginx для работы с HTTPS

set -e

# Загружаем переменные из .env
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "ERROR: .env file not found!"
    exit 1
fi

# Проверяем обязательные переменные
if [ -z "$DOMAIN" ] || [ -z "$SSL_EMAIL" ]; then
    echo "ERROR: DOMAIN и SSL_EMAIL должны быть установлены в .env файле"
    exit 1
fi

echo "============================================================================="
echo "SSL Certificate Setup для $DOMAIN"
echo "============================================================================="
echo "Email: $SSL_EMAIL"
echo "Staging: ${CERTBOT_STAGING:-1}"
echo ""

# Создаем необходимые директории
echo "→ Создание директорий..."
mkdir -p ./certbot/www
mkdir -p ./certbot/conf

# Запускаем nginx и certbot
echo "→ Запуск nginx..."
docker-compose up -d nginx

# Ждем запуска nginx
echo "→ Ожидание запуска nginx..."
sleep 5

# Формируем команду certbot
CERTBOT_CMD="certbot certonly --webroot --webroot-path=/var/www/certbot \
    --email $SSL_EMAIL \
    --agree-tos \
    --no-eff-email \
    -d $DOMAIN -d www.$DOMAIN"

# Добавляем staging флаг если нужно
if [ "${CERTBOT_STAGING:-1}" == "1" ]; then
    CERTBOT_CMD="$CERTBOT_CMD --staging"
    echo "→ ВНИМАНИЕ: Используется STAGING режим (тестовый сертификат)"
    echo "→ Для production сертификата установите CERTBOT_STAGING=0 в .env"
fi

# Получаем сертификат
echo "→ Получение SSL сертификата..."
docker-compose run --rm certbot $CERTBOT_CMD

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Сертификат успешно получен!"
    echo ""
    echo "→ Обновление конфигурации nginx..."
    
    # Раскомментируем HTTPS блок в nginx конфиге
    sed -i 's/^# server {/server {/g' ./nginx/conf.d/default.conf
    sed -i 's/^#     /    /g' ./nginx/conf.d/default.conf
    sed -i 's/^# }/}/g' ./nginx/conf.d/default.conf
    
    # Заменяем проксирование на HTTP редирект
    sed -i '/# Временно проксируем всё на API/,/^    }$/c\    # Редирект на HTTPS\n    location / {\n        return 301 https://$host$request_uri;\n    }' ./nginx/conf.d/default.conf
    
    # Перезагружаем nginx
    echo "→ Перезагрузка nginx..."
    docker-compose exec nginx nginx -t && docker-compose exec nginx nginx -s reload
    
    echo ""
    echo "============================================================================="
    echo "✅ SSL НАСТРОЕН УСПЕШНО!"
    echo "============================================================================="
    echo ""
    echo "Ваш сайт теперь доступен по HTTPS:"
    echo "  https://$DOMAIN"
    echo "  https://www.$DOMAIN"
    echo ""
    
    if [ "${CERTBOT_STAGING:-1}" == "1" ]; then
        echo "⚠️  ВНИМАНИЕ: Используется ТЕСТОВЫЙ сертификат!"
        echo ""
        echo "Для получения настоящего сертификата:"
        echo "  1. Установите CERTBOT_STAGING=0 в .env"
        echo "  2. Удалите тестовый сертификат: rm -rf ./certbot/conf/*"
        echo "  3. Запустите скрипт снова: ./setup-ssl.sh"
        echo ""
    fi
    
    echo "Сертификат будет автоматически обновляться каждые 12 часов."
    echo "============================================================================="
else
    echo ""
    echo "❌ ОШИБКА получения сертификата!"
    echo ""
    echo "Проверьте:"
    echo "  1. DNS записи для $DOMAIN указывают на ваш сервер"
    echo "  2. Порт 80 открыт и доступен из интернета"
    echo "  3. Nginx запущен и работает"
    echo ""
    exit 1
fi
