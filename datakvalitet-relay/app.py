"""datakvalitet-relay – server-side relay for Datakvalitet sin AI-chat.

Hvorfor: Anders' verktøy kalte Anthropic DIREKTE fra nettleseren, med API-nøkkel i
klienten og konfidensielle aggregerte data sendt eksternt. Denne relayen flytter det
server-side (samme mønster som e-post via SMTP2GO og felles auth):
  - Anthropic-nøkkelen ligger i miljøet (secret-or-die), aldri i nettleseren.
  - Endepunktet ligger på subpath /datakvalitet/api/chat (jf. BYGGESTANDARD §2).
  - Tilgang håndheves server-side: krever gyldig pn_auth-token med permissions.datakvalitet
    (i tillegg til nginx auth_request som allerede beskytter /datakvalitet/).
  - Rate-limit. DEBUG=false → ingen API-dok.

Kontrakt mot nettleser:
  POST /datakvalitet/api/chat  { system: str, messages: [{role, content}] }
  → { text: str }   (eller HTTP-feil)
"""
# NB: IKKE `from __future__ import annotations` – FastAPI må kunne lese Depends-metadataen
# på det lokale Tilgang-aliaset (ellers blir annotasjonen en streng som ikke kan resolves).

import os
import time
from collections import defaultdict, deque
from typing import Annotated

import httpx
import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

ALGORITHM = "HS256"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"


class Settings:
    def __init__(self) -> None:
        self.auth_secret = os.environ.get("AUTH_SECRET", "")
        if len(self.auth_secret) < 32:
            raise RuntimeError("AUTH_SECRET må være satt (min 32 tegn) – delt med pn-auth.")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not self.anthropic_key:
            raise RuntimeError("ANTHROPIC_API_KEY må være satt (server-side, aldri i nettleseren).")
        self.cookie_name = os.environ.get("COOKIE_NAME", "pn_auth")
        self.model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        self.max_tokens = int(os.environ.get("ANTHROPIC_MAX_TOKENS", "1000"))
        self.debug = os.environ.get("DEBUG", "false").strip().lower() in ("1", "true", "yes")
        self.rate_max = int(os.environ.get("CHAT_RATE_MAX", "30"))
        self.rate_window_s = int(os.environ.get("CHAT_RATE_WINDOW_S", "300"))


class Msg(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=20000)


class ChatBody(BaseModel):
    system: str = Field(default="", max_length=40000)
    messages: list[Msg] = Field(min_length=1, max_length=40)


class RateLimiter:
    def __init__(self, maks: int, vindu: int) -> None:
        self.maks, self.vindu = maks, vindu
        self._treff: dict[str, deque] = defaultdict(deque)

    def ok(self, nokkel: str) -> bool:
        na = time.monotonic()
        q = self._treff[nokkel]
        while q and na - q[0] > self.vindu:
            q.popleft()
        if len(q) >= self.maks:
            return False
        q.append(na)
        return True


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or Settings()
    limiter = RateLimiter(cfg.rate_max, cfg.rate_window_s)
    docs = dict(docs_url="/datakvalitet/api/docs") if cfg.debug else dict(docs_url=None, redoc_url=None, openapi_url=None)
    app = FastAPI(title="datakvalitet-relay", version="1.0.0", **docs)
    app.state.cfg = cfg

    def krev_tilgang(request: Request) -> dict:
        token = request.cookies.get(cfg.cookie_name)
        if not token:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ikke innlogget")
        try:
            # verify_sub=False: pn_auth-tokenet har numerisk sub (user_id); nyere PyJWT
            # krever ellers streng. exp valideres fortsatt.
            claims = jwt.decode(token, cfg.auth_secret, algorithms=[ALGORITHM],
                                options={"verify_sub": False})
        except jwt.PyJWTError:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ugyldig økt")
        perms = claims.get("permissions") or {}
        if not (perms.get("datakvalitet") or perms.get("admin")):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Mangler tilgang til Datakvalitet")
        return claims

    Tilgang = Annotated[dict, Depends(krev_tilgang)]

    def klient_ip(request: Request) -> str:
        fwd = request.headers.get("x-forwarded-for")
        return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "ukjent")

    @app.post("/datakvalitet/api/chat")
    async def chat(body: ChatBody, request: Request, claims: Tilgang):
        if not limiter.ok(str(claims.get("sub")) or klient_ip(request)):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "For mange forespørsler. Vent litt.")
        payload = {
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "system": body.system,
            "messages": [m.model_dump() for m in body.messages],
        }
        headers = {"x-api-key": cfg.anthropic_key, "anthropic-version": "2023-06-01",
                   "content-type": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=60) as c:
                r = await c.post(ANTHROPIC_URL, json=payload, headers=headers)
        except httpx.HTTPError:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Fikk ikke kontakt med AI-tjenesten.")
        if r.status_code != 200:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "AI-tjenesten svarte med feil.")
        data = r.json()
        text = "".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text")
        return {"text": text or "Fikk tomt svar."}

    @app.get("/datakvalitet/api/health")
    def health():
        return {"status": "ok"}

    return app
