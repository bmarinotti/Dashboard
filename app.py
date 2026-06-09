"""
Monitor Macro — Streamlit App
Fontes: B3 DI1 API (15 min lag) + ANBIMA NTN-B arquivo diário
Design refeito focado em UX (Light Theme) com tabelas centralizadas, claras e auto-refresh de 10 min.
"""

import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
from datetime import datetime, date, timedelta
from io import StringIO
from urllib.parse import urlparse

# ================================================================
# PAGE CONFIG & CSS DEFINITIONS
# ================================================================
st.set_page_config(
    page_title="Monitor Macro",
    layout="wide",
    page_icon="📈",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
    /* Cores Light Mode baseadas em Design Systems Modernos */
    --bg: #F4F7F9;          /* Fundo da aplicação - cinza claro */
    --surf: #FFFFFF;        /* Superfície principal (Cards) - branco */
    --surf2: #F8FAFC;       /* Superfície secundária (Hovers e cabeçalhos de tabela) */
    --surf3: #F1F5F9;       /* Superfície terciária (Tabs inativas) */
    --border: #E2E8F0;      /* Bordas suaves */
    --border2: #CBD5E1;     /* Bordas com mais contraste (Inputs) */
    
    --text1: #0F172A;       /* Texto principal (quase preto para legibilidade) */
    --text2: #475569;       /* Texto secundário (cinza escuro) */
    --text3: #64748B;       /* Texto terciário/Metadados (cinza médio) */
    
    --accent: #2563EB;      /* Azul Royal corporativo moderno */
    --accentbg: #EFF6FF;    /* Fundo azul translúcido */
    
    --green: #059669;       /* Verde acessível (lucro/alta) */
    --greenbg: #D1FAE5;     
    --red: #DC2626;         /* Vermelho acessível (prejuízo/baixa) */
    --redbg: #FEE2E2;       
    
    --radius: 12px;         /* Cantos arredondados modernos */
    --radius-sm: 8px;
    --shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
}

*,*::before,*::after{box-sizing:border-box}
html,body,[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"]>.main{
    background:var(--bg)!important;
    font-family:'Plus Jakarta Sans',-apple-system,system-ui,sans-serif;
    -webkit-font-smoothing:antialiased; color:var(--text1);
}
[data-testid="stHeader"]{background:transparent!important}
[data-testid="stDecoration"]{display:none!important}
section[data-testid="stSidebar"]{display:none!important}
.block-container{padding-top:0rem!important;padding-bottom:4rem!important;max-width:1440px}
hr{border-color:var(--border)!important;margin:0rem 0!important}

/* ── Tabs ─ segmented control moderno ── */
.stTabs [data-baseweb="tab-list"]{
    background:var(--surf);border:1px solid var(--border);
    border-radius:var(--radius);padding:5px;gap:4px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
}
.stTabs [data-baseweb="tab"]{
    background:transparent;color:var(--text2);font-size:12px;
    font-weight:600;letter-spacing:.02em;text-transform:uppercase;
    padding:8px 16px;border-radius:var(--radius-sm);
    border:none!important;transition:all .2s ease;
}
.stTabs [data-baseweb="tab"]:hover{color:var(--text1);background:var(--surf2)}
.stTabs [aria-selected="true"]{
    background:var(--accentbg)!important;color:var(--accent)!important;
    box-shadow: 0 1px 3px rgba(0,0,0,.04)!important;
}
.stTabs [data-baseweb="tab-panel"]{padding-top:1.5rem}

/* ── Buttons (Seletores Robustos) ── */
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
    background: var(--surf) !important;
    border: 1px solid var(--border2) !important;
    color: var(--text2) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important;
    transition: all .2s !important;
}

div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
    background: var(--surf2) !important;
    color: var(--text1) !important;
    transform: translateY(-1px);
    border-color: var(--text3) !important;
}

/* ── Botões Primários ── */
div[data-testid="stButton"] > button[kind="primary"] {
    background: var(--accent) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 2px 4px rgba(37,99,235,0.2) !important;
}

div[data-testid="stButton"] > button[kind="primary"]:hover {
    opacity: 0.9 !important; 
    transform: translateY(-1px);
}

/* ── Inputs ── */
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea{
    background:var(--surf)!important;border:1px solid var(--border2)!important;
    border-radius:var(--radius-sm)!important;color:var(--text1)!important;
    font-size:13px!important; box-shadow: inset 0 1px 2px rgba(0,0,0,0.02)!important;
}
[data-testid="stTextInput"] input:focus,[data-testid="stTextArea"] textarea:focus{
    border-color:var(--accent)!important; outline: none!important; box-shadow: 0 0 0 2px var(--accentbg)!important;
}
[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div{
    background:var(--surf)!important;border:1px solid var(--border2)!important;
    border-radius:var(--radius-sm)!important;color:var(--text1)!important;
}

/* ── Expander ── */
[data-testid="stExpander"]{
    background:var(--surf)!important;border:1px solid var(--border)!important;
    border-radius:var(--radius)!important;overflow:hidden;
    box-shadow: var(--shadow);
}
[data-testid="stExpander"] summary{
    font-size:13px!important;font-weight:600!important;
    color:var(--text2)!important; padding: 12px 16px!important;
}
[data-testid="stExpander"] summary:hover{color:var(--text1)!important; background: var(--surf2)!important;}

/* ── Caption ── */
[data-testid="stCaptionContainer"] p{color:var(--text3)!important;font-size:11px!important}

/* ── Table card wrapper (Aba Principal) ── */
.table-card{
    background:var(--surf);border:1px solid var(--border);
    border-radius:var(--radius);overflow:hidden;margin-bottom:16px;
    box-shadow: var(--shadow);
}
.table-card-header{
    padding:16px 20px 14px;border-bottom:1px solid var(--border);
    background:var(--surf);
    display:flex;justify-content:space-between;align-items:baseline;
}
.table-card-title{font-size:14px;font-weight:700;color:var(--text1);letter-spacing:-.01em}
.table-card-meta{font-size:10px;color:var(--text3);font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;text-transform:uppercase;letter-spacing:.04em}

/* ── Monitor table ── */
.mon-table{width:100%;border-collapse:collapse;font-family:'JetBrains Mono',ui-monospace,monospace;font-size:12.5px; background:var(--surf);}
.mon-table thead{background:var(--surf2)}
.mon-table th{
    font-family:'Plus Jakarta Sans',system-ui,sans-serif;font-size:10.5px;
    font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--text3);
    padding:7px 16px;text-align:center;border-bottom:2px solid var(--border);white-space:nowrap; /* Alterado para center */
}
.mon-table th.center{text-align:center}
.mon-table td{
    padding:6px 16px;color:var(--text2);text-align:center; /* Alterado para center */
    border-bottom:1px solid var(--border);font-size:13px;
    vertical-align: middle;
}
.mon-table td.ticker{text-align:center;color:var(--text1);font-weight:600;font-size:12.5px}
.mon-table td.rate{color:var(--text2); font-weight: 500;}
.mon-table td.dur{color:var(--text3)}
.mon-table td.hi{color:var(--text1);font-weight:600}
.mon-table tbody tr:last-child td{border-bottom:1px solid var(--border)}
.mon-table tbody tr:hover td{background:var(--surf2)}
#table-di{width:437px!important}

/* ── Container do Dataframe nativo ── */
[data-testid="stDataFrame"], 
[data-testid="stDataFrame"] > div, 
[data-testid="stDataFrame"] iframe {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    overflow: hidden !important;
    box-shadow: var(--shadow) !important;
    background-color: #FFFFFF !important;
}

/* ── Deltas ── */
.dp{color:var(--green);font-weight:600;background:var(--greenbg);padding:3px 8px;border-radius:6px;font-size:11.5px;display:inline-block;}
.dn{color:var(--red);font-weight:600;background:var(--redbg);padding:3px 8px;border-radius:6px;font-size:11.5px;display:inline-block;}
.d0{color:var(--text3);font-size:11.5px;font-weight:500;}

/* ── Section labels ── */
.mon-head{font-family:'Plus Jakarta Sans',system-ui,sans-serif;font-size:15px;font-weight:700;color:var(--text1);margin:20px 0 10px;letter-spacing:-.01em}
.mon-sub{font-size:11px;color:var(--text3);margin-bottom:8px}

/* ── Badges ── */
.badge-ok{background:var(--greenbg);color:var(--green);font-size:11px;font-weight:700;padding:4px 10px;border-radius:20px;}
.badge-mt{background:var(--surf2);color:var(--text3);font-size:11px;font-weight:600;padding:4px 10px;border-radius:20px;border:1px solid var(--border)}

/* ── Column helpers ── */
.col-narrow{width:75px}.col-mid{width:105px;min-width:105px;max-width:105px}

/* ── News ── */
.news-source-badge{display:inline-block;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent);margin-bottom:12px;background:var(--accentbg);padding:4px 10px;border-radius:6px;}
.news-card{padding:14px;border:1px solid var(--border); border-radius:var(--radius); margin-bottom:12px; background:var(--surf); box-shadow:0 1px 2px rgba(0,0,0,0.02); transition: all 0.2s;}
.news-card:hover{box-shadow:var(--shadow); transform:translateY(-1px); border-color:var(--border2);}
.news-title a{color:var(--text1)!important;text-decoration:none!important;font-size:13.5px;font-weight:700;line-height:1.4;letter-spacing:-.01em;display:block;}
.news-title a:hover{color:var(--accent)!important}
.news-summary{color:var(--text2);font-size:12px;margin-top:6px;line-height:1.5}

/* ── News card full-width (nova aba noticias) ── */
.news-card-full{padding:16px 0 10px;border-bottom:none;margin-bottom:2px;}
.news-card-full .news-title a{font-size:15px;font-weight:700;}
.news-card-full .news-summary{font-size:13px;margin-top:4px;}
.news-reader{padding:28px 36px;background:var(--surf);border:1px solid var(--border);
    border-radius:var(--radius);font-size:14px;color:var(--text1);line-height:1.8;
    box-shadow:var(--shadow);margin:8px 0 16px;}
.news-reader img{max-width:100%!important;height:auto!important;border-radius:6px;margin:8px 0;}
.news-reader h1,.news-reader h2,.news-reader h3{color:var(--text1);margin-top:1.2em;}
.news-reader a{color:var(--accent);}
.news-reader p{margin-bottom:.8em;}

/* ── Auxiliary tab banner ── */
.aux-tab-banner{
    display:inline-flex;align-items:center;gap:6px;
    background:var(--surf2);border:1px solid var(--border);border-radius:var(--radius-sm);
    padding:6px 14px;font-size:10.5px;font-weight:700;color:var(--text3);
    text-transform:uppercase;letter-spacing:.05em;margin-bottom:14px;
}

/* ── Separator tab (7th tab — "Auxiliares") — não clicável ── */
.stTabs [data-baseweb="tab-list"] > [data-baseweb="tab"]:nth-child(7){
    pointer-events:none!important;cursor:default!important;
    color:var(--text3)!important;background:transparent!important;
    box-shadow:none!important;padding:8px 10px!important;
    font-size:10px!important;font-weight:600!important;letter-spacing:.06em!important;
    opacity:.75!important;border-left:1px solid var(--border)!important;
    margin-left:6px!important;user-select:none!important;
}
.stTabs [data-baseweb="tab-list"] > [data-baseweb="tab"]:nth-child(7)[aria-selected="true"]{
    background:transparent!important;color:var(--border2)!important;
    box-shadow:none!important;
}

