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
.block-container{padding-top:2rem!important;padding-bottom:4rem!important;max-width:1440px}
hr{border-color:var(--border)!important;margin:1rem 0!important}

/* ── Tabs ─ segmented control moderno ── */
.stTabs [data-baseweb="tab-list"]{
    background:var(--surf);border:1px solid var(--border);
    border-radius:var(--radius);padding:4px;gap:4px;
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
    padding:12px 16px;text-align:center;border-bottom:2px solid var(--border);white-space:nowrap; /* Alterado para center */
}
.mon-table th.left{text-align:left}
.mon-table td{
    padding:10px 16px;color:var(--text2);text-align:center; /* Alterado para center */
    border-bottom:1px solid var(--border);font-size:13px;
    vertical-align: middle;
}
.mon-table td.ticker{text-align:center;color:var(--text1);font-weight:600;font-size:12.5px}
.mon-table td.rate{color:var(--text2); font-weight: 500;}
.mon-table td.dur{color:var(--text3)}
.mon-table td.hi{color:var(--text1);font-weight:600}
.mon-table tbody tr:last-child td{border-bottom:none}
.mon-table tbody tr:hover td{background:var(--surf2)}
#table-di{width:380px!important}

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

    st.caption(f"🔄 Tabelas atualizadas automaticamente em: {datetime.now().strftime('%H:%M:%S')} (Próximo refresh em 10 min)")

    tabs = st.tabs([
        "Principal",
        "Cotacao DI",
        "Curva DI",
        "NTN-B ANBIMA",
        "Calls NTN-B",
        "Noticias",
        "Newsletters",
        "Ativos",
        "SRE CVM",
    ])
    with tabs[0]: render_principal(di_data, anbima_df, current_calls, ajuste_locked)
    with tabs[1]: render_cotacao_di(di_data)
    with tabs[2]: render_curva_di(di_data)
    with tabs[3]: render_ntnb_anbima(anbima_df, ref_dt)
    with tabs[4]: render_calls(anbima_df, current_calls, save_calls)
    with tabs[5]: render_noticias()
    with tabs[6]: render_newsletters()
    with tabs[7]: render_ativos()
    with tabs[8]: render_cvm()


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
                    st.rerun()  

    if limpar:
        for k in ("manha","tarde","fechamento"):
            calls[k] = {}
        save_fn(calls)
        st.rerun()


# ================================================================
# CONTROLADOR PRINCIPAL (MAIN)
# ================================================================
def main():
    if "calls" not in st.session_state:
        st.session_state["calls"] = load_calls()
        
    current_calls = st.session_state["calls"]

    # ── Header Estático ───────────────────────────────────────
    st.markdown("<div style='margin-top:0.1rem'></div>", unsafe_allow_html=True)

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
     "url": "https://valor.globo.com", "allow_gn": True, "enabled": True},
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
]

