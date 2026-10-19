# -*- coding: utf-8 -*-
"""
02 — Dados de mercado (Yahoo Finance via yfinance).

Baixa preços diários (fechamento e fechamento ajustado) de GGBR4.SA, GGBR3.SA e ^BVSP
de 2005 até hoje, e os proventos (dividendos/JCP) e desdobramentos/bonificações de GGBR4.SA
e GGBR3.SA. Também baixa CSNA3.SA e USIM5.SA (pares) para eventual comparação.

Saídas (raw/yfinance/):
  precos_<ticker>.csv     -> Date, Open, High, Low, Close, Adj Close, Volume
  dividendos_<ticker>.csv -> Date, Dividends (R$ por ação, já ajustado por desdobramentos pelo Yahoo)
  splits_<ticker>.csv     -> Date, Stock Splits (fator)

Observações:
- O "Close" do Yahoo já é ajustado por desdobramentos/bonificações (não por proventos);
  o "Adj Close" é ajustado também por proventos (retorno total). Ver Fontes e notas dos dados.md.
- Se o yfinance falhar, tenta-se a API do stooq (CSV) como alternativa para os preços.
Uso:  python -I 02_precos_yfinance.py [--forcar]
"""
import io
import os
import sys

import site  # noqa: E402
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import pandas as pd  # noqa: E402
import requests  # noqa: E402

from _comum import HEADERS, pasta_raw, registrar  # noqa: E402

TICKERS = ["GGBR4.SA", "GGBR3.SA", "^BVSP", "CSNA3.SA", "USIM5.SA"]
INICIO = "2005-01-01"
FORCAR = "--forcar" in sys.argv
PASTA = pasta_raw("yfinance")


def nome(t):
    return t.replace("^", "").replace(".", "_")


def via_yfinance(t):
    import yfinance as yf
    tk = yf.Ticker(t)
    # auto_adjust=False para manter Close e Adj Close separados
    df = tk.history(start=INICIO, auto_adjust=False, actions=True)
    if df is None or df.empty:
        raise RuntimeError("vazio")
    df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
    df.index.name = "Date"
    return df


def via_stooq(t):
    # Alternativa: stooq (sem Adj Close). Símbolos: ggbr4.br? stooq não cobre bem a B3; ^bvp para Ibovespa
    mapa = {"^BVSP": "^bvp"}
    s = mapa.get(t, t.lower().replace(".sa", ""))
    url = f"https://stooq.com/q/d/l/?s={s}&i=d"
    r = requests.get(url, headers=HEADERS, timeout=60)
    df = pd.read_csv(io.StringIO(r.text), parse_dates=["Date"]).set_index("Date")
    if df.empty:
        raise RuntimeError("stooq vazio")
    return df, url


for t in TICKERS:
    arq = os.path.join(PASTA, f"precos_{nome(t)}.csv")
    if os.path.exists(arq) and not FORCAR:
        print(f"{t}: já existe ({arq}); use --forcar para atualizar")
        continue
    print(f"{t}: baixando...")
    try:
        df = via_yfinance(t)
        url = f"https://finance.yahoo.com/quote/{t} (yfinance Ticker.history, auto_adjust=False)"
        cols = [c for c in ["Open", "High", "Low", "Close", "Adj Close", "Volume"] if c in df.columns]
        df[cols].to_csv(arq)
        registrar("Yahoo Finance", url, arq, f"{len(df)} pregões {df.index.min().date()} a {df.index.max().date()}")
        if "Dividends" in df.columns:
            d = df.loc[df["Dividends"] != 0, ["Dividends"]]
            a = os.path.join(PASTA, f"dividendos_{nome(t)}.csv")
            d.to_csv(a)
            registrar("Yahoo Finance", url, a, f"{len(d)} eventos")
        if "Stock Splits" in df.columns:
            s = df.loc[df["Stock Splits"] != 0, ["Stock Splits"]]
            a = os.path.join(PASTA, f"splits_{nome(t)}.csv")
            s.to_csv(a)
            registrar("Yahoo Finance", url, a, f"{len(s)} eventos")
        print(f"  ok: {len(df)} linhas, {df.index.min().date()} a {df.index.max().date()}")
    except Exception as e:  # noqa: BLE001
        print(f"  yfinance falhou ({e}); tentando stooq")
        try:
            df, url = via_stooq(t)
            df.to_csv(arq)
            registrar("stooq", url, arq, "alternativa ao Yahoo (sem Adj Close)")
            print(f"  ok via stooq: {len(df)} linhas")
        except Exception as e2:  # noqa: BLE001
            print(f"  stooq também falhou: {e2}")
