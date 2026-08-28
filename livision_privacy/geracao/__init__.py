"""
Geração do dataset sintético do Li-Vision.

    vocabulario.py  Listas de nomes, cidades, aparelhos, gestos. Só dados.
    fabricas.py     Constrói cada aba. Uma função por aba.
    sintetico.py    Orquestra as fábricas e devolve a planilha completa.
"""

from .sintetico import gerar_planilha

__all__ = ["gerar_planilha"]
