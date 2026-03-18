"""
YUSO Dashboard - Servidor Flask para Mercado Livre
Porta: 8080 (local) ou Railway (produção)
Suporte a PKCE (OAuth 2.0 com code_verifier)
"""

from flask import Flask, redirect, request, jsonify, session
import requests
import json
import os
import secrets
import hashlib
import base64

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "yuso-secret-key-2024-xK9mP")

# ============================================================
# CONFIGURAÇÕES DO APP MERCADO LIVRE
# ============================================================
CLIENT_ID     = os.environ.get("CLIENT_ID", "1584789193455000")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "Use8WAMLgvKgvVdQZNdXWhGCH4tFbK8n")
PUBLIC_URL    = os.environ.get("PUBLIC_URL", "https://web-production-ff08f.up.railway.app")

REDIRECT_URI  = f"{PUBLIC_URL}/callback"
ML_AUTH_URL   = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL  = "https://api.mercadolibre.com/oauth/token"
ML_API_BASE   = "https://api.mercadolibre.com"

TOKEN_FILE = "ml_token.json"

# ============================================================
# PKCE HELPERS
# ============================================================

def generate_code_verifier():
    """Gera um code_verifier aleatório (64 bytes = ~86 chars base64url)"""
    return secrets.token_urlsafe(64)

def generate_code_challenge(verifier):
    """Gera o code_challenge a partir do verifier (SHA256 + base64url)"""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

# ============================================================
# FUNÇÕES DE TOKEN
# ============================================================

def save_token(token_data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def refresh_token_data(token_data):
    resp = requests.post(ML_TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": token_data["refresh_token"]
    })
    if resp.status_code == 200:
        new_token = resp.json()
        save_token(new_token)
        return new_token
    return None

def get_valid_token():
    return load_token()

def ml_get(path, token):
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    resp = requests.get(f"{ML_API_BASE}{path}", headers=headers)
    if resp.status_code == 401:
        new_token = refresh_token_data(token)
        if new_token:
            headers = {"Authorization": f"Bearer {new_token['access_token']}"}
            resp = requests.get(f"{ML_API_BASE}{path}", headers=headers)
    return resp

# ============================================================
# ROTAS
# ============================================================

@app.route("/")
def index():
    token = get_valid_token()
    if token:
        return f"""
        <html><body style="font-family:sans-serif;padding:40px;background:#F5F6FA;">
        <h2 style="color:#E87722">✅ YUSO Server rodando!</h2>
        <p>Mercado Livre <strong>conectado</strong> — User ID: {token.get('user_id', '?')}</p>
        <p><a href="/api/resumo">Ver dados /api/resumo</a></p>
        <p><a href="/api/pedidos">Ver pedidos /api/pedidos</a></p>
        </body></html>
        """
    else:
        return f"""
        <html><body style="font-family:sans-serif;padding:40px;background:#F5F6FA;">
        <h2 style="color:#E87722">🔗 YUSO Server rodando!</h2>
        <p>Mercado Livre ainda <strong>não conectado</strong>.</p>
        <br>
        <a href="/login" style="background:#E87722;color:white;padding:14px 28px;border-radius:8px;
           text-decoration:none;font-weight:bold;font-size:16px;">Conectar ao Mercado Livre</a>
        </body></html>
        """

