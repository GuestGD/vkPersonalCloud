import os
import random
import requests

from .config import VK_TOKEN, GROUP_ID, API_VERSION

API = "https://api.vk.com/method/"


def call(method, params=None, timeout=30):
    data = dict(params or {})
    data["access_token"] = VK_TOKEN
    data["v"] = API_VERSION
    return requests.get(API + method, params=data, timeout=timeout).json()


def _raise(resp, ctx):
    if "error" in resp:
        e = resp["error"]
        raise RuntimeError("%s: %s (%s)" %
                           (ctx, e.get("error_msg"), e.get("error_code")))


def upload_to_docs(path, name):
    """Загружает любой файл (фото или видео) в документы группы."""
    r = call("docs.getWallUploadServer", {"group_id": GROUP_ID})
    _raise(r, "getWallUploadServer")
    url = r["response"]["upload_url"]

    with open(path, "rb") as fh:
        # 30 минут на файл, чтобы не отваливалось по таймауту
        resp = requests.post(url, files={"file": (name, fh)}, timeout=1800)

    try:
        up = resp.json()
    except ValueError:
        raise RuntimeError(
            "ВК вернул не JSON (HTTP %s). Возможно, оборвалась сеть." % resp.status_code)

    if "file" not in up:
        raise RuntimeError("upload error: %s" % str(up)[:200])

    s = call("docs.save", {"file": up["file"], "title": name})
    _raise(s, "docs.save")
    return s["response"]["doc"]