/* ── Market status badges ── */
.mkt-open{color:var(--green);font-size:11px;font-weight:700;background:var(--greenbg);padding:3px 10px;border-radius:20px;display:inline-block;}
.mkt-closed{color:var(--text3);font-size:11px;font-weight:600;background:var(--surf2);padding:3px 10px;border-radius:20px;border:1px solid var(--border);display:inline-block;}
.mkt-ts{font-size:10px;color:var(--text3);margin-left:6px;font-family:'Plus Jakarta Sans',sans-serif;}
</style>
""", unsafe_allow_html=True)


# ================================================================
# FERIADOS ANBIMA 2024-2028
# ================================================================
FERIADOS = {
    date(2024,1,1), date(2024,2,12), date(2024,2,13), date(2024,3,29),
    date(2024,4,21), date(2024,5,1),  date(2024,5,30), date(2024,9,7),
    date(2024,10,12), date(2024,11,2), date(2024,11,15), date(2024,11,20), date(2024,12,25),
    date(2025,1,1), date(2025,3,3), date(2025,3,4), date(2025,4,18),
    date(2025,4,21), date(2025,5,1), date(2025,6,19), date(2025,9,7),
    date(2025,10,12), date(2025,11,2), date(2025,11,15), date(2025,11,20), date(2025,12,25),
    date(2026,1,1), date(2026,2,16), date(2026,2,17), date(2026,4,3),
    date(2026,4,21), date(2026,5,1), date(2026,6,4), date(2026,9,7),
    date(2026,10,12), date(2026,11,2), date(2026,11,15), date(2026,11,20), date(2026,12,25),
    date(2027,1,1), date(2027,2,8), date(2027,2,9), date(2027,3,26),
    date(2027,4,21), date(2027,5,1), date(2027,5,27), date(2027,9,7),
    date(2027,10,12), date(2027,11,2), date(2027,11,15), date(2027,11,20), date(2027,12,25),
    date(2028,1,1), date(2028,2,28), date(2028,2,29), date(2028,4,14),
    date(2028,4,21), date(2028,5,1), date(2028,6,15), date(2028,9,7),
    date(2028,10,12), date(2028,11,2), date(2028,11,15), date(2028,11,20), date(2028,12,25),
}

_HOLIDAYS_NP = np.array(sorted(FERIADOS), dtype="datetime64[D]")
_BUSDAYCAL   = np.busdaycalendar(holidays=_HOLIDAYS_NP)


# ================================================================
# HELPERS
# ================================================================
def is_bday(d):
    return d.weekday() < 5 and d not in FERIADOS

def last_bday(from_date=None):
    d = (from_date or date.today()) - timedelta(days=1)
    while not is_bday(d):
        d -= timedelta(days=1)
    return d

def count_du(start, end):
    if end <= start:
        return 0
    return int(np.busday_count(start, end, busdaycal=_BUSDAYCAL))

def hora_brt():
    return (datetime.utcnow() - timedelta(hours=3)).hour + \
           (datetime.utcnow() - timedelta(hours=3)).minute / 60

def _us_in_dst(d: date) -> bool:
    """Retorna True se os EUA estão em horário de verão (DST) na data d."""
    y = d.year
    mar1 = date(y, 3, 1)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7) + timedelta(7)   # 2º domingo de março
    nov1 = date(y, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)                    # 1º domingo de novembro
    return dst_start <= d < dst_end

def _market_status(group: str):
    """Retorna (aberto: bool, label: str, timestamp_brt: str).
    Usa time.time() → UTC epoch para máxima confiabilidade multiplataforma.
    Brasil não tem horário de verão desde 2019: BRT = UTC-3 fixo.
    """
    # Fonte de tempo: epoch UTC via kernel clock (independente de tzdata local)
    now_utc  = datetime.utcfromtimestamp(_time.time())
    now_brt  = now_utc - timedelta(hours=3)
    today    = now_brt.date()
    h        = now_brt.hour + now_brt.minute / 60   # horas decimais em BRT
    wd       = today.weekday()                       # 0=seg … 6=dom
    ts       = now_brt.strftime("%H:%M BRT")         # para exibição

    if wd >= 5:                                      # sáb ou dom
        return False, f"Fechado · final de semana", ts

    if group in ("BR", "FUTURES"):
        if today in FERIADOS:
            return False, "Fechado · feriado B3", ts
        # B3: mini-contratos 9h-18h; ações 10h-17h55
        open_h  = 9.0  if group == "FUTURES" else 10.0
        close_h = 18.0 if group == "FUTURES" else (17.0 + 55.0/60.0)
        if open_h <= h < close_h:
            return True,  "Aberto · B3", ts
        return False, "Fechado · B3", ts

    elif group == "INT":
        dst     = _us_in_dst(today)
        offset  = 1 if dst else 2          # BRT - ET = offset h
        nyse_o  = 9.5  + offset            # 9h30 ET em BRT
        nyse_c  = 16.0 + offset            # 16h00 ET em BRT
        tz_lbl  = "EDT" if dst else "EST"
        if nyse_o <= h < nyse_c:
            return True,  f"Aberto · NYSE ({tz_lbl})", ts
        return False, f"Fechado · NYSE ({tz_lbl})", ts

    return False, "—", ts

def anbima_url_and_date():
    lbd = last_bday()
    return f"https://www.anbima.com.br/informacoes/merc-sec/arqs/ms{lbd.strftime('%y%m%d')}.txt", lbd

def january_di_tickers():
    base = date.today().year
    return [f"DI1F{str(base + i + 1)[-2:]}" for i in range(10)]

def string_or_serial_to_date(val):
    if not val:
        return None
    val_str = str(val).strip()
    
    if "/" in val_str:
        try:
            parts = val_str.split("/")
            day = int(parts[0])
            month = int(parts[1])
            year = int(parts[2])
            if year < 100:
                year += 2000
            return date(year, month, day)
        except Exception:
            pass

    try:
        n = int(float(val_str.replace(",", ".")))
        if n < 40000:
            return None
        return date(1899, 12, 30) + timedelta(days=n)
    except Exception:
        return None


# ---- Formatação ------------------------------------------------
def fr(v, dec=2):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "—"
        return f"{v:,.{dec}f}" # Adicionado apenas a vírgula antes do ponto
    except Exception:
        return "—"

def fd(v):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '<span class="d0">—</span>'
        vi   = int(round(v))
        sign = "+" if vi > 0 else ""
        cls  = "dp" if vi > 0 else ("dn" if vi < 0 else "d0")
        return f'<span class="{cls}">{sign}{vi}</span>'
    except Exception:
        return '<span class="d0">—</span>'


def fd2(v, dec: int = 2, suffix: str = ""):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return '<span class="d0">—</span>'
        cls  = "dp" if v > 0 else ("dn" if v < 0 else "d0")
        sign = "+" if v >= 0 else ""
        txt  = f"{sign}{v:,.{dec}f}{suffix}"
        return f'<span class="{cls}">{txt}</span>'
    except Exception:
        return '<span class="d0">—</span>'


# ================================================================
# MACAULAY DURATION (NTN-B)
# ================================================================
def calc_duration(vencimento, tx_ind, today_date=None):
    if tx_ind is None or (isinstance(tx_ind, float) and np.isnan(tx_ind)):
        return None
    today = today_date or date.today()
    venc  = vencimento.date() if hasattr(vencimento, "date") else vencimento
    if venc <= today:
        return None

    y = tx_ind / 100                 
    c = (1.06 ** 0.5) - 1           

    coupon_dates = []
    for yr in range(today.year, venc.year + 2):
        for mo in (2, 8):
            try:
                d = date(yr, mo, 15)
            except ValueError:
                continue
            if today < d <= venc:
                coupon_dates.append(d)
    if venc not in coupon_dates:
        coupon_dates.append(venc)
    coupon_dates = sorted(set(coupon_dates))

    if not coupon_dates:
        return None

    pv_t = 0.0
    pv   = 0.0
    for cd in coupon_dates:
        du   = int(np.busday_count(today, cd, busdaycal=_BUSDAYCAL))
        t    = du / 252
        cf   = (1 + c) if cd == venc else c   
        pv_i = cf / (1 + y) ** t
        pv   += pv_i
        pv_t += t * pv_i

    return (pv_t / pv) if pv > 0 else None


# ================================================================
# FETCH B3 DI1
# ================================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_b3_di():
    url = "https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        out = {}
        for s in data.get("Scty", []):
            ticker = s.get("symb", "")
            if not ticker.startswith("DI1F"):
                continue
            q = s.get("SctyQtn", {})
            a = s.get("asset", {}).get("AsstSummry", {})
            out[ticker] = {
                "ticker":     ticker,
                "ajuste":     q.get("prvsDayAdjstmntPric"),
                "ultimo":     q.get("curPrc"),
                "abertura":   q.get("opngPric"),
                "min":        q.get("minPric"),
                "max":        q.get("maxPric"),
                "compra":     s.get("buyOffer",  {}).get("price"),
                "venda":      s.get("sellOffer", {}).get("price"),
                "vencimento": a.get("mtrtyCode"),
                "contratos":  a.get("opnCtrcts"),
                "negocios":   a.get("tradQty"),
            }
        ts = data.get("Msg", {}).get("dtTm", "")
        return {"tickers": out, "timestamp": ts}, None
    except Exception as e:
        return None, str(e)


# ================================================================
# FETCH ANBIMA NTN-B
# ================================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_anbima():
    url, ref = anbima_url_and_date()
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        text  = r.content.decode("latin-1")
        lines = text.strip().splitlines()
        hi    = next((i for i, l in enumerate(lines) if l.strip().startswith("Titulo@")), None)
        if hi is None:
            return None, "Header não encontrado no arquivo ANBIMA", ref

        raw = "\n".join(lines[hi:])
        df  = pd.read_csv(StringIO(raw), sep="@", dtype=str, on_bad_lines="skip")
        df.columns = [c.strip() for c in df.columns]

        titulo_col = next((c for c in df.columns if c.lower().startswith("titulo")), None)
        if titulo_col is None:
            return None, f"Coluna 'Titulo' não encontrada. Colunas: {list(df.columns)}", ref
        df = df[df[titulo_col].str.strip() == "NTN-B"].copy()

        venc_col = next(
            (c for c in df.columns if "vencimento" in c.lower() or c.lower() in ("venc","dt venc","dt.venc")),
            None,
        )
        if venc_col is None:
            return None, f"Coluna de vencimento não encontrada. Colunas: {list(df.columns)}", ref

        df["vencimento"] = pd.to_datetime(df[venc_col].str.strip(), format="%Y%m%d", errors="coerce")
        df = df[df["vencimento"] >= pd.Timestamp(date.today())].copy()

        skip_cols = {titulo_col, venc_col, "Criterio"}
        for col in df.columns:
            if col in skip_cols or col == "vencimento":
                continue
            df[col] = pd.to_numeric(
                df[col].str.strip()
                       .str.replace(".", "", regex=False)
                       .str.replace(",", ".", regex=False)
                       .replace({"--": "", "N/D": "", "n/d": ""}),
                errors="coerce",
            )

        tx_col       = next((c for c in df.columns if "indicat" in c.lower()), None)
        df["tx_ind"] = df[tx_col] if tx_col else np.nan

        df["duration"] = df.apply(
            lambda row: calc_duration(row["vencimento"], row["tx_ind"]),
            axis=1,
        )

        df["label"] = df["vencimento"].dt.strftime("B%y")   
        df = df.sort_values("vencimento").reset_index(drop=True)
        return df, None, ref

    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code} — {url}", ref
    except Exception as e:
        return None, str(e), ref


# ================================================================
# CALLS — Persistência e Parser
# ================================================================
CALLS_FILE = "calls_ntnb.json"

def load_calls():
    if os.path.exists(CALLS_FILE):
        try:
            with open(CALLS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"manha": {}, "tarde": {}, "fechamento": {}}

def save_calls(calls):
    with open(CALLS_FILE, "w") as f:
        json.dump(calls, f, indent=2)

def _to_float(s):
    if s is None:
        return None
    s = str(s).strip().replace(" ", "").replace("%", "")
    if not s or s in ("-", "--", "N/D"):
        return None
    if "," in s and "." in s:
        if s.rindex(",") > s.rindex("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None

def parse_call_range(text, anbima_df):
    if not text or not text.strip():
        return None

    sessions = {"manha": {}, "tarde": {}, "fechamento": {}}
    
    venc_lookup = {}
    if anbima_df is not None:
        for _, row in anbima_df.iterrows():
            vd = row["vencimento"].date() if hasattr(row["vencimento"], "date") else row["vencimento"]
            venc_lookup[vd] = row["label"]

    for line in text.strip().splitlines():
        cols = line.split("\t")
        if len(cols) < 3:
            continue

        venc_date = None
        compra_m = venda_m = compra_t = venda_t = compra_f = venda_f = None

        if "/" in cols[1] or (cols[1].replace(",", "").replace(".", "").isdigit() and len(cols[1]) >= 4):
            venc_date = string_or_serial_to_date(cols[1])
            if venc_date and len(cols) >= 12:
                compra_m = _to_float(cols[4])
                venda_m  = _to_float(cols[5])
                compra_t = _to_float(cols[7])
                venda_t  = _to_float(cols[8])
                compra_f = _to_float(cols[10])
                venda_f  = _to_float(cols[11])

        elif len(cols) > 2 and ("/" in cols[2] or cols[2].replace(",", "").replace(".", "").isdigit()):
            venc_date = string_or_serial_to_date(cols[2])
            if venc_date and len(cols) >= 13:
                compra_m = _to_float(cols[5])
                venda_m  = _to_float(cols[6])
                compra_t = _to_float(cols[8])
                venda_t  = _to_float(cols[9])
                compra_f = _to_float(cols[11])
                venda_f  = _to_float(cols[12])

        if venc_date is None:
            continue

        label = venc_lookup.get(venc_date)
        if label is None:
            for delta in range(-3, 4):
                label = venc_lookup.get(venc_date + timedelta(days=delta))
                if label:
                    break
        if label is None:
            continue

        for sess, cp, vd in [
            ("manha",      compra_m, venda_m),
            ("tarde",      compra_t, venda_t),
            ("fechamento", compra_f, venda_f),
        ]:
            vals = [x for x in [cp, vd] if x is not None]
            if vals:
                sessions[sess][label] = sum(vals) / len(vals)

    return sessions if any(sessions.values()) else None


# ================================================================
# RENDER HELPERS
# ================================================================
def render_table(headers, rows_html, table_id=None, title=None, meta=None):
    id_attr = f' id="{table_id}"' if table_id else ""
    ths     = "".join(f'<th class="{cls}">{h}</th>' for h, cls in headers)
    hdr     = ""
    if title:
        m   = f'<span class="table-card-meta">{meta}</span>' if meta else ""
        hdr = f'<div class="table-card-header"><span class="table-card-title">{title}</span>{m}</div>'
    st.markdown(
        f'<div class="table-card">{hdr}'
        f'<table class="mon-table"{id_attr}><thead><tr>{ths}</tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>',
        unsafe_allow_html=True,
    )

def get_centralized_config(df):
    return {col: st.column_config.Column(alignment="center") for col in df.columns}


# ================================================================
# FRAGMENTO DE AUTO-REFRESH DE DADOS (10 MINUTOS)
# ================================================================
@st.fragment(run_every=600)
def render_conteudo_dinamico(current_calls):
    """Encapsula todas as abas e coletas que mudam ao longo do dia para auto-refresh silencioso."""
    
    di_data, di_err = fetch_b3_di()
    anbima_df, anbima_err, ref_dt = fetch_anbima()

    if di_err:
        st.error(f"**B3 DI:** {di_err}")
    if anbima_err:
        st.error(f"**ANBIMA:** {anbima_err}")

    # Bloqueio de ajuste pós 16h BRT
    if hora_brt() >= 16.0 and di_data:
        if "ajuste_locked" not in st.session_state:
            st.session_state["ajuste_locked"] = {
                t: info.get("ajuste") for t, info in di_data["tickers"].items()
            }
    ajuste_locked = st.session_state.get("ajuste_locked", {})

    _now_brt = datetime.utcfromtimestamp(_time.time()) - timedelta(hours=3)
    st.caption(
        f"🔄 Último refresh: {_now_brt.strftime('%H:%M:%S')} BRT  ·  "
        f"DI/ANBIMA/Ativos cache 5 min  ·  Notícias cache 10 min  ·  próx. auto-refresh em ~10 min"
    )

    tabs = st.tabs([
        "Principal",
        "Calls NTN-B",
        "Notícias",
        "Newsletters",
        "Ativos",
        "SRE CVM",
        "Auxiliares ————›",          # separador visual — não abrível
        "📊 Cotação DI",
        "📊 Curva DI",
        "📊 NTN-B ANBIMA",
    ])
    with tabs[0]: render_principal(di_data, anbima_df, current_calls, ajuste_locked)
    with tabs[1]: render_calls(anbima_df, current_calls, save_calls)
    with tabs[2]: render_noticias()
    with tabs[3]: render_newsletters()
    with tabs[4]: render_ativos()
    with tabs[5]: render_cvm()
    # tabs[6] = separador visual — conteúdo propositalmente vazio
    with tabs[7]: render_cotacao_di(di_data)
    with tabs[8]: render_curva_di(di_data)
    with tabs[9]: render_ntnb_anbima(anbima_df, ref_dt)


# ================================================================
# ABAS DE CONTEÚDO
# ================================================================

# ---- Aba Principal -------------------------------------------
def render_principal(di, anbima, calls, ajuste_locked):

    frozen = hora_brt() >= 16.0
    ts_txt = di["timestamp"] if di else "—"
    status = " · ajuste bloqueado" if frozen else " · lag ~15 min"
    n = len(anbima) if anbima is not None else 0

    col_di, _, col_ntnb, col_btn = st.columns([1, 0.04, 1.4, 0.4])

    with col_btn:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("Limpar Calls", key="cl_principal_aligned", use_container_width=True):
            for k in st.session_state["calls"]:
                st.session_state["calls"][k] = {}
            save_calls(st.session_state["calls"])
            if "ajuste_locked" in st.session_state:
                del st.session_state["ajuste_locked"]
            st.rerun()
        if st.button("Atualizar DI", key="upd_di_principal", use_container_width=True):
            # Limpa apenas o cache de fetch_b3_di (DI Futuro)
            try:
                fetch_b3_di.clear()
            except Exception:
                # Fallback: limpa todo o cache se .clear() não estiver disponível
                st.cache_data.clear()
            if "ajuste_locked" in st.session_state:
                del st.session_state["ajuste_locked"]
            st.rerun(scope="fragment")

    with col_di:
        tickers = january_di_tickers()
        rows = ""
        for t in tickers:
            q      = (di or {}).get("tickers", {}).get(t, {})
            ajuste = ajuste_locked.get(t) if (frozen and ajuste_locked) else q.get("ajuste")
            ultimo = q.get("ultimo")
            delta  = (ultimo - ajuste) * 100 if (ultimo is not None and ajuste is not None) else float("nan")
            rows += (
                f'<tr>'
                f'<td class="ticker col-mid">{t}</td>'
                f'<td class="rate">{fr(ajuste)}</td>'
                f'<td class="hi">{fr(ultimo)}</td>'
                f'<td>{fd(delta)}</td>'
                f'</tr>'
            )
        render_table(
            [("Vértice","col-mid left"),("Ajuste D-1","col-mid"),
             ("Último","col-mid"),("Δ bps","col-mid")],
            rows, table_id="table-di",
            title="DI Futuro", meta=f"B3 · {ts_txt}{status}",
        )

    with col_ntnb:
        c_m = calls.get("manha", {})
        c_t = calls.get("tarde", {})
        rows = ""
        if anbima is not None:
            for _, ab in anbima.iterrows():
                lbl   = ab["label"]
                mtm   = ab["tx_ind"]   if pd.notna(ab.get("tx_ind"))   else None
                dur   = ab["duration"] if pd.notna(ab.get("duration")) else None
                manha = c_m.get(lbl)
                tarde = c_t.get(lbl)
                dm    = (manha - mtm)   * 100 if (manha is not None and mtm is not None)   else float("nan")
                dt    = (tarde - manha) * 100 if (tarde is not None and manha is not None) else float("nan")
                ddia  = (tarde - mtm)   * 100 if (tarde is not None and mtm is not None)   else dm
                rows += (
                    f'<tr>'
                    f'<td class="ticker">{lbl}</td>'
                    f'<td class="dur">{fr(dur)}</td>'
                    f'<td class="rate">{fr(mtm)}</td>'
                    f'<td class="hi">{fr(manha)}</td>'
                    f'<td class="hi">{fr(tarde)}</td>'
                    f'<td>{fd(dm)}</td>'
                    f'<td>{fd(dt)}</td>'
                    f'<td>{fd(ddia)}</td>'
                    f'</tr>'
                )
        render_table(
            [("Vértice","left"),("Duration",""),("MTM D-1",""),
             ("Call M",""),("Call T",""),("Δ M",""),("Δ T",""),("Δ Dia","")],
            rows,
            title="NTN-B",
            meta=f"ANBIMA · {n} títulos vigentes",
        )

# ---- Cotação DI completa ------------------------------------
def render_cotacao_di(di):
    st.markdown('<div class="aux-tab-banner">📊 Cotação DI — Referência auxiliar · dados completos da API B3</div>', unsafe_allow_html=True)
    if di is None:
        st.warning("Dados B3 indisponíveis.")
        return
    records = sorted(di["tickers"].values(), key=lambda x: x.get("vencimento") or "")
    df = pd.DataFrame(records)
    rename = {
        "ticker":"Vértice","vencimento":"Vencimento","ajuste":"Ajuste D-1",
        "compra":"Compra","venda":"Venda","ultimo":"Último",
        "min":"Min","max":"Max","contratos":"Contratos","negocios":"Negócios",
    }
    df = df[[c for c in rename if c in df.columns]].rename(columns=rename)
    fmt = {c: (lambda x: fr(x)) for c in ["Ajuste D-1","Compra","Venda","Último","Min","Max"]}
    fmt["Contratos"] = lambda x: f"{int(x):,}" if pd.notna(x) else "—"
    fmt["Negócios"]  = lambda x: f"{int(x):,}" if pd.notna(x) else "—"
    
    st.dataframe(
        df.style.format(fmt, na_rep="—"), 
        use_container_width=True, 
        hide_index=True,
        column_config=get_centralized_config(df)
    )


# ---- Curva DI ----------------------------------------------
def render_curva_di(di):
    st.markdown('<div class="aux-tab-banner">📊 Curva DI — Referência auxiliar · DU e FRA calculados</div>', unsafe_allow_html=True)
    if di is None:
        st.warning("Dados B3 indisponíveis.")
        return
    today   = date.today()
    records = sorted(
        [v for v in di["tickers"].values() if v.get("vencimento") and v.get("ultimo")],
        key=lambda x: x["vencimento"],
    )
    rows = []
    for i, r in enumerate(records):
        try:
            venc = date.fromisoformat(r["vencimento"])
        except ValueError:
            continue
        du  = count_du(today, venc)
        fra = dif = None
        if i > 0:
            try:
                pv  = date.fromisoformat(records[i-1]["vencimento"])
                dup = count_du(today, pv)
                dif = du - dup
                if dif > 0:
                    rn = r["ultimo"] / 100
                    rp = records[i-1]["ultimo"] / 100
                    fra = ((1+rn)**(du/252) / (1+rp)**(dup/252))**(252/dif) - 1
                    fra *= 100
            except Exception:
                pass
        rows.append({
            "Vértice":    r["ticker"],
            "Vencimento": r["vencimento"],
            "DU":         du,
            "Δ DU":       dif,
            "Taxa (%)":   r["ultimo"],
            "FRA (%)":    fra,
        })
    df = pd.DataFrame(rows)
    fmt = {
        "Taxa (%)": lambda x: fr(x),
        "FRA (%)":  lambda x: fr(x, 4),
        "Δ DU":     lambda x: str(int(x)) if pd.notna(x) else "—",
    }
    st.dataframe(
        df.style.format(fmt, na_rep="—"), 
        use_container_width=True, 
        hide_index=True,
        column_config=get_centralized_config(df)
    )


# ---- NTN-B ANBIMA completo ----------------------------------
def render_ntnb_anbima(anbima, ref):
    st.markdown('<div class="aux-tab-banner">📊 NTN-B ANBIMA — Referência auxiliar · arquivo diário ANBIMA completo</div>', unsafe_allow_html=True)
    if anbima is None:
        st.warning("Dados ANBIMA indisponíveis.")
        return
    st.caption(f"Referência ANBIMA: {ref}  ·  {len(anbima)} NTN-Bs vigentes")
    show   = ["label","vencimento","duration"]
    rename = {"label":"Vértice","vencimento":"Vencimento","duration":"Duration"}
    for src, dst in [
        ("Tx. Compra","Tx Compra"), ("Tx. Venda","Tx Venda"),
        ("tx_ind","Tx Indicativa"), ("PU","PU"), ("Desvio padrao","Desvio Padrão"),
    ]:
        if src in anbima.columns:
            show.append(src)
            rename[src] = dst
    df = anbima[[c for c in show if c in anbima.columns]].copy().rename(columns=rename)
    df["Vencimento"] = pd.to_datetime(df["Vencimento"]).dt.strftime("%Y-%m-%d")
    fmt = {
        "Duration": lambda x: fr(x),
    }
    for c in ["Tx Compra","Tx Venda","Tx Indicativa"]:
        if c in df.columns:
            fmt[c] = lambda x: fr(x)
    if "PU" in df.columns:
        fmt["PU"] = lambda x: f"{x:,.2f}" if pd.notna(x) else "—"
    st.dataframe(
        df.style.format(fmt, na_rep="—"), 
        use_container_width=True, 
        hide_index=True,
        column_config=get_centralized_config(df)
    )


# ---- Configuração de Upload dos Calls NTN-B -----------------
def render_calls(anbima, calls, save_fn):
    labels = {"manha":"Manhã","tarde":"Tarde","fechamento":"Fechamento"}
    sc1, sc2, sc3 = st.columns(3)
    for col, key in zip([sc1, sc2, sc3], ["manha","tarde","fechamento"]):
        with col:
            n   = len(calls.get(key, {}))
            tag = "badge-ok" if n else "badge-mt"
            txt = f"✓ {n} títulos" if n else "aguardando"
            st.markdown(f'**{labels[key]}** &nbsp; <span class="{tag}">{txt}</span>',
                        unsafe_allow_html=True)

    st.divider()
    st.markdown(
        "Cole o range da planilha de calls abaixo e clique **Aplicar**. "
        "A estrutura lê automaticamente as datas brasileiras coladas direto do seu Excel."
    )

    pasted = st.text_area(
        "Range do Excel",
        key="ta_calls",
        height=220,
        label_visibility="collapsed",
        placeholder="Cole o range do Excel aqui (Ctrl+V)..."
    )

    b1, b2 = st.columns([2, 1])
    with b1:
        aplicar = st.button("Aplicar Calls", key="ap_calls", use_container_width=True, type="primary")
    with b2:
        limpar  = st.button("Limpar tudo",  key="cl_calls", use_container_width=True)

    if aplicar:
        if not pasted.strip():
            st.warning("Nenhum texto colado.")
        else:
            parsed = parse_call_range(pasted, anbima)
            if parsed is None:
                st.error("Não foi possível interpretar o range. Verifique a estrutura de colunas.")
            else:
                changed = []
                for sess in ("manha","tarde","fechamento"):
                    if parsed[sess]:
                        calls[sess] = parsed[sess]
                        changed.append(f"{labels[sess]}: {len(parsed[sess])} títulos")
                if changed:
                    save_fn(calls)
                    st.success("Aplicado com sucesso! " + " · ".join(changed))
                    st.rerun(scope="fragment")

    if limpar:
        for k in ("manha","tarde","fechamento"):
            calls[k] = {}
        save_fn(calls)
        st.rerun(scope="fragment")


# ================================================================
# CONTROLADOR PRINCIPAL (MAIN)
# ================================================================
def main():
    if "calls" not in st.session_state:
        st.session_state["calls"] = load_calls()
        
    current_calls = st.session_state["calls"]

    # ── Header Estático ───────────────────────────────────────
    st.markdown("<div style='margin-top:0rem'></div>", unsafe_allow_html=True)

    # Nova proporção estrita solicitada pelo usuário
    h1, h2, h3 = st.columns([14.8, 1.5, 0.8])
    with h1:
        st.markdown(
            '<h1 style="font-family:\'Plus Jakarta Sans\',sans-serif;font-weight:800;'
            'font-size:1.8rem;margin:0;color:var(--text1);letter-spacing:-1px;">'
            'Monitor <span style="color:var(--accent)">Macro</span></h1>',
            unsafe_allow_html=True,
        )
    with h2:
        st.markdown("<div style='height:7px'></div>", unsafe_allow_html=True)
        if st.button("🔄 Atualizar", use_container_width=False):
            st.cache_data.clear()
            if "ajuste_locked" in st.session_state:
                del st.session_state["ajuste_locked"]
            st.rerun()
    with h3:
        st.markdown("<div style='height:23px'></div>", unsafe_allow_html=True)
        st.caption(datetime.now().strftime("%H:%M:%S"))

    st.divider()

    # ── Invocação do Fragmento Dinâmico Automático ────────────
    render_conteudo_dinamico(current_calls)


# ================================================================
# ██████╗  Módulos adicionais — imports
# ================================================================
import re
import zipfile
import io
import time as _time
import streamlit.components.v1 as _components

try:
    import feedparser as _feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import yfinance as _yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = True

try:
    from bs4 import BeautifulSoup as _BS
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


# ================================================================
# ── NOTÍCIAS  ─────────────────────────────────────────────────
# ================================================================
NEWS_FILE = "news_sources.json"

_DEFAULT_NEWS = [
    {"name": "Sherwood News",
     "rss_candidates": [
         "https://sherwood.news/feed/",
         "https://sherwood.news/rss/",
         "https://sherwood.news/rss.xml",
         "https://sherwood.news/feed.xml",
     ],
     "url": "https://sherwood.news", "allow_gn": True, "enabled": True},
    {"name": "WSJ",
     "rss_candidates": [
         "https://feeds.a.wallstreetjournal.com/rss/news_business.xml",
         "https://feeds.a.wallstreetjournal.com/rss/wsj_latest.xml",
         "https://feeds.a.wallstreetjournal.com/rss/markets_main.xml",
         "https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines",
         "https://www.wsj.com/news/rss-news-and-feeds",
     ],
     "url": "https://wsj.com", "allow_gn": True, "enabled": True},
    {"name": "Valor Econômico",
     "rss_candidates": [
         "https://valor.globo.com/rss/",
         "https://valor.globo.com/rss/home/",
         "https://valor.globo.com/financas/feed",
         "https://valor.globo.com/empresas/feed",
         "https://valor.globo.com/mercados/feed",
         "https://rss.globo.com/valor/",
     ],
     "url": "https://valor.globo.com", "site_strategy": "reader",
     "allow_gn": True, "enabled": True},
    {"name": "Neofeed",
     "rss_candidates": [
         "https://neofeed.com.br/feed/",
         "https://neofeed.com.br/rss/",
         "https://neofeed.com.br/rss.xml",
     ],
     "url": "https://neofeed.com.br", "allow_gn": True, "enabled": True},
    {"name": "Metro Quadrado",
     "rss_candidates": [
         "https://www.metroquadrado.com.br/noticias/feed/",
         "https://www.metroquadrado.com.br/feed/",
     ],
     "html_scrape_url": "https://metroquadrado.com/",
     "html_scrape_url_fallbacks": [
         "https://www.metroquadrado.com.br/",
         "https://www.metroquadrado.com.br/noticias/",
     ],
     "html_exclude_subtitle": ["Um conteudo", "Um conteúdo"],
     "url": "https://metroquadrado.com", "allow_gn": False, "enabled": True},
    {"name": "Brazil Journal",
     "rss_candidates": [
         "https://braziljournal.com/feed/",
         "https://braziljournal.com/rss/",
     ],
     "url": "https://braziljournal.com", "allow_gn": True, "enabled": True},
    {"name": "InvestNews",
     "rss_candidates": [
         "https://investnews.com.br/feed/",
         "https://investnews.com.br/rss/",
     ],
     "url": "https://investnews.com.br", "allow_gn": True, "enabled": True},
    {"name": "Globo Esporte",
     "rss_candidates": [
         "https://ge.globo.com/rss/ge/",
         "https://ge.globo.com/rss/",
         "https://pox.globo.com/rss/ge",
     ],
     "url": "https://ge.globo.com", "site_strategy": "reader",
     "allow_gn": True, "enabled": True},
    {"name": "ESPN",
     "rss_candidates": [
         "https://www.espn.com/espn/rss/news",
         "https://www.espn.com/espn/rss/nfl/news",
         "https://www.espn.com/espn/rss/nba/news",
     ],
     "url": "https://www.espn.com", "site_strategy": "reader",
     "allow_gn": True, "enabled": True},
]

def _load_news_sources():
    """Carrega fontes do disco e mescla com `_DEFAULT_NEWS` qualquer fonte
    nova que ainda não exista no JSON local (por nome). Isso garante que
    novas fontes adicionadas em atualizações do código apareçam mesmo
    se o JSON do usuário já existir.
    """
    existing = []
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, encoding="utf-8") as f:
                existing = json.load(f) or []
        except Exception:
            existing = []

    if not existing:
        s = [d.copy() for d in _DEFAULT_NEWS]
        _save_news_sources(s)
        return s

    # Merge: adiciona qualquer default ausente (por nome) ao final
    existing_names = {(s.get("name") or "").lower() for s in existing}
    added = False
    for d in _DEFAULT_NEWS:
        if (d.get("name") or "").lower() not in existing_names:
            existing.append(d.copy())
            added = True

    # Para fontes que já existem mas faltam campos importantes (ex: site_strategy
    # adicionado em release nova), atualiza esses campos sem mexer no enabled
    by_name = {(s.get("name") or "").lower(): s for s in existing}
    for d in _DEFAULT_NEWS:
        nm = (d.get("name") or "").lower()
        if nm in by_name:
            cur = by_name[nm]
            for k in ("site_strategy", "rss_candidates", "url"):
                if k in d and not cur.get(k):
                    cur[k] = d[k]
                    added = True

    if added:
        _save_news_sources(existing)
    return existing

def _save_news_sources(sources):
    with open(NEWS_FILE, "w", encoding="utf-8") as f:
        json.dump(sources, f, indent=2, ensure_ascii=False)

_BROWSER_HEADERS = {
    "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
}

@st.cache_data(ttl=600, show_spinner=False)
def fetch_news_feed(rss_candidates: list, site_url: str, allow_gn: bool = False,
                    max_items: int = 10):
    if not HAS_FEEDPARSER:
        return [], "feedparser não instalado"

    def _parse(url):
        try:
            f = _feedparser.parse(url)
            out = []
            for e in f.entries[:max_items]:
                title   = e.get("title", "").strip()
                raw_sum = e.get("summary", e.get("description", ""))
                summary = _BS(raw_sum, "html.parser").get_text() if HAS_BS4 else re.sub(r"<[^>]+>", "", raw_sum)
                summary = " ".join(summary.split())[:220]
                link    = e.get("link", "")
                if title:
                    out.append({"title": title, "summary": summary, "link": link})
            return out
        except Exception:
            return []

    if isinstance(rss_candidates, str):
        rss_candidates = [rss_candidates]
    for url in rss_candidates:
        items = _parse(url)
        if items:
            return items, None

    if allow_gn:
        try:
            from urllib.parse import urlparse
            domain = urlparse(site_url).netloc
            gn = f"https://news.google.com/rss/search?q=site:{domain}&hl=en-US&gl=US&ceid=US:en"
            items = _parse(gn)
            if items:
                return items, "via Google News"
        except Exception:
            pass

    return [], "RSS indisponível para esta fonte"

def _scrape_html_news(page_url: str, max_items: int = 10, fallback_urls: list = None, exclude_subtitle: list = None):
    if not HAS_BS4:
        return [], "beautifulsoup4 não instalado"
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    urls_to_try = [page_url] + (fallback_urls or [])
    last_err = "Todas as URLs falharam"
    r = None
    for url in urls_to_try:
        try:
            r = requests.get(url, timeout=12, headers=_BROWSER_HEADERS, verify=False)
            if r.status_code == 200:
                page_url = url
                break
            last_err = f"HTTP {r.status_code} ({url})"
        except Exception as e:
            last_err = str(e)
            r = None
    if r is None or r.status_code != 200:
        return [], last_err
    try:
        r.raise_for_status()
        soup = _BS(r.text, "html.parser") if HAS_BS4 else None
        if not soup:
            return [], "bs4 indisponível"

        from urllib.parse import urlparse as _up
        base = _up(page_url)
        site_root = f"{base.scheme}://{base.netloc}"

        items = []
        seen_titles = set()

        for art in soup.find_all("article")[:max_items * 2]:
            a = art.find("a", href=True)
            if not a:
                continue
            title = (art.find(["h1","h2","h3","h4"]) or a).get_text(strip=True)
            if len(title) < 15 or title.lower() in seen_titles:
                continue
            href = a["href"]
            if href.startswith("/"):
                href = site_root + href
            summary_tag = art.find("p")
            summary = summary_tag.get_text(strip=True)[:200] if summary_tag else ""
            if exclude_subtitle and any(ex.lower() in summary.lower() for ex in exclude_subtitle):
                continue
            seen_titles.add(title.lower())
            items.append({"title": title, "summary": summary, "link": href})
            if len(items) >= max_items:
                break

        if not items:
            for htag in soup.find_all(["h2","h3"])[:max_items * 3]:
                a = htag.find("a", href=True) or (
                    htag.find_next_sibling("a") if htag.find_next_sibling("a") else None)
                if not a:
                    parent_a = htag.find_parent("a", href=True)
                    a = parent_a
                if not a:
                    continue
                title = htag.get_text(strip=True)
                if len(title) < 15 or title.lower() in seen_titles:
                    continue
                href = a["href"]
                if href.startswith("/"):
                    href = site_root + href
                if not href.startswith("http"):
                    continue
                parsed_link = _up(href)
                if parsed_link.netloc and parsed_link.netloc != base.netloc:
                    continue
                seen_titles.add(title.lower())
                items.append({"title": title, "summary": "", "link": href})
                if len(items) >= max_items:
                    break

        return items, (None if items else "Nenhum artigo encontrado na página")
    except requests.HTTPError as e:
        return [], f"HTTP {e.response.status_code}"
    except Exception as e:
        return [], str(e)


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_site_html(url: str):
    """Busca o HTML de um site server-side e o reescreve para renderização inline.
    Contorna X-Frame-Options porque o conteúdo é servido pelo próprio Streamlit
    (não há requisição cross-origin de iframe).

    Reescritas:
    - <base href="..."> para resolver URLs relativas
    - <a target="_blank"> para links abrirem em nova aba (escapam o iframe interno)
    - Remove scripts frame-buster (top.location, self != top, etc.)
    """
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        r = requests.get(url, timeout=20, headers=_BROWSER_HEADERS,
                         allow_redirects=True, verify=False)
        r.raise_for_status()
        if not HAS_BS4:
            return r.text, None

        soup = _BS(r.text, "html.parser")
        parsed = urlparse(r.url)            # URL após redirects
        base_url = f"{parsed.scheme}://{parsed.netloc}/"

        # <base> tag para URLs relativas resolverem ao domínio original
        if soup.head:
            for b in soup.find_all("base"):
                b.decompose()
            base_tag = soup.new_tag("base", href=base_url)
            soup.head.insert(0, base_tag)
        else:
            # Cria <head> se não houver
            head = soup.new_tag("head")
            base_tag = soup.new_tag("base", href=base_url)
            head.append(base_tag)
            if soup.html:
                soup.html.insert(0, head)

        # Links abrem em nova aba (escapa o iframe Streamlit)
        for a in soup.find_all("a", href=True):
            a["target"] = "_blank"
            a["rel"] = "noopener noreferrer"

        # Remove scripts frame-buster que tentariam redirecionar a janela pai
        for s in soup.find_all("script"):
            txt = s.string or ""
            if any(p in txt for p in ("top.location", "self != top", "self!=top",
                                       "parent.location", "window.top", "top!=self")):
                s.decompose()

        return str(soup), None
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code}"
    except Exception as e:
        return None, str(e)


def _markdown_to_html_simple(md: str) -> str:
    """Conversor markdown→HTML mínimo (sem dependências externas).
    Trata headings, parágrafos, listas, blockquotes, links e código inline.
    """
    out_lines = []
    in_list = False
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if in_list:
                out_lines.append("</ul>")
                in_list = False
            out_lines.append("")
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            if in_list:
                out_lines.append("</ul>"); in_list = False
            n = len(m.group(1))
            out_lines.append(f"<h{n}>{m.group(2)}</h{n}>")
            continue

        # Blockquote
        if line.startswith("> "):
            if in_list:
                out_lines.append("</ul>"); in_list = False
            out_lines.append(f"<blockquote>{line[2:]}</blockquote>")
            continue

        # Lista
        if re.match(r"^\s*[-*+]\s+", line):
            if not in_list:
                out_lines.append("<ul>"); in_list = True
            item = re.sub(r"^\s*[-*+]\s+", "", line)
            out_lines.append(f"<li>{item}</li>")
            continue

        if in_list:
            out_lines.append("</ul>"); in_list = False
        out_lines.append(f"<p>{line}</p>")
    if in_list:
        out_lines.append("</ul>")

    html = "\n".join(out_lines)
    # Links: [texto](url)
    html = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', html)
    # Bold e itálico (ordem importa: bold primeiro)
    html = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", html)
    html = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", html)
    # Código inline
    html = re.sub(r"`([^`]+)`", r"<code>\1</code>", html)
    # Imagens (markdown): ![alt](url)
    html = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)",
                  r'<img src="\2" alt="\1" loading="lazy">', html)
    return html


def _wrap_reader_html(content: str, base_url: str) -> str:
    """Envelopa conteúdo em HTML completo com estilo limpo de leitura."""
    return (
        "<!doctype html><html><head>"
        "<meta charset='utf-8'>"
        "<base href='" + base_url + "'>"
        "<style>"
        "body{font-family:'Plus Jakarta Sans',system-ui,-apple-system,sans-serif;"
        "color:#0F172A;background:#FFFFFF;padding:24px 32px;line-height:1.65;"
        "max-width:900px;margin:0 auto;font-size:14px;}"
        "h1,h2,h3,h4{color:#0F172A;letter-spacing:-.01em;margin-top:1.4em;}"
        "h1{font-size:1.6em;}h2{font-size:1.3em;}h3{font-size:1.1em;}"
        "a{color:#2563EB;text-decoration:none;}"
        "a:hover{text-decoration:underline;}"
        "p{margin:.6em 0;}"
        "img{max-width:100%;height:auto;border-radius:8px;margin:10px 0;}"
        "hr{border:none;border-top:1px solid #E2E8F0;margin:20px 0;}"
        "code{background:#F1F5F9;padding:2px 6px;border-radius:4px;font-size:.92em;}"
        "blockquote{border-left:3px solid #CBD5E1;padding:4px 12px;color:#475569;margin:10px 0;}"
        "ul,ol{padding-left:1.4em;}"
        "li{margin:.3em 0;}"
        "</style></head><body>"
        + content +
        "</body></html>"
    )


@st.cache_data(ttl=900, show_spinner=False)
def _fetch_via_reader_proxy(url: str):
    """Tenta múltiplas estratégias para renderizar páginas JS-only que bloqueiam iframe.

    Ordem de tentativas:
    1. Jina AI Reader retornando HTML (mais rico)
    2. Jina AI Reader retornando markdown → convertido para HTML
    3. Erro consolidado com diagnóstico

    Retorna (html_envelopado, erro).
    """
    target = url.strip()
    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    base_headers = {
        "User-Agent": _BROWSER_HEADERS["User-Agent"],
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }

    diagnostics = []

    # Estratégia 1: Jina Reader em modo HTML
    try:
        r = requests.get(
            f"https://r.jina.ai/{target}",
            timeout=30,
            headers={**base_headers, "Accept": "text/html, */*", "X-Return-Format": "html"},
        )
        if r.status_code == 200:
            body = (r.text or "").strip()
            if body and len(body) > 400 and ("<" in body and ">" in body):
                return _wrap_reader_html(body, target), None
            diagnostics.append(f"Jina(html): resposta curta ({len(body)} chars)")
        else:
            diagnostics.append(f"Jina(html): HTTP {r.status_code}")
    except Exception as e:
        diagnostics.append(f"Jina(html): {e}")

    # Estratégia 2: Jina Reader em modo padrão (markdown)
    try:
        r = requests.get(
            f"https://r.jina.ai/{target}",
            timeout=30,
            headers={**base_headers, "Accept": "text/plain, */*"},
        )
        if r.status_code == 200:
            md = (r.text or "").strip()
            if md and len(md) > 200:
                html_body = _markdown_to_html_simple(md)
                return _wrap_reader_html(html_body, target), None
            diagnostics.append(f"Jina(md): resposta curta ({len(md)} chars)")
        else:
            diagnostics.append(f"Jina(md): HTTP {r.status_code}")
    except Exception as e:
        diagnostics.append(f"Jina(md): {e}")

    return None, " · ".join(diagnostics) or "Reader proxy indisponível"


@st.cache_data(ttl=3600, show_spinner=False)
def _wayback_iframe_url(url: str) -> str:
    """Constrói URL de snapshot mais recente da Wayback Machine usando
    a API pública `/wayback/available`. Se a API falhar, cai para o
    padrão `/web/{ano-atual}/url` que normalmente redireciona para o
    snapshot mais próximo.
    """
    target = url.strip()
    if not target.startswith(("http://", "https://")):
        target = "https://" + target

    # API oficial: retorna o snapshot mais próximo da data atual
    try:
        api = f"https://archive.org/wayback/available?url={target}"
        r = requests.get(api, timeout=10, headers={"User-Agent": _BROWSER_HEADERS["User-Agent"]})
        if r.status_code == 200:
            j = r.json() or {}
            snap = (j.get("archived_snapshots") or {}).get("closest") or {}
            snap_url = snap.get("url")
            if snap_url:
                # Wayback fornece URL com prefixo http: — normaliza para https
                if snap_url.startswith("http://web.archive.org"):
                    snap_url = snap_url.replace("http://", "https://", 1)
                return snap_url
    except Exception:
        pass

    # Fallback: ano atual (frequentemente redireciona para snapshot recente)
    return f"https://web.archive.org/web/{datetime.now().year}/{target}"


@st.cache_data(ttl=3600, show_spinner=False)
def _check_iframe_allowed(url: str) -> bool:
    """Verifica server-side se o site permite embedding via iframe.
    Tenta HEAD; se 405, tenta GET com stream. Cache de 1h."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def _parse_headers(headers) -> bool:
        xfo = headers.get("X-Frame-Options", "").upper().strip()
        if xfo in ("DENY", "SAMEORIGIN"):
            return False
        csp = headers.get("Content-Security-Policy", "").lower()
        if "frame-ancestors" in csp:
            if "frame-ancestors 'none'" in csp:
                return False
            # 'self' sem outros origens = bloqueia sites externos
            import re as _re
            fa = _re.search(r"frame-ancestors\s+([^;]+)", csp)
            if fa:
                val = fa.group(1).strip()
                if val in ("'self'", "'none'"):
                    return False
        return True

    try:
        r = requests.head(url, timeout=8, headers=_BROWSER_HEADERS,
                          allow_redirects=True, verify=False)
        if r.status_code == 405:
            raise ValueError("HEAD não suportado")
        return _parse_headers(r.headers)
    except Exception:
        try:
            r = requests.get(url, timeout=8, headers=_BROWSER_HEADERS,
                             allow_redirects=True, verify=False, stream=True)
            r.close()
            return _parse_headers(r.headers)
        except Exception:
            return False   # conservador: não exibe iframe se não conseguir checar


