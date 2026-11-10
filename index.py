#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VK Cloud Phone — ручной загрузчик.

Использование:
    python3 index.py                  # DCIM/Camera, 10 файлов
    python3 index.py /path/to/folder  # своя папка, 10 файлов
    python3 index.py 5                # DCIM/Camera, 5 файлов
    python3 index.py /path 20         # папка + количество
"""
import sys
import shutil
import subprocess

from src import config, uploader


def _wake_lock():
    if not shutil.which("termux-wake-lock"):
        return False
    try:
        subprocess.run(["termux-wake-lock"], check=True, timeout=5)
        return True
    except Exception:
        return False


def _wake_unlock():
    if not shutil.which("termux-wake-unlock"):
        return
    try:
        subprocess.run(["termux-wake-unlock"], check=True, timeout=5)
    except Exception:
        pass


def _parse_args(argv):
    folder, count = None, None
    if len(argv) >= 2:
        folder, count = argv[0], argv[1]
    elif len(argv) == 1:
        if argv[0].isdigit():
            count = argv[0]
        else:
            folder = argv[0]
    try:
        count = int(count) if count is not None else config.DEFAULT_COUNT
    except ValueError:
        sys.exit("[!] Количество должно быть числом")
    folder = folder or config.DEFAULT_FOLDER
    return folder, count


def main():
    if len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return

    folder, count = _parse_args(sys.argv[1:])
    print("Папка:  %s" % folder)
    print("Беру:   %d самых тяжёлых" % count)
    print("Выход:  %s" % config.UPLOADED_DIR)
    print("-" * 60)

    locked = _wake_lock()
    try:
        result = uploader.run(folder, count)
    finally:
        if locked:
            _wake_unlock()

    print("-" * 60)
    print("Итог: загружено %d из %d, ошибок %d"
          % (result["ok"], result["total"], result["failed"]))
    sys.exit(0 if result["failed"] == 0 else 1)


if __name__ == "__main__":
    main()