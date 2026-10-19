# -*- coding: utf-8 -*-
"""
01b — CVM Dados Abertos: Formulário de Referência (FRE) -> histórico de ações (total e tesouraria).

Por quê: o arquivo "composicao_capital" da DFP/ITR só existe a partir de 2020 nos dados abertos.
Para 2009–2019 usamos o FRE (disponível desde 2010), que traz:
  - capital_social           : quantidade de ações ON/PN do capital integralizado e data de aprovação
  - valor_mobiliario_tesouraria_movimentacao : saldo final de ações em tesouraria por exercício social
  - distribuicao_capital     : ações em circulação (free float, conceito de mercado) na data do FRE
Baixa fre_cia_aberta_AAAA.zip (2010–ano corrente) em raw/cvm/fre/ e extrai as linhas de
Gerdau S.A. (CNPJ 33.611.500/0001-19) e dos pares (CNPJs do cadastro, ver cvm_entidades.csv).

Saídas (Tabelas intermediárias (CSV)/): cvm_fre_capital_social.csv, cvm_fre_tesouraria_mov.csv, cvm_fre_distribuicao_capital.csv
Uso:  python -I 01b_cvm_fre_acoes.py [--forcar]   (rodar depois do 01_cvm_dfp_itr.py)
"""
import datetime as dt
import io
import os
import sys
import site
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import pandas as pd  # noqa: E402

from _comum import baixar, pasta_raw, pasta_tratados  # noqa: E402

FORCAR = "--forcar" in sys.argv
BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS"
RAW = pasta_raw(os.path.join("cvm", "fre"))
OUT = pasta_tratados()
ent = pd.read_csv(os.path.join(OUT, "cvm_entidades.csv"))
CNPJS = dict(zip(ent["CNPJ_CIA"], ent["EMPRESA"]))
ARQS = {"capital_social": [], "valor_mobiliario_tesouraria_movimentacao": [], "distribuicao_capital": []}

for ano in range(2010, dt.date.today().year + 1):
    nome = f"fre_cia_aberta_{ano}.zip"
    arq = os.path.join(RAW, nome)
    url = f"{BASE}/{nome}"
    if not baixar(url, arq, "CVM FRE", forcar=FORCAR or ano == dt.date.today().year and not os.path.exists(arq)):
        continue
    z = zipfile.ZipFile(arq)
    for chave in ARQS:
        n = f"fre_cia_aberta_{chave}_{ano}.csv"
        if n not in z.namelist():
            continue
        with z.open(n) as f:
            d = pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str)
        d = d[d["CNPJ_Companhia"].isin(CNPJS)].copy()
        d["EMPRESA"] = d["CNPJ_Companhia"].map(CNPJS)
        d["ARQUIVO_ZIP"] = nome
        d["URL_ZIP"] = url
        ARQS[chave].append(d)
    print(f"{nome}: lido")

saidas = {"capital_social": "cvm_fre_capital_social.csv",
          "valor_mobiliario_tesouraria_movimentacao": "cvm_fre_tesouraria_mov.csv",
          "distribuicao_capital": "cvm_fre_distribuicao_capital.csv"}
for chave, lst in ARQS.items():
    if lst:
        d = pd.concat(lst, ignore_index=True)
        d.to_csv(os.path.join(OUT, saidas[chave]), index=False)
        print(saidas[chave], len(d), "linhas")