def _render_rss_homepage(source_name: str, items: list, site_url: str):
    """Renderiza itens de RSS como uma 'homepage de revista': hero card
    para a primeira matéria + grid de cards menores. Usado como fallback
    quando reader proxy e proxy server-side falham — sempre funciona
    porque depende apenas de RSS (sem iframe nem JS).
    """
    if not items:
        return

    hero = items[0]
    rest = items[1:13]

    hero_summary = (hero.get("summary") or "")[:240]
    rest_html = ""
    for it in rest:
        title = (it.get("title") or "")[:140]
        link  = it.get("link", "#")
        summ  = (it.get("summary") or "")[:120]
        rest_html += (
            f'<div style="background:#FFFFFF;border:1px solid #E2E8F0;border-radius:10px;'
            f'padding:14px;box-shadow:0 1px 2px rgba(0,0,0,0.04);">'
            f'<a href="{link}" target="_blank" rel="noopener" '
            f'style="color:#0F172A;text-decoration:none;font-weight:700;font-size:13.5px;'
            f'line-height:1.35;letter-spacing:-.01em;display:block;">{title}</a>'
            + (f'<div style="color:#475569;font-size:12px;margin-top:6px;line-height:1.5;">{summ}</div>' if summ else "")
            + f'</div>'
        )

    page = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>"
        "body{font-family:'Plus Jakarta Sans',system-ui,-apple-system,sans-serif;"
        "background:#F4F7F9;margin:0;padding:24px 28px;color:#0F172A;}"
        ".hero{background:linear-gradient(135deg,#EFF6FF 0%,#FFFFFF 100%);"
        "border:1px solid #DBEAFE;border-radius:14px;padding:28px 32px;margin-bottom:20px;"
        "box-shadow:0 2px 8px rgba(37,99,235,0.06);}"
        ".badge{display:inline-block;background:#2563EB;color:#FFFFFF;"
        "font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.08em;"
        "padding:4px 10px;border-radius:6px;margin-bottom:14px;}"
        ".hero h1{font-size:1.6em;margin:0 0 10px;letter-spacing:-.02em;color:#0F172A;line-height:1.25;}"
        ".hero h1 a{color:inherit;text-decoration:none;}"
        ".hero h1 a:hover{color:#2563EB;}"
        ".hero p{color:#475569;font-size:14px;line-height:1.6;margin:0;}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:14px;}"
        "</style></head><body>"
        f"<div class='hero'><span class='badge'>{source_name} · DESTAQUE</span>"
        f"<h1><a href='{hero.get('link','#')}' target='_blank' rel='noopener'>{(hero.get('title') or '')[:200]}</a></h1>"
        + (f"<p>{hero_summary}</p>" if hero_summary else "")
        + f"</div>"
        f"<div class='grid'>{rest_html}</div>"
        "</body></html>"
    )
    _components.html(page, height=760, scrolling=True)


