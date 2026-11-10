import os
import time
import shutil

from . import config, dates, vkapi

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".3gp", ".webm"}
SUPPORTED = PHOTO_EXTS | VIDEO_EXTS
MIN_AGE = 3  # сек — не трогать файл, который только что начал писаться


class Session:
    """Кэш альбомов на время одного запуска (без файла состояния)."""

    def __init__(self):
        self._albums = None

    def album_id(self, title):
        if self._albums is None:
            self._albums = vkapi.list_albums()
        if title in self._albums:
            return self._albums[title]
        aid = vkapi.create_album(title)
        self._albums[title] = aid
        print("  + создан альбом %s" % title)
        return aid


def _stable(path):
    try:
        return (time.time() - os.path.getmtime(path)) >= MIN_AGE
    except OSError:
        return False


def _collect(folder, limit):
    if not os.path.isdir(folder):
        raise RuntimeError("нет папки: %s" % folder)
    items = []
    for name in os.listdir(folder):
        path = os.path.join(folder, name)
        if not os.path.isfile(path):
            continue
        if os.path.splitext(name)[1].lower() not in SUPPORTED:
            continue
        if not _stable(path):
            continue
        try:
            items.append((os.path.getsize(path), path))
        except OSError:
            continue
    items.sort(reverse=True)
    return [p for _s, p in items[:limit]], len(items)


def _unique_dest(name):
    dest = os.path.join(config.UPLOADED_DIR, name)
    if not os.path.exists(dest):
        return dest
    base, ext = os.path.splitext(name)
    return os.path.join(
        config.UPLOADED_DIR,
        "%s_%s%s" % (base, time.strftime("%Y%m%d_%H%M%S"), ext),
    )


def _move(path):
    os.makedirs(config.UPLOADED_DIR, exist_ok=True)
    dest = _unique_dest(os.path.basename(path))
    shutil.move(path, dest)  # os.rename если та же ФС, copy+del иначе
    return dest


def _is_photo(name):
    return os.path.splitext(name)[1].lower() in PHOTO_EXTS


def run(folder, limit):
    paths, total = _collect(folder, limit)
    print("Найдено подходящих файлов: %d, беру %d" % (total, len(paths)))

    result = {"total": len(paths), "ok": 0, "failed": 0}
    if not paths:
        return result

    session = Session()
    for i, path in enumerate(paths, 1):
        name = os.path.basename(path)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        print("[%d/%d] %s (%.1f МБ)" % (i, len(paths), name, size_mb), flush=True)

        try:
            if _is_photo(name):
                d = dates.get_date(path)
                if not d:
                    raise RuntimeError("не смог определить дату")
                title = dates.album_title(d)
                aid = session.album_id(title)
                vkapi.upload_photo(path, aid)
                print("  ✓ фото → альбом %s" % title)
            else:
                vkapi.upload_video_doc(path, name)
                print("  ✓ видео → документы группы")

            dest = _move(path)
            print("  ✓ перемещён → %s" % dest)
            result["ok"] += 1

        except Exception as exc:
            print("  ✗ ошибка: %s" % exc)
            result["failed"] += 1

    return result