"""
YUSO Dashboard - Servidor Flask com dashboard integrado
Histórico real por mês via API do Mercado Livre
"""

from flask import Flask, redirect, request, jsonify, session, Response
import requests, json, os, secrets, hashlib, base64
from datetime import datetime, timedelta
from calendar import monthrange

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "yuso-secret-key-2024-xK9mP")

CLIENT_ID     = os.environ.get("CLIENT_ID", "1584789193455000")
CLIENT_SECRET = os.environ.get("CLIENT_SECRET", "Use8WAMLgvKgvVdQZNdXWhGCH4tFbK8n")
PUBLIC_URL    = os.environ.get("PUBLIC_URL", "https://web-production-ff08f.up.railway.app")
REDIRECT_URI  = f"{PUBLIC_URL}/callback"
ML_AUTH_URL   = "https://auth.mercadolivre.com.br/authorization"
ML_TOKEN_URL  = "https://api.mercadolibre.com/oauth/token"
ML_API_BASE   = "https://api.mercadolibre.com"
TOKEN_FILE    = "ml_token.json"

def generate_code_verifier():
    return secrets.token_urlsafe(64)

def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b'=').decode()

def save_token(t):
    with open(TOKEN_FILE, "w") as f: json.dump(t, f)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f: return json.load(f)
    return None

def refresh_token_data(t):
    r = requests.post(ML_TOKEN_URL, data={
        "grant_type":"refresh_token","client_id":CLIENT_ID,
        "client_secret":CLIENT_SECRET,"refresh_token":t["refresh_token"]
    })
    if r.status_code == 200:
        nt = r.json(); save_token(nt); return nt
    return None

def ml_get(path, token):
    h = {"Authorization": f"Bearer {token['access_token']}"}
    r = requests.get(f"{ML_API_BASE}{path}", headers=h)
    if r.status_code == 401:
        nt = refresh_token_data(token)
        if nt:
            h = {"Authorization": f"Bearer {nt['access_token']}"}
            r = requests.get(f"{ML_API_BASE}{path}", headers=h)
    return r

def cors(data, status=200):
    r = jsonify(data)
    r.headers.add("Access-Control-Allow-Origin", "*")
    r.status_code = status
    return r

