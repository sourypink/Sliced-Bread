"""Accounts and saved budgets for Sliced Bread, kept as JSON files in DATA_DIR."""

import hashlib
import json
import os
import re
import secrets
from datetime import date

import budget

# Set SLICED_BREAD_DATA to a Google Drive folder in Colab so data survives a runtime reset.
DATA_DIR = os.environ.get("SLICED_BREAD_DATA", "data")
USERS_FILE = "users.json"
HASH_ROUNDS = 200_000  # PBKDF2 iterations; slow enough to resist guessing, fast enough to sign in
MIN_PASSWORD_LENGTH = 6  # characters
USERNAME_PATTERN = re.compile(r"[a-z0-9_]{3,20}")  # also safe as a file name


def _path(file_name):
    return os.path.join(DATA_DIR, file_name)


def _read_json(file_name, default):
    try:
        with open(_path(file_name), encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        return default


def _write_json(file_name, content):
    """Write to a temp file first, then swap it in, so a crash never leaves half a file."""
    os.makedirs(DATA_DIR, exist_ok=True)
    temp_path = _path(file_name + ".tmp")
    with open(temp_path, "w", encoding="utf-8") as file:
        json.dump(content, file, indent=2)
    os.replace(temp_path, _path(file_name))


def _hash_password(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), HASH_ROUNDS).hex()


def _check_password_rules(password):
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")


def normalize_username(text):
    """Lowercase and trim a username, or raise ValueError if it breaks the rules."""
    username = (text or "").strip().lower()
    if not USERNAME_PATTERN.fullmatch(username):
        raise ValueError("Username must be 3-20 letters, numbers or underscores")
    return username


def create_account(username_text, password, display_name=""):
    """Create a user and an empty budget; returns the username."""
    username = normalize_username(username_text)
    _check_password_rules(password)
    users = _read_json(USERS_FILE, {})
    if username in users:
        raise ValueError("That username is taken")
    salt = secrets.token_hex(16)
    users[username] = {
        "display_name": (display_name or "").strip() or username,
        "salt": salt,
        "password_hash": _hash_password(password, salt),
        "created": date.today().isoformat(),
    }
    _write_json(USERS_FILE, users)
    save_budget(username, budget.empty_budget())
    return username


def sign_in(username_text, password):
    """Return the username if the password matches, otherwise raise ValueError."""
    users = _read_json(USERS_FILE, {})
    username = (username_text or "").strip().lower()
    user = users.get(username)
    # Same message for both failures, so the screen doesn't reveal which usernames exist.
    if not user or not secrets.compare_digest(_hash_password(password or "", user["salt"]), user["password_hash"]):
        raise ValueError("Wrong username or password")
    return username


def change_password(username, current_password, new_password):
    """Replace a password after checking the current one."""
    try:
        sign_in(username, current_password)
    except ValueError:
        raise ValueError("Wrong current password") from None
    _check_password_rules(new_password)
    users = _read_json(USERS_FILE, {})
    salt = secrets.token_hex(16)
    users[username].update(salt=salt, password_hash=_hash_password(new_password, salt))
    _write_json(USERS_FILE, users)


def get_display_name(username):
    return _read_json(USERS_FILE, {})[username]["display_name"]


def set_display_name(username, display_name):
    users = _read_json(USERS_FILE, {})
    users[username]["display_name"] = (display_name or "").strip() or username
    _write_json(USERS_FILE, users)


def load_budget(username):
    return _read_json(f"{username}.json", budget.empty_budget())


def save_budget(username, user_budget):
    _write_json(f"{username}.json", user_budget)


def delete_account(username):
    """Remove the user and their budget file for good."""
    users = _read_json(USERS_FILE, {})
    users.pop(username, None)
    _write_json(USERS_FILE, users)
    budget_path = _path(f"{username}.json")
    if os.path.exists(budget_path):
        os.remove(budget_path)
