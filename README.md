# VK Cloud Phone

Ручная выгрузка фото и видео из папки телефона в VK-группу.
Фото → альбомы `08_05_2026` (дата из имени → EXIF → mtime).
Видео → документы группы.
После загрузки файлы **перемещаются** в `UPLOADED_DIR`.

## Установка (Termux)

```bash
pkg install git python termux-api
git clone https://github.com/GuestGD/vkPersonalCloud.git
cd vk-cloud-phone
python3 vkCloud.py
```
