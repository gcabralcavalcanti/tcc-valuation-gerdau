"""
04b — Séries de mercado para o custo de capital (custo da dívida e prêmio de risco), sem chave de API.

  FRED BAA     Moody's Seasoned Baa Corporate Bond Yield (% a.a., mensal) — spread de crédito da classe de
               rating da Gerdau (grau de investimento: BBB-/Baa nos 20-F de 2020 a 2024)
  FRED GS10    Treasury de 10 anos dos EUA (% a.a., mensal) — base do spread (BAA − GS10)
  Ipeadata     EMBI+ Brasil (JPM366_EMBI366, pontos-base, diário) — spread de default do país
  Tesouro      taxas diárias dos títulos do Tesouro Direto (Tesouro Transparente): NTN-F (Tesouro Prefixado com
               Juros Semestrais), o prefixado mais longo do governo — base da taxa livre de risco
  Shiller      ie_data.xls (shillerdata.com): índices mensais de retorno total REAL do S&P Composite e dos
               títulos de 10 anos dos EUA desde 1871 — prêmio maduro histórico, calculado no notebook

Saídas: raw/fred/BAA.csv, raw/fred/GS10.csv, raw/ipeadata/embi_brasil.json, raw/tesouro/precotaxatesourodireto.csv,
raw/shiller/ie_data.xls e, em Tabelas intermediárias (CSV)/: spread_baa_mensal.csv, embi_diario.csv, ntnf_diario.csv,
retornos_eua_dezembro.csv.
Uso:  python -I 04b_mercado_custo_capital.py [--forcar]
"""

import json
import os
import re
import site
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import pandas as pd  # noqa: E402
import requests  # noqa: E402
from _comum import HEADERS, baixar, pasta_raw, pasta_tratados  # noqa: E402

FORCAR = "--forcar" in sys.argv
TRATADOS = pasta_tratados()

# ------------------------------------------------------------------ FRED: Baa e Treasury de 10 anos
serie = {}
for s, desc in {
    "BAA": "Moody's Seasoned Baa Corporate Bond Yield (% a.a.)",
    "GS10": "Treasury de 10 anos dos EUA, média mensal (% a.a.)",
}.items():
    arq = os.path.join(pasta_raw("fred"), f"{s}.csv")
    if not baixar(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", arq, "FRED", forcar=FORCAR, obs=desc):
        sys.exit(f"Sem a série {s} do FRED")
    d = pd.read_csv(arq)
    serie[s] = pd.Series(pd.to_numeric(d.iloc[:, 1], errors="coerce").values, index=pd.to_datetime(d.iloc[:, 0]))
spread = pd.DataFrame({"baa": serie["BAA"], "gs10": serie["GS10"]}).dropna()
spread["spread_baa"] = spread["baa"] - spread["gs10"]
spread.rename_axis("mes").to_csv(os.path.join(TRATADOS, "spread_baa_mensal.csv"))

# ------------------------------------------------------------------ Ipeadata: EMBI+ Brasil
arq = os.path.join(pasta_raw("ipeadata"), "embi_brasil.json")
url = "http://www.ipeadata.gov.br/api/odata4/ValoresSerie(SERCODIGO='JPM366_EMBI366')"
if not baixar(url, arq, "Ipeadata", forcar=FORCAR, obs="EMBI+ Risco-Brasil (JP Morgan), pontos-base, diário"):
    sys.exit("Sem o EMBI+ do Ipeadata")
v = pd.DataFrame(json.load(open(arq, encoding="utf-8"))["value"])
embi = pd.DataFrame({"data": pd.to_datetime(v["VALDATA"].str[:10]), "embi_pb": v["VALVALOR"]}).dropna()
embi.sort_values("data").to_csv(os.path.join(TRATADOS, "embi_diario.csv"), index=False)

# ------------------------------------------------------------------ Tesouro Direto: NTN-F
# Taxa de compra da manhã (a que o Tesouro oferece ao investidor), % a.a., por vencimento e dia.
arq = os.path.join(pasta_raw("tesouro"), "precotaxatesourodireto.csv")
url = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/"
    "resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)
if not baixar(url, arq, "Tesouro Transparente", forcar=FORCAR, obs="Taxas dos títulos ofertados pelo Tesouro Direto"):
    sys.exit("Sem as taxas do Tesouro Direto")
td = pd.read_csv(arq, sep=";", decimal=",")
td = td[td["Tipo Titulo"] == "Tesouro Prefixado com Juros Semestrais"]
ntnf = pd.DataFrame(
    {
        "data": pd.to_datetime(td["Data Base"], dayfirst=True),
        "vencimento": pd.to_datetime(td["Data Vencimento"], dayfirst=True),
        "taxa_compra": td["Taxa Compra Manha"],
    }
)
ntnf = ntnf[ntnf["taxa_compra"] > 0].sort_values(["data", "vencimento"])
ntnf.to_csv(os.path.join(TRATADOS, "ntnf_diario.csv"), index=False)

# ------------------------------------------------------------------ Shiller: retornos totais reais dos EUA
# O link do arquivo muda a cada atualização; lê o link atual na página do site.
arq = os.path.join(pasta_raw("shiller"), "ie_data.xls")
if FORCAR or not os.path.exists(arq):
    pagina = requests.get("https://shillerdata.com/", headers=HEADERS, timeout=60).text
    link = re.search(r'href="(//[^"]*/ie_data\.xls[^"]*)"', pagina)
    if not link:
        sys.exit("Não achei o link do ie_data.xls em shillerdata.com")
    baixar(
        "https:" + link.group(1),
        arq,
        "Shiller",
        forcar=True,
        obs="ie_data.xls: S&P Composite e títulos de 10 anos, retornos totais reais mensais desde 1871",
    )
sh = pd.read_excel(arq, sheet_name="Data", header=None, skiprows=8)
sh = sh[[0, 9, 18]].copy()
sh.columns = ["data", "acoes_tr_real", "titulos_tr_real"]
sh = sh[pd.to_numeric(sh["data"], errors="coerce").notna()].dropna()
sh["ano"] = sh["data"].astype(float).astype(int)
sh["mes"] = ((sh["data"].astype(float) - sh["ano"]) * 100).round().astype(int)  # 1871.01 ... 1871.12
dez = sh[sh["mes"] == 12][["ano", "acoes_tr_real", "titulos_tr_real"]]
dez.to_csv(os.path.join(TRATADOS, "retornos_eua_dezembro.csv"), index=False)

print(
    f"spread Baa: {spread.index.min():%Y-%m} a {spread.index.max():%Y-%m}; "
    f"EMBI: {embi['data'].min():%Y-%m-%d} a {embi['data'].max():%Y-%m-%d}; "
    f"NTN-F: {ntnf['data'].min():%Y-%m-%d} a {ntnf['data'].max():%Y-%m-%d}; "
    f"Shiller (dezembros): {dez['ano'].min()} a {dez['ano'].max()}"
)
