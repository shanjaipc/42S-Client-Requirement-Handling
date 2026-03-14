"""
credentials.py — User registry for the 42Signals Requirement Handling app.
Passwords are stored as PBKDF2-HMAC-SHA256 hashes (260,000 iterations).

─────────────────────────────────────────────
HOW TO ADD A NEW USER
─────────────────────────────────────────────
1. Run this file directly:
       python3 credentials.py
2. Enter the new username and password when prompted.
3. Copy the printed dict entry into the USERS dict below.

HOW TO CHANGE A PASSWORD
─────────────────────────────────────────────
Same as adding — run python3 credentials.py, generate a new hash,
and replace the old entry in USERS.

⚠️  Keep this file out of public version control.
    Add credentials.py to .gitignore if the repo is shared externally.
─────────────────────────────────────────────
"""

import hashlib
import secrets
import sys
from typing import Dict, Optional, Any

# ─────────────────────────────────────────────────────────────────────────────
# USER REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
# Fields:
#   salt         — random 32-byte hex string, unique per user
#   hash         — PBKDF2-HMAC-SHA256 hex digest (260,000 iterations)
#   display_name — shown in the UI after login
#   role         — "admin" or "viewer" (reserved for future use)
#
# Default passwords (CHANGE THESE BEFORE DEPLOYMENT):
#   shanjai   → Shanjai@42S
#   srinivas  → Srinivas@42S
#   admin     → Admin@42S2026
#   pgupta    → Pgupta@42S
#   josh      → Josh@42S
#   ankit     → Ankit@42S
#   arunashok → Arunashok@42S
#   ravindran → Ravindran@42S

USERS: Dict[str, Any] = {
    "shanjai": {
        "salt": "2c946cdef9039924763634879e24419a8564d1ed5a7be68d204175a6b088d6e9",
        "hash": "41471e39c8e1b57a587c5c726bc100585ab0f846675f0489170fe69274b7e15d",
        "display_name": "Shanjai",
        "role": "admin",
    },
    "srinivas": {
        "salt": "1b2e89bba60567c27aba7850ebd0fb363c90ac8da72dcf2d19a56f0b60892c37",
        "hash": "c8ddf2d6b81aa63f5d39aaec4eb46e6c47ba27b30e2d0aca4e4ca96a796cffd7",
        "display_name": "Srinivas",
        "role": "admin",
    },
    "admin": {
        "salt": "9adf73d346ebf65e205a3c9f0b1986b8c41c185a30a447571cf5a3a8616ecc31",
        "hash": "f51844835a3b3c9886903084f14bb2a9fb813dfd5a6b7b0d63831b0d108c6134",
        "display_name": "Admin",
        "role": "admin",
    },
    "pgupta": {
        "salt": "08d03b6766d728b9f5253bc95b3cb3d0522eeb5a755ea0acf62e36cfa4ed9892",
        "hash": "5be10faf07a7713275ffc9aa182b7c5753e9445373c28bf4f8e31ff5206f81ed",
        "display_name": "Pgupta",
        "role": "admin",
    },
    "josh": {
        "salt": "47bb40a92cf98a9f744f2e060c6a572922c80d60ed8344df693ed4092abdd5c1",
        "hash": "35d5015c713c12dedc751d42f57d8799cc88ad6c72b0c75caf7d18f63747a121",
        "display_name": "Josh",
        "role": "admin",
    },
    "ankit": {
        "salt": "e5998a0320d7460ffb2bd14a6b6f08bcd9d6ec36ea565c5905c4955d9ee83237",
        "hash": "afbcfbf54f52fc8559f6b29a6b58d872b5177c15d37bfa01c906a683b9994bc5",
        "display_name": "Ankit",
        "role": "admin",
    },
    "arunashok": {
        "salt": "2eb6ea09c3fe52fa96a87043772a8ec4bb1c2787b282df180c4af155f42f9fb0",
        "hash": "de7902c109809313ccde4e766a527f189d7bdac6f781b73233d06dfd0a150296",
        "display_name": "Arunashok",
        "role": "admin",
    },
    "ravindran": {
        "salt": "87c2144ee6b2fbfefdab5cdc24d0ccdf72a8f8fc081419b9f395e35ddb0e907b",
        "hash": "57a80b117a6c6eddc40f06217acf5f4c1209f75316593b7e7bd22ebbc47ea4cc",
        "display_name": "Ravindran",
        "role": "admin",
    },
}

# Maximum failed login attempts before lockout
MAX_ATTEMPTS = 5
# Lockout duration in seconds
LOCKOUT_SECONDS = 300  # 5 minutes


# ─────────────────────────────────────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def hash_password(password: str) -> dict:
    """Generate a new PBKDF2-HMAC-SHA256 hash for a plaintext password.
    Returns a dict with 'salt' and 'hash' suitable for the USERS registry."""
    salt = secrets.token_hex(32)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        260_000,
    )
    return {"salt": salt, "hash": key.hex()}


def verify_password(username: str, password: str) -> bool:
    """Constant-time comparison of a candidate password against stored hash.
    Returns True only if username exists AND password matches."""
    user = USERS.get(username.strip().lower())
    if user is None:
        # Run the hash anyway to prevent username-enumeration via timing
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"dummy", 260_000)
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        user["salt"].encode("utf-8"),
        260_000,
    ).hex()
    return secrets.compare_digest(candidate, user["hash"])


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Return the user record (without hash/salt) or None if not found."""
    user = USERS.get(username.strip().lower())
    if user is None:
        return None
    return {"display_name": user["display_name"], "role": user["role"]}


# ─────────────────────────────────────────────────────────────────────────────
# CLI HELPER — run `python3 credentials.py` to generate a new hash
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n42Signals — Password Hash Generator")
    print("────────────────────────────────────")
    username = input("New username: ").strip().lower()
    password = input("Password    : ").strip()
    if not username or not password:
        print("Username and password cannot be empty.")
        sys.exit(1)
    result = hash_password(password)
    display = input("Display name (e.g. Shanjai): ").strip() or username.capitalize()
    print("\nAdd this entry to USERS in credentials.py:\n")
    print(f'    "{username}": {{')
    print(f'        "salt": "{result["salt"]}",')
    print(f'        "hash": "{result["hash"]}",')
    print(f'        "display_name": "{display}",')
    print(f'        "role": "admin",')
    print(f'    }},')
    print()
