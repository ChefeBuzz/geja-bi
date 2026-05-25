#!/usr/bin/env python3
"""
GEJA BI — Build Script
REGRA OFICIAL INADIMPLENCIA:
  INADIMPLENTE = "EM ATRASO!!" em qualquer semestre
               OU célula vazia/branco em qualquer semestre ("Não Informado")
  FORA DA LISTA = Pago, Nao Se Aplica, Isencao, Licenca, Desligamento, Nao Incluido
"""
import json, os, sys
from datetime import datetime, timezone, timedelta, date
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    os.system("pip install gspread google-auth -q")
    import gspread
    from google.oauth2.service_account import Credentials

SA_JSON = os.environ.get("GEJA_SA_KEY", "")
if not SA_JSON:
    print("ERRO: GEJA_SA_KEY nao definida"); sys.exit(1)

sa_info  = json.loads(SA_JSON)
SHEET_ID = "1lOBHTIAzYkAWOjGwR66ISguvs247CA4R9m32Tp603vc"
SCOPES   = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

print("Conectando ao Google Sheets...")
creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc    = gspread.authorize(creds)
sh    = gc.open_by_key(SHEET_ID)
print("Conectado!")

def col(row, i, default=""):
    try:
        v = row[i] if i < len(row) else ""
        return str(v).strip() if v not in (None, "") else default
    except: return default

# Valores que indicam que o pagamento está QUITADO ou NÃO SE APLICA
QUITADOS = {
    "nao se aplica", "não se aplica",
    "nao incluido", "não incluído", "nao incluído",
    "isencao", "isenção",
    "licenca", "licença",
    "desligamento",
}

def classifica_pag(val):
    """
    Retorna classificação do pagamento.
    Vazio/branco → 'Nao Informado'  (INADIMPLENTE)
    EM ATRASO!!  → 'EM ATRASO!!'   (INADIMPLENTE)
    Resto        → classificação normal (NÃO inadimplente)
    """
    v = str(val).strip() if val else ""
    # Vazio ou traço → Não Informado
    if not v or v in ("-", "—", "x", "X"):
        return "Nao Informado"
    vu = v.upper()
    if "EM ATRASO" in vu:                    return "EM ATRASO!!"
    if "SE APLICA" in vu:                    return "Nao Se Aplica"
    if "INCLU" in vu:                        return "Nao Incluido"
    if "ISEN" in vu:                         return "Isencao"
    if "LICEN" in vu:                        return "Licenca"
    if "DESLIG" in vu:                       return "Desligamento"
    if v.startswith("#") or "PAGO" in vu or "TRANSFER" in vu:
        return "Pago"
    return "Outro"

def is_inadimplente(val):
    """True se o valor indica inadimplência (EM ATRASO!! ou vazio)"""
    c = classifica_pag(val)
    return c in ("EM ATRASO!!", "Nao Informado")

print("Lendo aba Dados...")
ws        = sh.worksheet("Dados (2025 - 2026)")
all_rows  = ws.get_all_values()
data_rows = all_rows[3:]

I_STATUS=0; I_NUM=1; I_NOME=2; I_CAT=3; I_SECAO=4; I_FUNC=5
I_SIT_REG=20; I_VENC_REG=21; I_LIC=19; I_SEXO=51
I_INGRESSO=97; I_TEMPO=98; I_APF=99; I_ATV=96
I_P1S2025=8; I_P2S2025=10; I_P1S2026=14
I_NASC=48; I_ST_LIC=34; I_ST_DESL=39

hoje = date.today()
associados = []
adultos    = []
atraso_nomes = []

for row in data_rows:
    nome = col(row, I_NOME)
    if not nome or nome.lower() in ("nan","none",""): continue
    status = col(row, I_STATUS)

    p1s25_raw = col(row, I_P1S2025)
    p2s25_raw = col(row, I_P2S2025)
    p1s26_raw = col(row, I_P1S2026)

    pag1s25 = classifica_pag(p1s25_raw)
    pag2s25 = classifica_pag(p2s25_raw)
    pag1s26 = classifica_pag(p1s26_raw)

    ingresso = 0
    try: ingresso = int(float(col(row, I_INGRESSO)))
    except: pass
    tempo = 0
    try: tempo = int(float(col(row, I_TEMPO)))
    except: tempo = (hoje.year - ingresso) if ingresso else 0

    a = {
        "nome":          nome,
        "numero":        col(row, I_NUM),
        "status":        status,
        "categoria":     col(row, I_CAT),
        "secao":         col(row, I_SECAO),
        "funcao":        col(row, I_FUNC),
        "sit_registro":  col(row, I_SIT_REG),
        "em_licenca":    col(row, I_LIC),
        "sexo":          col(row, I_SEXO),
        "pag_1s2025":    pag1s25,
        "pag_2s2025":    pag2s25,
        "pag_1s2026":    pag1s26,
        "ingresso":      ingresso,
        "tempo_mov":     tempo,
        "venc_registro": col(row, I_VENC_REG)[:10],
        "status_licenca":col(row, I_ST_LIC),
        "status_desl":   col(row, I_ST_DESL),
        "atv":           col(row, I_ATV),
        "apf_nome":      col(row, I_APF),
    }
    associados.append(a)

    if a["categoria"] in ("Escotista","Dirigente","Colaboradores"):
        adultos.append(a)

    # REGRA FINAL: inadimplente se EM ATRASO!! OU vazio em qualquer semestre
    if status == "2. Ativo":
        if is_inadimplente(p1s25_raw) or is_inadimplente(p2s25_raw) or is_inadimplente(p1s26_raw):
            atraso_nomes.append(nome)

