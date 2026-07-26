"""items.py -- Black-market item catalog access for the simulation engine."""
from __future__ import annotations
import os
import json
from typing import Dict, Any
from engine import paths

_DATA_PATH = os.path.join(paths.app_root(), "data", "items.json")
_catalog: Dict[str, Dict[str, Any]] | None = None


def get_catalog() -> Dict[str, Dict[str, Any]]:
    """Item catalog keyed by item id, loaded once from data/items.json."""
    global _catalog
    if _catalog is None:
        _catalog = {}
        path = os.path.abspath(_DATA_PATH)
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for item in json.load(fh).get("items", []):
                    _catalog[item["id"]] = item
    return _catalog


def get_item(item_id: str) -> Dict[str, Any] | None:
    return get_catalog().get(item_id)


def prob_bonus(item_id: str) -> float:
    item = get_item(item_id)
    return float(item.get("prob_bonus", 0.0)) if item else 0.0


def is_single_use(item_id: str) -> bool:
    item = get_item(item_id)
    return bool(item.get("single_use", False)) if item else False
