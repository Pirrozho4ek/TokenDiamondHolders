# Changelog

## [1.1.0] - 2024-12-19

### Changed
- **Порты сервисов изменены для избежания конфликтов с локальными версиями:**
  - Diamond Agent API: `8000` → `8001`
  - Open WebUI: `3000` → `3001` 
  - Ollama: `11434` → `11435`

### Added
- Отдельный файл конфигурации `webui.env` для Open WebUI
- Улучшенный `start.sh` скрипт с проверками и информативным выводом
- Подробная документация в README.md
- Healthcheck для Diamond Agent контейнера
- Изолированная Docker сеть `diamond-network`

### Fixed
- Конфликты имен контейнеров (open-webui → open-webui-docker)
- Улучшенная структура Dockerfile с кэшированием зависимостей

## [1.0.0] - 2024-12-19

### Added
- Первоначальная версия Diamond Holders Agent
- Docker Compose конфигурация с Ollama и Open WebUI
- FastAPI сервер с OpenAI-совместимым API
- Интеграция с BitQuery для анализа блокчейн данных 