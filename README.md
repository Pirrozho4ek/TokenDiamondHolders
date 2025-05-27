# Diamond Holders Agent

Агент для анализа держателей токенов на блокчейне с веб-интерфейсом Open WebUI.

## Быстрый старт

### 1. Настройка переменных окружения

Создайте файл `.env` на основе `.env_template`:

```bash
cp .env_template .env
```

Отредактируйте `.env` файл:

```env
# BitQuery API Configuration
BITQUERY_API_KEY=your_bitquery_api_key_here
BITQUERY_GRAPHQL_URL=https://streaming.bitquery.io/graphql

# Tracing Configuration
OPENAI_AGENTS_DISABLE_TRACING=1

# Model Configuration for Docker
API_TYPE=ollama
MODEL_NAME=llama3.1
MODEL_BASE_URL=http://ollama:11434/v1
OPENAI_API_KEY=dummy
```

### 2. Запуск с Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down
```

## Сервисы

После запуска будут доступны:

- **Diamond Agent API**: http://localhost:8001
  - OpenAI-совместимый API
  - Документация: http://localhost:8001/docs
  - Модели: http://localhost:8001/v1/models

- **Open WebUI**: http://localhost:3001
  - Веб-интерфейс для чата с агентом
  - Автоматически подключен к Diamond Agent

- **Ollama**: http://localhost:11435
  - Локальная LLM (llama3.1)

## Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Open WebUI    │───▶│  Diamond Agent  │───▶│     Ollama      │
│   (Port 3001)   │    │   (Port 8001)   │    │  (Port 11435)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   BitQuery API  │
                       │   (External)    │
                       └─────────────────┘
```

## Использование

### Через Open WebUI (Рекомендуется)

1. Откройте http://localhost:3001
2. Создайте аккаунт или войдите
3. Начните чат с агентом

### Через API

```bash
# Проверка доступных моделей
curl http://localhost:8001/v1/models

# Отправка запроса
curl -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "diamond-agent",
    "messages": [
      {"role": "user", "content": "Show diamond holders of 0x..."}
    ]
  }'
```

## Примеры запросов

- "Show top 5 diamond holders of [token_address] with no updates in last 7 days"
- "Get top 20 diamond holders of [token_address]"
- "Give me diamond holders of [token_address]"

## Конфигурация

### Использование OpenAI вместо Ollama

В файле `.env` измените:

```env
API_TYPE=openai
MODEL_NAME=gpt-4
MODEL_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=your_openai_api_key_here
```

### Настройка Open WebUI

Переменные окружения в `docker-compose.yml`:

- `WEBUI_SECRET_KEY`: Секретный ключ для сессий
- `ENABLE_SIGNUP`: Разрешить регистрацию новых пользователей
- `DEFAULT_USER_ROLE`: Роль по умолчанию для новых пользователей

## Разработка

### Локальный запуск без Docker

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск сервера
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### Перезапуск отдельных сервисов

```bash
# Перезапуск только агента
docker-compose restart diamond-agent

# Перезапуск только Open WebUI
docker-compose restart open-webui
```

## Troubleshooting

### Проверка статуса сервисов

```bash
docker-compose ps
```

### Просмотр логов

```bash
# Все сервисы
docker-compose logs

# Конкретный сервис
docker-compose logs diamond-agent
docker-compose logs open-webui
docker-compose logs ollama
```

### Очистка данных

```bash
# Остановка и удаление контейнеров
docker-compose down

# Удаление volumes (ВНИМАНИЕ: удалит все данные)
docker-compose down -v
``` 