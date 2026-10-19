# -*- coding: utf-8 -*-
"""
04 — Séries setoriais do FRED (Federal Reserve Bank of St. Louis), sem chave de API.

URL: https://fred.stlouisfed.org/graph/fredgraph.csv?id=<SERIE>
Séries (todas mensais):
  WPU101       PPI EUA: Iron and Steel (índice 1982=100)
  WPU1017      PPI EUA: Steel Mill Products (índice 1982=100)
  WPU101704    PPI EUA: Hot Rolled Bars, Plates, and Structural Shapes (proxy de laminados a quente longos/planos)
  WPU101703    PPI EUA: Hot Rolled Steel Sheet and Strip, incl. tin mill (proxy de bobina a quente — HRC;
               DESCONTINUADA em fev/2022 no FRED)
  PCU3311103311105  idem, ótica da indústria (também termina em fev/2022)
  WPU101702    PPI EUA: Semifinished Steel Mill Products (tarugos/placas)
  WPU101705    PPI EUA: Steel Wire (fio-máquina/arame — produto de aço longo)
  PCU331110331110  PPI EUA: Iron and Steel Mills and Ferroalloy Mfg (indústria)
  WPU1012      PPI EUA: Iron and Steel Scrap (sucata — insumo das aciarias elétricas da Gerdau)
  PIORECRUSDM  Preço global do minério de ferro (US$/tonelada métrica, FMI)
Séries que não existirem/retornarem erro são apenas registradas como indisponíveis.
Saídas: raw/fred/<SERIE>.csv e Tabelas intermediárias (CSV)/fred_disponibilidade.csv
Uso:  python -I 04_fred_setor.py [--forcar]
"""
import io
import os
import sys
import site

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import pandas as pd  # noqa: E402

from _comum import baixar, pasta_raw, pasta_tratados  # noqa: E402

FORCAR = "--forcar" in sys.argv
PASTA = pasta_raw("fred")
SERIES = {
    "WPU101": "PPI EUA - Iron and steel (1982=100)",
    "WPU1017": "PPI EUA - Steel mill products (1982=100)",
    "WPU101704": "PPI EUA - Hot rolled bars, plates and structural shapes (1982=100)",
    "WPU101703": "PPI EUA - Hot rolled steel sheet and strip, incl. tin mill (proxy HRC; descontinuada fev/2022)",
    "PCU3311103311105": "PPI EUA indústria - Hot rolled steel sheet and strip (proxy HRC; descontinuada fev/2022)",
    "WPU101702": "PPI EUA - Semifinished steel mill products (1982=100)",
    "WPU101705": "PPI EUA - Steel wire (1982=100)",
    "PCU331110331110": "PPI EUA - Iron and steel mills and ferroalloy mfg (indústria)",
    "WPU1012": "PPI EUA - Iron and steel scrap (1982=100)",
    "PIORECRUSDM": "Preço global do minério de ferro (US$/t, FMI)",
}

disp = []
for s, desc in SERIES.items():
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}"
    arq = os.path.join(PASTA, f"{s}.csv")
    ok = baixar(url, arq, "FRED", forcar=FORCAR, obs=desc)
    info = {"serie": s, "descricao": desc, "url": url, "disponivel": False}
    if ok:
        try:
            d = pd.read_csv(arq)
            d.columns = ["data", "valor"]
            d["valor"] = pd.to_numeric(d["valor"], errors="coerce")
            d = d.dropna()
            info.update(disponivel=True, inicio=d["data"].min(), fim=d["data"].max(), n_obs=len(d))
        except Exception as e:  # noqa: BLE001  (ex.: FRED devolve HTML quando a série não existe)
            info["erro"] = str(e)[:100]
            os.remove(arq)
    disp.append(info)
    print(info)

pd.DataFrame(disp).to_csv(os.path.join(pasta_tratados(), "fred_disponibilidade.csv"), index=False)
