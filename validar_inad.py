#!/usr/bin/env python3
"""
Cruza lista de inscritos no acampamento com ficha médica (Dados Médicos).
Retorna classificação de restrição alimentar para cada inscrito.
"""
import json, os, base64, urllib.request, unicodedata
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

def normaliza(s):
    """Normaliza para comparação: minúsculo, sem acento, sem espaços duplos."""
    s = unicodedata.normalize("NFD", str(s))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return " ".join(s.lower().split())

# Índices
I_NOME     = 3
I_RESTRICAO = 45
I_REST_DET  = 46

def col(row, i):
    try: return str(row[i]).strip() if i < len(row) else ""
    except: return ""

NAO_RESTRICAO = [
    "nao","não","nenhuma","nenhum","nao possui","não possui",
    "sem restricao","sem restrição","s/r","","nao tem","não tem"
]

def classifica_restricao(restricao, det):
    """Classifica tipo de restrição alimentar."""
    val = (det or restricao).strip()
    vl  = normaliza(val)

    if not val or vl in NAO_RESTRICAO: return None, None

    # Categorias
    vl_full = normaliza(restricao + " " + det)
    cat = []

    if any(k in vl_full for k in ["lactose","leite","laticinio","laticinios",
                                    "derivado de leite","proteina do leite",
                                    "leite de vaca","iogurte","creme de leite",
                                    "manteiga","requeijao","queijo"]):
        cat.append("🥛 Lactose / Laticínios")

    if any(k in vl_full for k in ["vegetarian","vegano","vegan","nao come carne",
                                    "sem carne","ovolacto","ovovegetarian"]):
        cat.append("🥦 Vegetariano / Vegano")

    if any(k in vl_full for k in ["gluten","glúten"]):
        cat.append("🌾 Sem Glúten")

    if any(k in vl_full for k in ["frutos do mar","camarao","camarão","peixe",
                                    "marisco","salmao","atum","tilapia","tilápia"]):
        cat.append("🦐 Frutos do Mar / Peixe")

    if any(k in vl_full for k in ["ovo","eggs"]) and "ovolacto" not in vl_full:
        cat.append("🥚 Ovo")

    if any(k in vl_full for k in ["soja"]):
        cat.append("🫘 Soja")

    if any(k in vl_full for k in ["corante","g6pd","fava"]):
        cat.append("🎨 Corante / G6PD")

    if any(k in vl_full for k in ["carne de porco","carne suina","carne suína","suino"]):
        cat.append("🐷 Carne de Porco")

    if any(k in vl_full for k in ["banana","laranja","acai","açaí","oleaginosa",
                                    "kiwi","salsicha","salsichas"]):
        cat.append("🍌 Outros Alimentos")

    if any(k in vl_full for k in ["sal","baixo sodio","sodio"]):
        cat.append("🧂 Baixo Sódio")

    if not cat:
        cat.append("⚠️ Restrição Específica")

    return cat, val

# Montar dicionário da ficha médica: nome_normalizado → dados
ficha = {}
for row in data:
    nome = col(row, I_NOME)
    if not nome or nome.lower() in ("","nan","none"): continue
    ficha[normaliza(nome)] = {
        "nome_original": nome,
        "restricao": col(row, I_RESTRICAO),
        "restricao_det": col(row, I_REST_DET),
    }

# Lista de inscritos (passada como JSON no env)
inscritos = json.loads(os.environ["INSCRITOS_JSON"])

resultado = {
    "sem_restricao":    [],
    "com_restricao":    {},   # categoria → [nomes]
    "sem_ficha":        [],
    "total_inscritos":  len(inscritos),
    "total_com_rest":   0,
    "total_sem_rest":   0,
    "total_sem_ficha":  0,
}

cat_map = {}  # cat → [(nome, detalhe)]

for nome in inscritos:
    norm = normaliza(nome)

    # Busca exata
    entrada = ficha.get(norm)

    # Busca parcial se não achou
    if not entrada:
        for k, v in ficha.items():
            # Verifica se as primeiras 2 palavras batem
            partes_i = norm.split()
            partes_k = k.split()
            if len(partes_i) >= 2 and partes_i[:2] == partes_k[:2]:
                entrada = v
                break

    if not entrada:
        resultado["sem_ficha"].append(nome)
        resultado["total_sem_ficha"] += 1
        continue

    cats, det = classifica_restricao(entrada["restricao"], entrada["restricao_det"])

    if cats is None:
        resultado["sem_restricao"].append(entrada["nome_original"])
        resultado["total_sem_rest"] += 1
    else:
        resultado["total_com_rest"] += 1
        for cat in cats:
            if cat not in cat_map:
                cat_map[cat] = []
            cat_map[cat].append({
                "nome": entrada["nome_original"],
                "detalhe": det[:100]
            })

resultado["com_restricao"] = cat_map

print(f"Total inscritos: {len(inscritos)}")
print(f"Com ficha: {len(inscritos)-resultado['total_sem_ficha']}")
print(f"Sem ficha: {resultado['total_sem_ficha']}")
print(f"Com restrição: {resultado['total_com_rest']}")
print(f"Sem restrição: {resultado['total_sem_rest']}")
print(f"\nCategorias:")
for cat, pessoas in cat_map.items():
    print(f"  {cat}: {len(pessoas)} pessoas")

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

body = {"message": "restricao alimentar inscritos", "content": content_b64, "branch": "main"}
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
