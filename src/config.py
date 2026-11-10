import os
import json

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

with open(CONFIG_PATH, "r", encoding="utf-8") as _f:
    _cfg = json.load(_f)

VK_TOKEN = _cfg["VK_TOKEN"]
GROUP_ID = _cfg["GROUP_ID"]
API_VERSION = _cfg.get("API_VERSION", "5.131")
DEFAULT_FOLDER = _cfg["DEFAULT_FOLDER"]
DEFAULT_COUNT = _cfg.get("DEFAULT_COUNT", 10)
UPLOADED_DIR = _cfg["UPLOADED_DIR"]