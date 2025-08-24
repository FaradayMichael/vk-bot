#!/bin/bash
set -e

echo "***** SeleniumBase Docker Machine *****"

# Создание директории для скриншотов
mkdir -p /app/screenshots

# Очистка предыдущих файлов блокировки
rm -f /tmp/.X*-lock
rm -f /tmp/.X11-unix/X*

# Запуск Xvfb с правильными настройками
Xvfb :99 -screen 0 $RESOLUTION -ac +extension GLX +render -noreset > /dev/null 2>&1 &
XVFB_PID=$!
sleep 2
echo "Xvfb started"

if ! ps -p $XVFB_PID > /dev/null; then
    echo "Ошибка: Xvfb не запустился"
    exit 1
fi

# Настройка .Xauthority для доступа
touch $HOME/.Xauthority > /dev/null 2>&1
xauth generate :99 . trusted > /dev/null 2>&1
xauth add $DISPLAY . $(mcookie) > /dev/null 2>&1

# Запуск оконного менеджера
fluxbox > /dev/null 2>&1 &
FLUX_PID=$!
sleep 2
echo "Fluxbox started"

## Проверка доступности модулей
#echo "Проверка доступности модулей:"
#python3 -c "import seleniumbase; print('SeleniumBase:', seleniumbase.__version__)" || echo "SeleniumBase не найден!"
#python3 -c "import uvicorn; print('Uvicorn:', uvicorn.__version__)" || echo "Uvicorn не найден!"
#python3 -c "import fastapi; print('FastAPI:', fastapi.__version__)" || echo "FastAPI не найден!"

sleep 3

# Запуск Python-скрипта
echo "Запуск скрипта..."
python3 /code/utils_service.py

# Очистка при завершении
trap "kill $XVFB_PID $FLUX_PID; exit" SIGINT SIGTERM EXIT