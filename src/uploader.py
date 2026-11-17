import os
import time
import shutil

from . import config, vkapi

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".3gp", ".webm"}
SUPPORTED = PHOTO_EXTS | VIDEO_EXTS

MIN_AGE = 3  # сек — не трогать файл, который только что начал писаться


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
    shutil.move(path, dest)
    return dest


def run(folder, limit):
    paths, total = _collect(folder, limit)
    print("Найдено подходящих файлов: %d, беру %d" % (total, len(paths)))

    result = {"total": len(paths), "ok": 0, "failed": 0}
    if not paths:
        return result

    peer_id = vkapi.get_peer_id()

    for i, path in enumerate(paths, 1):
        name = os.path.basename(path)
        size_bytes = os.path.getsize(path)
        mtime = os.path.getmtime(path)
        size_mb = size_bytes / (1024 * 1024)
        print("[%d/%d] %s (%.1f МБ)" %
              (i, len(paths), name, size_mb), flush=True)

        try:
            doc = vkapi.upload_to_docs(path, name)
            print("  ✓ загружено в документы группы")

            text = vkapi.build_doc_message(
                name, size_bytes, timestamp=mtime, folder=folder
            )
            vkapi.send_doc_message(peer_id, doc, text)
            print("  ✓ добавлено в чат облака")

            dest = _move(path)
            print("  ✓ перемещён → %s" % dest)
            result["ok"] += 1

        except Exception as exc:
            print("  ✗ ошибка: %s" % exc)
            result["failed"] += 1

    return result
