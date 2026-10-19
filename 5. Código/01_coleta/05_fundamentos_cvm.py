"""
05 — Painel de fundamentos (anual e trimestral) a partir dos extratos da CVM.

Lê os CSVs gerados por 01_cvm_dfp_itr.py e 01b_cvm_fre_acoes.py (pasta Tabelas intermediárias (CSV)/) e monta:
  fundamentos_anuais.csv      Gerdau, CSN e Usiminas, 2009–2025 (2009 = coluna comparativa "PENÚLTIMO" da DFP
                              2010; demais anos = "ÚLTIMO" da DFP do próprio ano, isto é, o número COMO DIVULGADO
                              na época, sem reapresentações posteriores)
  fundamentos_trimestrais.csv Gerdau, 2010T1–último ITR: mesmas variáveis do painel anual, fluxos (DRE/DFC) em
                              TRIMESTRE ISOLADO + colunas LTM (12 meses)
  acoes_gerdau.csv            ações totais, em tesouraria e em circulação por data
  mapeamento_contas.csv       que conta CVM (código + descrição) alimentou cada variável em cada ano
  validacao_anual.txt         tabela de validação e alertas
(todos em Tabelas intermediárias (CSV)/)

Regra de mapeamento: por CÓDIGO e conferindo a DESCRIÇÃO (padrão regex). Quando a conta muda de código
ao longo dos anos (D&A, capex, arrendamentos), a busca é feita pela descrição dentro do grupo certo.
Todos os valores em R$ mil (exceto ações, em unidades, e LPA, em R$/ação).
Sinais: mantidos como na CVM (custos/despesas negativos), EXCETO capex, que é guardado positivo.
Uso:  python -I 05_fundamentos_cvm.py
"""

import os
import re
import site
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from _comum import pasta_tratados  # noqa: E402

OUT = pasta_tratados()
ULT, PEN = "ÚLTIMO", "PENÚLTIMO"

# --------------------------------------------------------------------------------------------
# Contas de código fixo: variável -> (demonstração, código, regex que a descrição deve conter)
FIXAS = {
    "receita_liquida": ("DRE", "3.01", r"receita"),
    "cpv": ("DRE", "3.02", r"custo"),
    "lucro_bruto": ("DRE", "3.03", r"bruto"),
    "despesas_operacionais": ("DRE", "3.04", r"despesas|receitas"),
    "ebit": ("DRE", "3.05", r"antes do resultado financeiro"),
    "resultado_financeiro": ("DRE", "3.06", r"financeir"),
    "receitas_financeiras": ("DRE", "3.06.01", r"receitas financeiras"),
    "despesas_financeiras": ("DRE", "3.06.02", r"despesas financeiras"),
    "lair": ("DRE", "3.07", r"antes dos tributos"),
    "ir_cs": ("DRE", "3.08", r"imposto"),
    "lucro_liquido": ("DRE", "3.11", r"lucro|preju"),
    "lucro_controladores": ("DRE", "3.11.01", r"controladora"),
    "lucro_nao_controladores": ("DRE", "3.11.02", r"n.o controladores"),
    "lpa_basico_on": ("DRE", "3.99.01.01", r"ON"),
    "lpa_basico_pn": ("DRE", "3.99.01.02", r"PN"),
    "ativo_total": ("BPA", "1", r"ativo total"),
    "caixa_equivalentes": ("BPA", "1.01.01", r"caixa"),
    "aplicacoes_financeiras_cp": ("BPA", "1.01.02", r"aplica"),
    "contas_receber": ("BPA", "1.01.03", r"receber"),
    "estoques": ("BPA", "1.01.04", r"estoque"),
    "imobilizado": ("BPA", "1.02.03", r"imobilizado"),
    "intangivel": ("BPA", "1.02.04", r"intang"),
    "passivo_total": ("BPP", "2", r"passivo total"),
    "fornecedores": ("BPP", "2.01.02", r"fornecedor"),
    "emprestimos_cp_total": ("BPP", "2.01.04", r"empr.stimos"),
    "emprestimos_financiamentos_cp": ("BPP", "2.01.04.01", r"empr.stimos"),
    "debentures_cp": ("BPP", "2.01.04.02", r"deb.ntures"),
    "arrend_financeiro_cp": ("BPP", "2.01.04.03", r"arrendamento"),
    "emprestimos_lp_total": ("BPP", "2.02.01", r"empr.stimos"),
    "emprestimos_financiamentos_lp": ("BPP", "2.02.01.01", r"empr.stimos"),
    "debentures_lp": ("BPP", "2.02.01.02", r"deb.ntures"),
    "arrend_financeiro_lp": ("BPP", "2.02.01.03", r"arrendamento"),
    "pl_total": ("BPP", "2.03", r"patrim"),
}


