#!/bin/bash

# Цвета для красивого вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # Сброс цвета

# Проверка минимального количества аргументов
if [ $# -lt 2 ]; then
    echo -e "${RED}❌ Ошибка: Недостаточно аргументов.${NC}"
    echo -e "Использование: ${CYAN}./env <action> <environment> [services/flags...]${NC}"
    echo ""
    echo "Примеры:"
    echo "  ./env up dev                  # Запустить всё в dev"
    echo "  ./env up dev zebra-bib        # Запустить только zebra-bib в dev"
    echo "  ./env up prod -d              # Запустить prod в фоне (detached)"
    echo "  ./env down dev                # Остановить dev"
    echo "  ./env logs dev frontend       # Логи frontend в dev"
    echo "  ./env exec dev frontend bash  # Зайти в консоль frontend в dev"
    exit 1
fi

ACTION=$1
ENV=$2
shift 2 # Сдвигаем аргументы, чтобы $@ содержал только сервисы и доп. флаги

# Базовые файлы
BASE_FILE="docker-compose.yaml"
DEV_FILE="docker-compose.dev.yaml"

if [ ! -f "$BASE_FILE" ]; then
    echo -e "${RED}❌ Ошибка: Базовый файл $BASE_FILE не найден в текущей директории.${NC}"
    exit 1
fi

# Формируем базовую команду
COMPOSE_CMD="docker compose -f $BASE_FILE"

# Подключаем файлы в зависимости от окружения
case "$ENV" in
    dev)
        if [ -f "$DEV_FILE" ]; then
            COMPOSE_CMD="$COMPOSE_CMD -f $DEV_FILE"
        else
            echo -e "${YELLOW}⚠️  Предупреждение: Файл $DEV_FILE не найден. Используется только базовая конфигурация.${NC}"
        fi
        ;;
    prod)
        # Для prod используем только базовый файл (без переопределений)
        ;;
    *)
        echo -e "${RED}❌ Ошибка: Неизвестное окружение '$ENV'.${NC}"
        echo "Доступные окружения: ${GREEN}dev${NC}, ${GREEN}prod${NC}."
        exit 1
        ;;
esac

# Выводим итоговую команду для прозрачности (чтобы видеть, что именно выполняется)
echo -e "${CYAN}▶ Выполняется: $COMPOSE_CMD $ACTION $@${NC}"

# Запускаем docker compose
# "$@" правильно обрабатывает аргументы с пробелами, если они вдруг появятся
$COMPOSE_CMD $ACTION "$@"
