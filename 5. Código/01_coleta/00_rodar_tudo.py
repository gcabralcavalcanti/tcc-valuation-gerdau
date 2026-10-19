# -*- coding: utf-8 -*-
"""
00 — Roda toda a coleta e a montagem da planilha, na ordem certa.
Cada etapa é chamada com "python -I" (modo isolado: não importa código da pasta corrente nem
das pastas de dados baixados). Uso:  python -I 00_rodar_tudo.py [--forcar]
--forcar  rebaixa os arquivos já existentes (atualização completa).
"""
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
ETAPAS = ["01_cvm_dfp_itr.py", "01b_cvm_fre_acoes.py", "02_precos_yfinance.py", "03_bcb_sgs_focus.py",
          "04_fred_setor.py", "04b_mercado_custo_capital.py", "05_fundamentos_cvm.py", "06_montar_planilha.py",
          "07_planilha_enxuta.py"]
extra = [a for a in sys.argv[1:] if a == "--forcar"]
for e in ETAPAS:
    print(f"\n===== {e} =====", flush=True)
    r = subprocess.run([sys.executable, "-I", os.path.join(AQUI, e)] + extra, cwd=AQUI)
    if r.returncode != 0:
        sys.exit(f"Falhou: {e}")
print("\nConcluído.")
