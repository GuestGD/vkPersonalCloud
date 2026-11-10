# VK Cloud Phone

Ручная выгрузка фото и видео из папки телефона в VK-группу.
Фото → альбомы `08_05_2026` (дата из имени → EXIF → mtime).
Видео → документы группы.
После загрузки файлы **перемещаются** в `UPLOADED_DIR`.

## Установка (Termux)

```bash
pkg update -y && pkg upgrade -y
pkg install git python termux-api python-requests python-pillow -y

termux-setup-storage

git clone https://github.com/GuestGD/vkPersonalCloud.git
cd vkPersonalCloud
python vkCloud.py
```
