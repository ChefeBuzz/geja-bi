#!/usr/bin/env python3
"""
Gera relação refinada de pulseiras.
Remédio contínuo = exclui "Nenhum medicamento informado" e marcações "N" (não contínuo)
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
ws    = sh.worksheet("Dados Médicos")
rows  = ws.get_all_values()
data  = rows[1:]

I_NOME      = 3
I_ALERGIAS  = 49
I_RESTRICAO = 45
I_REST_DET  = 46
I_MED       = 53

NENHUM = [
    "nenhum medicamento informado",
    "nenhum",
    "nenhuma",
    "não possui",
    "nao possui",
    "não usa",
    "nao usa",
    "não toma",
    "nao toma",
]

def col(row, i):
    try: return str(row[i]).strip() if i < len(row) else ""
    except: return ""

def tem_remedio_continuo(val):
    """Só conta como remédio contínuo se tiver 'S' de contínuo na ficha
    e não for uma das frases de negação."""
    v = val.strip()
    vl = v.lower()
    if not v or any(neg in vl for neg in NENHUM):
        return False, ""
    # Verificar se há pelo menos um item com 'S' (contínuo) na listagem
    # Padrão da ficha: "NomeMed S" ou "NomeMed N" (S=sim contínuo, N=não contínuo/eventual)
    linhas = [l.strip() for l in v.replace(";","\n").split("\n") if l.strip()]
    continuos = []
    for linha in linhas:
        partes = linha.rsplit(" ", 1)
        if len(partes) == 2 and partes[1].strip().upper() == "S":
            continuos.append(partes[0].strip())
        elif len(partes) == 2 and partes[1].strip().upper() == "N":
            continue  # eventual, não conta
        elif len(partes) >= 1 and partes[0].strip():
            # sem marcação S/N — incluir se não for frase negativa
            if not any(neg in linha.lower() for neg in NENHUM):
                continuos.append(linha)
    if continuos:
        return True, "; ".join(continuos[:3])
    return False, ""

def tem_picada(alergias):
    a = alergias.lower()
    return any(k in a for k in ["picada","inseto","abelha","vespa","formiga",
                                  "mosquito","aranha","pernilongo","marimbondo",
                                  "burrachudo"])

def tem_med_alergia(alergias):
    a = alergias.lower()
    return any(k in a for k in ["medicament","remédio","remedio",
                                  "antibiótico","antibiotic","dipirona",
                                  "anestesi","penicilina","aspirina",
                                  "ibuprofeno","alivium","sulfa","tramal",
                                  "corante","amoxicilina","tilatil",
                                  "sotalol","ácido acetil","g6pd"])

def tem_restricao(restricao, det):
    nao = ["não possui","nao possui","não tem","nao tem","nenhuma",
           "não","nao","s/r","sem restrição","sem restricao"]
    for v in [restricao, det]:
        vl = v.lower().strip()
        if not vl or any(n == vl for n in nao):
            continue
        if any(neg in vl for neg in nao):
            continue
        return True, v
    return False, ""

# Processar
pessoas = []
for row in data:
    nome = col(row, I_NOME)
    if not nome or nome.lower() in ("","nan","none"): continue

    alergias  = col(row, I_ALERGIAS)
    restricao = col(row, I_RESTRICAO)
    rest_det  = col(row, I_REST_DET)
    med       = col(row, I_MED)

    p1 = tem_picada(alergias)
    p2 = tem_med_alergia(alergias)
    ok_med, med_detalhe = tem_remedio_continuo(med)
    p3 = ok_med
    ok_rest, rest_detalhe = tem_restricao(restricao, rest_det)
    p4 = ok_rest

    qtd = sum([p1, p2, p3, p4])
    if qtd == 0: continue

    campos = []
    if p1: campos.append("ALERGIA A PICADAS")
    if p2: campos.append("ALERGIA A MEDICAMENTOS")
    if p3: campos.append("REMEDIO CONTINUO")
    if p4: campos.append("RESTRICAO ALIMENTAR")

    # Detalhe útil para o PDF
    det = []
    if p1:
        trecho = alergias.split("Picada")[1][:60] if "Picada" in alergias else alergias[:60]
        det.append(f"Picada: {trecho.strip()}")
    if p2:
        idx = alergias.lower().find("medicament")
        trecho = alergias[max(0,idx):idx+60] if idx>=0 else alergias[:60]
        det.append(f"Alergia med: {trecho.strip()}")
    if p3:
        det.append(f"Remedio: {med_detalhe[:60]}")
    if p4:
        det.append(f"Restricao: {rest_detalhe[:60]}")

    pessoas.append({
        "nome":   nome,
        "qtd":    qtd,
        "campos": campos,
        "detalhe":det,
    })

pessoas.sort(key=lambda x: (-x["qtd"], x["nome"]))

nos4 = [p for p in pessoas if p["qtd"]==4]
nos3 = [p for p in pessoas if p["qtd"]==3]
nos2 = [p for p in pessoas if p["qtd"]==2]
nos1 = [p for p in pessoas if p["qtd"]==1]

print(f"Total: {len(pessoas)}")
print(f"  4 campos: {len(nos4)}")
print(f"  3 campos: {len(nos3)}")
print(f"  2 campos: {len(nos2)}")
print(f"  1 campo:  {len(nos1)}")

result = {
    "total": len(pessoas),
    "nos4": nos4, "nos3": nos3,
    "nos2": nos2, "nos1": nos1
}

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

body = {"message": "pulseiras refinadas", "content": content_b64, "branch": "main"}
if sha: body["sha"] = sha
req2 = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
    data=json.dumps(body).encode(),
    headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json",
             "Accept": "application/vnd.github+json"},
    method="PUT"
)
with urllib.request.urlopen(req2) as r:
    print(f"Salvo! ({r.status})")
print("FIM")