def norm(s):
    return s.fillna("").str.lower()


def valor_fixo(d, dem, cod, padrao, avisos, var):
    x = d[(d["DEMONSTRACAO"] == dem) & (d["CD_CONTA"] == cod)]
    if x.empty:
        return np.nan, ""
    desc = x["DS_CONTA"].iloc[0]
    if not re.search(padrao, desc, flags=re.I):
        avisos.append(f"{var}: conta {cod} com descrição inesperada '{desc}'")
    return float(x["VL_CONTA_MIL"].iloc[0]), f"{cod} {desc}"


def raizes(x):
    """Mantém só as contas mais 'altas' da seleção (sem ancestral também selecionado), para não somar
    pai + filho. Usa-se a raiz (e não a folha) porque algumas empresas preenchem a subconta com zero e
    informam o valor só na conta-mãe (ex.: Gerdau 2015, 3.04.03 = −4.996 mi e 3.04.03.01 = 0)."""
    cods = set(x["CD_CONTA"])
    mask = np.array([not any(c.startswith(o + ".") for o in cods) for c in x["CD_CONTA"]], dtype=bool)
    return x.loc[mask]


def soma_desc(d, dems, prefixo, incluir, excluir=None, sinal=None):
    """Soma as contas (raízes da seleção) cujo código começa com `prefixo` e cuja descrição casa com `incluir`
    (e não casa com `excluir`). `sinal`='neg' mantém só valores negativos (saídas de caixa)."""
    x = d[d["DEMONSTRACAO"].isin(dems) & d["CD_CONTA"].str.startswith(prefixo)]
    m = norm(x["DS_CONTA"]).str.contains(incluir, regex=True)
    if excluir:
        m &= ~norm(x["DS_CONTA"]).str.contains(excluir, regex=True)
    x = raizes(x[m])
    if sinal == "neg":
        x = x[x["VL_CONTA_MIL"] <= 0]
    if x.empty:
        return np.nan, ""
    contas = " + ".join(f"{c} {s}" for c, s in zip(x["CD_CONTA"], x["DS_CONTA"], strict=True))
    return float(x["VL_CONTA_MIL"].sum()), contas


