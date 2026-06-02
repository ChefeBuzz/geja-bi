#!/usr/bin/env python3
"""
Gera relação nominal para pulseiras do acampamento:
  1. ALERGIA a picadas de inseto
  2. ALERGIA a medicamentos
  3. REMÉDIO CONTÍNUO
  4. RESTRIÇÃO ALIMENTAR
Agrupado por: nos 4, nos 3, nos 2, nos 1 (qual).
"""
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

# ── Ler aba Dados Médicos ──────────────────────────────────────
ws   = sh.worksheet("Dados Médicos")
rows = ws.get_all_values()

# Mapear cabeçalhos
headers = rows[0] if rows else []
print("Total linhas:", len(rows))
print("Cabeçalhos:")
for i, h in enumerate(headers):
    print(f"  col {i:3d}: '{h}'")

# Salvar cabeçalhos para análise
result = {
    "total_linhas": len(rows),
    "headers": {str(i): h for i, h in enumerate(headers)},
    "amostra": [rows[r][:20] for r in range(1, min(6, len(rows)))]
}

content_b64 = base64.b64encode(json.dumps(result, ensure_ascii=False, indent=2).encode()).decode()
sha = None
try:
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
        headers={"Authorization": f"token {TOKEN}"}
    )
    with urllib.request.urlopen(req) as r:
        sha = json.loads(r.read()).get("sha")
except: pass
body = {"message": "headers Dados Medicos", "content": content_b64, "branch": "main"}
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