def render_noticias():
    # Sempre recarrega do disco para refletir novas fontes adicionadas
    # via _DEFAULT_NEWS em atualizações do código (ex: ESPN, GE).
    sources = _load_news_sources()
    st.session_state["news_sources"] = sources

    with st.expander("⚙️ Gerenciar fontes", expanded=False):
        st.caption("Ative/desative fontes ou adicione novas (URL do feed RSS).")
        changed = False
        for i, src in enumerate(sources):
            c1, c2, c3 = st.columns([0.4, 2, 0.5])
            with c1:
                enabled = st.checkbox("", value=src.get("enabled", True), key=f"news_en_{i}", label_visibility="collapsed")
                if enabled != src.get("enabled", True):
                    sources[i]["enabled"] = enabled
                    changed = True
            with c2:
                rss_display = (src.get('rss_candidates') or [src.get('rss','')])[0]
                st.markdown(f"**{src['name']}** &nbsp;<span style='color:var(--text3);font-size:11px'>{rss_display[:60]}</span>", unsafe_allow_html=True)
            with c3:
                if st.button("Remover", key=f"news_rm_{i}"):
                    sources.pop(i)
                    _save_news_sources(sources)
                    st.rerun(scope="fragment")
        if changed:
            _save_news_sources(sources)

        st.divider()
        st.markdown("**Adicionar fonte**")
        nc1, nc2, nc3 = st.columns([1.5, 2, 0.7])
        new_name = nc1.text_input("Nome", key="news_new_name", label_visibility="visible")
        new_rss  = nc2.text_input("URL do RSS", key="news_new_rss", label_visibility="visible")
        new_url  = nc3.text_input("Site base", key="news_new_url", label_visibility="visible")
        if st.button("Adicionar", key="news_add"):
            if new_name and new_rss:
                sources.append({"name": new_name, "rss_candidates": [new_rss],
                                 "url": new_url or new_rss, "enabled": True})
                _save_news_sources(sources)
                st.success(f"'{new_name}' adicionado.")
                st.rerun(scope="fragment")

    enabled_sources = [s for s in sources if s.get("enabled", True)]
    if not enabled_sources:
        st.info("Nenhuma fonte ativada.")
        return

    # ── Seletor de fonte ────────────────────────────────────────────
    source_names = [s["name"] for s in enabled_sources]
    if "news_sel" not in st.session_state or st.session_state.get("news_sel") not in source_names:
        st.session_state["news_sel"] = source_names[0]

    sel = st.radio(
        "Fonte",
        source_names,
        horizontal=True,
        index=source_names.index(st.session_state["news_sel"]),
        key="news_source_sel",
        label_visibility="collapsed",
    )
    st.session_state["news_sel"] = sel

    src = next((s for s in enabled_sources if s["name"] == sel), None)
    if not src:
        return

    site_url = src.get("url", "").rstrip("/")
    if not site_url:
        st.warning("URL não configurada para esta fonte.")
        return
    if not site_url.startswith("http"):
        site_url = "https://" + site_url

    # Estratégia configurada por fonte (ex: "reader" para sites JS-only como Valor)
    site_strategy = src.get("site_strategy", "auto")  # "auto" | "reader" | "iframe"

    # ── Verificação server-side de iframe (cache 1h) — pulada se reader ──
    if site_strategy == "reader":
        can_iframe = False
    else:
        with st.spinner(f"Verificando {sel}…"):
            can_iframe = _check_iframe_allowed(site_url)

    key_mode = f"news_mode_{sel}"
    if key_mode not in st.session_state:
        st.session_state[key_mode] = "iframe"   # sempre abre "Site" primeiro
    mode = st.session_state[key_mode]

    # ── Barra de controle: toggle de modo + link externo ────────────
    ctrl1, ctrl2, ctrl3, ctrl_space = st.columns([0.7, 0.9, 1.5, 6])
    with ctrl1:
        if st.button("🌐 Site", key=f"nm_i_{sel}", use_container_width=True,
                     type="primary" if mode == "iframe" else "secondary"):
            st.session_state[key_mode] = "iframe"
            st.rerun(scope="fragment")
    with ctrl2:
        if st.button("📰 Artigos", key=f"nm_a_{sel}", use_container_width=True,
                     type="primary" if mode == "articles" else "secondary"):
            st.session_state[key_mode] = "articles"
            st.rerun(scope="fragment")
    with ctrl3:
        st.markdown(
            f'<div style="padding-top:9px">'
            f'<a href="{site_url}" target="_blank" '
            f'style="color:var(--text3);font-size:11px;font-weight:600;text-decoration:none;">'
            f'↗ Abrir em nova aba</a></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── MODO IFRAME (Site) ──────────────────────────────────────────
    if mode == "iframe":
        if site_strategy == "reader":
            # Cadeia robusta: Jina Reader → Proxy server-side → RSS magazine view
            errs = []
            shown = False

            # 1. Jina Reader (real-time, conteúdo limpo)
            with st.spinner(f"Carregando {sel} via reader proxy…"):
                html_content, err_r = _fetch_via_reader_proxy(site_url)
            if html_content:
                st.caption(
                    f"📡 Renderizado via reader proxy (Jina AI)  ·  conteúdo limpo  ·  "
                    f"links abrem em nova aba"
                )
                _components.html(html_content, height=760, scrolling=True)
                shown = True
            else:
                errs.append(f"Jina: {err_r}")

            # 2. Proxy server-side da home (re-escreve HTML)
            if not shown:
                with st.spinner(f"Tentando proxy server-side…"):
                    html_content2, err_p = _fetch_site_html(site_url)
                if html_content2 and len(html_content2) > 2000:
                    st.caption(
                        f"📡 Renderizado via proxy server-side  ·  X-Frame-Options contornado"
                    )
                    _components.html(html_content2, height=760, scrolling=True)
                    shown = True
                else:
                    errs.append(f"Proxy: {err_p or 'conteúdo vazio'}")

            # 3. Fallback final: RSS renderizado como "homepage de revista"
            if not shown:
                with st.spinner(f"Reader/proxy indisponíveis · montando visão RSS…"):
                    items, err_rss = fetch_news_feed(
                        src.get("rss_candidates", [src.get("rss", "")]),
                        src.get("url", ""),
                        src.get("allow_gn", True),
                        max_items=20,
                    )
                if items:
                    st.caption(
                        f"📰 Reader e proxy falharam ({' · '.join(errs)}). "
                        f"Exibindo as últimas {len(items)} matérias via RSS."
                    )
                    _render_rss_homepage(sel, items, site_url)
                    shown = True

            # 4. Tudo falhou
            if not shown:
                st.warning(
                    f"**{sel}** indisponível em todas as estratégias. "
                    f"Erros: {' · '.join(errs)}. "
                    f"Tente o botão **📰 Artigos** ou abra [{site_url}]({site_url})."
                )
        elif can_iframe:
            # Site permite embedding direto — iframe nativo
            _components.iframe(site_url, height=760, scrolling=True)
        else:
            # Site bloqueia (X-Frame-Options/CSP) — busca server-side e renderiza inline
            with st.spinner(f"Carregando {sel} via proxy server-side…"):
                html_content, err_p = _fetch_site_html(site_url)
            # Fallback automático para reader proxy caso o HTML server-side falhe
            if err_p or not html_content:
                with st.spinner(f"Tentando reader proxy…"):
                    html_content, err_r = _fetch_via_reader_proxy(site_url)
                if html_content:
                    st.caption(
                        f"📡 Renderizado via reader proxy (Jina AI)  ·  fallback automático  ·  "
                        f"links abrem em nova aba"
                    )
                    _components.html(html_content, height=760, scrolling=True)
                else:
                    st.warning(
                        f"**{sel}** bloqueia incorporação. Erro proxy: {err_p or '—'}. "
                        f"Erro reader: {err_r or '—'}. Use **📰 Artigos** ou o link → nova aba."
                    )
            else:
                st.caption(
                    f"📡 Carregado via proxy server-side  ·  X-Frame-Options contornado  ·  "
                    f"links abrem em nova aba"
                )
                _components.html(html_content, height=760, scrolling=True)

    # ── MODO ARTIGOS (RSS + scraper) ─────────────────────────────────
    else:
        with st.spinner(f"Buscando artigos · {sel}…"):
            items, err = fetch_news_feed(
                src.get("rss_candidates", [src.get("rss", "")]),
                src.get("url", ""),
                src.get("allow_gn", True),
                max_items=10,
            )
            if not items:
                # Fallback: HTML scraping explícito (config) ou automático da homepage
                scrape_target = src.get("html_scrape_url") or site_url
                items, err = _scrape_html_news(
                    scrape_target,
                    fallback_urls=src.get("html_scrape_url_fallbacks", []),
                    exclude_subtitle=src.get("html_exclude_subtitle", []),
                )

        if err and not items:
            st.caption(f"⚠️ {err}")
        elif err:
            st.caption(f"ℹ️ {err}")

        if not items:
            st.info(f"Nenhum artigo encontrado para {sel}.")
            return

        for i, item in enumerate(items):
            key_open = f"news_art_{sel}_{i}"

            st.markdown(
                f'<div class="news-card-full">'
                f'<div class="news-title">'
                f'<a href="{item["link"]}" target="_blank">{item["title"]}</a>'
                f'</div>'
                + (f'<div class="news-summary">{item["summary"]}</div>'
                   if item.get("summary") else "")
                + f'</div>',
                unsafe_allow_html=True,
            )

            lbl = "▲ Fechar" if st.session_state.get(key_open, False) else "▼ Ler no dashboard"
            if st.button(lbl, key=f"nb_{sel}_{i}"):
                st.session_state[key_open] = not st.session_state.get(key_open, False)

            if st.session_state.get(key_open, False):
                with st.spinner("Carregando artigo…"):
                    html_c, err_c = _fetch_nl_content(item["link"])
                if err_c:
                    st.warning(f"Não foi possível carregar: {err_c}")
                    st.markdown(f'[↗ Abrir no site]({item["link"]})')
                elif html_c:
                    st.markdown(
                        f'<div class="news-reader">{html_c}</div>',
                        unsafe_allow_html=True,
                    )

            st.markdown(
                "<hr style='margin:6px 0 14px;border:none;"
                "border-top:1px solid var(--border)'>",
                unsafe_allow_html=True,
            )


# ================================================================
# ── NEWSLETTERS  ──────────────────────────────────────────────
# ================================================================
_NEWSLETTER_SOURCES = {
    "Exec Sum": {
        "archive_url":    "https://litquidity.co/newsletter/exec-sum/",
        "site_url":       "https://litquidity.co",
        "rss_candidates": [],
        "section_header": "more from the archive",
        "min_title_len":  8,
    },
    "TNS Money": {
        "archive_url":    "https://money.thenews.com.br/",
        "site_url":       "https://money.thenews.com.br",
        "rss_candidates": ["https://money.thenews.com.br/feed","https://money.thenews.com.br/rss"],
        "section_header": "archive",
        "skip_tag_links": True,
        "min_title_len":  15,
        "post_path_prefix": "/p/",   # Beehiiv: posts em /p/, tags em /t/ — filtra só posts reais
    },
    "TNS Sports": {
        "archive_url":    "https://sports.thenews.com.br/",
        "site_url":       "https://sports.thenews.com.br",
        "rss_candidates": ["https://sports.thenews.com.br/feed","https://sports.thenews.com.br/rss"],
    },
}

_PT_MONTHS = {
    "janeiro":1,"fevereiro":2,"março":3,"marco":3,"abril":4,"maio":5,"junho":6,
    "julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12,
    "jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,
    "jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12,
}

def _extract_date(s: str):
    s2 = s.lower()
    m = re.search(r"(20\d{2})[-/](\d{2})[-/](\d{2})", s)
    if m: return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{2})[-/](\d{2})[-/](20\d{2})", s)
    if m: return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.search(r"/(20\d{2})/(\d{2})/", s)
    if m: return f"{m.group(1)}-{m.group(2)}-01"
    for mn, mv in _PT_MONTHS.items():
        m = re.search(rf"(\d{{1,2}})[- ]{mn}[- ](20\d{{2}}|\d{{2}})", s2)
        if m:
            day, yr = int(m.group(1)), int(m.group(2))
            return f"{yr if yr > 100 else 2000 + yr}-{mv:02d}-{day:02d}"
    return None