def extrair(d):
    """d = contas de UMA empresa, UM período, UMA ordem de exercício. Devolve (valores, origens, avisos)."""
    v, o, avisos = {}, {}, []
    for var, (dem, cod, pad) in FIXAS.items():
        v[var], o[var] = valor_fixo(d, dem, cod, pad, avisos, var)
    # DFC: método indireto (MI); se ausente, método direto (MD)
    dfc = ["DFC_MI"] if (d["DEMONSTRACAO"] == "DFC_MI").any() else ["DFC_MD"]
    v["dfc_metodo"] = dfc[0]
    # D&A: linha(s) de ajuste do caixa operacional com 'deprecia'
    v["da"], o["da"] = soma_desc(d, dfc, "6.01", r"deprecia")
    # Capex: saídas de caixa de investimento em imobilizado / intangível (exclui vendas/recebimentos)
    excl = r"venda|recebi|aliena|baixa|juros"
    ci, o["capex_imobilizado"] = soma_desc(d, dfc, "6.02", r"imobilizado", excl + r"|intang", sinal="neg")
    cn, o["capex_intangivel"] = soma_desc(d, dfc, "6.02", r"intang", excl + r"|imobilizado", sinal="neg")
    # linha combinada (ex.: CSN 2020+: "Aquisição de ativos imobilizados, intangível ...")
    cc, oc = soma_desc(d, dfc, "6.02", r"imobilizado.*intang|intang.*imobilizado", excl, sinal="neg")
    v["capex_imobilizado"] = -np.nansum([ci, cc]) if not (np.isnan(ci) and np.isnan(cc)) else np.nan
    v["capex_intangivel"] = -cn if not np.isnan(cn) else 0.0
    if oc:
        o["capex_imobilizado"] = (o["capex_imobilizado"] + " + " + oc).strip(" +")
    v["capex"] = v["capex_imobilizado"] + v["capex_intangivel"]
    # Juros: despesa de juros (ajuste no caixa operacional) e juros pagos (exclui arrendamento e receitas)
    v["despesa_juros_dfc"], o["despesa_juros_dfc"] = soma_desc(
        d, dfc, "6.01.01", r"juros", r"arrendamento|receita|m.tuo|ligadas|aplica|capital pr.prio|ativo"
    )
    v["juros_pagos_dfc"], o["juros_pagos_dfc"] = soma_desc(
        d, dfc, "6.0", r"(?:pagamento.*juros|juros.*pagos)", r"arrendamento|capital pr.prio"
    )
    v["dividendos_jcp_pagos_dfc"], o["dividendos_jcp_pagos_dfc"] = soma_desc(
        d, dfc, "6.03", r"dividendo|capital pr.prio", r"recebi"
    )
    # Impairment (linhas 3.04.xx com 'recuperabilidade') e equivalência patrimonial
    v["impairment"], o["impairment"] = soma_desc(d, ["DRE"], "3.04", r"recuperabilidade")
    v["equivalencia_patrimonial"], o["equivalencia_patrimonial"] = soma_desc(d, ["DRE"], "3.04", r"equival")
    # Arrendamentos IFRS 16 (em "outras obrigações", códigos variam): 2.01.05 / 2.02.02
    v["arrend_ifrs16_cp"], o["arrend_ifrs16_cp"] = soma_desc(d, ["BPP"], "2.01.05", r"arrendamento")
    v["arrend_ifrs16_lp"], o["arrend_ifrs16_lp"] = soma_desc(d, ["BPP"], "2.02.02", r"arrendamento")
    # Não controladores no PL
    v["pl_nao_controladores"], o["pl_nao_controladores"] = soma_desc(d, ["BPP"], "2.03", r"n.o controladores")
    # ---- agregados
    z = lambda k: 0.0 if pd.isna(v.get(k)) else v[k]  # noqa: E731
    v["despesas_vendas_ga"] = np.nan
    v["divida_bruta"] = z("emprestimos_cp_total") + z("emprestimos_lp_total")  # inclui debêntures e arrend. financeiro
    v["arrendamentos_total"] = (
        z("arrend_ifrs16_cp") + z("arrend_ifrs16_lp") + z("arrend_financeiro_cp") + z("arrend_financeiro_lp")
    )
    v["divida_bruta_com_arrend_ifrs16"] = v["divida_bruta"] + z("arrend_ifrs16_cp") + z("arrend_ifrs16_lp")
    v["caixa_aplicacoes"] = z("caixa_equivalentes") + z("aplicacoes_financeiras_cp")
    v["divida_liquida"] = v["divida_bruta"] - v["caixa_aplicacoes"]
    v["ebitda"] = v["ebit"] + v["da"] if not pd.isna(v["da"]) else np.nan
    v["ebit_ex_impairment"] = v["ebit"] - z("impairment")  # EBIT recorrente (sem perdas/reversões de impairment)
    v["pl_controladores"] = z("pl_total") - z("pl_nao_controladores")
    # checagens internas
    if not pd.isna(v["ativo_total"]) and abs(v["ativo_total"] - z("passivo_total")) > 1:
        avisos.append("ativo total != passivo total")
    soma_cp = z("emprestimos_financiamentos_cp") + z("debentures_cp") + z("arrend_financeiro_cp")
    if soma_cp != 0 and abs(soma_cp - z("emprestimos_cp_total")) > 1:  # (CSN só informa o total)
        avisos.append(f"dívida CP: partes ({soma_cp:,.0f}) != total ({z('emprestimos_cp_total'):,.0f})")
    if pd.isna(v["da"]):
        avisos.append("D&A não encontrada na DFC")
    return v, o, avisos


