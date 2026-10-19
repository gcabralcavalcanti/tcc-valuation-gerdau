"""
06 — Monta a base completa "4. Dados Gerdau/Tabelas intermediárias (CSV)/Base completa (arquivo).xlsx" (sobrescreve).
A planilha enxuta, que vai para o GitHub, é gerada depois pelo 07.

Lê os arquivos de raw/ e Tabelas intermediárias (CSV)/ gerados pelos scripts 01–05 e grava uma aba por tema, em formato
"tidy"/painel, para o Colab ler com pd.read_excel(url_raw, sheet_name=...).
Abas: LEIAME, Datas_base, Fundamentos_anuais, Fundamentos_trimestrais, DFP_contas, ITR_contas,
      Mapeamento_contas, Acoes, Precos_diarios, Proventos, Macro_diario, Macro_mensal, Macro_anual,
      Setor, Pares
Uso:  python -I 06_montar_planilha.py
"""

import os
import site
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from _comum import LOG_PROVENIENCIA, PASTA_RAW, pasta_tratados
from _comum import PLANILHA_COMPLETA as PLANILHA  # noqa: E402

TR = pasta_tratados()
RAW = PASTA_RAW
prov = pd.read_csv(LOG_PROVENIENCIA)


def coleta(padrao):
    """Data de coleta (mais recente) dos arquivos raw cujo caminho contém `padrao`."""
    x = prov[prov["arquivo"].str.contains(padrao, regex=False)]
    return x["data_coleta"].max()[:10] if not x.empty else ""


def rd(*p, **kw):
    return pd.read_csv(os.path.join(*p), **kw)


abas = {}
dic = []  # dicionário do LEIAME


def doc(aba, variavel, descricao, unidade, fonte, url, data_coleta):
    dic.append(
        {
            "aba": aba,
            "variavel": variavel,
            "descricao": descricao,
            "unidade": unidade,
            "fonte": fonte,
            "url": url,
            "data_coleta": data_coleta,
        }
    )


URL_CVM = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/"
DC_CVM = coleta("/cvm/")

