import argparse
# pyrefly: ignore [missing-import]
import bcrypt
import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "train-mock-data"
PASSWORD_FILE = DATA_DIR / "user_password.json"


def hash_password(password: str, salt: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), salt.encode("utf-8")).decode("utf-8")


def load_passwords():
    if not PASSWORD_FILE.exists():
        return []
    with PASSWORD_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_passwords(passwords):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with PASSWORD_FILE.open("w", encoding="utf-8") as f:
        json.dump(passwords, f, indent=4, ensure_ascii=False)


def upsert_password(user_id: str, password: str):
    salt = bcrypt.gensalt().decode("utf-8")
    password_hash = hash_password(password, salt)
    updated_at = datetime.utcnow().isoformat() + "Z"

    passwords = load_passwords()
    existing = next((item for item in passwords if item.get("user_id") == user_id), None)
    entry = {
        "user_id": user_id,
        "password_hash": password_hash,
        "salt": salt,
        "updated_at": updated_at,
    }

    if existing:
        passwords = [entry if item.get("user_id") == user_id else item for item in passwords]
    else:
        passwords.append(entry)

    save_passwords(passwords)
    return entry


def parse_args():
    parser = argparse.ArgumentParser(description="Generate or update train-mock-data/user_password.json")
    parser.add_argument("user_id", nargs="?", default="user1", help="User ID to generate password for")
    parser.add_argument("password", nargs="?", default="mypassword", help="Plaintext password")
    return parser.parse_args()


def main():
    args = parse_args()
    entry = upsert_password(args.user_id, args.password)
    print(f"Updated {PASSWORD_FILE}")
    print(json.dumps(entry, indent=4, ensure_ascii=False))


if __name__ == "__main__":
    main()