#!/usr/bin/env python3
"""
Lê a aba Dados Médicos (PAXTU) e identifica quem precisa de cada campo
marcado na pulseira amarela:
  1. ALERGIA a picadas
  2. ALERGIA a medicamentos
  3. REMÉDIO CONTÍNUO
  4. RESTRIÇÃO ALIMENTAR
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

# Listar todas as abas disponíveis
abas = [ws.title for ws in sh.worksheets()]
print("Abas disponíveis:", abas)

# Tentar ler aba de dados médicos
aba_med = None
for candidato in ["Dados Médicos", "Dados Medicos", "PAXTU", "Médico", "Medico", "Ficha"]:
    if candidato in abas:
        aba_med = candidato
        break

if not aba_med:
    # Usar aba principal e buscar colunas médicas
    print("Aba médica não encontrada — usando aba principal")
    ws = sh.worksheet("Dados (2025 - 2026)")
    rows = ws.get_all_values()
    headers = rows[2]
    print("\nColunas com dados médicos (alergia, remédio, restrição):")
    for i, h in enumerate(headers):
        hl = h.lower()
        if any(k in hl for k in ['alergia','remédio','remedio','restrição','restricao','medicament','piçad','picad','aliment']):
            vals = [str(r[i]).strip() for r in rows[3:] if i < len(r) and str(r[i]).strip() not in ('','—','-')]
            print(f"  col {i:3d}: '{h}' — {len(vals)} preenchidas")
            if vals: print(f"           ex: {vals[:3]}")
else:
    print(f"Aba médica encontrada: '{aba_med}'")
    ws  = sh.worksheet(aba_med)
    rows = ws.get_all_values()
    print(f"Linhas: {len(rows)}")
    print("Cabeçalhos (primeiras 30 colunas):")
    if rows:
        for i, h in enumerate(rows[0][:30]):
            print(f"  col {i:2d}: '{h}'")
    print("\nPrimeiras 3 linhas de dados:")
    for row in rows[1:4]:
        print(row[:15])

# Salvar resultado preliminar
result = {"abas": abas, "aba_medica": aba_med}
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
body = {"message": "pulseira diag", "content": content_b64, "branch": "main"}
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
