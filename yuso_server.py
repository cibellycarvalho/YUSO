"""
YUSO Dashboard - Servidor Flask com dashboard integrado
"""

from flask import Flask, redirect, request, jsonify, session, Response
import requests, json, os, secrets, hashlib, base64

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
    r = requests.post(ML_TOKEN_URL, data={"grant_type":"refresh_token","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET,"refresh_token":t["refresh_token"]})
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
/* SIDEBAR */
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
/* MAIN */
.main{flex:1;overflow-y:auto;display:flex;flex-direction:column;}
.tb{background:#fff;border-bottom:1px solid var(--bdr);padding:14px 28px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}
.tb-t{font-size:18px;font-weight:700;}
.tb-s{font-size:12px;color:var(--tl);margin-top:2px;}
.tr{display:flex;align-items:center;gap:12px;}
.bdg{background:var(--acc-l);color:var(--acc);padding:4px 10px;border-radius:20px;font-size:11px;font-weight:700;}
.bdg.grn{background:#E8F8F0;color:var(--grn);}
.bdg.red{background:#FDEDEC;color:var(--red);}
.cnt{padding:24px 28px;flex:1;}
/* CARDS */
.cr{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;}
.card{background:var(--card);border-radius:12px;border:1px solid var(--bdr);padding:20px;flex:1;min-width:150px;}
.cl{font-size:11px;color:var(--tl);font-weight:600;text-transform:uppercase;letter-spacing:.5px;}
.cv{font-size:24px;font-weight:800;margin:6px 0 2px;}
.cc{font-size:12px;font-weight:600;color:var(--tl);}
.cc.up{color:var(--grn);} .cc.dn{color:var(--red);}
/* CHART CARDS */
.chrow{display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;}
.cc2{background:var(--card);border-radius:12px;border:1px solid var(--bdr);padding:20px;}
.ct{font-size:13px;font-weight:700;margin-bottom:4px;}
.cs{font-size:11px;color:var(--tl);margin-bottom:12px;}
/* TABLE */
.tc{background:var(--card);border-radius:12px;border:1px solid var(--bdr);overflow:hidden;margin-bottom:20px;}
.th{padding:14px 20px;border-bottom:1px solid var(--bdr);display:flex;align-items:center;justify-content:space-between;}
.tt{font-size:13px;font-weight:700;}
table{width:100%;border-collapse:collapse;}
th{font-size:11px;color:var(--tl);text-transform:uppercase;padding:10px 20px;text-align:left;background:#FAFAFA;border-bottom:1px solid var(--bdr);}
td{font-size:13px;padding:11px 20px;border-bottom:1px solid var(--bdr);}
tr:last-child td{border-bottom:none;}
tr:hover td{background:#FAFBFF;}
/* PILLS */
.p{display:inline-block;padding:3px 9px;border-radius:20px;font-size:11px;font-weight:700;}
.pg{background:#E8F8F0;color:var(--grn);} .pa{background:#FEF9E7;color:var(--amb);}
.pr{background:#FDEDEC;color:var(--red);} .pb{background:#EAF4FB;color:var(--blu);}
.py{background:#F2F2F2;color:var(--tl);}
/* MISC */
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
.dw{position:relative;display:inline-flex;align-items:center;justify-content:center;}
.dc{position:absolute;text-align:center;}
.dc .db{font-size:19px;font-weight:800;}
.dc .ds{font-size:10px;color:var(--tl);}
.gw{display:flex;flex-direction:column;align-items:center;}
.gv{font-size:26px;font-weight:800;margin-top:4px;}
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
  <div class="tb"><div><div class="tb-t">Resumo Geral</div><div class="tb-s">Dados reais do Mercado Livre</div></div>
  <div class="tr"><span class="bdg" id="bdg">Carregando...</span><button class="btn bp" onclick="init()">↻ Atualizar</button></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Faturamento</div><div class="cv" id="k-fat">—</div><div class="cc">Mês atual</div></div>
      <div class="card"><div class="cl">Pedidos</div><div class="cv" id="k-ped">—</div><div class="cc">Mês atual</div></div>
      <div class="card"><div class="cl">Ticket Médio</div><div class="cv" id="k-tkt">—</div><div class="cc">Por pedido</div></div>
      <div class="card"><div class="cl">Produtos</div><div class="cv" id="k-prod">—</div><div class="cc up">No catálogo</div></div>
      <div class="card"><div class="cl">Reputação</div><div class="cv" style="color:var(--grn)">🟢</div><div class="cc up">Verde / Ótima</div></div>
    </div>
    <div class="chrow">
      <div class="cc2" style="flex:1.2">
        <div class="ct">Faturamento por Mês</div><div class="cs">Histórico 6 meses</div>
        <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap">
          <div class="dw">
            <svg width="160" height="160" viewBox="0 0 180 180">
              <circle cx="90" cy="90" r="70" fill="none" stroke="#F0F0F0" stroke-width="22"/>
              <circle cx="90" cy="90" r="70" fill="none" stroke="#E87722" stroke-width="22" stroke-dasharray="60.6 379.4" stroke-dashoffset="-330" transform="rotate(-90 90 90)"/>
              <circle cx="90" cy="90" r="70" fill="none" stroke="#F39C12" stroke-width="22" stroke-dasharray="65.6 374.4" stroke-dashoffset="-264.4" transform="rotate(-90 90 90)"/>
              <circle cx="90" cy="90" r="70" fill="none" stroke="#27AE60" stroke-width="22" stroke-dasharray="77 363" stroke-dashoffset="-187.4" transform="rotate(-90 90 90)"/>
              <circle cx="90" cy="90" r="70" fill="none" stroke="#2980B9" stroke-width="22" stroke-dasharray="88.4 351.6" stroke-dashoffset="-99" transform="rotate(-90 90 90)"/>
              <circle cx="90" cy="90" r="70" fill="none" stroke="#8E44AD" stroke-width="22" stroke-dasharray="101.2 338.8" stroke-dashoffset="2.2" transform="rotate(-90 90 90)"/>
              <circle cx="90" cy="90" r="70" fill="none" stroke="#E74C3C" stroke-width="22" stroke-dasharray="47 393" stroke-dashoffset="103.4" transform="rotate(-90 90 90)"/>
            </svg>
            <div class="dc"><div class="db">R$61,7k</div><div class="ds">6 meses</div></div>
          </div>
          <div style="display:flex;flex-direction:column;gap:7px;font-size:12px">
            <div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:#E87722;display:inline-block"></span><span style="color:var(--tm)">Out/25</span><strong style="margin-left:6px">R$8.500</strong></div>
            <div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:#F39C12;display:inline-block"></span><span style="color:var(--tm)">Nov/25</span><strong style="margin-left:6px">R$9.200</strong></div>
            <div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:#27AE60;display:inline-block"></span><span style="color:var(--tm)">Dez/25</span><strong style="margin-left:6px">R$10.800</strong></div>
            <div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:#2980B9;display:inline-block"></span><span style="color:var(--tm)">Jan/26</span><strong style="margin-left:6px">R$12.400</strong></div>
            <div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:#8E44AD;display:inline-block"></span><span style="color:var(--tm)">Fev/26</span><strong style="margin-left:6px">R$14.200</strong></div>
            <div style="display:flex;align-items:center;gap:7px"><span style="width:10px;height:10px;border-radius:50%;background:#E74C3C;display:inline-block"></span><span style="color:var(--tm)">Mar/26</span><strong style="margin-left:6px" id="mar-v">—</strong></div>
          </div>
        </div>
      </div>
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
            <line x1="100" y1="108" x2="103" y2="32" stroke="#1A1A1A" stroke-width="2.5" stroke-linecap="round"/>
            <circle cx="100" cy="108" r="6" fill="#1A1A1A"/>
            <circle cx="100" cy="108" r="3" fill="white"/>
          </svg>
          <div class="gv" style="color:var(--amb)">5,1%</div>
          <div style="font-size:11px;color:var(--tl)">⚠️ Limite da zona verde</div>
        </div>
      </div>
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
      <tbody id="t-res"><tr><td colspan="6" class="lod">⏳ Buscando dados do Mercado Livre...</td></tr></tbody></table>
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
  <div class="tb"><div><div class="tb-t">Campanhas / ADS</div><div class="tb-s">Product Ads · Mercado Livre</div></div><div class="tr"><span class="bdg">TACOS: 5,1%</span></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Gasto ADS</div><div class="cv">R$3.147</div><div class="cc">Mês atual</div></div>
      <div class="card"><div class="cl">Vendas via ADS</div><div class="cv">R$22.400</div><div class="cc up">36% do total</div></div>
      <div class="card"><div class="cl">ROAS</div><div class="cv" style="color:var(--grn)">7,1x</div><div class="cc up">Ótimo</div></div>
      <div class="card"><div class="cl">CPC Médio</div><div class="cv">R$0,94</div><div class="cc">Estável</div></div>
    </div>
    <div class="al aw"><span>⚠️</span><span>TACOS em <strong>5,1%</strong> — limite da zona verde. Monitore para não ultrapassar 10%.</span></div>
    <div class="tc"><div class="th"><span class="tt">Campanhas Ativas</span></div>
    <table><thead><tr><th>Campanha</th><th>Gasto</th><th>Impressões</th><th>ROAS</th><th>Status</th></tr></thead>
    <tbody>
      <tr><td>Kit Suporte Monitor</td><td>R$1.240</td><td>72.000</td><td>8,2x</td><td><span class="p pg">Ativa</span></td></tr>
      <tr><td>Cabo USB-C</td><td>R$840</td><td>58.000</td><td>7,8x</td><td><span class="p pg">Ativa</span></td></tr>
      <tr><td>Hub USB 7 Portas</td><td>R$620</td><td>34.000</td><td>6,4x</td><td><span class="p pg">Ativa</span></td></tr>
      <tr><td>Mousepad XL</td><td>R$447</td><td>20.000</td><td>5,1x</td><td><span class="p pa">Pausada</span></td></tr>
    </tbody></table></div>
  </div>
</div>

<!-- MARGEM -->
<div id="page-margem" class="page">
  <div class="tb"><div><div class="tb-t">Margem pós-ADS</div><div class="tb-s">Lucratividade real</div></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Faturamento Bruto</div><div class="cv">R$61.700</div><div class="cc">6 meses</div></div>
      <div class="card"><div class="cl">Custo ADS</div><div class="cv" style="color:var(--red)">−R$3.147</div><div class="cc dn">5,1%</div></div>
      <div class="card"><div class="cl">Taxas ML 12%</div><div class="cv" style="color:var(--red)">−R$7.404</div><div class="cc dn">Plataforma</div></div>
      <div class="card"><div class="cl">CMV 35%</div><div class="cv" style="color:var(--red)">−R$21.595</div><div class="cc dn">Produto</div></div>
      <div class="card"><div class="cl">Lucro Líquido</div><div class="cv" style="color:var(--grn)">R$29.554</div><div class="cc up">Margem 47,9%</div></div>
    </div>
    <div class="cc2"><div class="ct">Composição da Margem</div><div class="cs">% do faturamento</div>
      <div style="display:flex;flex-direction:column;gap:12px;margin-top:6px">
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:var(--grn);font-weight:700">Lucro Líquido</span><span>47,9%</span></div><div class="pb2"><div class="pf" style="width:47.9%;background:var(--grn)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:var(--amb);font-weight:700">CMV</span><span>35,0%</span></div><div class="pb2"><div class="pf" style="width:35%;background:var(--amb)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:var(--red);font-weight:700">Taxas ML</span><span>12,0%</span></div><div class="pb2"><div class="pf" style="width:12%;background:var(--red)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span style="color:#E74C3C;font-weight:700">ADS</span><span>5,1%</span></div><div class="pb2"><div class="pf" style="width:5.1%;background:#E74C3C"></div></div></div>
      </div>
    </div>
  </div>
</div>

<!-- RANQUEAMENTO -->
<div id="page-ranqueamento" class="page">
  <div class="tb"><div><div class="tb-t">Ranqueamento</div><div class="tb-s">Posição no Mercado Livre</div></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">Top 3</div><div class="cv" style="color:var(--grn)">6</div><div class="cc up">Produtos</div></div>
      <div class="card"><div class="cl">Página 1</div><div class="cv">11</div><div class="cc up">Top 10</div></div>
      <div class="card"><div class="cl">Posição Média</div><div class="cv">4,2</div><div class="cc up">Melhora</div></div>
    </div>
    <div class="cc2"><div class="ct">Fatores de Ranqueamento</div><div class="cs">Impacto no posicionamento</div>
      <div style="display:flex;flex-direction:column;gap:12px;margin-top:6px">
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Reputação</span><span style="color:var(--grn);font-weight:700">97%</span></div><div class="pb2"><div class="pf" style="width:97%;background:var(--grn)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Velocidade de envio</span><span style="color:var(--grn);font-weight:700">94%</span></div><div class="pb2"><div class="pf" style="width:94%;background:var(--grn)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Taxa de conversão</span><span style="color:var(--amb);font-weight:700">3,2%</span></div><div class="pb2"><div class="pf" style="width:32%;background:var(--amb)"></div></div></div>
        <div><div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:12px"><span>Qualidade dos títulos</span><span style="color:var(--blu);font-weight:700">78%</span></div><div class="pb2"><div class="pf" style="width:78%;background:var(--blu)"></div></div></div>
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
          <div style="background:var(--acc-l);border-radius:8px;padding:12px"><div style="font-size:13px;font-weight:700">Cabo USB4 Gen 3</div><div style="font-size:11px;color:var(--tm);margin-top:2px">12 vendedores · 8.400 buscas/mês</div><div style="display:flex;gap:6px;margin-top:6px"><span class="p pg">Alta demanda</span><span class="p pb">Baixa concorrência</span></div></div>
          <div style="background:#F0FFF4;border-radius:8px;padding:12px"><div style="font-size:13px;font-weight:700">Carregador Wireless 30W</div><div style="font-size:11px;color:var(--tm);margin-top:2px">8 vendedores · 6.100 buscas/mês</div><div style="display:flex;gap:6px;margin-top:6px"><span class="p pg">Alta demanda</span><span class="p pg">Baixíssima concorrência</span></div></div>
        </div>
      </div>
    </div>
  </div>
</div>

<!-- FINANCEIRO -->
<div id="page-financeiro" class="page">
  <div class="tb"><div><div class="tb-t">Financeiro</div><div class="tb-s">Repasses e fluxo de caixa</div></div></div>
  <div class="cnt">
    <div class="cr">
      <div class="card"><div class="cl">A Receber</div><div class="cv" style="color:var(--grn)">R$4.280</div><div class="cc up">Próximos repasses</div></div>
      <div class="card"><div class="cl">Próximo Repasse</div><div class="cv">R$2.140</div><div class="cc">22/03/2026</div></div>
      <div class="card"><div class="cl">Taxas (mês)</div><div class="cv" style="color:var(--red)">R$792</div><div class="cc dn">12% das vendas</div></div>
      <div class="card"><div class="cl">Total Recebido</div><div class="cv">R$54.296</div><div class="cc up">Acumulado</div></div>
    </div>
    <div class="tc"><div class="th"><span class="tt">Histórico de Repasses</span></div>
    <table><thead><tr><th>Data</th><th>Pedidos</th><th>Bruto</th><th>Taxas</th><th>Líquido</th><th>Status</th></tr></thead>
    <tbody>
      <tr><td>22/03/2026</td><td>14</td><td>R$2.520</td><td>−R$302</td><td><strong>R$2.140</strong></td><td><span class="p pb">Agendado</span></td></tr>
      <tr><td>15/03/2026</td><td>21</td><td>R$3.780</td><td>−R$454</td><td><strong>R$3.209</strong></td><td><span class="p pg">Pago</span></td></tr>
      <tr><td>08/03/2026</td><td>23</td><td>R$4.140</td><td>−R$497</td><td><strong>R$3.515</strong></td><td><span class="p pg">Pago</span></td></tr>
      <tr><td>29/02/2026</td><td>19</td><td>R$3.420</td><td>−R$410</td><td><strong>R$2.904</strong></td><td><span class="p pg">Pago</span></td></tr>
    </tbody></table></div>
  </div>
</div>

<!-- INTEGRAÇÕES -->
<div id="page-integracoes" class="page">
  <div class="tb"><div><div class="tb-t">Integrações</div><div class="tb-s">Conexões externas</div></div></div>
  <div class="cnt">
    <div class="al as" id="al-on" style="display:none"><span>✅</span><div><strong>Mercado Livre conectado!</strong> Dados atualizados automaticamente a cada 5 minutos.</div></div>
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
var ok=false;
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
    ok=d.authenticated; updateUI(d.authenticated,d.user_id);
    if(d.authenticated){loadPedidos();loadProdutos();}
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
function loadPedidos(){
  fetch('/api/pedidos').then(function(r){return r.json();}).then(function(data){
    var res=data.results||[];
    var total=res.reduce(function(a,o){return a+parseFloat(o.total_amount||0);},0);
    var ok2=res.filter(function(o){return['paid','delivered','confirmed'].indexOf(o.status)>-1;}).length;
    var can=res.filter(function(o){return o.status==='cancelled';}).length;
    var tkt=res.length?total/res.length:0;
    s('k-fat',fmt(total)); s('k-ped',res.length); s('k-tkt','R$ '+tkt.toFixed(0));
    s('v-ped',res.length); s('v-fat',fmt(total)); s('v-tkt','R$ '+tkt.toFixed(0));
    s('v-ok',ok2); s('v-can',can);
    s('mar-v',fmt(total));
    s('perf-ped',res.length+' pedidos');
    var pb=document.getElementById('perf-pedb'); if(pb)pb.style.width=Math.min(100,res.length*5)+'%';
    if(!res.length){var msg='<tr><td colspan="6" class="lod">Nenhum pedido encontrado.</td></tr>';sh('t-res',msg);sh('t-ven',msg);return;}
    var html=res.map(function(p){
      var title=p.order_items&&p.order_items[0]?p.order_items[0].item.title.substring(0,30)+'...':'—';
      var buyer=p.buyer?(p.buyer.nickname||p.buyer.first_name||'—'):'—';
      var val=p.total_amount?fmt(p.total_amount):'—';
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
    var pb=document.getElementById('perf-pb'); if(pb)pb.style.width=Math.min(100,ids.length*3.5)+'%';
    if(!ids.length){sh('t-prod','<tr><td colspan="5" class="lod">Nenhum produto encontrado.</td></tr>');return;}
    Promise.all(ids.slice(0,15).map(function(id){
      return fetch('/api/produto/'+id).then(function(r){return r.json();}).catch(function(){return{id:id};});
    })).then(function(prods){
      var at=0,pa=0,se=0;
      var html=prods.map(function(p){
        var st=p.status==='active'?'<span class="p pg">Ativo</span>':p.status==='paused'?'<span class="p pa">Pausado</span>':'<span class="p py">'+(p.status||'?')+'</span>';
        if(p.status==='active')at++;else pa++;
        if(p.available_quantity===0)se++;
        var preco=p.price?fmt(p.price):'—';
        var esq=p.available_quantity!==undefined?p.available_quantity:'—';
        var title=p.title?p.title.substring(0,38):p.id;
        return'<tr><td>'+title+'</td><td style="font-size:11px;color:var(--tl)">'+p.id+'</td><td>'+preco+'</td><td>'+esq+'</td><td>'+st+'</td></tr>';
      }).join('');
      sh('t-prod',html);
      s('p-at',at); s('p-pa',pa); s('p-se',se);
    });
  }).catch(function(){});
}
function init(){checkStatus();}
init();
setInterval(init,300000);
</script>
</body>
</html>"""

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
    r = requests.post(ML_TOKEN_URL, data={"grant_type":"authorization_code","client_id":CLIENT_ID,"client_secret":CLIENT_SECRET,"code":code,"redirect_uri":REDIRECT_URI,"code_verifier":v})
    if r.status_code == 200:
        save_token(r.json()); session.pop("code_verifier", None); return redirect("/")
    return f"Erro: {r.text}", 400

@app.route("/status")
def status():
    t = load_token()
    return cors({"authenticated": bool(t), "user_id": t.get("user_id") if t else None})

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
