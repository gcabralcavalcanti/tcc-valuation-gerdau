# Coleta de dados — TCC Valuation Gerdau S.A. (GGBR4)

Scripts Python que baixam os dados brutos e montam `4. Dados Gerdau/Database Valuation Gerdau.xlsx`.
Todos são **re-executáveis e idempotentes**: arquivos já baixados não são baixados de novo (use `--forcar` para atualizar).

## Requisitos

Python 3.10+ e os pacotes: `pip install pandas openpyxl requests yfinance`

## Como rodar

Na pasta `5. Código/01_coleta/`:

```bash
python -I 00_rodar_tudo.py            # tudo, na ordem (≈1 min se os zips da CVM já estiverem baixados)
python -I 00_rodar_tudo.py --forcar   # rebaixa tudo (os zips da CVM somam ~700 MB)
```

Ou etapa por etapa:

| Ordem | Script | O que faz | Saída |
|---|---|---|---|
| 01 | `01_cvm_dfp_itr.py` | Cadastro CVM (acha CSN e Usiminas pelo nome), zips DFP 2010–2025 e ITR 2011–2026. Extrai BPA/BPP/DRE/DFC consolidados, composição do capital e as datas de entrega (`DT_RECEB`) de Gerdau, CSN e Usiminas | `Downloads originais (raw)/cvm/`, `Tabelas intermediárias (CSV)/cvm_*` |
| 01b | `01b_cvm_fre_acoes.py` | Formulário de Referência 2010–2026: capital social e ações em tesouraria (a composição do capital da DFP/ITR só existe a partir de 2020) | `Downloads originais (raw)/cvm/fre/`, `Tabelas intermediárias (CSV)/cvm_fre_*` |
| 02 | `02_precos_yfinance.py` | Preços diários 2005–hoje (GGBR4, GGBR3, ^BVSP, CSNA3, USIM5), proventos e desdobramentos. Alternativa: stooq | `Downloads originais (raw)/yfinance/` |
| 03 | `03_bcb_sgs_focus.py` | BCB-SGS (CDI 12, Selic 11, meta Selic 432, PTAX 1, IPCA 433, IBC-Br 24363, PIB 7326) em blocos de 5 anos; Focus anual (PIB, IPCA, Câmbio, Selic) | `Downloads originais (raw)/bcb/`, `Tabelas intermediárias (CSV)/focus_mensal.csv` |
| 04 | `04_fred_setor.py` | FRED: PPIs do aço (WPU101, WPU1017, WPU101704, WPU101703, …), sucata, minério de ferro | `Downloads originais (raw)/fred/` |
| 04b | `04b_mercado_custo_capital.py` | FRED (Baa e Treasury de 10 anos), Ipeadata (EMBI+ Brasil, até 30/07/2024) e Shiller (retornos totais reais dos EUA desde 1871): custo da dívida e prêmio de risco | `Downloads originais (raw)/fred/`, `ipeadata/`, `shiller/`; `Tabelas intermediárias (CSV)/spread_baa_mensal.csv`, `embi_diario.csv`, `retornos_eua_dezembro.csv` |
| 05 | `05_fundamentos_cvm.py` | Mapeia as contas CVM em variáveis do modelo; painel anual (2009–2025) e trimestral (2010T1–último ITR, com LTM); ações em circulação; validação | `Tabelas intermediárias (CSV)/fundamentos_*.csv`, `Tabelas intermediárias (CSV)/validacao_anual.txt` |
| 06 | `06_montar_planilha.py` | Monta a base completa (trimestral, pares, setor) | `Tabelas intermediárias (CSV)/Base completa (arquivo).xlsx` |
| 07 | `07_planilha_enxuta.py` | Monta a planilha da versão 1 (5 datas-base, 7 abas) | `Database Valuation Gerdau.xlsx` |

`_comum.py` tem os caminhos, a função de download e o registro de proveniência.

## Regras de segurança/organização

- Arquivos baixados ficam em `4. Dados Gerdau/Downloads originais (raw)/<fonte>/` e são tratados como **dados** (nunca executados).
  Os scripts ficam fora dessas pastas e rodam com `python -I` (modo isolado). Como o `-I` também desliga os
  pacotes instalados com `pip --user`, cada script adiciona explicitamente `site.getusersitepackages()` ao `sys.path`.
- Cada download é registrado em `Downloads originais (raw)/_proveniencia.csv` (fonte, URL, arquivo, data/hora da coleta).
- `Tabelas intermediárias (CSV)/` guarda os extratos filtrados e painéis intermediários (CSV) que alimentam a planilha.

## Entidade

Gerdau S.A., **CVM 3980**, CNPJ 33.611.500/0001-19 (o script confere o CNPJ). Nunca a Metalúrgica Gerdau (CVM 2879).
Pares, localizados no cadastro: CSN = CVM 4030 (33.042.730/0001-04); Usiminas = CVM 14320 (60.894.730/0001-05).

## GitHub

Para o repositório, basta versionar `5. Código/` e `4. Dados Gerdau/Database Valuation Gerdau.xlsx` (~2 MB).
Sugere-se colocar `4. Dados Gerdau/Downloads originais (raw)/` no `.gitignore` (os zips da CVM têm ~700 MB); eles podem ser
recriados com `00_rodar_tudo.py`.

## Uso no Colab

```python
import pandas as pd

URL = (
    "https://raw.githubusercontent.com/gcabralcavalcanti/tcc-valuation-gerdau/main/"
    "4.%20Dados%20Gerdau/Database%20Valuation%20Gerdau.xlsx"
)
datas = pd.read_excel(URL, sheet_name="Datas-base")
fund = pd.read_excel(URL, sheet_name="Fundamentos")
```