# ------------------------------------------------------------------ Fundamentos
FA = rd(TR, "fundamentos_anuais.csv")
FT = rd(TR, "fundamentos_trimestrais.csv")
abas["Fundamentos_anuais"] = FA[FA["empresa"] == "GERDAU"].drop(columns=["empresa"])
abas["Fundamentos_trimestrais"] = FT
DESCR = {
    "receita_liquida": ("Receita líquida de vendas (DRE 3.01)", "R$ mil"),
    "cpv": ("Custo dos produtos vendidos (DRE 3.02; negativo)", "R$ mil"),
    "lucro_bruto": ("Resultado bruto (DRE 3.03)", "R$ mil"),
    "despesas_operacionais": ("Despesas/receitas operacionais (DRE 3.04; inclui impairment e equivalência)", "R$ mil"),
    "impairment": (
        "Perdas/reversões por não recuperabilidade de ativos (linhas 3.04.xx com 'recuperabilidade')",
        "R$ mil",
    ),
    "equivalencia_patrimonial": ("Resultado de equivalência patrimonial (3.04.xx)", "R$ mil"),
    "ebit": ("Resultado antes do resultado financeiro e dos tributos (DRE 3.05)", "R$ mil"),
    "ebit_ex_impairment": ("EBIT − impairment (EBIT recorrente; calculado)", "R$ mil"),
    "da": ("Depreciação, amortização e exaustão (DFC, ajuste ao lucro com 'deprecia')", "R$ mil"),
    "ebitda": ("EBIT + D&A (calculado)", "R$ mil"),
    "resultado_financeiro": ("Resultado financeiro (DRE 3.06)", "R$ mil"),
    "receitas_financeiras": ("Receitas financeiras (DRE 3.06.01)", "R$ mil"),
    "despesas_financeiras": ("Despesas financeiras (DRE 3.06.02; inclui variação cambial negativa)", "R$ mil"),
    "despesa_juros_dfc": ("Despesa de juros sobre dívidas (ajuste na DFC; exclui arrendamento)", "R$ mil"),
    "juros_pagos_dfc": ("Juros pagos de empréstimos (DFC; negativo)", "R$ mil"),
    "lair": ("Resultado antes dos tributos (DRE 3.07)", "R$ mil"),
    "ir_cs": ("IR e CSLL (DRE 3.08; negativo = despesa)", "R$ mil"),
    "lucro_liquido": ("Lucro líquido consolidado (DRE 3.11)", "R$ mil"),
    "lucro_controladores": ("Lucro atribuído aos controladores (DRE 3.11.01)", "R$ mil"),
    "lucro_nao_controladores": ("Lucro atribuído aos não controladores (DRE 3.11.02)", "R$ mil"),
    "lpa_basico_on": ("Lucro básico por ação ON (DRE 3.99.01.01)", "R$/ação"),
    "lpa_basico_pn": ("Lucro básico por ação PN (DRE 3.99.01.02)", "R$/ação"),
    "capex_imobilizado": ("Aquisições de imobilizado (DFC investimento; positivo)", "R$ mil"),
    "capex_intangivel": ("Aquisições de intangível (DFC investimento; positivo)", "R$ mil"),
    "capex": ("Capex total = imobilizado + intangível", "R$ mil"),
    "dividendos_jcp_pagos_dfc": ("Dividendos e JCP pagos (DFC financiamento)", "R$ mil"),
    "contas_receber": ("Contas a receber CP (BPA 1.01.03)", "R$ mil"),
    "estoques": ("Estoques (BPA 1.01.04)", "R$ mil"),
    "fornecedores": ("Fornecedores CP (BPP 2.01.02)", "R$ mil"),
    "caixa_equivalentes": ("Caixa e equivalentes (BPA 1.01.01)", "R$ mil"),
    "aplicacoes_financeiras_cp": ("Aplicações financeiras CP (BPA 1.01.02)", "R$ mil"),
    "caixa_aplicacoes": ("Caixa + aplicações financeiras CP", "R$ mil"),
    "emprestimos_financiamentos_cp": ("Empréstimos e financiamentos CP (2.01.04.01)", "R$ mil"),
    "debentures_cp": ("Debêntures CP (2.01.04.02)", "R$ mil"),
    "arrend_financeiro_cp": ("Financiamento por arrendamento CP (2.01.04.03)", "R$ mil"),
    "emprestimos_cp_total": ("Empréstimos e financiamentos CP, total (2.01.04)", "R$ mil"),
    "emprestimos_financiamentos_lp": ("Empréstimos e financiamentos LP (2.02.01.01)", "R$ mil"),
    "debentures_lp": ("Debêntures LP (2.02.01.02)", "R$ mil"),
    "arrend_financeiro_lp": ("Financiamento por arrendamento LP (2.02.01.03)", "R$ mil"),
    "emprestimos_lp_total": ("Empréstimos e financiamentos LP, total (2.02.01)", "R$ mil"),
    "divida_bruta": ("Dívida bruta = 2.01.04 + 2.02.01 (inclui debêntures; exclui arrendamento IFRS 16)", "R$ mil"),
    "arrend_ifrs16_cp": ("Passivo de arrendamento IFRS 16 CP (2.01.05.xx 'arrendamento'; desde 2019)", "R$ mil"),
    "arrend_ifrs16_lp": ("Passivo de arrendamento IFRS 16 LP (2.02.02.xx 'arrendamento'; desde 2019)", "R$ mil"),
    "arrendamentos_total": ("Todos os arrendamentos (financeiro + IFRS 16)", "R$ mil"),
    "divida_bruta_com_arrend_ifrs16": ("Dívida bruta + arrendamentos IFRS 16", "R$ mil"),
    "divida_liquida": ("Dívida bruta − caixa e aplicações CP", "R$ mil"),
    "ativo_total": ("Ativo total (BPA 1)", "R$ mil"),
    "imobilizado": ("Imobilizado (BPA 1.02.03)", "R$ mil"),
    "intangivel": ("Intangível (BPA 1.02.04)", "R$ mil"),
    "pl_total": ("Patrimônio líquido consolidado (BPP 2.03)", "R$ mil"),
    "pl_nao_controladores": ("Participação dos não controladores no PL (2.03.xx)", "R$ mil"),
    "pl_controladores": ("PL atribuído aos controladores", "R$ mil"),
    "acoes_total": ("Ações do capital integralizado (ON+PN)", "ações"),
    "tesouraria_total": ("Ações em tesouraria (ON+PN)", "ações"),
    "acoes_circulacao": ("Ações em circulação = total − tesouraria", "ações"),
    "acoes_implicitas_lpa": ("Conferência: lucro dos controladores / LPA PN (média ponderada)", "ações"),
    "dt_receb": ("Data de entrega à CVM da versão usada", "data"),
    "dt_receb_primeira": ("Data da 1ª entrega do documento (usar para 'informação disponível na data')", "data"),
    "versao": ("Versão do documento na CVM (a mais recente)", "nº"),
}
for aba, df in [("Fundamentos_anuais", abas["Fundamentos_anuais"]), ("Fundamentos_trimestrais", FT)]:
    for c in df.columns:
        base = c.replace("_ltm", "").replace("_ytd", "")
        d, u = DESCR.get(base, (c, ""))
        if c.endswith("_ltm"):
            d = "Últimos 12 meses (soma de 4 trimestres): " + d
        elif c.endswith("_ytd"):
            d = "Acumulado no ano (como divulgado): " + d
        elif (
            aba == "Fundamentos_trimestrais"
            and base in DESCR
            and u == "R$ mil"
            and c
            in (
                "receita_liquida",
                "cpv",
                "lucro_bruto",
                "despesas_operacionais",
                "impairment",
                "equivalencia_patrimonial",
                "ebit",
                "ebit_ex_impairment",
                "da",
                "ebitda",
                "resultado_financeiro",
                "receitas_financeiras",
                "despesas_financeiras",
                "despesa_juros_dfc",
                "juros_pagos_dfc",
                "lair",
                "ir_cs",
                "lucro_liquido",
                "lucro_controladores",
                "lucro_nao_controladores",
                "capex_imobilizado",
                "capex_intangivel",
                "capex",
                "dividendos_jcp_pagos_dfc",
            )
        ):
            d = "Trimestre isolado: " + d
        doc(aba, c, d, u, "CVM DFP/ITR consolidado (CD_CVM 3980)", URL_CVM, DC_CVM)