def _load_news_sources():
    if os.path.exists(NEWS_FILE):
        try:
            with open(NEWS_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    s = [d.copy() for d in _DEFAULT_NEWS]
    _save_news_sources(s)
    return s

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


def render_noticias():
    if "news_sources" not in st.session_state:
        st.session_state["news_sources"] = _load_news_sources()
    sources = st.session_state["news_sources"]

    with st.expander("Gerenciar fontes", expanded=False):
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
                    st.rerun()
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
                sources.append({"name": new_name, "rss": new_rss,
                                 "url": new_url or new_rss, "enabled": True})
                _save_news_sources(sources)
                st.success(f"'{new_name}' adicionado.")
                st.rerun()

    enabled_sources = [s for s in sources if s.get("enabled", True)]
    if not enabled_sources:
        st.info("Nenhuma fonte ativada.")
        return

    cols = st.columns(min(len(enabled_sources), 3), gap="large")
    col_cycle = 0
    for src in enabled_sources:
        with cols[col_cycle % len(cols)]:
            st.markdown(f'<div class="news-source-badge">{src["name"]}</div>', unsafe_allow_html=True)
            items, err = fetch_news_feed(src.get("rss_candidates", [src.get("rss","")]), src.get("url", ""), src.get("allow_gn", True), max_items=5)
            if not items and src.get("html_scrape_url"):
                items, err = _scrape_html_news(
                    src["html_scrape_url"],
                    fallback_urls=src.get("html_scrape_url_fallbacks", []),
                    exclude_subtitle=src.get("html_exclude_subtitle", []),
                )
            if err and not items:
                st.caption(f"⚠️ {err}")
            elif err:
                st.caption(f"ℹ️ {err}")
            for item in items:
                st.markdown(
                    f'<div class="news-card">'
                    f'<div class="news-title"><a href="{item["link"]}" target="_blank">{item["title"]}</a></div>'
                    f'<div class="news-summary">{item["summary"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        col_cycle += 1


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
        "min_title_len":  20,
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
                        items.append({"url": link, "title": title, "date": date_str})
                if items: return items, None
        except Exception: pass

    section_header = cfg.get("section_header", "")
    skip_tag_links = cfg.get("skip_tag_links", False)
    min_title_len  = cfg.get("min_title_len", 8)

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
        text = a_tag.get_text(strip=True)
        if len(text) < min_title_len: return None, None
        if skip_tag_links and len(text) < 20 and " " not in text: return None, None
        return href, text

    try:
        r = requests.get(archive_url, timeout=15, headers=_BROWSER_HEADERS)
        r.raise_for_status()
        soup, editions, seen_p = _BS(r.text, "html.parser"), [], set()

        if section_header:
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
            for a in soup.find_all("a", href=True):
                href, text = _ok_link(a)
                if not href: continue
                p = urlparse(href).path
                if p in seen_p: continue
                seen_p.add(p)
                editions.append({"url":href,"title":text[:150], "date":_extract_date(href) or _extract_date(text) or ""})

        if not editions:
            return [], "Nenhuma edição encontrada"

        dated   = sorted([e for e in editions if e["date"]], key=lambda x: x["date"], reverse=True)
        undated = [e for e in editions if not e["date"]]
        cutoff  = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
        result  = dated if any(e["date"] >= cutoff for e in dated) else (undated + dated)
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
    cols = st.columns(len(_NEWSLETTER_SOURCES), gap="large")
    for col, (name, cfg) in zip(cols, _NEWSLETTER_SOURCES.items()):
        with col:
            st.markdown(f'<p class="mon-head">{name}</p>', unsafe_allow_html=True)
            if "btn_ref" not in st.session_state: st.session_state["btn_ref"] = {}

            with st.spinner("Buscando edições…"):
                editions, err_idx = _fetch_nl_index(name)

            if err_idx and not editions:
                st.error(f"Índice indisponível: {err_idx}")
                st.caption(f"Acesse diretamente: [{cfg['archive_url']}]({cfg['archive_url']})")
                continue

            latest = _latest_edition(editions)

            if latest:
                st.caption(f"Edição mais recente: {latest['date'] or 'data desconhecida'}")
                st.markdown(
                    f'<a href="{latest["url"]}" target="_blank" style="color:var(--accent);font-size:13px;font-weight:600;">'
                    f'{latest["title"][:80]}</a>',
                    unsafe_allow_html=True,
                )

                key_open = f"nl_open_{name}"
                if st.button("Ler no dashboard", key=f"nl_btn_{name}", use_container_width=True):
                    st.session_state[key_open] = not st.session_state.get(key_open, False)

                if st.session_state.get(key_open, False):
                    with st.spinner("Carregando conteúdo…"):
                        html, err_c = _fetch_nl_content(latest["url"])
                    if err_c:
                        st.warning(f"Não foi possível carregar: {err_c}")
                    elif html:
                        with st.container():
                            st.markdown(
                                f'<div style="max-height:70vh;overflow-y:auto;padding:20px;'
                                f'background:var(--surf);border:1px solid var(--border);border-radius:var(--radius);'
                                f'font-size:14px;color:var(--text2);line-height:1.6;box-shadow:inset 0 2px 4px rgba(0,0,0,0.02);">{html}</div>',
                                unsafe_allow_html=True,
                            )

            if len(editions) > 1:
                with st.expander("Ver edições anteriores"):
                    for ed in editions[1:10]:
                        label = f"{ed['date']} — {ed['title'][:50]}" if ed['date'] else ed['title'][:60]
                        st.markdown(
                            f'<a href="{ed["url"]}" target="_blank" style="color:var(--text3);font-size:12px;">'
                            f'{label}</a><br>',
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
        return max(contracts[:3], key=lambda x: x["oi"]) if len(contracts) >= 3 else contracts[0], None
    except Exception as e: return None, str(e)

@st.cache_data(ttl=300, show_spinner=False)
def _fetch_yf_quote(ticker: str):
    if not HAS_YFINANCE: return None, "yfinance não instalado"
    try:
        t = _yf.Ticker(ticker)
        
        target_date = last_bday()
        target_str = target_date.strftime("%Y-%m-%d")
        
        hist = t.history(period="7d", auto_adjust=True)
        
        if hist.empty:
            fi = t.fast_info
            return {"price": fi.last_price, "prev": fi.previous_close, "high": fi.day_high, "low": fi.day_low}, None

        price = float(hist["Close"].iloc[-1])
        high  = float(hist["High"].iloc[-1])
        low   = float(hist["Low"].iloc[-1])
        
        prev = None
        if target_str in hist.index.strftime("%Y-%m-%d"):
            prev = float(hist.loc[hist.index.strftime("%Y-%m-%d") == target_str, "Close"].iloc[0])
        
        if prev is None:
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price

        if price == prev and len(hist) > 2:
            prev = float(hist["Close"].iloc[-2])

        return {"price": price, "prev": prev, "high": high, "low": low}, None
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
            st.rerun()

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
                st.rerun()

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
        st.markdown(f'<p class="mon-head">{label}</p>', unsafe_allow_html=True)

        rows = ""
        for asset in assets:
            q, err = _quote_for_asset(asset)
            if q:
                price, prev = q.get("price"), q.get("prev")
                pct, pts, high, low = _pct(price, prev), _pts(price, prev), q.get("high"), q.get("low")
                ticker_disp = asset["ticker"].replace(".SA","").replace("=X","")
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

        render_table([("Ativo","left"),("Preço",""),("Δ %",""),("Δ pts",""),("Máx",""),("Mín","")], rows)
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

    with st.expander("Filtros", expanded=True):
        fc1, fc2, fc3 = st.columns(3)
        date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
        date_col  = date_cols[0] if date_cols else None
        if date_col:
            min_d, max_d = df[date_col].dropna().min().date(), df[date_col].dropna().max().date()
            from_d = fc1.date_input("De", value=max_d - timedelta(days=365), min_value=min_d, max_value=max_d, key="cvm_from")
            to_d   = fc2.date_input("Até", value=max_d, min_value=min_d, max_value=max_d, key="cvm_to")
        else: from_d = to_d = None

        tipo_candidates = [c for c in df.columns if any(k in c.upper() for k in ["TIPO","CATEG","CLASSE","ATIVO","OFERTA"])]
        if tipo_candidates:
            tipo_col = tipo_candidates[0]
            tipos = ["Todos"] + sorted(df[tipo_col].dropna().unique().tolist())
            sel_tipo = fc3.selectbox("Tipo de ativo", tipos, key="cvm_tipo")
        else: tipo_col = sel_tipo = None

        all_cols = list(df.columns)
        sel_cols = st.multiselect("Colunas a exibir", all_cols, default=all_cols[:min(12, len(all_cols))], key="cvm_cols")

    fdf = df.copy()
    if date_col and from_d and to_d:
        fdf = fdf[(fdf[date_col].dt.date >= from_d) & (fdf[date_col].dt.date <= to_d)]
    if tipo_col and sel_tipo and sel_tipo != "Todos": fdf = fdf[fdf[tipo_col] == sel_tipo]
    if sel_cols: fdf = fdf[[c for c in sel_cols if c in fdf.columns]]

    st.caption(f"{len(fdf):,} registros após filtros")
    
    st.dataframe(
        fdf, 
        use_container_width=True, 
        hide_index=True, 
        height=500,
        column_config=get_centralized_config(fdf)
    )

    csv_bytes = fdf.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()
    st.download_button("Baixar filtrado (.csv)", csv_bytes, file_name="cvm_sre_filtrado.csv", mime="text/csv")

if __name__ == "__main__":
    main()