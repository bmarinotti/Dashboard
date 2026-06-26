"""Funções puras de seleção/ranqueamento dos 'Destaques do Dia'.

Sem dependência de Streamlit nem de rede: recebem estruturas Python simples
(listas/dicts) e devolvem listas de itens normalizados — testáveis de forma
isolada com pytest. A orquestração/render vive em app.py (render_destaques),
que busca os dados (cacheados) e chama estas funções.

Item normalizado (dict):
    {
      "secao":  str,                 # "acoes" | "comunicados" | "juros" | "spreads" | "sre"
      "titulo": str,
      "detalhe": str,
      "valor":  float | None,        # valor BRUTO (a camada de render formata via fr/fd2)
      "delta":  float | None,        # variação BRUTA (% para ações, bps para juros/spreads)
      "data":   date | datetime | None,
      "link":   str | None,
    }
"""
from __future__ import annotations

import unicodedata
from datetime import date, datetime


# Categorias de "alto sinal" do Plantão B3 (normalizadas: minúsculas, sem acento).
_CATEGORIAS_ALTO_SINAL = {
    "fato relevante",
    "aviso aos acionistas",
    "outros comunicados ao mercado",
}

# Palavras-chave fortes (normalizadas) que promovem um comunicado a destaque.
_KEYWORDS = {
    "provento", "jcp", "juros sobre capital", "dividendo", "recompra",
    "subscri", "oferta", "aquisi", "incorpora", "fus", "rating", "relevante",
}


def _norm(s) -> str:
    """Minúsculas, sem acento — para casamento de categorias/palavras-chave."""
    s = str(s or "").lower().strip()
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def _as_date(d):
    """Coage datetime/Timestamp para date; mantém date; None -> None."""
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    # pandas.Timestamp e afins expõem .date()
    fn = getattr(d, "date", None)
    if callable(fn):
        try:
            return fn()
        except Exception:
            return None
    return None


def _sort_key_data(d):
    """Chave de ordenação por data (None vai para o fim em reverse=True)."""
    dd = _as_date(d)
    return dd or date.min


# ── 1) Ações em movimento ─────────────────────────────────────────
def destaques_acoes(quotes, limiar_pct=2.0):
    """quotes: [{"name","ticker","group","price","prev"}].
    Mantém |Δ%| >= limiar_pct; ordena por |Δ%| desc."""
    itens = []
    for q in (quotes or []):
        price, prev = q.get("price"), q.get("prev")
        if not price or not prev:
            continue
        try:
            pct = (price - prev) / prev * 100.0
        except ZeroDivisionError:
            continue
        if abs(pct) < limiar_pct:
            continue
        itens.append({
            "secao": "acoes",
            "titulo": q.get("ticker") or q.get("name") or "—",
            "detalhe": q.get("name", ""),
            "valor": price,
            "delta": pct,
            "data": None,
            "link": None,
        })
    itens.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return itens


# ── 2) Comunicados & Fatos Relevantes ─────────────────────────────
def destaques_comunicados(itens, categorias=None, keywords=None):
    """itens: [{"empresa","ticker","data","desc","link"}].
    Mantém se a descrição casa uma categoria de alto sinal OU uma palavra-chave;
    ordena por data desc."""
    cats = _CATEGORIAS_ALTO_SINAL if categorias is None else {_norm(c) for c in categorias}
    kws = _KEYWORDS if keywords is None else {_norm(k) for k in keywords}
    out = []
    for it in (itens or []):
        desc = it.get("desc", "")
        d = _norm(desc)
        if not d:
            continue
        casa = any(c in d for c in cats) or any(k in d for k in kws)
        if not casa:
            continue
        out.append({
            "secao": "comunicados",
            "titulo": it.get("empresa") or it.get("ticker") or "—",
            "detalhe": desc,
            "valor": None,
            "delta": None,
            "data": it.get("data"),
            "link": it.get("link"),
        })
    out.sort(key=lambda x: _sort_key_data(x["data"]), reverse=True)
    return out


# ── 3) Maiores movimentos de juros (DI + NTN-B) ───────────────────
def destaques_juros(serie_hoje, serie_prev, top_n=5):
    """serie_hoje/serie_prev: {rotulo: taxa(%)}.
    Δbps = (hoje - prev) * 100; top_n por |Δbps| desc. Ignora rótulo sem par."""
    prev = serie_prev or {}
    out = []
    for rotulo, taxa in (serie_hoje or {}).items():
        p = prev.get(rotulo)
        if taxa is None or p is None:
            continue
        try:
            delta_bps = (float(taxa) - float(p)) * 100.0
        except (TypeError, ValueError):
            continue
        out.append({
            "secao": "juros",
            "titulo": rotulo,
            "detalhe": "",
            "valor": float(taxa),
            "delta": delta_bps,
            "data": None,
            "link": None,
        })
    out.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return out[:top_n] if top_n else out


