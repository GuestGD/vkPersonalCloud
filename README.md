# VK Cloud Phone

Ручная выгрузка фото и видео из папки телефона в VK-группу.
Все файлы (и фото, и видео) загружаются в **документы группы**.
После загрузки файлы **перемещаются** в `UPLOADED_DIR`.

## Установка (Termux)

pkg update -y && pkg upgrade -y
pkg install git python termux-api python-requests python-pillow -y

termux-setup-storage

git clone https://github.com/GuestGD/vkPersonalCloud.git
cd vkPersonalCloud
python vkCloud.py
