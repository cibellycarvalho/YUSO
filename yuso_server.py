"""
YUSO Dashboard - Servidor Flask para Mercado Livre
Porta: 8080
"""

from flask import Flask, redirect, request, jsonify, session
import requests
import json
import os

app = Flask(__name__)
app.secret_key = 'yuso-secret-key-2024'

# ============================================================
# CONFIGURAÇÕES DO APP MERCADO LIVRE
# ============================================================
CLIENT_ID = "1584789193455000"
CLIENT_SECRET = "Use8WAMLgvKgvVdQZNdXWhGCH4tFbK8n"

# Quando usar Railway, troque o NGROK_URL pela URL do Railway
# Ex: NGROK_URL = "https://yuso-server.up.railway.app"
NGROK_URL = os.environ.get("PUBLIC_URL", "https://inexorable-photoperiodic-doria.ngrok-free.dev")

REDIRECT_URI = f"{NGROK_URL}/callback"
ML_AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
ML_API_BASE = "https://api.mercadolibre.com"

TOKEN_FILE = "ml_token.json"

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

def refresh_token(token_data):
    resp = requests.post(ML_TOKEN_URL, data={
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "refresh_token": token_data["refresh_token"]
    })
    if resp.status_code == 200:
        new_token = resp.json()
        save_token(new_token)
        return new_token
    return None

def get_valid_token():
    token = load_token()
    if not token:
        return None
    # Tenta usar; se der 401, faz refresh
    return token

def ml_get(path, token):
    headers = {"Authorization": f"Bearer {token['access_token']}"}
    resp = requests.get(f"{ML_API_BASE}{path}", headers=headers)
    if resp.status_code == 401:
        # Token expirado, tenta refresh
        new_token = refresh_token(token)
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
        <p><a href="/login" style="background:#E87722;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold;">Conectar ao Mercado Livre</a></p>
        </body></html>
        """

@app.route("/login")
def login():
    auth_url = (
        f"{ML_AUTH_URL}"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return redirect(auth_url)

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code:
        return "Erro: código de autorização não encontrado.", 400

    resp = requests.post(ML_TOKEN_URL, data={
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    })

    if resp.status_code == 200:
        token_data = resp.json()
        save_token(token_data)
        return """
        <html><body style="font-family:sans-serif;padding:40px;background:#F5F6FA;text-align:center;">
        <h2 style="color:#27AE60">✅ Conectado com sucesso!</h2>
        <p>Mercado Livre autorizado. Pode fechar esta janela.</p>
        <p>Volte ao <a href="javascript:window.close()">dashboard</a> e atualize a página.</p>
        <script>
          // Tenta fechar automaticamente após 3 segundos
          setTimeout(function(){ window.close(); }, 3000);
        </script>
        </body></html>
        """
    else:
        return f"Erro ao obter token: {resp.text}", 400

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
    # Busca dados de vendas do último mês
    orders_resp = ml_get(f"/orders/search?seller={user_id}&order.status=paid&limit=50", token)

    if orders_resp.status_code == 200:
        orders = orders_resp.json()
        results = orders.get("results", [])
        total = sum(float(o.get("total_amount", 0)) for o in results)
        n_pedidos = len(results)
        ticket = total / n_pedidos if n_pedidos > 0 else 0
        resp = jsonify({
            "faturamento": total,
            "pedidos": n_pedidos,
            "ticket_medio": ticket
        })
    else:
        resp = jsonify({"faturamento": 0, "pedidos": 0, "ticket_medio": 0, "error": orders_resp.text})

    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@app.route("/api/pedidos")
def api_pedidos():
    token = get_valid_token()
    if not token:
        resp = jsonify({"error": "not_authenticated"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp, 401

    user_id = token.get("user_id")
    orders_resp = ml_get(f"/orders/search?seller={user_id}&sort=date_desc&limit=20", token)

    if orders_resp.status_code == 200:
        data = orders_resp.json()
        resp = jsonify(data)
    else:
        resp = jsonify({"error": orders_resp.text})

    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

@app.route("/api/produtos")
def api_produtos():
    token = get_valid_token()
    if not token:
        resp = jsonify({"error": "not_authenticated"})
        resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp, 401

    user_id = token.get("user_id")
    items_resp = ml_get(f"/users/{user_id}/items/search?limit=50", token)

    if items_resp.status_code == 200:
        data = items_resp.json()
        resp = jsonify(data)
    else:
        resp = jsonify({"error": items_resp.text})

    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp

# ============================================================
# INICIAR SERVIDOR
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n🚀 YUSO Server iniciando na porta {port}...")
    print(f"🔗 Acesse: http://127.0.0.1:{port}")
    print(f"🔗 URL pública: {NGROK_URL}")
    print(f"🔗 Redirect URI configurada: {REDIRECT_URI}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
