# Secrets Directory

Эта директория содержит конфиденциальные данные для локальной разработки.

**ВАЖНО:** Файлы из этой директории **НЕ ДОЛЖНЫ** попадать в Git!

## Локальная разработка

Для локального запуска через Docker Compose создайте следующие файлы:

### secrets/db_user.txt
```
webapp_user
```

### secrets/db_password.txt
```
your_strong_password_here
```

## Production деплой

При деплое на продакшн сервер эти файлы создаются **автоматически** из GitHub Secrets:
- `secrets/db_user.txt` ← из `${{ secrets.DB_USER }}`
- `secrets/db_password.txt` ← из `${{ secrets.DB_PASSWORD }}`

## Создание секретов

### Linux/Mac
```bash
echo "webapp_user" > secrets/db_user.txt
echo "your_password" > secrets/db_password.txt
```

### Windows PowerShell
```powershell
"webapp_user" | Out-File -FilePath secrets/db_user.txt -Encoding utf8 -NoNewline
"your_password" | Out-File -FilePath secrets/db_password.txt -Encoding utf8 -NoNewline
```

### Windows CMD
```cmd
echo webapp_user > secrets/db_user.txt
echo your_password > secrets/db_password.txt
```

## Проверка

После создания файлов убедитесь, что они не отслеживаются Git:

```bash
git status
# secrets/ не должна появляться в списке измененных файлов
```
