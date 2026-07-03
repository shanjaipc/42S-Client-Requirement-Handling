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
import json
import secrets
import sys
from pathlib import Path
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
        "salt": "7072ad91f3370c819233577a615dcb323954e0b1c847b14829098026cf275b3c",
        "hash": "959e46ce88536c1ffd5d438b89ed21728b5f7694e9b9d79ed73bbf16ea6991fc",
        "display_name": "Srinivas",
        "role": "viewer",
    },
    "admin": {
        "salt": "9adf73d346ebf65e205a3c9f0b1986b8c41c185a30a447571cf5a3a8616ecc31",
        "hash": "f51844835a3b3c9886903084f14bb2a9fb813dfd5a6b7b0d63831b0d108c6134",
        "display_name": "Admin",
        "role": "admin",
    },
    "pgupta": {
        "salt": "e243d6c79c7cc303496e51429c82a69d714bd88f711cb8bb521f4394ecf53b52",
        "hash": "f607f50f5fbfd7335b9cb133b191a60bd26131ffa45058c34b32404ad1e622d7",
        "display_name": "Pgupta",
        "role": "viewer",
    },
    "josh": {
        "salt": "a38ed120166913648742e52511c1635af828b61e35b41ccd3e87cc79b6b9eca2",
        "hash": "14c950ab748fa3fba25f282b1286ce0c1141c0b5e30dd48f226b4defc2d5bf93",
        "display_name": "Josh",
        "role": "viewer",
    },
    "ankit": {
        "salt": "58c3e59d612c70d7782595810ea94c63b8bc90a5d57fefd478a698aadedad742",
        "hash": "3787f5fa611ba45ed95dbaa6f4c05bd9253bae577d743bdb29e23acba51ba73a",
        "display_name": "Ankit",
        "role": "viewer",
    },
    "arunashok": {
        "salt": "ed103b6e15d63093947bcd225a89537f39e6253ebfc689b4414b73f83473f025",
        "hash": "ead2a9d9ad7b5c3f4359d9f1bf2611dd3ac7f38c46668139bcae05add7242e05",
        "display_name": "Arunashok",
        "role": "viewer",
    },
    "ravindran": {
        "salt": "55e059e1cc947789a2ed18badcd438f15fb808e11a9adff5203dab57001bce74",
        "hash": "7ad3b62c3f0a5209c49d4175af5822729db8d8f65d87a72acd0787d6e5fbb876",
        "display_name": "Ravindran",
        "role": "viewer",
    },
}

# ── Sidecar DB: persists runtime user changes across restarts ─────────────────
_USERS_DB = Path(__file__).parent / "users_db.json"
if _USERS_DB.exists():
    try:
        _stored = json.loads(_USERS_DB.read_text())
        USERS.update(_stored)
    except (OSError, json.JSONDecodeError):
        pass

# Maximum failed login attempts before lockout
MAX_ATTEMPTS = 5
# Lockout duration in seconds
LOCKOUT_SECONDS = 300  # 5 minutes

# ── Open login — any name + this shared password is accepted for non-admin access ──
_OPEN_SALT = "a3f8c2d1e0b7946f5234089a1bc6e7d85f3219c047a8d6e23051f79b4c8a0de2"
_OPEN_HASH = "e6ca1a00294d8bbba922e555671d283aef9500751166b935dc676ccfdb69715b"


def is_admin_user(username: str) -> bool:
    """Return True if the username belongs to an admin account."""
    user = USERS.get(username.strip().lower())
    return user is not None and user.get("role") == "admin"


def verify_open_password(password: str) -> bool:
    """Check password against the shared non-admin password hash."""
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        _OPEN_SALT.encode("utf-8"),
        260_000,
    ).hex()
    return secrets.compare_digest(candidate, _OPEN_HASH)


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


def get_user(username: str) -> Optional[Dict[str, Any]]:
    """Return the user record (without hash/salt) or None if not found."""
    user = USERS.get(username.strip().lower())
    if user is None:
        return None
    return {
        "display_name": user["display_name"],
        "role":         user["role"],
        "active":       user.get("active", True),
    }


def verify_password(username: str, password: str) -> bool:
    """Constant-time comparison. Also blocks deactivated accounts."""
    user = USERS.get(username.strip().lower())
    if user is None:
        hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"dummy", 260_000)
        return False
    if not user.get("active", True):
        return False
    candidate = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        user["salt"].encode("utf-8"),
        260_000,
    ).hex()
    return secrets.compare_digest(candidate, user["hash"])


# ── Runtime user management ───────────────────────────────────────────────────

def save_users() -> None:
    """Persist the current USERS dict to users_db.json."""
    try:
        _USERS_DB.write_text(json.dumps(USERS, indent=2))
    except OSError:
        pass


def list_users() -> list:
    return [
        {
            "username":     u,
            "display_name": v["display_name"],
            "role":         v["role"],
            "active":       v.get("active", True),
        }
        for u, v in USERS.items()
    ]


def add_user(username: str, password: str, display_name: str, role: str = "viewer") -> bool:
    """Add a new user. Returns False if username already exists."""
    key = username.strip().lower()
    if key in USERS:
        return False
    creds = hash_password(password)
    USERS[key] = {
        "salt":         creds["salt"],
        "hash":         creds["hash"],
        "display_name": display_name,
        "role":         role,
        "active":       True,
    }
    return True


def set_password(username: str, new_password: str) -> bool:
    key = username.strip().lower()
    if key not in USERS:
        return False
    creds = hash_password(new_password)
    USERS[key]["salt"] = creds["salt"]
    USERS[key]["hash"] = creds["hash"]
    return True


def set_role(username: str, role: str) -> bool:
    key = username.strip().lower()
    if key not in USERS or role not in ("admin", "viewer"):
        return False
    USERS[key]["role"] = role
    return True


def set_active(username: str, active: bool) -> bool:
    key = username.strip().lower()
    if key not in USERS:
        return False
    USERS[key]["active"] = active
    return True


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
