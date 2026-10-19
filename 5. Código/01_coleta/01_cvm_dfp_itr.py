"""
01 — CVM Dados Abertos: DFP (anual) e ITR (trimestral) de Gerdau S.A. e pares.

Etapas
  1. Baixa o cadastro de companhias abertas e localiza, PELO NOME, os códigos CVM de
     CSN (Cia Siderúrgica Nacional) e Usiminas; confirma Gerdau S.A. = CVM 3980 / CNPJ 33.611.500/0001-19.
     (NUNCA Metalúrgica Gerdau, CVM 2879.)
  2. Baixa os zips DFP 2010–2025 e ITR 2011–2026 para raw/cvm/dfp e raw/cvm/itr (se ainda não existirem).
  3. Lê, de dentro de cada zip (sem extrair tudo), apenas as linhas das empresas-alvo em:
       BPA_con, BPP_con, DRE_con, DFC_MI_con, DFC_MD_con (demonstrações consolidadas)
       composicao_capital (quantidade de ações; arquivo identificado por CNPJ)
       arquivo-índice <dfp|itr>_cia_aberta_AAAA.csv (todas as versões entregues, com DT_RECEB)
  4. Grava em "4. Dados Gerdau/Tabelas intermediárias (CSV)/":
       cvm_entidades.csv          -> empresas e códigos encontrados no cadastro
       cvm_dfp_entregas.csv       -> uma linha por (empresa, DT_REFER, VERSAO) com DT_RECEB e link do documento
       cvm_dfp_contas.csv         -> contas (todas as ORDEM_EXERC), já com DT_RECEB da versão,
                                     VERSAO, DT_RECEB_PRIMEIRA (1ª entrega do período) e N_VERSOES
       cvm_dfp_composicao_capital.csv
       (idem cvm_itr_*)
     Os valores são convertidos para R$ mil (VL_CONTA_MIL) quando ESCALA_MOEDA = 'UNIDADE'.

Observações
  - Os arquivos da CVM são latin-1, separador ';'.
  - Os arquivos de demonstrações trazem apenas a versão mais recente de cada documento; o índice
    traz todas as versões — por isso guardamos também a data da 1ª entrega (para a regra
    "informação disponível na data-base" usar a data correta).
Uso:  python -I 01_cvm_dfp_itr.py [--forcar]   (--forcar baixa os zips de novo)
"""

import io
import os
import site
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # pasta dos scripts (código próprio)
sys.path.append(site.getusersitepackages())  # pacotes instalados com pip --user (o -I os desativa)
import pandas as pd  # noqa: E402
from _comum import GERDAU_CD_CVM, GERDAU_CNPJ, baixar, pasta_raw, pasta_tratados, registrar  # noqa: E402

FORCAR = "--forcar" in sys.argv
BASE = "https://dados.cvm.gov.br/dados/CIA_ABERTA"
RAW = pasta_raw("cvm")
OUT = pasta_tratados()
ANOS = {"dfp": range(2010, 2026), "itr": range(2011, 2027)}
DEMONSTRACOES = ["BPA_con", "BPP_con", "DRE_con", "DFC_MI_con", "DFC_MD_con"]

# ---------------------------------------------------------------- 1. cadastro
url_cad = f"{BASE}/CAD/DADOS/cad_cia_aberta.csv"
arq_cad = os.path.join(RAW, "cad_cia_aberta.csv")
baixar(url_cad, arq_cad, "CVM cadastro", forcar=FORCAR)
cad = pd.read_csv(arq_cad, sep=";", encoding="latin-1", dtype=str)
cad["CD_CVM_INT"] = pd.to_numeric(cad["CD_CVM"], errors="coerce")


