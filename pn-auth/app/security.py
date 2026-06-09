"""Passordhashing (bcrypt), JWT (pn_auth-token) og rate-limiting.

Token-kontrakten her er DELT med integrasjonene:
  - integrasjon/oppdrag-node/pnAuth.js  (verifiserer samme HS256-token)
  - integrasjon/sanksjon-fastapi/pn_auth.py
Endrer du payload/algoritme her, må de oppdateres i takt.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any

import bcrypt
import jwt  # PyJWT

ALGORITHM = "HS256"


# ---- Passord -------------------------------------------------------------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---- JWT (pn_auth) -------------------------------------------------------
def make_token(*, secret: str, user_id: int, name: str, email: str,
               permissions: dict[str, int], ttl_min: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "name": name,
        "email": email,
        "permissions": {
            "oppdrag": int(bool(permissions.get("oppdrag"))),
            "sanksjon": int(bool(permissions.get("sanksjon"))),
            "datakvalitet": int(bool(permissions.get("datakvalitet"))),
            "admin": int(bool(permissions.get("admin"))),
        },
        "iat": now,
        "exp": now + ttl_min * 60,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token: str, secret: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None


def has_system_access(claims: dict[str, Any], system: str) -> bool:
    """admin=1 gir implisitt tilgang til alt (jf. FELLES_AUTH_spec §1)."""
    perms = claims.get("permissions") or {}
    if perms.get("admin"):
        return True
    return bool(perms.get(system))


# ---- Rate-limiting på innlogging ----------------------------------------
class RateLimiter:
    """Enkel glidende vindu-teller per nøkkel (IP). In-memory.

    NB: gjelder per prosess. Kjør pn-auth med ÉN uvicorn-worker (det holder for
    ~10 brukere), eller bytt til en delt teller (Redis) hvis dere skalerer ut.
    """

    def __init__(self, max_hits: int, window_s: int) -> None:
        self.max_hits = max_hits
        self.window_s = window_s
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> bool:
        """True hvis tillatt (og teller forsøket), False hvis over grensen."""
        now = time.time()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self.window_s:
                q.popleft()
            if len(q) >= self.max_hits:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