_SKIP_HREFS = {"twitter","instagram","facebook","linkedin","mailto","youtube",
               "tiktok","whatsapp","telegram","pinterest","snapchat","#"}

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_nl_index(source_name: str):
    if not HAS_BS4: return [], "beautifulsoup4 não instalado"
    cfg = _NEWSLETTER_SOURCES.get(source_name, {})
    archive_url, site_url = cfg.get("archive_url", ""), cfg.get("site_url", "")

    for rss_url in cfg.get("rss_candidates", []):
        try:
            if not HAS_FEEDPARSER: break
            feed = _feedparser.parse(rss_url)
            if feed.entries:
                items = []
                for e in feed.entries[:20]:
                    title = e.get("title", "").strip()
                    link, pub = e.get("link", ""), e.get("published", e.get("updated", ""))
                    date_str = _extract_date(pub) or _extract_date(link) or ""
                    if title and link:
                        # Filtro TNS Sports: ignora "INSCREVA-SE"
                        if source_name == "TNS Sports" and (
                            "INSCREVA-SE" in title.upper()
                            or "INSCREVASE" in title.upper().replace("-", "")
                        ):
                            continue
                        items.append({"url": link, "title": title, "date": date_str})
                if items: return items, None
        except Exception: pass

    section_header   = cfg.get("section_header", "")
    skip_tag_links   = cfg.get("skip_tag_links", False)
    min_title_len    = cfg.get("min_title_len", 8)
    post_path_prefix = cfg.get("post_path_prefix", "")   # ex: "/p/" para Beehiiv

    def _ok_link(a_tag):
        href = a_tag.get("href","").strip()
        if not href or href.startswith("#"): return None, None
        if href.startswith("/"): href = site_url.rstrip("/") + href
        elif not href.startswith("http"): return None, None
        if any(x in href.lower() for x in _SKIP_HREFS): return None, None
        if href.rstrip("/") == archive_url.rstrip("/"): return None, None
        ph = urlparse(href); ps = urlparse(site_url)
        if ph.netloc and ph.netloc != ps.netloc: return None, None
        if not [p for p in ph.path.split("/") if p]: return None, None
        # Filtro por prefixo de post (ex: somente /p/ = posts Beehiiv reais)
        if post_path_prefix and not ph.path.lower().startswith(post_path_prefix):
            return None, None
        text = a_tag.get_text(strip=True)
        if len(text) < min_title_len: return None, None
        if skip_tag_links:
            path_lower = ph.path.lower()
            # Pula por URL: páginas de tag/categoria/tópico/t
            if any(seg in path_lower for seg in ("/tag/", "/t/", "/categoria/", "/category/", "/topic/", "/topico/")):
                return None, None
            # Pula textos curtos e sem espaço (ex: "Ibovespa", "Bitcoin")
            if len(text) < 25 and " " not in text:
                return None, None
        return href, text

    try:
        r = requests.get(archive_url, timeout=15, headers=_BROWSER_HEADERS)
        r.raise_for_status()
        soup, editions, seen_p = _BS(r.text, "html.parser"), [], set()

        # Quando post_path_prefix está definido, varrer a página inteira é mais robusto
        # do que depender de encontrar um section_header exato no DOM
        use_full_scan = bool(post_path_prefix)

        if section_header and not use_full_scan:
            sec = None
            for el in soup.find_all(string=re.compile(section_header, re.I)):
                sec = el.find_parent()
                break
            if sec:
                for a in sec.find_all_next("a", href=True):
                    href, text = _ok_link(a)
                    if not href: continue
                    p = urlparse(href).path
                    if p in seen_p: continue
                    seen_p.add(p)
                    editions.append({"url":href,"title":text[:150], "date":_extract_date(href) or _extract_date(text) or ""})
                    if len(editions) >= 10: break
        else:
            # Varredura completa: coleta em ordem DOM (mais recente = primeiro na página)
            for a in soup.find_all("a", href=True):
                href, text = _ok_link(a)
                if not href: continue
                p = urlparse(href).path
                if p in seen_p: continue
                seen_p.add(p)
                editions.append({"url":href,"title":text[:150], "date":_extract_date(href) or _extract_date(text) or ""})

        if not editions:
            return [], "Nenhuma edição encontrada"

        # Filtro específico TNS Sports: ignora edições com "INSCREVA-SE" no título
        if source_name == "TNS Sports":
            editions = [
                e for e in editions
                if "INSCREVA-SE" not in (e.get("title") or "").upper()
                and "INSCREVASE" not in (e.get("title") or "").upper().replace("-", "")
            ]

        # Preserva a ordem do DOM (Archive lista mais recente primeiro)
        # Separa por data apenas para ordenar as datadas; sem-data ficam na posição original
        dated   = sorted([e for e in editions if e["date"]], key=lambda x: x["date"], reverse=True)
        undated = [e for e in editions if not e["date"]]
        cutoff  = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
        # Se há datadas recentes, usa datadas (ordenadas desc); caso contrário DOM-order (undated primeiro)
        if dated and any(e["date"] >= cutoff for e in dated):
            result = dated + undated
        else:
            # Mantém ordem DOM para fontes sem datas (como TNS Money)
            result = editions
        return result[:25], None

    except requests.HTTPError as e: return [], f"HTTP {e.response.status_code}"
    except Exception as e: return [], str(e)

