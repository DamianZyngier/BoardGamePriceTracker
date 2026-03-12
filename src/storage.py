import json
import os
import logging
from typing import List, Dict, Any

from src.logger import setup_logger

logger = setup_logger(__name__)

def load_json(file_path: str) -> Any:
    """Loads a JSON file, returning an empty list if it doesn't exist or is invalid."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error reading JSON from {file_path}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error reading {file_path}: {e}")
        return []

def save_json(file_path: str, data: Any):
    """Saves data to a JSON file."""
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving JSON to {file_path}: {e}")
