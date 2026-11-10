import os
import re
import datetime

# Паттерны: порядок важен (20260508 → 2026-05-08 → 08.05.2026)
_PATTERNS = [
    # IMG_20260508
    (re.compile(r"(?P<y>20\d{2})(?P<m>\d{2})(?P<d>\d{2})"), "ymd"),
    # 2026-05-08
    (re.compile(r"(?P<y>20\d{2})[-_.](?P<m>\d{2})[-_.](?P<d>\d{2})"), "ymd"),
    # 08.05.2026
    (re.compile(r"(?P<d>\d{2})[-_.](?P<m>\d{2})[-_.](?P<y>20\d{2})"), "dmy"),
]


def from_filename(filename):
    for pat, order in _PATTERNS:
        m = pat.search(filename)
        if not m:
            continue
        try:
            y, mo, d = int(m.group("y")), int(m.group("m")), int(m.group("d"))
            return datetime.date(y, mo, d)
        except ValueError:
            continue
    return None


def from_exif(filepath):
    try:
        from PIL import Image
        img = Image.open(filepath)
        exif = img._getexif() or {}
        # DateTimeOriginal / DateTimeDigitized
        raw = exif.get(36867) or exif.get(36868)
        if raw:
            return datetime.datetime.strptime(raw, "%Y:%m:%d %H:%M:%S").date()
    except Exception:
        pass
    return None


def from_mtime(filepath):
    try:
        return datetime.date.fromtimestamp(os.path.getmtime(filepath))
    except OSError:
        return None


def get_date(filepath):
    return (from_filename(os.path.basename(filepath))
            or from_exif(filepath)
            or from_mtime(filepath))


def album_title(d):
    return d.strftime("%d_%m_%Y")  # 08_05_2026
