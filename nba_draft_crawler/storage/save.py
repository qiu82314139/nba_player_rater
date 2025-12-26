import json
import os

BASE_PATH = "data"

def save_json(filename, data):
    os.makedirs(BASE_PATH, exist_ok=True)
    path = os.path.join(BASE_PATH, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)