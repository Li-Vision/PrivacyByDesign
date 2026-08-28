"""
Entrada e saída de planilhas.

Único módulo que conhece pandas.ExcelWriter/openpyxl. Trocar o formato de saída
(CSV, Parquet, banco) implica reescrever só este arquivo — o pipeline devolve
DataFrames e não sabe onde eles serão gravados.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

#: Largura máxima de coluna no Excel, em caracteres.
LARGURA_MAXIMA = 42

#: Quantas linhas inspecionar para estimar a largura de uma coluna.
#: Varrer a planilha inteira seria lento sem ganho visível de precisão.
LINHAS_AMOSTRA_LARGURA = 200


def ler_planilha(caminho: Path) -> dict[str, pd.DataFrame]:
    """Lê todas as abas. Retorna {nome_da_aba: DataFrame}."""
    if not caminho.exists():
        raise FileNotFoundError(caminho)
    return pd.read_excel(caminho, sheet_name=None)


def escrever_planilha(caminho: Path, abas: dict[str, pd.DataFrame]) -> None:
    """Grava as abas na ordem dada, com largura de coluna ajustada."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(caminho, engine="openpyxl") as writer:
        for nome, df in abas.items():
            df.to_excel(writer, sheet_name=nome, index=False)
            _ajustar_larguras(writer, nome, df)


def _ajustar_larguras(writer: pd.ExcelWriter, aba: str, df: pd.DataFrame) -> None:
    """Ajusta a largura de cada coluna ao conteúdo e congela o cabeçalho."""
    ws = writer.sheets[aba]
    for idx, coluna in enumerate(df.columns, start=1):
        tamanhos = [len(str(v)) for v in df[coluna].head(LINHAS_AMOSTRA_LARGURA)]
        largura = max([len(str(coluna))] + tamanhos) + 2
        letra = ws.cell(row=1, column=idx).column_letter
        ws.column_dimensions[letra].width = min(largura, LARGURA_MAXIMA)
    ws.freeze_panes = "A2"


def resolver_caminho(valor: str, base: Path) -> Path:
    """Caminho relativo é resolvido contra `base`, não contra o cwd.

    Assim os scripts funcionam de qualquer diretório: `python data-privacy/x.py`
    encontra a planilha ao lado do script, e não onde o terminal está.
    """
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else base / caminho
