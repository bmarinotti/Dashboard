"""
Monitor Macro — Streamlit App
Fontes: B3 DI1 API (15 min lag) + ANBIMA NTN-B arquivo diário
Design: Light Theme, Plus Jakarta Sans + JetBrains Mono, cards com shadow.

Fase 1:
- SQLite local: snapshots DI/ANBIMA, ajuste_locked persistente, fallback B3
- hora_brt() unificada via _time.time() (UTC epoch, sem tzdata)
- Upload de MTM1.xlsx para aplicar calls NTN-B
- Responsividade mobile básica (tabelas scrolláveis)
"""

# ================================================================
# IMPORTS — todos no topo
# ================================================================
import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
import re
import io
import zipfile
import sqlite3
import bisect
import time as _time
import streamlit.components.v1 as _components
from datetime import datetime, date, timedelta
from io import StringIO
from urllib.parse import urlparse

try:
    import feedparser as _feedparser
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

try:
    import yfinance as _yf
    HAS_YFINANCE = True
except ImportError:
    HAS_YFINANCE = False

try:
    from bs4 import BeautifulSoup as _BS
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

LIMIAR_BPS_DEFAULT = 10

# ================================================================
# PAGE CONFIG & CSS
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
    --bg: #F4F7F9;
    --surf: #FFFFFF;
    --surf2: #F8FAFC;
    --surf3: #F1F5F9;
    --border: #E2E8F0;
    --border2: #CBD5E1;
    --text1: #0F172A;
    --text2: #475569;
    --text3: #64748B;
    --accent: #2563EB;
    --accentbg: #EFF6FF;
    --green: #059669;
    --greenbg: #D1FAE5;
    --red: #DC2626;
    --redbg: #FEE2E2;
    --amber: #B45309;
    --amberbg: #FEF3C7;
    --radius: 12px;
    --radius-sm: 8px;
    --shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
}

*,*::before,*::after { box-sizing: border-box }
html, body, [data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background: var(--bg) !important;
    font-family: 'Plus Jakarta Sans', -apple-system, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased;
    color: var(--text1);
}
[data-testid="stHeader"] { background: transparent !important }
[data-testid="stDecoration"] { display: none !important }
section[data-testid="stSidebar"] { display: none !important }
.block-container { padding-top: 0rem !important; padding-bottom: 4rem !important; max-width: 1440px }
hr { border-color: var(--border) !important; margin: 0rem 0 !important }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surf); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 4px; gap: 4px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.02);
    flex-wrap: wrap;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; color: var(--text2); font-size: 12px;
    font-weight: 600; letter-spacing: .02em; text-transform: uppercase;
    padding: 8px 16px; border-radius: var(--radius-sm);
    border: none !important; transition: all .2s ease;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text1); background: var(--surf2) }
.stTabs [aria-selected="true"] {
    background: var(--accentbg) !important; color: var(--accent) !important;
    box-shadow: 0 1px 3px rgba(0,0,0,.04) !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.0rem }

/* ── Separador visual (7ª aba) ── */
.stTabs [data-baseweb="tab-list"] > [data-baseweb="tab"]:nth-child(7) {
    pointer-events: none !important; cursor: default !important; gap: 2px;
    color: var(--text3) !important; background: transparent !important;
    box-shadow: none !important; padding: 8px 10px !important;
    font-size: 10px !important; font-weight: 600 !important; letter-spacing: .06em !important;
    opacity: .75 !important; border-left: 1px solid var(--border) !important;
    margin-left: 6px !important; user-select: none !important;
}
.stTabs [data-baseweb="tab-list"] > [data-baseweb="tab"]:nth-child(7)[aria-selected="true"] {
    background: transparent !important; color: var(--border2) !important; box-shadow: none !important;
}
/* Abas auxiliares (a partir da 7ª posição) — fonte reduzida */
.stTabs [data-baseweb="tab-list"] > [data-baseweb="tab"]:nth-child(n+7) p{
    font-size: 11px !important;
}

/* ── Buttons ── */
div[data-testid="stButton"] > button,
div[data-testid="stDownloadButton"] > button {
    background: var(--surf) !important; border: 1px solid var(--border2) !important;
    color: var(--text2) !important; border-radius: var(--radius-sm) !important;
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif !important;
    font-size: 13px !important; font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03) !important; transition: all .2s !important;
}
div[data-testid="stButton"] > button:hover,
div[data-testid="stDownloadButton"] > button:hover {
    background: var(--surf2) !important; color: var(--text1) !important;
    transform: translateY(-1px); border-color: var(--text3) !important;
}
div[data-testid="stButton"] > button[kind="primary"] {
    background: var(--accent) !important; border: none !important;
    color: #ffffff !important; box-shadow: 0 2px 4px rgba(37,99,235,0.2) !important;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    opacity: 0.9 !important; transform: translateY(-1px);
}

/* ── Inputs ── */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background: var(--surf) !important; border: 1px solid var(--border2) !important;
    border-radius: var(--radius-sm) !important; color: var(--text1) !important;
    font-size: 13px !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color: var(--accent) !important; outline: none !important;
    box-shadow: 0 0 0 2px var(--accentbg) !important;
}
[data-testid="stSelectbox"] > div > div, [data-testid="stMultiSelect"] > div > div {
    background: var(--surf) !important; border: 1px solid var(--border2) !important;
    border-radius: var(--radius-sm) !important; color: var(--text1) !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--surf) !important; border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important; overflow: hidden; box-shadow: var(--shadow);
}
[data-testid="stExpander"] summary {
    font-size: 13px !important; font-weight: 600 !important;
    color: var(--text2) !important; padding: 12px 16px !important;
}
[data-testid="stExpander"] summary:hover { color: var(--text1) !important; background: var(--surf2) !important; }
[data-testid="stCaptionContainer"] p { color: var(--text3) !important; font-size: 11px !important }

/* ── Table card ── */
.table-card {
    background: var(--surf); border: 1px solid var(--border);
    border-radius: var(--radius); overflow: hidden; margin-bottom: 16px;
    box-shadow: var(--shadow); overflow-x: auto;
}
.table-card-header {
    padding: 16px 20px 14px; border-bottom: 1px solid var(--border);
    background: var(--surf); display: flex; justify-content: space-between; align-items: baseline;
}
.table-card-title { font-size: 14px; font-weight: 700; color: var(--text1); letter-spacing: -.01em }
.table-card-meta { font-size: 10px; color: var(--text3); font-family: 'Plus Jakarta Sans', sans-serif; font-weight: 600; text-transform: uppercase; letter-spacing: .04em }

/* ── Monitor table ── */
.mon-table {
    width: 100%; border-collapse: collapse;
    font-family: 'JetBrains Mono', ui-monospace, monospace; font-size: 12.5px;
    background: var(--surf);
}
.mon-table thead { background: var(--surf2) }
.mon-table th {
    font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: 10.5px;
    font-weight: 700; text-transform: uppercase; letter-spacing: .05em; color: var(--text3);
    padding: 7px 16px; text-align: center; border-bottom: 2px solid var(--border); white-space: nowrap;
}
.mon-table th.left { text-align: left }
.mon-table td {
    padding: 6px 16px; color: var(--text2); text-align: center;
    border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle;
}
.mon-table td.ticker { text-align: center; color: var(--text1); font-weight: 600; font-size: 12.5px }
.mon-table td.rate { color: var(--text2); font-weight: 500 }
.mon-table td.dur { color: var(--text3) }
.mon-table td.hi { color: var(--text1); font-weight: 600 }
.mon-table tbody tr:last-child td { border-bottom: 1px solid var(--border) }
.mon-table tbody tr:hover td { background: var(--surf2) }
#table-di { width: 437px !important }

/* ── Dataframe nativo ── */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] iframe {
    border: 1px solid var(--border) !important; border-radius: var(--radius) !important;
    overflow: hidden !important; box-shadow: var(--shadow) !important;
    background-color: #FFFFFF !important;
}

/* ── Deltas ── */
.dp { color: var(--green); font-weight: 600; background: var(--greenbg); padding: 3px 8px; border-radius: 6px; font-size: 11.5px; display: inline-block }
.dn { color: var(--red); font-weight: 600; background: var(--redbg); padding: 3px 8px; border-radius: 6px; font-size: 11.5px; display: inline-block }
.d0 { color: var(--text3); font-size: 11.5px; font-weight: 500 }

/* ── Cache warning chip ── */
.cache-warn {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--amberbg); color: var(--amber);
    font-size: 11px; font-weight: 700; padding: 4px 12px;
    border-radius: 20px; border: 1px solid #FCD34D; margin-bottom: 8px;
}

/* ── Section labels ── */
.mon-head { font-family: 'Plus Jakarta Sans', system-ui, sans-serif; font-size: 15px; font-weight: 700; color: var(--text1); margin: 20px 0 10px; letter-spacing: -.01em }
.mon-sub { font-size: 11px; color: var(--text3); margin-bottom: 8px }

/* ── Badges ── */
.badge-ok { background: var(--greenbg); color: var(--green); font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 20px }
.badge-mt { background: var(--surf2); color: var(--text3); font-size: 11px; font-weight: 600; padding: 4px 10px; border-radius: 20px; border: 1px solid var(--border) }

/* ── News ── */
.news-card-full { padding: 16px 0 10px; border-bottom: none; margin-bottom: 2px }
.news-card-full .news-title a { color: var(--text1) !important; text-decoration: none !important; font-size: 15px; font-weight: 700; line-height: 1.4; letter-spacing: -.01em; display: block }
.news-card-full .news-title a:hover { color: var(--accent) !important }
.news-card-full .news-summary { color: var(--text2); font-size: 13px; margin-top: 4px }
.news-reader { padding: 28px 36px; background: var(--surf); border: 1px solid var(--border); border-radius: var(--radius); font-size: 14px; color: var(--text1); line-height: 1.8; box-shadow: var(--shadow); margin: 8px 0 16px }
.news-reader img { max-width: 100% !important; height: auto !important; border-radius: 6px; margin: 8px 0 }
.news-reader h1, .news-reader h2, .news-reader h3 { color: var(--text1); margin-top: 1.2em }
.news-reader a { color: var(--accent) }
.news-reader p { margin-bottom: .8em }
.news-source-badge { display: inline-block; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: .08em; color: var(--accent); margin-bottom: 12px; background: var(--accentbg); padding: 4px 10px; border-radius: 6px }

/* ── Aux tab banner ── */
.aux-tab-banner {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--surf2); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 6px 14px; font-size: 10.5px; font-weight: 700; color: var(--text3);
    text-transform: uppercase; letter-spacing: .05em; margin-bottom: 14px;
}

/* ── Market status badges ── */
.mkt-open { color: var(--green); font-size: 11px; font-weight: 700; background: var(--greenbg); padding: 3px 10px; border-radius: 20px; display: inline-block }
.mkt-closed { color: var(--text3); font-size: 11px; font-weight: 600; background: var(--surf2); padding: 3px 10px; border-radius: 20px; border: 1px solid var(--border); display: inline-block }
.mkt-ts { font-size: 10px; color: var(--text3); margin-left: 6px; font-family: 'Plus Jakarta Sans', sans-serif }

/* ── Mobile ── */
@media (max-width: 768px) {
    .block-container { padding-left: 12px !important; padding-right: 12px !important }
    .mon-table th, .mon-table td { padding: 6px 10px; font-size: 11.5px }
    .mon-table td.dur { display: none }
    .mon-table:not(#table-di) th:nth-child(2) { display: none }
    #table-di { width: 100% !important; min-width: 300px }
    h1 { font-size: 1.35rem !important }
    .cr-kpis { grid-template-columns: repeat(2,1fr) !important }
}

/* ── Crédito estruturado (mockup E) ── */
.cred-illus { display:inline-block; font-size:9px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--amber); background:var(--amberbg); padding:2px 7px; border-radius:5px; vertical-align:middle }
.cred-src { font-size:10px; color:var(--text3); margin-top:6px; line-height:1.5 }

.cr-agstrip { display:flex; gap:10px; overflow-x:auto; padding:4px 2px 12px; margin-bottom:6px }
.cr-agitem { flex:0 0 auto; background:var(--surf); border:1px solid var(--border); border-radius:10px; padding:9px 14px; box-shadow:var(--shadow); min-width:150px }
.cr-agitem .d { font-family:'JetBrains Mono',monospace; font-size:10px; color:var(--accent); font-weight:600 }
.cr-agitem .e { font-size:12px; font-weight:700; color:var(--text1); margin-top:2px }
.cr-agitem .m { font-size:10.5px; color:var(--text3) }
.cr-agitem.hot { border-color:#FCD34D; background:#FFFBEB }
.cr-agitem.inf .d { color:var(--amber) }
.cr-agitem.act .d { color:var(--green) }

.cr-kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; margin-bottom:16px }
.cr-kpi { background:var(--surf); border:1px solid var(--border); border-radius:var(--radius); padding:13px 16px; box-shadow:var(--shadow) }
.cr-kpi .l { font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:var(--text3) }
.cr-kpi .v { font-family:'JetBrains Mono',monospace; font-size:19px; font-weight:600; margin-top:4px; color:var(--text1) }
.cr-kpi .s { font-size:12px; margin-top:3px; font-family:'JetBrains Mono',monospace; color:var(--text2) }
.cr-up { color:var(--green) } .cr-dn { color:var(--red) } .cr-fl { color:var(--text3) }

