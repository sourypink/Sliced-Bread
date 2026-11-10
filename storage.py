"""Saved budgets for Sliced Bread: one JSON file per account email in DATA_DIR, with a salted password hash inside."""

import hashlib
import hmac
import json
import os
import re
import secrets

import budget

# Set SLICED_BREAD_DATA to save budgets somewhere other than ./data.
DATA_DIR = os.environ.get("SLICED_BREAD_DATA", "data")
MAX_NAME_LENGTH = 30  # characters
MIN_PASSWORD_LENGTH = 8  # characters
PASSWORD_ITERATIONS = 600_000  # PBKDF2-SHA256 rounds, OWASP's 2023 figure
SALT_BYTES = 16
MAX_EMAIL_LENGTH = 254  # characters, the longest an address can be
# Lowercase letters, digits and . _ % + - only, so the address itself is a safe file name.
EMAIL_SHAPE = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}")


# ---------- Names and saved files ----------

def clean_name(text):
    """The name as it will be shown: trimmed, single spaces. Raises ValueError if unusable."""
    name = " ".join((text or "").split())
    if not name:
        raise ValueError("Enter your name")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be {MAX_NAME_LENGTH} characters or fewer")
    return name


def _path(key):
    return os.path.join(DATA_DIR, f"{key}.json")


def load_budget(key):
    with open(_path(key), encoding="utf-8") as file:
        return json.load(file)


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


def account_exists(key):
    return os.path.exists(_path(key))


def rename_budget(old_key, new_key):
    """Move a budget to a new email's file. Refuses an email another account already has."""
    if account_exists(new_key):
        raise ValueError("Another account already uses that email")
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


# ---------- Accounts ----------

def clean_email(text):
    """The account's email, trimmed and lowercased; also its file key. Raises ValueError if it can't be one."""
    email = (text or "").strip().lower()
    if not email:
        raise ValueError("Enter your email")
    if len(email) > MAX_EMAIL_LENGTH or not EMAIL_SHAPE.fullmatch(email):
        raise ValueError("Email should look like name@example.com")
    return email


def create_account(name_text, email_text, password, confirm):
    """(file key, budget) for a new account. Refuses an email that already has one."""
    name = clean_name(name_text)
    key = clean_email(email_text)
    if account_exists(key):
        raise ValueError("An account with that email already exists. Log in instead")
    if password != confirm:
        raise ValueError("The passwords don't match")
    user_budget = budget.empty_budget()
    user_budget["account"] = {"name": name, "email": key, **new_password(password)}
    save_budget(key, user_budget)
    return key, user_budget


def log_in(email_text, password):
    """(file key, budget) for an email and its password. Says the same thing for an unknown email as a wrong password."""
    key = clean_email(email_text)
    user_budget = load_budget(key) if account_exists(key) else None
    if not (user_budget and check_password(user_budget["account"], password)):
        raise ValueError("That email and password don't match")
    return key, user_budget
