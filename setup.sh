#!/bin/bash

set -e

USER_HOME=$(eval echo ~${SUDO_USER})
HOME_DIR="$USER_HOME/pdfiler"
INSTALL_DIR="/usr/local/pdfiler"
BIN_PATH="/usr/local/bin/pdfiler"
REPO_URL="https://github.com/RockerzXY/pdfiler"

# Проверка наличия Git
if ! command -v git &> /dev/null; then
    echo "Git не установлен. Устанавливаем..."
    sudo apt update && sudo apt install -yq git
fi

# Проверка наличия Python
if ! command -v python3 &> /dev/null; then
    echo "Python3 не установлен. Устанавливаем..."
    sudo apt update && sudo apt install -yq python3
fi

# Проверка и установка python3-venv
if ! dpkg -s python3-venv &> /dev/null; then
    echo "python3-venv не установлен. Устанавливаем..."
    sudo apt install -yq python3-venv
fi

# Клонирование репозитория
if [ ! -d "$HOME_DIR" ]; then
    echo "Клонируем репозиторий..."
    git clone "$REPO_URL" "$HOME_DIR"
fi

# Перемещение файлов в нужное место
echo "Перемещаем файлы в $INSTALL_DIR..."
sudo mkdir -p "$INSTALL_DIR"
sudo cp -r "$HOME_DIR"/* "$INSTALL_DIR"

# Создание виртуального окружения в новом месте
echo "Создаём виртуальное окружение..."
cd "$INSTALL_DIR"
python3 -m venv venv

# Установка зависимостей
echo "Установка зависимостей..."
source "$INSTALL_DIR/venv/bin/activate"
pip install --upgrade pip
pip install -r "$INSTALL_DIR/requirements.txt"

# Выдача прав на исполнение
sudo chmod +x "$INSTALL_DIR/pdfiler.py"

# Создание запускного скрипта
echo "#!/bin/bash
source $INSTALL_DIR/venv/bin/activate
python3 $INSTALL_DIR/pdfiler.py \"\$@\"" | sudo tee $BIN_PATH > /dev/null
sudo chmod +x $BIN_PATH

rm -rf "$HOME_DIR"

echo "Установка завершена. Теперь можно использовать команду pdfiler."
