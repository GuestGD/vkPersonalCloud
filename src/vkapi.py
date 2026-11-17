import os
import re
import time
import random
import requests

from . import config

API = "https://api.vk.com/method/"

_PHOTO_EXTS = {"jpg", "jpeg", "png", "webp", "heic", "heif", "gif"}
_VIDEO_EXTS = {"mp4", "mov", "mkv", "avi", "3gp", "webm"}
_DATE_RE = re.compile(
    r"(?<!\d)(20\d{2})[-_]?(0[1-9]|1[0-2])[-_]?(0[1-9]|[12]\d|3[01])(?!\d)"
)

_PEER_ID_CACHE = None


class FloodControlError(RuntimeError):
    pass


def call(method, params=None, timeout=30):
    data = dict(params or {})
    data["access_token"] = config.VK_TOKEN
    data["v"] = config.API_VERSION
    return requests.post(API + method, data=data, timeout=timeout).json()


def _raise(resp, ctx):
    if "error" in resp:
        e = resp["error"]
        code = e.get("error_code")
        msg = "%s: %s (%s)" % (ctx, e.get("error_msg"), code)
        if code == 9:
            raise FloodControlError(msg)
        raise RuntimeError(msg)


def get_peer_id():
    global _PEER_ID_CACHE
    if _PEER_ID_CACHE is not None:
        return _PEER_ID_CACHE

    cfg_peer = getattr(config, "PEER_ID", None)
    if cfg_peer:
        _PEER_ID_CACHE = int(cfg_peer)
        return _PEER_ID_CACHE

    r = call("messages.getConversations", {"count": 20})
    _raise(r, "messages.getConversations")
    items = r["response"].get("items", [])
    if not items:
        raise RuntimeError(
            "Нет диалогов в группе. Напиши группе любое сообщение со своего аккаунта!"
        )

    for item in items:
        peer = item["conversation"]["peer"]
        if peer.get("type") == "user":
            _PEER_ID_CACHE = peer["id"]
            return _PEER_ID_CACHE

    _PEER_ID_CACHE = items[0]["conversation"]["peer"]["id"]
    return _PEER_ID_CACHE


def format_size(size_bytes):
    if size_bytes >= 1024 * 1024:
        return "%.1f МБ" % (size_bytes / (1024 * 1024))
    return "%d КБ" % max(1, size_bytes // 1024)


def build_doc_message(title, size_bytes, ext="", timestamp=0, folder=None):
    ext_raw = (ext or os.path.splitext(title)[1].lstrip(".")).lower()
    ext_tag = re.sub(r"[^a-z0-9а-яё_]", "", ext_raw)

    if ext_tag in _VIDEO_EXTS:
        type_tag = "#видео"
    elif ext_tag in _PHOTO_EXTS:
        type_tag = "#фото"
    else:
        type_tag = "#файл"

    tags = [type_tag]
    if ext_tag:
        tags.append("#" + ext_tag)

    year, month = None, None
    m = _DATE_RE.search(title or "")
    if m:
        year, month = m.group(1), m.group(2)
    elif timestamp:
        tm = time.localtime(timestamp)
        year, month = "%04d" % tm.tm_year, "%02d" % tm.tm_mon

    if year and month:
        tags.append("#y" + year)
        tags.append("#d%s_%s" % (year, month))

    if size_bytes >= 100 * 1024 * 1024:
        tags.append("#heavy")

    if folder:
        dir_name = os.path.basename(os.path.normpath(folder)).lower()
        dir_tag = re.sub(r"[^a-z0-9а-яё_]+", "_", dir_name).strip("_")
        if dir_tag:
            tags.append("#dir_" + dir_tag)

    return "%s\n%s · %s" % (" ".join(tags), title, format_size(size_bytes))


def doc_to_attachment(doc):
    if isinstance(doc, str):
        return doc
    attach = "doc%s_%s" % (doc["owner_id"], doc["id"])
    if doc.get("access_key"):
        attach += "_" + doc["access_key"]
    return attach


def upload_to_docs(path, name):
    """Загружает любой файл (фото или видео) в документы группы."""
    r = call("docs.getWallUploadServer", {"group_id": config.GROUP_ID})
    _raise(r, "getWallUploadServer")
    url = r["response"]["upload_url"]

    with open(path, "rb") as fh:
        resp = requests.post(url, files={"file": (name, fh)}, timeout=1800)

    try:
        up = resp.json()
    except ValueError:
        raise RuntimeError(
            "ВК вернул не JSON (HTTP %s). Возможно, оборвалась сеть."
            % resp.status_code
        )

    if "file" not in up:
        raise RuntimeError("upload error: %s" % str(up)[:200])

    s = call("docs.save", {"file": up["file"], "title": name})
    _raise(s, "docs.save")
    return s["response"]["doc"]


def send_doc_message(peer_id, doc, text, retries=3):
    attachment = doc_to_attachment(doc)
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            r = call(
                "messages.send",
                {
                    "peer_id": peer_id,
                    "random_id": random.randint(1, 2_000_000_000),
                    "message": text,
                    "attachment": attachment,
                },
            )
            if "error" in r:
                code = r["error"].get("error_code")
                if code == 6 and attempt < retries:
                    time.sleep(1.5 * attempt)
                    continue
                _raise(r, "messages.send")
            return r["response"]
        except FloodControlError:
            raise
        except Exception as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(2 * attempt)
    raise last_err


def delete_messages(msg_ids):
    if not msg_ids:
        return
    r = call(
        "messages.delete",
        {
            "message_ids": ",".join(str(x) for x in msg_ids),
            "delete_for_all": 1,
        },
    )
    _raise(r, "messages.delete")


def get_chat_index(peer_id):
    """Возвращает (set('doc{owner}_{id}'), set((title, size))) всех документов в чате."""
    keys = set()
    meta = set()
    offset = 0
    while True:
        r = call(
            "messages.getHistory",
            {"peer_id": peer_id, "count": 200, "offset": offset},
        )
        _raise(r, "messages.getHistory")
        resp = r["response"]
        items = resp.get("items", [])
        if not items:
            break

        for msg in items:
            for att in msg.get("attachments", []):
                if att.get("type") == "doc":
                    d = att["doc"]
                    keys.add("doc%s_%s" % (d["owner_id"], d["id"]))
                    meta.add((d.get("title", ""), int(d.get("size") or 0)))

        offset += len(items)
        if offset >= resp.get("count", 0):
            break
        time.sleep(0.25)

    return keys, meta
