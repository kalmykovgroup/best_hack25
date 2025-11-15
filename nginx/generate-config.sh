#!/bin/sh
# Умный генератор nginx конфигурации
# Создает конфигурацию в зависимости от наличия SSL сертификата

set -e

DOMAIN=${DOMAIN:-localhost}
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"
OUTPUT="/etc/nginx/conf.d/default.conf"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔧 Генерация nginx конфигурации"
echo "📍 Домен: ${DOMAIN}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Проверяем наличие SSL сертификата
if [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    echo "✅ SSL сертификат найден, создаю конфигурацию с HTTPS"

    # Создаем конфигурацию с HTTPS
    cat > "$OUTPUT" << 'EOF'
upstream api_backend {
    server webapi:8080;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    # SSL Configuration
    ssl_certificate CERT_PATH_PLACEHOLDER;
    ssl_certificate_key KEY_PATH_PLACEHOLDER;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;

    # HSTS (опционально, раскомментируйте после тестирования)
    # add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # OCSP Stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate CERT_PATH_PLACEHOLDER;

    # Важные статические файлы (sitemap, robots, manifest)
    # Обрабатываются с особым заголовком для корректной работы в SPA
    location ~* \.(xml|txt|json|webmanifest)$ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Accept-Static-File "true";
        expires 1d;
        add_header Cache-Control "public, must-revalidate";
    }

    # Service Worker - не кэшировать
    location ~* ^/(sw\.js|registerSW\.js|workbox-.*\.js)$ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Accept-Static-File "true";
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Static files caching (изображения, стили, скрипты)
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Accept-Static-File "true";
        proxy_cache_valid 200 1d;
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    # Proxy to API
    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $server_name;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

    # Заменяем placeholders
    sed -i "s|DOMAIN_PLACEHOLDER|${DOMAIN}|g" "$OUTPUT"
    sed -i "s|CERT_PATH_PLACEHOLDER|${CERT_PATH}|g" "$OUTPUT"
    sed -i "s|KEY_PATH_PLACEHOLDER|${KEY_PATH}|g" "$OUTPUT"

else
    echo "⚠️  SSL сертификат не найден, создаю конфигурацию только для HTTP"

    # Создаем конфигурацию без HTTPS
    cat > "$OUTPUT" << 'EOF'
upstream api_backend {
    server webapi:8080;
    keepalive 32;
}

server {
    listen 80;
    listen [::]:80;
    server_name DOMAIN_PLACEHOLDER www.DOMAIN_PLACEHOLDER;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        try_files $uri =404;
    }

    # Важные статические файлы (sitemap, robots, manifest)
    location ~* \.(xml|txt|json|webmanifest)$ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Accept-Static-File "true";
        expires 1d;
        add_header Cache-Control "public, must-revalidate";
    }

    # Service Worker - не кэшировать
    location ~* ^/(sw\.js|registerSW\.js|workbox-.*\.js)$ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Accept-Static-File "true";
        expires -1;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }

    # Static files caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|svg|woff|woff2|ttf|eot)$ {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Accept-Static-File "true";
        expires 1d;
        add_header Cache-Control "public, immutable";
    }

    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;

        # Headers
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        # Buffering
        proxy_buffering off;
        proxy_cache_bypass $http_upgrade;
    }
}
EOF

    # Заменяем placeholders
    sed -i "s|DOMAIN_PLACEHOLDER|${DOMAIN}|g" "$OUTPUT"
fi

echo "✅ Конфигурация создана: ${OUTPUT}"

# Проверяем конфигурацию
if nginx -t 2>&1; then
    echo "✅ Конфигурация nginx валидна"
else
    echo "❌ Ошибка в конфигурации nginx!"
    exit 1
fi