def procurar(padrao):
    """Procura no cadastro por DENOM_SOCIAL (regex), preferindo registro ATIVO."""
    m = cad[cad["DENOM_SOCIAL"].str.contains(padrao, case=False, regex=True, na=False)]
    ativos = m[m["SIT"] == "ATIVO"]
    m = ativos if not ativos.empty else m
    m = m.drop_duplicates("CD_CVM_INT")
    if len(m) != 1:
        print(m[["DENOM_SOCIAL", "CD_CVM", "CNPJ_CIA", "SIT"]])
        raise SystemExit(f"Busca ambígua/vazia no cadastro: {padrao}")
    r = m.iloc[0]
    return int(r["CD_CVM_INT"]), r["CNPJ_CIA"], r["DENOM_SOCIAL"], r["SIT"]


ger = cad[cad["CD_CVM_INT"] == GERDAU_CD_CVM].iloc[0]
assert ger["CNPJ_CIA"] == GERDAU_CNPJ, "CNPJ da Gerdau não confere!"
ent = {
    "GERDAU": (GERDAU_CD_CVM, GERDAU_CNPJ, ger["DENOM_SOCIAL"], ger["SIT"]),
    "CSN": procurar(r"^CIA SIDERURGICA NACIONAL$|^COMPANHIA SIDER[UÚ]RGICA NACIONAL$"),
    # nome no cadastro: "USINAS SID DE MINAS GERAIS S.A.-USIMINAS"
    "USIMINAS": procurar(r"USINAS SID.* DE MINAS GERAIS.*USIMINAS"),
}
df_ent = pd.DataFrame(
    [{"EMPRESA": k, "CD_CVM": v[0], "CNPJ_CIA": v[1], "DENOM_SOCIAL": v[2], "SIT": v[3]} for k, v in ent.items()]
)
df_ent.to_csv(os.path.join(OUT, "cvm_entidades.csv"), index=False)
print(df_ent.to_string(index=False))
assert 2879 not in df_ent["CD_CVM"].values  # Metalúrgica Gerdau jamais
CODIGOS = {v[0]: k for k, v in ent.items()}
CNPJS = {v[1]: k for k, v in ent.items()}


# ---------------------------------------------------------------- 2/3. zips
def ler_csv_do_zip(z, nome):
    with z.open(nome) as f:
        return pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str)