@st.cache_data(ttl=3600, show_spinner=False)
def _fetch_nl_content(url: str):
    if not HAS_BS4: return None, "beautifulsoup4 não instalado"
    try:
        r = requests.get(url, timeout=15, headers=_BROWSER_HEADERS)
        r.raise_for_status()
        soup = _BS(r.text, "html.parser")
        for tag in soup(["script","style","nav","header","footer","aside","form","iframe"]):
            tag.decompose()
        content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(id=re.compile(r"content|main|article|post", re.I)) or
            soup.find(class_=re.compile(r"post|article|content|newsletter|body-content", re.I)) or
            soup.find("body")
        )
        if content:
            html = str(content)
            html = re.sub(r'(<img\b[^>]*)(width|height)="[^"]*"', r'\1', html, flags=re.I)
            return html, None
        return None, "Conteúdo não encontrado"
    except Exception as e: return None, str(e)

def _latest_edition(editions):
    today_str = date.today().strftime("%Y-%m-%d")
    h_brt = hora_brt()
    for ed in editions:
        if ed["date"] == today_str: return ed
        if h_brt < 11.0: return editions[0] if editions else None
        break
    return editions[0] if editions else None

def render_newsletters():
    # ── Seletor de newsletter (mesmo padrão da aba Notícias) ─────────
    nl_names = list(_NEWSLETTER_SOURCES.keys())
    if not nl_names:
        st.info("Nenhuma newsletter configurada.")
        return

    if "nl_sel" not in st.session_state or st.session_state.get("nl_sel") not in nl_names:
        st.session_state["nl_sel"] = nl_names[0]

    sel = st.radio(
        "Newsletter",
        nl_names,
        horizontal=True,
        index=nl_names.index(st.session_state["nl_sel"]),
        key="nl_source_sel",
        label_visibility="collapsed",
    )
    st.session_state["nl_sel"] = sel

    cfg = _NEWSLETTER_SOURCES.get(sel, {})
    archive_url = cfg.get("archive_url", "")

    # ── Busca índice de edições ─────────────────────────────────────
    with st.spinner(f"Buscando edições · {sel}…"):
        editions, err_idx = _fetch_nl_index(sel)

    if err_idx and not editions:
        st.error(f"Índice indisponível: {err_idx}")
        st.caption(f"Acesse diretamente: [{archive_url}]({archive_url})")
        return

    if not editions:
        st.info(f"Nenhuma edição encontrada para {sel}.")
        return

    # ── Seletor de edição (latest por padrão) ───────────────────────
    latest = _latest_edition(editions) or editions[0]

    edition_labels = []
    for ed in editions[:25]:
        lbl = f"{ed['date']} — {ed['title'][:70]}" if ed.get("date") else ed["title"][:90]
        edition_labels.append(lbl)

    key_ed = f"nl_ed_{sel}"
    if key_ed not in st.session_state:
        try:
            st.session_state[key_ed] = editions.index(latest)
        except ValueError:
            st.session_state[key_ed] = 0

    ctrl1, ctrl2 = st.columns([4, 1])
    with ctrl1:
        idx = st.selectbox(
            "Edição",
            range(len(edition_labels)),
            format_func=lambda i: edition_labels[i],
            index=min(st.session_state[key_ed], len(edition_labels) - 1),
            key=f"nl_ed_sel_{sel}",
            label_visibility="collapsed",
        )
        st.session_state[key_ed] = idx
    with ctrl2:
        ed_url = editions[idx]["url"]
        st.markdown(
            f'<div style="padding-top:9px">'
            f'<a href="{ed_url}" target="_blank" '
            f'style="color:var(--text3);font-size:11px;font-weight:600;text-decoration:none;">'
            f'↗ Abrir em nova aba</a></div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

    # ── Renderização full-width da edição selecionada ───────────────
    ed = editions[idx]
    ed_date = ed.get("date") or "data desconhecida"
    st.caption(f"📅 {ed_date}  ·  {ed.get('title', '')[:120]}")

    with st.spinner("Carregando conteúdo…"):
        html, err_c = _fetch_nl_content(ed["url"])

    if err_c:
        st.warning(f"Não foi possível carregar: {err_c}")
        st.markdown(f'[↗ Abrir no site]({ed["url"]})')
    elif html:
        st.markdown(
            f'<div class="news-reader">{html}</div>',
            unsafe_allow_html=True,
        )


# ================================================================
# ── ATIVOS — WATCHLIST  ───────────────────────────────────────
# ================================================================
WATCHLIST_FILE = "watchlist.json"

_DEFAULT_WATCHLIST = [
    {"ticker": "TAEE11.SA", "name": "Taesa",           "group": "BR"},
    {"ticker": "ISAE4.SA",  "name": "Isa Cteep",       "group": "BR"},
    {"ticker": "BBSE3.SA",  "name": "BB Seguridade",   "group": "BR"},
    {"ticker": "ITUB4.SA",  "name": "Itaú Unibanco",   "group": "BR"},
    {"ticker": "SANB11.SA", "name": "Santander BR",    "group": "BR"},
    {"ticker": "BRBI11.SA", "name": "BR Advisory",     "group": "BR"},
    {"ticker": "ABCB4.SA",  "name": "ABC Brasil",      "group": "BR"},
    {"ticker": "CPFE3.SA",  "name": "CPFL Energia",    "group": "BR"},
    {"ticker": "IND",       "name": "Ibov Futuro",     "group": "FUTURES"},
    {"ticker": "USDBRL=X",  "name": "Dólar Comercial", "group": "INT"},
    {"ticker": "^GSPC",     "name": "S&P 500",         "group": "INT"},
    {"ticker": "NKE",       "name": "Nike",            "group": "INT"},
    {"ticker": "BRK-B",     "name": "Berkshire B",     "group": "INT"},
]

def _load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, encoding="utf-8") as f: return json.load(f)
        except Exception: pass
    wl = [d.copy() for d in _DEFAULT_WATCHLIST]
    _save_watchlist(wl)
    return wl

