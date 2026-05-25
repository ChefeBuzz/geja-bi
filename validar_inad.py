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

# Mostrar cabeçalhos das colunas de semestralidade para confirmar índices
print("=== CABEÇALHOS SEMESTRALIDADE ===")
for i, h in enumerate(headers):
    if any(k in h.lower() for k in ['sem', 'semestral', 'obs', '2025', '2026', 'fin']):
        print(f"  col {i:3d}: '{h}'")

print("\n=== CÉLULAS RAW — ISABEL E ÍTALO (todos os cols 0-20) ===")
for row in data_rows:
    nome = col(row, 2)
    if not nome: continue
    nl = nome.lower()
    if "isabel pereira" in nl or "italo rigotti" in nl:
        print(f"\nNOME: {nome}")
        print(f"STATUS: {col(row,0)} | SECAO: {col(row,4)}")
        # Mostrar colunas 6 a 20 com valores
        for i in range(6, 21):
            val = col(row, i)
            if val:
                print(f"  col {i:2d} [{headers[i][:30] if i < len(headers) else '?'}]: '{val}'")

# Verificar qual coluna TEM o EM ATRASO!! para a Isabel
print("\n=== ONDE ESTÁ O 'EM ATRASO!!' DA ISABEL ===")
for row in data_rows:
    nome = col(row, 2)
    if not nome or "isabel pereira" not in nome.lower(): continue
    for i, v in enumerate(row):
        if "atraso" in str(v).lower():
            h = headers[i] if i < len(headers) else "?"
            print(f"  col {i}: [{h}] = '{v}'")

result = {"diagnostico": "ok"}
content_b64 = base64.b64encode(json.dumps(result).encode()).decode()
sha = None
try:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
        headers={"Authorization": f"token {TOKEN}"}
    )
    with urllib.request.urlopen(req) as r:
        sha = json.loads(r.read()).get("sha")
except: pass
body = {"message": "diag", "content": content_b64, "branch": "main"}
if sha: body["sha"] = sha
req2 = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json",
             "Accept": "application/vnd.github+json"},
    method="PUT"
)
with urllib.request.urlopen(req2) as r:
    print(f"\nSalvo! ({r.status})")
print("FIM")
