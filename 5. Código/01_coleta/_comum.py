"""
Funções e caminhos comuns aos scripts de coleta do TCC (Valuation Gerdau S.A.).

- Define os caminhos do projeto (pasta raw, planilha final).
- Faz downloads com registro de proveniência (URL, data/hora de coleta, arquivo local)
  em "4. Dados Gerdau/raw/_proveniencia.csv".
- Todos os scripts são idempotentes: um arquivo já baixado não é baixado de novo,
  a menos que se passe forcar=True (ou a flag --forcar na linha de comando).
"""

import csv
import datetime as dt
import os
import time

import requests

# Raiz do projeto = duas pastas acima deste arquivo (5. Código/01_coleta/ -> raiz)
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PASTA_DADOS = os.path.join(RAIZ, "4. Dados Gerdau")
PASTA_RAW = os.path.join(PASTA_DADOS, "Downloads originais (raw)")
PASTA_TRATADOS = os.path.join(
    PASTA_DADOS, "Tabelas intermediárias (CSV)"
)  # CSVs intermediários (gerados pelos scripts)
PLANILHA = os.path.join(PASTA_DADOS, "Database Valuation Gerdau.xlsx")  # versão enxuta (vai para o GitHub)
PLANILHA_COMPLETA = os.path.join(
    PASTA_TRATADOS, "Base completa (arquivo).xlsx"
)  # tudo o que foi coletado, para consulta
LOG_PROVENIENCIA = os.path.join(PASTA_RAW, "_proveniencia.csv")

# Identificação da entidade avaliada (NUNCA usar a Metalúrgica Gerdau, CVM 2879)
GERDAU_CD_CVM = 3980
GERDAU_CNPJ = "33.611.500/0001-19"

HEADERS = {"User-Agent": "Mozilla/5.0 (TCC IE-UFRJ - coleta de dados academica)"}


def pasta_raw(fonte):
    """Cria (se preciso) e devolve raw/<fonte>/."""
    p = os.path.join(PASTA_RAW, fonte)
    os.makedirs(p, exist_ok=True)
    return p


def pasta_tratados():
    os.makedirs(PASTA_TRATADOS, exist_ok=True)
    return PASTA_TRATADOS


def agora():
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def registrar(fonte, url, arquivo, obs=""):
    """Acrescenta uma linha ao log de proveniência (substitui registro anterior do mesmo arquivo)."""
    os.makedirs(PASTA_RAW, exist_ok=True)
    linhas = []
    if os.path.exists(LOG_PROVENIENCIA):
        with open(LOG_PROVENIENCIA, encoding="utf-8", newline="") as f:
            linhas = list(csv.DictReader(f))
    rel = os.path.relpath(arquivo, PASTA_DADOS).replace("\\", "/")
    linhas = [linha for linha in linhas if linha["arquivo"] != rel]
    linhas.append({"fonte": fonte, "url": url, "arquivo": rel, "data_coleta": agora(), "obs": obs})
    with open(LOG_PROVENIENCIA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["fonte", "url", "arquivo", "data_coleta", "obs"])
        w.writeheader()
        w.writerows(linhas)


def baixar(url, destino, fonte, forcar=False, tentativas=4, timeout=180, obs=""):
    """Baixa url -> destino (se ainda não existir). Devolve True se o arquivo existe ao final.
    Status 404 devolve False sem erro (ex.: ano ainda não publicado)."""
    if os.path.exists(destino) and os.path.getsize(destino) > 0 and not forcar:
        return True
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    for i in range(tentativas):
        try:
            r = requests.get(url, headers=HEADERS, timeout=timeout, stream=True)
            if r.status_code == 404:
                print(f"  404 (não existe): {url}")
                return False
            r.raise_for_status()
            tmp = destino + ".part"
            with open(tmp, "wb") as f:
                for bloco in r.iter_content(1 << 20):
                    f.write(bloco)
            os.replace(tmp, destino)
            registrar(fonte, url, destino, obs)
            print(f"  ok: {os.path.basename(destino)} ({os.path.getsize(destino) / 1e6:.1f} MB)")
            return True
        except Exception as e:  # noqa: BLE001
            print(f"  falha ({i + 1}/{tentativas}) {url}: {e}")
            time.sleep(3 * (i + 1))
    return False


def get_json(url, params=None, tentativas=4, timeout=120):
    """GET que devolve JSON, com novas tentativas."""
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001
            print(f"  falha ({i + 1}/{tentativas}) {url}: {e}")
            time.sleep(3 * (i + 1))
    raise RuntimeError(f"Não foi possível obter {url}")
