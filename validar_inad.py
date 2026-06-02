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

ws   = sh.worksheet("Dados Médicos")
rows = ws.get_all_values()
data = rows[1:]  # pular cabeçalho

# Colunas mapeadas
I_NOME       = 3
I_SEXO       = 4
I_ALERGIAS   = 49  # Alergias - Resumo
I_RESTRICAO  = 45  # Restrição Alimentar (col 45 = Sim/Não, col 46 = detalhe)
I_REST_DET   = 46  # Detalhe Restrição Alimentar
I_MEDICAMENT = 53  # Medicamentos
I_IMP_FIS    = 43  # Impedimento Físico

def col(row, i):
    try: return str(row[i]).strip() if i < len(row) else ""
    except: return ""

def sim(val):
    v = val.strip().lower()
    return v not in ("", "não", "nao", "n", "0", "-", "—", "nenhum", "nenhuma", "não possui")

def tem_picada(alergias):
    a = alergias.lower()
    return any(k in a for k in ["picada","inseto","abelha","vespa","formiga","mosquito","aranha"])

def tem_med_alergia(alergias):
    a = alergias.lower()
    return any(k in a for k in ["medicament","remédio","remedio","antibiótico","antibiotic","dipirona","anestesi","penicilina","aspirina","ibuprofeno"])

# Processar cada pessoa
pessoas = []
for row in data:
    nome = col(row, I_NOME)
    if not nome or nome.lower() in ("", "nan", "none"): continue

    alergias   = col(row, I_ALERGIAS)
    restricao  = col(row, I_RESTRICAO)
    rest_det   = col(row, I_REST_DET)
    medicament = col(row, I_MEDICAMENT)

    p1 = tem_picada(alergias)            # Alergia a picadas
    p2 = tem_med_alergia(alergias)       # Alergia a medicamentos
    p3 = sim(medicament)                 # Remédio contínuo
    p4 = sim(restricao) or sim(rest_det) # Restrição alimentar

    qtd = sum([p1, p2, p3, p4])
    if qtd == 0: continue

    pessoas.append({
        "nome":      nome,
        "sexo":      col(row, I_SEXO),
        "picadas":   p1,
        "med_alerg": p2,
        "remedio":   p3,
        "restricao": p4,
        "qtd":       qtd,
        "alergias_raw":  alergias,
        "medicament_raw": medicament,
        "restricao_raw": rest_det or restricao,
    })

# Agrupar por quantidade de campos marcados
nos4 = [p for p in pessoas if p["qtd"]==4]
nos3 = [p for p in pessoas if p["qtd"]==3]
nos2 = [p for p in pessoas if p["qtd"]==2]
nos1 = [p for p in pessoas if p["qtd"]==1]

print(f"{'='*65}")
print(f"PULSEIRAS — RELAÇÃO NOMINAL")
print(f"Total com alguma marcação: {len(pessoas)}")
print(f"{'='*65}")

def labels(p):
    l = []
    if p["picadas"]:   l.append("PICADAS")
    if p["med_alerg"]: l.append("MED.ALERGIA")
    if p["remedio"]:   l.append("REMÉDIO")
    if p["restricao"]: l.append("RESTRICAO")
    return "+".join(l)

for grupo, titulo in [(nos4,"NOS 4 CAMPOS"),(nos3,"NOS 3 CAMPOS"),(nos2,"NOS 2 CAMPOS"),(nos1,"EM 1 CAMPO")]:
    print(f"\n── {titulo} ({len(grupo)} pessoas) ──")
    for p in sorted(grupo, key=lambda x: x["nome"]):
        print(f"  {p['nome']:<50} [{labels(p)}]")

result = {
    "total": len(pessoas),
    "nos4": [{"nome":p["nome"],"campos":labels(p),"alergias":p["alergias_raw"],"remedio":p["medicament_raw"],"restricao":p["restricao_raw"]} for p in sorted(nos4, key=lambda x: x["nome"])],
    "nos3": [{"nome":p["nome"],"campos":labels(p),"alergias":p["alergias_raw"],"remedio":p["medicament_raw"],"restricao":p["restricao_raw"]} for p in sorted(nos3, key=lambda x: x["nome"])],
    "nos2": [{"nome":p["nome"],"campos":labels(p),"alergias":p["alergias_raw"],"remedio":p["medicament_raw"],"restricao":p["restricao_raw"]} for p in sorted(nos2, key=lambda x: x["nome"])],
    "nos1": [{"nome":p["nome"],"campos":labels(p),"alergias":p["alergias_raw"],"remedio":p["medicament_raw"],"restricao":p["restricao_raw"]} for p in sorted(nos1, key=lambda x: x["nome"])],
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
body = {"message": "pulseiras relacao nominal", "content": content_b64, "branch": "main"}
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
