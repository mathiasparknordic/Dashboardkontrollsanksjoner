import os, sys, time
import jwt, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SECRET = "z"*40

def _token(perms):
    return jwt.encode({"sub":1,"name":"T","email":"t@parknordic.no","permissions":perms,
                       "exp":int(time.time())+600}, SECRET, algorithm="HS256")

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test-xyz")
    monkeypatch.setenv("DEBUG", "false")
    import importlib, app as appmod; importlib.reload(appmod)
    # mock Anthropic-kallet
    class FakeResp:
        status_code = 200
        def json(self): return {"content":[{"type":"text","text":"Svar fra AI"}]}
    class FakeClient:
        def __init__(self,*a,**k): pass
        async def __aenter__(self): return self
        async def __aexit__(self,*a): return False
        async def post(self,*a,**k): return FakeResp()
    monkeypatch.setattr(appmod.httpx, "AsyncClient", FakeClient)
    from fastapi.testclient import TestClient
    return TestClient(appmod.create_app())

def test_krever_innlogging(client):
    r = client.post("/datakvalitet/api/chat", json={"messages":[{"role":"user","content":"hei"}]})
    assert r.status_code == 401

def test_krever_datakvalitet_tilgang(client):
    client.cookies.set("pn_auth", _token({"sanksjon":1}))
    r = client.post("/datakvalitet/api/chat", json={"messages":[{"role":"user","content":"hei"}]})
    assert r.status_code == 403

def test_chat_med_tilgang_returnerer_tekst(client):
    client.cookies.set("pn_auth", _token({"datakvalitet":1}))
    r = client.post("/datakvalitet/api/chat", json={"system":"ctx","messages":[{"role":"user","content":"hei"}]})
    assert r.status_code == 200 and r.json()["text"] == "Svar fra AI"

def test_admin_har_tilgang(client):
    client.cookies.set("pn_auth", _token({"admin":1}))
    r = client.post("/datakvalitet/api/chat", json={"messages":[{"role":"user","content":"hei"}]})
    assert r.status_code == 200

def test_health(client):
    assert client.get("/datakvalitet/api/health").json()["status"] == "ok"

def test_secret_or_die(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "kort")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "x")
    import importlib, app as appmod; importlib.reload(appmod)
    with pytest.raises(RuntimeError):
        appmod.Settings()

def test_mangler_anthropic_nokkel_stopper(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    import importlib, app as appmod; importlib.reload(appmod)
    with pytest.raises(RuntimeError):
        appmod.Settings()
