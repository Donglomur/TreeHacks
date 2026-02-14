import hashlib
import json
import os
from typing import Optional, Dict, Any

CACHE_DIR = "cache/why_stopped"
os.makedirs(CACHE_DIR, exist_ok=True)

def _hash(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

def load_cached(text: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(CACHE_DIR, _hash(text) + ".json")
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_cached(text: str, result: Dict[str, Any]) -> None:
    path = os.path.join(CACHE_DIR, _hash(text) + ".json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
