#!/usr/bin/env python3
"""
Regra oficial de inadimplência:
  Inadimplente = célula contém "EM ATRASO!!" (qualquer semestre)
  Tudo mais (vazio, #numero, NÃO SE APLICA, etc.) NÃO é inadimplente.
"""
import json, os, base64, urllib.request
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

def is_atraso(val):
    """Regra oficial: inadimplente SOMENTE se contém 'EM ATRASO!!'"""
    return "EM ATRASO" in str(val).upper()

def classifica(val):
    v = str(val).strip()
    if not v or v in ("-","—"):          return "Não informado"
    if "EM ATRASO" in v.upper():         return "EM ATRASO!!"
    if "SE APLICA" in v.upper():         return "Não Se Aplica"
    if "INCLUÍ" in v or "INCLUIDO" in v.upper(): return "Não Incluído"
    if "ISEN" in v.upper():              return "Isenção"
    if "LICEN" in v.upper():             return "Licença"
    if "DESLIG" in v.upper():            return "Desligamento"
    if v.startswith("#") or "PAGO" in v.upper() or "TRANSFER" in v.upper():
        return "Pago"
    return f"Outro: {v[:30]}"

# Índices das colunas
I_STATUS=0; I_NUM=1; I_NOME=2; I_CAT=3; I_SECAO=4
I_P1S2025=8; I_P2S2025=10; I_P1S2026=14

inad_1s2026 = []
inad_2s2025 = []
inad_1s2025 = []
italo_isabel = []

for row in data_rows:
    nome   = col(row, I_NOME)
    status = col(row, I_STATUS)
    if not nome or nome.lower() in ("nan","none",""): continue

    p1s25 = col(row, I_P1S2025)
    p2s25 = col(row, I_P2S2025)
    p1s26 = col(row, I_P1S2026)
    secao = col(row, I_SECAO)
    cat   = col(row, I_CAT)

    # Verificar Ítalo e Isabel
    nl = nome.lower()
    if "italo" in nl or "ítalo" in nl or "isabel" in nl:
        italo_isabel.append({
            "nome": nome, "status": status, "secao": secao,
            "1s2025": classifica(p1s25), "atraso_1s2025": is_atraso(p1s25),
            "2s2025": classifica(p2s25), "atraso_2s2025": is_atraso(p2s25),
            "1s2026": classifica(p1s26), "atraso_1s2026": is_atraso(p1s26),
        })

    # Só considerar ativos
    if status != "2. Ativo": continue

    entry = {"nome": nome, "secao": secao, "categoria": cat,
             "1s2025": classifica(p1s25),
             "2s2025": classifica(p2s25),
             "1s2026": classifica(p1s26)}

    if is_atraso(p1s26): inad_1s2026.append(entry)
    if is_atraso(p2s25): inad_2s2025.append(entry)
    if is_atraso(p1s25): inad_1s2025.append(entry)

inad_1s2026.sort(key=lambda x: x["nome"])
inad_2s2025.sort(key=lambda x: x["nome"])
inad_1s2025.sort(key=lambda x: x["nome"])

print(f"\n=== INADIMPLENTES POR SEMESTRE ===")
print(f"  1s2025: {len(inad_1s2025)}")
print(f"  2s2025: {len(inad_2s2025)}")
print(f"  1s2026: {len(inad_1s2026)}")

print(f"\n=== ÍTALO E ISABEL ===")
for p in italo_isabel:
    print(f"  {p['nome']} | {p['status']} | {p['secao']}")
    print(f"    1s2025: {p['1s2025']} {'⚠️' if p['atraso_1s2025'] else ''}")
    print(f"    2s2025: {p['2s2025']} {'⚠️' if p['atraso_2s2025'] else ''}")
    print(f"    1s2026: {p['1s2026']} {'⚠️' if p['atraso_1s2026'] else ''}")

result = {
    "regra": "Inadimplente = celula contem 'EM ATRASO!!'",
    "inad_1s2026": inad_1s2026,
    "inad_2s2025": inad_2s2025,
    "inad_1s2025": inad_1s2025,
    "total_1s2026": len(inad_1s2026),
    "total_2s2025": len(inad_2s2025),
    "total_1s2025": len(inad_1s2025),
    "italo_e_isabel": italo_isabel
}

# Salvar no repositório
content_b64 = base64.b64encode(
    json.dumps(result, ensure_ascii=False, indent=2).encode()
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

body = {"message": "Validacao com regra EM ATRASO!!",
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
    print(f"\nResultado salvo! ({r.status})")
print("FIM")
