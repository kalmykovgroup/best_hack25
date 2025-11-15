# Исправление проблемы с памятью для address-parser

## Проблема
Контейнер `address-parser` завершается с кодом 137 (SIGKILL) из-за нехватки памяти.
libpostal требует около 2-4 GB RAM при загрузке данных.

## Диагностика на сервере

### 1. Проверить доступную память
```bash
free -h
```

### 2. Проверить логи контейнера
```bash
cd /var/www/besthack25/current
docker compose logs address-parser
```

### 3. Проверить события OOM
```bash
dmesg | grep -i "killed process"
```

## Решения

### Вариант 1: Увеличить swap (если мало RAM)

Если на сервере < 6 GB RAM, добавьте swap:

```bash
# Создать 4GB swap файл
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Сделать постоянным
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# Проверить
free -h
```

### Вариант 2: Увеличить memory limit для контейнера

Если памяти достаточно, но Docker имеет ограничения, увеличьте лимит в docker-compose.yaml.

### Вариант 3: Настроить Docker daemon

Если Docker имеет глобальные ограничения:

```bash
# Проверить ограничения
docker info | grep -i memory

# Если есть ограничения, отредактировать
sudo nano /etc/docker/daemon.json
```

Добавить:
```json
{
  "default-ulimits": {
    "memlock": {
      "Hard": -1,
      "Name": "memlock",
      "Soft": -1
    }
  }
}
```

Перезапустить Docker:
```bash
sudo systemctl restart docker
```

## Проверка после исправления

```bash
cd /var/www/besthack25/current
docker compose up -d
docker compose ps
docker compose logs -f address-parser
```

Ищите в логах:
```
Address Parser gRPC server started on port 50052
```

Если видите эту строку - сервис запустился успешно.