atraso_nomes = sorted(set(atraso_nomes))
print(f"{len(associados)} associados | {len(adultos)} adultos | {len(atraso_nomes)} inadimplentes")

# Seções PAXTU
print("Calculando secoes...")
secoes_map = {
    "(2) ALG": {"ramo":"Lobinho","faixa":"Lobinho - 6-10 anos","color":"#10B981","bg":"#059669"},
    "(2) ALP": {"ramo":"Lobinho","faixa":"Lobinho - 6-10 anos","color":"#10B981","bg":"#047857"},
    "(2) AUC": {"ramo":"Lobinho","faixa":"Lobinho - 6-10 anos","color":"#10B981","bg":"#065F46"},
    "(3) TEA": {"ramo":"Escoteiro","faixa":"Escoteiro - 11-14 anos","color":"#3B82F6","bg":"#1D4ED8"},
    "(3) TECS":{"ramo":"Escoteiro","faixa":"Escoteiro - 11-14 anos","color":"#3B82F6","bg":"#1E40AF"},
    "(3) TEG": {"ramo":"Escoteiro","faixa":"Escoteiro - 11-14 anos","color":"#3B82F6","bg":"#1e3a8a"},
    "(4) TSI": {"ramo":"Senior","faixa":"Senior - 15-17 anos","color":"#F59E0B","bg":"#B45309"},
    "(4) TSY": {"ramo":"Senior","faixa":"Senior - 15-17 anos","color":"#F59E0B","bg":"#92400E"},
    "(5) CLÃ": {"ramo":"Pioneiro","faixa":"Pioneiro - 18-21 anos","color":"#8B5CF6","bg":"#6D28D9"},
}

secoes_data   = {k: [] for k in list(secoes_map.keys()) + ["Adultos Voluntarios"]}
secoes_config = []

for row in data_rows:
    if col(row, I_STATUS) != "2. Ativo": continue
    nome = col(row, I_NOME)
    if not nome or nome.lower() in ("nan","none",""): continue
    sec  = col(row, I_SECAO)
    reg  = col(row, I_NUM)
    sx   = col(row, I_SEXO)
    sexo = "Feminino" if sx=="F" else "Masculino" if sx=="M" else sx
    cat  = col(row, I_CAT)
    func = col(row, I_FUNC)
    nasc = col(row, I_NASC)
    idade = None
    if nasc:
        for fmt in ("%Y-%m-%d","%d/%m/%Y"):
            try:
                from datetime import datetime as dt
                n = dt.strptime(nasc[:10], fmt).date()
                idade = hoje.year - n.year - ((hoje.month,hoje.day)<(n.month,n.day))
                break
            except: pass
    entry = [nome, reg, sexo, idade, cat, func]
    if sec in secoes_map:
        secoes_data[sec].append(entry)
    else:
        secoes_data["Adultos Voluntarios"].append(entry + [sec])

seen = set()
for sec, cfg in secoes_map.items():
    if sec in seen: continue
    seen.add(sec)
    lista = secoes_data.get(sec, [])
    secoes_config.append({
        "key": sec, "ramo": cfg["ramo"], "faixa": cfg["faixa"],
        "color": cfg["color"], "bg": cfg["bg"],
        "M": sum(1 for m in lista if m[2]=="Masculino"),
        "F": sum(1 for m in lista if m[2]=="Feminino"),
        "total": len(lista)
    })

lav = secoes_data["Adultos Voluntarios"]
secoes_config.append({
    "key":"Adultos Voluntarios","ramo":"Adulto Voluntario",
    "faixa":"Escotistas e Dirigentes","color":"#EF4444","bg":"#B91C1C",
    "M": sum(1 for m in lav if m[2]=="Masculino"),
    "F": sum(1 for m in lav if m[2]=="Feminino"),
    "total": len(lav)
})

total_ativos = sum(s["total"] for s in secoes_config)
brt = timezone(timedelta(hours=-3))
ts  = datetime.now(brt).strftime("%d/%m/%Y as %H:%M (BRT)")
print(f"Timestamp: {ts}")

payload = {
    "db_adm":       {"associados": associados, "atraso_2026": atraso_nomes},
    "db_adultos":   adultos,
    "secoes_paxtu": secoes_config,
    "secoes_data":  secoes_data,
    "timestamp":    ts,
    "total_ativos": total_ativos,
}
Path("/tmp/payload_fresh.json").write_text(
    json.dumps(payload, ensure_ascii=False, separators=(",",":"), default=str),
    encoding="utf-8"
)
print(f"Payload: {Path('/tmp/payload_fresh.json').stat().st_size:,} bytes")
print("BUILD OK")