for tipo, anos in ANOS.items():
    contas, entregas, capital = [], [], []
    for ano in anos:
        nome_zip = f"{tipo}_cia_aberta_{ano}.zip"
        url = f"{BASE}/DOC/{tipo.upper()}/DADOS/{nome_zip}"
        arq = os.path.join(RAW, tipo, nome_zip)
        if not baixar(url, arq, f"CVM {tipo.upper()}", forcar=FORCAR):
            print(f"{nome_zip}: indisponível")
            continue
        z = zipfile.ZipFile(arq)
        nomes = z.namelist()
        # índice de entregas (todas as versões)
        idx = ler_csv_do_zip(z, f"{tipo}_cia_aberta_{ano}.csv")
        idx["CD_CVM_INT"] = pd.to_numeric(idx["CD_CVM"], errors="coerce")
        idx = idx[idx["CD_CVM_INT"].isin(CODIGOS)].copy()
        idx["ARQUIVO_ZIP"] = nome_zip
        idx["URL_ZIP"] = url
        entregas.append(idx)
        # demonstrações consolidadas
        for dem in DEMONSTRACOES:
            n = f"{tipo}_cia_aberta_{dem}_{ano}.csv"
            if n not in nomes:
                continue
            d = ler_csv_do_zip(z, n)
            d["CD_CVM_INT"] = pd.to_numeric(d["CD_CVM"], errors="coerce")
            d = d[d["CD_CVM_INT"].isin(CODIGOS)].copy()
            d["DEMONSTRACAO"] = dem.replace("_con", "")
            d["ARQUIVO_ZIP"] = nome_zip
            d["URL_ZIP"] = url
            contas.append(d)
        # composição do capital (não tem CD_CVM -> filtra por CNPJ)
        n = f"{tipo}_cia_aberta_composicao_capital_{ano}.csv"
        if n in nomes:
            c = ler_csv_do_zip(z, n)
            c = c[c["CNPJ_CIA"].isin(CNPJS)].copy()
            c["EMPRESA"] = c["CNPJ_CIA"].map(CNPJS)
            c["ARQUIVO_ZIP"] = nome_zip
            c["URL_ZIP"] = url
            capital.append(c)
        print(f"{nome_zip}: lido ({sum(len(x) for x in contas)} linhas acumuladas)")

    # ---------------- consolida e grava
    E = pd.concat(entregas, ignore_index=True)
    E["VERSAO"] = E["VERSAO"].astype(int)
    E["EMPRESA"] = E["CD_CVM_INT"].map(CODIGOS)
    prim = (
        E.groupby(["CD_CVM_INT", "DT_REFER"])
        .agg(DT_RECEB_PRIMEIRA=("DT_RECEB", "min"), N_VERSOES=("VERSAO", "nunique"), VERSAO_MAX=("VERSAO", "max"))
        .reset_index()
    )
    E.drop(columns="CD_CVM_INT").to_csv(os.path.join(OUT, f"cvm_{tipo}_entregas.csv"), index=False)

    C = pd.concat(contas, ignore_index=True)
    C["VERSAO"] = C["VERSAO"].astype(int)
    C["EMPRESA"] = C["CD_CVM_INT"].map(CODIGOS)
    # data de entrega da versão efetivamente presente no arquivo de demonstrações
    C = C.merge(
        E[["CD_CVM_INT", "DT_REFER", "VERSAO", "DT_RECEB", "ID_DOC"]],
        on=["CD_CVM_INT", "DT_REFER", "VERSAO"],
        how="left",
    )
    C = C.merge(prim, on=["CD_CVM_INT", "DT_REFER"], how="left")
    # se, por algum motivo, houver mais de uma versão no arquivo, fica só a mais recente
    vmax = C.groupby(["CD_CVM_INT", "DT_REFER"])["VERSAO"].transform("max")
    C = C[C["VERSAO"] == vmax]
    C["VL_CONTA"] = pd.to_numeric(C["VL_CONTA"], errors="coerce")
    C["VL_CONTA_MIL"] = C["VL_CONTA"].where(C["ESCALA_MOEDA"] == "MIL", C["VL_CONTA"] / 1000)
    cols = [
        "EMPRESA",
        "CD_CVM_INT",
        "CNPJ_CIA",
        "DENOM_CIA",
        "DT_REFER",
        "VERSAO",
        "ID_DOC",
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
        "ESCALA_MOEDA",
        "MOEDA",
        "ST_CONTA_FIXA",
        "ARQUIVO_ZIP",
        "URL_ZIP",
    ]
    cols = [c for c in cols if c in C.columns]
    C = C[cols].rename(columns={"CD_CVM_INT": "CD_CVM"})
    C.to_csv(os.path.join(OUT, f"cvm_{tipo}_contas.csv"), index=False)

    if capital:
        K = pd.concat(capital, ignore_index=True)
        K["VERSAO"] = K["VERSAO"].astype(int)
        K = K[K["VERSAO"] == K.groupby(["CNPJ_CIA", "DT_REFER"])["VERSAO"].transform("max")]
        K.to_csv(os.path.join(OUT, f"cvm_{tipo}_composicao_capital.csv"), index=False)
    print(
        f"{tipo.upper()}: {len(C)} linhas de contas; {len(E)} entregas; "
        f"{sum(len(k) for k in capital)} linhas de composição do capital"
    )

registrar(
    "CVM (derivado)",
    f"{BASE}/DOC/",
    os.path.join(OUT, "cvm_dfp_contas.csv"),
    "extrato filtrado (Gerdau, CSN, Usiminas) dos zips DFP/ITR em raw/cvm",
)