@app.route("/login")
def login():
    # Gera PKCE
    verifier   = generate_code_verifier()
    challenge  = generate_code_challenge(verifier)
    session["code_verifier"] = verifier

    auth_url = (
        f"{ML_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&code_challenge={challenge}"
        f"&code_challenge_method=S256"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Erro: código de autorização não encontrado.", 400

    verifier = session.get("code_verifier")
    if not verifier:
        return """
        <html><body style="font-family:sans-serif;padding:40px;">
        <h3 style="color:#E74C3C">⚠️ Sessão expirada</h3>
        <p>A sessão expirou durante a autenticação. Por favor, tente novamente.</p>
        <br><a href="/login" style="background:#E87722;color:white;padding:12px 24px;
        border-radius:8px;text-decoration:none;font-weight:bold;">Tentar novamente</a>
        </body></html>
        """, 400

    resp = requests.post(ML_TOKEN_URL, data={
        "grant_type":    "authorization_code",
        "client_id":     CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code":          code,
        "redirect_uri":  REDIRECT_URI,
        "code_verifier": verifier
    })

    if resp.status_code == 200:
        token_data = resp.json()
        save_token(token_data)
        session.pop("code_verifier", None)
        return """
        <html><body style="font-family:sans-serif;padding:40px;background:#F5F6FA;text-align:center;">
        <div style="max-width:400px;margin:0 auto;padding:40px;background:white;
             border-radius:16px;box-shadow:0 4px 24px rgba(0,0,0,0.08);">
          <div style="font-size:60px;margin-bottom:16px;">✅</div>
          <h2 style="color:#27AE60">Conectado com sucesso!</h2>
          <p style="color:#555;margin-top:8px;">
            Mercado Livre autorizado. Você pode fechar esta janela e voltar ao dashboard.
          </p>
        </div>
        <script>setTimeout(function(){ window.close(); }, 3000);</script>
        </body></html>
        """
    else:
        return f"""
        <html><body style="font-family:sans-serif;padding:40px;">
        <h3 style="color:#E74C3C">Erro ao obter token</h3>
        <pre style="background:#f5f5f5;padding:16px;border-radius:8px;">{resp.text}</pre>
        <br><a href="/login" style="background:#E87722;color:white;padding:12px 24px;
        border-radius:8px;text-decoration:none;font-weight:bold;">Tentar novamente</a>
        </body></html>
        """, 400

@app.route("/status")
def status():
    token = get_valid_token()
    response = jsonify({
        "authenticated": bool(token),
        "user_id": token.get("user_id") if token else None
    })
    response.headers.add("Access-Control-Allow-Origin", "*")
    return response

@app.route("/api/resumo")
def api_resumo():
    token = get_valid_token()
    if not token:
        resp = jsonify({"error": "not_authenticated"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp, 401

    user_id = token.get("user_id")
    orders_resp = ml_get(
        f"/orders/search?seller={user_id}&order.status=paid&limit=50", token
    )

    if orders_resp.status_code == 200:
        results = orders_resp.json().get("results", [])
        total    = sum(float(o.get("total_amount", 0)) for o in results)
        n        = len(results)
        ticket   = total / n if n > 0 else 0
        resp = jsonify({"faturamento": total, "pedidos": n, "ticket_medio": ticket})
    else:
        resp = jsonify({"faturamento": 0, "pedidos": 0, "ticket_medio": 0,
                        "error": orders_resp.text})

    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@app.route("/api/pedidos")
def api_pedidos():
    token = get_valid_token()
    if not token:
        resp = jsonify({"error": "not_authenticated"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp, 401

    user_id     = token.get("user_id")
    orders_resp = ml_get(
        f"/orders/search?seller={user_id}&sort=date_desc&limit=20", token
    )

    resp = jsonify(orders_resp.json() if orders_resp.status_code == 200
                   else {"error": orders_resp.text})
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@app.route("/api/produtos")
def api_produtos():
    token = get_valid_token()
    if not token:
        resp = jsonify({"error": "not_authenticated"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp, 401

    user_id    = token.get("user_id")
    items_resp = ml_get(f"/users/{user_id}/items/search?limit=50", token)

    resp = jsonify(items_resp.json() if items_resp.status_code == 200
                   else {"error": items_resp.text})
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n🚀 YUSO Server iniciando na porta {port}...")
    print(f"🔗 URL pública: {PUBLIC_URL}")
    print(f"🔗 Redirect URI: {REDIRECT_URI}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
