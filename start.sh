#!/bin/bash

# ============================================
# Rick Sanchez Bot - Startup Script
# ============================================
# 
# Этот скрипт:
# 1. Проверяет наличие Python
# 2. Создаёт виртуальное окружение (venv) если его нет
# 3. Активирует venv
# 4. Устанавливает зависимости
# 5. Проверяет наличие .env файла
# 6. Запускает бота

set -e  # Exit on error

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода цветных сообщений
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Баннер
print_banner() {
    echo -e "${GREEN}"
    cat << 'EOF'
    ╔═══════════════════════════════════════════════════════╗
    ║                                                       ║
    ║   🧪 Rick Sanchez Telegram Bot 🧪                    ║
    ║                                                       ║
    ║   *burp* Wubba Lubba Dub Dub!                       ║
    ║                                                       ║
    ║   Startup Script v1.0                                ║
    ║                                                       ║
    ╚═══════════════════════════════════════════════════════╝
EOF
    echo -e "${NC}"
}

# Проверка наличия Python
check_python() {
    log_info "Проверка наличия Python..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        log_error "Python не найден! Установите Python 3.10 или выше."
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    log_success "Python найден: $PYTHON_VERSION"
    
    # Проверка минимальной версии Python (3.10+)
    PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
    PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')
    
    if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
        log_warning "Рекомендуется Python 3.10+, у вас $PYTHON_VERSION"
        log_warning "Бот может работать, но возможны проблемы с совместимостью"
    fi
}

# Создание виртуального окружения
setup_venv() {
    if [ -d "venv" ]; then
        log_info "Виртуальное окружение уже существует"
    else
        log_info "Создание виртуального окружения..."
        $PYTHON_CMD -m venv venv
        
        if [ $? -eq 0 ]; then
            log_success "Виртуальное окружение создано"
        else
            log_error "Не удалось создать виртуальное окружение"
            log_info "Попробуйте установить python3-venv:"
            log_info "  Ubuntu/Debian: sudo apt install python3-venv"
            log_info "  macOS: venv должен быть встроен"
            exit 1
        fi
    fi
}

# Активация виртуального окружения
activate_venv() {
    log_info "Активация виртуального окружения..."
    
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
        log_success "Виртуальное окружение активировано"
    elif [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate
        log_success "Виртуальное окружение активировано"
    else
        log_error "Не найден скрипт активации venv"
        exit 1
    fi
}

# Установка зависимостей
install_dependencies() {
    log_info "Проверка и установка зависимостей..."
    
    if [ ! -f "requirements.txt" ]; then
        log_error "Файл requirements.txt не найден!"
        exit 1
    fi
    
    # Обновление pip
    log_info "Обновление pip..."
    pip install --upgrade pip -q
    
    # Установка зависимостей
    log_info "Установка зависимостей из requirements.txt..."
    pip install -r requirements.txt -q
    
    if [ $? -eq 0 ]; then
        log_success "Зависимости установлены"
    else
        log_error "Ошибка при установке зависимостей"
        exit 1
    fi
}

# Проверка наличия .env файла
check_env_file() {
    log_info "Проверка конфигурации..."
    
    if [ ! -f ".env" ]; then
        log_error "Файл .env не найден!"
        echo ""
        log_info "Создайте файл .env с необходимыми переменными:"
        echo ""
        echo "  TELEGRAM_BOT_TOKEN=your_token_here"
        echo ""
        log_info "См. QUICKSTART.md для подробных инструкций"
        echo ""
        
        read -p "Хотите создать .env из примера? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -f ".env.example" ]; then
                cp .env.example .env
                log_success "Файл .env создан. Отредактируйте его и запустите скрипт снова."
            else
                log_warning "Файл .env.example не найден"
            fi
        fi
        exit 1
    fi
    
    log_success "Файл .env найден"
    
    # Проверка обязательных переменных
    log_info "Проверка обязательных переменных..."
    
    source .env
    
    if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
        log_error "TELEGRAM_BOT_TOKEN не указан в .env"
        exit 1
    fi
    
    if [ -z "$ELIZA_TOKEN" ]; then
        log_error "ELIZA_TOKEN не указан в .env"
        exit 1
    fi
    
    log_success "Все обязательные переменные заполнены"
}

# Запуск бота
run_bot() {
    log_info "Запуск Rick Sanchez Bot..."
    echo ""
    
    # Запуск с обработкой Ctrl+C
    $PYTHON_CMD run.py
    
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -eq 0 ]; then
        log_success "Бот остановлен корректно"
    elif [ $EXIT_CODE -eq 130 ]; then
        # 130 = Ctrl+C
        log_info "Бот остановлен пользователем (Ctrl+C)"
    else
        log_error "Бот завершился с ошибкой (код: $EXIT_CODE)"
        exit $EXIT_CODE
    fi
}

# Главная функция
main() {
    print_banner
    
    log_info "Начало инициализации..."
    echo ""
    
    # 1. Проверка Python
    check_python
    echo ""
    
    # 2. Создание venv
    setup_venv
    echo ""
    
    # 3. Активация venv
    activate_venv
    echo ""
    
    # 4. Установка зависимостей
    install_dependencies
    echo ""
    
    # 5. Проверка .env
    check_env_file
    echo ""
    
    log_success "✅ Инициализация завершена!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    
    # 6. Запуск бота
    run_bot
}

# Обработка аргументов командной строки
case "${1:-}" in
    --help|-h)
        echo "Rick Sanchez Bot - Startup Script"
        echo ""
        echo "Использование:"
        echo "  ./start.sh          Запустить бота (создаёт venv если нужно)"
        echo "  ./start.sh --help   Показать эту справку"
        echo "  ./start.sh --setup  Только создать venv и установить зависимости"
        echo ""
        echo "Первый запуск:"
        echo "  1. chmod +x start.sh"
        echo "  2. ./start.sh"
        echo ""
        exit 0
        ;;
    --setup)
        print_banner
        log_info "Режим настройки (только создание окружения)"
        echo ""
        check_python
        echo ""
        setup_venv
        echo ""
        activate_venv
        echo ""
        install_dependencies
        echo ""
        log_success "✅ Настройка завершена!"
        log_info "Теперь создайте файл .env и запустите: ./start.sh"
        exit 0
        ;;
    "")
        # Запуск по умолчанию
        main
        ;;
    *)
        log_error "Неизвестный аргумент: $1"
        echo "Используйте --help для справки"
        exit 1
        ;;
esac

