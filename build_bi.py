#!/usr/bin/env python3
"""
GEJA BI — Build Script
Busca dados do Google Sheets e gera index.html atualizado.
Roda via GitHub Actions todo dia às 2h BRT (5h UTC).
"""

import json, time, base64, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Dependências ──────────────────────────────────────────────
try:
    import gspread
    from google.oauth2.service_account import Credentials
except ImportError:
    os.system("pip install gspread google-auth -q")
    import gspread
    from google.oauth2.service_account import Credentials

# ── Credenciais ───────────────────────────────────────────────
SA_JSON = os.environ.get("GEJA_SA_KEY", "")
if not SA_JSON:
    # Tentar ler arquivo local para testes
    sa_path = Path("data-geja-5f503fb3a23f.json")
    if sa_path.exists():
        SA_JSON = sa_path.read_text()
    else:
        print("❌ GEJA_SA_KEY não definida"); sys.exit(1)

sa_info = json.loads(SA_JSON)
SHEET_ID = "1lOBHTIAzYkAWOjGwR66ISguvs247CA4R9m32Tp603vc"

# ── Conectar ao Google Sheets ──────────────────────────────────
print("🔗 Conectando ao Google Sheets...")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds  = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
gc     = gspread.authorize(creds)
sh     = gc.open_by_key(SHEET_ID)
print("✅ Conectado!")

# ── Helpers ───────────────────────────────────────────────────
def ws(name):
    return sh.worksheet(name)

def col(row, i, default=""):
    try:
        v = row[i] if i < len(row) else ""
        return str(v).strip() if v not in (None, "") else default
    except:
        return default

def classifica_pag(val):
    if not val or val in ("-", ""):
        return "Inativo/Desligado"
    v = str(val).strip().upper()
    if v == "NÃO SE APLICA":  return "Não Se Aplica"
    if v == "NÃO INCLUÍDO":   return "Não Incluído"
    if v == "ISENÇÃO":        return "Isenção"
    if v == "LICENÇA":        return "Licença"
    if v == "DESLIGAMENTO":   return "Desligamento"
    if v.startswith("#") or "PAGO" in v or "TRANSFERÊNCIA" in v:
        return "Pago"
    return "Outro"

def get_ramo(secao):
    s = str(secao).strip()
    if s.startswith("(2)"): return "Lobinho"
    if s.startswith("(3)"): return "Escoteiro"
    if s.startswith("(4)"): return "Sênior"
    if s.startswith("(5)"): return "Pioneiro"
    return "Adulto Voluntário"

# ── Aba principal: Dados (2025-2026) ──────────────────────────
print("📊 Lendo aba Dados...")
dados_ws  = ws("Dados (2025 - 2026)")
all_rows  = dados_ws.get_all_values()
headers   = all_rows[2]   # linha 3 = cabeçalhos
data_rows = all_rows[3:]  # linha 4 em diante

# Mapear índices pelos cabeçalhos reais
def idx(nome_col):
    for i, h in enumerate(headers):
        if nome_col.lower() in h.lower():
            return i
    return -1

# Índices fixos confirmados anteriormente
I_STATUS  = 0;  I_NUM = 1;  I_NOME = 2;  I_CAT = 3
I_SECAO   = 4;  I_FUNC = 5; I_SIT_REG = 20; I_VENC_REG = 21
I_LIC     = 19; I_SEXO = 51; I_INGRESSO = 97; I_TEMPO = 98
I_APF     = 99; I_ATV = 96
I_P1S2025 = 8;  I_P2S2025 = 10; I_P1S2026 = 14
I_NASC    = 48; I_IDADE = 49
I_ST_LIC  = 34; I_ST_DESL = 39

associados = []
adultos    = []
atraso_2026 = []

from datetime import date
hoje = date.today()

