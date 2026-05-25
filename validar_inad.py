#!/usr/bin/env python3
import json, os, sys, base64, urllib.request
from google.oauth2.service_account import Credentials
import gspread

sa_info  = json.loads(os.environ["GEJA_SA_KEY"])
TOKEN    = os.environ["GITHUB_TOKEN"]
REPO     = "ChefeBuzz/geja-bi"
SHEET_ID = "1lOBHTIAzYkAWOjGwR66ISguvs247CA4R9m32Tp603vc"
SCOPES   = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

print("Conectando ao Google Sheets...")
creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc    = gspread.authorize(creds)
sh    = gc.open_by_key(SHEET_ID)
ws    = sh.worksheet("Dados (2025 - 2026)")
rows  = ws.get_all_values()
data_rows = rows[3:]
print(f"Lidas {len(data_rows)} linhas")

def col(row, i):
    try: return str(row[i]).strip() if i < len(row) else ""
    except: return ""

def pag(val):
    if not val or val in ("-","—",""): return "NAO PAGO"
    v = val.strip().upper()
    if "SE APLICA" in v:  return "Não Se Aplica"
    if "INCLU"     in v:  return "Não Incluído"
    if "ISEN"      in v:  return "Isenção"
    if "LICEN"     in v:  return "Licença"
    if "DESLIG"    in v:  return "Desligamento"
    if v.startswith("#") or "PAGO" in v or "TRANSFER" in v: return "Pago"
    return "OUTRO: " + val[:25]

# Coletar inadimplentes
inad = []
italo_isabel = []

for row in data_rows:
    nome   = col(row, 2)
    status = col(row, 0)
    if not nome or nome.lower() in ("nan","none",""): continue
    
    p1s26 = col(row, 14)
    p2s25 = col(row, 10)
    p1s25 = col(row, 8)
    secao = col(row, 4)
    pg26  = pag(p1s26)
    
    # Verificar Ítalo e Isabel independente do status
    nl = nome.lower()
    if "italo" in nl or "ítalo" in nl or "isabel" in nl:
        italo_isabel.append({
            "nome": nome, "status": status, "secao": secao,
            "1s2025": p1s25, "status_1s2025": pag(p1s25),
            "2s2025": p2s25, "status_2s2025": pag(p2s25),
            "1s2026": p1s26, "status_1s2026": pg26
        })
    
    # Inadimplentes: ativos com 1s2026 não pago
    if status == "2. Ativo" and pg26 not in ("Pago","Não Se Aplica","Isenção","Não Incluído","Licença","Desligamento"):
        inad.append({"nome": nome, "secao": secao, "valor_raw": p1s26, "classificacao": pg26})

inad.sort(key=lambda x: x["nome"])

result = {
    "total_inad": len(inad),
    "inadimplentes": inad,
    "italo_e_isabel": italo_isabel
}

# Gravar resultado no repositório
content = json.dumps(result, ensure_ascii=False, indent=2)
content_b64 = base64.b64encode(content.encode()).decode()

# Pegar SHA se existir
sha = None
req_get = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
    headers={"Authorization": f"token {TOKEN}"}
)
try:
    with urllib.request.urlopen(req_get) as r:
        sha = json.loads(r.read()).get("sha")
except: pass

body = {"message": "Resultado validacao inadimplentes",
        "content": content_b64, "branch": "main"}
if sha: body["sha"] = sha

req2 = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"token {TOKEN}",
             "Content-Type": "application/json",
             "Accept": "application/vnd.github+json"},
    method="PUT"
)
with urllib.request.urlopen(req2) as r:
    print(f"Resultado salvo no repositório! Status: {r.status}")

print("FIM")
