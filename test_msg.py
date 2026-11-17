#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import json
import random
from src import vkapi

# 1. Ищем vk_docs.json
docs_path = None
for candidate in ("vk_docs.json", "/sdcard/Download/VK/vk_docs.json"):
    if os.path.exists(candidate):
        docs_path = candidate
        break

if not docs_path:
    raise SystemExit(
        "[!] Не найден vk_docs.json ни в текущей папке, ни в /sdcard/Download/VK/")

# 2. Находим диалог с тобой
conv = vkapi.call("messages.getConversations", {"count": 5})
vkapi._raise(conv, "messages.getConversations")
items = conv["response"].get("items", [])
if not items:
    raise SystemExit(
        "[!] Диалогов нет. Напиши группе сообщение со своего аккаунта!")

peer_id = items[0]["conversation"]["peer"]["id"]
print("Найден peer_id:", peer_id)

# 3. Пробуем отправить 1-й документ из vk_docs.json
with open(docs_path, "r", encoding="utf-8") as f:
    docs = json.load(f)

first = docs[0]
print("Отправляю:", first["attach"], first["title"])

res = vkapi.call("messages.send", {
    "peer_id": peer_id,
    "random_id": random.randint(1, 2000000000),
    "message": "Тест: " + first["title"],
    "attachment": first["attach"],
})
vkapi._raise(res, "messages.send")
print("Отправлено! message_id =", res["response"])

# 4. Читаем это же сообщение обратно через messages.getHistory
hist = vkapi.call("messages.getHistory", {"peer_id": peer_id, "count": 1})
vkapi._raise(hist, "messages.getHistory")
print(json.dumps(hist["response"]["items"][0], indent=2, ensure_ascii=False))
