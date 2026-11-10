#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Установщик VK Cloud Phone (Termux / Linux)."""

import os
import sys
import json
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))


def is_termux():
    return os.path.isdir("/data/data/com.termux")


def run(cmd):
    print("$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)


def install_deps():
    if is_termux():
        run(["pkg", "update", "-y"])
        run(["pkg", "install", "-y", "python", "python-pillow", "termux-api"])
        run(["pip", "install", "--upgrade", "pip", "requests"])
    else:
        run(["sudo", "apt", "install", "-y", "python3", "python3-pil",
             "python3-requests"])


def get_args():
    token = os.environ.get("VK_TOKEN")
    group_id = os.environ.get("VK_GROUP_ID")
    if len(sys.argv) >= 3:
        token, group_id = sys.argv[1], sys.argv[2]
    token = (token or input("1. Токен сообщества VK: ")).strip()
    group_id = (group_id or input("2. ID группы (цифры): ")).strip().replace("-", "")
    if not group_id.isdigit():
        sys.exit("[!] ID группы — только цифры.")
    return token.replace(" ", ""), int(group_id)


def _default_folder():
    if is_termux():
        return "/sdcard/DCIM/Camera"
    return os.path.join(os.path.expanduser("~"), "Pictures")


def _default_uploaded():
    if is_termux():
        return "/sdcard/Pictures/vkUploaded"
    return os.path.join(os.path.expanduser("~"), "Pictures", "vkUploaded")


def check_storage():
    if not is_termux():
        return
    if not os.path.isdir("/sdcard/DCIM"):
        print("\n[!] /sdcard недоступен. Запусти: termux-setup-storage", flush=True)
        run(["termux-setup-storage"])


def write_config(token, group_id):
    cfg = {
        "VK_TOKEN": token,
        "GROUP_ID": group_id,
        "API_VERSION": "5.131",
        "DEFAULT_FOLDER": _default_folder(),
        "DEFAULT_COUNT": 10,
        "UPLOADED_DIR": _default_uploaded(),
    }
    path = os.path.join(HERE, "config.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.chmod(path, 0o600)
    print("\n[OK] config.json создан:", flush=True)
    for k, v in cfg.items():
        if k != "VK_TOKEN":
            print("     %-15s = %s" % (k, v), flush=True)


def main():
    print("=" * 60)
    print("   VK CLOUD PHONE — УСТАНОВКА")
    print("=" * 60)
    check_storage()
    install_deps()
    token, group_id = get_args()
    write_config(token, group_id)
    print("\n✅ Готово.")
    print("  Запуск:  python3 index.py")
    print("  Своя папка:  python3 index.py /path/to/folder")
    print("  Своё число:  python3 index.py /path 5")


if __name__ == "__main__":
    main()