# --------------------------------------------------------------------------------------------
# 1) ANUAL
C = pd.read_csv(os.path.join(OUT, "cvm_dfp_contas.csv"), dtype={"CD_CONTA": str})
C["ano_dfp"] = C["DT_REFER"].str[:4].astype(int)
linhas, mapa, alertas = [], [], []
for (emp, ano_dfp), g in C.groupby(["EMPRESA", "ano_dfp"]):
    ordens = [(ULT, ano_dfp)]
    if ano_dfp == C["ano_dfp"].min():  # DFP 2010 -> também o comparativo de 2009
        ordens.append((PEN, ano_dfp - 1))
    for ordem, exerc in ordens:
        d = g[g["ORDEM_EXERC"] == ordem]
        # BP: posição na data de fim; DRE/DFC: exercício completo
        v, o, av = extrair(d)
        info = d.iloc[0]
        v.update(
            empresa=emp,
            exercicio=exerc,
            dt_fim_exercicio=f"{exerc}-12-31",
            fonte_dfp=f"DFP {ano_dfp} ({ordem})",
            versao=int(info["VERSAO"]),
            dt_receb=info["DT_RECEB"],
            dt_receb_primeira=info["DT_RECEB_PRIMEIRA"],
            url_zip=info["URL_ZIP"],
        )
        linhas.append(v)
        for var, orig in o.items():
            mapa.append({"empresa": emp, "exercicio": exerc, "variavel": var, "contas_cvm": orig})
        alertas += [f"{emp} {exerc}: {a}" for a in av]
F = pd.DataFrame(linhas)

# 2) AÇÕES (Gerdau) ----------------------------------------------------------------------------
acoes = []
for tipo in ["dfp", "itr"]:
    p = os.path.join(OUT, f"cvm_{tipo}_composicao_capital.csv")
    if os.path.exists(p):
        k = pd.read_csv(p)
        k = k[k["EMPRESA"] == "GERDAU"]
        for _, r in k.iterrows():
            acoes.append(
                {
                    "data": r["DT_REFER"],
                    "fonte": f"CVM {tipo.upper()} composicao_capital (v{r['VERSAO']})",
                    "on_total": r["QT_ACAO_ORDIN_CAP_INTEGR"],
                    "pn_total": r["QT_ACAO_PREF_CAP_INTEGR"],
                    "acoes_total": r["QT_ACAO_TOTAL_CAP_INTEGR"],
                    "on_tesouraria": r["QT_ACAO_ORDIN_TESOURO"],
                    "pn_tesouraria": r["QT_ACAO_PREF_TESOURO"],
                    "tesouraria_total": r["QT_ACAO_TOTAL_TESOURO"],
                    "url": r["URL_ZIP"],
                }
            )
# FRE (2009–2019): total pelo histórico de aprovações de capital; tesouraria pela movimentação anual
cs = pd.read_csv(os.path.join(OUT, "cvm_fre_capital_social.csv"))
cs = cs[(cs["EMPRESA"] == "GERDAU") & (cs["Tipo_Capital"] == "Capital Integralizado")]
cs = cs.sort_values(["Data_Referencia", "Versao"]).drop_duplicates("Data_Autorizacao_Aprovacao", keep="last")
cs = cs.sort_values("Data_Autorizacao_Aprovacao")
tm = pd.read_csv(os.path.join(OUT, "cvm_fre_tesouraria_mov.csv"))
tm = tm[tm["EMPRESA"] == "GERDAU"].copy()
tm["ano_fre"] = tm["Data_Referencia"].str[:4].astype(int)
tm["ano_ex"] = tm["Data_Fim_Exercicio_Social"].str[:4].astype(int)
tm = tm[tm["Versao"] == tm.groupby("ano_fre")["Versao"].transform("max")]
tm["especie"] = np.where(tm["Especie_Acao"].str.startswith("Ord"), "on", "pn")


