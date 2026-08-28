"""
Saída de terminal: encoding e formatação de relatório.

Isolado para que o pipeline não misture cálculo com apresentação — e para que o
fix de encoding do Windows exista em um lugar só, em vez de repetido no topo de
cada script.
"""

from __future__ import annotations

import sys
from typing import Iterable, Mapping, Sequence


def configurar_encoding() -> None:
    """Força UTF-8 no stdout.

    O console do Windows usa cp1252 por padrão e levanta UnicodeEncodeError ao
    imprimir 'ε' ou texto acentuado. `errors="replace"` garante que um caractere
    exótico degrade para '?' em vez de derrubar o processo no meio do relatório.
    """
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8", errors="replace")


def titulo(texto: str) -> None:
    print(f"\n{texto}")


def contagem(titulo_secao: str, itens: Mapping[str, int], largura: int = 26) -> None:
    """Imprime um mapa nome → quantidade, alinhado."""
    print(f"\n{titulo_secao}")
    for nome, qtd in itens.items():
        print(f"  {nome:<{largura}} {qtd:>3}")


def tabela(cabecalhos: Sequence[str], linhas: Iterable[Sequence[object]],
           larguras: Sequence[int]) -> None:
    """Tabela de largura fixa. Primeira coluna à esquerda, demais à direita."""
    cab = f"  {str(cabecalhos[0]):<{larguras[0]}}"
    cab += "".join(f"{str(c):>{w}}" for c, w in zip(cabecalhos[1:], larguras[1:]))
    print(f"\n{cab}")
    for linha in linhas:
        texto = f"  {str(linha[0]):<{larguras[0]}}"
        texto += "".join(f"{str(v):>{w}}" for v, w in zip(linha[1:], larguras[1:]))
        print(texto)
