import os
import json
import time
import shutil

from . import config, vkapi

PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".avi", ".3gp", ".webm"}
SUPPORTED = PHOTO_EXTS | VIDEO_EXTS

MIN_AGE = 3  # сек — не трогать файл, который только что начал писаться
PENDING_PATH = os.path.join(config.BASE_DIR, "pending_chat.json")


def _load_pending():
    if not os.path.exists(PENDING_PATH):
        return {}
    try:
        with open(PENDING_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_pending(data):
    if not data:
        if os.path.exists(PENDING_PATH):
            os.remove(PENDING_PATH)
        return
    with open(PENDING_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


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
    print("Проверяю индекс облака...", flush=True)
    _, cloud_meta = vkapi.get_chat_index(peer_id)
    pending = _load_pending()

    for i, path in enumerate(paths, 1):
        name = os.path.basename(path)
        size_bytes = os.path.getsize(path)
        mtime = os.path.getmtime(path)
        size_mb = size_bytes / (1024 * 1024)
        print("[%d/%d] %s (%.1f МБ)" %
              (i, len(paths), name, size_mb), flush=True)

        if (name, size_bytes) in cloud_meta:
            print("  ✓ уже есть в чате облака (загрузка не нужна)")
            dest = _move(path)
            print("  ✓ перемещён → %s" % dest)
            result["ok"] += 1
            continue

        pkey = "%s|%d" % (name, size_bytes)
        try:
            if pkey in pending:
                attach = pending[pkey]
                print("  ✓ найден в pending, досылаю в чат без перезаливки")
            else:
                doc = vkapi.upload_to_docs(path, name)
                attach = vkapi.doc_to_attachment(doc)
                pending[pkey] = attach
                _save_pending(pending)
                print("  ✓ загружено в документы группы")

            text = vkapi.build_doc_message(
                name,
                size_bytes,
                timestamp=mtime,
                folder=folder,
                doc_link=vkapi.doc_eternal_url(attach),
            )
            vkapi.send_doc_message(peer_id, attach, text)
            print("  ✓ добавлено в чат облака")

            pending.pop(pkey, None)
            _save_pending(pending)
            cloud_meta.add((name, size_bytes))

            dest = _move(path)
            print("  ✓ перемещён → %s" % dest)
            result["ok"] += 1

        except vkapi.FloodControlError as exc:
            print("  ✗ %s" % exc)
            print(
                "[!] Лимит 100 сообщений подряд. Отправь любое сообщение в чат группы и запусти снова.")
            result["failed"] += 1
            break

        except Exception as exc:
            print("  ✗ ошибка: %s" % exc)
            result["failed"] += 1

    return result