# ------------------------------------------------------------------ Contas brutas (só Gerdau, consolidado)
cols_ct = [
    "DT_REFER",
    "VERSAO",
    "DT_RECEB",
    "DT_RECEB_PRIMEIRA",
    "N_VERSOES",
    "DEMONSTRACAO",
    "ORDEM_EXERC",
    "DT_INI_EXERC",
    "DT_FIM_EXERC",
    "CD_CONTA",
    "DS_CONTA",
    "VL_CONTA_MIL",
    "ST_CONTA_FIXA",
    "URL_ZIP",
]
D = rd(TR, "cvm_dfp_contas.csv", dtype={"CD_CONTA": str})
D = D[
    (D["EMPRESA"] == "GERDAU")
    & ((D["ORDEM_EXERC"] == "ÚLTIMO") | ((D["DT_REFER"] == "2010-12-31") & (D["ORDEM_EXERC"] == "PENÚLTIMO")))
]
abas["DFP_contas"] = D[cols_ct].sort_values(["DT_REFER", "DEMONSTRACAO", "ORDEM_EXERC", "CD_CONTA"])
It = rd(TR, "cvm_itr_contas.csv", dtype={"CD_CONTA": str})
It = It[
    (It["EMPRESA"] == "GERDAU")
    & (
        (It["ORDEM_EXERC"] == "ÚLTIMO")
        | (
            (It["DT_REFER"].str[:4] == "2011")
            & (It["ORDEM_EXERC"] == "PENÚLTIMO")
            & ~It["DEMONSTRACAO"].isin(["BPA", "BPP"])
        )
    )
]
abas["ITR_contas"] = It[cols_ct].sort_values(["DT_REFER", "DEMONSTRACAO", "ORDEM_EXERC", "DT_INI_EXERC", "CD_CONTA"])
for aba in ["DFP_contas", "ITR_contas"]:
    for c, d, u in [
        ("DT_REFER", "Data de referência do documento (fim do período)", "data"),
        ("VERSAO", "Versão do documento (mantida só a mais recente)", "nº"),
        ("DT_RECEB", "Data de entrega da versão mantida", "data"),
        ("DT_RECEB_PRIMEIRA", "Data da 1ª entrega do documento (qualquer versão)", "data"),
        ("N_VERSOES", "Nº de versões entregues", "nº"),
        ("DEMONSTRACAO", "BPA, BPP, DRE, DFC_MI (DFC_MD se não houver MI)", ""),
        (
            "ORDEM_EXERC",
            "ÚLTIMO = período do documento; PENÚLTIMO = comparativo (só DFP 2010 e ITRs 2011, para 2009/2010)",
            "",
        ),
        (
            "DT_INI_EXERC",
            "Início do período do valor (ITR-DRE: início do trimestre = 3 meses; 1º jan = acumulado)",
            "data",
        ),
        ("DT_FIM_EXERC", "Fim do período do valor", "data"),
        ("CD_CONTA", "Código da conta CVM", ""),
        ("DS_CONTA", "Descrição da conta", ""),
        ("VL_CONTA_MIL", "Valor", "R$ mil"),
        ("ST_CONTA_FIXA", "S = conta padronizada CVM", ""),
        ("URL_ZIP", "Arquivo da CVM de origem", "URL"),
    ]:
        doc(
            aba, c, d, u, "CVM Dados Abertos", URL_CVM + ("DFP/DADOS/" if aba == "DFP_contas" else "ITR/DADOS/"), DC_CVM
        )
