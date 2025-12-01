#!/bin/bash

# ============================================
# Rick Sanchez Bot - Quick Run Script
# ============================================
# 
# Быстрый запуск (предполагается что venv уже настроен)
# Если venv не настроен, используйте ./start.sh

set -e

# Цвета
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}🧪 Rick Sanchez Bot - Quick Run${NC}"
echo ""

# Проверка наличия venv
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠️  Виртуальное окружение не найдено${NC}"
    echo "Запустите сначала: ./start.sh"
    exit 1
fi

# Активация venv
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "Ошибка активации venv"
    exit 1
fi

# Запуск
exec python run.py

