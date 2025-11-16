# Nginx с встроенным certbot для автоматического получения SSL
FROM nginx:alpine

# Устанавливаем certbot, bash и необходимые зависимости
RUN apk add --no-cache \
    certbot \
    certbot-nginx \
    openssl \
    bash

# Создаем директории для certbot и конфигурации
RUN mkdir -p /var/www/certbot /etc/letsencrypt /etc/nginx/conf.d

# Копируем скрипты
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY generate-config.sh /etc/nginx/generate-config.sh

# Исправляем окончания строк и делаем скрипты исполняемыми
RUN dos2unix /docker-entrypoint.sh /etc/nginx/generate-config.sh 2>/dev/null || \
    sed -i 's/\r$//' /docker-entrypoint.sh /etc/nginx/generate-config.sh && \
    chmod +x /docker-entrypoint.sh /etc/nginx/generate-config.sh

# Используем bash для запуска entrypoint
ENTRYPOINT ["/bin/bash", "/docker-entrypoint.sh"]