M = rd(TR, "mapeamento_contas.csv")
abas["Mapeamento_contas"] = M[M["empresa"] == "GERDAU"].drop(columns="empresa")
doc(
    "Mapeamento_contas",
    "contas_cvm",
    "Conta(s) CVM (código + descrição) somadas para cada variável do painel anual",
    "",
    "derivado (05_fundamentos_cvm.py)",
    "",
    DC_CVM,
)

# ------------------------------------------------------------------ Ações
A = rd(TR, "acoes_gerdau.csv")
abas["Acoes"] = A[
    [
        "data",
        "on_total",
        "pn_total",
        "acoes_total",
        "on_tesouraria",
        "pn_tesouraria",
        "tesouraria_total",
        "acoes_circulacao",
        "fonte",
        "url",
    ]
]
for c, d in [
    ("data", "Data de referência"),
    ("on_total", "Ações ON do capital"),
    ("pn_total", "Ações PN do capital"),
    ("acoes_total", "Total de ações"),
    ("on_tesouraria", "ON em tesouraria"),
    ("pn_tesouraria", "PN em tesouraria"),
    ("tesouraria_total", "Total em tesouraria"),
    ("acoes_circulacao", "Total − tesouraria"),
    ("fonte", "Documento de origem (2020+: composicao_capital DFP/ITR; 2009–2019: FRE)"),
]:
    doc("Acoes", c, d, "ações" if c not in ("data", "fonte") else "", "CVM DFP/ITR/FRE", URL_CVM, DC_CVM)

# ------------------------------------------------------------------ Preços
YF = os.path.join(RAW, "yfinance")


def px(nome, cols, ren):
    d = pd.read_csv(os.path.join(YF, f"precos_{nome}.csv"), parse_dates=["Date"]).set_index("Date")[cols]
    return d.rename(columns=ren)


P = pd.concat(
    [
        px(
            "GGBR4_SA",
            ["Close", "Adj Close", "Volume"],
            {"Close": "ggbr4_fech", "Adj Close": "ggbr4_ajust", "Volume": "ggbr4_volume"},
        ),
        px("GGBR3_SA", ["Close", "Adj Close"], {"Close": "ggbr3_fech", "Adj Close": "ggbr3_ajust"}),
        px("BVSP", ["Close"], {"Close": "ibov"}),
        px("CSNA3_SA", ["Adj Close"], {"Adj Close": "csna3_ajust"}),
        px("USIM5_SA", ["Adj Close"], {"Adj Close": "usim5_ajust"}),
    ],
    axis=1,
).sort_index()
P.index.name = "data"
# O Yahoo mantém linhas em feriados da B3 repetindo o último preço com volume 0 -> marcamos os pregões reais
P["pregao_b3"] = (P["ggbr4_volume"] > 0).astype(int)
# O "Close" do Yahoo é retroajustado por desdobramentos/bonificações. Para obter o preço NOMINAL negociado no dia
# (compatível com a quantidade de ações informada à CVM naquela data), multiplica-se pelos fatores dos eventos
# posteriores.
_sp = pd.read_csv(os.path.join(YF, "splits_GGBR4_SA.csv"), parse_dates=["Date"])
_fat = pd.Series(1.0, index=P.index)
for _, e in _sp.iterrows():
    _fat[P.index < e["Date"]] *= e["Stock Splits"]
P["ggbr4_fator_eventos_posteriores"] = _fat
P["ggbr4_fech_nominal"] = P["ggbr4_fech"] * _fat
P = P.round(6).reset_index()
abas["Precos_diarios"] = P
DC_YF = coleta("/yfinance/")
for c, d, u in [
    ("ggbr4_fech", "GGBR4 fechamento (Yahoo: ajustado só por desdobramentos/bonificações)", "R$"),
    ("ggbr4_ajust", "GGBR4 fechamento ajustado por proventos e eventos (retorno total)", "R$"),
    ("ggbr4_volume", "GGBR4 volume", "ações"),
    ("ggbr3_fech", "GGBR3 fechamento", "R$"),
    ("ggbr3_ajust", "GGBR3 ajustado", "R$"),
    ("ibov", "Ibovespa (índice de retorno total por metodologia B3)", "pontos"),
    ("csna3_ajust", "CSNA3 ajustado (par)", "R$"),
    ("usim5_ajust", "USIM5 ajustado (par)", "R$"),
    (
        "ggbr4_fator_eventos_posteriores",
        "Produto dos fatores de desdobramento/bonificação com data-ex POSTERIOR ao dia",
        "x",
    ),
    (
        "ggbr4_fech_nominal",
        "GGBR4 fechamento nominal do dia = ggbr4_fech × fator (preço efetivamente negociado; usar com "
        "a quantidade de ações da CVM na mesma data para o valor de mercado)",
        "R$",
    ),
    (
        "pregao_b3",
        "1 = pregão com negócios na GGBR4; 0 = linha do Yahoo em feriado (preço repetido, volume 0) — "
        "filtrar antes de calcular retornos",
        "0/1",
    ),
]:
    doc("Precos_diarios", c, d, u, "Yahoo Finance (yfinance)", "https://finance.yahoo.com/", DC_YF)

