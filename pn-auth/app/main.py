"""pn-auth – Park Nordics felles auth- og tilgangstjeneste (FastAPI).

Én brukerkilde, én innlogging, tilgang per system. Bak nginx på subpath /auth.
Se FELLES_AUTH_spec.md for kontrakten.
"""
# NB: IKKE `from __future__ import annotations` her – FastAPI må kunne lese
# Depends-metadataen i de lokale Annotated-aliasene (Claims/Admin) ved def-tid.

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, EmailStr, Field

from . import db, epost, security
from .config import Settings, load_settings

SYSTEMS = ("oppdrag", "sanksjon", "datakvalitet", "admin")


# ---- Request-/response-modeller -----------------------------------------
class LoginBody(BaseModel):
    brukernavn: str = Field(min_length=1)  # username eller e-post
    passord: str = Field(min_length=1)


class ChangePwdBody(BaseModel):
    gammelt_passord: str = Field(min_length=1)
    nytt_passord: str = Field(min_length=8)


class PermissionsBody(BaseModel):
    oppdrag: bool = False
    sanksjon: bool = False
    datakvalitet: bool = False
    admin: bool = False


class NewUserBody(BaseModel):
    username: str = Field(min_length=1)
    email: EmailStr
    name: str = Field(min_length=1)
    passord: str = Field(min_length=8)
    permissions: PermissionsBody = PermissionsBody()
    must_change_password: bool = True


class ActiveBody(BaseModel):
    active: bool


class ResetPwdBody(BaseModel):
    passord: str | None = Field(default=None, min_length=8)


def _perm_dict(row) -> dict[str, int]:
    return {s: int(row[s]) for s in SYSTEMS}


