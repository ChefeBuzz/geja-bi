#!/usr/bin/env python3
import json, base64, re, os, sys, urllib.request, urllib.error
from pathlib import Path

TOKEN = os.environ.get("GITHUB_TOKEN","")
REPO  = "ChefeBuzz/geja-bi"

with open("/tmp/payload_fresh.json", encoding="utf-8") as f:
    p = json.load(f)

html = Path("index.html").read_text(encoding="utf-8")

def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",",":"), default=str)

def extract_const(h, name):
    idx = h.find("const " + name)
    if idx < 0: return "null"
    eq = h.find("=", idx) + 1
    depth=0; in_s=False; esc=False; end=eq
    for pos, ch in enumerate(h[eq:], eq):
        if esc: esc=False; continue
        if ch==chr(92) and in_s: esc=True; continue
        if ch==chr(34) and not esc: in_s=not in_s; continue
        if in_s: continue
        if ch in "[{": depth+=1
        elif ch in "]}":
            depth-=1
            if depth==0: end=pos+1; break
    return h[eq:end].strip()

db_paxtu_str = extract_const(html, "DB_PAXTU")
data_med_str = extract_const(html, "DATA_MED")

START = "// DADOS_START"
END   = "// DADOS_END"

if START not in html or END not in html:
    print("ERRO: marcadores DADOS_START/END nao encontrados"); sys.exit(1)

ts = p.get("timestamp","desconhecido")

partes = [
    START, "\n",
    "const DB_PAXTU    = ", db_paxtu_str, ";\n",
    "const DATA_MED    = ", data_med_str, ";\n",
    "const SECOES_PAXTU= ", js(p["secoes_paxtu"]), ";\n",
    "const SECOES_DATA = ", js(p["secoes_data"]), ";\n",
    "const DB_ADM      = ", js(p["db_adm"]), ";\n",
    "const DB_ADULTOS  = ", js(p["db_adultos"]), ";\n",
    "const ATRASO_2026 = ", js(p["db_adm"]["atraso_2026"]), ";\n",
    "const ASSOC       = DB_ADM.associados;\n",
    'const LAST_UPDATE = "', ts, '";\n',
]
novo_bloco = "".join(partes)

s = html.find(START)
e = html.find(END)
html = html[:s] + novo_bloco + "\n" + html[e:]

html = re.sub(
    r'id="badge-update">[^<]+<',
    'id="badge-update">Atualizado: ' + ts + '<',
    html, count=1
)
html = re.sub(
    r'id="hdata">[^<]+<',
    'id="hdata">Grupo Escoteiro \u2014 Atualizado ' + ts + '<',
    html, count=1
)

print("HTML: {:,} chars".format(len(html)))
Path("index.html").write_text(html, encoding="utf-8")

content_b64 = base64.b64encode(html.encode()).decode()
req = urllib.request.Request(
    "https://api.github.com/repos/" + REPO + "/contents/index.html",
    headers={"Authorization": "token " + TOKEN, "Accept": "application/vnd.github+json"}
)
with urllib.request.urlopen(req) as r:
    sha = json.loads(r.read())["sha"]

payload_data = json.dumps({
    "message": "Atualizado BI GEJA — " + ts,
    "content": content_b64, "sha": sha, "branch": "main"
}).encode()
req2 = urllib.request.Request(
    "https://api.github.com/repos/" + REPO + "/contents/index.html",
    data=payload_data,
    headers={"Authorization": "token " + TOKEN,
             "Content-Type": "application/json",
             "Accept": "application/vnd.github+json"},
    method="PUT"
)
with urllib.request.urlopen(req2) as r:
    resp = json.loads(r.read())
print("Push OK! Commit: " + resp["commit"]["sha"][:12])
print("PUSH OK")
