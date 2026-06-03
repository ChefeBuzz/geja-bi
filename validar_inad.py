#!/usr/bin/env python3
import json, os, base64, unicodedata, urllib.request
from google.oauth2.service_account import Credentials
import gspread

sa_info  = json.loads(os.environ["GEJA_SA_KEY"])
TOKEN    = os.environ["GITHUB_TOKEN"]
REPO     = "ChefeBuzz/geja-bi"
SHEET_ID = "1lOBHTIAzYkAWOjGwR66ISguvs247CA4R9m32Tp603vc"
SCOPES   = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

def norm(s):
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())

creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc    = gspread.authorize(creds)
sh    = gc.open_by_key(SHEET_ID)
ws    = sh.worksheet("Dados Médicos")
rows  = ws.get_all_values()
data  = rows[1:]

I_NOME=3; I_REST=45; I_DET=46

def col(row,i):
    try: return str(row[i]).strip() if i<len(row) else ""
    except: return ""

NAO = ["nao","não","nenhuma","nenhum","nao possui","não possui","sem restricao",
       "sem restrição","s/r","","nao tem","não tem","nao ha","não há"]

def classifica(restricao, det):
    val = det.strip() if det.strip() else restricao.strip()
    vl = norm(val)
    if not val or vl in NAO or len(vl) < 3: return [], ""

    cats = []
    vf = norm(restricao+" "+det)
    if any(k in vf for k in ["lactose","leite","laticinio","laticinios","proteina do leite",
                               "iogurte","creme de leite","manteiga","requeijao","queijo"]):
        cats.append("Lactose / Laticínios")
    if any(k in vf for k in ["vegetarian","vegano","vegan","nao come carne","sem carne",
                               "ovolacto","ovoveget","carne de origem animal"]):
        cats.append("Vegetariano / Vegano")
    if any(k in vf for k in ["gluten","glúten"]):
        cats.append("Sem Glúten")
    if any(k in vf for k in ["frutos do mar","camarao","camarão","peixe","marisco",
                               "tilapia","tilápia","atum"]):
        cats.append("Frutos do Mar / Peixe")
    if "ovo" in vf and "ovolacto" not in vf and "ovoveget" not in vf:
        cats.append("Ovo")
    if any(k in vf for k in ["corante","g6pd","fava"]):
        cats.append("Corante / G6PD")
    if any(k in vf for k in ["carne de porco","carne suina","carne suína","suino","suína"]):
        cats.append("Carne de Porco")
    if any(k in vf for k in ["banana","laranja","acai","oleaginosa","kiwi","salsich",
                               "abobora","brocolis","sal ","sodio","açaí"]):
        cats.append("Outros Alimentos")
    if any(k in vf for k in ["soja"]):
        cats.append("Soja")
    if not cats:
        cats.append("Específica")
    return cats, val

# Montar dicionário ficha médica
ficha = {}
for row in data:
    nome = col(row, I_NOME)
    if not nome or nome.lower() in ("","nan","none"): continue
    cats, det = classifica(col(row,I_REST), col(row,I_DET))
    ficha[norm(nome)] = {
        "nome": nome,
        "cats": cats,
        "detalhe": det,
        "tem_rest": bool(cats)
    }

print(f"Fichas carregadas: {len(ficha)}")
print(f"Com restrição: {sum(1 for v in ficha.values() if v['tem_rest'])}")

# Lista de inscritos
inscritos_txt = os.environ.get("INSCRITOS_JSON","[]")
inscritos = json.loads(inscritos_txt)

resultado = {
    "total": len(inscritos),
    "categorias": {},
    "sem_restricao": [],
    "sem_ficha": [],
}

cat_map = {}

for nome in inscritos:
    nn = norm(nome)
    entrada = ficha.get(nn)
    if not entrada:
        # busca parcial
        partes = nn.split()
        for k,v in ficha.items():
            kp = k.split()
            if len(partes)>=2 and len(kp)>=2 and partes[:2]==kp[:2]:
                entrada=v; break
    if not entrada:
        resultado["sem_ficha"].append(nome)
        continue
    if not entrada["tem_rest"]:
        resultado["sem_restricao"].append(entrada["nome"])
        continue
    for cat in entrada["cats"]:
        if cat not in cat_map: cat_map[cat]=[]
        cat_map[cat].append({"nome":entrada["nome"],"detalhe":entrada["detalhe"]})

resultado["categorias"] = cat_map
resultado["total_com_rest"] = sum(len(v) for v in cat_map.values())
resultado["total_sem_rest"] = len(resultado["sem_restricao"])
resultado["total_sem_ficha"]= len(resultado["sem_ficha"])

print(f"\nResultado:")
print(f"  Com restrição: {resultado['total_com_rest']}")
print(f"  Sem restrição: {resultado['total_sem_rest']}")
print(f"  Sem ficha    : {resultado['total_sem_ficha']}")
for cat, lista in cat_map.items():
    print(f"  {cat}: {[p['nome'] for p in lista]}")

content_b64 = base64.b64encode(json.dumps(resultado,ensure_ascii=False,indent=2).encode()).decode()
sha = None
try:
    req=urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
        headers={"Authorization":f"token {TOKEN}"})
    with urllib.request.urlopen(req) as r: sha=json.loads(r.read()).get("sha")
except: pass
body={"message":"restricao inscritos completo","content":content_b64,"branch":"main"}
if sha: body["sha"]=sha
req2=urllib.request.Request(f"https://api.github.com/repos/{REPO}/contents/validacao_resultado.json",
    data=json.dumps(body).encode(),
    headers={"Authorization":f"token {TOKEN}","Content-Type":"application/json","Accept":"application/vnd.github+json"},
    method="PUT")
with urllib.request.urlopen(req2) as r: print(f"\nSalvo! ({r.status})")
print("FIM")
