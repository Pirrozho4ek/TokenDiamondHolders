#!/bin/bash

echo "🚀 Запуск Diamond Holders Agent..."

# Проверяем наличие .env файла
if [ ! -f .env ]; then
    echo "⚠️  Файл .env не найден. Создаю на основе шаблона..."
    cp .env_template .env
    echo "✅ Файл .env создан. Пожалуйста, отредактируйте его перед запуском:"
    echo "   - Добавьте ваш BITQUERY_API_KEY"
    echo "   - При необходимости настройте другие параметры"
    echo ""
    echo "После редактирования .env запустите скрипт снова."
    exit 1
fi

# Проверяем наличие Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Пожалуйста, установите Docker."
    exit 1
fi

# Проверяем наличие Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен. Пожалуйста, установите Docker Compose."
    exit 1
fi

echo "🔧 Запуск сервисов..."
docker-compose up -d

echo ""
echo "⏳ Ожидание запуска сервисов..."
sleep 10

echo ""
echo "📊 Статус сервисов:"
docker-compose ps

echo ""
echo "🎉 Сервисы запущены!"
echo ""
echo "📍 Доступные URL:"
echo "   • Open WebUI:     http://localhost:3001"
echo "   • Diamond Agent:  http://localhost:8001"
echo "   • API Docs:       http://localhost:8001/docs"
echo "   • Ollama:         http://localhost:11435"
echo ""
echo "📝 Полезные команды:"
echo "   • Просмотр логов:     docker-compose logs -f"
echo "   • Остановка:          docker-compose down"
echo "   • Перезапуск агента:  docker-compose restart diamond-agent"
echo ""
echo "💡 Для первого входа в Open WebUI создайте аккаунт на http://localhost:3001" 