# ------------------------------------------------------------------ Proventos
prv = []
for tk in ["GGBR4_SA", "GGBR3_SA"]:
    dv = pd.read_csv(os.path.join(YF, f"dividendos_{tk}.csv"))
    prv.append(
        pd.DataFrame(
            {
                "data_ex": dv["Date"],
                "ticker": tk.replace("_", "."),
                "tipo": "dividendo/JCP",
                "valor_por_acao": dv["Dividends"],
                "fator_desdobramento": np.nan,
            }
        )
    )
    sp = pd.read_csv(os.path.join(YF, f"splits_{tk}.csv"))
    prv.append(
        pd.DataFrame(
            {
                "data_ex": sp["Stock Splits"].index.map(lambda i, sp=sp: sp["Date"][i]),
                "ticker": tk.replace("_", "."),
                "tipo": "desdobramento/bonificação",
                "valor_por_acao": np.nan,
                "fator_desdobramento": sp["Stock Splits"],
            }
        )
    )
abas["Proventos"] = pd.concat(prv).sort_values(["ticker", "data_ex"]).reset_index(drop=True)
for c, d, u in [
    ("data_ex", "Data ex", "data"),
    ("ticker", "Ativo", ""),
    ("tipo", "dividendo/JCP (Yahoo não separa) ou desdobramento/bonificação", ""),
    ("valor_por_acao", "Provento por ação, AJUSTADO por desdobramentos/bonificações posteriores (Yahoo)", "R$/ação"),
    ("fator_desdobramento", "Fator (1,2 = bonificação de 20%; 2 = desdobramento 1:2)", "x"),
]:
    doc("Proventos", c, d, u, "Yahoo Finance (yfinance)", "https://finance.yahoo.com/", DC_YF)

# ------------------------------------------------------------------ Macro
BCB = os.path.join(RAW, "bcb")


def sgs(cod, nome):
    d = pd.read_csv(os.path.join(BCB, f"sgs_{cod}.csv"), parse_dates=["data"]).set_index("data")["valor"]
    return d.rename(nome)


DC_BCB = coleta("/bcb/sgs")
cdi, selic, meta, ptax = sgs(12, "cdi_ad"), sgs(11, "selic_ad"), sgs(432, "selic_meta_aa"), sgs(1, "ptax_venda")
MD = pd.concat([cdi, selic, ptax], axis=1).sort_index()
MD = pd.merge_asof(MD.reset_index(), meta.reset_index(), on="data")
abas["Macro_diario"] = MD
urlsgs = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{}/dados?formato=json"
for c, d, u, k in [
    ("cdi_ad", "CDI diário", "% ao dia", 12),
    ("selic_ad", "Selic efetiva diária", "% ao dia", 11),
    ("ptax_venda", "PTAX venda", "R$/US$", 1),
    ("selic_meta_aa", "Meta Selic (Copom) vigente", "% a.a.", 432),
]:
    doc("Macro_diario", c, f"{d} (SGS {k})", u, "BCB-SGS", urlsgs.format(k), DC_BCB)

