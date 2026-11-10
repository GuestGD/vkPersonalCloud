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


# ---------------- Альбомы ----------------

def list_albums():
    """{title: album_id} — только альбомы группы."""
    r = call("photos.getAlbums", {"owner_id": -GROUP_ID, "need_system": 1})
    _raise(r, "getAlbums")
    return {a["title"]: a["id"] for a in r["response"]["items"]}


def create_album(title):
    r = call("photos.createAlbum", {
        "group_id": GROUP_ID,
        "title": title,
        "privacy_view": "all",
        "privacy_comment": "all",
    })
    _raise(r, "createAlbum")
    return r["response"]["id"]


# ---------------- Фото ----------------

def upload_photo(path, album_id):
    r = call("photos.getUploadServer", {
             "group_id": GROUP_ID, "album_id": album_id})
    _raise(r, "getUploadServer")
    url = r["response"]["upload_url"]

    with open(path, "rb") as fh:
        up = requests.post(url, files={"file1": fh}, timeout=180).json()
    if "server" not in up:
        raise RuntimeError("photo upload: %s" % str(up)[:200])

    s = call("photos.save", {
        "group_id": GROUP_ID,
        "album_id": album_id,
        "server": up["server"],
        "photos_list": up["photos_list"],
        "hash": up["hash"],
    })
    _raise(s, "photos.save")
    return s["response"]


# ---------------- Видео → документы группы ----------------

def upload_video_doc(path, name):
    r = call("docs.getWallUploadServer", {"group_id": GROUP_ID})
    _raise(r, "getWallUploadServer")
    url = r["response"]["upload_url"]

    with open(path, "rb") as fh:
        up = requests.post(url, files={"file": (name, fh)}, timeout=900).json()
    if "file" not in up:
        raise RuntimeError("video upload: %s" % str(up)[:200])

    s = call("docs.save", {"file": up["file"], "title": name})
    _raise(s, "docs.save")
    return s["response"]["doc"]
