"""Saved budgets for Sliced Bread: one JSON file per name in DATA_DIR, with a salted password hash inside."""

import hashlib
import hmac
import json
import os
import re
import secrets

import budget

# Set SLICED_BREAD_DATA to a Google Drive folder in Colab so data survives a runtime reset.
DATA_DIR = os.environ.get("SLICED_BREAD_DATA", "data")
MAX_NAME_LENGTH = 30  # characters
UNSAFE_FILE_CHARACTERS = re.compile(r"[^a-z0-9_-]+")
MIN_PASSWORD_LENGTH = 8  # characters
PASSWORD_ITERATIONS = 600_000  # PBKDF2-SHA256 rounds, OWASP's 2023 figure
SALT_BYTES = 16
MAX_EMAIL_LENGTH = 254  # characters, the longest an address can be
EMAIL_SHAPE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


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


def rename_budget(old_key, new_key):
    """Move a budget to a new name's file. Refuses a name someone else already has."""
    if os.path.exists(_path(new_key)):
        raise ValueError("That name is taken")
    os.replace(_path(old_key), _path(new_key))


# ---------- Passwords ----------

def hash_password(password, salt_hex=None):
    """The salt and PBKDF2 hash to store for a password, both as hex. A new salt unless one is given."""
    salt = bytes.fromhex(salt_hex) if salt_hex else secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return {"salt": salt.hex(), "password_hash": digest.hex()}


def check_password(account, password):
    """Whether password matches the account's stored hash, compared in constant time."""
    expected = hash_password(password or "", account["salt"])["password_hash"]
    return hmac.compare_digest(expected, account["password_hash"])


def new_password(password):
    """Hash a password being set, or raise ValueError if it is too short."""
    if len(password or "") < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
    return hash_password(password)


def clean_email(text):
    """A trimmed email address, blank allowed. Raises ValueError if it can't be one."""
    email = (text or "").strip()
    if email and (len(email) > MAX_EMAIL_LENGTH or not EMAIL_SHAPE.fullmatch(email)):
        raise ValueError("Email should look like name@example.com")
    return email


def sign_in(name_text, password):
    """(file key, budget) for a name and password. A new name, or a budget saved before passwords, takes this one."""
    name = clean_name(name_text)
    key = file_key(name)
    user_budget = load_budget(key)
    account = user_budget.get("account", {})
    if account.get("password_hash"):
        if not check_password(account, password):
            raise ValueError("That name and password don't match")
        return key, user_budget
    user_budget["account"] = {"name": name, "email": "", **new_password(password)}
    save_budget(key, user_budget)
    return key, user_budget