for row in data_rows:
    nome = col(row, I_NOME)
    if not nome or nome.lower() == "nan": continue
    status = col(row, I_STATUS)

    pag1s25 = classifica_pag(col(row, I_P1S2025))
    pag2s25 = classifica_pag(col(row, I_P2S2025))
    pag1s26 = classifica_pag(col(row, I_P1S2026))

    ingresso = col(row, I_INGRESSO)
    try:   ingresso = int(float(ingresso))
    except: ingresso = 0

    tempo = col(row, I_TEMPO)
    try:   tempo = int(float(tempo))
    except: tempo = (hoje.year - ingresso) if ingresso else 0

    a = {
        "nome":        nome,
        "numero":      col(row, I_NUM),
        "status":      status,
        "categoria":   col(row, I_CAT),
        "secao":       col(row, I_SECAO),
        "funcao":      col(row, I_FUNC),
        "sit_registro":col(row, I_SIT_REG),
        "em_licenca":  col(row, I_LIC),
        "sexo":        col(row, I_SEXO),
        "pag_1s2025":  pag1s25,
        "pag_2s2025":  pag2s25,
        "pag_1s2026":  pag1s26,
        "ingresso":    ingresso,
        "tempo_mov":   tempo,
        "venc_registro":col(row, I_VENC_REG)[:10] if col(row, I_VENC_REG) else "",
        "status_licenca": col(row, I_ST_LIC),
        "status_desl":    col(row, I_ST_DESL),
        "atv":         col(row, I_ATV),
        "apf_nome":    col(row, I_APF),
    }
    associados.append(a)

    # Adultos
    if a["categoria"] in ("Escotista","Dirigente","Colaboradores"):
        adultos.append(a)

    # Inadimplentes 1s2026 (ativo + pag = Inativo ou Outro)
    if status == "2. Ativo" and pag1s26 not in ("Pago","Não Se Aplica","Isenção","Não Incluído","Licença"):
        atraso_2026.append(nome)

db_adm = {"associados": associados, "atraso_2026": sorted(set(atraso_2026))}
print(f"  ✅ {len(associados)} associados | {len(adultos)} adultos | {len(atraso_2026)} inadimplentes")

# ── Seções PAXTU ──────────────────────────────────────────────
print("📊 Calculando seções PAXTU...")
secoes_map = {
    "(2) ALG": {"ramo":"Lobinho","faixa":"Lobinho · 6–10 anos","color":"#10B981","bg":"#059669"},
    "(2) ALP": {"ramo":"Lobinho","faixa":"Lobinho · 6–10 anos","color":"#10B981","bg":"#047857"},
    "(2) AUC": {"ramo":"Lobinho","faixa":"Lobinho · 6–10 anos","color":"#10B981","bg":"#065F46"},
    "(3) TEA": {"ramo":"Escoteiro","faixa":"Escoteiro · 11–14 anos","color":"#3B82F6","bg":"#1D4ED8"},
    "(3) TECS":{"ramo":"Escoteiro","faixa":"Escoteiro · 11–14 anos","color":"#3B82F6","bg":"#1E40AF"},
    "(3) TEG": {"ramo":"Escoteiro","faixa":"Escoteiro · 11–14 anos","color":"#3B82F6","bg":"#1e3a8a"},
    "(4) TSI": {"ramo":"Sênior","faixa":"Sênior · 15–17 anos","color":"#F59E0B","bg":"#B45309"},
    "(4) TSY": {"ramo":"Sênior","faixa":"Sênior · 15–17 anos","color":"#F59E0B","bg":"#92400E"},
    "(5) CLÃ": {"ramo":"Pioneiro","faixa":"Pioneiro · 18–21 anos","color":"#8B5CF6","bg":"#6D28D9"},
}
ADULTO_SECS = {"ADM","DME","ECOM","EEVT","EGAD","ELAN","ELOJ","EMED","EPAT","GOV","PRES","À definir","Não se aplica","EMED"}

secoes_data   = {k: [] for k in list(secoes_map.keys()) + ["Adultos Voluntários"]}
secoes_config = []