ipca, ibc = sgs(433, "ipca_mensal"), sgs(24363, "ibcbr")
mm = pd.DataFrame(index=pd.period_range("2000-01", pd.Timestamp.today(), freq="M"))
mm["ipca_mensal"] = ipca.groupby(ipca.index.to_period("M")).last()
mm["ipca_12m"] = ((1 + mm["ipca_mensal"] / 100).rolling(12).apply(np.prod, raw=True) - 1) * 100
mm["ibcbr"] = ibc.groupby(ibc.index.to_period("M")).last()
mm["cdi_mes"] = ((1 + cdi / 100).groupby(cdi.index.to_period("M")).prod() - 1) * 100
mm["ptax_fim_mes"] = ptax.groupby(ptax.index.to_period("M")).last()
mm["selic_meta_fim_mes"] = meta.groupby(meta.index.to_period("M")).last()
foc = rd(TR, "focus_mensal.csv", parse_dates=["Data"])
foc["mes"] = foc["Data"].dt.to_period("M")
foc["h"] = foc["DataReferencia"].astype(int) - foc["Data"].dt.year
apel = {"PIB Total": "pib", "IPCA": "ipca", "Câmbio": "cambio", "Selic": "selic"}
foc["col"] = "focus_" + foc["Indicador"].map(apel) + "_t" + foc["h"].astype(str)
wide = foc.pivot_table(index="mes", columns="col", values="Mediana", aggfunc="last")
ordem = [f"focus_{a}_t{h}" for a in apel.values() for h in range(5) if f"focus_{a}_t{h}" in wide.columns]
mm = mm.join(wide[ordem])
mm["focus_data_pesquisa"] = foc.groupby("mes")["Data"].max().dt.strftime("%Y-%m-%d")
mm.index = mm.index.to_timestamp()
mm.index.name = "mes"
mm = mm.dropna(how="all", subset=[c for c in mm.columns if c != "focus_data_pesquisa"])
abas["Macro_mensal"] = mm.round(6).reset_index()
for c, d, u, f, url in [
    ("ipca_mensal", "IPCA variação mensal (SGS 433)", "% a.m.", "BCB-SGS", urlsgs.format(433)),
    ("ipca_12m", "IPCA acumulado 12 meses (calculado)", "%", "BCB-SGS", urlsgs.format(433)),
    ("ibcbr", "IBC-Br sem ajuste sazonal (SGS 24363)", "índice", "BCB-SGS", urlsgs.format(24363)),
    ("cdi_mes", "CDI acumulado no mês (calculado do SGS 12)", "%", "BCB-SGS", urlsgs.format(12)),
    ("ptax_fim_mes", "PTAX venda no último dia útil do mês", "R$/US$", "BCB-SGS", urlsgs.format(1)),
    ("selic_meta_fim_mes", "Meta Selic no fim do mês", "% a.a.", "BCB-SGS", urlsgs.format(432)),
]:
    doc("Macro_mensal", c, d, u, f, url, DC_BCB)
for c in ordem:
    a, h = c.split("_")[1], c.split("_t")[-1]
    un = {
        "pib": "% a.a. (var. real)",
        "ipca": "% a.a.",
        "cambio": "R$/US$ (fim de ano)",
        "selic": "% a.a. (fim de ano)",
    }[a]
    doc(
        "Macro_mensal",
        c,
        f"Focus — mediana da expectativa de {a.upper()} para o ano (ano da pesquisa + {h}); "
        "última pesquisa do mês, base de cálculo 0",
        un,
        "BCB-Focus (Olinda)",
        "https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais",
        coleta("focus_anuais"),
    )
doc(
    "Macro_mensal",
    "focus_data_pesquisa",
    "Data da pesquisa Focus usada no mês",
    "data",
    "BCB-Focus (Olinda)",
    "",
    coleta("focus_anuais"),
)

pib = sgs(7326, "pib_real_var")
ma = pd.DataFrame(index=range(2000, pd.Timestamp.today().year + 1))
ma.index.name = "ano"
ma["pib_real_var"] = pib.groupby(pib.index.year).last()
ma["ipca_ano"] = ((1 + ipca / 100).groupby(ipca.index.year).prod() - 1) * 100
ma["cdi_ano"] = ((1 + cdi / 100).groupby(cdi.index.year).prod() - 1) * 100
ma["selic_meta_fim"] = meta.groupby(meta.index.year).last()
ma["ptax_fim"] = ptax.groupby(ptax.index.year).last()
ma["ptax_media"] = ptax.groupby(ptax.index.year).mean()
ma["ano_incompleto"] = np.where(ma.index == pd.Timestamp.today().year, "sim", "")
abas["Macro_anual"] = ma.round(6).reset_index()
for c, d, u, k in [
    ("pib_real_var", "PIB real, variação anual (SGS 7326)", "%", 7326),
    ("ipca_ano", "IPCA acumulado no ano (calculado)", "%", 433),
    ("cdi_ano", "CDI acumulado no ano", "%", 12),
    ("selic_meta_fim", "Meta Selic no fim do ano", "% a.a.", 432),
    ("ptax_fim", "PTAX venda fim do ano", "R$/US$", 1),
    ("ptax_media", "PTAX venda média do ano", "R$/US$", 1),
]:
    doc("Macro_anual", c, d, u, "BCB-SGS", urlsgs.format(k), DC_BCB)