def _save_watchlist(wl):
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(wl, f, indent=2, ensure_ascii=False)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_b3_futures_front(product: str):
    url = f"https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/{product}"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data, contracts = r.json(), []
        ts_api = data.get("Msg", {}).get("dtTm", "")
        for s in data.get("Scty", []):
            t = s.get("symb", "")
            if not (t.startswith(product) and len(t) > len(product)): continue
            q, a = s.get("SctyQtn", {}), s.get("asset", {}).get("AsstSummry", {})
            vd, oi = a.get("mtrtyCode", ""), a.get("opnCtrcts") or 0
            
            lp = q.get("curPrc") 
            ajuste = q.get("prvsDayAdjstmntPric") 
            
            if vd and (lp or ajuste):
                contracts.append({
                    "ticker": t, "venc": vd, "price": lp if lp else ajuste, "prev": ajuste,
                    "high": q.get("maxPric"), "low": q.get("minPric"), "oi": oi,
                })
        if not contracts: return None, "Sem contratos"
        contracts.sort(key=lambda x: x["venc"])
        best = max(contracts[:3], key=lambda x: x["oi"]) if len(contracts) >= 3 else contracts[0]
        best["last_ts"] = ts_api[:16] if ts_api else "—"
        return best, None
    except Exception as e: return None, str(e)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_yf_quote(ticker: str):
    if not HAS_YFINANCE: return None, "yfinance não instalado"
    try:
        t = _yf.Ticker(ticker)
        
        hist = t.history(period="7d", auto_adjust=True)
        
        if hist.empty:
            fi = t.fast_info
            last_ts = "tempo real"
            return {"price": fi.last_price, "prev": fi.previous_close,
                    "high": fi.day_high, "low": fi.day_low, "last_ts": last_ts}, None

        # Última linha disponível = pregão mais recente (inclui fin. de semana → sexta)
        price    = float(hist["Close"].iloc[-1])
        high     = float(hist["High"].iloc[-1])
        low      = float(hist["Low"].iloc[-1])
        last_idx = hist.index[-1]
        try:
            last_ts = last_idx.strftime("%d/%m/%y")
        except Exception:
            last_ts = str(last_idx)[:10]

        # Anterior: penúltima linha (pregão do dia anterior ou 2º mais recente)
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price

        # Se preço == anterior e tiver mais dados (mercado fechado sem variação),
        # garante que usamos o fechamento anterior real
        if price == prev and len(hist) > 2:
            prev = float(hist["Close"].iloc[-2])

        return {"price": price, "prev": prev, "high": high, "low": low, "last_ts": last_ts}, None
    except Exception as e: return None, str(e)

def _quote_for_asset(asset: dict):
    grp, ticker = asset.get("group", ""), asset["ticker"]
    if grp == "FUTURES":
        q, err = _fetch_b3_futures_front(ticker)
        if q: return {"price": q["price"], "prev": q["prev"], "high": q["high"], "low": q["low"]}, None
        return None, err
    return _fetch_yf_quote(ticker)

def _pct(price, prev): return (price - prev) / prev * 100 if price and prev and prev != 0 else None
def _pts(price, prev): return price - prev if price and prev else None

