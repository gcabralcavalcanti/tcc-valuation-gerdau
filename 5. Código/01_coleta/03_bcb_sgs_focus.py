# -*- coding: utf-8 -*-
"""
03 — Banco Central do Brasil: séries SGS e expectativas Focus (API Olinda).

SGS (https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial=..&dataFinal=..)
  A API limita séries diárias a 10 anos por consulta -> baixamos em blocos de 5 anos e juntamos.
  12    CDI (% a.d.)                          diária
  11    Selic efetiva (% a.d.)                diária
  432   Meta Selic (% a.a.)                   diária
  1     PTAX venda (R$/US$)                   diária
  433   IPCA (% a.m.)                         mensal
  24363 IBC-Br (índice, sem ajuste sazonal)   mensal
  7326  PIB real (var. % anual)               anual

Focus (Olinda, ExpectativasMercadoAnuais): PIB Total, IPCA, Câmbio, Selic.
  Para manter pequeno, amostramos a ÚLTIMA data de pesquisa de cada mês (base de cálculo 0 =
  todos os respondentes), guardando mediana, média, desvio, mín., máx. e nº de respondentes,
  para os anos de referência = ano da pesquisa até ano+4.

Saídas: raw/bcb/sgs_<codigo>.csv  e  raw/bcb/focus_anuais_<indicador>.csv (bruto completo
da API por indicador) + Tabelas intermediárias (CSV)/focus_mensal.csv (amostra mensal).
Uso:  python -I 03_bcb_sgs_focus.py [--forcar]
"""
import datetime as dt
import os
import sys
import site
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import pandas as pd  # noqa: E402

from _comum import get_json, pasta_raw, pasta_tratados, registrar  # noqa: E402

FORCAR = "--forcar" in sys.argv
PASTA = pasta_raw("bcb")
INICIO = 2000
HOJE = dt.date.today()

SERIES = {
    12: "CDI (% a.d.)",
    11: "Selic efetiva (% a.d.)",
    432: "Meta Selic (% a.a.)",
    1: "PTAX venda (R$/US$)",
    433: "IPCA (% a.m.)",
    24363: "IBC-Br (índice 2002=100, sem ajuste)",
    7326: "PIB real (var. % anual)",
}


def baixar_sgs(cod):
    arq = os.path.join(PASTA, f"sgs_{cod}.csv")
    if os.path.exists(arq) and not FORCAR:
        print(f"SGS {cod}: já existe")
        return
    partes = []
    for ini in range(INICIO, HOJE.year + 1, 5):
        fim = min(dt.date(ini + 4, 12, 31), HOJE)
        url = (f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json"
               f"&dataInicial=01/01/{ini}&dataFinal={fim:%d/%m/%Y}")
        js = get_json(url)  # se um bloco falhar após as tentativas, o script para (evita lacunas silenciosas)
        if isinstance(js, list) and js:
            partes.append(pd.DataFrame(js))
    df = pd.concat(partes).drop_duplicates("data")
    df["data"] = pd.to_datetime(df["data"], dayfirst=True)
    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
    df = df.sort_values("data")
    df.to_csv(arq, index=False)
    registrar("BCB-SGS", f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json (blocos de 5 anos desde {INICIO})",
              arq, f"{SERIES[cod]}; {len(df)} obs {df.data.min().date()} a {df.data.max().date()}")
    print(f"SGS {cod}: {len(df)} obs {df.data.min().date()} a {df.data.max().date()}")


for c in SERIES:
    baixar_sgs(c)

# ---------------- Focus ----------------
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais"
INDICADORES = {"PIB Total": "pib", "IPCA": "ipca", "Câmbio": "cambio", "Selic": "selic"}

amostras = []
for ind, apelido in INDICADORES.items():
    arq = os.path.join(PASTA, f"focus_anuais_{apelido}.csv")
    if not os.path.exists(arq) or FORCAR:
        filtro = f"Indicador eq '{ind}'"
        url = (OLINDA + "?$filter=" + urllib.parse.quote(filtro) + "&$format=json&$top=1000000")
        # obs.: o parâmetro $select provoca erro 403 no firewall do Olinda; por isso baixamos todas as colunas
        js = get_json(url, timeout=600)
        df = pd.DataFrame(js["value"])
        df.to_csv(arq, index=False)
        registrar("BCB-Focus (Olinda)", url, arq, f"{len(df)} linhas")
        print(f"Focus {ind}: {len(df)} linhas")
    df = pd.read_csv(arq)
    df["Data"] = pd.to_datetime(df["Data"])
    df = df[df["baseCalculo"] == 0]
    if "IndicadorDetalhe" in df.columns:  # alguns indicadores têm detalhe (ex.: Câmbio "Fim do ano"/"Média do ano")
        df = df[df["IndicadorDetalhe"].isna() | df["IndicadorDetalhe"].astype(str).str.contains("Fim", case=False)
                | (df["IndicadorDetalhe"].astype(str) == "nan")]
    df["mes"] = df["Data"].dt.to_period("M")
    ult = df.groupby("mes")["Data"].transform("max")
    df = df[df["Data"] == ult]
    df["DataReferencia"] = pd.to_numeric(df["DataReferencia"], errors="coerce")
    df = df[(df["DataReferencia"] >= df["Data"].dt.year) & (df["DataReferencia"] <= df["Data"].dt.year + 4)]
    amostras.append(df.drop(columns="mes"))

foc = pd.concat(amostras).sort_values(["Indicador", "Data", "DataReferencia"])
foc.to_csv(os.path.join(pasta_tratados(), "focus_mensal.csv"), index=False)
print("Focus mensal:", len(foc), "linhas", foc["Data"].min().date(), "a", foc["Data"].max().date())
