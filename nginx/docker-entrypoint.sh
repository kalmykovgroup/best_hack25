#!/bin/sh
# Умный entrypoint для nginx
# Автоматически проверяет наличие SSL и получает сертификат если нужно

set -e

echo "🚀 Starting Nginx with smart SSL detection..."

# Переменные окружения
DOMAIN=${DOMAIN:-localhost}
EMAIL=${EMAIL:-admin@example.com}
AUTO_GENERATE_CONFIG=${AUTO_GENERATE_CONFIG:-true}
CERTBOT_STAGING=${CERTBOT_STAGING:-0}

# Путь к сертификату
CERT_DIR="/etc/letsencrypt/live"
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
NEED_CERTIFICATE=false

# Функция для проверки валидности сертификата
check_certificate_validity() {
    if [ ! -f "$CERT_PATH" ] || [ ! -f "$KEY_PATH" ]; then
        echo "⚠️  SSL certificate not found for domain: $DOMAIN"
        return 1
    fi

    echo "📋 Checking SSL certificate validity..."

    # Проверяем срок действия (> 30 дней)
    if openssl x509 -checkend 2592000 -noout -in "$CERT_PATH" > /dev/null 2>&1; then
        expiry_date=$(openssl x509 -enddate -noout -in "$CERT_PATH" | cut -d= -f2)
        echo "✅ Certificate is valid until: $expiry_date"
        return 0
    else
        echo "⚠️  Certificate expires soon (less than 30 days) or has expired"
        return 1
    fi
}

# Функция для получения SSL сертификата
obtain_ssl_certificate() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔐 Attempting to obtain SSL certificate"
    echo "📍 Domain: $DOMAIN"
    echo "📧 Email: $EMAIL"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Проверяем что это не localhost
    if [ "$DOMAIN" = "localhost" ]; then
        echo "⚠️  Cannot obtain SSL certificate for localhost"
        echo "💡 Set DOMAIN environment variable to your domain name"
        return 1
    fi

    # Создаем директории для certbot
    mkdir -p /var/www/certbot

    # Запускаем nginx в фоне для ACME challenge
    echo "🌐 Starting nginx in HTTP mode for ACME challenge..."
    nginx -g 'daemon on;'
    sleep 3

    # Проверяем что nginx запустился
    if ! pgrep nginx > /dev/null; then
        echo "❌ Failed to start nginx"
        return 1
    fi

    # Пытаемся получить сертификат через certbot
    if [ "$CERTBOT_STAGING" = "1" ]; then
        echo "📝 Requesting STAGING certificate from Let's Encrypt (for testing)..."
        STAGING_FLAG="--staging"
    else
        echo "📝 Requesting PRODUCTION certificate from Let's Encrypt..."
        STAGING_FLAG=""
    fi

    if certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "$EMAIL" \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        $STAGING_FLAG \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" 2>&1; then

        echo "✅ SSL certificate obtained successfully!"

        # Останавливаем временный nginx
        nginx -s stop
        sleep 2

        return 0
    else
        echo "❌ Failed to obtain SSL certificate"
        echo "⚠️  Common reasons:"
        echo "   - Domain DNS not configured correctly"
        echo "   - Firewall blocking port 80"
        echo "   - Let's Encrypt rate limit reached"
        echo "💡 Continuing in HTTP-only mode"

        # Останавливаем временный nginx
        nginx -s stop 2>/dev/null || true
        sleep 2

        return 1
    fi
}

# Проверяем валидность существующего сертификата
if ! check_certificate_validity; then
    NEED_CERTIFICATE=true
fi

# Если нужен сертификат - пытаемся получить
if [ "$NEED_CERTIFICATE" = "true" ]; then
    # Генерируем HTTP-only конфигурацию для ACME challenge
    echo "🔧 Generating HTTP-only configuration for certificate request..."
    if [ -f "/etc/nginx/generate-config.sh" ]; then
        sh /etc/nginx/generate-config.sh
    fi

    # Пытаемся получить сертификат
    if obtain_ssl_certificate; then
        echo "✅ SSL certificate is now available"
        # Проверяем еще раз
        check_certificate_validity
    else
        echo "⚠️  Will continue in HTTP-only mode"
    fi
fi

# Генерируем финальную конфигурацию (с HTTPS если сертификат есть)
echo "🔧 Generating final nginx configuration for domain: $DOMAIN"
if [ -f "/etc/nginx/generate-config.sh" ]; then
    sh /etc/nginx/generate-config.sh || {
        echo "⚠️  Config generation failed, using existing config"
    }
else
    echo "⚠️  generate-config.sh not found, using existing config"
fi

# Тестируем конфигурацию
echo "🔍 Testing nginx configuration..."
if ! nginx -t; then
    echo "❌ Nginx configuration test failed!"
    echo "📋 Current configuration:"
    cat /etc/nginx/conf.d/default.conf 2>/dev/null || echo "Config file not found"
    exit 1
fi

echo "✅ Nginx configuration is valid"

# Информация о режиме работы
if [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ Starting nginx with HTTPS support"
    echo "🌐 Domain: $DOMAIN"
    echo "🔒 HTTPS: Enabled"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️  Starting nginx in HTTP-only mode"
    echo "🌐 Domain: $DOMAIN"
    echo "🔓 HTTPS: Disabled"
    echo "💡 SSL certificate will be requested automatically"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi

# Запускаем nginx в foreground режиме
echo "🎯 Starting nginx..."
exec nginx -g 'daemon off;'
