# Production Deployment Guide

## 🚀 Production Build

### 1. Настройка переменных окружения

Обновите `.env.production` с вашими production URL:

```env
VITE_SIGNALR_HUB_URL=https://your-api-domain.com/hubs/geocode
```

### 2. Production Build

```bash
npm run build:prod
```

Это создаст оптимизированную сборку в папке `dist/`.

### 3. Preview Production Build

```bash
npm run preview
```

Откройте http://localhost:5174 для предпросмотра production сборки.

## 📦 Что включено в Production Build

### Оптимизации

- ✅ **Code Splitting** - автоматическое разделение на chunks:
  - `vendor.js` - React, React-DOM, React-Redux
  - `redux.js` - Redux Toolkit
  - `signalr.js` - SignalR client
  - `index.js` - ваш код приложения

- ✅ **Minification** - Terser минификация с:
  - Удаление всех `console.log/info/debug`
  - Удаление `debugger` statements
  - `console.error` остается (для production отладки)

- ✅ **Tree Shaking** - удаление неиспользуемого кода

- ✅ **Source Maps** - для отладки в production (можно отключить)

### Production-Safe Logging

Весь код использует `logger` утилиту вместо `console`:

```typescript
import { logger } from './utils/logger';

// В development: выводится
// В production: не выводится
logger.log('Debug info');
logger.info('Info message');
logger.warn('Warning');

// В production: выводится всегда
logger.error('Error message');
```

## 🏗️ Deployment Options

### Option 1: Static Hosting (Vercel, Netlify, Cloudflare Pages)

```bash
# Build
npm run build:prod

# Deploy dist/ folder
# Vercel CLI:
vercel --prod

# Netlify CLI:
netlify deploy --prod --dir=dist
```

### Option 2: Docker

```dockerfile
# Dockerfile
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build:prod

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

```nginx
# nginx.conf
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # Кэширование статики
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
```

### Option 3: Node Server

```bash
npm install -g serve
serve -s dist -p 5174
```

## 🔒 Security Checklist

- [ ] HTTPS включен
- [ ] CORS настроен правильно на backend
- [ ] API keys не включены в frontend код
- [ ] `.env.production` в `.gitignore`
- [ ] Source maps отключены (если требуется)
- [ ] CSP headers настроены

## ⚡ Performance Checklist

- [x] Code splitting включен
- [x] Минификация включена
- [x] Tree shaking включен
- [x] Source maps включены (опционально)
- [ ] CDN настроен для статики
- [ ] Gzip/Brotli compression включена
- [ ] Cache headers настроены

## 📊 Bundle Analysis

Проверьте размер bundle:

```bash
npm run analyze
```

Это создаст визуализацию bundle для анализа.

## 🐛 Production Debugging

### 1. Проверка логов

```bash
# В браузере (F12)
# Фильтр: только errors
# logger.error() будет виден
```

### 2. Source Maps

Если включены source maps, вы можете отладить production код через DevTools.

### 3. Redux DevTools

Работает только в development. В production отключен автоматически.

## 📈 Monitoring

Рекомендуется добавить:

- **Sentry** - для отслеживания ошибок
- **Google Analytics** - для аналитики
- **LogRocket** - для session replay

```bash
npm install @sentry/react
```

## 🔄 CI/CD Example (GitHub Actions)

```yaml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Build
        run: npm run build:prod
        env:
          VITE_SIGNALR_HUB_URL: ${{ secrets.PROD_API_URL }}

      - name: Deploy to Vercel
        run: vercel --prod --token=${{ secrets.VERCEL_TOKEN }}
```

## 🚨 Rollback Plan

1. Сохраняйте предыдущие builds
2. Используйте версионирование (git tags)
3. Имейте backup production environment

## 📝 Production Checklist

- [ ] `.env.production` настроен
- [ ] Production API URL корректен
- [ ] Build прошел успешно (`npm run build:prod`)
- [ ] Preview проверен (`npm run preview`)
- [ ] Bundle size приемлем
- [ ] Console logs удалены
- [ ] Error monitoring настроен
- [ ] HTTPS настроен
- [ ] CORS настроен
- [ ] Performance протестирован

## 🎯 Performance Targets

- **Initial Load**: < 3 seconds
- **Time to Interactive**: < 5 seconds
- **Bundle Size**: < 500kb (gzipped)
- **Lighthouse Score**: > 90

## 📞 Support

Для production проблем:
1. Проверьте логи в браузере
2. Проверьте Network tab (Failed requests)
3. Проверьте SignalR подключение
4. Проверьте CORS headers

---

**Готово к production! 🎉**
