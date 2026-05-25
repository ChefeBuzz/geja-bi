#!/usr/bin/env python3
"""Injeta dados frescos no template e faz push para o GitHub Pages."""
import json, base64, re, os, sys, urllib.request
from pathlib import Path

TOKEN = os.environ.get("GITHUB_TOKEN","")
REPO  = "ChefeBuzz/geja-bi"

with open("/tmp/payload_fresh.json", encoding="utf-8") as f:
    p = json.load(f)

html = Path("index.html").read_text(encoding="utf-8")

def js(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",",":"), default=str)

# Substituir bloco de dados
START = "// ═══════════ DADOS ═══════════"
END   = "// ═══════════ AUTH ═══════════"
s = html.find(START); e = html.find(END)
if s < 0 or e < 0:
    print("❌ Marcadores não encontrados"); sys.exit(1)

# Preservar DB_PAXTU e DATA_MED (dados médicos fixos até nova aba)
idx_paxtu = html.find("const DB_PAXTU")
idx_datamed = html.find("const DATA_MED")

def extract_const(h, name):
    idx = h.find(f"const {name}")
    if idx < 0: return "null"
    eq = h.find("=", idx) + 1
    depth = 0; in_str = False; esc = False; end = eq
    for pos, ch in enumerate(h[eq:], eq):
        if esc: esc=False; continue
        if ch == "\\" and in_str: esc=True; continue
        if ch == "\"" and not esc: in_str = not in_str; continue
        if in_str: continue
        if ch in "[{": depth+=1
        elif ch in "]}":
            depth -= 1
            if depth == 0: end=pos+1; break
    return h[eq:end].strip()

db_paxtu_str = extract_const(html, "DB_PAXTU")
data_med_str = extract_const(html, "DATA_MED")

novo_bloco = f"""{START}
const DB_PAXTU    = {db_paxtu_str};
const DATA_MED    = {data_med_str};
const SECOES_PAXTU= {js(p["secoes_paxtu"])};
const SECOES_DATA = {js(p["secoes_data"])};
const DB_ADM      = {js(p["db_adm"])};
const DB_ADULTOS  = {js(p["db_adultos"])};
const ATRASO_2026 = {js(p["db_adm"]["atraso_2026"])};
const ASSOC       = DB_ADM.associados;
"""
html = html[:s] + novo_bloco + "\n" + html[e:]

# Atualizar badge de timestamp
ts = p.get("timestamp","—")
html = re.sub(
    r'id="badge-update">⬤ [^<]+<',
    f'id="badge-update">⬤ Atualizado: {ts}<',
    html, count=1
)
html = re.sub(
    r'id="hdata">[^<]+<',
    f'id="hdata">Grupo Escoteiro — Atualizado {ts}<',
    html, count=1
)
print(f"✅ HTML montado: {len(html):,} chars")
Path("index.html").write_text(html, encoding="utf-8")

# Push via API
content_b64 = base64.b64encode(html.encode()).decode()
req = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/index.html",
    headers={"Authorization": f"token {TOKEN}", "Accept": "application/vnd.github+json"}
)
with urllib.request.urlopen(req) as r:
    sha = json.loads(r.read())["sha"]

payload = json.dumps({
    "message": f"🔄 Auto-update BI GEJA — {ts}",
    "content": content_b64, "sha": sha, "branch": "main"
}).encode()
req2 = urllib.request.Request(
    f"https://api.github.com/repos/{REPO}/contents/index.html",
    data=payload,
    headers={"Authorization": f"token {TOKEN}", "Content-Type": "application/json"},
    method="PUT"
)
with urllib.request.urlopen(req2) as r:
    resp = json.loads(r.read())
print(f"✅ Push OK! Commit: {resp['commit']['sha'][:12]}")
print(f"🌐 https://chefebuzz.github.io/geja-bi/")