# ── DASHBOARD HTML ────────────────────────────────────────────
HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>YUSO Dashboard</title>
<style>
:root{--acc:#E87722;--acc-l:#FFF3E8;--td:#1A1A1A;--tm:#555;--tl:#888;--bg:#F5F6FA;--card:#fff;--bdr:#E8E8E8;--grn:#27AE60;--amb:#F39C12;--red:#E74C3C;--blu:#2980B9;}
*{box-sizing:border-box;margin:0;padding:0;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--td);display:flex;height:100vh;overflow:hidden;}
.sb{width:220px;background:#fff;border-right:1.5px solid var(--bdr);display:flex;flex-direction:column;height:100vh;overflow-y:auto;flex-shrink:0;}
.logo{padding:24px 20px 16px;border-bottom:1px solid var(--bdr);}
.logo-t{font-size:22px;font-weight:800;color:var(--acc);letter-spacing:2px;}
.logo-s{font-size:10px;color:var(--tl);text-transform:uppercase;letter-spacing:1px;margin-top:2px;}
.ns{font-size:9px;font-weight:700;color:var(--tl);letter-spacing:1.5px;text-transform:uppercase;padding:12px 20px 4px;}
.ni{display:flex;align-items:center;gap:10px;padding:10px 20px;cursor:pointer;font-size:13px;color:var(--tm);font-weight:500;border-left:3px solid transparent;transition:all .15s;text-decoration:none;}
.ni:hover{background:var(--acc-l);color:var(--acc);}
.ni.active{color:var(--td);border-left-color:var(--acc);background:var(--acc-l);font-weight:700;}
.sf{padding:14px 20px;border-top:1px solid var(--bdr);font-size:11px;color:var(--tl);margin-top:auto;}
.dot{width:8px;height:8px;border-radius:50%;background:#ccc;display:inline-block;margin-right:5px;}
.dot.on{background:var(--grn);}
.main{flex:1;overflow-y:auto;display:flex;flex-direction:column;}
.tb{background:#fff;border-bottom:1px solid var(--bdr);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.tb-t{font-size:18px;font-weight:700;}
.tb-s{font-size:12px;color:var(--tl);margin-top:2px;}
.tr{display:flex;align-items:center;gap:12px;}
.bdg{background:var(--acc-l);color:var(--acc);padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700;}
.bdg.grn{background:#E8F8F0;color:var(--grn);}
.bdg.red{background:#FDEDEC;color:var(--red);}
.cnt{padding:24px 28px;flex:1;}
.cr{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;}
.card{background:var(--card);border-radius:12px;border:1px solid var(--bdr);padding:20px;flex:1;min-width:150px;}
.cl{font-size:11px;color:var(--tl);font-weight:600;text-transform:uppercase;letter-spacing:.5px;}
.cv{font-size:24px;font-weight:800;margin:6px 0 2px;}
.cc{font-size:12px;font-weight:600;color:var(--tl);}
.cc.up{color:var(--grn);} .cc.dn{color:var(--red);}
.chrow{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;}
.cc2{background:var(--card);border-radius:12px;border:1px solid var(--bdr);padding:20px;}
.ct{font-size:13px;font-weight:700;margin-bottom:4px;}
.cs{font-size:11px;color:var(--tl);margin-bottom:12px;}
.tc{background:var(--card);border-radius:12px;border:1px solid var(--bdr);overflow:hidden;margin-bottom:20px;}
.th{padding:14px 20px;border-bottom:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between;}
.tt{font-size:13px;font-weight:700;}
table{width:100%;border-collapse:collapse;}
th{font-size:11px;color:var(--tl);text-transform:uppercase;padding:10px 20px;text-align:left;background:#FAFAFA;border-bottom:1px solid var(--bdr);}
td{font-size:13px;padding:11px 20px;border-bottom:1px solid var(--bdr);}
tr:last-child td{border-bottom:none;}
tr:hover td{background:#FAFBFF;}
.p{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700;}
.pg{background:#E8F8F0;color:var(--grn);} .pa{background:#FEF9E7;color:var(--amb);}
.pr{background:#FDEDEC;color:var(--red);} .pb{background:#EAF4FB;color:var(--blu);}
.py{background:#F2F2F2;color:var(--tl);}
.page{display:none;} .page.active{display:block;}
.pb2{background:#F0F0F0;border-radius:4px;height:8px;overflow:hidden;}
.pf{height:100%;border-radius:4px;}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:16px;}
.al{border-radius:10px;padding:14px 18px;font-size:13px;margin-bottom:16px;display:flex;align-items:flex-start;gap:12px;}
.aw{background:#FEF9E7;border:1px solid #F9E4A0;color:#7D6608;}
.as{background:#E8F8F0;border:1px solid #A9DFBF;color:#1E6040;}
.btn{padding:9px 18px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;border:none;transition:all .15s;}
.bp{background:var(--acc);color:white;} .bp:hover{background:#c9600f;}
.bo{background:white;color:var(--td);border:1.5px solid var(--bdr);text-decoration:none;display:inline-block;}
.lod{text-align:center;color:var(--tl);padding:28px;font-size:13px;}
.gw{display:flex;flex-direction:column;align-items:center;}
.gv{font-size:26px;font-weight:800;margin-top:4px;}
.spin{display:inline-block;animation:spin 1s linear infinite;}
@keyframes spin{from{transform:rotate(0deg)}to{transform:rotate(360deg)}}
</style>
</head>
<body>
<aside class="sb">
  <div class="logo"><div class="logo-t">YUSO</div><div class="logo-s">Marketplace ML</div></div>
  <nav style="padding:10px 0;flex:1">
    <div class="ns">Visão Geral</div>
    <a class="ni active" data-page="resumo" href="#">📊 Resumo</a>
    <div class="ns">Vendas & Produtos</div>
    <a class="ni" data-page="vendas" href="#">🛒 Vendas</a>
    <a class="ni" data-page="produtos" href="#">📦 Produtos</a>
    <div class="ns">Marketing</div>
    <a class="ni" data-page="ads" href="#">📣 Campanhas / ADS</a>
    <a class="ni" data-page="margem" href="#">💰 Margem pós-ADS</a>
    <div class="ns">Inteligência</div>
    <a class="ni" data-page="ranqueamento" href="#">🏆 Ranqueamento</a>
    <a class="ni" data-page="pesquisa" href="#">🔍 Pesquisa de Mercado</a>
    <div class="ns">Gestão</div>
    <a class="ni" data-page="financeiro" href="#">💳 Financeiro</a>
    <a class="ni" data-page="integracoes" href="#">🔗 Integrações</a>
  </nav>
  <div class="sf">
    <span class="dot" id="dot"></span><span id="mls">Verificando...</span>
    <div style="font-size:10px;margin-top:3px;" id="upd"></div>
  </div>
</aside>

<main class="main">

<!-- RESUMO -->
<div id="page-resumo" class="page active">
  <div class="tb">
    <div><div class="tb-t">Resumo Geral</div><div class="tb-s">Dados reais do Mercado Livre</div></div>
    <div class="tr"><span class="bdg" id="bdg">Carregando...</span><button class="btn bp" onclick="init()">↻ Atualizar</button></div>
  </div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Faturamento</div><div class="cv" id="k-fat">—</div><div class="cc" id="k-fat-per">Mês atual</div></div>
      <div class="card"><div class="cl">Pedidos</div><div class="cv" id="k-ped">—</div><div class="cc">Mês atual</div></div>
      <div class="card"><div class="cl">Ticket Médio</div><div class="cv" id="k-tkt">—</div><div class="cc">Por pedido</div></div>
      <div class="card"><div class="cl">Produtos</div><div class="cv" id="k-prod">—</div><div class="cc up">No catálogo</div></div>
      <div class="card"><div class="cl">Reputação</div><div class="cv" style="color:var(--grn)">🟢</div><div class="cc up">Verde / Ótima</div></div>
    </div>

    <div class="chrow">
      <!-- DONUT HISTÓRICO REAL -->
      <div class="cc2" style="flex:1.3">
        <div class="ct">Faturamento por Mês — Dados Reais</div>
        <div class="cs" id="hist-sub">⏳ Buscando histórico do Mercado Livre...</div>
        <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap" id="hist-wrap">
          <div style="display:flex;align-items:center;justify-content:center;width:160px;height:160px;">
            <span class="spin" style="font-size:32px">⏳</span>
          </div>
          <div id="hist-legend" style="display:flex;flex-direction:column;gap:7px;font-size:12px;color:var(--tl)">
            Carregando histórico real...
          </div>
        </div>
      </div>

      <!-- TACOS GAUGE -->
      <div class="cc2" style="flex:0.8">
        <div class="ct">TACOS</div><div class="cs">Total Advertising Cost of Sale</div>
        <div class="gw">
          <svg width="190" height="112" viewBox="0 0 200 120">
            <path d="M 20,108 A 80,80 0 0,1 180,108" fill="none" stroke="#F0F0F0" stroke-width="18" stroke-linecap="round"/>
            <path d="M 20,108 A 80,80 0 0,1 100,28" fill="none" stroke="#27AE60" stroke-width="18" stroke-linecap="round" opacity=".85"/>
            <path d="M 100,28 A 80,80 0 0,1 180,108" fill="none" stroke="#F39C12" stroke-width="18" stroke-linecap="round" opacity=".85"/>
            <text x="22" y="118" font-size="9" fill="#27AE60" font-weight="700">0%</text>
            <text x="90" y="22" font-size="9" fill="#888" text-anchor="middle">5%</text>
            <text x="174" y="118" font-size="9" fill="#F39C12" font-weight="700">10%</text>
            <line x1="100" y1="108" x2="103" y2="32" stroke="#1A1A1A" stroke-width="2.5" stroke-linecap="round" id="needle-line"/>
            <circle cx="100" cy="108" r="6" fill="#1A1A1A"/>
            <circle cx="100" cy="108" r="3" fill="white"/>
          </svg>
          <div class="gv" id="tacos-val" style="color:var(--grn)">—</div>
          <div style="font-size:11px;color:var(--tl)" id="tacos-desc">Calculando...</div>
          <div style="display:flex;gap:16px;margin-top:10px">
            <div style="text-align:center"><div style="font-size:10px;color:var(--tl)">Faturamento</div><div style="font-size:13px;font-weight:700" id="tacos-fat">—</div></div>
          </div>
        </div>
      </div>

      <!-- PERFORMANCE -->
      <div class="cc2" style="flex:0.8">
        <div class="ct">Performance da Loja</div><div class="cs">Métricas principais</div>
        <div style="display:flex;flex-direction:column;gap:12px;margin-top:4px">
          <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Satisfação clientes</span><span style="font-weight:700">97,4%</span></div><div class="pb2"><div class="pf" style="width:97%;background:var(--grn)"></div></div></div>
          <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Produtos publicados</span><span style="font-weight:700" id="perf-p">—</span></div><div class="pb2"><div class="pf" id="perf-pb" style="width:0%;background:var(--blu)"></div></div></div>
          <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Pedidos no mês</span><span style="font-weight:700" id="perf-ped">—</span></div><div class="pb2"><div class="pf" id="perf-pedb" style="width:0%;background:var(--acc)"></div></div></div>
        </div>
      </div>
    </div>

    <div class="tc">
      <div class="th"><span class="tt">📦 Pedidos Recentes — Dados Reais ML</span><button class="btn bo" onclick="showPage('vendas')">Ver todos →</button></div>
      <table><thead><tr><th>#Pedido</th><th>Produto</th><th>Comprador</th><th>Valor</th><th>Data</th><th>Status</th></tr></thead>
      <tbody id="t-res"><tr><td colspan="6" class="lod">⏳ Carregando...</td></tr></tbody></table>
    </div>
  </div>
</div>

<!-- VENDAS -->
<div id="page-vendas" class="page">
  <div class="tb"><div><div class="tb-t">Vendas</div><div class="tb-s">Pedidos reais do Mercado Livre</div></div>
  <div class="tr"><button class="btn bp" onclick="loadPedidos()">↻ Atualizar</button></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Pedidos</div><div class="cv" id="v-ped">—</div><div class="cc up">Dados reais</div></div>
      <div class="card"><div class="cl">Receita</div><div class="cv" id="v-fat">—</div><div class="cc up">Dados reais</div></div>
      <div class="card"><div class="cl">Ticket Médio</div><div class="cv" id="v-tkt">—</div><div class="cc">Por pedido</div></div>
      <div class="card"><div class="cl">Confirmados</div><div class="cv" id="v-ok" style="color:var(--grn)">—</div><div class="cc up">Pagos/entregues</div></div>
      <div class="card"><div class="cl">Cancelados</div><div class="cv" id="v-can" style="color:var(--red)">—</div><div class="cc dn">Verificar</div></div>
    </div>
    <div class="tc"><div class="th"><span class="tt">Todos os Pedidos</span></div>
    <table><thead><tr><th>#Pedido</th><th>Produto</th><th>Comprador</th><th>Valor</th><th>Data</th><th>Status</th></tr></thead>
    <tbody id="t-ven"><tr><td colspan="6" class="lod">⏳ Carregando...</td></tr></tbody></table></div>
  </div>
</div>

<!-- PRODUTOS -->
<div id="page-produtos" class="page">
  <div class="tb"><div><div class="tb-t">Produtos</div><div class="tb-s">Catálogo ativo no Mercado Livre</div></div>
  <div class="tr"><button class="btn bp" onclick="loadProdutos()">↻ Atualizar</button></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Total</div><div class="cv" id="p-tot">—</div><div class="cc">Catálogo</div></div>
      <div class="card"><div class="cl">Ativos</div><div class="cv" id="p-at" style="color:var(--grn)">—</div><div class="cc up">Publicados</div></div>
      <div class="card"><div class="cl">Pausados</div><div class="cv" id="p-pa" style="color:var(--amb)">—</div><div class="cc">Verificar</div></div>
      <div class="card"><div class="cl">Sem Estoque</div><div class="cv" id="p-se" style="color:var(--red)">—</div><div class="cc dn">Repor</div></div>
    </div>
    <div class="tc"><div class="th"><span class="tt">Catálogo de Produtos</span></div>
    <table><thead><tr><th>Título</th><th>ID ML</th><th>Preço</th><th>Estoque</th><th>Status</th></tr></thead>
    <tbody id="t-prod"><tr><td colspan="5" class="lod">⏳ Carregando...</td></tr></tbody></table></div>
  </div>
</div>

<!-- ADS -->
<div id="page-ads" class="page">
  <div class="tb"><div><div class="tb-t">Campanhas / ADS</div><div class="tb-s">Product Ads · Mercado Livre</div></div><div class="tr"><span class="bdg" id="tacos-badge">TACOS: —</span></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">TACOS</div><div class="cv" id="ads-tacos">—</div><div class="cc">% do faturamento</div></div>
      <div class="card"><div class="cl">Faturamento</div><div class="cv" id="ads-fat">—</div><div class="cc">Período atual</div></div>
      <div class="card"><div class="cl">Pedidos</div><div class="cv" id="ads-ped">—</div><div class="cc">Confirmados</div></div>
    </div>
    <div class="al aw" id="ads-alert" style="display:none"><span>⚠️</span><span id="ads-alert-txt"></span></div>
    <div class="tc"><div class="th"><span class="tt">Histórico Mensal Real</span></div>
    <table><thead><tr><th>Mês</th><th>Faturamento</th><th>Pedidos</th><th>Ticket Médio</th></tr></thead>
    <tbody id="t-hist"><tr><td colspan="4" class="lod">⏳ Carregando histórico...</td></tr></tbody></table></div>
  </div>
</div>

<!-- MARGEM -->
<div id="page-margem" class="page">
  <div class="tb"><div><div class="tb-t">Margem pós-ADS</div><div class="tb-s">Lucratividade real estimada</div></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Faturamento Total</div><div class="cv" id="mg-fat">—</div><div class="cc">6 meses reais</div></div>
      <div class="card"><div class="cl">Taxas ML ~12%</div><div class="cv" id="mg-taxas" style="color:var(--red)">—</div><div class="cc dn">Estimado</div></div>
      <div class="card"><div class="cl">CMV ~35%</div><div class="cv" id="mg-cmv" style="color:var(--red)">—</div><div class="cc dn">Estimado</div></div>
      <div class="card"><div class="cl">Lucro Estimado</div><div class="cv" id="mg-lucro" style="color:var(--grn)">—</div><div class="cc up">~53% de margem</div></div>
    </div>
    <div class="cc2"><div class="ct">Composição da Margem</div><div class="cs">Estimativa baseada nos seus dados reais</div>
      <div style="display:flex;flex-direction:column;gap:12px;margin-top:6px">
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:var(--grn);font-weight:700">Lucro Líquido</span><span>~53%</span></div><div class="pb2"><div class="pf" style="width:53%;background:var(--grn)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:var(--amb);font-weight:700">CMV (produto)</span><span>~35%</span></div><div class="pb2"><div class="pf" style="width:35%;background:var(--amb)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:var(--red);font-weight:700">Taxas ML</span><span>~12%</span></div><div class="pb2"><div class="pf" style="width:12%;background:var(--red)"></div></div></div>
      </div>
      <p style="font-size:11px;color:var(--tl);margin-top:14px">💡 Os percentuais de CMV e taxas são estimativas. Para maior precisão, ajuste conforme seus custos reais.</p>
    </div>
  </div>
</div>

<!-- RANQUEAMENTO -->
<div id="page-ranqueamento" class="page">
  <div class="tb"><div><div class="tb-t">Ranqueamento</div><div class="tb-s">Posição no Mercado Livre</div></div></div>
  <div class="cnt">
    <div class="cc2"><div class="ct">Fatores de Ranqueamento</div><div class="cs">Impacto no posicionamento</div>
      <div style="display:flex;flex-direction:column;gap:12px;margin-top:6px">
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Reputação</span><span style="color:var(--grn);font-weight:700">Verde ✅</span></div><div class="pb2"><div class="pf" style="width:97%;background:var(--grn)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Velocidade de envio</span><span style="color:var(--grn);font-weight:700">Excelente</span></div><div class="pb2"><div class="pf" style="width:90%;background:var(--grn)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Qualidade dos títulos</span><span style="color:var(--amb);font-weight:700">Melhorar</span></div><div class="pb2"><div class="pf" style="width:65%;background:var(--amb)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Fotos profissionais</span><span style="color:var(--amb);font-weight:700">Melhorar</span></div><div class="pb2"><div class="pf" style="width:60%;background:var(--amb)"></div></div></div>
      </div>
    </div>
  </div>
</div>

<!-- PESQUISA -->
<div id="page-pesquisa" class="page">
  <div class="tb"><div><div class="tb-t">Pesquisa de Mercado</div><div class="tb-s">Oportunidades e concorrência</div></div></div>
  <div class="cnt">
    <div class="g2">
      <div class="cc2"><div class="ct">🔥 Categorias em Alta</div><div class="cs">Crescimento (30 dias)</div>
        <div style="display:flex;flex-direction:column;gap:10px;margin-top:6px">
          <div><div style="display:flex;justify-content:space-between;margin-bottom:3px;font-size:12px"><span>Carregadores GaN</span><span style="color:var(--grn);font-weight:700">+84%</span></div><div class="pb2"><div class="pf" style="width:84%;background:var(--grn)"></div></div></div>
          <div><div style="display:flex;justify-content:space-between;margin-bottom:3px;font-size:12px"><span>Hub USB-C Multiporta</span><span style="color:var(--grn);font-weight:700">+67%</span></div><div class="pb2"><div class="pf" style="width:67%;background:var(--grn)"></div></div></div>
          <div><div style="display:flex;justify-content:space-between;margin-bottom:3px;font-size:12px"><span>Suporte Monitor Gamer</span><span style="color:var(--blu);font-weight:700">+45%</span></div><div class="pb2"><div class="pf" style="width:45%;background:var(--blu)"></div></div></div>
        </div>
      </div>
      <div class="cc2"><div class="ct">🎯 Oportunidades</div><div class="cs">Alta demanda + baixa concorrência</div>
        <div style="display:flex;flex-direction:column;gap:10px;margin-top:6px">
          <div style="background:var(--acc-l);border-radius:8px;padding:12px"><div style="font-size:13px;font-weight:700">Cabo USB4 Gen 3</div><div style="font-size:11px;color:var(--tm);margin-top:2px">12 vendedores · 8.400 buscas/mês</div></div>
          <div style="background:#F0FFF4;border-radius:8px;padding:12px"><div style="font-size:13px;font-weight:700">Carregador Wireless 30W</div><div style="font-size:11px;color:var(--tm);margin-top:2px">8 vendedores · 6.100 buscas/mês</div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- FINANCEIRO -->
<div id="page-financeiro" class="page">
  <div class="tb"><div><div class="tb-t">Financeiro</div><div class="tb-s">Repasses e fluxo de caixa estimado</div></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Faturamento Total</div><div class="cv" id="fin-fat">—</div><div class="cc">6 meses reais</div></div>
      <div class="card"><div class="cl">Taxas ML (~12%)</div><div class="cv" id="fin-taxas" style="color:var(--red)">—</div><div class="cc dn">Estimado</div></div>
      <div class="card"><div class="cl">Líquido estimado</div><div class="cv" id="fin-liq" style="color:var(--grn)">—</div><div class="cc up">Após taxas ML</div></div>
      <div class="card"><div class="cl">Total Pedidos</div><div class="cv" id="fin-ped">—</div><div class="cc">6 meses</div></div>
    </div>
    <div class="tc"><div class="th"><span class="tt">Histórico Mensal Real</span></div>
    <table><thead><tr><th>Mês</th><th>Faturamento</th><th>Pedidos</th><th>Taxas ML (est.)</th><th>Líquido (est.)</th></tr></thead>
    <tbody id="t-fin"><tr><td colspan="5" class="lod">⏳ Carregando histórico...</td></tr></tbody></table></div>
  </div>
</div>

<!-- INTEGRAÇÕES -->
<div id="page-integracoes" class="page">
  <div class="tb"><div><div class="tb-t">Integrações</div><div class="tb-s">Conexões externas</div></div></div>
  <div class="cnt">
    <div class="al as" id="al-on" style="display:none"><span>✅</span><div><strong>Mercado Livre conectado!</strong> Dados atualizados automaticamente.</div></div>
    <div class="al aw" id="al-off"><span>⚠️</span><div><strong>Mercado Livre desconectado.</strong><br><a href="/login" style="color:var(--acc);font-weight:700">Clique aqui para conectar</a></div></div>
    <div style="background:var(--card);border-radius:12px;border:1px solid var(--bdr);padding:20px;margin-bottom:12px;display:flex;align-items:center;justify-content:space-between">
      <div style="display:flex;align-items:center;gap:14px">
        <div style="width:44px;height:44px;border-radius:10px;background:#FFF3CD;display:flex;align-items:center;justify-content:center;font-size:22px">🛒</div>
        <div><div style="font-size:14px;font-weight:700">Mercado Livre</div><div style="font-size:12px;color:var(--tl)">Pedidos, produtos e métricas em tempo real</div></div>
      </div>
      <div style="display:flex;align-items:center;gap:10px">
        <span id="ml-pill" class="p pa">Verificando...</span>
        <a href="/login" class="btn bo">Reconectar</a>
      </div>
    </div>
    <div class="cc2"><div class="ct">🌐 Servidor Railway</div><div class="cs">Rodando 24h na nuvem</div>
      <div style="background:#F5F6FA;border-radius:8px;padding:14px;font-family:monospace;font-size:12px;line-height:2">
        URL: <strong style="color:var(--acc)">https://web-production-ff08f.up.railway.app</strong><br>
        Status: <strong id="srv-st">—</strong> &nbsp;|&nbsp; User ML: <strong id="srv-uid">—</strong><br>
        Última atualização: <strong id="srv-upd">—</strong>
      </div>
    </div>
  </div>
</div>

</main>
<script>
var CORES=['#E87722','#F39C12','#27AE60','#2980B9','#8E44AD','#E74C3C','#16A085','#D35400'];
var historicoGlobal=[];

document.querySelectorAll('.ni').forEach(function(el){
  el.addEventListener('click',function(e){e.preventDefault();showPage(this.getAttribute('data-page'));});
});
function showPage(n){
  document.querySelectorAll('.page').forEach(function(p){p.classList.remove('active');});
  document.querySelectorAll('.ni').forEach(function(x){x.classList.remove('active');});
  var pg=document.getElementById('page-'+n); if(pg) pg.classList.add('active');
  var nav=document.querySelector('[data-page="'+n+'"]'); if(nav) nav.classList.add('active');
}
function fmt(n){n=parseFloat(n||0);if(n>=1000)return'R$ '+(n/1000).toFixed(1)+'k';return'R$ '+n.toFixed(2);}
function fmt2(n){n=parseFloat(n||0);return'R$ '+n.toLocaleString('pt-BR',{minimumFractionDigits:2,maximumFractionDigits:2});}
function s(id,v){var e=document.getElementById(id);if(e)e.textContent=v;}
function sh(id,h){var e=document.getElementById(id);if(e)e.innerHTML=h;}
function pill(st){
  var m={'paid':'<span class="p pb">Pago</span>','confirmed':'<span class="p pb">Confirmado</span>',
         'delivered':'<span class="p pg">Entregue</span>','shipped':'<span class="p pa">Transporte</span>',
         'cancelled':'<span class="p pr">Cancelado</span>'};
  return m[st]||'<span class="p py">'+(st||'?')+'</span>';
}

function checkStatus(){
  fetch('/status').then(function(r){return r.json();}).then(function(d){
    updateUI(d.authenticated,d.user_id);
    if(d.authenticated){loadPedidos();loadProdutos();loadHistorico();}
  }).catch(function(){updateUI(false);});
}

function updateUI(on,uid){
  var now=new Date().toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'});
  document.getElementById('dot').className='dot'+(on?' on':'');
  s('mls',on?'🟢 ML Conectado':'🔴 Desconectado');
  s('upd','Atualizado às '+now);
  var bdg=document.getElementById('bdg');
  if(bdg){bdg.textContent=on?'✅ ML Conectado':'Desconectado';bdg.className='bdg '+(on?'grn':'red');}
  var mp=document.getElementById('ml-pill');
  if(mp){mp.textContent=on?'Conectado ✅':'Desconectado';mp.className='p '+(on?'pg':'pr');}
  var ao=document.getElementById('al-on'),af=document.getElementById('al-off');
  if(ao)ao.style.display=on?'flex':'none';
  if(af)af.style.display=on?'none':'flex';
  s('srv-st',on?'🟢 Online':'🔴 Offline');
  s('srv-uid',uid||'—'); s('srv-upd',now);
}

// ── HISTÓRICO REAL ───────────────────────────────────────────
function loadHistorico(){
  fetch('/api/historico').then(function(r){return r.json();}).then(function(data){
    if(!data.meses||!data.meses.length){
      s('hist-sub','Sem dados históricos disponíveis.');
      return;
    }
    historicoGlobal=data.meses;
    renderDonut(data.meses);
    renderHistoricoTabelas(data.meses);
    calcularMargem(data.meses);
    calcularFinanceiro(data.meses);
    calcularTACOS(data.meses);
  }).catch(function(e){
    s('hist-sub','Erro ao buscar histórico: '+e.message);
  });
}

function renderDonut(meses){
  var total=meses.reduce(function(a,m){return a+m.faturamento;},0);
  if(total===0){s('hist-sub','Sem vendas no período.');return;}

  var circ=2*Math.PI*70; // circunferência
  var offset=0;
  var svgCircles='';
  var legend='';

  meses.forEach(function(m,i){
    var pct=m.faturamento/total;
    var dash=pct*circ;
    var cor=CORES[i%CORES.length];
    // stroke-dashoffset começa do topo (rotação -90°)
    svgCircles+='<circle cx="90" cy="90" r="70" fill="none" stroke="'+cor+'" stroke-width="22"'+
      ' stroke-dasharray="'+dash.toFixed(1)+' '+(circ-dash).toFixed(1)+'"'+
      ' stroke-dashoffset="'+(-(offset)).toFixed(1)+'"'+
      ' transform="rotate(-90 90 90)"/>';
    offset+=dash;
    legend+='<div style="display:flex;align-items:center;gap:7px">'+
      '<span style="width:10px;height:10px;border-radius:50%;background:'+cor+';display:inline-block;flex-shrink:0"></span>'+
      '<span style="color:var(--tm)">'+m.label+'</span>'+
      '<strong style="margin-left:6px">'+fmt2(m.faturamento)+'</strong>'+
      '</div>';
  });

  var donutHTML='<div style="position:relative;display:inline-flex;align-items:center;justify-content:center">'+
    '<svg width="160" height="160" viewBox="0 0 180 180">'+
    '<circle cx="90" cy="90" r="70" fill="none" stroke="#F0F0F0" stroke-width="22"/>'+
    svgCircles+'</svg>'+
    '<div style="position:absolute;text-align:center">'+
    '<div style="font-size:16px;font-weight:800">'+fmt(total)+'</div>'+
    '<div style="font-size:10px;color:var(--tl)">'+meses.length+' meses</div>'+
    '</div></div>';

  sh('hist-wrap','<div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">'+
    donutHTML+
    '<div style="display:flex;flex-direction:column;gap:7px;font-size:12px">'+legend+'</div>'+
    '</div>');
  s('hist-sub','Dados reais dos últimos '+meses.length+' meses');
}

function renderHistoricoTabelas(meses){
  var htmlHist=meses.map(function(m){
    var tkt=m.pedidos>0?(m.faturamento/m.pedidos):0;
    return'<tr><td>'+m.label+'</td><td>'+fmt2(m.faturamento)+'</td><td>'+m.pedidos+'</td><td>'+fmt2(tkt)+'</td></tr>';
  }).join('');
  sh('t-hist',htmlHist||'<tr><td colspan="4" class="lod">Sem dados</td></tr>');
}

function calcularMargem(meses){
  var total=meses.reduce(function(a,m){return a+m.faturamento;},0);
  var taxas=total*0.12;
  var cmv=total*0.35;
  var lucro=total-taxas-cmv;
  s('mg-fat',fmt2(total));
  s('mg-taxas','−'+fmt2(taxas));
  s('mg-cmv','−'+fmt2(cmv));
  s('mg-lucro',fmt2(lucro));
}

function calcularFinanceiro(meses){
  var total=meses.reduce(function(a,m){return a+m.faturamento;},0);
  var totalPed=meses.reduce(function(a,m){return a+m.pedidos;},0);
  var taxas=total*0.12;
  var liq=total-taxas;
  s('fin-fat',fmt2(total));
  s('fin-taxas','−'+fmt2(taxas));
  s('fin-liq',fmt2(liq));
  s('fin-ped',totalPed);

  var htmlFin=meses.map(function(m){
    var tx=m.faturamento*0.12;
    var lq=m.faturamento-tx;
    return'<tr><td>'+m.label+'</td><td>'+fmt2(m.faturamento)+'</td><td>'+m.pedidos+'</td><td>−'+fmt2(tx)+'</td><td>'+fmt2(lq)+'</td></tr>';
  }).join('');
  sh('t-fin',htmlFin||'<tr><td colspan="5" class="lod">Sem dados</td></tr>');
}

function calcularTACOS(meses){
  var fat=meses.reduce(function(a,m){return a+m.faturamento;},0);
  // TACOS estimado: sem dados reais de ADS, mostramos N/A
  s('tacos-fat',fmt2(fat));
  s('ads-fat',fmt2(fat));
  var totalPed=meses.reduce(function(a,m){return a+m.pedidos;},0);
  s('ads-ped',totalPed);

  // Gauge sem dados de ADS
  s('tacos-val','N/D');
  s('tacos-desc','Conecte o Product Ads para ver');
  s('ads-tacos','N/D');
  s('tacos-badge','TACOS: N/D');
}

function loadPedidos(){
  fetch('/api/pedidos').then(function(r){return r.json();}).then(function(data){
    var res=data.results||[];
    var total=res.reduce(function(a,o){return a+parseFloat(o.total_amount||0);},0);
    var ok=res.filter(function(o){return['paid','delivered','confirmed'].indexOf(o.status)>-1;}).length;
    var can=res.filter(function(o){return o.status==='cancelled';}).length;
    var tkt=res.length?total/res.length:0;
    s('k-fat',fmt2(total)); s('k-ped',res.length); s('k-tkt','R$ '+tkt.toFixed(0));
    s('v-ped',res.length); s('v-fat',fmt2(total)); s('v-tkt','R$ '+tkt.toFixed(0));
    s('v-ok',ok); s('v-can',can);
    s('perf-ped',res.length+' pedidos');
    var pb=document.getElementById('perf-pedb'); if(pb)pb.style.width=Math.min(100,res.length*5)+'%';
    if(!res.length){var msg='<tr><td colspan="6" class="lod">Nenhum pedido encontrado.</td></tr>';sh('t-res',msg);sh('t-ven',msg);return;}
    var html=res.map(function(p){
      var title=p.order_items&&p.order_items[0]?p.order_items[0].item.title.substring(0,32)+'...':'—';
      var buyer=p.buyer?(p.buyer.nickname||p.buyer.first_name||'—'):'—';
      var val=p.total_amount?fmt2(p.total_amount):'—';
      var dt=p.date_created?p.date_created.substring(0,10):'—';
      return'<tr><td style="font-size:11px">#'+p.id+'</td><td>'+title+'</td><td>'+buyer+'</td><td>'+val+'</td><td>'+dt+'</td><td>'+pill(p.status)+'</td></tr>';
    }).join('');
    sh('t-res',html); sh('t-ven',html);
  }).catch(function(){});
}

function loadProdutos(){
  fetch('/api/produtos').then(function(r){return r.json();}).then(function(data){
    var ids=data.results||[];
    s('k-prod',ids.length); s('p-tot',ids.length); s('p-at',ids.length); s('p-pa',0); s('p-se',0);
    s('perf-p',ids.length+' produtos');
    var pb=document.getElementById('perf-pb'); if(pb)pb.style.width=Math.min(100,ids.length*2)+'%';
    if(!ids.length){sh('t-prod','<tr><td colspan="5" class="lod">Nenhum produto.</td></tr>');return;}
    Promise.all(ids.slice(0,15).map(function(id){
      return fetch('/api/produto/'+id).then(function(r){return r.json();}).catch(function(){return{id:id};});
    })).then(function(prods){
      var at=0,pa=0,se=0;
      var html=prods.map(function(p){
        var st=p.status==='active'?'<span class="p pg">Ativo</span>':p.status==='paused'?'<span class="p pa">Pausado</span>':'<span class="p py">'+(p.status||'?')+'</span>';
        if(p.status==='active')at++;else pa++;
        if(p.available_quantity===0)se++;
        return'<tr><td>'+((p.title||p.id||'').substring(0,40))+'</td><td style="font-size:11px;color:var(--tl)">'+p.id+'</td><td>'+(p.price?fmt2(p.price):'—')+'</td><td>'+(p.available_quantity!==undefined?p.available_quantity:'—')+'</td><td>'+st+'</td></tr>';
      }).join('');
      sh('t-prod',html); s('p-at',at); s('p-pa',pa); s('p-se',se);
    });
  }).catch(function(){});
}

function init(){checkStatus();}
init();
setInterval(init,300000);
</script>
</body>
</html>"""

# ── ROTAS ─────────────────────────────────────────────────────

@app.route("/")
def index():
    token = load_token()
    if token:
        return Response(HTML, mimetype='text/html')
    return Response("""<!DOCTYPE html><html><body style="font-family:sans-serif;padding:60px;background:#F5F6FA;text-align:center">
    <div style="max-width:400px;margin:0 auto;background:white;padding:40px;border-radius:16px;border:1px solid #E8E8E8">
    <div style="font-size:48px;margin-bottom:16px">🔗</div>
    <h2 style="color:#E87722">YUSO Dashboard</h2>
    <p style="color:#555;margin:12px 0 24px">Conecte sua conta do Mercado Livre para acessar.</p>
    <a href="/login" style="background:#E87722;color:white;padding:14px 32px;border-radius:10px;text-decoration:none;font-weight:bold;font-size:16px">
    Conectar ao Mercado Livre</a></div></body></html>""", mimetype='text/html')

@app.route("/login")
def login():
    v = generate_code_verifier()
    c = generate_code_challenge(v)
    session["code_verifier"] = v
    return redirect(f"{ML_AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&code_challenge={c}&code_challenge_method=S256")

@app.route("/callback")
def callback():
    code = request.args.get("code")
    if not code: return "Erro: código não encontrado.", 400
    v = session.get("code_verifier")
    if not v: return redirect("/login")
    r = requests.post(ML_TOKEN_URL, data={
        "grant_type":"authorization_code","client_id":CLIENT_ID,
        "client_secret":CLIENT_SECRET,"code":code,
        "redirect_uri":REDIRECT_URI,"code_verifier":v
    })
    if r.status_code == 200:
        save_token(r.json()); session.pop("code_verifier", None); return redirect("/")
    return f"Erro: {r.text}", 400

@app.route("/status")
def status():
    t = load_token()
    return cors({"authenticated": bool(t), "user_id": t.get("user_id") if t else None})

@app.route("/api/historico")
def api_historico():
    """Busca faturamento real dos últimos 6 meses na API do ML"""
    t = load_token()
    if not t: return cors({"error": "not_authenticated"}, 401)

    user_id = t.get("user_id")
    hoje = datetime.now()
    meses = []
    nomes_pt = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']

    for i in range(5, -1, -1):
        # Calcula o mês
        if hoje.month - i <= 0:
            mes = hoje.month - i + 12
            ano = hoje.year - 1
        else:
            mes = hoje.month - i
            ano = hoje.year

        ultimo_dia = monthrange(ano, mes)[1]
        date_from = f"{ano}-{mes:02d}-01T00:00:00.000-03:00"
        date_to   = f"{ano}-{mes:02d}-{ultimo_dia:02d}T23:59:59.000-03:00"
        label     = f"{nomes_pt[mes-1]}/{str(ano)[-2:]}"

        total_fat = 0
        total_ped = 0
        offset    = 0

        # Pagina os resultados (ML retorna max 50 por vez)
        while True:
            url = (f"/orders/search?seller={user_id}"
                   f"&order.date_created.from={date_from}"
                   f"&order.date_created.to={date_to}"
                   f"&order.status=paid"
                   f"&limit=50&offset={offset}")
            r = ml_get(url, t)
            if r.status_code != 200:
                break
            data    = r.json()
            results = data.get("results", [])
            if not results:
                break
            for o in results:
                total_fat += float(o.get("total_amount", 0))
                total_ped += 1
            paging = data.get("paging", {})
            total_avail = paging.get("total", 0)
            offset += 50
            if offset >= total_avail or offset >= 200:  # max 200 por mês
                break

        meses.append({"label": label, "faturamento": round(total_fat, 2), "pedidos": total_ped, "mes": mes, "ano": ano})

    return cors({"meses": meses})

@app.route("/api/pedidos")
def api_pedidos():
    t = load_token()
    if not t: return cors({"error": "not_authenticated"}, 401)
    r = ml_get(f"/orders/search?seller={t.get('user_id')}&sort=date_desc&limit=20", t)
    return cors(r.json() if r.status_code == 200 else {"error": r.text})

@app.route("/api/produtos")
def api_produtos():
    t = load_token()
    if not t: return cors({"error": "not_authenticated"}, 401)
    r = ml_get(f"/users/{t.get('user_id')}/items/search?limit=50", t)
    return cors(r.json() if r.status_code == 200 else {"error": r.text})

@app.route("/api/produto/<item_id>")
def api_produto(item_id):
    t = load_token()
    if not t: return cors({"error": "not_authenticated"}, 401)
    r = ml_get(f"/items/{item_id}", t)
    return cors(r.json() if r.status_code == 200 else {"error": r.text})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"🚀 YUSO rodando na porta {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
