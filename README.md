# Valuation da Gerdau S.A. (GGBR4)

Dados e código da monografia de graduação em Ciências Econômicas (IE-UFRJ), de Guilherme Cabral Cavalcanti,
com orientação do Prof. Pedro Hemsley.

Pergunta: a janela usada para estimar as premissas do fluxo de caixa descontado (crescimento, margem, beta,
perpetuidade) gera desvios sistemáticos entre valor justo e preço, ligados à fase do ciclo do aço?

## Conteúdo

| Caminho | O que é |
|---|---|
| `4. Dados Gerdau/Database Valuation Gerdau.xlsx` | Todos os dados do modelo: datas-base, fundamentos anuais (CVM), preços diários, macro e expectativas Focus |
| `5. Código/03_modelo/Modelo FCD Gerdau.ipynb` | Modelo FCFF/WACC nas 5 datas-base, com beta por regressão e janelas de 3, 5 e 10 anos |
| `5. Código/01_coleta/` | Scripts que baixam os dados públicos (CVM, Yahoo Finance, BCB, FRED) e montam a planilha |

## Como rodar

[Abrir o notebook no Colab](https://colab.research.google.com/github/gcabralcavalcanti/tcc-valuation-gerdau/blob/main/5.%20C%C3%B3digo/03_modelo/Modelo%20FCD%20Gerdau.ipynb).
Ele lê a planilha deste link:

```
https://raw.githubusercontent.com/gcabralcavalcanti/tcc-valuation-gerdau/main/4.%20Dados%20Gerdau/Database%20Valuation%20Gerdau.xlsx
```

Para refazer a planilha a partir das fontes: `python -I "5. Código/01_coleta/00_rodar_tudo.py"` (os arquivos da CVM somam ~700 MB).