def tesouraria_fre(ano, esp):
    """Saldo final de tesouraria do exercício `ano`: usa o FRE do ano seguinte (exercício mais recente
    do formulário). Fallback: saldo inicial do exercício ano+1 no FRE de ano+2. (Os FREs mais novos
    às vezes repetem exercícios antigos com datas deslocadas — por isso não usamos o último FRE.)"""
    x = tm[(tm["ano_fre"] == ano + 1) & (tm["ano_ex"] == ano) & (tm["especie"] == esp)]
    if not x.empty:
        return float(x["Quantidade_Final"].iloc[0]), f"FRE {ano + 1} (saldo final {ano})"
    x = tm[(tm["ano_fre"] == ano + 2) & (tm["ano_ex"] == ano + 1) & (tm["especie"] == esp)]
    if not x.empty:
        return float(x["Quantidade_Inicial"].iloc[0]), f"FRE {ano + 2} (saldo inicial {ano + 1})"
    return (0.0, "sem registro no FRE (assumido 0)") if esp == "on" else (np.nan, "sem registro")


anos_com_comp = {int(a["data"][:4]) for a in acoes if a["data"].endswith("12-31")}
for ano in range(2009, 2020):
    if ano in anos_com_comp:
        continue
    lim = f"{ano}-12-31"
    c = cs[cs["Data_Autorizacao_Aprovacao"] <= lim]
    on_t, f_on = tesouraria_fre(ano, "on")
    pn_t, f_pn = tesouraria_fre(ano, "pn")
    r = c.iloc[-1] if not c.empty else None
    # 2009–2010: os FREs 2010/2011 são inconsistentes (FRE 2010 informa 412,7 mi de ações; FRE 2011, na
    # última versão, 1.719,7 mi "aprovado em 31/12/2010", mas o FRE 2012 data esse capital de 12/04/2011 e o
    # LPA de 2010 implica ~1.425 mi). Como os dados abertos guardam só a última versão do FRE, deixamos vazio.
    if ano < 2011:
        r = None
    acoes.append(
        {
            "data": lim,
            "fonte": "CVM FRE: capital social aprovado em "
            f"{r['Data_Autorizacao_Aprovacao'] if r is not None else 'n/d (FRE inconsistente)'}; "
            f"tesouraria ON {f_on}, PN {f_pn}",
            "on_total": r["Quantidade_Acoes_Ordinarias"] if r is not None else np.nan,
            "pn_total": r["Quantidade_Acoes_Preferenciais"] if r is not None else np.nan,
            "acoes_total": r["Quantidade_Total_Acoes"] if r is not None else np.nan,
            "on_tesouraria": on_t,
            "pn_tesouraria": pn_t,
            "tesouraria_total": on_t + pn_t,
            "url": "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FRE/DADOS/",
        }
    )
A = pd.DataFrame(acoes)
A["acoes_circulacao"] = A["acoes_total"] - A["tesouraria_total"]
A = A.sort_values("data").drop_duplicates("data", keep="first").reset_index(drop=True)
A.to_csv(os.path.join(OUT, "acoes_gerdau.csv"), index=False)

# junta ações ao painel anual da Gerdau + ações implícitas no LPA (conferência)
Aa = A[A["data"].str.endswith("12-31")].copy()
Aa["exercicio"] = Aa["data"].str[:4].astype(int)
F = F.merge(
    Aa[["exercicio", "acoes_total", "tesouraria_total", "acoes_circulacao", "fonte"]]
    .rename(columns={"fonte": "fonte_acoes"})
    .assign(empresa="GERDAU"),
    on=["empresa", "exercicio"],
    how="left",
)
F["acoes_implicitas_lpa"] = (F["lucro_controladores"] * 1000 / F["lpa_basico_pn"]).where(
    F["lpa_basico_pn"].abs() > 0.005
)