def render_ativos():
    if "watchlist" not in st.session_state: st.session_state["watchlist"] = _load_watchlist()
    wl = st.session_state["watchlist"]

    with st.expander("Gerenciar watchlist", expanded=False):
        st.caption("Remova ativos ou adicione novos (ticker exato do yfinance ou B3).")
        to_remove = None
        for i, asset in enumerate(wl):
            c1, c2, c3 = st.columns([2, 1, 0.6])
            c1.markdown(f"**{asset['name']}** `{asset['ticker']}`")
            c2.caption(asset.get("group", ""))
            if c3.button("Remover", key=f"wl_rm_{i}"): to_remove = i
        if to_remove is not None:
            wl.pop(to_remove)
            _save_watchlist(wl)
            st.rerun(scope="fragment")

        st.divider()
        wc1, wc2, wc3, wc4 = st.columns([2, 1, 1, 0.8])
        n_ticker = wc1.text_input("Ticker", key="wl_t", label_visibility="visible")
        n_name   = wc2.text_input("Nome",   key="wl_n", label_visibility="visible")
        n_group  = wc3.selectbox("Grupo", ["BR","INT","FUTURES","OUTRO"], key="wl_g")
        wc4.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if wc4.button("Adicionar", key="wl_add"):
            if n_ticker:
                t = n_ticker.strip().upper()
                if n_group == "BR" and not t.endswith(".SA") and not t.startswith("^"): t += ".SA"
                wl.append({"ticker": t, "name": n_name or t, "group": n_group})
                _save_watchlist(wl)
                st.success(f"{t} adicionado.")
                st.rerun(scope="fragment")

    if not wl:
        st.info("Watchlist vazia.")
        return

    groups = {}
    for asset in wl: groups.setdefault(asset.get("group", "Outros"), []).append(asset)
    group_order = ["BR", "FUTURES", "INT", "OUTRO"]
    sorted_groups = sorted(groups.keys(), key=lambda g: group_order.index(g) if g in group_order else 99)

    for g in sorted_groups:
        assets = groups[g]
        label  = {"BR":"Ações BR","FUTURES":"Futuros B3","INT":"Internacional","OUTRO":"Outros"}.get(g, g)

        # ── Status do mercado ──────────────────────────────────────
        is_open, mkt_label, mkt_ts = _market_status(g)
        mkt_badge = f'<span class="mkt-open">🟢 {mkt_label}</span>' if is_open \
                    else f'<span class="mkt-closed">🔴 {mkt_label}</span>'
        st.markdown(
            f'<p class="mon-head" style="display:flex;align-items:center;gap:10px;">'
            f'{label} {mkt_badge}'
            f'<span class="mkt-ts">BRT {mkt_ts}</span>'
            f'</p>',
            unsafe_allow_html=True,
        )

        rows      = ""
        last_tses = []
        for asset in assets:
            q, err = _quote_for_asset(asset)
            if q:
                price, prev = q.get("price"), q.get("prev")
                pct, pts, high, low = _pct(price, prev), _pts(price, prev), q.get("high"), q.get("low")
                ticker_disp = asset["ticker"].replace(".SA","").replace("=X","")
                ts_disp = q.get("last_ts", "")
                if ts_disp: last_tses.append(ts_disp)
                rows += (
                    f'<tr>'
                    f'<td class="ticker" style="text-align:left">{asset["name"]} <span style="color:var(--text3);font-size:11px">({ticker_disp})</span></td>'
                    f'<td class="hi">{fr(price, 2) if price else "—"}</td>'
                    f'<td>{fd2(pct, 2, "%") if pct is not None else "—"}</td>'
                    f'<td>{fd2(pts, 2)      if pts is not None else "—"}</td>'
                    f'<td class="rate">{fr(high, 2) if high else "—"}</td>'
                    f'<td class="rate">{fr(low,  2) if low  else "—"}</td>'
                    f'</tr>'
                )
            else:
                rows += (
                    f'<tr>'
                    f'<td class="ticker" style="text-align:left">{asset["name"]}</td>'
                    f'<td colspan="5" style="color:var(--text3);font-size:12px">{err or "—"}</td>'
                    f'</tr>'
                )

        # Meta: data do último pregão disponível
        last_ts_unique = sorted(set(last_tses))
        meta_ts = f"dados de {last_ts_unique[-1]}" if last_ts_unique else "lag ~15 min"
        st.caption(f"🕐 {meta_ts} · cache 5 min")

        render_table(
            [("Ativo","left"),("Preço",""),("Δ %",""),("Δ pts",""),("Máx",""),("Mín","")],
            rows,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)



# ================================================================
# ── SRE CVM  ──────────────────────────────────────────────────
# ================================================================
_CVM_URL = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cvm_sre():
    try:
        r = requests.get(_CVM_URL, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        dfs = []
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            csv_files = sorted([n for n in z.namelist() if n.lower().endswith(".csv")])
            for fn in csv_files:
                with z.open(fn) as f:
                    try:
                        df = pd.read_csv(f, encoding="latin-1", sep=";", on_bad_lines="skip", low_memory=False)
                        df.columns = [c.strip() for c in df.columns]
                        dfs.append(df)
                    except Exception: pass
        if not dfs: return None, "Nenhum CSV legível no ZIP"
        df = pd.concat(dfs, ignore_index=True)
        for col in df.columns:
            if "DT" in col.upper() or "DATA" in col.upper():
                try: df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
                except Exception: pass
        return df, None
    except Exception as e: return None, str(e)

def render_cvm():
    st.markdown(f'<p class="mon-sub">Fonte: <a href="{_CVM_URL}" target="_blank" style="color:var(--accent)">{_CVM_URL}</a></p>',
                unsafe_allow_html=True)

    with st.spinner("Baixando dados da CVM (pode levar alguns segundos)…"):
        df, err = fetch_cvm_sre()

    if err:
        st.error(f"Erro ao carregar dados CVM: {err}")
        return
    if df is None or df.empty:
        st.warning("Dados CVM vazios.")
        return

    st.caption(f"{len(df):,} registros · {len(df.columns)} colunas · Atualizado há menos de 1h")

    # ── Coluna de data preferida: Data_requerimento ──────────────────
    def _find_col(df_in, target_name: str):
        target_norm = target_name.replace("_", "").replace(" ", "").lower()
        for c in df_in.columns:
            if c.replace("_", "").replace(" ", "").lower() == target_norm:
                return c
        return None

    date_col = _find_col(df, "Data_requerimento")
    if date_col is None:
        # Fallback: primeira coluna datetime detectada
        dt_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        date_col = dt_cols[0] if dt_cols else None

    # Garante tipo datetime mesmo se a auto-detecção do fetch falhou
    if date_col and not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        try:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce", dayfirst=True)
        except Exception:
            pass

    # ── Coluna do filtro "Tipo de ativo" — na verdade filtra Valor_Mobiliario ──
    tipo_col = _find_col(df, "Valor_Mobiliario")

    # ── Colunas dos filtros adicionais ───────────────────────────────
    emissor_col = _find_col(df, "Nome_Emissor")
    devedor_col = _find_col(df, "Identificacao_devedores_coobrigados")
    coord_col   = _find_col(df, "Nome_Lider")

    # ── Colunas-padrão visíveis (na ordem solicitada) ────────────────
    default_cols_request = [
        "Data_requerimento",
        "Status_requerimento",
        "Valor_Mobiliario",
        "Nome_Emissor",
        "Identificacao_devedores_coobrigados",
        "Nome_Lider",
        "Valor_Total_Registrado",
        "Destinacao_recursos",
        "Descricao_garantias",
    ]
    default_cols_present = []
    for want in default_cols_request:
        c = _find_col(df, want)
        if c and c not in default_cols_present:
            default_cols_present.append(c)

    valor_col = _find_col(df, "Valor_Total_Registrado")
    if valor_col and not pd.api.types.is_numeric_dtype(df[valor_col]):
        try:
            df[valor_col] = pd.to_numeric(
                df[valor_col].astype(str)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False),
                errors="coerce",
            )
        except Exception:
            pass

    with st.expander("Filtros", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        today = date.today()
        if date_col:
            series_dates = df[date_col].dropna()
            if not series_dates.empty:
                min_d_data = series_dates.min().date()
                max_d_data = series_dates.max().date()
            else:
                min_d_data, max_d_data = today - timedelta(days=365 * 5), today

            # Limite superior do widget = hoje (mesmo que dados vão além)
            widget_max = max(max_d_data, today)
            # Limite inferior do widget = min disponível
            widget_min = min(min_d_data, today - timedelta(days=365 * 5))
            # Padrão: hoje até 6 meses atrás (≈ 182 dias)
            default_from = today - timedelta(days=182)
            default_to = today
            # Garante que os defaults estejam dentro dos limites do widget
            default_from = max(default_from, widget_min)
            default_to = min(default_to, widget_max)
            from_d = fc1.date_input("De", value=default_from,
                                    min_value=widget_min, max_value=widget_max,
                                    key="cvm_from", format="DD/MM/YYYY")
            to_d   = fc2.date_input("Até", value=default_to,
                                    min_value=widget_min, max_value=widget_max,
                                    key="cvm_to", format="DD/MM/YYYY")
        else:
            from_d = to_d = None

        if tipo_col:
            tipos = ["Todos"] + sorted(df[tipo_col].dropna().astype(str).unique().tolist())
            sel_tipo = fc3.selectbox("Tipo de ativo", tipos, key="cvm_tipo")
        else:
            sel_tipo = None
            fc3.caption("Coluna 'Valor_Mobiliario' não encontrada no dataset.")

        # ── Filtros adicionais: Emissor / Devedor / Coordenador Líder ──
        ec1, ec2, ec3 = st.columns(3)
        if emissor_col:
            opts_em = ["Todos"] + sorted(df[emissor_col].dropna().astype(str).unique().tolist())
            sel_emissor = ec1.selectbox("Emissor", opts_em, key="cvm_emissor")
        else:
            sel_emissor = None
            ec1.caption("Coluna 'Nome_Emissor' ausente.")

        if devedor_col:
            opts_dv = ["Todos"] + sorted(df[devedor_col].dropna().astype(str).unique().tolist())
            sel_devedor = ec2.selectbox("Devedor", opts_dv, key="cvm_devedor")
        else:
            sel_devedor = None
            ec2.caption("Coluna 'Identificacao_devedores_coobrigados' ausente.")

        if coord_col:
            opts_cd = ["Todos"] + sorted(df[coord_col].dropna().astype(str).unique().tolist())
            sel_coord = ec3.selectbox("Coordenador Lider", opts_cd, key="cvm_coord")
        else:
            sel_coord = None
            ec3.caption("Coluna 'Nome_Lider' ausente.")

        all_cols = list(df.columns)
        sel_cols = st.multiselect(
            "Colunas a exibir",
            all_cols,
            default=default_cols_present if default_cols_present else all_cols[:min(12, len(all_cols))],
            key="cvm_cols",
        )

    fdf = df.copy()
    if date_col and from_d and to_d:
        fdf = fdf[(fdf[date_col].dt.date >= from_d) & (fdf[date_col].dt.date <= to_d)]
    if tipo_col and sel_tipo and sel_tipo != "Todos":
        fdf = fdf[fdf[tipo_col].astype(str) == sel_tipo]
    if emissor_col and sel_emissor and sel_emissor != "Todos":
        fdf = fdf[fdf[emissor_col].astype(str) == sel_emissor]
    if devedor_col and sel_devedor and sel_devedor != "Todos":
        fdf = fdf[fdf[devedor_col].astype(str) == sel_devedor]
    if coord_col and sel_coord and sel_coord != "Todos":
        fdf = fdf[fdf[coord_col].astype(str) == sel_coord]

    # Ordena por Data_requerimento mais recente primeiro (antes de fatiar colunas)
    if date_col and date_col in fdf.columns:
        fdf = fdf.sort_values(date_col, ascending=False, na_position="last")

    if sel_cols:
        fdf = fdf[[c for c in sel_cols if c in fdf.columns]]

    st.caption(f"{len(fdf):,} registros após filtros · ordenado por data mais recente")

    # ── Formatação: Valor_Total_Registrado com separador de milhar ──
    fmt_map = {}
    if valor_col and valor_col in fdf.columns:
        fmt_map[valor_col] = (
            lambda x: f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notna(x) else "—"
        )
    if date_col and date_col in fdf.columns and pd.api.types.is_datetime64_any_dtype(fdf[date_col]):
        fmt_map[date_col] = lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "—"

    styled = fdf.style.format(fmt_map, na_rep="—") if fmt_map else fdf

    # ── Autosize por coluna: calcula width baseado em conteúdo + cabeçalho ──
    def _autosize_config(df_in):
        cfg = {}
        for col in df_in.columns:
            header_len = len(str(col))
            try:
                sample = df_in[col].dropna().head(500).astype(str).str.len()
                content_max = int(sample.max()) if not sample.empty else 0
            except Exception:
                content_max = 0
            approx = max(header_len, content_max)
            # Buckets Streamlit: small (~75px), medium (~200px), large (~400px)
            if approx <= 14:
                w = "small"
            elif approx <= 40:
                w = "medium"
            else:
                w = "large"
            cfg[col] = st.column_config.Column(width=w, help=str(col))
        return cfg

    st.dataframe(
        styled,
        use_container_width=True,
        hide_index=True,
        height=500,
        column_config=_autosize_config(fdf),
    )

    csv_bytes = fdf.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()
    st.download_button("Baixar filtrado (.csv)", csv_bytes, file_name="cvm_sre_filtrado.csv", mime="text/csv")

if __name__ == "__main__":
    main()