# core/utils.py
import tempfile
import os
import json
from typing import Any

def save_temp_file(content: bytes, suffix: str = ".pdf") -> str:
    """Save bytes to temporary file and return path"""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        return tmp.name

def cleanup_temp_file(path: str):
    """Remove temporary file"""
    if os.path.exists(path):
        os.remove(path)

def load_json(path: str) -> Any:
    """Load JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(data: Any, path: str):
    """Save data to JSON file"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)