import json
from pathlib import Path

import bcrypt

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "train-mock-data"
REGISTERED_USERS_FILE = DATA_DIR / "registered_users.json"


def is_bcrypt_hash(value: str) -> bool:
    return isinstance(value, str) and value.startswith("$2")


def hash_passwords_in_file() -> None:
    if not REGISTERED_USERS_FILE.exists():
        raise FileNotFoundError(f"Missing file: {REGISTERED_USERS_FILE}")

    with REGISTERED_USERS_FILE.open("r", encoding="utf-8") as f:
        users = json.load(f)

    updated = False
    for user in users:
        password = user.get("password", "")
        if password and not is_bcrypt_hash(password):
            hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
            user["password"] = hashed.decode("utf-8")
            updated = True

    if updated:
        with REGISTERED_USERS_FILE.open("w", encoding="utf-8") as f:
            json.dump(users, f, indent=2, ensure_ascii=False)
        print(f"Updated {REGISTERED_USERS_FILE} with bcrypt hashed passwords.")
    else:
        print(f"No plaintext passwords found in {REGISTERED_USERS_FILE}. No changes made.")


if __name__ == "__main__":
    hash_passwords_in_file()
