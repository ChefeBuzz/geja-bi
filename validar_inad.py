#!/usr/bin/env python3
import json, os, sys
from google.oauth2.service_account import Credentials
import gspread

sa_info  = json.loads(os.environ["GEJA_SA_KEY"])
SHEET_ID = "1lOBHTIAzYkAWOjGwR66ISguvs247CA4R9m32Tp603vc"
SCOPES   = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc    = gspread.authorize(creds)
sh    = gc.open_by_key(SHEET_ID)
ws    = sh.worksheet("Dados (2025 - 2026)")
rows  = ws.get_all_values()
data_rows = rows[3:]

def col(row, i):
    try: return str(row[i]).strip() if i < len(row) else ""
    except: return ""

def pag(val):
    if not val or val in ("-","—",""): return "NAO PAGO"
    v = val.strip().upper()
    if "SE APLICA" in v:  return "NAO SE APLICA"
    if "INCLU"     in v:  return "NAO INCLUIDO"
    if "ISEN"      in v:  return "ISENCAO"
    if "LICEN"     in v:  return "LICENCA"
    if "DESLIG"    in v:  return "DESLIGAMENTO"
    if v.startswith("#") or "PAGO" in v or "TRANSFER" in v: return "PAGO"
    return "OUTRO: " + val[:25]

print("=" * 60)
print("VALIDACAO AO VIVO — GOOGLE SHEETS")
print("=" * 60)

# 1. Ítalo e Isabel
print("\n--- ITALO E ISABEL ---")
for row in data_rows:
    nome = col(row, 2)
    if not nome or nome.lower() in ("nan","none",""): continue
    nl = nome.lower()
    if "italo" in nl or "ítalo" in nl or "isabel" in nl:
        status = col(row, 0)
        secao  = col(row, 4)
        p1s26  = col(row, 14)
        p2s25  = col(row, 10)
        print(f"\nNome  : {nome}")
        print(f"Status: {status} | Secao: {secao}")
        print(f"2s2025: {p2s25} -> {pag(p2s25)}")
        print(f"1s2026: {p1s26} -> {pag(p1s26)}")

# 2. Lista completa de inadimplentes 1s2026
print("\n\n--- INADIMPLENTES 1s2026 (ativos) ---")
inad = []
for row in data_rows:
    nome   = col(row, 2)
    status = col(row, 0)
    p1s26  = col(row, 14)
    if not nome or nome.lower() in ("nan","none",""): continue
    if status != "2. Ativo": continue
    pg = pag(p1s26)
    if pg not in ("PAGO","NAO SE APLICA","ISENCAO","NAO INCLUIDO","LICENCA","DESLIGAMENTO"):
        inad.append((nome, col(row, 4), p1s26, pg))

print(f"Total inadimplentes: {len(inad)}")
for i, (nome, sec, val, pg) in enumerate(sorted(inad), 1):
    print(f"  {i:2d}. {nome:<45} | {sec:<12} | {val[:20]:<22} | {pg}")

# Salvar resultado
result = {
    "total_inad": len(inad),
    "inadimplentes": [{"nome":n,"secao":s,"valor":v,"status":p} for n,s,v,p in sorted(inad)]
}
with open("validacao_resultado.json","w",encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
print("\nArquivo validacao_resultado.json salvo!")
print("FIM DA VALIDACAO")
