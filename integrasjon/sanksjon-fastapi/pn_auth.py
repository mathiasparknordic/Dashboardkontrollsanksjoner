"""Park Nordic – felles auth for Sanksjon (FastAPI).

Avhengighet som leser pn_auth-cookien, verifiserer JWT stateless med delt AUTH_SECRET
og krever permissions[system] (eller admin). Samme token-kontrakt som pn-auth utsteder.

Dette ERSTATTER Sanksjons egen pn_session-innlogging OG «Brukere med tilgang»-skjermen –
brukeradministrasjon skjer nå bare i portalens admin-skjerm mot pn-auth.

Bruk i Sanksjon:
    from pn_auth import require_sanksjon
    @router.get("/sanksjon/api/sanksjoner")
    def liste(bruker: dict = Depends(require_sanksjon)):
        ...

For HTML-sider: la en 401-handler redirecte uinnloggede til portalen «/» (felles
innlogging), slik at de ikke møter en egen innloggingsskjerm. Se redirect_to_portal().
"""
import os

import jwt
from fastapi import HTTPException, Request, status
from fastapi.responses import RedirectResponse

COOKIE_NAME = os.environ.get("COOKIE_NAME", "pn_auth")
PORTAL_URL = os.environ.get("PORTAL_URL", "/")


def _secret() -> str:
    s = os.environ.get("AUTH_SECRET", "")
    if len(s) < 32:
        # Sikkerhetsbaseline: ingen hardkodet reserve – stopp hvis nøkkel mangler.
        raise RuntimeError("AUTH_SECRET må være satt (min 32 tegn).")
    return s


def current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ikke innlogget")
    try:
        return jwt.decode(token, _secret(), algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Ugyldig eller utløpt token")


def require_system(system: str):
    def dep(request: Request) -> dict:
        claims = current_user(request)
        perms = claims.get("permissions") or {}
        if not (perms.get("admin") or perms.get(system)):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Ingen tilgang til {system}")
        return claims
    return dep


require_sanksjon = require_system("sanksjon")


def redirect_to_portal() -> RedirectResponse:
    """Bruk i en exception-handler for HTML-ruter slik at uinnloggede sendes til portalen.

        @app.exception_handler(401)
        async def _login(request, exc):
            if "text/html" in request.headers.get("accept", ""):
                return redirect_to_portal()
            return JSONResponse({"detail": exc.detail}, status_code=401)
    """
    return RedirectResponse(PORTAL_URL, status_code=302)