cols_id = ["empresa", "exercicio", "dt_fim_exercicio", "fonte_dfp", "versao", "dt_receb", "dt_receb_primeira"]
cols_var = [
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
    "lpa_basico_on",
    "lpa_basico_pn",
    "capex_imobilizado",
    "capex_intangivel",
    "capex",
    "dividendos_jcp_pagos_dfc",
    "contas_receber",
    "estoques",
    "fornecedores",
    "caixa_equivalentes",
    "aplicacoes_financeiras_cp",
    "caixa_aplicacoes",
    "emprestimos_financiamentos_cp",
    "debentures_cp",
    "arrend_financeiro_cp",
    "emprestimos_cp_total",
    "emprestimos_financiamentos_lp",
    "debentures_lp",
    "arrend_financeiro_lp",
    "emprestimos_lp_total",
    "divida_bruta",
    "arrend_ifrs16_cp",
    "arrend_ifrs16_lp",
    "arrendamentos_total",
    "divida_bruta_com_arrend_ifrs16",
    "divida_liquida",
    "ativo_total",
    "imobilizado",
    "intangivel",
    "pl_total",
    "pl_nao_controladores",
    "pl_controladores",
    "acoes_total",
    "tesouraria_total",
    "acoes_circulacao",
    "acoes_implicitas_lpa",
    "fonte_acoes",
    "dfc_metodo",
    "url_zip",
]
F = F[cols_id + cols_var].sort_values(["empresa", "exercicio"])
F.to_csv(os.path.join(OUT, "fundamentos_anuais.csv"), index=False)
pd.DataFrame(mapa).to_csv(os.path.join(OUT, "mapeamento_contas.csv"), index=False)

# 3) VALIDAÇÃO ---------------------------------------------------------------------------------
G = F[F["empresa"] == "GERDAU"].set_index("exercicio")
tab = pd.DataFrame(
    {
        "receita": G["receita_liquida"] / 1e3,
        "ebit": G["ebit"] / 1e3,
        "mg_ebit_%": 100 * G["ebit"] / G["receita_liquida"],
        "d&a": G["da"] / 1e3,
        "capex": G["capex"] / 1e3,
        "div_bruta": G["divida_bruta"] / 1e3,
        "caixa+aplic": G["caixa_aplicacoes"] / 1e3,
        "div_liq": G["divida_liquida"] / 1e3,
        "lucro_contr": G["lucro_controladores"] / 1e3,
        "acoes_circ_mi": G["acoes_circulacao"] / 1e6,
        "acoes_lpa_mi": G["acoes_implicitas_lpa"] / 1e6,
        "dt_receb": G["dt_receb"],
    }
)
# alertas automáticos: variações extremas
for col in ["receita", "ebit", "d&a", "capex", "div_bruta"]:
    s = tab[col]
    var = s.pct_change(fill_method=None)
    for a, x in var.items():
        if pd.notna(x) and abs(x) > 0.6:
            alertas.append(f"GERDAU {a}: {col} variou {100 * x:+.0f}% vs ano anterior (conferir)")
for a, r in tab.iterrows():
    if (
        pd.notna(r["acoes_circ_mi"])
        and pd.notna(r["acoes_lpa_mi"])
        and abs(r["acoes_circ_mi"] / r["acoes_lpa_mi"] - 1) > 0.1
    ):
        alertas.append(
            f"GERDAU {a}: ações em circulação ({r['acoes_circ_mi']:.0f} mi) difere >10% das implícitas no LPA "
            f"({r['acoes_lpa_mi']:.0f} mi)"
        )
    if pd.isna(r["acoes_circ_mi"]):
        alertas.append(f"GERDAU {a}: ações em circulação indisponível (usar acoes_implicitas_lpa como aproximação)")

