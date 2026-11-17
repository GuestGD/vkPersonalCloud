#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Разовый перенос документов из vk_docs.json в Сообщения сообщества."""
import os
import json
import time
import shutil
import subprocess

from src import vkapi


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


def _find_docs_json():
    for candidate in ("vk_docs.json", "/sdcard/Download/VK/vk_docs.json"):
        if os.path.exists(candidate):
            return candidate
    raise SystemExit(
        "[!] Не найден vk_docs.json ни в текущей папке, ни в /sdcard/Download/VK/")


def _cleanup_test_messages(peer_id):
    r = vkapi.call("messages.getHistory", {"peer_id": peer_id, "count": 20})
    vkapi._raise(r, "messages.getHistory")
    test_ids = [
        m["id"] for m in r["response"].get("items", [])
        if (m.get("text") or "").startswith("Тест:")
    ]
    if test_ids:
        try:
            vkapi.delete_messages(test_ids)
            print("Удалено тестовых сообщений:", len(test_ids))
        except Exception as exc:
            print("[!] Не удалось удалить тестовое сообщение:", exc)


def main():
    docs_path = _find_docs_json()
    with open(docs_path, "r", encoding="utf-8") as f:
        docs = json.load(f)

    peer_id = vkapi.get_peer_id()
    print("Диалог peer_id:", peer_id)
    print("Всего записей в JSON:", len(docs))

    _cleanup_test_messages(peer_id)

    print("Проверяю, что уже есть в чате...")
    existing, _ = vkapi.get_chat_index(peer_id)
    print("Уже в чате документов:", len(existing))

    to_send = []
    seen = set(existing)
    for item in reversed(docs):
        base_key = "doc%s_%s" % (item["owner_id"], item["id"])
        if base_key in seen:
            continue
        seen.add(base_key)
        to_send.append(item)

    print("Осталось перенести:", len(to_send))
    if not to_send:
        print("Всё уже в чате!")
        return

    print("-" * 60)
    locked = _wake_lock()
    ok, failed = 0, 0
    try:
        for i, item in enumerate(to_send, 1):
            title = item.get("title") or ("doc_%s" % item["id"])
            size_bytes = int(item.get("size") or 0)
            ext = item.get("ext") or ""
            date_ts = int(item.get("date") or 0)
            attach = item.get("attach") or ("doc%s_%s" %
                                            (item["owner_id"], item["id"]))

            text = vkapi.build_doc_message(
                title, size_bytes, ext=ext, timestamp=date_ts
            )

            try:
                vkapi.send_doc_message(peer_id, attach, text)
                ok += 1
                print("[%d/%d] ✓ %s" % (i, len(to_send), title), flush=True)
            except vkapi.FloodControlError as exc:
                failed += 1
                print("[%d/%d] ✗ %s: %s" %
                      (i, len(to_send), title, exc), flush=True)
                print("\n[!] Сработал лимит ВК (100 сообщений за окно).")
                print("    Подожди 15-60 минут и запусти скрипт снова — первые %d уже пропустятся." %
                      (len(existing) + ok))
                break
            except Exception as exc:
                failed += 1
                print("[%d/%d] ✗ %s: %s" %
                      (i, len(to_send), title, exc), flush=True)

            time.sleep(0.4)
    finally:
        if locked:
            _wake_unlock()

    print("-" * 60)
    print("Итог запуска: перенесено %d, ошибок %d" % (ok, failed))


if __name__ == "__main__":
    main()
