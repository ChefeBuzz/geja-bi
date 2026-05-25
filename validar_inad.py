#!/usr/bin/env python3
import json, os, base64, urllib.request
from google.oauth2.service_account import Credentials
import gspread

sa_info  = json.loads(os.environ["GEJA_SA_KEY"])
TOKEN    = os.environ["GITHUB_TOKEN"]
REPO     = "ChefeBuzz/geja-bi"
SHEET_ID = "1lOBHTIAzYkAWOjGwR66ISguvs247CA4R9m32Tp603vc"
SCOPES   = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc    = gspread.authorize(creds)
sh    = gc.open_by_key(SHEET_ID)
ws    = sh.worksheet("Dados (2025 - 2026)")
rows  = ws.get_all_values()
headers   = rows[2]
data_rows = rows[3:]

def col(row, i):
    try: return str(row[i]).strip() if i < len(row) else ""
    except: return ""

# Coletar diagnóstico
resultado = {
    "colunas_semestralidade": {},
    "isabel": {},
    "italo": {},
    "todos_atraso_qualquer_sem": []
}

# Mapear colunas relevantes
for i, h in enumerate(headers):
    hl = h.lower()
    if any(k in hl for k in ['sem', '2025', '2026', 'fin', 'obs']):
        resultado["colunas_semestralidade"][str(i)] = h

# Isabel e Ítalo - valores RAW de TODAS as colunas com dado
for row in data_rows:
    nome = col(row, 2)
    if not nome: continue
    nl = nome.lower()
    
    if "isabel pereira" in nl or "italo rigotti" in nl:
        chave = "isabel" if "isabel" in nl else "italo"
        resultado[chave] = {
            "nome": nome,
            "status": col(row, 0),
            "secao": col(row, 4),
            "celulas_com_valor": {}
        }
        # Guardar todos os cols não vazios
        for i, v in enumerate(row):
            vs = str(v).strip()
            if vs and vs not in ("-", "—"):
                h = headers[i] if i < len(headers) else f"col_{i}"
                resultado[chave]["celulas_com_valor"][str(i)] = {
                    "header": h, "valor": vs,
                    "tem_atraso": "ATRASO" in vs.upper()
                }

# Coletar TODOS que têm EM ATRASO!! em qualquer coluna (ativos)
for row in data_rows:
    nome   = col(row, 2)
    status = col(row, 0)
    if not nome or status != "2. Ativo": continue
    atrasos = {}
    for i, v in enumerate(row):
        if "ATRASO" in str(v).upper():
            h = headers[i] if i < len(headers) else f"col_{i}"
            atrasos[str(i)] = {"header": h, "valor": str(v).strip()}
    if atrasos:
        resultado["todos_atraso_qualquer_sem"].append({
            "nome": nome,
            "secao": col(row, 4),
            "atrasos": atrasos
        })

# Salvar no repositório
content_b64 = base64.b64encode(
    json.dumps(resultado, ensure_ascii=False, indent=2).encode()
).decode()

sha = None
try:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
        headers={"Authorization": f"token {TOKEN}"}
    )
    with urllib.request.urlopen(req) as r:
        sha = json.loads(r.read()).get("sha")
except: pass

body = {"message": "diagnostico raw Isabel e Italo",
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
    print(f"Salvo! ({r.status})")
print("FIM")
