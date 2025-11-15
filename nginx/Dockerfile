# Nginx с встроенным certbot для автоматического получения SSL
FROM nginx:alpine

# Устанавливаем certbot и необходимые зависимости
RUN apk add --no-cache \
    certbot \
    certbot-nginx \
    openssl

# Создаем директории для certbot и конфигурации
RUN mkdir -p /var/www/certbot /etc/letsencrypt /etc/nginx/conf.d

# Копируем скрипты
COPY docker-entrypoint.sh /docker-entrypoint.sh
COPY generate-config.sh /etc/nginx/generate-config.sh

# Делаем скрипты исполняемыми
RUN chmod +x /docker-entrypoint.sh /etc/nginx/generate-config.sh

# Используем наш entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]