pd.set_option("display.width", 250)
txt = (
    "TABELA DE VALIDAÇÃO — GERDAU S.A. consolidado (R$ milhões; ações em milhões)\n"
    + tab.round(1).to_string()
    + "\n\nALERTAS\n"
    + "\n".join(alertas)
)
open(os.path.join(OUT, "validacao_anual.txt"), "w", encoding="utf-8").write(txt)
print(txt)

# 4) TRIMESTRAL (Gerdau) -----------------------------------------------------------------------
# Princípio: para cada trimestre, os FLUXOS (DRE e DFC) são extraídos como ACUMULADO NO ANO (YTD):
#   - ITR: DRE com DT_INI_EXERC = 1º de janeiro (a CVM traz também a coluna de 3 meses) e DFC (sempre YTD);
#   - 4º tri: DFP anual.
# O trimestre isolado = YTD(t) − YTD(t−1) dentro do mesmo ano (no 1º tri, = YTD). Assim o 4º tri =
# DFP anual − 9 meses do ITR do 3º tri. Os SALDOS (BPA/BPP) vêm da posição na data de fim do trimestre.
# 2010 T1–T3: a série de ITR nos dados abertos começa em 2011, então os FLUXOS de 2010 vêm da coluna
# comparativa (PENÚLTIMO) dos ITRs de 2011 (entregues em 2011 -> NÃO estavam disponíveis em 2010);
# os saldos de 2010 T1–T3 ficam vazios.
FLUXOS = [
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
]
SALDOS = [
    c
    for c in cols_var
    if c not in FLUXOS
    and c
    not in (
        "lpa_basico_on",
        "lpa_basico_pn",
        "acoes_total",
        "tesouraria_total",
        "acoes_circulacao",
        "acoes_implicitas_lpa",
        "fonte_acoes",
        "dfc_metodo",
        "url_zip",
    )
]
itr = pd.read_csv(os.path.join(OUT, "cvm_itr_contas.csv"), dtype={"CD_CONTA": str})
itr = itr[itr["EMPRESA"] == "GERDAU"]
tri = []


def registro_tri(d_fluxo_ytd, d_saldo, dt_fim, info, fonte, obs=""):
    vf, _, _ = extrair(d_fluxo_ytd)
    r = {
        "dt_fim_periodo": dt_fim,
        "ano": int(dt_fim[:4]),
        "trimestre": int(dt_fim[5:7]) // 3,
        "documento": fonte.split()[0],
        "fonte": fonte,
        "versao": int(info["VERSAO"]),
        "dt_receb_primeira": info["DT_RECEB_PRIMEIRA"],
        "dt_receb": info["DT_RECEB"],
        "n_versoes": int(info["N_VERSOES"]) if pd.notna(info["N_VERSOES"]) else np.nan,
        "obs": obs,
    }
    for c in FLUXOS:
        r[c + "_ytd"] = vf.get(c, np.nan)
    if d_saldo is not None:
        vs, _, _ = extrair(d_saldo)
        for c in SALDOS:
            r[c] = vs.get(c, np.nan)
    return r


for dt_ref, g in itr.groupby("DT_REFER"):
    ano = int(dt_ref[:4])
    u = g[g["ORDEM_EXERC"] == ULT]
    ytd = u[(u["DEMONSTRACAO"] != "DRE") | (u["DT_INI_EXERC"] == f"{ano}-01-01")]
    saldo = u[u["DEMONSTRACAO"].isin(["BPA", "BPP"])]
    tri.append(registro_tri(ytd, saldo, dt_ref, u.iloc[0], f"ITR {dt_ref}"))
    if ano == 2011:  # comparativos -> fluxos de 2010 T1–T3
        p = g[(g["ORDEM_EXERC"] == PEN) & (g["DEMONSTRACAO"] != "BPA") & (g["DEMONSTRACAO"] != "BPP")]
        p = p[(p["DEMONSTRACAO"] != "DRE") | (p["DT_INI_EXERC"] == "2010-01-01")]
        dt10 = "2010" + dt_ref[4:]
        tri.append(
            registro_tri(
                p,
                None,
                dt10,
                u.iloc[0],
                f"ITR {dt_ref} (comparativo)",
                "fluxos de 2010 tirados do comparativo do ITR 2011; saldos indisponíveis",
            )
        )