# ------------------------------------------------------------------ Setor (FRED)
fd = rd(TR, "fred_disponibilidade.csv")
fd = fd[fd["disponivel"]]
S = []
for _, r in fd.iterrows():
    d = pd.read_csv(os.path.join(RAW, "fred", f"{r['serie']}.csv"))
    d.columns = ["mes", r["serie"]]
    d[r["serie"]] = pd.to_numeric(d[r["serie"]], errors="coerce")
    S.append(d.set_index("mes"))
S = pd.concat(S, axis=1).sort_index()
S = S[S.index >= "2000-01-01"]
S.index = pd.to_datetime(S.index)
abas["Setor"] = S.reset_index()
for _, r in fd.iterrows():
    doc(
        "Setor",
        r["serie"],
        f"{r['descricao']} (FRED; disponível {r['inicio']} a {r['fim']})",
        "US$/t" if r["serie"] == "PIORECRUSDM" else "índice",
        "FRED (St. Louis Fed)",
        r["url"],
        coleta("/fred/"),
    )

# ------------------------------------------------------------------ Pares
pc = [
    "empresa",
    "exercicio",
    "receita_liquida",
    "ebit",
    "da",
    "ebitda",
    "lucro_liquido",
    "capex",
    "divida_bruta",
    "caixa_aplicacoes",
    "divida_liquida",
    "pl_total",
    "dt_receb_primeira",
]
Pr = FA[pc].copy()
Pr["margem_ebit"] = Pr["ebit"] / Pr["receita_liquida"]
Pr["margem_ebitda"] = Pr["ebitda"] / Pr["receita_liquida"]
abas["Pares"] = Pr
ent = rd(TR, "cvm_entidades.csv")
doc(
    "Pares",
    "empresa",
    "GERDAU (CVM 3980), CSN (CVM "
    + str(ent.set_index("EMPRESA").loc["CSN", "CD_CVM"])
    + "), USIMINAS (CVM "
    + str(ent.set_index("EMPRESA").loc["USIMINAS", "CD_CVM"])
    + "); códigos obtidos no cadastro CVM pelo nome",
    "",
    "CVM cadastro",
    "https://dados.cvm.gov.br/dados/CIA_ABERTA/CAD/DADOS/cad_cia_aberta.csv",
    coleta("cad_cia"),
)
for c in pc[2:] + ["margem_ebit", "margem_ebitda"]:
    d, u = DESCR.get(c, (c, "fração" if c.startswith("margem") else ""))
    if c.startswith("margem"):
        d, u = ("EBIT / receita" if c == "margem_ebit" else "EBITDA / receita"), "fração"
    doc("Pares", c, d, u, "CVM DFP consolidado", URL_CVM, DC_CVM)

# ------------------------------------------------------------------ Datas-base (trimestrais 2020T1–2024T4)
pregões = pd.DatetimeIndex(P["data"][P["pregao_b3"] == 1])
DB = FT[(FT["ano"] >= 2020) & (FT["ano"] <= 2024)][
    ["ano", "trimestre", "dt_fim_periodo", "documento", "dt_receb_primeira", "dt_receb", "versao", "n_versoes"]
].copy()


def prox_pregao(d):
    i = pregões.searchsorted(pd.Timestamp(d), side="right")  # 1º pregão ESTRITAMENTE após a entrega
    return pregões[i].strftime("%Y-%m-%d") if i < len(pregões) else None