# ── 4) Spreads de crédito abrindo/fechando ────────────────────────
def destaques_spreads(registros, limiar_bps):
    """registros: [{"run_type","emissor","ativo","delta"(bps),
                    "indexador","compra","venda","mid","spread_b"}].
    Mantém |delta| >= limiar_bps; ordena por |delta| desc. Propaga os campos
    de exibição (indexador/compra/venda/mid/spread_b) p/ a camada de render
    montar a taxa, o bid/ask e o Spread Over B."""
    limiar = abs(limiar_bps) if limiar_bps else 0
    out = []
    for r in (registros or []):
        delta = r.get("delta")
        if delta is None or abs(delta) < limiar:
            continue
        rt = r.get("run_type", "")
        ativo = r.get("ativo", "")
        detalhe = " · ".join(p for p in (f"{rt}+" if rt else "", ativo) if p)
        out.append({
            "secao": "spreads",
            "titulo": r.get("emissor") or ativo or "—",
            "detalhe": detalhe,
            "valor": None,
            "delta": float(delta),
            "data": None,
            "link": None,
            "indexador": r.get("indexador"),
            "compra": r.get("compra"),
            "venda": r.get("venda"),
            "mid": r.get("mid"),
            "anbima": r.get("anbima"),   # taxa NTN-B de ref. (p/ Spread Over B do IPCA)
            "run_type": rt,
        })
    out.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return out


def _is_num(x):
    """True se x é número real (não None, não NaN). numpy floats contam."""
    return isinstance(x, (int, float)) and not isinstance(x, bool) and x == x


def bid_ask_taxa(compra, venda):
    """Ordena um par de TAXAS (yield) em (bid, ask): o bid é a MAIOR taxa e o
    ask a MENOR — em renda fixa, yield maior = preço menor, então o bid (compra)
    tem taxa acima do ask (venda). Robusto a dado invertido (convenção de preço).
    Retorna (None, None) se faltar algum valor."""
    if not (_is_num(compra) and _is_num(venda)):
        return None, None
    return (compra, venda) if compra >= venda else (venda, compra)


def fmt_spread_row(item, fr):
    """Monta as duas strings de exibição de um item de spread:
      taxa: '<indexador> <mid>%'   (taxa atual logo após o indexador)
      meio (sem repetir o indexador) — sempre bid (MAIOR taxa) antes do ask:
            CDI  -> '<bid> / <ask>%'             (taxas nominais)
            IPCA -> '<bid_SOB> / <ask_SOB> bps'  (bid/ask em Spread Over B,
                    cada um = (taxa - anbima)*100; sem prefixo "B+")
            '—' quando faltar dado
    `fr` é o formatador numérico do app (fr(valor, casas) -> str) — injetado
    para manter este módulo livre de dependências de UI."""
    idx = (item.get("indexador") or "").strip()
    mid = item.get("mid")
    bid, ask = bid_ask_taxa(item.get("compra"), item.get("venda"))
    taxa = f"{idx} {fr(mid, 2)}%" if (idx and _is_num(mid)) else idx
    if "IPCA" in idx.upper():
        an = item.get("anbima")
        if bid is not None and _is_num(an):
            meio = f"{(bid - an) * 100:.0f} / {(ask - an) * 100:.0f} bps".replace("-", "−")
        else:
            meio = "—"
    else:
        meio = f"{fr(bid, 2)} / {fr(ask, 2)}%" if bid is not None else "—"
    return taxa, meio


# ── Link público da oferta no SRE da CVM ──────────────────────────
_SRE_OFERTA_BASE = "https://web.cvm.gov.br/sre-publico-cvm/#/oferta-publica/"


def sre_oferta_url(numero):
    """URL pública da oferta no SRE da CVM a partir do Numero_Requerimento.
    Retorna None se o número for vazio/ausente. Tolera número vindo como float
    (ex.: '396.0' -> '.../396')."""
    if numero is None:
        return None
    s = str(numero).strip()
    if not s or s.lower() in ("nan", "none", "—"):
        return None
    if s.endswith(".0"):
        s = s[:-2]
    return _SRE_OFERTA_BASE + s


# ── 5) Novidades no primário (SRE) ────────────────────────────────
# Tipos cujo título usa o DEVEDOR (lastro) no lugar do emissor (a securitizadora).
_SRE_TIPOS_USA_DEVEDOR = {"cri", "cra", "securitizacao"}


def destaques_sre(ofertas, d1, d0):
    """ofertas: [{"emissor","tipo","volume","data","link"(opc.),"devedor"(opc.)}].
    Mantém d1 <= data <= d0; ordena por data desc, depois volume desc.
    Para CRI/CRA/Securitização o título usa o DEVEDOR (o lastro) no lugar do
    emissor (a securitizadora), caindo de volta no emissor se o devedor faltar.
    Propaga o 'link' (URL da oferta no SRE) para o item normalizado."""
    di, df = _as_date(d1), _as_date(d0)
    out = []
    for o in (ofertas or []):
        dd = _as_date(o.get("data"))
        if dd is None or (di and dd < di) or (df and dd > df):
            continue
        dev = str(o.get("devedor") or "").strip()
        usa_dev = (_norm(o.get("tipo")) in _SRE_TIPOS_USA_DEVEDOR
                   and dev and dev.lower() not in ("nan", "none", "—"))
        titulo = (dev if usa_dev else (o.get("emissor") or "")) or "—"
        out.append({
            "secao": "sre",
            "titulo": titulo,
            "detalhe": o.get("tipo", ""),
            "valor": o.get("volume"),
            "delta": None,
            "data": o.get("data"),
            "link": o.get("link"),
        })
    out.sort(key=lambda x: (_sort_key_data(x["data"]), x["valor"] or 0), reverse=True)
    return out