Cg = C[C["EMPRESA"] == "GERDAU"]
for ano_dfp, g in Cg.groupby("ano_dfp"):
    u = g[g["ORDEM_EXERC"] == ULT]
    tri.append(registro_tri(u, u, f"{ano_dfp}-12-31", u.iloc[0], f"DFP {ano_dfp}"))
T = pd.DataFrame(tri).sort_values(["ano", "trimestre"]).drop_duplicates(["ano", "trimestre"]).reset_index(drop=True)
T = T[T["ano"] >= 2010].reset_index(drop=True)

# trimestre isolado a partir do acumulado
for c in FLUXOS:
    prev = T.groupby("ano")[c + "_ytd"].shift(1)
    T[c] = np.where(T["trimestre"] == 1, T[c + "_ytd"], T[c + "_ytd"] - prev)
    # se faltar o trimestre anterior do mesmo ano, o isolado fica NaN
    falta = (T["trimestre"] > 1) & (T.groupby("ano")["trimestre"].shift(1) != T["trimestre"] - 1)
    T.loc[falta, c] = np.nan
# LTM = soma dos 4 últimos trimestres consecutivos
T["_idx"] = T["ano"] * 4 + T["trimestre"]
consec = (T["_idx"] - T["_idx"].shift(3)) == 3
LTM = [
    "receita_liquida",
    "ebit",
    "ebit_ex_impairment",
    "da",
    "ebitda",
    "capex",
    "ir_cs",
    "lair",
    "lucro_liquido",
    "lucro_controladores",
    "despesa_juros_dfc",
]
for c in LTM:
    T[c + "_ltm"] = T[c].rolling(4, min_periods=4).sum().where(consec)
# conferência: LTM no 4º tri deve bater com o anual
chk = T[T["trimestre"] == 4][["ano", "receita_liquida_ltm", "receita_liquida_ytd"]].dropna()
dif = (chk["receita_liquida_ltm"] - chk["receita_liquida_ytd"]).abs().max()
print(f"Conferência LTM(4T) vs anual (receita): diferença máx. = {dif:,.1f} (R$ mil)")
# ações em circulação: composição do capital do próprio trimestre (ITR/DFP 2020+); antes, último dado anual
A2 = A.copy()
A2["dt"] = pd.to_datetime(A2["data"])
T["dt"] = pd.to_datetime(T["dt_fim_periodo"])
T = pd.merge_asof(
    T.sort_values("dt"),
    A2[["dt", "acoes_total", "tesouraria_total", "acoes_circulacao", "data"]]
    .sort_values("dt")
    .rename(columns={"data": "data_ref_acoes"}),
    on="dt",
    direction="backward",
)
cols_t = (
    ["dt_fim_periodo", "ano", "trimestre", "documento", "fonte", "versao", "n_versoes", "dt_receb_primeira", "dt_receb"]
    + FLUXOS
    + [c + "_ltm" for c in LTM]
    + SALDOS
    + ["acoes_total", "tesouraria_total", "acoes_circulacao", "data_ref_acoes"]
    + [c + "_ytd" for c in FLUXOS]
    + ["obs"]
)
T = T[cols_t]
T.to_csv(os.path.join(OUT, "fundamentos_trimestrais.csv"), index=False)
print("Trimestral:", len(T), "linhas", T["dt_fim_periodo"].min(), "a", T["dt_fim_periodo"].max())
q = (
    T.set_index("dt_fim_periodo")[
        [
            "receita_liquida",
            "ebit",
            "da",
            "capex",
            "ir_cs",
            "receita_liquida_ltm",
            "divida_bruta",
            "caixa_aplicacoes",
            "acoes_circulacao",
        ]
    ]
    / 1e3
)
print((q.round(0)).to_string())