.cr-chip { padding:2px 7px; border-radius:6px; font-weight:600; font-size:10.5px; display:inline-block }
.cr-chip.up { background:var(--greenbg); color:var(--green) }
.cr-chip.dn { background:var(--redbg); color:var(--red) }
.cr-chip.fl { color:var(--text3) }
.cr-chip.warn { background:var(--amberbg); color:var(--amber) }
.cr-chip.alert { background:var(--redbg); color:var(--red) }
.cr-chip.ok { background:var(--greenbg); color:var(--green) }
.cr-tag { font-size:9.5px; font-weight:700; padding:2px 7px; border-radius:5px }
.cr-tag.cdi { background:#EFF6FF; color:#1D4ED8 } .cr-tag.ipca { background:#F0FDF4; color:#15803D }
.cr-tag.cri { background:#FEF3C7; color:#92400E } .cr-tag.cra { background:#FAF5FF; color:#7E22CE }

.cr-feed { padding:4px 0 }
.cr-fitem { display:flex; gap:12px; padding:9px 18px; border-bottom:1px solid var(--border); align-items:baseline }
.cr-fitem:last-child { border-bottom:none }
.cr-fitem .ag { font-size:14px; font-weight:800; letter-spacing:.06em; min-width:62px; color:#7C3AED;text-align:center }
.cr-fitem .tx { font-size:14px; color:var(--text1); line-height:1.4 }
.cr-fitem .tx small { color:var(--text3); display:block; font-size:10.5px; margin-top:1px }
.cr-up-ar { color:var(--green); font-weight:700 } .cr-dn-ar { color:var(--red); font-weight:700 }
.cr-hint { font-size:11px; color:var(--text3); padding:9px 18px; background:var(--surf2); border-top:1px solid var(--border) }

.briefing-grid { display:grid; grid-template-columns:1fr 0.7fr 1.6fr; gap:12px; margin-bottom:16px }
.briefing-card { background:var(--surf); border:1px solid var(--border); border-radius:var(--radius); padding:14px 16px; box-shadow:var(--shadow) }
.briefing-card h4 { font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:.06em; color:var(--text3); margin:0 0 10px }
.briefing-row { display:flex; justify-content:space-between; align-items:baseline; padding:3px 0; border-bottom:1px solid var(--border) }
.briefing-row:last-child { border-bottom:none }
.briefing-row .nm { font-size:12px; color:var(--text1); font-weight:600; width: 60%; /* <--- FIXE O TAMANHO DA "COLUNA" ESQUERDA AQUI */
    white-space: nowrap; 
    overflow: hidden; 
    /*text-overflow: ellipsis;  <-- Adiciona '...' se o nome do emissor for muito grande */
}
.briefing-row .dl { font-family:'JetBrains Mono',monospace; font-size:11.5px; width: 40%; /* <--- FIXE O TAMANHO DA "COLUNA" DIREITA AQUI */
	text-align: center;

}
.briefing-fallback { font-size:11.5px; color:var(--text3); font-style:italic; padding:6px 0 }
.briefing-synth { background:var(--amberbg); border:1px solid #FCD34D; border-radius:var(--radius-sm); padding:9px 14px; margin-bottom:12px; margin-top:10px; font-size:12.5px; color:var(--amber); line-height:1.5 }
@media (max-width: 560px) {
    .briefing-grid { grid-template-columns:1fr !important }
}

/* ── Periodicidade (radio horizontal estilo segmented control) ── */
div[role="radiogroup"] {
    gap: 4px !important; background: var(--surf); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 3px; display: inline-flex;
    box-shadow: 0 1px 2px rgba(0,0,0,.02);
}
div[role="radiogroup"] label {
    margin: 0 !important; padding: 4px 10px !important; border-radius: 6px !important;
    cursor: pointer; transition: all .15s ease;
}
div[role="radiogroup"] label:hover { background: var(--surf2) }
div[role="radiogroup"] label p {
    font-size: 11px !important; font-weight: 600 !important; color: var(--text2) !important;
}
div[role="radiogroup"] label:has(input:checked) { background: var(--accentbg) !important }
div[role="radiogroup"] label:has(input:checked) p { color: var(--accent) !important }
div[role="radiogroup"] label > div:first-child { display: none !important } /* esconde a bolinha */
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
# SQLITE — banco local de snapshots e meta
# ================================================================
DB_FILE = "monitor_macro.db"


def _db():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    """Cria tabelas se nao existirem. Idempotente."""
    with _db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS di_snapshots (
            saved_at       INTEGER NOT NULL,
            brt_date       TEXT    NOT NULL,
            ticker         TEXT    NOT NULL,
            ajuste         REAL,
            ajuste_oficial REAL,
            ultimo         REAL,
            vencimento     TEXT,
            PRIMARY KEY (brt_date, ticker)
        );
        CREATE TABLE IF NOT EXISTS anbima_snapshots (
            ref_date   TEXT NOT NULL,
            label      TEXT NOT NULL,
            vencimento TEXT NOT NULL,
            tx_ind     REAL,
            duration   REAL,
            PRIMARY KEY (ref_date, label)
        );
        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS credito_runs (
            brt_date    TEXT NOT NULL,
            run_type    TEXT NOT NULL,    -- CDI | IPCA | LF
            saved_at    INTEGER NOT NULL,
            ativo       TEXT,
            emissor     TEXT,
            tipo        TEXT,             -- LF/LFSC/LFSN/CDB (só LF); senão NULL
            vencimento  TEXT,
            indexador   TEXT,
            compra      REAL,
            venda       REAL,
            anbima      REAL,
            duration    REAL,
            rating      TEXT,
            secao       TEXT,             -- comum | isenta (IPCA); senão NULL
            spread_b    REAL,             -- bps, calculado p/ IPCA+ via interpolação NTN-B
            PRIMARY KEY (brt_date, run_type, ativo, vencimento, indexador)
        );
        CREATE TABLE IF NOT EXISTS calls_historico (
            brt_date TEXT NOT NULL,
            session  TEXT NOT NULL,
            label    TEXT NOT NULL,
            taxa     REAL,
            PRIMARY KEY (brt_date, session, label)
        );
        """)
    # Migração idempotente: adiciona ajuste_oficial em bancos antigos
    try:
        with _db() as con:
            cols = [r[1] for r in con.execute("PRAGMA table_info(di_snapshots)").fetchall()]
            if "ajuste_oficial" not in cols:
                con.execute("ALTER TABLE di_snapshots ADD COLUMN ajuste_oficial REAL")
    except Exception:
        pass


def _brt_today() -> str:
    return (datetime.utcfromtimestamp(_time.time()) - timedelta(hours=3)).strftime("%Y-%m-%d")


def _brt_date() -> date:
    """Data atual em BRT. Em servidor UTC (Streamlit Cloud), date.today()
    adianta 1 dia entre 21h e 00h BRT — usar esta função para datas de mercado."""
    return (datetime.utcfromtimestamp(_time.time()) - timedelta(hours=3)).date()


def save_di_snapshot(di_data: dict):
    """Persiste snapshot DI. Chamado fora do cache Streamlit.

    Após 16h30 BRT o campo prvsDayAdjstmntPric da B3 já é o ajuste OFICIAL
    de hoje — capturamos em ajuste_oficial, que vira o D-1 oficial amanhã.
    Durante o pregão, prvsDayAdjstmntPric ainda é o D-1; salvamos só em ajuste.
    """
    brt_date = _brt_today()
    now_ts   = int(_time.time())
    is_pos_fechamento = hora_brt() >= 16.5   # 16h30
    rows = []
    for ticker, info in di_data.get("tickers", {}).items():
        prvs = info.get("ajuste")
        oficial = prvs if is_pos_fechamento else None
        rows.append((now_ts, brt_date, ticker,
                     prvs, oficial, info.get("ultimo"), info.get("vencimento")))
    if not rows:
        return
    try:
        with _db() as con:
            # COALESCE preserva ajuste_oficial já gravado se este update vier com NULL
            con.executemany(
                "INSERT INTO di_snapshots"
                " (saved_at, brt_date, ticker, ajuste, ajuste_oficial, ultimo, vencimento)"
                " VALUES (?,?,?,?,?,?,?)"
                " ON CONFLICT(brt_date, ticker) DO UPDATE SET"
                "   saved_at=excluded.saved_at,"
                "   ajuste=excluded.ajuste,"
                "   ajuste_oficial=COALESCE(excluded.ajuste_oficial, di_snapshots.ajuste_oficial),"
                "   ultimo=excluded.ultimo,"
                "   vencimento=excluded.vencimento",
                rows,
            )
    except Exception:
        pass


def get_prev_bday_ajuste() -> dict:
    """Retorna {ticker: ajuste D-1 OFICIAL} do último dia útil no banco (exceto hoje).
    Prioriza ajuste_oficial (capturado pós-fechamento); cai para ajuste se ausente."""
    today = _brt_today()
    try:
        with _db() as con:
            rows = con.execute(
                "SELECT ticker, COALESCE(ajuste_oficial, ajuste) FROM di_snapshots"
                " WHERE brt_date = ("
                "   SELECT MAX(brt_date) FROM di_snapshots WHERE brt_date < ?"
                " ) AND COALESCE(ajuste_oficial, ajuste) IS NOT NULL",
                (today,),
            ).fetchall()
        return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


def load_di_from_cache() -> tuple:
    """Fallback: carrega ultimo snapshot DI do banco quando API B3 falha."""
    try:
        with _db() as con:
            rows = con.execute(
                "SELECT ticker, COALESCE(ajuste_oficial, ajuste), ultimo, vencimento, saved_at"
                " FROM di_snapshots"
                " WHERE brt_date = (SELECT MAX(brt_date) FROM di_snapshots)",
            ).fetchall()
        if not rows:
            return None, "Sem snapshots DI no banco local"
        saved_at = rows[0][4]
        ts_str = (datetime.utcfromtimestamp(saved_at) - timedelta(hours=3)).strftime("%d/%m %H:%M") \
                 if saved_at else "?"
        out = {r[0]: {"ticker": r[0], "ajuste": r[1], "ultimo": r[2],
                      "vencimento": r[3]} for r in rows}
        return {"tickers": out, "timestamp": ts_str, "from_cache": True}, None
    except Exception as e:
        return None, str(e)


def save_anbima_snapshot(df: pd.DataFrame, ref_date):
    """Persiste snapshot ANBIMA no banco."""
    ref_str = ref_date.strftime("%Y-%m-%d") if hasattr(ref_date, "strftime") else str(ref_date)
    rows = []
    for _, row in df.iterrows():
        vd = row["vencimento"]
        vd_str = vd.strftime("%Y-%m-%d") if hasattr(vd, "strftime") else str(vd)
        rows.append((ref_str, row["label"], vd_str,
                     row.get("tx_ind"), row.get("duration")))
    if not rows:
        return
    try:
        with _db() as con:
            con.executemany(
                "INSERT OR REPLACE INTO anbima_snapshots"
                " (ref_date, label, vencimento, tx_ind, duration)"
                " VALUES (?,?,?,?,?)",
                rows,
            )
    except Exception:
        pass


def load_anbima_prev():
    """Retorna DataFrame (label, tx_ind_prev) do penúltimo ref_date em anbima_snapshots, ou None."""
    try:
        with _db() as con:
            rows = con.execute(
                "SELECT DISTINCT ref_date FROM anbima_snapshots ORDER BY ref_date DESC LIMIT 2"
            ).fetchall()
        if len(rows) < 2:
            return None
        prev_date = rows[1][0]
        with _db() as con:
            data = con.execute(
                "SELECT label, tx_ind FROM anbima_snapshots WHERE ref_date=?", (prev_date,)
            ).fetchall()
        if not data:
            return None
        return pd.DataFrame(data, columns=["label", "tx_ind_prev"])
    except Exception:
        return None


def load_anbima_series(label: str, n_days: int = 252):
    """Série histórica de tx_ind de um vértice NTN-B nos últimos n_days pregões."""
    try:
        with _db() as con:
            rows = con.execute(
                "SELECT tx_ind FROM anbima_snapshots"
                " WHERE label = ? AND ref_date >= date('now', ? || ' days')"
                " ORDER BY ref_date",
                (label, f"-{n_days}"),
            ).fetchall()
        vals = [r[0] for r in rows if r[0] is not None]
        return pd.Series(vals) if vals else None
    except Exception:
        return None


def percentil_anbima(label: str, valor_hoje, n_days: int = 252):
    """Percentil de valor_hoje dentro da série histórica. None se < 10 obs."""
    if valor_hoje is None:
        return None
    serie = load_anbima_series(label, n_days)
    if serie is None or len(serie) < 10:
        return None
    return int(round((serie < valor_hoje).sum() / len(serie) * 100))


def load_anbima_from_cache() -> tuple:
    """Fallback: carrega ultimo snapshot ANBIMA do banco."""
    try:
        with _db() as con:
            ref = con.execute(
                "SELECT MAX(ref_date) FROM anbima_snapshots"
            ).fetchone()[0]
            if not ref:
                return None, None, "Sem snapshots ANBIMA no banco local"
            rows = con.execute(
                "SELECT label, vencimento, tx_ind, duration"
                " FROM anbima_snapshots WHERE ref_date = ?",
                (ref,),
            ).fetchall()
        df = pd.DataFrame(rows, columns=["label", "vencimento", "tx_ind", "duration"])
        df["vencimento"] = pd.to_datetime(df["vencimento"])
        return df, date.fromisoformat(ref), None
    except Exception as e:
        return None, None, str(e)


def set_meta(key: str, value: str):
    try:
        with _db() as con:
            con.execute(
                "INSERT OR REPLACE INTO meta (key, value) VALUES (?,?)", (key, value)
            )
    except Exception:
        pass


def get_meta(key: str):
    try:
        with _db() as con:
            row = con.execute(
                "SELECT value FROM meta WHERE key = ?", (key,)
            ).fetchone()
        return row[0] if row else None
    except Exception:
        return None


# ================================================================
# HELPERS
# ================================================================
def hora_brt() -> float:
    """Hora decimal em BRT (UTC-3 fixo). Usa _time.time() — sem tzdata."""
    now_brt = datetime.utcfromtimestamp(_time.time()) - timedelta(hours=3)
    return now_brt.hour + now_brt.minute / 60


def is_bday(d):
    return d.weekday() < 5 and d not in FERIADOS


def last_bday(from_date=None):
    d = (from_date or _brt_date()) - timedelta(days=1)
    while not is_bday(d):
        d -= timedelta(days=1)
    return d


def count_du(start, end):
    if end <= start:
        return 0
    return int(np.busday_count(start, end, busdaycal=_BUSDAYCAL))


def _us_in_dst(d: date) -> bool:
    y = d.year
    mar1 = date(y, 3, 1)
    dst_start = mar1 + timedelta(days=(6 - mar1.weekday()) % 7) + timedelta(7)
    nov1 = date(y, 11, 1)
    dst_end = nov1 + timedelta(days=(6 - nov1.weekday()) % 7)
    return dst_start <= d < dst_end


def _market_status(group: str):
    now_utc  = datetime.utcfromtimestamp(_time.time())
    now_brt  = now_utc - timedelta(hours=3)
    today    = now_brt.date()
    h        = now_brt.hour + now_brt.minute / 60
    wd       = today.weekday()
    ts       = now_brt.strftime("%H:%M BRT")

    if wd >= 5:
        return False, "Fechado · final de semana", ts

    if group in ("BR", "FUTURES"):
        if today in FERIADOS:
            return False, "Fechado · feriado B3", ts
        open_h  = 9.0  if group == "FUTURES" else 10.0
        close_h = 18.0 if group == "FUTURES" else (17.0 + 55.0/60.0)
        if open_h <= h < close_h:
            return True, "Aberto · B3", ts
        return False, "Fechado · B3", ts

    elif group == "INT":
        dst    = _us_in_dst(today)
        offset = 1 if dst else 2
        nyse_o = 9.5  + offset
        nyse_c = 16.0 + offset
        tz_lbl = "EDT" if dst else "EST"
        if nyse_o <= h < nyse_c:
            return True,  f"Aberto · NYSE ({tz_lbl})", ts
        return False, f"Fechado · NYSE ({tz_lbl})", ts

    return False, "—", ts


def anbima_url_and_date():
    lbd = last_bday()
    return f"https://www.anbima.com.br/informacoes/merc-sec/arqs/ms{lbd.strftime('%y%m%d')}.txt", lbd


def january_di_tickers():
    base = _brt_date().year
    return [f"DI1F{str(base + i + 1)[-2:]}" for i in range(10)]


def string_or_serial_to_date(val):
    if val is None:
        return None
    # Objeto datetime/date/Timestamp (openpyxl, pandas)
    if hasattr(val, "date") and callable(val.date):
        return val.date()
    if isinstance(val, date):
        return val
    val_str = str(val).strip()
    # ISO yyyy-mm-dd (pandas retorna assim para datas do Excel)
    try:
        return date.fromisoformat(val_str[:10])
    except Exception:
        pass
    # dd/mm/yyyy
    if "/" in val_str:
        try:
            parts = val_str.split("/")
            day, month, year = int(parts[0]), int(parts[1]), int(parts[2])
            if year < 100:
                year += 2000
            return date(year, month, day)
        except Exception:
            pass
    # Serial Excel
    try:
        n = int(float(val_str.replace(",", ".")))
        if n < 40000:
            return None
        return date(1899, 12, 30) + timedelta(days=n)
    except Exception:
        return None


def fr(v, dec=2):
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "—"
        return f"{v:,.{dec}f}"
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
    today = today_date or _brt_date()
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
# FETCH B3 DI
# ================================================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_b3_di():
    url = "https://cotacao.b3.com.br/mds/api/v1/DerivativeQuotation/DI1"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        data = r.json()
        out  = {}
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
        if not out:
            raise ValueError("Sem tickers DI1F na resposta")
        ts = data.get("Msg", {}).get("dtTm", "")
        return {"tickers": out, "timestamp": ts, "from_cache": False}, None
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
            return None, "Header nao encontrado no arquivo ANBIMA", ref
        raw = "\n".join(lines[hi:])
        df  = pd.read_csv(StringIO(raw), sep="@", dtype=str, on_bad_lines="skip")
        df.columns = [c.strip() for c in df.columns]
        titulo_col = next((c for c in df.columns if c.lower().startswith("titulo")), None)
        if titulo_col is None:
            return None, f"Coluna 'Titulo' nao encontrada. Colunas: {list(df.columns)}", ref
        df = df[df[titulo_col].str.strip() == "NTN-B"].copy()
        venc_col = next(
            (c for c in df.columns if "vencimento" in c.lower() or c.lower() in ("venc","dt venc","dt.venc")),
            None,
        )
        if venc_col is None:
            return None, f"Coluna de vencimento nao encontrada. Colunas: {list(df.columns)}", ref
        df["vencimento"] = pd.to_datetime(df[venc_col].str.strip(), format="%Y%m%d", errors="coerce")
        df = df[df["vencimento"] >= pd.Timestamp(_brt_date())].copy()
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
            lambda row: calc_duration(row["vencimento"], row["tx_ind"]), axis=1
        )
        df["label"] = df["vencimento"].dt.strftime("B%y")
        df = df.sort_values("vencimento").reset_index(drop=True)
        return df, None, ref
    except requests.HTTPError as e:
        return None, f"HTTP {e.response.status_code} — {url}", ref
    except Exception as e:
        return None, str(e), ref


# ================================================================
# CALLS — Persistencia, parsers (texto + xlsx)
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


def load_calls_historico(n_days=30):
    """Retorna DataFrame com calls dos últimos n_days dias."""
    try:
        with _db() as con:
            rows = con.execute(
                "SELECT brt_date, session, label, taxa FROM calls_historico"
                " WHERE brt_date >= date('now', ? || ' days')"
                " ORDER BY brt_date DESC",
                (f"-{n_days}",),
            ).fetchall()
        if not rows:
            return None
        return pd.DataFrame(rows, columns=["brt_date", "session", "label", "taxa"])
    except Exception:
        return None


def save_calls(calls):
    with open(CALLS_FILE, "w") as f:
        json.dump(calls, f, indent=2)
    today = _brt_today()
    rows = []
    for session, entries in calls.items():
        for label, taxa in (entries or {}).items():
            if taxa is not None:
                rows.append((today, session, label, float(taxa)))
    if rows:
        try:
            with _db() as con:
                con.executemany(
                    "INSERT OR REPLACE INTO calls_historico"
                    " (brt_date, session, label, taxa) VALUES (?,?,?,?)",
                    rows,
                )
        except Exception:
            pass


def _to_float(s):
    if s is None:
        return None
    s = str(s).strip().replace(" ", "").replace("%", "")
    if not s or s in ("-", "--", "N/D", "nan"):
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
    """Parser do range TSV colado do Excel (fallback/legado)."""
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
                compra_m = _to_float(cols[4]); venda_m = _to_float(cols[5])
                compra_t = _to_float(cols[7]); venda_t = _to_float(cols[8])
                compra_f = _to_float(cols[10]); venda_f = _to_float(cols[11])
        elif len(cols) > 2 and ("/" in cols[2] or cols[2].replace(",", "").replace(".", "").isdigit()):
            venc_date = string_or_serial_to_date(cols[2])
            if venc_date and len(cols) >= 13:
                compra_m = _to_float(cols[5]); venda_m = _to_float(cols[6])
                compra_t = _to_float(cols[8]); venda_t = _to_float(cols[9])
                compra_f = _to_float(cols[11]); venda_f = _to_float(cols[12])
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
        for sess, cp, vd in [("manha", compra_m, venda_m), ("tarde", compra_t, venda_t), ("fechamento", compra_f, venda_f)]:
            vals = [x for x in [cp, vd] if x is not None]
            if vals:
                sessions[sess][label] = sum(vals) / len(vals)
    return sessions if any(sessions.values()) else None


def parse_call_xlsx(file_bytes: bytes, anbima_df) -> dict:
    """
    Le MTM1.xlsx e extrai calls de NTN-B.
    Estrutura confirmada: aba MTM, NTN-B em row=37 col=1 (0-based).
    Cabecalho 3 linhas abaixo. Datas retornam como Timestamp do pandas.

    Offsets a partir da coluna NTN-B:
      0=TITULO, 1=VENCTO, 2=ANBIMA D-1, 3=IMPLICITA D-1,
      4=COMPRA M, 5=VENDA M, 6=ULT NEG M,
      7=COMPRA T, 8=VENDA T, 9=ULT NEG T,
      10=COMPRA F, 11=VENDA F, 12=ULT NEG F
    """
    try:
        try:
            df_raw = pd.read_excel(
                io.BytesIO(file_bytes), sheet_name="MTM",
                header=None, engine="openpyxl",
            )
        except Exception:
            df_raw = pd.read_excel(
                io.BytesIO(file_bytes), sheet_name=0,
                header=None, engine="openpyxl",
            )
    except Exception:
        return None

    # Localiza "NTN-B" na planilha
    ntnb_row = ntnb_col = None
    for r in range(len(df_raw)):
        for c in range(len(df_raw.columns)):
            try:
                val = str(df_raw.iat[r, c]).strip()
            except Exception:
                continue
            if val == "NTN-B":
                ntnb_row, ntnb_col = r, c
                break
        if ntnb_row is not None:
            break
    if ntnb_row is None:
        return None

    # Localiza linha de cabecalho (TITULO na coluna ntnb_col)
    header_row = None
    for r in range(ntnb_row, min(ntnb_row + 10, len(df_raw))):
        try:
            raw_val = df_raw.iat[r, ntnb_col]
            val = str(raw_val).strip().upper()
        except Exception:
            continue
        if "T" in val and ("TULO" in val or "\u00cdTULO" in val):
            header_row = r
            break
    if header_row is None:
        return None

    # Monta venc → label a partir do ANBIMA
    venc_lookup = {}
    if anbima_df is not None:
        for _, row in anbima_df.iterrows():
            vd = row["vencimento"]
            if hasattr(vd, "date"):
                vd = vd.date()
            venc_lookup[vd] = row["label"]

    sessions = {"manha": {}, "tarde": {}, "fechamento": {}}

    def _cell(r, offset):
        col_idx = ntnb_col + offset
        if col_idx >= len(df_raw.columns):
            return None
        val = df_raw.iat[r, col_idx]
        try:
            if pd.isna(val):
                return None
        except (TypeError, ValueError):
            pass
        return _to_float(val)

    for r in range(header_row + 1, len(df_raw)):
        try:
            titulo = df_raw.iat[r, ntnb_col]
        except Exception:
            continue
        try:
            if pd.isna(titulo):
                continue
        except (TypeError, ValueError):
            pass
        titulo_str = str(titulo).strip()
        # Fim da secao NTN-B
        try:
            float(titulo_str.replace(",", "."))
        except ValueError:
            if titulo_str:
                break
            continue

        # VENCTO — pandas entrega como Timestamp para celulas de data
        try:
            vencto_raw = df_raw.iat[r, ntnb_col + 1]
        except Exception:
            continue
        venc_date = string_or_serial_to_date(vencto_raw)
        if venc_date is None:
            continue

        # Resolve label via lookup (tolerancia de +/-3 dias)
        label = venc_lookup.get(venc_date)
        if label is None:
            for delta in range(-3, 4):
                label = venc_lookup.get(venc_date + timedelta(days=delta))
                if label:
                    break
        if label is None:
            continue

        # Media compra+venda por sessao
        for sess, cp_off, vd_off in [("manha", 4, 5), ("tarde", 7, 8), ("fechamento", 10, 11)]:
            cp = _cell(r, cp_off)
            vd = _cell(r, vd_off)
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


def render_collapsible_table(headers, rows_list, key, n=4, title=None, meta=None,
                             label_more="Ver todos", label_less="Recolher"):
    """Tabela com expandir/retrair quando a lista passa de `n` itens.
    `rows_list` = lista de strings <tr>…</tr>. Mostra `n` por padrão."""
    total = len(rows_list)
    expanded = st.session_state.get(key, False)
    shown = rows_list if (expanded or total <= n) else rows_list[:n]
    render_table(headers, "".join(shown), title=title, meta=meta)
    if total > n:
        lbl = f"{label_less} ▴" if expanded else f"{label_more} ({total}) ▾"
        if st.button(lbl, key=f"btn_{key}", use_container_width=True):
            st.session_state[key] = not expanded
            st.rerun(scope="fragment")


def get_centralized_config(df):
    return {col: st.column_config.Column(alignment="center") for col in df.columns}


# ================================================================
# FRAGMENTO DE AUTO-REFRESH (10 MINUTOS)
# ================================================================
@st.fragment(run_every=600)
def render_conteudo_dinamico(current_calls):
    """Encapsula toda logica dinamica com auto-refresh silencioso."""

    # ── Fetch ─────────────────────────────────────────────────
    di_data,   di_err              = fetch_b3_di()
    anbima_df, anbima_err, ref_dt  = fetch_anbima()

    # ── Fallbacks SQLite ───────────────────────────────────────
    di_cache_msg = None
    if di_data is None:
        di_data, cache_err = load_di_from_cache()
        if di_data:
            di_cache_msg = f"API B3 indisponível — cache de {di_data['timestamp']}"
        else:
            di_err = di_err or cache_err
    else:
        save_di_snapshot(di_data)

    if anbima_df is None:
        anbima_df, ref_dt_cache, _ = load_anbima_from_cache()
        if anbima_df is not None:
            ref_dt = ref_dt_cache
    else:
        save_anbima_snapshot(anbima_df, ref_dt)

    # ── Erros ─────────────────────────────────────────────────
    if di_err and not di_cache_msg:
        st.error(f"**B3 DI:** {di_err}")
    if anbima_err and "cache" not in str(anbima_err):
        st.error(f"**ANBIMA:** {anbima_err}")
    if di_cache_msg:
        st.markdown(f'<div class="cache-warn">⚠️ {di_cache_msg}</div>', unsafe_allow_html=True)

    # ── Ajuste lock pos-16h (SQLite-persistente) ───────────────
    today_str = _brt_today()
    frozen    = hora_brt() >= 16.0

    if frozen and "ajuste_locked" not in st.session_state:
        locked_date = get_meta("ajuste_locked_date")
        if locked_date == today_str:
            locked_json = get_meta("ajuste_locked")
            if locked_json:
                try:
                    st.session_state["ajuste_locked"] = json.loads(locked_json)
                except Exception:
                    pass
        if "ajuste_locked" not in st.session_state and di_data and not di_data.get("from_cache"):
            locked = {t: info.get("ajuste") for t, info in di_data["tickers"].items()}
            st.session_state["ajuste_locked"] = locked
            set_meta("ajuste_locked", json.dumps(locked))
            set_meta("ajuste_locked_date", today_str)

    ajuste_locked    = st.session_state.get("ajuste_locked", {})
    prev_bday_ajuste = get_prev_bday_ajuste()

    # ── Caption de status ──────────────────────────────────────
    _now_brt = datetime.utcfromtimestamp(_time.time()) - timedelta(hours=3)
    parts = [f"🔄 {_now_brt.strftime('%H:%M:%S')} BRT"]
    if frozen:
        parts.append("ajuste bloqueado às 16:00")
    parts.append("cache 5 min · refresh ~10 min")
    st.caption("  ·  ".join(parts))

    st.session_state.setdefault("limiar_bps", LIMIAR_BPS_DEFAULT)

    # ── Abas ──────────────────────────────────────────────────
    tabs = st.tabs([
        "Principal",
        "Primário CVM",
        "Crédito",
        "Ativos",
        "Notícias",
        "Newsletters",
        "Auxiliares ————›",
        "Runs corretora",
        "Calls NTN-B",
        "FRA",
        "NTN-B ANBIMA",
    ])
    with tabs[0]: render_principal(di_data, anbima_df, current_calls, ajuste_locked, prev_bday_ajuste)
    with tabs[1]: render_cvm()
    with tabs[2]: render_credito(anbima_df)
    with tabs[3]: render_ativos()
    with tabs[4]: render_noticias()
    with tabs[5]: render_newsletters()
    with tabs[7]: render_runs(anbima_df)
    with tabs[8]: render_calls(anbima_df, current_calls, save_calls)
    with tabs[9]: render_curva_di(di_data)
    with tabs[10]: render_ntnb_anbima(anbima_df, ref_dt)


# ================================================================
# ABAS DE CONTEUDO
# ================================================================

def render_principal(di, anbima, calls, ajuste_locked, prev_bday_ajuste=None):
    frozen = hora_brt() >= 16.0
    ts_txt = (di or {}).get("timestamp", "—")
    status = " · ajuste bloqueado" if frozen else " · lag ~15 min"
    n = len(anbima) if anbima is not None else 0

    render_briefing_credito(anbima)

    col_di, col_ntnb, col_btn = st.columns([0.94, 1.34, 0.4])

    with col_btn:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        if st.button("Limpar Calls", key="cl_principal_aligned", use_container_width=True):
            for k in st.session_state["calls"]:
                st.session_state["calls"][k] = {}
            save_calls(st.session_state["calls"])
            if "ajuste_locked" in st.session_state:
                del st.session_state["ajuste_locked"]
            set_meta("ajuste_locked_date", "")   # invalida lock persistido no banco
            st.rerun()
        # Atualiza SÓ o DI Futuro: limpa o cache de fetch_b3_di e re-renderiza
        # o fragment (demais caches ficam quentes → só o DI re-busca da B3).
        if st.button("Atualizar DI", key="upd_di_principal", use_container_width=True):
            fetch_b3_di.clear()
            st.rerun(scope="fragment")

    with col_di:
        tickers = january_di_tickers()
        in_pregao = 9.0 <= hora_brt() < 16.5
        rows = ""
        for t in tickers:
            q = (di or {}).get("tickers", {}).get(t, {})
            # Ajuste D-1 OFICIAL — hierarquia:
            #   1) SQLite D-1 (ajuste_oficial do último pregão fechado) — fonte canônica
            #   2) API durante o pregão (prvsDayAdjstmntPric ainda é D-1 antes de 16h30)
            #   3) lock pós-16h (se banco vazio e já capturamos hoje)
            ajuste = (prev_bday_ajuste or {}).get(t)
            if ajuste is None and in_pregao:
                ajuste = q.get("ajuste")           # durante pregão, prvsDay = D-1 confiável
            if ajuste is None and ajuste_locked:
                ajuste = ajuste_locked.get(t)
            ultimo = q.get("ultimo")
            delta  = (ultimo - ajuste) * 100 if (ultimo is not None and ajuste is not None) else float("nan")
            rows += (
                f'<tr>'
                f'<td class="ticker">{t}</td>'
                f'<td class="rate">{fr(ajuste)}</td>'
                f'<td class="hi">{fr(ultimo)}</td>'
                f'<td>{fd(delta)}</td>'
                f'</tr>'
            )
        ajuste_src = "D-1 oficial" if prev_bday_ajuste else ("D-1 intraday" if in_pregao else "D-1 indisp.")
        render_table(
            [("Vértice", ""), ("Ajuste D-1", ""), ("Último", ""), ("Δ bps", "")],
            rows, table_id="table-di",
            title="DI Futuro", meta=f"B3 · {ts_txt} · {ajuste_src}",
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
                dm    = (manha - mtm)   * 100 if (manha is not None and mtm is not None) else float("nan")
                dt    = (tarde - manha) * 100 if (tarde is not None and manha is not None) else float("nan")
                ddia  = (tarde - mtm)   * 100 if (tarde is not None and mtm is not None) else dm
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
            [("Vértice", "left"), ("Duration", ""), ("MTM D-1", ""),
             ("Call M", ""), ("Call T", ""), ("Δ M", ""), ("Δ T", ""), ("Δ Dia", "")],
            rows,
            title="NTN-B",
            meta=f"ANBIMA · {n} títulos",
        )


def render_curva_di(di):
    st.markdown('<div class="aux-tab-banner">📊 Curva DI — DU e FRA calculados</div>', unsafe_allow_html=True)
    if di is None:
        st.warning("Dados B3 indisponíveis.")
        return
    today   = _brt_date()
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
            "Vértice": r["ticker"], "Vencimento": r["vencimento"],
            "DU": du, "Δ DU": dif, "Taxa (%)": r["ultimo"], "FRA (%)": fra,
        })
    df = pd.DataFrame(rows)
    fmt = {
        "Taxa (%)": lambda x: fr(x),
        "FRA (%)":  lambda x: fr(x, 4),
        "Δ DU":     lambda x: str(int(x)) if pd.notna(x) else "—",
    }
    st.dataframe(df.style.format(fmt, na_rep="—"), use_container_width=True,
                 hide_index=True, column_config=get_centralized_config(df))


def render_ntnb_anbima(anbima, ref):
    st.markdown('<div class="aux-tab-banner">📊 NTN-B ANBIMA — arquivo diário completo</div>', unsafe_allow_html=True)
    if anbima is None:
        st.warning("Dados ANBIMA indisponíveis.")
        return
    # T1-A — seletor de janela para percentil histórico
    janela = st.select_slider(
        "Janela histórica (percentil)",
        options=[63, 126, 252],
        value=252,
        format_func=lambda x: {63: "3 meses", 126: "6 meses", 252: "1 ano"}[x],
        key="ntnb_janela",
    )
    st.caption(f"Referência ANBIMA: {ref}  ·  {len(anbima)} NTN-Bs vigentes")
    show   = ["label", "vencimento", "duration"]
    rename = {"label": "Vértice", "vencimento": "Vencimento", "duration": "Duration"}
    for src, dst in [
        ("Tx. Compra", "Tx Compra"), ("Tx. Venda", "Tx Venda"),
        ("tx_ind", "Tx Indicativa"), ("PU", "PU"), ("Desvio padrao", "Desvio Padrão"),
    ]:
        if src in anbima.columns:
            show.append(src)
            rename[src] = dst
    df = anbima[[c for c in show if c in anbima.columns]].copy().rename(columns=rename)
    df["Vencimento"] = pd.to_datetime(df["Vencimento"]).dt.strftime("%Y-%m-%d")
    # T1-B — coluna de percentil (1 query SQLite por vértice, ~10–15 chamadas, aceitável)
    df["Percentil"] = df.apply(
        lambda r: percentil_anbima(r.get("Vértice"), r.get("Tx Indicativa"), n_days=janela),
        axis=1,
    )
    df["Percentil"] = df["Percentil"].apply(lambda p: f"p{p}" if p is not None else "—")
    fmt = {"Duration": lambda x: fr(x)}
    for c in ["Tx Compra", "Tx Venda", "Tx Indicativa"]:
        if c in df.columns:
            fmt[c] = lambda x: fr(x)
    if "PU" in df.columns:
        fmt["PU"] = lambda x: f"{x:,.2f}" if pd.notna(x) else "—"
    st.dataframe(df.style.format(fmt, na_rep="—"), use_container_width=True,
                 hide_index=True, column_config=get_centralized_config(df))
    # T1-C — export do histórico completo
    if st.button("Exportar histórico ANBIMA (.csv)", key="btn_export_anbima"):
        try:
            with _db() as con:
                hist = pd.read_sql_query(
                    "SELECT * FROM anbima_snapshots ORDER BY ref_date DESC, label",
                    con,
                )
            csv_bytes = hist.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()
            st.download_button(
                "Baixar histórico (.csv)", csv_bytes,
                file_name=f"anbima_historico_{_brt_today()}.csv", mime="text/csv",
                key="dl_anbima_hist",
            )
        except Exception as e:
            st.warning(f"Erro ao exportar histórico: {e}")


def render_calls(anbima, calls, save_fn):
    labels = {"manha": "Manhã", "tarde": "Tarde", "fechamento": "Fechamento"}
    sc1, sc2, sc3 = st.columns(3)
    for col, key in zip([sc1, sc2, sc3], ["manha", "tarde", "fechamento"]):
        with col:
            n   = len(calls.get(key, {}))
            tag = "badge-ok" if n else "badge-mt"
            txt = f"✓ {n} títulos" if n else "aguardando"
            st.markdown(f'**{labels[key]}** &nbsp; <span class="{tag}">{txt}</span>',
                        unsafe_allow_html=True)

    st.divider()

    # ── Status do histórico + backup do banco ──────────────────
    with st.expander("💾 Histórico local (SQLite)", expanded=False):
        try:
            with _db() as con:
                n_di_days = con.execute(
                    "SELECT COUNT(DISTINCT brt_date) FROM di_snapshots").fetchone()[0]
                n_anb_days = con.execute(
                    "SELECT COUNT(DISTINCT ref_date) FROM anbima_snapshots").fetchone()[0]
                first_di = con.execute(
                    "SELECT MIN(brt_date) FROM di_snapshots").fetchone()[0]
            st.caption(
                f"DI: **{n_di_days}** dias de snapshots (desde {first_di or '—'})  ·  "
                f"ANBIMA: **{n_anb_days}** dias"
            )
            st.caption(
                "⚠️ No Streamlit Cloud o arquivo é perdido em cada redeploy. "
                "Baixe o backup periodicamente — para restaurar, suba o arquivo no repositório."
            )
            if os.path.exists(DB_FILE):
                with open(DB_FILE, "rb") as fdb:
                    st.download_button(
                        "Baixar backup (.db)", fdb.read(),
                        file_name=f"monitor_macro_{_brt_today()}.db",
                        mime="application/octet-stream", key="db_backup",
                    )
        except Exception as e:
            st.caption(f"Banco indisponível: {e}")

    st.divider()

    # ── Opcao 1: Upload do .xlsx ───────────────────────────────
    st.markdown("**Upload do MTM1.xlsx** — salve o anexo do email e faça upload aqui.")
    uploaded = st.file_uploader(
        "Upload MTM1.xlsx",
        type=["xlsx"],
        key="xlsx_upload",
        label_visibility="collapsed",
    )
    if uploaded is not None:
        if st.button("Aplicar do Excel", key="ap_xlsx", type="primary"):
            parsed = parse_call_xlsx(uploaded.getvalue(), anbima)
            if parsed is None:
                st.error("NTN-B não encontrada no arquivo. Verifique se a aba se chama 'MTM' e a estrutura está correta.")
            else:
                changed = []
                for sess in ("manha", "tarde", "fechamento"):
                    if parsed[sess]:
                        calls[sess] = parsed[sess]
                        changed.append(f"{labels[sess]}: {len(parsed[sess])} títulos")
                if changed:
                    save_fn(calls)
                    st.success("✓ Aplicado — " + " · ".join(changed))
                    st.rerun(scope="fragment")
                else:
                    st.warning("Nenhuma call encontrada para os vencimentos ANBIMA ativos.")

    st.divider()

    # ── Opcao 2: Cola de texto (fallback) ─────────────────────
    with st.expander("Colar range do Excel (alternativa)", expanded=False):
        st.markdown("Cole o range da planilha e clique **Aplicar**.")
        pasted = st.text_area(
            "Range do Excel",
            key="ta_calls",
            height=200,
            label_visibility="collapsed",
            placeholder="Cole o range do Excel aqui (Ctrl+V)...",
        )
        b1, b2 = st.columns([2, 1])
        with b1:
            if st.button("Aplicar Calls (texto)", key="ap_calls", use_container_width=True, type="primary"):
                if not pasted.strip():
                    st.warning("Nenhum texto colado.")
                else:
                    parsed = parse_call_range(pasted, anbima)
                    if parsed is None:
                        st.error("Não foi possível interpretar o range.")
                    else:
                        changed = []
                        for sess in ("manha", "tarde", "fechamento"):
                            if parsed[sess]:
                                calls[sess] = parsed[sess]
                                changed.append(f"{labels[sess]}: {len(parsed[sess])} títulos")
                        if changed:
                            save_fn(calls)
                            st.success("Aplicado — " + " · ".join(changed))
                            st.rerun(scope="fragment")
        with b2:
            if st.button("Limpar tudo", key="cl_calls", use_container_width=True):
                for k in ("manha", "tarde", "fechamento"):
                    calls[k] = {}
                save_fn(calls)
                st.rerun(scope="fragment")

    st.markdown("---")
    render_placar_calls()


# ================================================================
# MAIN
# ================================================================
def _gh_cfg():
    """Lê credenciais do GitHub de st.secrets['github']. Token NUNCA no código."""
    try:
        c = st.secrets["github"]
        if not c.get("token") or not c.get("repo"):
            return None
        return {"token": c["token"], "repo": c["repo"],
                "path": c.get("path", "monitor_macro.db"),
                "branch": c.get("branch", "main")}
    except Exception:
        return None


def _gh_headers(token):
    return {"Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"}


def restore_db_from_github(force=False):
    """Baixa o .db do GitHub. Por padrão só se o local não existir/estiver vazio
    (cenário Streamlit Cloud que apaga o .db no redeploy). force=True sempre baixa."""
    cfg = _gh_cfg()
    if not cfg:
        return False, "sem credenciais em st.secrets['github']"
    if not force and os.path.exists(DB_FILE) and os.path.getsize(DB_FILE) > 0:
        return False, "db local já presente"
    import base64
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}"
    try:
        r = requests.get(url, params={"ref": cfg["branch"]},
                         headers=_gh_headers(cfg["token"]), timeout=30)
        if r.status_code == 404:
            return False, "ainda não há backup no repo"
        r.raise_for_status()
        data = base64.b64decode(r.json().get("content", ""))
        with open(DB_FILE, "wb") as f:
            f.write(data)
        return True, f"db restaurado ({len(data)//1024} KB)"
    except Exception as e:
        return False, str(e)


def backup_db_to_github():
    """Envia o .db local para o GitHub (cria/atualiza o arquivo via contents API)."""
    cfg = _gh_cfg()
    if not cfg:
        return False, "sem credenciais em st.secrets['github']"
    if not os.path.exists(DB_FILE):
        return False, "db local não existe"
    import base64
    with open(DB_FILE, "rb") as f:
        data = f.read()
    url = f"https://api.github.com/repos/{cfg['repo']}/contents/{cfg['path']}"
    h = _gh_headers(cfg["token"])
    try:
        sha = None
        g = requests.get(url, params={"ref": cfg["branch"]}, headers=h, timeout=30)
        if g.status_code == 200:
            sha = g.json().get("sha")
        payload = {"message": f"backup monitor_macro.db {_brt_today()}",
                   "content": base64.b64encode(data).decode(), "branch": cfg["branch"]}
        if sha:
            payload["sha"] = sha
        p = requests.put(url, headers=h, json=payload, timeout=60)
        p.raise_for_status()
        return True, f"backup enviado ({len(data)//1024} KB)"
    except Exception as e:
        return False, str(e)


def main():
    # Restaura o banco do GitHub no boot se o local sumiu (redeploy Streamlit Cloud).
    if "db_restored" not in st.session_state:
        st.session_state["db_restored"] = True
        ok, msg = restore_db_from_github()
        if ok:
            st.session_state["db_restore_msg"] = msg
    init_db()

    if "calls" not in st.session_state:
        st.session_state["calls"] = load_calls()
    current_calls = st.session_state["calls"]

    st.markdown("<div style='margin-top:0rem'></div>", unsafe_allow_html=True)

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
            set_meta("ajuste_locked_date", "")   # invalida lock persistido no banco
            st.rerun()
    with h3:
        st.markdown("<div style='height:23px'></div>", unsafe_allow_html=True)
        st.caption((datetime.utcfromtimestamp(_time.time()) - timedelta(hours=3)).strftime("%H:%M:%S"))

    st.divider()
    render_conteudo_dinamico(current_calls)


# ================================================================
# NOTICIAS
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
     "url": "https://sherwood.news", "site_strategy": "reader",
     "allow_gn": True, "enabled": True},
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

    st.markdown(
        f'<div style="padding-top:4px;padding-bottom:8px">'
        f'<a href="{site_url}" target="_blank" '
        f'style="color:var(--text3);font-size:11px;font-weight:600;text-decoration:none;">'
        f'↗ Abrir em nova aba</a></div>',
        unsafe_allow_html=True,
    )

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
                f"Abra [{site_url}]({site_url}) diretamente."
            )
    elif can_iframe:
        # Site permite embedding direto — iframe nativo
        _components.iframe(site_url, height=760, scrolling=True)
    else:
        # Site bloqueia (X-Frame-Options/CSP) — cadeia: proxy → reader → RSS magazine
        errs = []
        shown = False

        # 1. Proxy server-side (re-escreve HTML)
        with st.spinner(f"Carregando {sel} via proxy server-side…"):
            html_content, err_p = _fetch_site_html(site_url)
        if html_content and len(html_content) > 2000:
            st.caption(
                f"📡 Carregado via proxy server-side  ·  X-Frame-Options contornado  ·  "
                f"links abrem em nova aba"
            )
            _components.html(html_content, height=760, scrolling=True)
            shown = True
        else:
            errs.append(f"Proxy: {err_p or 'conteúdo vazio'}")

        # 2. Reader proxy (Jina)
        if not shown:
            with st.spinner(f"Tentando reader proxy…"):
                html_content, err_r = _fetch_via_reader_proxy(site_url)
            if html_content:
                st.caption(
                    f"📡 Renderizado via reader proxy (Jina AI)  ·  fallback automático  ·  "
                    f"links abrem em nova aba"
                )
                _components.html(html_content, height=760, scrolling=True)
                shown = True
            else:
                errs.append(f"Reader: {err_r}")

        # 3. Fallback final: RSS magazine view (sempre funciona se há RSS)
        if not shown:
            with st.spinner(f"Montando visão RSS…"):
                items, err_rss = fetch_news_feed(
                    src.get("rss_candidates", [src.get("rss", "")]),
                    src.get("url", ""),
                    src.get("allow_gn", True),
                    max_items=20,
                )
            if items:
                st.caption(
                    f"Proxy e reader falharam ({' · '.join(errs)}). "
                    f"Exibindo as últimas {len(items)} matérias via RSS."
                )
                _render_rss_homepage(sel, items, site_url)
                shown = True

        # 4. Tudo falhou
        if not shown:
            st.warning(
                f"**{sel}** indisponível em todas as estratégias. "
                f"Erros: {' · '.join(errs)}. "
                f"Abra [{site_url}]({site_url}) diretamente."
            )
# ================================================================
# NEWSLETTERS
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
        "post_path_prefix": "/p/",
    },
    "TNS Sports": {
        "archive_url":    "https://sports.thenews.com.br/",
        "site_url":       "https://sports.thenews.com.br",
        "rss_candidates": ["https://sports.thenews.com.br/feed","https://sports.thenews.com.br/rss"],
        "exclude_title_keywords": ["inscreva"],
    },
}

_PT_MONTHS = {
    "janeiro":1,"fevereiro":2,"março":3,"marco":3,"abril":4,"maio":5,"junho":6,
    "julho":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"dezembro":12,
    "jan":1,"fev":2,"mar":3,"abr":4,"mai":5,"jun":6,
    "jul":7,"ago":8,"set":9,"out":10,"nov":11,"dez":12,
}

_SKIP_HREFS = {"twitter","instagram","facebook","linkedin","mailto","youtube",
               "tiktok","whatsapp","telegram","pinterest","snapchat","#"}


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
                if items:
                    exc_kw = [k.lower() for k in cfg.get("exclude_title_keywords", [])]
                    if exc_kw:
                        items = [i for i in items if not any(k in i.get("title","").lower() for k in exc_kw)]
                    return items, None
        except Exception: pass

    section_header   = cfg.get("section_header", "")
    skip_tag_links   = cfg.get("skip_tag_links", False)
    min_title_len    = cfg.get("min_title_len", 8)
    post_path_prefix = cfg.get("post_path_prefix", "")

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
        if post_path_prefix and not ph.path.lower().startswith(post_path_prefix): return None, None
        text = a_tag.get_text(strip=True)
        if len(text) < min_title_len: return None, None
        if skip_tag_links:
            path_lower = ph.path.lower()
            if any(seg in path_lower for seg in ("/tag/","/t/","/categoria/","/category/","/topic/","/topico/")):
                return None, None
            if len(text) < 25 and " " not in text: return None, None
        return href, text

    try:
        r = requests.get(archive_url, timeout=15, headers=_BROWSER_HEADERS)
        r.raise_for_status()
        soup, editions, seen_p = _BS(r.text, "html.parser"), [], set()
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
                    editions.append({"url":href,"title":text[:150],"date":_extract_date(href) or _extract_date(text) or ""})
                    if len(editions) >= 10: break
        else:
            for a in soup.find_all("a", href=True):
                href, text = _ok_link(a)
                if not href: continue
                p = urlparse(href).path
                if p in seen_p: continue
                seen_p.add(p)
                editions.append({"url":href,"title":text[:150],"date":_extract_date(href) or _extract_date(text) or ""})
        if not editions:
            return [], "Nenhuma edição encontrada"
        dated   = sorted([e for e in editions if e["date"]], key=lambda x: x["date"], reverse=True)
        undated = [e for e in editions if not e["date"]]
        cutoff  = (date.today() - timedelta(days=90)).strftime("%Y-%m-%d")
        if dated and any(e["date"] >= cutoff for e in dated):
            result = dated + undated
        else:
            result = editions
        exc_kw = [k.lower() for k in cfg.get("exclude_title_keywords", [])]
        if exc_kw:
            result = [e for e in result if not any(k in e.get("title","").lower() for k in exc_kw)]
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
            soup.find("article") or soup.find("main") or
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
    today_str = _brt_date().strftime("%Y-%m-%d")
    h_brt = hora_brt()
    for ed in editions:
        if ed["date"] == today_str: return ed
        if h_brt < 11.0: return editions[0] if editions else None
        break
    return editions[0] if editions else None


def render_newsletters():
    names = list(_NEWSLETTER_SOURCES.keys())

    # Seletor de newsletter (igual ao seletor de fonte de notícias)
    if "nl_sel" not in st.session_state or st.session_state["nl_sel"] not in names:
        st.session_state["nl_sel"] = names[0]

    sel = st.radio(
        "Newsletter",
        names,
        horizontal=True,
        index=names.index(st.session_state["nl_sel"]),
        key="nl_source_sel",
        label_visibility="collapsed",
    )
    st.session_state["nl_sel"] = sel

    cfg = _NEWSLETTER_SOURCES[sel]

    with st.spinner(f"Buscando edições de {sel}…"):
        editions, err_idx = _fetch_nl_index(sel)

    if err_idx and not editions:
        st.error(f"Índice indisponível: {err_idx}")
        st.caption(f"Acesse: [{cfg['archive_url']}]({cfg['archive_url']})")
        return

    latest = _latest_edition(editions)
    if latest:
        st.caption(f"Edição mais recente: {latest['date'] or 'data desconhecida'}")
        st.markdown(
            f'<a href="{latest["url"]}" target="_blank" '
            f'style="color:var(--accent);font-size:13px;font-weight:600;">'
            f'{latest["title"][:120]}</a>',
            unsafe_allow_html=True,
        )
        key_open = f"nl_open_{sel}"
        lbl = "▲ Fechar" if st.session_state.get(key_open, False) else "▼ Ler no dashboard"
        if st.button(lbl, key=f"nl_btn_{sel}", use_container_width=True):
            st.session_state[key_open] = not st.session_state.get(key_open, False)

        if st.session_state.get(key_open, False):
            with st.spinner("Carregando conteúdo…"):
                html, err_c = _fetch_nl_content(latest["url"])
            if err_c:
                st.warning(f"Não foi possível carregar: {err_c}")
                st.markdown(f'[↗ Abrir no site]({latest["url"]})')
            elif html:
                _components.html(
                    f'<!doctype html><html><head><meta charset="utf-8">'
                    f'<style>body{{font-family:"Plus Jakarta Sans",system-ui,sans-serif;'
                    f'font-size:14px;color:#0F172A;line-height:1.65;max-width:900px;'
                    f'margin:0 auto;padding:24px;background:#fff;}}'
                    f'a{{color:#2563EB;}}img{{max-width:100%;height:auto;border-radius:8px;}}'
                    f'h1,h2,h3{{color:#0F172A;}}p{{margin:.5em 0;}}</style></head>'
                    f'<body>{html}</body></html>',
                    height=760, scrolling=True,
                )

    if len(editions) > 1:
        with st.expander("Ver edições anteriores"):
            for ed in editions[1:10]:
                label = f"{ed['date']} — {ed['title'][:60]}" if ed['date'] else ed['title'][:70]
                st.markdown(
                    f'<a href="{ed["url"]}" target="_blank" '
                    f'style="color:var(--text3);font-size:12px;">{label}</a><br>',
                    unsafe_allow_html=True,
                )


# ================================================================
# ATIVOS — WATCHLIST
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
                contracts.append({"ticker": t, "venc": vd, "price": lp if lp else ajuste,
                                   "prev": ajuste, "high": q.get("maxPric"), "low": q.get("minPric"), "oi": oi})
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
            return {"price": fi.last_price, "prev": fi.previous_close,
                    "high": fi.day_high, "low": fi.day_low, "last_ts": "tempo real"}, None
        price = float(hist["Close"].iloc[-1])
        high  = float(hist["High"].iloc[-1])
        low   = float(hist["Low"].iloc[-1])
        last_idx = hist.index[-1]
        try:
            last_ts = last_idx.strftime("%d/%m/%y")
        except Exception:
            last_ts = str(last_idx)[:10]
        prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else price
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
        n_ticker = wc1.text_input("Ticker", key="wl_t")
        n_name   = wc2.text_input("Nome",   key="wl_n")
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
        is_open, mkt_label, mkt_ts = _market_status(g)
        mkt_badge = f'<span class="mkt-open">🟢 {mkt_label}</span>' if is_open \
                    else f'<span class="mkt-closed">🔴 {mkt_label}</span>'
        st.markdown(
            f'<p class="mon-head" style="display:flex;align-items:center;gap:10px;">'
            f'{label} {mkt_badge}<span class="mkt-ts">BRT {mkt_ts}</span></p>',
            unsafe_allow_html=True,
        )
        rows = ""
        last_tses = []
        for asset in assets:
            q, err = _quote_for_asset(asset)
            if q:
                price, prev = q.get("price"), q.get("prev")
                pct, pts = _pct(price, prev), _pts(price, prev)
                high, low = q.get("high"), q.get("low")
                ticker_disp = asset["ticker"].replace(".SA","").replace("=X","")
                ts_disp = q.get("last_ts", "")
                if ts_disp: last_tses.append(ts_disp)
                rows += (
                    f'<tr>'
                    f'<td class="ticker" style="text-align:left">{asset["name"]} <span style="color:var(--text3);font-size:11px">({ticker_disp})</span></td>'
                    f'<td class="hi">{fr(price, 2) if price else "—"}</td>'
                    f'<td>{fd2(pct, 2, "%") if pct is not None else "—"}</td>'
                    f'<td>{fd2(pts, 2) if pts is not None else "—"}</td>'
                    f'<td class="rate">{fr(high, 2) if high else "—"}</td>'
                    f'<td class="rate">{fr(low, 2) if low else "—"}</td>'
                    f'</tr>'
                )
            else:
                rows += (
                    f'<tr><td class="ticker" style="text-align:left">{asset["name"]}</td>'
                    f'<td colspan="5" style="color:var(--text3);font-size:12px">{err or "—"}</td></tr>'
                )
        last_ts_unique = sorted(set(last_tses))
        meta_ts = f"dados de {last_ts_unique[-1]}" if last_ts_unique else "lag ~15 min"
        st.caption(f"🕐 {meta_ts} · cache 5 min")
        render_table(
            [("Ativo","left"),("Preço",""),("Δ %",""),("Δ pts",""),("Máx",""),("Mín","")],
            rows,
        )
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)



# ================================================================
# CRÉDITO ESTRUTURADO — aba (layout mockup E)
# ================================================================
# Radar micro = dados reais (BCB SGS). Demais seções com dados
# ilustrativos até a fonte real ser conectada (ANBIMA deb / FIDC CVM
# / feed de ratings). O fluxo antigo de upload CDI/IPCA/LF foi removido.

# ── FIDC: informe mensal (dados abertos CVM) ────────────────────
# Estrutura pós-2023: zip com vários CSVs (inf_mensal_fidc_tab_I … tab_X).
# Layout muda; por isso o parser é por NOME de coluna (nunca por offset)
# e há um inspetor que mostra a estrutura real do arquivo carregado.
_FIDC_INF_URL = ("https://dados.cvm.gov.br/dados/FIDC/DOC/INF_MENSAL/DADOS/"
                 "inf_mensal_fidc_{ym}.zip")


def _fidc_default_ym() -> str:
    """YYYYMM provável de já estar publicado (mês anterior ao corrente em BRT)."""
    d = _brt_date()
    y, m = d.year, d.month - 1
    if m == 0:
        y, m = y - 1, 12
    return f"{y}{m:02d}"


@st.cache_data(ttl=21600, show_spinner=False)
def fetch_fidc_informe(ym: str):
    """Baixa o informe mensal FIDC (zip) do mês YYYYMM. Roda na máquina do
    usuário (rede completa). Retorna ({nome_csv: DataFrame}, erro)."""
    url = _FIDC_INF_URL.format(ym=ym)
    try:
        r = requests.get(url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 404:
            return None, f"sem arquivo publicado para {ym}"
        r.raise_for_status()
        tables = {}
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            for name in z.namelist():
                if not name.lower().endswith(".csv"):
                    continue
                try:
                    with z.open(name) as f:
                        df = pd.read_csv(f, sep=";", encoding="latin-1", dtype=str,
                                         on_bad_lines="skip", low_memory=False)
                    df.columns = [c.strip() for c in df.columns]
                    tables[name] = df
                except Exception:
                    continue
        if not tables:
            return None, "zip sem CSVs legíveis"
        return tables, None
    except Exception as e:
        return None, str(e)


def _fidc_fund_table(tables):
    """Escolhe o CSV de nível de fundo: tem CNPJ_FUNDO e alguma coluna de PL."""
    if not tables:
        return None, None
    for name, df in tables.items():
        cols = set(df.columns)
        if "CNPJ_FUNDO" in cols and any("PATRIM_LIQ" in c for c in cols):
            return name, df
    for name, df in tables.items():
        if "CNPJ_FUNDO" in df.columns:
            return name, df
    return None, None


def _fidc_to_float(s):
    """Converte string numérica CVM (vírgula decimal) em float; None se falhar."""
    if s is None:
        return None
    s = str(s).strip()
    if not s or s.lower() in ("nan", "none", "-"):
        return None
    try:
        return float(s.replace(".", "").replace(",", ".")) if ("," in s and "." in s) \
            else float(s.replace(",", "."))
    except ValueError:
        return None


def _fidc_fmt_mm(v):
    """Float → 'R$ X,X mm' (milhões). '—' se None."""
    f = _fidc_to_float(v)
    if f is None:
        return "—"
    return f"{f/1e6:,.1f}".replace(",", "·").replace(".", ",").replace("·", ".")


# ── ANBIMA: mercado secundário de debêntures (arquivo público diário) ──
# Layout real (dbYYMMDD.txt, latin-1, separador '@', 15 campos):
#  0 Código · 1 Nome · 2 Repac./Venc · 3 Índice/Correção · 4 Taxa Compra
#  5 Taxa Venda · 6 Taxa Indicativa · 7 Desvio · 8 Int.Mín · 9 Int.Máx
#  10 PU · 11 %PU Par/VNE · 12 Duration(du) · 13 %Reune · 14 Ref NTN-B
_ANBIMA_DEB_URL = ("https://www.anbima.com.br/informacoes/merc-sec-debentures/"
                   "arqs/db{ymd}.txt")


def _anb_num(s):
    """Número ANBIMA (vírgula decimal). '--'/'N/D'/'' → None."""
    if s is None:
        return None
    s = str(s).strip()
    if not s or s.upper() in ("--", "N/D", "ND", "NAN"):
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_anbima_debentures(ymd: str):
    """Baixa e parseia o arquivo do secundário de debêntures (db{ymd}.txt).
    ymd = AAMMDD. Roda na máquina do usuário. Retorna (DataFrame, erro)."""
    url = _ANBIMA_DEB_URL.format(ymd=ymd)
    try:
        r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code != 200 or not r.content:
            return None, f"sem arquivo {ymd}"
        text = r.content.decode("latin-1", errors="replace")
        lines = [ln for ln in text.splitlines() if "@" in ln]
        if len(lines) < 2:
            return None, "formato inesperado"
        recs = []
        for ln in lines[1:]:                       # lines[0] = cabeçalho
            f = ln.split("@")
            if len(f) < 13 or not f[0].strip():
                continue
            recs.append({
                "codigo": f[0].strip(), "nome": f[1].strip(),
                "vencimento": f[2].strip(), "indice": f[3].strip(),
                "compra": _anb_num(f[4]), "venda": _anb_num(f[5]),
                "indicativa": _anb_num(f[6]),
                "duration_du": _anb_num(f[12]) if len(f) > 12 else None,
            })
        if not recs:
            return None, "sem registros"
        return pd.DataFrame(recs), None
    except Exception as e:
        return None, str(e)


def _anbima_deb_load_latest(max_back: int = 6):
    """Tenta o arquivo do último dia útil disponível (hoje → D-n). Cacheado."""
    d = _brt_date()
    for _ in range(max_back + 1):
        if d.weekday() < 5:                        # seg–sex (feriado cai no fetch)
            ymd = d.strftime("%y%m%d")
            df, _err = fetch_anbima_debentures(ymd)
            if df is not None and len(df):
                return df, ymd
        d -= timedelta(days=1)
    return None, None


def _anb_grupo(indice: str) -> str:
    s = (indice or "").strip().upper()
    if s.startswith("DI"):
        return "CDI+"
    if "IPCA" in s:
        return "IPCA+"
    return "Outros"


# ================================================================
# RUNS DE CORRETORA — upload (Deb CDI+ / Deb IPCA+ / LF)
# ================================================================
# Parser por NOME de coluna (validado contra arquivos reais 15/06/26).
# Cabeçalho na linha onde a col 1 = "Ativo" (deb) ou "Tipo" (LF).
# Salvo por data no SQLite (credito_runs) → estudo de movimentação D/D.
_RUN_LABELS = {"CDI": "Debêntures CDI+", "IPCA": "Debêntures IPCA+",
               "LF": "Instituições Financeiras (LF)"}


def _run_norm(s):
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", s).strip().lower()


def _run_to_float(x):
    if x is None:
        return None
    s = str(x).strip()
    if not s or s in ("-", "--", "-/-", "nan", "N/D"):
        return None
    if "(" in s:                       # '40,00 (PU)' não é taxa
        return None
    s = s.replace("%", "").replace(" ", "")
    try:
        return (float(s.replace(".", "").replace(",", "."))
                if ("," in s and "." in s) else float(s.replace(",", ".")))
    except ValueError:
        return None


def parse_run_xlsx(file_bytes):
    """Retorna (run_type, run_date_iso, [ativos]). (None, None, []) se não reconhecer."""
    try:
        df = pd.read_excel(io.BytesIO(file_bytes), header=None, engine="openpyxl")
    except Exception:
        return None, None, []
    hr = hdr = None
    for r in range(min(12, len(df))):
        vals = [_run_norm(df.iat[r, c]) for c in range(df.shape[1])]
        if "ativo" in vals or "tipo" in vals:
            hr, hdr = r, vals
            break
    if hr is None:
        return None, None, []
    colmap = {h: i for i, h in enumerate(hdr) if h and h != "nan"}

    rdate = None
    for r in range(min(4, len(df))):
        for c in range(df.shape[1]):
            v = df.iat[r, c]
            if isinstance(v, (pd.Timestamp, datetime)):
                rdate = pd.Timestamp(v).date().isoformat()
                break
        if rdate:
            break

    if "tipo" in colmap and "ativo" not in colmap:
        rtype = "LF"
    elif "spread over b" in colmap:
        rtype = "IPCA"
    elif "lote padrao" in colmap or "negocio" in colmap:
        rtype = "CDI"
    else:
        rtype = "CDI" if "ativo" in colmap else None

    def gc(*names):
        for n in names:
            if n in colmap:
                return colmap[n]
        return None

    ic = {"ativo": gc("ativo"), "tipo": gc("tipo"), "emissor": gc("emissor"),
          "venc": gc("vencimento", "vencimento/call"), "idx": gc("indexador"),
          "compra": gc("compra (%)", "compra"), "venda": gc("venda (%)", "venda"),
          "anbima": gc("anbima"), "dur": gc("duration (anos)", "duration"),
          "rating": gc("rating")}

    def cell(r, k):
        i = ic[k]
        return df.iat[r, i] if i is not None else None

    def cdate(v):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        if isinstance(v, (pd.Timestamp, datetime)):
            return pd.Timestamp(v).date().isoformat()
        try:
            return pd.to_datetime(v).date().isoformat()
        except Exception:
            return None

    def s_or_none(r, k):
        v = cell(r, k)
        if v is None or _run_norm(v) in ("nan", "-", ""):
            return None
        return str(v).strip()

    out = []
    for r in range(hr + 1, len(df)):
        keyv = cell(r, "ativo") if ic["ativo"] is not None else cell(r, "tipo")
        if keyv is None or _run_norm(keyv) in ("nan", "ativo", "tipo", ""):
            continue
        comp = _run_to_float(cell(r, "compra"))
        vend = _run_to_float(cell(r, "venda"))
        if comp is None and vend is None:
            continue
        out.append({
            "ativo": s_or_none(r, "ativo"), "tipo": s_or_none(r, "tipo"),
            "emissor": s_or_none(r, "emissor"), "vencimento": cdate(cell(r, "venc")),
            "indexador": s_or_none(r, "idx"), "compra": comp, "venda": vend,
            "anbima": _run_to_float(cell(r, "anbima")),
            "duration": _run_to_float(cell(r, "dur")), "rating": s_or_none(r, "rating"),
        })
    return rtype, rdate, out


def save_run(rtype, run_date, rows):
    """Persiste um run por (data, tipo) no SQLite. Substitui o do mesmo dia/tipo."""
    if not rows:
        return 0
    ts = int(_time.time())
    recs = []
    for a in rows:
        key = a.get("ativo") or f'{a.get("tipo","")}|{a.get("emissor","")}|{a.get("vencimento","")}'
        recs.append((run_date, rtype, ts, key, a.get("emissor"), a.get("tipo"),
                     a.get("vencimento"), a.get("indexador"), a.get("compra"),
                     a.get("venda"), a.get("anbima"), a.get("duration"),
                     a.get("rating"), None, None))
    try:
        with _db() as con:
            con.execute("DELETE FROM credito_runs WHERE brt_date=? AND run_type=?",
                        (run_date, rtype))
            con.executemany(
                "INSERT OR REPLACE INTO credito_runs"
                " (brt_date, run_type, saved_at, ativo, emissor, tipo, vencimento,"
                "  indexador, compra, venda, anbima, duration, rating, secao, spread_b)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", recs)
        return len(recs)
    except Exception:
        return 0


def load_run_dates(rtype):
    try:
        with _db() as con:
            r = con.execute("SELECT DISTINCT brt_date FROM credito_runs WHERE run_type=?"
                            " ORDER BY brt_date DESC", (rtype,)).fetchall()
        return [x[0] for x in r if x[0]]
    except Exception:
        return []


# ── Periodicidade de análise (dias úteis para trás) ──────────────
PERIODO_OPCOES = [
    ("1 dia útil",   1),
    ("5 dias úteis", 5),
    ("10 dias úteis", 10),
    ("20 dias úteis", 20),
]
PERIODO_DEFAULT = 1


def get_periodo_du(key: str) -> int:
    """Lê a periodicidade (dias úteis) selecionada para um bloco; default 1."""
    return int(st.session_state.get(f"periodo_du_{key}", PERIODO_DEFAULT))


def render_periodo_toggle(key: str):
    """Renderiza um seletor de periodicidade (1/5/10/20 du) para um bloco.
    Persiste em st.session_state[f'periodo_du_{key}']."""
    atual = get_periodo_du(key)
    labels = [lbl for lbl, _ in PERIODO_OPCOES]
    vals   = [v for _, v in PERIODO_OPCOES]
    try:
        idx = vals.index(atual)
    except ValueError:
        idx = vals.index(PERIODO_DEFAULT)
    escolha = st.radio(
        "Periodicidade (dias úteis)", labels, index=idx,
        horizontal=True, key=f"periodo_radio_{key}",
        label_visibility="collapsed",
    )
    st.session_state[f"periodo_du_{key}"] = dict(zip(labels, vals))[escolha]
    return st.session_state[f"periodo_du_{key}"]


def _target_date_n_du_back(ref: date, n_du: int) -> date:
    """Retorna a data n dias úteis antes de ref (usando calendário ANBIMA)."""
    try:
        d64 = np.busday_offset(
            np.datetime64(ref, "D"), -int(n_du), roll="backward",
            busdaycal=_BUSDAYCAL,
        )
        return d64.astype("datetime64[D]").astype(date)
    except Exception:
        d = ref
        steps = n_du
        while steps > 0:
            d -= timedelta(days=1)
            if is_bday(d):
                steps -= 1
        return d


def pick_prev_run_date(dates_desc, n_du: int):
    """Dada lista de datas (str ISO) ordenada desc e nº de dias úteis para trás,
    escolhe a data de run de comparação: a mais recente <= alvo (ref - n_du).
    Fallback: a mais antiga disponível. Retorna str ou None."""
    if not dates_desc:
        return None
    try:
        ref = date.fromisoformat(dates_desc[0])
    except Exception:
        # se não-ISO, cai no comportamento por índice
        idx = min(n_du, len(dates_desc) - 1)
        return dates_desc[idx] if len(dates_desc) > 1 else None
    alvo = _target_date_n_du_back(ref, n_du)
    alvo_iso = alvo.isoformat()
    # dates_desc está em ordem decrescente; pega a 1ª data <= alvo
    for d in dates_desc[1:]:
        if d <= alvo_iso:
            return d
    # nenhuma <= alvo → usa a mais antiga disponível (que ainda seja < ref)
    candidatas = [d for d in dates_desc[1:] if d < dates_desc[0]]
    return candidatas[-1] if candidatas else None



def load_run_on(rtype, brt_date):
    try:
        with _db() as con:
            rows = con.execute(
                "SELECT ativo, emissor, tipo, vencimento, indexador, compra, venda,"
                " anbima, duration, rating FROM credito_runs WHERE run_type=? AND brt_date=?",
                (rtype, brt_date)).fetchall()
        if not rows:
            return None
        return pd.DataFrame(rows, columns=["ativo", "emissor", "tipo", "vencimento",
                                           "indexador", "compra", "venda", "anbima",
                                           "duration", "rating"])
    except Exception:
        return None


def compute_run_premio(rtype):
    """Prêmio (bps) do run mais recente: mid (compra/venda) − Anbima. Só deb."""
    dates = load_run_dates(rtype)
    if not dates:
        return None
    df = load_run_on(rtype, dates[0])
    if df is None or "anbima" not in df.columns:
        return None
    d = df.copy()
    d["mid"] = d[["compra", "venda"]].mean(axis=1)
    # T4 — exige bid (compra) e ask (venda) não-nulos na call
    d = d.dropna(subset=["compra", "venda", "anbima"])
    if d.empty:
        return None
    d["premio_bps"] = (d["mid"] - d["anbima"]) * 100
    return {"date": dates[0], "df": d}


def compute_run_movement(rtype):
    """Movimentação D/D: mid do run mais recente vs run anterior, por ativo."""
    dates = load_run_dates(rtype)
    if len(dates) < 2:
        return None
    cur, prev = load_run_on(rtype, dates[0]), load_run_on(rtype, dates[1])
    if cur is None or prev is None:
        return None
    cur = cur.copy(); prev = prev.copy()
    cur["mid"] = cur[["compra", "venda"]].mean(axis=1)
    prev["mid_p"] = prev[["compra", "venda"]].mean(axis=1)
    prev["compra_p"] = prev["compra"]
    prev["venda_p"]  = prev["venda"]
    cur["k"] = cur["ativo"].astype(str)
    prev["k"] = prev["ativo"].astype(str)
    j = cur.merge(prev[["k", "mid_p", "compra_p", "venda_p"]], on="k",
                  how="inner").dropna(subset=["mid", "mid_p"])
    # T4 — exige bid (compra) e ask (venda) não-nulos nos DOIS runs
    j = j[j["compra"].notna() & j["venda"].notna() &
          j["compra_p"].notna() & j["venda_p"].notna()]
    if j.empty:
        return None
    j["delta_bps"] = (j["mid"] - j["mid_p"]) * 100
    return {"cur": dates[0], "prev": dates[1], "df": j}


def _compute_top_movers(run_type, n_du: int = 1):
    """Top movers D/D: Δ bps (CDI) ou Δ SOB (IPCA) entre o run mais recente e o
    run de n_du dias úteis atrás (default 1)."""
    dates = load_run_dates(run_type)
    if len(dates) < 2:
        return None
    prev_date = pick_prev_run_date(dates, n_du)
    if prev_date is None:
        return None
    df_hoje = load_run_on(run_type, dates[0])
    df_prev  = load_run_on(run_type, prev_date)
    if df_hoje is None or df_prev is None:
        return None
    df_hoje = df_hoje.copy()
    df_prev  = df_prev.copy()
    df_hoje["mid"]   = df_hoje[["compra", "venda"]].mean(axis=1)
    df_prev["mid_p"] = df_prev[["compra", "venda"]].mean(axis=1)
    merged = df_hoje.merge(
        df_prev[["ativo", "mid_p", "anbima", "compra", "venda"]].rename(
            columns={"anbima": "anbima_p", "compra": "compra_p", "venda": "venda_p"}),
        on="ativo", how="inner",
    )
    merged = merged.dropna(subset=["mid", "mid_p"])
    # T4 — exige bid (compra) e ask (venda) não-nulos nos DOIS runs
    merged = merged[
        merged["compra"].notna() & merged["venda"].notna() &
        merged["compra_p"].notna() & merged["venda_p"].notna()
    ]
    if merged.empty:
        return None
    if run_type == "CDI":
        merged["delta"] = (merged["mid"] - merged["mid_p"]) * 100
    else:  # IPCA — variação do spread over NTN-B
        sob_hoje = (merged["mid"]   - merged["anbima"])   * 100
        sob_prev = (merged["mid_p"] - merged["anbima_p"]) * 100
        merged["delta"] = sob_hoje - sob_prev
    merged["_abs"] = merged["delta"].abs()
    ab = merged[merged["delta"] > 0].sort_values("_abs", ascending=False).head(15)
    fe = merged[merged["delta"] < 0].sort_values("_abs", ascending=False).head(15)
    return {
        "data_hoje": dates[0],
        "data_prev": prev_date,
        "abertura":  ab.reset_index(drop=True),
        "fechamento": fe.reset_index(drop=True),
        "n_total": len(merged),
    }


def render_runs(anbima_df):
    st.markdown('<p class="mon-sub">Suba os runs de corretora. Parsing por nome de coluna; '
                'cada run é salvo por data no banco e alimenta o estudo de movimentação na aba '
                '<b>Crédito</b>. Subir o run do mesmo tipo/dia substitui o anterior.</p>',
                unsafe_allow_html=True)

    cols = st.columns(3)
    for col, rt in zip(cols, ("CDI", "IPCA", "LF")):
        with col:
            dates = load_run_dates(rt)
            status = (f'<span class="badge-ok">✓ {dates[0]}</span>' if dates
                      else '<span class="badge-mt">aguardando</span>')
            st.markdown(f"**{_RUN_LABELS[rt]}** &nbsp; {status}", unsafe_allow_html=True)
            up = st.file_uploader(f"xlsx {rt}", type=["xlsx"], key=f"run_up_{rt}",
                                  label_visibility="collapsed")
            if up is not None and st.button(f"Aplicar {rt}", key=f"run_ap_{rt}",
                                            type="primary", use_container_width=True):
                detected, rdate, rows = parse_run_xlsx(up.getvalue())
                if detected is None or not rows:
                    st.error("Arquivo não reconhecido como run.")
                else:
                    if detected != rt:
                        st.warning(f"Detectei **{_RUN_LABELS[detected]}** — salvando como tal.")
                    n = save_run(detected, rdate or _brt_today(), rows)
                    st.success(f"✓ {n} ativos · run {rdate or _brt_today()} ({detected}).")
                    st.rerun(scope="fragment")

    st.divider()

    for rt in ("CDI", "IPCA", "LF"):
        dates = load_run_dates(rt)
        if not dates:
            continue
        df = load_run_on(rt, dates[0])
        if df is None:
            continue
        st.markdown(f'<p class="mon-head">{_RUN_LABELS[rt]} — run {dates[0]} · {len(df)} ativos</p>',
                    unsafe_allow_html=True)
        rows_html = []
        for _, a in df.iterrows():
            ident = a["ativo"] or a["tipo"] or "—"
            venc = (a["vencimento"] or "")[:7]
            extra = (f'<td class="hi">{fr(a["anbima"])}</td><td class="dur">{fr(a["duration"])}</td>'
                     if rt != "LF" else "")
            rows_html.append(
                f'<tr><td class="ticker" style="text-align:left">{ident}</td>'
                f'<td style="text-align:left;font-size:11px;color:var(--text3)">{(a["emissor"] or "")[:26]}</td>'
                f'<td>{venc}</td>'
                f'<td class="rate">{fr(a["compra"])}</td>'
                f'<td class="rate">{fr(a["venda"])}</td>'
                f'{extra}'
                f'<td style="font-size:11px">{a["rating"] or "—"}</td></tr>')
        hdrs = [("Ativo", "left"), ("Emissor", "left"), ("Vencto", ""),
                ("Compra", ""), ("Venda", "")]
        if rt != "LF":
            hdrs += [("Anbima", ""), ("Dur", "")]
        hdrs += [("Rating", "")]
        render_collapsible_table(hdrs, rows_html, key=f"run_prev_{rt}", n=4,
                                 title=f"Run {rt}", meta=dates[0])

    st.divider()
    with st.expander("☁️ Persistência do banco no GitHub (backup / restore)"):
        cfg = _gh_cfg()
        if not cfg:
            st.caption("Não configurado. Crie `.streamlit/secrets.toml` (e o secret no "
                       "Streamlit Cloud) com:")
            st.code('[github]\ntoken = "github_pat_…"   # NUNCA no app.py\n'
                    'repo = "bmarinotti/Dashboard"\npath = "monitor_macro.db"\nbranch = "main"',
                    language="toml")
            st.caption("Garanta que `.streamlit/secrets.toml` está no `.gitignore`. "
                       "O token só é lido de st.secrets — nunca fica no código.")
        else:
            st.caption(f"Repo `{cfg['repo']}` · arquivo `{cfg['path']}` · branch `{cfg['branch']}`. "
                       "No boot o banco é restaurado automaticamente se sumir (redeploy).")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("⬆️ Backup agora → GitHub", use_container_width=True, type="primary"):
                    ok, msg = backup_db_to_github()
                    (st.success if ok else st.error)(msg)
            with b2:
                if st.button("⬇️ Restaurar do GitHub", use_container_width=True):
                    ok, msg = restore_db_from_github(force=True)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun(scope="fragment")


def render_credito(anbima_df):
    """Aba Crédito — spreads secundário, runs e radar micro de lastros."""
    _cr_agenda()
    _cr_kpis()
    _cr_top_movers()

    col_radar, col_rating = st.columns([1.45, 1], gap="small")
    with col_radar:
        _cr_radar_micro_card()
    with col_rating:
        _cr_rating_actions()

    with st.expander("Watchlist FIDC", expanded=False):
        _cr_watchlist_fidc()

    with st.expander("Debêntures — secundário ANBIMA", expanded=False):
        _cr_spreads_segmento()

    st.markdown(
        '<p class="cred-src"><b>Fontes:</b> radar micro = BCB SGS (real) · debêntures secundário + '
        'KPIs CDI+/IPCA+ = ANBIMA (real) · prêmio, movers D/D = seus runs de corretora (real) · '
        'watchlist FIDC = informe mensal CVM (real).</p>',
        unsafe_allow_html=True,
    )


def _cr_card_open(title, meta_html):
    return (f'<div class="table-card"><div class="table-card-header">'
            f'<span class="table-card-title">{title}</span>{meta_html}</div>')


_CR_ILLUS = '<span class="cred-illus">ilustrativo</span>'


def _cr_agenda():
    """Agenda macro DCM 2026 — BC, inflação e atividade."""
    today = _brt_date()

    _COPOM    = [date(2026,1,29), date(2026,3,19), date(2026,5,7),
                 date(2026,6,17), date(2026,7,30), date(2026,9,17),
                 date(2026,11,5), date(2026,12,10)]
    _ATA      = [date(2026,2,6),  date(2026,3,27), date(2026,5,15),
                 date(2026,6,26), date(2026,8,7),  date(2026,9,25),
                 date(2026,11,13), date(2026,12,18)]
    _FOMC     = [date(2026,1,29), date(2026,3,19), date(2026,5,7),
                 date(2026,6,17), date(2026,7,30), date(2026,9,16),
                 date(2026,10,29), date(2026,12,10)]
    _IPCA     = [date(2026,1,14), date(2026,2,10), date(2026,3,12),
                 date(2026,4,9),  date(2026,5,12), date(2026,6,9),
                 date(2026,7,9),  date(2026,8,11), date(2026,9,10),
                 date(2026,10,8), date(2026,11,10), date(2026,12,10)]
    _IPCA15   = [date(2026,1,23), date(2026,2,20), date(2026,3,20),
                 date(2026,4,24), date(2026,5,22), date(2026,6,23),
                 date(2026,7,24), date(2026,8,21), date(2026,9,24),
                 date(2026,10,22), date(2026,11,20), date(2026,12,18)]
    _IGPM     = [date(2026,1,30), date(2026,2,27), date(2026,3,31),
                 date(2026,4,30), date(2026,5,29), date(2026,6,30),
                 date(2026,7,31), date(2026,8,31), date(2026,9,30),
                 date(2026,10,30), date(2026,11,30), date(2026,12,30)]
    # INCC-M (FGV) — índice de custo da construção, relevante p/ CRI e incorporação
    _INCC     = [date(2026,1,29), date(2026,2,26), date(2026,3,30),
                 date(2026,4,29), date(2026,5,28), date(2026,6,29),
                 date(2026,7,30), date(2026,8,28), date(2026,9,29),
                 date(2026,10,29), date(2026,11,27), date(2026,12,29)]
    _PIB      = [date(2026,5,29), date(2026,8,28), date(2026,11,27)]
    _RTN      = [date(2026,1,29), date(2026,2,26), date(2026,3,26),
                 date(2026,4,30), date(2026,5,29), date(2026,6,25),
                 date(2026,7,30), date(2026,8,27), date(2026,9,25),
                 date(2026,10,29), date(2026,11,26), date(2026,12,17)]

    def _next(cal, label, evento, cat):
        for d in cal:
            if d >= today:
                dias = (d - today).days
                hot  = "hot" if dias <= 3 else ""
                dm   = "HOJE" if dias == 0 else ("AMANHÃ" if dias == 1 else f"+{dias}d")
                return (d, hot, cat, f"{label} · {d:%d/%m}", evento, dm)
        return None

    candidates = [
        _next(_COPOM,  "Copom",       "decisão Selic",     ""),
        _next(_ATA,    "Ata Copom",   "ata da reunião",    ""),
        _next(_FOMC,   "FOMC",        "decisão FFR",       ""),
        _next(_IPCA,   "IPCA",        "IBGE · inflação",   "inf"),
        _next(_IPCA15, "IPCA-15",     "IBGE · prévia",     "inf"),
        _next(_IGPM,   "IGP-M",       "FGV · inflação",    "inf"),
        _next(_INCC,   "INCC-M",      "FGV · construção",  "inf"),
        _next(_PIB,    "PIB",         "IBGE · crescimento","act"),
        _next(_RTN,    "Res. Primário","Tesouro · fiscal", "act"),
    ]
    events = sorted([e for e in candidates if e], key=lambda x: x[0])

    items = ""
    for _d, hot, cat, d_lbl, evento, meta in events[:6]:
        cls = (hot + " " + cat).strip()
        items += (f'<div class="cr-agitem {cls}"><div class="d">{d_lbl}</div>'
                  f'<div class="e">{evento}</div><div class="m">{meta}</div></div>')

    if not items:
        items = '<div class="cr-agitem"><div class="d">—</div><div class="e">sem eventos 2026</div></div>'

    st.markdown(
        f'<p class="mon-head" style="margin:8px 0 4px">Agenda macro '
        f'<span class="table-card-meta" style="color:var(--green)">'
        f'</span></p>'
        f'<div class="cr-agstrip">{items}</div>',
        unsafe_allow_html=True,
    )


def _cr_kpi_card(label, value, sub, real):
    note = "" if real else f' {_CR_ILLUS}'
    vcol = ""
    if isinstance(value, str) and value[:1] == "+":
        vcol = " style='color:var(--green)'"
    elif isinstance(value, str) and value[:1] in ("−", "-"):
        vcol = " style='color:var(--red)'"
    return (f'<div class="cr-kpi"><div class="l">{label}{note}</div>'
            f'<div class="v"{vcol}>{value}</div><div class="s cr-fl">{sub}</div></div>')


def _cr_kpis():
    """Taxa indicativa média por classe. Deb CDI+/IPCA+ = ANBIMA real; CRI/CRA = ilustrativo."""
    cdi_txt = ipca_txt = None
    cdi_sub = ipca_sub = "sem dados"
    cdi_src = ipca_src = None
    ipca_label = "Deb IPCA+ · indicativa méd"

    # Calls primeiro (runs de corretora)
    for rt, is_cdi in (("CDI", True), ("IPCA", False)):
        dates = load_run_dates(rt)
        if dates:
            run_df = load_run_on(rt, dates[0])
            if run_df is not None:
                run_df = run_df.copy()
                run_df["mid"] = run_df[["compra", "venda"]].mean(axis=1)
                if is_cdi:
                    mid_ok = run_df.dropna(subset=["mid"])
                    if len(mid_ok):
                        cdi_txt = f"DI + {fr(mid_ok['mid'].mean(), 2)}%"
                        cdi_sub = f"{len(mid_ok)} papéis · calls {dates[0]}"
                        cdi_src = "calls"
                else:
                    sob_ok = run_df.dropna(subset=["mid", "anbima"])
                    if len(sob_ok):
                        sob_ok = sob_ok.copy()
                        sob_ok["sob"] = (sob_ok["mid"] - sob_ok["anbima"]) * 100
                        mid_val  = sob_ok["mid"].mean()
                        sob_mean = sob_ok["sob"].mean()
                        ipca_txt = f"IPCA + {fr(mid_val, 2)}%"
                        ipca_sub = f"{sob_mean:+.0f} bps over B · {len(sob_ok)} papéis · {dates[0]}"
                        ipca_src = "calls"
                        ipca_label = "Deb IPCA+ · indicativa méd"
                    else:
                        mid_ok = run_df.dropna(subset=["mid"])
                        if len(mid_ok):
                            ipca_txt = f"IPCA + {fr(mid_ok['mid'].mean(), 2)}%"
                            ipca_sub = f"{len(mid_ok)} papéis · {dates[0]}"
                            ipca_src = "calls"

    # Fallback ANBIMA
    df, ymd = _anbima_deb_load_latest()
    if df is not None:
        up = df["indice"].fillna("").str.upper()
        if cdi_txt is None:
            cdi = df.loc[up.str.startswith("DI"), "indicativa"].dropna()
            if len(cdi):
                cdi_txt = f"DI + {fr(cdi.mean(), 2)}%"
                cdi_sub = f"{len(cdi)} papéis · méd. ANBIMA"
                cdi_src = "anbima"
        if ipca_txt is None:
            ipca = df.loc[up.str.contains("IPCA"), "indicativa"].dropna()
            if len(ipca):
                ipca_txt = f"IPCA + {fr(ipca.mean(), 2)}%"
                ipca_sub = f"{len(ipca)} papéis · méd. ANBIMA"
                ipca_src = "anbima"

    src_parts = []
    if cdi_src == "calls" or ipca_src == "calls":
        src_parts.append("Calls: Ativa")
    if cdi_src == "anbima" or ipca_src == "anbima":
        src_parts.append(f"ANBIMA db{ymd}" if ymd else "ANBIMA")
    src = " + ".join(src_parts) if src_parts else "—"

    # ── Prêmio s/ ANBIMA + Movimentação D/D (dos runs de corretora) ──
    prem_dfs = []
    for rt in ("CDI", "IPCA"):
        r = compute_run_premio(rt)
        if r is not None:
            prem_dfs.append(r["df"][["ativo", "premio_bps"]])
    if prem_dfs:
        allp = pd.concat(prem_dfs, ignore_index=True)
        ptop = allp.sort_values("premio_bps", ascending=False).iloc[0]
        prem_val = f"{allp['premio_bps'].mean():+.0f} bps".replace("-", "−")
        prem_sub = f"top {ptop['ativo']} {ptop['premio_bps']:+.0f}".replace("-", "−")
        prem_real = True
    else:
        prem_val, prem_sub, prem_real = "—", "suba um run", False

    mv_dfs = []
    for rt in ("CDI", "IPCA"):
        m = compute_run_movement(rt)
        if m is not None:
            mv_dfs.append(m["df"][["ativo", "delta_bps"]])
    if mv_dfs:
        allm = pd.concat(mv_dfs, ignore_index=True)
        ab = allm.sort_values("delta_bps", ascending=False).iloc[0]
        fe = allm.sort_values("delta_bps").iloc[0]
        ab_txt = f"{ab['ativo']} {ab['delta_bps']:+.0f} bps".replace("-", "−")
        fe_txt = f"{fe['ativo']} {fe['delta_bps']:+.0f} bps".replace("-", "−")
        ab_color = "var(--green)" if ab["delta_bps"] > 0 else ("var(--red)" if ab["delta_bps"] < 0 else "var(--text2)")
        fe_color = "var(--green)" if fe["delta_bps"] > 0 else ("var(--red)" if fe["delta_bps"] < 0 else "var(--text2)")
        mv_card_html = (
            f'<div class="cr-kpi">'
            f'<div class="l">Mov. D/D · abertura / fechamento</div>'
            f'<div style="display:flex;flex-direction:column;gap:5px;margin-top:6px">'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:13px;'
            f'font-weight:600;color:{ab_color}">↑ {ab_txt}</div>'
            f'<div style="font-family:\'JetBrains Mono\',monospace;font-size:13px;'
            f'font-weight:600;color:{fe_color}">↓ {fe_txt}</div>'
            f'</div></div>'
        )
    else:
        mv_card_html = _cr_kpi_card("Mov. D/D", "—", "precisa 2 runs", real=False)

    cards = (
        _cr_kpi_card("Deb CDI+ · indicativa méd", cdi_txt or "—", cdi_sub, real=cdi_txt is not None)
        + _cr_kpi_card(ipca_label, ipca_txt or "—", ipca_sub, real=ipca_txt is not None)
        + _cr_kpi_card("Spread médio over ANBIMA", prem_val, prem_sub, real=prem_real)
        + mv_card_html
    )
    st.markdown(
        f'<p class="mon-head" style="margin:8px 0 4px">Briefing do Secundário '
        f'<span class="table-card-meta" style="color:var(--green)">{src}</span></p>'
        f'<div class="cr-kpis">{cards}</div>',
        unsafe_allow_html=True,
    )


def _cr_spreads_segmento_illustrativo():
    """Fallback ilustrativo quando o arquivo ANBIMA não está disponível."""
    rows = [
        ('<span class="cr-tag cdi">CDI+</span> Deb AAA', "+1,12%", "84"),
        ('<span class="cr-tag cdi">CDI+</span> Deb AA',  "+1,68%", "112"),
        ('<span class="cr-tag ipca">IPCA+</span> Incent. infra', "+0,42%", "156"),
        ('<span class="cr-tag cra">CRA</span>',          "+0,98%", "71"),
    ]
    body = "".join(
        f'<tr><td class="ticker" style="text-align:left">{seg}</td>'
        f'<td class="hi">{spread}</td><td class="dur">{n}</td></tr>'
        for seg, spread, n in rows
    )
    st.markdown(
        _cr_card_open("Spreads por segmento — exemplo", _CR_ILLUS)
        + '<table class="mon-table"><thead><tr>'
          '<th class="left">Segmento</th><th>Spread</th><th>Papéis</th>'
          f'</tr></thead><tbody>{body}</tbody></table>'
          '<div class="cr-hint">Arquivo ANBIMA do dia indisponível — exibindo exemplo. '
          'Tente novamente em horário de pregão/fechamento.</div></div>',
        unsafe_allow_html=True,
    )


def _cr_spreads_segmento():
    """Debêntures — secundário ANBIMA (dados REAIS do arquivo diário db{ymd}.txt)."""
    df, ymd = _anbima_deb_load_latest()
    if df is None:
        _cr_spreads_segmento_illustrativo()
        return
    ddmmyy = f"{ymd[4:6]}/{ymd[2:4]}/{ymd[0:2]}" if ymd and len(ymd) == 6 else (ymd or "")
    st.markdown('<p class="mon-head" style="margin:4px 0 6px">Debêntures — secundário '
                f'<span class="table-card-meta" style="color:var(--green)">ANBIMA · {ddmmyy} · real</span></p>',
                unsafe_allow_html=True)

    q = st.text_input("Buscar debênture (código ou emissor)", key="anb_deb_q",
                      placeholder="ex: AEGEA, ARML, ENGIE, ELET")
    fdf = df
    if q:
        ql = q.lower()
        fdf = df[df["codigo"].str.lower().str.contains(ql, na=False)
                 | df["nome"].str.lower().str.contains(ql, na=False)]
    total = len(fdf)
    fdf = fdf.head(120)

    rows = []
    for _, a in fdf.iterrows():
        grp = _anb_grupo(a["indice"])
        tagcls = "cdi" if grp == "CDI+" else ("ipca" if grp == "IPCA+" else "cri")
        dur = a["duration_du"]
        dur_y = f"{dur/252:.2f}".replace(".", ",") if dur else "—"
        rows.append(
            f'<tr><td class="ticker" style="text-align:left">{a["codigo"]}</td>'
            f'<td style="text-align:left;font-size:11px;color:var(--text3)">{(a["nome"] or "")[:28]}</td>'
            f'<td>{a["vencimento"]}</td>'
            f'<td><span class="cr-tag {tagcls}">{a["indice"]}</span></td>'
            f'<td class="rate">{fr(a["compra"])}</td>'
            f'<td class="rate">{fr(a["venda"])}</td>'
            f'<td class="hi">{fr(a["indicativa"])}</td>'
            f'<td class="dur">{dur_y}</td></tr>'
        )
    render_collapsible_table(
        [("Código", "left"), ("Emissor", "left"), ("Vencto", ""), ("Índice", ""),
         ("Compra", ""), ("Venda", ""), ("Indicativa", ""), ("Dur (a)", "")],
        rows, key="anb_deb_exp", n=4,
        title="Debêntures — secundário ANBIMA", meta=f"db{ymd} · {total} papéis")
    st.caption("Indicativa = spread s/ DI (papéis DI+) ou taxa real (IPCA+). Duration em anos (du/252).")


def _cr_watchlist_fidc_illustrativo():
    """Tabela ilustrativa exibida enquanto nenhum informe real foi carregado."""
    rows = [
        ("FIDC Consignado Alpha", "820",   "24,1%", ("up","+0,4 pp"), "2,1%", ("ok","estável")),
        ("FIDC Cartões Beta",     "1.340", "18,2%", ("dn","−1,1 pp"), "4,8%", ("warn","atenção")),
        ("FIDC Agro Gamma",       "560",   "15,0%", ("dn","−2,3 pp"), "6,2%", ("alert","deterioração")),
        ("FIDC Veículos Delta",   "990",   "21,7%", ("fl","0"),       "3,0%", ("ok","estável")),
    ]
    body = ""
    for nome, pl, sub, dsub, inad, sinal in rows:
        body += (
            f'<tr><td class="ticker" style="text-align:left">{nome}</td>'
            f'<td>{pl}</td><td>{sub}</td>'
            f'<td><span class="cr-chip {dsub[0]}">{dsub[1]}</span></td>'
            f'<td class="hi">{inad}</td>'
            f'<td><span class="cr-chip {sinal[0]}">{sinal[1]}</span></td></tr>'
        )
    st.markdown(
        _cr_card_open("Watchlist FIDC — exemplo", f'{_CR_ILLUS}')
        + '<table class="mon-table"><thead><tr>'
          '<th class="left">FIDC</th><th>PL (mm)</th><th>Subord.</th><th>Δ sub.</th><th>Inad. 90d+</th><th>Sinal</th>'
          f'</tr></thead><tbody>{body}</tbody></table>'
          '<div class="cr-hint">Carregue um informe real acima para substituir este exemplo. '
          'Subordinação/inadimplência: mapeadas após confirmar colunas no inspetor.</div></div>',
        unsafe_allow_html=True,
    )


def _cr_watchlist_fidc():
    """Watchlist FIDC com dados REAIS do informe mensal CVM (carregado sob demanda)."""
    st.markdown('<p class="mon-head" style="margin:4px 0 6px">Watchlist FIDC '
                '<span class="table-card-meta" style="color:var(--green)">informe mensal CVM</span></p>',
                unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        ym = st.text_input("Mês (AAAAMM)", value=st.session_state.get("fidc_ym", _fidc_default_ym()),
                           key="fidc_ym_in", max_chars=6)
    with c2:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        if st.button("Carregar informe", key="fidc_load", use_container_width=True):
            ym2 = (ym or "").strip()
            with st.spinner(f"Baixando informe FIDC {ym2}…"):
                tables, err = fetch_fidc_informe(ym2)
            if err:
                st.warning(f"FIDC {ym2}: {err}")
            else:
                st.session_state["fidc_tables"] = tables
                st.session_state["fidc_ym"] = ym2
                st.success(f"Informe {ym2} · {len(tables)} arquivos.")

    tables = st.session_state.get("fidc_tables")
    if not tables:
        _cr_watchlist_fidc_illustrativo()
        return

    cur_ym = st.session_state.get("fidc_ym", "")
    with st.expander(f"🔎 Inspetor — estrutura real do informe {cur_ym}"):
        for nm, df in tables.items():
            st.markdown(f"**{nm}** — {len(df)} linhas · {len(df.columns)} colunas")
            st.caption(", ".join(df.columns[:40]) + (" …" if len(df.columns) > 40 else ""))

    name, fdf = _fidc_fund_table(tables)
    if fdf is None:
        st.info("Não localizei tabela de nível de fundo (coluna CNPJ_FUNDO). "
                "Use o inspetor para identificar o arquivo certo.")
        return

    pl_col = next((c for c in fdf.columns if "PATRIM_LIQ" in c), None)
    denom_col = next((c for c in fdf.columns
                      if c in ("DENOM_SOCIAL", "NM_FUNDO", "DENOM_FUNDO")), None)

    raw = st.text_area("CNPJs monitorados (um por linha ou vírgula) — vazio mostra amostra",
                       value=st.session_state.get("fidc_cnpjs", ""), key="fidc_cnpjs_in",
                       height=70, placeholder="00.000.000/0001-00")
    st.session_state["fidc_cnpjs"] = raw
    wanted = [re.sub(r"\D", "", x) for x in re.split(r"[\n,;]+", raw) if x.strip()]

    fdf2 = fdf.copy()
    fdf2["_d"] = fdf2["CNPJ_FUNDO"].astype(str).str.replace(r"\D", "", regex=True)
    sub = fdf2[fdf2["_d"].isin(wanted)] if wanted else fdf2.head(15)

    rows = ""
    for _, a in sub.iterrows():
        nome = a[denom_col] if denom_col else a["CNPJ_FUNDO"]
        pl = _fidc_fmt_mm(a[pl_col]) if pl_col else "—"
        rows += (f'<tr><td class="ticker" style="text-align:left">{a["CNPJ_FUNDO"]}</td>'
                 f'<td style="text-align:left;font-size:11px">{(str(nome) or "")[:34]}</td>'
                 f'<td class="hi">{pl}</td></tr>')
    render_table([("CNPJ", "left"), ("Fundo", "left"), ("PL (R$ mm)", "")], rows,
                 title=f"FIDC · informe {cur_ym}", meta=name)
    st.caption(f"PL real da coluna «{pl_col or '—'}». {len(sub)} fundos exibidos. "
               "Subordinação e inadimplência 90d+ entram após mapear as colunas no inspetor.")


def _cr_radar_micro_card():
    """Radar micro — DADOS REAIS via BCB SGS (fetch_radar_micro)."""
    with st.spinner("Buscando BCB SGS…"):
        radar = fetch_radar_micro()
    body = ""
    for r in radar:
        if r["valor"] is None:
            body += (f'<tr><td class="ticker" style="text-align:left">{r["label"]}</td>'
                     f'<td colspan="3" class="dur" style="font-size:11px">indisponível</td></tr>')
            continue
        val = f'{fr(r["valor"], r["dec"])}{r["suf"]}'
        if r["delta"] is None:
            dhtml = '<span class="cr-chip fl">—</span>'
        else:
            sgn = "+" if r["delta"] > 0 else ""
            cls = "up" if r["delta"] > 0 else ("dn" if r["delta"] < 0 else "fl")
            dhtml = f'<span class="cr-chip {cls}">{sgn}{fr(r["delta"], r["dec"])} pp</span>'
        # Coluna 12 meses
        v12 = r.get("valor_12m")
        if v12 is None:
            m12_html = '<span style="color:var(--text3)">—</span>'
        else:
            m12_html = f'{fr(v12, r["dec"])}{r["suf"]}'
        ref = f' · {r["data"]}' if r.get("data") else ""
        body += (f'<tr><td class="ticker" style="text-align:left">{r["label"]}'
                 f'<small style="color:var(--text3);font-weight:400">{ref}</small></td>'
                 f'<td class="hi">{val}</td><td>{dhtml}</td>'
                 f'<td class="rate">{m12_html}</td></tr>')
    st.markdown(
        _cr_card_open("Radar micro — lastros",
                      '<span class="table-card-meta" style="color:var(--green)">BCB SGS · real</span>')
        + '<table class="mon-table"><thead><tr>'
          '<th class="left">Indicador</th><th>Último</th><th>Δ período</th><th>12 meses</th>'
          f'</tr></thead><tbody>{body}</tbody></table>'
          '<div class="cr-hint">Inadimplência por modalidade + índices, direto da API do BCB (cache 1h). '
          '12m = acumulado (índices) ou valor de 1 ano atrás (inadimplência). '
          'Commodities CEPEA (soja/milho/boi) entram quando a fonte for conectada.</div></div>',
        unsafe_allow_html=True,
    )


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_rating_news():
    """Busca ações de rating de S&P (scraping HTML direto), Moody's e Fitch (Google News filtrado).
    
    S&P brazil.ratings.spglobal.com retorna HTML estático com a tabela de ações.
    Moody's (moodyslocal.com.br) e Fitch retornam 403 via Cloudflare/egress block —
    para essas duas agências usamos Google News com query específica por agência.
    """
    import urllib3; urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    items = []

    # ── 1. S&P Global Ratings Brasil — scraping HTML direto ─────
    # A página retorna tabela HTML estática com CSS class ratingsActions-table-module__row.
    # Cols: 0=emissor, 1=classe, 2=vencto, 3=tipo-rating, 4=data-ação,
    #       5=rating-novo(Para), 6=cw-novo, 7=rating-ant(De), 8=cw-ant, 9=tipo-ação
    if HAS_BS4:
        try:
            _SP_URL = "https://brazil.ratings.spglobal.com/ratings/pt/regulatory/ratings-actions"
            _SP_BASE = "https://brazil.ratings.spglobal.com"
            r = requests.get(_SP_URL, timeout=20, headers=_BROWSER_HEADERS, verify=False)
            if r.status_code == 200 and r.content:
                soup = _BS(r.content, "lxml")
                rows = soup.select(".ratingsActions-table-module__row")
                seen_entities = set()
                for row in rows:
                    cols = row.select(".ratingsActions-table-module__column")
                    if len(cols) < 6:
                        continue
                    entity = cols[0].get_text(separator=" ", strip=True)
                    if not entity or len(entity) < 5:
                        continue
                    # Deduplica emissores com múltiplas classes (ex.: várias cotas do mesmo FIDC)
                    entity_key = entity[:40]
                    if entity_key in seen_entities:
                        continue
                    seen_entities.add(entity_key)
                    link_tag = cols[0].find("a")
                    href = (_SP_BASE + link_tag.get("href", "")) if link_tag else _SP_URL
                    acao     = cols[9].get_text(strip=True) if len(cols) > 9 else ""
                    rat_novo = cols[5].get_text(strip=True) if len(cols) > 5 else ""
                    rat_ant  = cols[7].get_text(strip=True) if len(cols) > 7 else ""
                    data_ac  = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                    # Monta título legível: [Ação] Emissor → Rating novo (era Rating ant)
                    titulo = f"[{acao}] {entity[:70]}"
                    if rat_novo:
                        titulo += f" → {rat_novo}"
                    if rat_ant and rat_ant not in (acao, rat_novo, "De", "Para"):
                        titulo += f" (era {rat_ant})"
                    items.append({
                        "title": titulo[:160],
                        "link": href,
                        "source": "S&P",
                        "data": data_ac,
                    })
                    if len(items) >= 5:
                        break
        except Exception:
            pass  # falha silenciosa; complementado pelo bloco GN abaixo

    # ── 2. Moody's Local — Google News por agência ───────────────
    # moodyslocal.com.br retorna 403 Cloudflare para requests diretos.
    if HAS_FEEDPARSER:
        try:
            _GN_MOODY = (
                "https://news.google.com/rss/search?q="
                "%22Moody%27s%22+rating+brasil"
                "+debenture+OR+CRI+OR+CRA+OR+rebaixa+OR+afirma+OR+eleva"
                "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            )
            feed = _feedparser.parse(_GN_MOODY)
            _MOODY_KEYS = ("moody", "moody's")
            for e in feed.entries[:8]:
                title = e.get("title", "").strip()
                src_n = (e.get("source") or {}).get("title", "") or ""
                title_l = title.lower()
                if title and any(k in title_l or k in src_n.lower() for k in _MOODY_KEYS):
                    items.append({
                        "title": title[:160],
                        "link": e.get("link", ""),
                        "source": "Moody's",
                    })
            # Limita a 4 itens de Moody's
            items = [it for it in items if it["source"] != "Moody's"] + \
                    [it for it in items if it["source"] == "Moody's"][:4]
        except Exception:
            pass

    # ── 3. Fitch Ratings — Google News por agência ───────────────
    # fitchratings.com retorna 403 egress block no ambiente Streamlit Cloud.
    if HAS_FEEDPARSER:
        try:
            _GN_FITCH = (
                "https://news.google.com/rss/search?q="
                "%22Fitch%22+rating+brasil"
                "+debenture+OR+CRI+OR+CRA+OR+rebaixa+OR+afirma+OR+eleva"
                "&hl=pt-BR&gl=BR&ceid=BR:pt-419"
            )
            feed = _feedparser.parse(_GN_FITCH)
            _FITCH_KEYS = ("fitch",)
            fitch_added = 0
            for e in feed.entries[:8]:
                if fitch_added >= 2:
                    break
                title = e.get("title", "").strip()
                src_n = (e.get("source") or {}).get("title", "") or ""
                if title and any(k in title.lower() or k in src_n.lower() for k in _FITCH_KEYS):
                    items.append({
                        "title": title[:160],
                        "link": e.get("link", ""),
                        "source": "Fitch",
                    })
                    fitch_added += 1
        except Exception:
            pass

    return items[:12], None


def _cr_rating_actions():
    """Ações de rating & fatos relevantes — Moody's Local, S&P Brazil, Fitch + GN (cache 30 min)."""
    items, err = _fetch_rating_news()
    if items:
        feed_html = ""
        for it in items:
            ag = (it["source"] or "GN")[:14]
            feed_html += (
                f'<div class="cr-fitem"><span class="ag">{ag}</span>'
                f'<span class="tx"><a href="{it["link"]}" target="_blank" '
                f'style="color:var(--text1);text-decoration:none">{it["title"][:110]}</a>'
                f'</span></div>'
            )
        st.markdown(
            _cr_card_open("Ações de rating &amp; fatos relevantes",
                          '<span class="table-card-meta" style="color:var(--green)">Moody\'s · S&amp;P · Fitch</span>')
            + f'<div class="cr-feed">{feed_html}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            _cr_card_open("Ações de rating &amp; fatos relevantes",
                          '<span class="table-card-meta">Moody\'s · S&amp;P · Fitch</span>')
            + '<div class="cr-feed"><div class="cr-fitem">'
            + '<span class="tx" style="color:var(--text3)">'
            + (err or "Nenhuma ação de rating disponível no momento.")
            + '</span></div></div></div>',
            unsafe_allow_html=True,
        )


def _cr_top_movers():
    """Grid 2×2 — top 15 por |Δ bps| separados por tipo (CDI/IPCA) e direção."""
    st.markdown(
        '<p class="mon-head" style="margin:16px 0 6px">Top movers D/D '
        '<span class="table-card-meta" style="color:var(--green)">Fonte: Call Ativa</span></p>',
        unsafe_allow_html=True,
    )
    n_du = render_periodo_toggle("top_movers")
    data = {rt: _compute_top_movers(rt, n_du) for rt in ("CDI", "IPCA")}
    if all(v is None for v in data.values()):
        st.caption("Histórico insuficiente para a periodicidade selecionada.")
        return

    headers = [
        ("Ativo", "left"), ("Emissor", "left"), ("Δ bps", ""),
        ("Bid", ""), ("Ask", ""), ("Dur", ""),
    ]

    def _rows(df, chip_cls):
        out = []
        for _, a in df.iterrows():
            d    = a["delta"]
            dtxt = f"{d:+.0f} bps".replace("-", "−")
            dur_raw = a.get("duration")
            dur = f"{dur_raw:.2f} a" if pd.notna(dur_raw) and dur_raw else "—"
            out.append(
                f'<tr><td class="ticker" style="text-align:left"><b>{a["ativo"]}</b></td>'
                f'<td style="text-align:left;font-size:11px;color:var(--text3)">{(a["emissor"] or "")[:20]}</td>'
                f'<td><span class="cr-chip {chip_cls}">{dtxt}</span></td>'
                f'<td class="rate">{fr(a["compra"], 2)}</td>'
                f'<td class="rate">{fr(a["venda"], 2)}</td>'
                f'<td class="dur">{dur}</td></tr>'
            )
        return out

    _EMPTY_ROW = ('<tr><td colspan="6" style="color:var(--text3);text-align:center">'
                  '— sem movimentos nessa direção</td></tr>')

    col_l, col_r = st.columns([1, 1], gap="medium")
    for col, direction, chip_cls, arrow in (
        (col_l, "abertura",  "up", "↑"),
        (col_r, "fechamento", "dn", "↓"),
    ):
        with col:
            for rt_label, rt in (("CDI+", "CDI"), ("IPCA+", "IPCA")):
                m = data[rt]
                if m is None:
                    st.caption(
                        f"Suba ao menos 2 runs {rt_label} em datas diferentes "
                        "para ver o ranking."
                    )
                    continue
                df_dir  = m[direction]
                meta_s  = f"{m['data_prev']} → {m['data_hoje']} · {m['n_total']} ativos"
                title_s = f"{rt_label} · {'Abertura' if direction == 'abertura' else 'Fechamento'} {arrow}"
                rows = _rows(df_dir, chip_cls) if not df_dir.empty else [_EMPTY_ROW]
                render_collapsible_table(
                    headers, rows,
                    key=f"cr_tm_{rt}_{direction}",
                    n=15, title=title_s, meta=meta_s,
                )


# (tabelas de run CDI/IPCA/LF removidas — fluxo antigo descontinuado)



# ================================================================
# RADAR MICRO — indicadores de lastro via BCB SGS (API pública)
# ================================================================
# Inadimplência por modalidade + indexadores. Fonte estável e oficial.
# Usado na aba Crédito como leitura "micro" de risco de crédito.

# (sid, rótulo, grupo, n_casas, sufixo)
_SGS_SERIES = [
    (21082, "Inadimplência PF",          "Inadimplência", 2, "%"),
    (21084, "Inadimplência PJ",          "Inadimplência", 2, "%"),
    (21112, "Inad. crédito livre PF",    "Inadimplência", 2, "%"),
    (20768, "Inad. cartão rotativo",     "Inadimplência", 2, "%"),
    (433,   "IPCA",                      "Índices (mês)", 2, "%"),
    (189,   "IGP-M",                     "Índices (mês)", 2, "%"),
    (192,   "INCC",                      "Índices (mês)", 2, "%"),
    (4390,  "Selic mensal",              "Juros",         2, "%"),
]


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_sgs_series(sid: int, n: int = 2):
    """Busca os últimos n pontos de uma série SGS do BCB. Retorna (lista, erro)."""
    url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{sid}/dados/ultimos/{n}?formato=json"
    try:
        r = requests.get(url, timeout=12, headers={"User-Agent": "Mozilla/5.0"}, verify=False)
        r.raise_for_status()
        data = r.json()
        out = []
        for d in data:
            try:
                out.append({"data": d["data"], "valor": float(str(d["valor"]).replace(",", "."))})
            except (ValueError, KeyError):
                continue
        return out, None
    except Exception as e:
        return None, str(e)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_radar_micro():
    """Coleta todas as séries do radar. Retorna lista de dicts com último valor, Δ e acumulado 12m."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    # Séries com acumulado via soma (indexadores mensais)
    _ACUM_SOMA = {433, 189, 192}   # IPCA, IGP-M, INCC
    # Série com acumulado via produto (Selic mensal)
    _ACUM_PROD = {4390}
    # Séries de inadimplência: exibe valor de 1 ano atrás
    _INAD = {21082, 21084, 21112, 20768}
    rows = []
    for sid, label, grupo, dec, suf in _SGS_SERIES:
        pts, err = fetch_sgs_series(sid, 14)  # 14 pontos → ~12m de lookback
        if not pts:
            rows.append({"label": label, "grupo": grupo, "valor": None,
                         "delta": None, "valor_12m": None, "data": None,
                         "dec": dec, "suf": suf, "err": err})
            continue
        ultimo = pts[-1]
        delta = (ultimo["valor"] - pts[-2]["valor"]) if len(pts) >= 2 else None
        # Cálculo do valor 12m
        valor_12m = None
        if sid in _INAD:
            # Valor de aproximadamente 1 ano atrás (13 meses antes do mais recente)
            if len(pts) >= 13:
                valor_12m = pts[-13]["valor"]
        elif sid in _ACUM_SOMA:
            # Acumulado 12 meses = soma dos últimos 12 valores mensais
            if len(pts) >= 12:
                valor_12m = sum(p["valor"] for p in pts[-12:])
        elif sid in _ACUM_PROD:
            # Acumulado Selic = produto composto dos últimos 12 valores mensais
            if len(pts) >= 12:
                acc = 1.0
                for p in pts[-12:]:
                    acc *= (1 + p["valor"] / 100)
                valor_12m = (acc - 1) * 100
        rows.append({
            "label": label, "grupo": grupo,
            "valor": ultimo["valor"], "delta": delta, "data": ultimo["data"],
            "valor_12m": valor_12m,
            "dec": dec, "suf": suf, "err": None,
        })
    return rows


# (render_radar_micro removido — radar agora em _cr_radar_micro_card)


# ================================================================
# SRE CVM
# ================================================================
_CVM_URL = "https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip"

# Mapa de tipo de ativo → rótulo curto DCM (a partir de Valor_Mobiliario)
_CVM_TIPO_MAP = [
    ("FIDC",           ["fidc"]),
    ("Debênture",      ["debêntures", "debentures"]),
    ("CRI",            ["recebíveis imobiliários", "recebiveis imobiliarios"]),
    ("CRA",            ["recebíveis do agronegócio", "recebiveis do agronegocio",
                        "direitos creditórios do agronegócio", "direitos creditorios do agronegocio"]),
    ("NC", ["notas comerciais", "nota comercial"]),
    ("FIAGRO",         ["fiagro"]),
    ("CPR",            ["cédula de produto rural", "cedula de produto rural", "cpr"]),
    ("Securitização",  ["securitização", "securitizacao", "certificados de recebíveis",
                        "certificados de recebiveis"]),
    ("FII",            ["fii", "fundo imobiliário", "fundo imobiliario"]),
    ("FI-Infra",       ["fundos de infra", "fundo de infra", "fi-infra"]),
    ("FIP",            ["fip"]),
    ("FIF",            ["fif"]),
    ("Ação",           ["ações", "acoes", "ação"]),
]

_RUN_PARA_SRE: dict = {
    "CDI":  ["Debênture", "NC"],
    "IPCA": ["Debênture", "CRI", "CRA", "FI-Infra", "FIAGRO", "Securitização"],
}


def _find_col(df_in, target_name):
    t = target_name.replace("_", "").replace(" ", "").lower()
    for c in df_in.columns:
        if c.replace("_", "").replace(" ", "").lower() == t:
            return c
    return None


def _autosize_config(df_in):
    cfg = {}
    for col in df_in.columns:
        try:
            content_max = int(df_in[col].dropna().head(500).astype(str).str.len().max() or 0)
        except Exception:
            content_max = 0
        approx = max(len(str(col)), content_max)
        w = "small" if approx <= 14 else ("medium" if approx <= 40 else "large")
        
        if "total" in col.lower():
            w = 120  # Força a coluna do Emissor a ter xpx de largura
        elif "data" in col.lower():
            w = 80
        elif "emissor" in col.lower():
            w = 220
        elif "devedor" in col.lower():
            w = 220
        elif "lider" in col.lower():
            w = 200
        elif "destinacao" in col.lower():
            w = 180
        elif "garantia" in col.lower():
            w = 180
        elif "valor" in col.lower():
            w = 195  # Força a coluna do Emissor a ter xpx de largura
        
        cfg[col] = st.column_config.Column(width=w, help=str(col))
    return cfg


def _cvm_tipo_curto(valor_mobiliario: str) -> str:
    if not isinstance(valor_mobiliario, str):
        return "Outros"
    v = valor_mobiliario.lower()
    for label, keys in _CVM_TIPO_MAP:
        if any(k in v for k in keys):
            return label
    return "Outros"


def _sre_pipeline_por_segmento(df, dias=30, limiar=5):
    """Conta ofertas recentes por segmento (coluna Tipo já processada); flag 'pesado' se >= limiar."""
    if df is None or df.empty:
        return {}
    date_col_s = _find_col(df, "Data_requerimento")
    tipo_col_s = _find_col(df, "Tipo")
    if not date_col_s:
        return {}
    cutoff = pd.Timestamp(_brt_date()) - pd.Timedelta(days=dias)
    recentes = df[pd.to_datetime(df[date_col_s], errors="coerce") >= cutoff]
    if recentes.empty:
        return {}
    seg = recentes[tipo_col_s] if tipo_col_s else pd.Series(
        ["Outros"] * len(recentes), index=recentes.index
    )
    counts = seg.value_counts().to_dict()
    return {s: {"contagem": n, "pesado": n >= limiar} for s, n in counts.items()}


def _segmentos_sre_relevantes(run_type: str) -> set:
    """Retorna set de instrumentos SRE relevantes para run_type se houver abertura >= limiar."""
    limiar = st.session_state.get("limiar_bps", LIMIAR_BPS_DEFAULT)
    movers = _compute_top_movers(run_type)
    if movers is None or movers["abertura"].empty:
        return set()
    df_ab = movers["abertura"]
    if df_ab[df_ab["delta"].abs() >= limiar].empty:
        return set()
    return set(_RUN_PARA_SRE.get(run_type, []))


def _normaliza_emissor(nome: str) -> str:
    """Normaliza nome de emissor para comparação aproximada (possível match, não assertivo)."""
    if not nome:
        return ""
    n = nome.upper()
    for suf in (r"\bS\.?A\.?\b", r"\bLTDA\.?\b", r"\bS\.?C\.?A\.?\b",
                r"\bFIDC\b", r"\bFII\b", r"\bFIP\b"):
        n = re.sub(suf, "", n)
    n = re.sub(r"[^\w\s]", " ", n)
    return " ".join(n.split())


def _similaridade(a: str, b: str) -> float:
    """Ratio de similaridade entre duas strings (0.0–1.0). Usa SequenceMatcher."""
    from difflib import SequenceMatcher
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def load_run_emissores_abrindo(run_type: str) -> list:
    """
    Retorna lista de emissores com spread_b abrindo >= limiar no run mais recente.
    Compara run mais recente com o anterior para o mesmo run_type.
    Usa spread_b (bps) diretamente — não passa por load_run_on.
    """
    limiar = st.session_state.get("limiar_bps", LIMIAR_BPS_DEFAULT)
    try:
        with _db() as con:
            datas = con.execute(
                "SELECT DISTINCT brt_date FROM credito_runs WHERE run_type=?"
                " ORDER BY brt_date DESC LIMIT 2",
                (run_type,),
            ).fetchall()
        if len(datas) < 2:
            return []
        d_hoje, d_ontem = datas[0][0], datas[1][0]
        with _db() as con:
            hoje = pd.read_sql_query(
                "SELECT ativo, emissor, spread_b FROM credito_runs"
                " WHERE run_type=? AND brt_date=?",
                con, params=(run_type, d_hoje),
            )
            ontem = pd.read_sql_query(
                "SELECT ativo, spread_b AS spread_b_prev FROM credito_runs"
                " WHERE run_type=? AND brt_date=?",
                con, params=(run_type, d_ontem),
            )
        merged = hoje.merge(ontem, on="ativo", how="inner")
        merged["delta"] = merged["spread_b"] - merged["spread_b_prev"]
        abrindo = merged[merged["delta"] >= limiar]
        emissores = abrindo["emissor"].dropna().unique().tolist()
        return [e for e in emissores if e]
    except Exception:
        return []


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_cvm_sre():
    """Carrega oferta_resolucao_160.csv (ofertas modernas pós-Res. CVM 160,
    com lastro/garantias/bookbuilding). Retorna (df, err)."""
    try:
        r = requests.get(_CVM_URL, timeout=90, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            target = next((n for n in z.namelist() if "resolucao_160" in n.lower()), None)
            if target is None:
                target = next((n for n in z.namelist() if n.lower().endswith(".csv")), None)
            if target is None:
                return None, "Nenhum CSV no ZIP"
            with z.open(target) as f:
                df = pd.read_csv(f, encoding="latin-1", sep=";",
                                 on_bad_lines="skip", low_memory=False)
        df.columns = [c.strip() for c in df.columns]

        # Datas em formato ISO (%Y-%m-%d) — sem dayfirst
        for col in df.columns:
            if col.lower().startswith("data") or col.lower().startswith("dt"):
                df[col] = pd.to_datetime(df[col], errors="coerce")

        # Numérico
        for col in ["Valor_Total_Registrado", "Qtde_Total_Registrada"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        # Tipo curto DCM
        if "Valor_Mobiliario" in df.columns:
            df["Tipo"] = df["Valor_Mobiliario"].apply(_cvm_tipo_curto)
        else:
            df["Tipo"] = "Outros"

        return df, None
    except Exception as e:
        return None, str(e)


def _fmt_bi(v):
    """Formata R$ em bilhões/milhões."""
    try:
        if v is None or (isinstance(v, float) and np.isnan(v)):
            return "—"
        if abs(v) >= 1e9:
            return f"R$ {v/1e9:,.1f} bi"
        if abs(v) >= 1e6:
            return f"R$ {v/1e6:,.0f} mi"
        return f"R$ {v:,.0f}"
    except Exception:
        return "—"


def render_cvm():
    st.markdown(
        f'<p class="mon-sub">Ofertas públicas (Res. CVM 160) · Fonte: '
        f'<a href="{_CVM_URL}" target="_blank" style="color:var(--accent)">dados.cvm.gov.br</a></p>',
        unsafe_allow_html=True,
    )
    with st.spinner("Baixando dados da CVM…"):
        df, err = fetch_cvm_sre()
    if err:
        st.error(f"Erro ao carregar dados CVM: {err}")
        return
    if df is None or df.empty:
        st.warning("Dados CVM vazios.")
        return

    date_col = "Data_requerimento" if "Data_requerimento" in df.columns else None
    if date_col is None:
        st.warning("Coluna de data não encontrada no arquivo CVM.")
        st.dataframe(df.head(200), use_container_width=True, hide_index=True)
        return

    emissor_col = _find_col(df, "Nome_Emissor")
    devedor_col = _find_col(df, "Identificacao_devedores_coobrigados")
    coord_col   = _find_col(df, "Nome_Lider")
    default_cols_request = [
        "Data_requerimento", "Valor_Mobiliario", "Nome_Emissor",
        "Identificacao_devedores_coobrigados", "Nome_Lider", "Valor_Total_Registrado",
        "Destinacao_recursos", "Descricao_garantias",
    ]
    default_cols_present = []
    for want in default_cols_request:
        c = _find_col(df, want)
        if c and c not in default_cols_present:
            default_cols_present.append(c)

    # ── "Novas desde última visita" (persistido em SQLite) ─────
    last_visit = get_meta("cvm_last_visit")
    novas_n = 0
    if last_visit:
        try:
            lv = pd.Timestamp(last_visit)
            novas_n = int((df[date_col] > lv).sum())
        except Exception:
            novas_n = 0
    # Marca visita atual (após calcular as novas)
    set_meta("cvm_last_visit", _brt_date().strftime("%Y-%m-%d"))

    # ── Filtros ────────────────────────────────────────────────
    with st.expander("Filtros", expanded=True):
        fc1, fc2, fc3, fc4 = st.columns(4)
        valid_dates = df[date_col].dropna()
        min_d = valid_dates.min().date()
        max_d = valid_dates.max().date()
        default_from = max(min_d, (_brt_date() - timedelta(days=180)))
        from_d = fc1.date_input("De", value=default_from, min_value=min_d, max_value=max_d, key="cvm_from")
        to_d   = fc2.date_input("Até", value=max_d, min_value=min_d, max_value=max_d, key="cvm_to")

        tipos = ["Todos"] + sorted(df["Tipo"].dropna().unique().tolist())
        sel_tipo = fc3.selectbox("Tipo", tipos, key="cvm_tipo")

        status_opts = ["Todos"]
        if "Status_Requerimento" in df.columns:
            status_opts += sorted(df["Status_Requerimento"].dropna().unique().tolist())
        sel_status = fc4.selectbox("Status", status_opts, key="cvm_status")

        fc5, fc6, fc8 = st.columns(3)
        publico_opts = ["Todos"]
        if "Publico_alvo" in df.columns:
            publico_opts += sorted(df["Publico_alvo"].dropna().unique().tolist())
        sel_publico = fc5.selectbox("Público-alvo", publico_opts, key="cvm_publico")

        lastro_opts = ["Todos"]
        if "Tipo_lastro" in df.columns:
            lastro_opts += sorted(df["Tipo_lastro"].dropna().unique().tolist())
        sel_lastro = fc6.selectbox("Lastro", lastro_opts, key="cvm_lastro")
        
        rating_opts = ["Todos"]
        if "Avaliador_Risco" in df.columns:
            rating_opts += sorted(df["Avaliador_Risco"].dropna().unique().tolist())
        sel_rating = fc8.selectbox("Agência rating", rating_opts, key="cvm_rating")
	
        fc9, fc10, fc11 = st.columns(3)
        book_opts = ["Todos"]
        if "Bookbuilding" in df.columns:
            book_opts += sorted(df["Bookbuilding"].dropna().astype(str).unique().tolist())
        sel_book = fc9.selectbox("Bookbuilding", book_opts, key="cvm_book")

        _vol_avail = "Valor_Total_Registrado" in df.columns
        if _vol_avail:
            _vmax_g = int((df["Valor_Total_Registrado"].dropna().max() or 0) / 1_000_000) + 1
            vol_min_mi = fc10.number_input("Vol mín (R$ mi)", min_value=0, value=0,
                                            step=100, key="cvm_vol_min")
            vol_max_mi = fc11.number_input("Vol máx (R$ mi)", min_value=0, value=_vmax_g,
                                            step=100, key="cvm_vol_max")
        else:
            vol_min_mi = vol_max_mi = None

        ec1, ec2, ec3 = st.columns(3)
        sel_emissor = ec1.selectbox(
            "Emissor", ["Todos"] + sorted(df[emissor_col].dropna().astype(str).unique().tolist()),
            key="cvm_emissor",
        ) if emissor_col else None
        sel_devedor = ec2.selectbox(
            "Devedor", ["Todos"] + sorted(df[devedor_col].dropna().astype(str).unique().tolist()),
            key="cvm_devedor",
        ) if devedor_col else None
        if coord_col:
            opts_cd = ["Todos"] + sorted(df[coord_col].dropna().astype(str).unique().tolist())
            sel_coord = ec3.selectbox("Coordenador Lider", opts_cd, key="cvm_coord")
        else:
            sel_coord = None
            ec3.caption("Coluna 'Nome_Lider' ausente.")

        sel_cols = st.multiselect(
            "Colunas a exibir", list(df.columns),
            default=default_cols_present or list(df.columns)[:12],
            key="cvm_cols",
        )

    # ── Aplica filtros ─────────────────────────────────────────
    fdf = df[(df[date_col].dt.date >= from_d) & (df[date_col].dt.date <= to_d)].copy()
    if sel_tipo != "Todos":
        fdf = fdf[fdf["Tipo"] == sel_tipo]
    if sel_status != "Todos" and "Status_Requerimento" in fdf.columns:
        fdf = fdf[fdf["Status_Requerimento"] == sel_status]
    if sel_publico != "Todos" and "Publico_alvo" in fdf.columns:
        fdf = fdf[fdf["Publico_alvo"] == sel_publico]
    if sel_lastro != "Todos" and "Tipo_lastro" in fdf.columns:
        fdf = fdf[fdf["Tipo_lastro"] == sel_lastro]
    if sel_rating != "Todos" and "Avaliador_Risco" in fdf.columns:
        fdf = fdf[fdf["Avaliador_Risco"] == sel_rating]
    if sel_book != "Todos" and "Bookbuilding" in fdf.columns:
        fdf = fdf[fdf["Bookbuilding"].astype(str) == sel_book]
    if _vol_avail and vol_min_mi is not None:
        fdf = fdf[fdf["Valor_Total_Registrado"].fillna(0) >= vol_min_mi * 1_000_000]
        if vol_max_mi and vol_max_mi > vol_min_mi:
            fdf = fdf[fdf["Valor_Total_Registrado"].fillna(0) <= vol_max_mi * 1_000_000]
    if sel_emissor and sel_emissor != "Todos" and emissor_col:
        fdf = fdf[fdf[emissor_col].astype(str) == sel_emissor]
    if sel_devedor and sel_devedor != "Todos" and devedor_col:
        fdf = fdf[fdf[devedor_col].astype(str) == sel_devedor]
    if coord_col and sel_coord and sel_coord != "Todos":
        fdf = fdf[fdf[coord_col].astype(str) == sel_coord]

    # ── KPIs + Distribuição: janela de N dias úteis para trás (default 1) ──
    st.caption("Distribuição por ativo · período")
    n_du_cvm = render_periodo_toggle("cvm_distribuicao")
    _hoje_cvm  = pd.Timestamp(_brt_date()).normalize()
    _ini_cvm   = pd.Timestamp(_target_date_n_du_back(_brt_date(), n_du_cvm)).normalize()
    if date_col:
        _col_dt = pd.to_datetime(df[date_col], errors="coerce").dt.normalize()
        fdf_kpi = df[(_col_dt >= _ini_cvm) & (_col_dt <= _hoje_cvm)].copy()
    else:
        fdf_kpi = df.copy()

    # ── KPIs ───────────────────────────────────────────────────
    vol_total = fdf_kpi["Valor_Total_Registrado"].sum() if "Valor_Total_Registrado" in fdf_kpi.columns else 0
    n_ofertas = len(fdf_kpi)
    n_book = int((fdf_kpi["Status_Requerimento"] == "Aguardando Bookbuilding").sum()) \
             if "Status_Requerimento" in fdf_kpi.columns else 0
    n_vivo = int(fdf_kpi["Status_Requerimento"].isin(
        ["Registro Concedido", "Aguardando Bookbuilding"]).sum()) \
        if "Status_Requerimento" in fdf_kpi.columns else 0

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f'<div class="table-card" style="padding:14px 18px;margin-bottom:0">'
                f'<div class="table-card-meta">Ofertas no período</div>'
                f'<div style="font-size:22px;font-weight:800;color:var(--text1)">{n_ofertas:,}</div>'
                f'</div>', unsafe_allow_html=True)
    k2.markdown(f'<div class="table-card" style="padding:14px 18px;margin-bottom:0">'
                f'<div class="table-card-meta">Volume registrado</div>'
                f'<div style="font-size:22px;font-weight:800;color:var(--text1)">{_fmt_bi(vol_total)}</div>'
                f'</div>', unsafe_allow_html=True)
    k3.markdown(f'<div class="table-card" style="padding:14px 18px;margin-bottom:0">'
                f'<div class="table-card-meta">Pipeline vivo</div>'
                f'<div style="font-size:22px;font-weight:800;color:var(--accent)">{n_vivo:,}</div>'
                f'</div>', unsafe_allow_html=True)
    novas_color = "var(--green)" if novas_n else "var(--text3)"
    k4.markdown(f'<div class="table-card" style="padding:14px 18px;margin-bottom:0">'
                f'<div class="table-card-meta">Novas desde última visita</div>'
                f'<div style="font-size:22px;font-weight:800;color:{novas_color}">{novas_n:,}</div>'
                f'</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Tabela detalhada (colunas DCM) ─────────────────────────
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    fdf_sorted = fdf.sort_values(date_col, ascending=False)
    show_cols = [c for c in sel_cols if c in fdf_sorted.columns] if sel_cols else list(fdf_sorted.columns)
    detail = fdf_sorted[show_cols].copy() if show_cols else fdf_sorted.copy()

    val_c = _find_col(detail, "Valor_Total_Registrado")
    fmt_map = {}
    if val_c and val_c in detail.columns:
        fmt_map[val_c] = lambda x: (
            f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            if pd.notna(x) else "—"
        )
    if date_col in detail.columns and pd.api.types.is_datetime64_any_dtype(detail[date_col]):
        fmt_map[date_col] = lambda x: x.strftime("%d/%m/%Y") if pd.notna(x) else "—"
    styled = detail.style.format(fmt_map, na_rep="—") if fmt_map else detail

    st.caption(f"{len(detail):,} ofertas · ordenadas por data (mais recente primeiro)")
    st.dataframe(styled, use_container_width=True, hide_index=True, height=460,
                 column_config=_autosize_config(detail))

    csv_bytes = detail.to_csv(index=False, sep=";", encoding="utf-8-sig").encode()
    st.download_button("Baixar filtrado (.csv)", csv_bytes,
                       file_name=f"cvm_ofertas_{_brt_today()}.csv", mime="text/csv")

    # ── Volume por tipo (mini-resumo) — mesmo intervalo D-1/D0 dos KPIs ──
    if "Valor_Total_Registrado" in fdf_kpi.columns and not fdf_kpi.empty:
        by_tipo = (fdf_kpi.groupby("Tipo")
                      .agg(n=("Tipo", "size"), vol=("Valor_Total_Registrado", "sum"))
                      .sort_values("vol", ascending=False))
        rows = ""
        for tipo, r in by_tipo.iterrows():
            rows += (f'<tr><td class="ticker" style="text-align:left">{tipo}</td>'
                     f'<td class="hi">{int(r["n"])}</td>'
                     f'<td class="rate">{_fmt_bi(r["vol"])}</td></tr>')
        render_table(
            [("Tipo", "left"), ("Ofertas", ""), ("Volume", "")],
            rows, title="Distribuição por tipo", meta=f"{n_du_cvm} du · {_ini_cvm.strftime('%d/%m')} – {_hoje_cvm.strftime('%d/%m')}",
        )


# ================================================================
# BRIEFING DE CRÉDITO
# ================================================================
def render_briefing_credito(anbima_df):
    """3 cards de síntese (spreads, ANBIMA, SRE) + faixa de leitura. Aparece acima das tabelas na Principal."""
    limiar = st.session_state.get("limiar_bps", LIMIAR_BPS_DEFAULT)

    # ── Periodicidade independente p/ Spreads D/D e ANBIMA deb ──
    _pcol1, _pcol2, _pcol3 = st.columns([1, 1, 1])
    with _pcol1:
        st.caption("Spreads · período")
        n_du_spreads = render_periodo_toggle("briefing_spreads")
    with _pcol2:
        st.caption("ANBIMA deb · período")
        n_du_anbima = render_periodo_toggle("briefing_anbima")

    # ── Bloco 1: Spreads D/D (runs CDI + IPCA) ─────────────────
    def _bloco_spreads():
        mov_cdi  = _compute_top_movers("CDI", n_du_spreads)
        mov_ipca = _compute_top_movers("IPCA", n_du_spreads)
        if mov_cdi is None and mov_ipca is None:
            return None, None, None  # sem dados
        frames_ab = []
        frames_fe = []
        for mov in [mov_cdi, mov_ipca]:
            if mov is None:
                continue
            ab = mov["abertura"].copy()
            fe = mov["fechamento"].copy()
            ab["_abs"] = ab["delta"].abs()
            fe["_abs"] = fe["delta"].abs()
            frames_ab.append(ab)
            frames_fe.append(fe)
        if not frames_ab:
            return None, None, None
        all_ab = pd.concat(frames_ab).sort_values("_abs", ascending=False)
        all_fe = pd.concat(frames_fe).sort_values("_abs", ascending=False)
        all_ab = all_ab[all_ab["_abs"] >= limiar]
        all_fe = all_fe[all_fe["_abs"] >= limiar]
        ab = all_ab.head(6)
        fe = all_fe.head(6)
        return (ab, fe), len(all_ab), len(all_fe)

    # ── Bloco 2: ANBIMA debêntures — maiores aberturas/fechamentos de spread D/D ──
    def _bloco_anbima():
        # Arquivo do último dia útil disponível
        df_hoje, ymd_hoje = _anbima_deb_load_latest()
        if df_hoje is None or df_hoje.empty or not ymd_hoje:
            return None
        # Arquivo do dia útil de comparação (n_du dias úteis atrás)
        d_atual = datetime.strptime(ymd_hoje, "%y%m%d").date()
        alvo = _target_date_n_du_back(d_atual, n_du_anbima)
        df_prev, ymd_prev = None, None
        d = alvo
        for _ in range(12):
            if d.weekday() < 5 and d < d_atual:
                _ymd = d.strftime("%y%m%d")
                _df, _e = fetch_anbima_debentures(_ymd)
                if _df is not None and len(_df):
                    df_prev, ymd_prev = _df, _ymd
                    break
            d -= timedelta(days=1)
        if df_prev is None or df_prev.empty:
            return None

        cur = df_hoje[["codigo", "nome", "indice", "indicativa"]].dropna(subset=["indicativa"])
        prv = df_prev[["codigo", "indicativa"]].dropna(subset=["indicativa"]).rename(
            columns={"indicativa": "indicativa_prev"})
        merged = cur.merge(prv, on="codigo", how="inner")
        if merged.empty:
            return None
        # Spread em bps: indicativa está em % → ×100 p/ bps
        merged["delta_bps"] = (merged["indicativa"] - merged["indicativa_prev"]) * 100
        merged = merged.dropna(subset=["delta_bps"])
        if merged.empty:
            return None
        # label = código (nome do papel), tx_ind = indicativa atual
        merged["label"]  = merged["codigo"].astype(str).str.strip()
        merged["tx_ind"] = merged["indicativa"]
        merged["_abs"]   = merged["delta_bps"].abs()
        return merged.sort_values("_abs", ascending=False).head(6)

    # ── Bloco 3: SRE — ofertas do último dia disponível ─────────
    def _bloco_sre():
        try:
            df_sre, _err = fetch_cvm_sre()
        except Exception:
            df_sre, _err = None, "indisponível"
        if df_sre is None or df_sre.empty:
            return None, {}, "SRE indisponível", None

        date_col = _find_col(df_sre, "Data_requerimento")
        tipo_col = _find_col(df_sre, "Tipo")
        emis_col = _find_col(df_sre, "Nome_Emissor")
        dev_col  = _find_col(df_sre, "Identificacao_devedores_coobrigados")
        vol_col  = _find_col(df_sre, "Valor_Total_Registrado")

        # D-1 até D0
        _d0 = pd.Timestamp(_brt_date())
        _d1 = _d0 - pd.Timedelta(days=1)
        if date_col:
            novas = df_sre[
                (df_sre[date_col] >= _d1) & (df_sre[date_col] <= _d0)
            ].copy()
        else:
            novas = df_sre.head(10).copy()
        data_txt = f"{_d1.strftime('%d/%m')}–{_d0.strftime('%d/%m')}"

        # Filtra só instrumentos DCM relevantes (Debênture, CRI, CRA, NC)
        _TIPOS_BRIEFING = {"Debênture", "CRI", "CRA", "NC"}
        if tipo_col and tipo_col in novas.columns:
            novas = novas[novas[tipo_col].isin(_TIPOS_BRIEFING)]

        # Pipeline por segmento (mantém para a síntese)
        pipeline = _sre_pipeline_por_segmento(df_sre)

        rows_html = ""
        for _, r in novas.head(7).iterrows():
            emissor = (str(r[emis_col]) if emis_col and pd.notna(r.get(emis_col)) else "—")[:40]
            tipo    = str(r[tipo_col]) if tipo_col and pd.notna(r.get(tipo_col)) else "—"
            # Para CRI/CRA/CR mostra o devedor no lugar do emissor (securitizadora)
            _tipo_norm = tipo.strip().upper()
            if _tipo_norm in ("CRI", "CRA", "CR"):
                dev_val = str(r[dev_col]) if dev_col and pd.notna(r.get(dev_col)) else ""
                dev_val = dev_val.strip()
                if dev_val and dev_val not in ("—", "nan", "None"):
                    emissor = dev_val[:40]
            vol_raw = r.get(vol_col) if vol_col else None
            vol_txt = (f"R$ {vol_raw/1e6:.0f}M" if pd.notna(vol_raw) and vol_raw else "—")
            rows_html += (
                f'<div class="briefing-row">'
                f'<span class="nm">{emissor}</span>'
                f'<span class="dl">'
                f'<span class="cr-chip fl">{tipo}</span>&nbsp;{vol_txt}'
                f'</span>'
                f'</div>'
            )
        if not rows_html:
            rows_html = '<span style="color:var(--text3);font-size:12px">sem ofertas no período</span>'

        return rows_html, pipeline, None, data_txt

    top3_spreads, n_ab, n_fe = _bloco_spreads()
    top3_anbima  = _bloco_anbima()
    novas_html, pipeline_sre, sre_err, sre_data = _bloco_sre()

    # ── Matching por emissor (possível match — fuzzy, threshold 0.82) ──
    try:
        df_sre_local, _ = fetch_cvm_sre()
        emissor_col_sre = _find_col(df_sre_local, "Nome_Emissor")
        if df_sre_local is not None and not df_sre_local.empty and emissor_col_sre:
            sre_emissores = df_sre_local[emissor_col_sre].dropna().unique().tolist()
            LIMIAR_SIM = 0.82

            matches = []
            sre_norm_list = [(e, _normaliza_emissor(e)) for e in sre_emissores
                             if _normaliza_emissor(e)]

            for rt in ("CDI", "IPCA"):
                for em in load_run_emissores_abrindo(rt):
                    em_norm = _normaliza_emissor(em)
                    if not em_norm:
                        continue
                    melhor_score = 0.0
                    melhor_nome_sre = None
                    for nome_sre, norm_sre in sre_norm_list:
                        score = _similaridade(em_norm, norm_sre)
                        if score > melhor_score:
                            melhor_score = score
                            melhor_nome_sre = nome_sre
                    if melhor_score >= LIMIAR_SIM:
                        label_rt = "CDI+" if rt == "CDI" else "IPCA+"
                        matches.append(
                            f"<b>{em}</b> ({label_rt}) abrindo · "
                            f"SRE: {melhor_nome_sre} "
                            f'<span style="color:var(--text3);font-size:10px">'
                            f"sim={melhor_score:.0%}</span>"
                        )

            if matches:
                aviso = "; ".join(matches[:3])
                st.markdown(
                    f'<div class="briefing-synth" style="border-color:#93C5FD;'
                    f'background:var(--accentbg);color:var(--accent)">'
                    f'🔍 Possível match emissor: {aviso}</div>',
                    unsafe_allow_html=True,
                )
    except Exception:
        pass  # matching por emissor é best-effort; falha silenciosa

    # ── Grid 3 cards ────────────────────────────────────────────
    html_b1 = html_b2 = html_b3 = ""

    # Card 1
    if top3_spreads is None:
        html_b1 = '<p class="briefing-fallback">Suba ≥2 runs para ver</p>'
    else:
        ab_df, fe_df = top3_spreads

        def _spread_rows(df_sr, chip_cls):
            rows = ""
            for _, r in df_sr.iterrows():
                idx    = r.get("indexador", "")
                compra = r.get("compra")
                venda  = r.get("venda")
                if pd.notna(compra) and pd.notna(venda):
                    mid = (compra + venda) / 2
                elif pd.notna(compra):
                    mid = compra
                elif pd.notna(venda):
                    mid = venda
                else:
                    mid = None
                taxa = f"{idx}{fr(mid, 2)}%" if mid is not None else "—"
                d    = r["delta"]
                rows += (
                    f'<div class="briefing-row">'
                    f'<span class="nm">{r["ativo"]}&nbsp;&nbsp;<span style="font-size:10.5px;color:var(--text3)">{taxa}</span></span>'
                    f'<span class="dl">'
                    f'<span class="cr-chip {chip_cls}">{d:+.0f} bps</span>'
                    f'</span></div>'
                )
            return rows or '<span style="color:var(--text3);font-size:11px">—</span>'

        html_ab   = _spread_rows(ab_df, "up")
        html_fe   = _spread_rows(fe_df, "dn")
        count_txt = f"{n_ab} abrindo · {n_fe} fechando" if n_ab is not None else ""
        html_b1 = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
            f'<div><div style="font-size:9.5px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.05em;color:var(--text3);margin-bottom:4px">Abertura ↑</div>'
            f'{html_ab}</div>'
            f'<div><div style="font-size:9.5px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.05em;color:var(--text3);margin-bottom:4px">Fechamento ↓</div>'
            f'{html_fe}</div>'
            f'</div>'
            f'<div style="font-size:10px;color:var(--text3);margin-top:6px">{count_txt}</div>'
        )

    # Card 2
    if top3_anbima is None:
        html_b2 = '<p class="briefing-fallback">histórico insuficiente</p>'
    else:
        top_ab2 = top3_anbima[top3_anbima["delta_bps"] > 0].head(6)
        top_fe2 = top3_anbima[top3_anbima["delta_bps"] < 0].head(6)

        def _anbima_rows(df_an):
            rows = ""
            for _, r in df_an.iterrows():
                lbl     = str(r.get("label", "—"))[:14]
                tx_hoje = r.get("tx_ind")
                delta   = r.get("delta_bps", float("nan"))
                cls     = "up" if delta > 0 else "dn"
                sign    = "+" if delta > 0 else ""
                pct     = percentil_anbima(lbl, tx_hoje)
                if pct is None:
                    pct_html = '<span style="color:var(--text3)">—</span>'
                elif pct >= 80:
                    pct_html = f'<span class="cr-chip dn">p{pct}</span>'
                elif pct <= 20:
                    pct_html = f'<span class="cr-chip up">p{pct}</span>'
                else:
                    pct_html = f'<span style="color:var(--text3);font-size:10.5px;font-weight:600">p{pct}</span>'
                rows += (
                    f'<div class="briefing-row">'
                    f'<span class="nm" span style="width: 200%">{lbl}'
                    f'&nbsp;<span class="cr-chip {cls}" span style="text-align:center font-size:12px; font-weight:600">{sign}{delta:.0f} bps</span>'
                    f'</span></div>'
                )
            return rows or '<span style="color:var(--text3);font-size:11px">—</span>'

        html_b2 = (
            f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">'
            f'<div><div style="font-size:9.5px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.05em;color:var(--text3);margin-bottom:4px">Abertura ↑</div>'
            f'{_anbima_rows(top_ab2)}</div>'
            f'<div><div style="font-size:9.5px;font-weight:700;text-transform:uppercase;'
            f'letter-spacing:.05em;color:var(--text3);margin-bottom:4px">Fechamento ↓</div>'
            f'{_anbima_rows(top_fe2)}</div>'
            f'</div>'
        )

    # Card 3 — ofertas registradas no último dia do SRE
    if sre_err:
        html_b3 = f'<p class="briefing-fallback">SRE {sre_err}</p>'
    else:
        html_b3 = novas_html
    sre_titulo = f"SRE · ofertas {sre_data}" if sre_data else "SRE Pipeline"

    st.markdown(
        f'<div class="briefing-grid">'
        f'<div class="briefing-card"><h4>Spreads</h4>{html_b1}</div>'
        f'<div class="briefing-card"><h4>ANBIMA deb · spread</h4>{html_b2}</div>'
        f'<div class="briefing-card"><h4>{sre_titulo}</h4>{html_b3}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ================================================================
# PLACAR DE CALLS
# ================================================================
def _anbima_datas_disponiveis():
    """Lista ordenada de ref_date distintos em anbima_snapshots."""
    try:
        with _db() as con:
            return [r[0] for r in con.execute(
                "SELECT DISTINCT ref_date FROM anbima_snapshots ORDER BY ref_date"
            ).fetchall()]
    except Exception:
        return []


def render_placar_calls():
    """Placar de acerto das calls de manhã vs MTM ANBIMA D+1."""
    hist = load_calls_historico()
    if hist is None:
        st.info(
            "Nenhuma call registrada ainda. "
            "As calls passarão a ser salvas automaticamente a partir de hoje."
        )
        return

    # Só manhã tem referência de preço fechamento D-1 para comparar
    manha = hist[hist["session"] == "manha"].copy()
    if manha.empty:
        st.info("Nenhuma call de manhã registrada nos últimos 30 dias.")
        return

    # Busca snapshot ANBIMA de cada D+1 para as datas de call
    datas_anbima = _anbima_datas_disponiveis()
    if not datas_anbima:
        st.info("Sem snapshots ANBIMA no banco — histórico insuficiente.")
        return

    # Carrega todos os snapshots ANBIMA de uma vez
    try:
        with _db() as con:
            snap_rows = con.execute(
                "SELECT ref_date, label, tx_ind FROM anbima_snapshots"
            ).fetchall()
    except Exception:
        st.warning("Erro ao ler snapshots ANBIMA.")
        return

    snap_df = pd.DataFrame(snap_rows, columns=["ref_date", "label", "tx_ind"])

    # Para cada call, acha o primeiro ref_date > brt_date (D+1 ANBIMA)
    pares = []
    for _, row in manha.iterrows():
        brt = row["brt_date"]
        idx = bisect.bisect_right(datas_anbima, brt)
        if idx >= len(datas_anbima):
            continue
        ref_d1 = datas_anbima[idx]
        match = snap_df[(snap_df["ref_date"] == ref_d1) & (snap_df["label"] == row["label"])]
        if match.empty:
            continue
        tx_d1 = match.iloc[0]["tx_ind"]
        if tx_d1 is None:
            continue
        erro = (row["taxa"] - tx_d1) * 100
        pares.append({
            "label":    row["label"],
            "call_m":   row["taxa"],
            "mtm_d1":   tx_d1,
            "erro_bps": erro,
            "data":     brt,
            "ref_d1":   ref_d1,
        })

    if not pares:
        st.info("Histórico insuficiente — aguardando D+1 ANBIMA para os dias registrados.")
        return

    if len(pares) >= 3:
        erros = [p["erro_bps"] for p in pares if p.get("erro_bps") is not None]
        if erros:
            import statistics as _stats
            from collections import defaultdict as _dd
            mae  = round(sum(abs(e) for e in erros) / len(erros), 1)
            vies = round(sum(erros) / len(erros), 1)
            sinal_vies = "+" if vies > 0 else ""
            por_vertice = _dd(list)
            for p in pares:
                if p.get("erro_bps") is not None:
                    por_vertice[p["label"]].append(abs(p["erro_bps"]))
            vertice_pior = max(por_vertice, key=lambda v: sum(por_vertice[v]) / len(por_vertice[v]))
            mae_pior = round(sum(por_vertice[vertice_pior]) / len(por_vertice[vertice_pior]), 1)
            st.markdown(
                f'<div class="cr-kpis">'
                f'<div class="cr-kpi"><div class="l">MAE médio (todos)</div>'
                f'<div class="v">{mae} bps</div></div>'
                f'<div class="cr-kpi"><div class="l">Viés sistemático</div>'
                f'<div class="v">{sinal_vies}{vies} bps</div>'
                f'<div class="s" style="color:var(--text3)">'
                f'{"call acima do MTM" if vies > 0 else "call abaixo do MTM"}</div></div>'
                f'<div class="cr-kpi"><div class="l">Vértice mais impreciso</div>'
                f'<div class="v">{vertice_pior}</div>'
                f'<div class="s" style="color:var(--text3)">MAE {mae_pior} bps</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    meta = f"{len(pares)} par(es)" if len(pares) >= 3 else "histórico insuficiente"
    rows_html = ""
    for p in sorted(pares, key=lambda x: x["data"], reverse=True):
        erro = p["erro_bps"]
        cls  = "dp" if erro > 0 else ("dn" if erro < 0 else "d0")
        sign = "+" if erro > 0 else ""
        rows_html += (
            f'<tr>'
            f'<td class="ticker">{p["label"]}</td>'
            f'<td class="rate">{fr(p["call_m"])}</td>'
            f'<td class="rate">{fr(p["mtm_d1"])}</td>'
            f'<td>{fd2(erro, dec=1)}</td>'
            f'<td class="ticker">{p["data"]}</td>'
            f'</tr>'
        )
    render_table(
        [("Vértice", ""), ("Call M", ""), ("MTM D+1", ""), ("Erro bps", ""), ("Data", "")],
        rows_html,
        title="Acerto das calls · últimos 30 dias",
        meta=meta,
    )
    pares_df = pd.DataFrame(pares).rename(columns={
        "data":    "brt_date",
        "call_m":  "taxa",
        "mtm_d1":  "tx_ind_d1",
    })
    csv_bytes = pares_df[["brt_date", "label", "taxa", "tx_ind_d1", "erro_bps"]].to_csv(
        index=False, sep=";", encoding="utf-8-sig"
    ).encode()
    st.download_button(
        "Baixar placar (.csv)", csv_bytes,
        file_name=f"placar_calls_{_brt_today()}.csv", mime="text/csv",
    )


# ================================================================
# ENTRY POINT
# ================================================================
if __name__ == "__main__":
    main()