"""Ponto de entrada da CLI a partir da raiz do projeto.

O pacote mora em `src/`, e o `pythonpath = ["src"]` do `pyproject.toml` só vale
para o `pytest`. Este arquivo faz o mesmo ajuste para a execução manual, para
que `python main.py` funcione sem instalar nada nem exportar `PYTHONPATH`.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from celular_robo.cli import main  # noqa: E402  (depende do sys.path acima)

if __name__ == "__main__":
    raise SystemExit(main())
