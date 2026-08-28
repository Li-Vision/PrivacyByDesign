"""
Orquestração da geração sintética.

Só define a ordem e as dependências entre as abas — cada uma é construída pela
fábrica correspondente. `ranking` depende de `amostras`, que depende de
`usuarios`; por isso a ordem aqui não é arbitrária.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

import numpy as np
import pandas as pd

from . import fabricas
from . import vocabulario as voc


@dataclass(frozen=True)
class Volume:
    """Quantidade de registros a gerar por aba."""

    usuarios: int = 120
    amostras: int = 3000
    sessoes: int = 800


def gerar_planilha(volume: Volume | None = None,
                   seed: int = voc.SEED) -> dict[str, pd.DataFrame]:
    """Gera a planilha sintética completa.

    Seed fixa por padrão: rodar duas vezes produz exatamente o mesmo arquivo,
    o que torna possível comparar saídas do pipeline entre execuções.
    """
    vol = volume or Volume()
    rng = random.Random(seed)
    npr = np.random.default_rng(seed)

    usuarios = fabricas.criar_usuarios(rng, npr, vol.usuarios)
    amostras = fabricas.criar_amostras(rng, npr, usuarios, vol.amostras)
    sessoes = fabricas.criar_sessoes(rng, npr, usuarios, vol.sessoes)

    return {
        "usuarios": usuarios,
        "amostras_coleta": amostras,
        "sessoes_traducao": sessoes,
        "ranking": fabricas.criar_ranking(usuarios, amostras),
        "progresso_aprendizado": fabricas.criar_progresso(rng, npr, usuarios),
        "modelos_treinados": fabricas.criar_modelos(rng, npr),
    }
