"""Saved budgets for Sliced Bread: one JSON file per name in DATA_DIR. Demo mode, so no passwords."""

import json
import os
import re

import budget

# Set SLICED_BREAD_DATA to a Google Drive folder in Colab so data survives a runtime reset.
DATA_DIR = os.environ.get("SLICED_BREAD_DATA", "data")
MAX_NAME_LENGTH = 30  # characters
UNSAFE_FILE_CHARACTERS = re.compile(r"[^a-z0-9_-]+")


def clean_name(text):
    """The name as it will be shown: trimmed, single spaces. Raises ValueError if unusable."""
    name = " ".join((text or "").split())
    if not name:
        raise ValueError("Enter your name")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be {MAX_NAME_LENGTH} characters or fewer")
    return name


def file_key(name):
    """The file a name's budget lives in: 'Mark G' is 'mark_g'. Anything that isn't a letter or digit is dropped."""
    key = UNSAFE_FILE_CHARACTERS.sub("_", clean_name(name).lower()).strip("_")
    if not key:
        raise ValueError("Name needs at least one letter or number")
    return key


def _path(key):
    return os.path.join(DATA_DIR, f"{key}.json")


def load_budget(key):
    """The saved budget for this key, or a new empty one."""
    try:
        with open(_path(key), encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return budget.empty_budget()


def save_budget(key, user_budget):
    """Write to a temp file first, then swap it in, so a crash never leaves half a file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_path = _path(key) + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(user_budget, file, indent=2)
    os.replace(temp_path, _path(key))


def delete_budget(key):
    """Remove this name's saved budget for good."""
    if os.path.exists(_path(key)):
        os.remove(_path(key))