def _user_public(row) -> dict:
    return {"id": row["id"], "username": row["username"], "email": row["email"],
            "name": row["name"]}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def create_app(settings: Settings | None = None) -> FastAPI:
    cfg = settings or load_settings()
    db.init_schema(cfg.db_path)
    limiter = security.RateLimiter(cfg.login_rate_max, cfg.login_rate_window_s)

    # SIKKERHETSFUNN #1: API-dok eksponeres KUN i DEBUG. I produksjon = ingen Swagger.
    # Rutene bærer hele /auth-prefikset; nginx proxy_pass UTEN trailing slash bevarer
    # stien (jf. BYGGESTANDARD §2). Derfor IKKE root_path her – det ville strippe /auth.
    docs = dict(docs_url="/auth/docs", redoc_url=None, openapi_url="/auth/openapi.json") \
        if cfg.debug else dict(docs_url=None, redoc_url=None, openapi_url=None)
    app = FastAPI(title="pn-auth", version="1.0.0", **docs)
    app.state.cfg = cfg

    if cfg.debug and cfg.dev_cors_origin:
        from fastapi.middleware.cors import CORSMiddleware
        app.add_middleware(
            CORSMiddleware, allow_origins=[cfg.dev_cors_origin],
            allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
        )

    def set_auth_cookie(resp: Response, token: str) -> None:
        resp.set_cookie(
            key=cfg.cookie_name, value=token, max_age=cfg.token_ttl_min * 60,
            httponly=True, secure=cfg.cookie_secure, samesite="lax",
            domain=cfg.cookie_domain, path="/",
        )

    def clear_auth_cookie(resp: Response) -> None:
        resp.delete_cookie(key=cfg.cookie_name, domain=cfg.cookie_domain, path="/")

    # ---- Avhengigheter --------------------------------------------------
    def current_claims(request: Request) -> dict:
        token = request.cookies.get(cfg.cookie_name)
        claims = security.decode_token(token, cfg.auth_secret) if token else None
        if not claims:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ikke innlogget")
        return claims

    def require_admin(claims: Annotated[dict, Depends(current_claims)]) -> dict:
        if not (claims.get("permissions") or {}).get("admin"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Krever admin")
        return claims

    Claims = Annotated[dict, Depends(current_claims)]
    Admin = Annotated[dict, Depends(require_admin)]

    # ---- Innlogging / sesjon -------------------------------------------
    @app.post("/auth/login")
    def login(body: LoginBody, request: Request, response: Response):
        ip = _client_ip(request)
        if not limiter.check(ip):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                                "For mange forsøk. Prøv igjen om litt.")
        conn = db.connect(cfg.db_path)
        try:
            row = db.user_with_permissions(conn, login=body.brukernavn)
        finally:
            conn.close()
        # Samme svar uansett om bruker finnes eller passord er feil (ingen lekkasje).
        if not row or not row["active"] or not security.verify_password(
                body.passord, row["password_hash"]):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Feil brukernavn eller passord")
        limiter.reset(ip)
        perms = _perm_dict(row)
        token = security.make_token(
            secret=cfg.auth_secret, user_id=row["id"], name=row["name"],
            email=row["email"], permissions=perms, ttl_min=cfg.token_ttl_min)
        set_auth_cookie(response, token)
        return {"user": _user_public(row), "permissions": perms,
                "must_change_password": bool(row["must_change_password"])}

    @app.post("/auth/logout")
    def logout(response: Response):
        clear_auth_cookie(response)
        return {"ok": True}

    @app.get("/auth/me")
    def me(claims: Claims, response: Response):
        # Last tilganger på nytt fra DB → endringer (admin ga/fjernet tilgang,
        # deaktivering) slår inn ved neste poll. Samtidig rullerende fornyelse.
        conn = db.connect(cfg.db_path)
        try:
            row = db.user_with_permissions(conn, user_id=int(claims["sub"]))
        finally:
            conn.close()
        if not row or not row["active"]:
            clear_auth_cookie(response)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bruker deaktivert")
        perms = _perm_dict(row)
        token = security.make_token(
            secret=cfg.auth_secret, user_id=row["id"], name=row["name"],
            email=row["email"], permissions=perms, ttl_min=cfg.token_ttl_min)
        set_auth_cookie(response, token)
        return {"user": _user_public(row), "permissions": perms,
                "must_change_password": bool(row["must_change_password"])}

    @app.get("/auth/verify")
    def verify(claims: Claims, system: str = Query(default="")):
        # Stateless – brukes av nginx auth_request for statiske verktøy.
        if system and not security.has_system_access(claims, system):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ingen tilgang")
        return {"ok": True}

    @app.post("/auth/change-password")
    def change_password(body: ChangePwdBody, claims: Claims, response: Response):
        uid = int(claims["sub"])
        conn = db.connect(cfg.db_path)
        try:
            row = db.user_with_permissions(conn, user_id=uid)
            if not row or not security.verify_password(body.gammelt_passord, row["password_hash"]):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Feil nåværende passord")
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 0 WHERE id = ?",
                (security.hash_password(body.nytt_passord), uid))
            conn.commit()
        finally:
            conn.close()
        return {"ok": True}

    # ---- Admin: brukere og tilganger -----------------------------------
    @app.get("/auth/users")
    def list_users(_: Admin):
        conn = db.connect(cfg.db_path)
        try:
            rows = db.list_users(conn)
        finally:
            conn.close()
        return [{**_user_public(r), "active": bool(r["active"]),
                 "must_change_password": bool(r["must_change_password"]),
                 "created_at": r["created_at"], "permissions": _perm_dict(r)} for r in rows]

    @app.post("/auth/users", status_code=status.HTTP_201_CREATED)
    def create_user(body: NewUserBody, admin: Admin):
        actor = int(admin["sub"])
        conn = db.connect(cfg.db_path)
        try:
            try:
                cur = conn.execute(
                    "INSERT INTO users (username, email, name, password_hash, active, "
                    "must_change_password) VALUES (?, ?, ?, ?, 1, ?)",
                    (body.username, str(body.email), body.name,
                     security.hash_password(body.passord), int(body.must_change_password)))
            except Exception:
                raise HTTPException(status.HTTP_409_CONFLICT,
                                    "Brukernavn eller e-post finnes allerede")
            uid = cur.lastrowid
            p = body.permissions
            conn.execute(
                "INSERT INTO permissions (user_id, oppdrag, sanksjon, datakvalitet, admin) "
                "VALUES (?, ?, ?, ?, ?)",
                (uid, int(p.oppdrag), int(p.sanksjon), int(p.datakvalitet), int(p.admin)))
            db.log_change(conn, actor, uid, "opprettet")
            conn.commit()
        finally:
            conn.close()
        # Best effort: send innloggingsinfo. Velter aldri opprettelsen.
        epost_status = epost.send_velkomst(
            cfg, til=str(body.email), navn=body.name, brukernavn=body.username,
            temp_passord=body.passord)
        return {"id": uid, "epost": epost_status}

    @app.put("/auth/users/{uid}/permissions")
    def set_permissions(uid: int, body: PermissionsBody, admin: Admin):
        actor = int(admin["sub"])
        conn = db.connect(cfg.db_path)
        try:
            row = db.user_with_permissions(conn, user_id=uid)
            if not row:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Ukjent bruker")
            new = {"oppdrag": int(body.oppdrag), "sanksjon": int(body.sanksjon),
                   "datakvalitet": int(body.datakvalitet), "admin": int(body.admin)}
            conn.execute(
                "INSERT INTO permissions (user_id, oppdrag, sanksjon, datakvalitet, admin) "
                "VALUES (:uid, :oppdrag, :sanksjon, :datakvalitet, :admin) "
                "ON CONFLICT(user_id) DO UPDATE SET oppdrag=:oppdrag, sanksjon=:sanksjon, "
                "datakvalitet=:datakvalitet, admin=:admin",
                {"uid": uid, **new})
            for s in SYSTEMS:
                if int(row[s]) != new[s]:
                    db.log_change(conn, actor, uid, f"{s}: {int(row[s])}→{new[s]}")
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "permissions": new}

    @app.put("/auth/users/{uid}/active")
    def set_active(uid: int, body: ActiveBody, admin: Admin):
        actor = int(admin["sub"])
        conn = db.connect(cfg.db_path)
        try:
            row = db.user_with_permissions(conn, user_id=uid)
            if not row:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Ukjent bruker")
            conn.execute("UPDATE users SET active = ? WHERE id = ?", (int(body.active), uid))
            db.log_change(conn, actor, uid, "aktivert" if body.active else "deaktivert")
            conn.commit()
        finally:
            conn.close()
        return {"ok": True, "active": body.active}

    @app.post("/auth/users/{uid}/reset-password")
    def reset_password(uid: int, body: ResetPwdBody, admin: Admin):
        import secrets
        actor = int(admin["sub"])
        temp = body.passord or ("Pn-" + secrets.token_urlsafe(9))
        conn = db.connect(cfg.db_path)
        try:
            row = db.user_with_permissions(conn, user_id=uid)
            if not row:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Ukjent bruker")
            conn.execute(
                "UPDATE users SET password_hash = ?, must_change_password = 1 WHERE id = ?",
                (security.hash_password(temp), uid))
            db.log_change(conn, actor, uid, "passord nullstilt")
            conn.commit()
            navn, til = row["name"], row["email"]
        finally:
            conn.close()
        # Best effort: varsle brukeren om nytt midlertidig passord.
        epost_status = epost.send_nullstilt(cfg, til=til, navn=navn, temp_passord=temp)
        # Returner det temporære passordet KUN når admin ikke selv satte ett.
        return {"ok": True, "temp_passord": None if body.passord else temp,
                "epost": epost_status}

    # ---- Helse (robusthet/overvåking, lekker ikke brukerantall) ---------
    @app.get("/auth/health")
    def health():
        return {"status": "ok"}

    return app