for row in data_rows:
    if col(row, I_STATUS) != "2. Ativo": continue
    nome = col(row, I_NOME)
    if not nome or nome.lower() == "nan": continue
    sec  = col(row, I_SECAO)
    reg  = col(row, I_NUM)
    sexo_raw = col(row, I_SEXO)
    sexo = "Feminino" if sexo_raw == "F" else "Masculino" if sexo_raw == "M" else sexo_raw
    cat  = col(row, I_CAT)
    func = col(row, I_FUNC)
    nasc = col(row, I_NASC)
    idade = None
    if nasc:
        try:
            from datetime import datetime as dt
            n = dt.strptime(nasc[:10], "%Y-%m-%d").date()
            idade = hoje.year - n.year - ((hoje.month, hoje.day) < (n.month, n.day))
        except:
            try:
                n = dt.strptime(nasc[:10], "%d/%m/%Y").date()
                idade = hoje.year - n.year - ((hoje.month, hoje.day) < (n.month, n.day))
            except: pass

    if sec in secoes_map:
        secoes_data[sec].append([nome, reg, sexo, idade, cat, func])
    elif any(s in sec for s in ADULTO_SECS) or sec not in secoes_map:
        secoes_data["Adultos Voluntários"].append([nome, reg, sexo, idade, cat, func, sec])

# Montar config
cores_adulto = {"color":"#EF4444","bg":"#B91C1C","ramo":"Adulto Voluntário","faixa":"Escotistas e Dirigentes"}
for sec, cfg in secoes_map.items():
    lista = secoes_data[sec]
    secoes_config.append({
        "key": sec, "ramo": cfg["ramo"], "faixa": cfg["faixa"],
        "color": cfg["color"], "bg": cfg["bg"],
        "M": sum(1 for m in lista if m[2]=="Masculino"),
        "F": sum(1 for m in lista if m[2]=="Feminino"),
        "total": len(lista)
    })

lista_av = secoes_data["Adultos Voluntários"]
secoes_config.append({
    "key":"Adultos Voluntários","ramo":"Adulto Voluntário",
    "faixa":"Escotistas e Dirigentes",
    "color":"#EF4444","bg":"#B91C1C",
    "M": sum(1 for m in lista_av if m[2]=="Masculino"),
    "F": sum(1 for m in lista_av if m[2]=="Feminino"),
    "total": len(lista_av)
})

total_ativos = sum(s["total"] for s in secoes_config)
print(f"  ✅ {total_ativos} ativos em {len(secoes_config)} seções")

# ── Dados Médicos (PAXTU) ─────────────────────────────────────
print("📊 Lendo aba Dados Médicos (PAXTU)...")
# Tentar ler aba — se não existir, usar dados fixos da v5.1
try:
    med_ws   = ws("Dados Médicos")
    med_rows = med_ws.get_all_values()
    print(f"  ✅ Dados Médicos: {len(med_rows)} linhas")
    HAS_MED = True
except:
    print("  ⚠️  Aba 'Dados Médicos' não encontrada — usando dados anteriores")
    HAS_MED = False

# ── Gerar timestamp BRT ───────────────────────────────────────
brt = timezone(timedelta(hours=-3))
now_brt = datetime.now(brt)
timestamp = now_brt.strftime("%d/%m/%Y às %H:%M (BRT)")
print(f"\n🕐 Timestamp: {timestamp}")

# ── Salvar payload ────────────────────────────────────────────
payload = {
    "db_adm":       db_adm,
    "db_adultos":   adultos,
    "secoes_paxtu": secoes_config,
    "secoes_data":  secoes_data,
    "timestamp":    timestamp,
    "total_ativos": total_ativos,
}
with open("/tmp/payload_fresh.json","w",encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, separators=(",",":"), default=str)

size = Path("/tmp/payload_fresh.json").stat().st_size
print(f"✅ Payload gerado: {size:,} bytes")