DB["data_base"] = DB["dt_receb_primeira"].map(prox_pregao)
DB["trimestre_id"] = DB["ano"].astype(str) + "T" + DB["trimestre"].astype(str)
pxi = P.set_index("data")
DB["ggbr4_fech_data_base"] = DB["data_base"].map(lambda d: pxi.loc[pd.Timestamp(d), "ggbr4_fech"])
DB["ggbr4_fech_nominal_data_base"] = DB["data_base"].map(lambda d: pxi.loc[pd.Timestamp(d), "ggbr4_fech_nominal"])
DB["ggbr4_ajust_data_base"] = DB["data_base"].map(lambda d: pxi.loc[pd.Timestamp(d), "ggbr4_ajust"])
DB["ibov_data_base"] = DB["data_base"].map(lambda d: pxi.loc[pd.Timestamp(d), "ibov"])
DB["obs"] = np.where(
    DB["n_versoes"] > 1,
    "documento reapresentado: valores da planilha são da última versão (entregue em "
    + DB["dt_receb"].astype(str)
    + ")",
    "",
)
DB["fase_ciclo"] = ""
DB = DB.rename(
    columns={"trimestre_id": "trimestre_ref", "dt_fim_periodo": "data_fim_periodo", "dt_receb_primeira": "DT_RECEB"}
)
abas["Datas_base"] = DB[
    [
        "trimestre_ref",
        "data_fim_periodo",
        "documento",
        "DT_RECEB",
        "data_base",
        "versao",
        "n_versoes",
        "dt_receb",
        "ggbr4_fech_data_base",
        "ggbr4_fech_nominal_data_base",
        "ggbr4_ajust_data_base",
        "ibov_data_base",
        "fase_ciclo",
        "obs",
    ]
]
for c, d, u in [
    ("trimestre_ref", "Trimestre fiscal cujo documento define a data-base", ""),
    ("data_fim_periodo", "Fim do trimestre fiscal", "data"),
    ("documento", "ITR (T1–T3) ou DFP (T4)", ""),
    ("DT_RECEB", "1ª entrega do documento à CVM", "data"),
    ("data_base", "1º pregão da B3 (dia com volume > 0 na GGBR4) estritamente após DT_RECEB", "data"),
    ("dt_receb", "Entrega da última versão (se reapresentado)", "data"),
    ("ggbr4_fech_data_base", "GGBR4 fechamento na data-base (Yahoo, retroajustado por bonificações)", "R$"),
    ("ggbr4_fech_nominal_data_base", "GGBR4 fechamento nominal (efetivamente negociado) na data-base", "R$"),
    ("ggbr4_ajust_data_base", "GGBR4 ajustado na data-base", "R$"),
    ("ibov_data_base", "Ibovespa na data-base", "pontos"),
    ("fase_ciclo", "Fase do ciclo do aço (a preencher pelo autor)", ""),
]:
    doc("Datas_base", c, d, u, "construída (CVM + Yahoo)", "", DC_CVM)

# ------------------------------------------------------------------ LEIAME
cab = pd.DataFrame(
    [
        {
            "aba": "LEIAME",
            "variavel": "(geral)",
            "descricao": "Base de dados do TCC 'Valuation da Gerdau S.A. (GGBR4)' — IE-UFRJ. "
            "Entidade: Gerdau S.A., CVM 3980, CNPJ 33.611.500/0001-19 (NÃO Metalúrgica Gerdau). "
            "Demonstrações consolidadas.",
            "unidade": "",
            "fonte": "",
            "url": "",
            "data_coleta": pd.Timestamp.today().strftime("%Y-%m-%d"),
        },
        {
            "aba": "LEIAME",
            "variavel": "(regra de data)",
            "descricao": "Usar DT_RECEB / dt_receb_primeira para saber quando a informação "
            "ficou disponível. Valores DFP/ITR = versão mais recente do documento do próprio período "
            "(sem reapresentações em anos seguintes).",
            "unidade": "",
            "fonte": "",
            "url": "",
            "data_coleta": "",
        },
        {
            "aba": "LEIAME",
            "variavel": "(código)",
            "descricao": "Gerada por Código/01_coleta/06_montar_planilha.py; ver README.md e "
            "Fontes e notas dos dados.md. Proveniência arquivo a arquivo em raw/_proveniencia.csv.",
            "unidade": "",
            "fonte": "",
            "url": "",
            "data_coleta": "",
        },
    ]
)
abas["LEIAME"] = pd.concat([cab, pd.DataFrame(dic)], ignore_index=True)

# ------------------------------------------------------------------ grava
ORDEM = [
    "LEIAME",
    "Datas_base",
    "Fundamentos_anuais",
    "Fundamentos_trimestrais",
    "DFP_contas",
    "ITR_contas",
    "Mapeamento_contas",
    "Acoes",
    "Precos_diarios",
    "Proventos",
    "Macro_diario",
    "Macro_mensal",
    "Macro_anual",
    "Setor",
    "Pares",
]
with pd.ExcelWriter(PLANILHA, engine="openpyxl") as w:
    for aba in ORDEM:
        df = abas[aba]
        df.to_excel(w, sheet_name=aba, index=False)
        ws = w.sheets[aba]
        ws.freeze_panes = "B2"
        for i, col in enumerate(df.columns, 1):
            larg = min(max(len(str(col)), 10), 60 if aba == "LEIAME" else 22)
            ws.column_dimensions[ws.cell(1, i).column_letter].width = larg + 2
for aba in ORDEM:
    print(f"{aba:25s} {abas[aba].shape}")
print(f"\nGravado: {PLANILHA} ({os.path.getsize(PLANILHA) / 1e6:.1f} MB)")
