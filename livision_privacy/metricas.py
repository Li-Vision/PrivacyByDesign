"""
Métricas de privacidade — apenas MEDEM, nunca modificam.

Separado de `kanonimato.py` de propósito: medir e transformar são operações
distintas, e misturá-las esconderia o efeito real da transformação. Aqui é
possível auditar o dataset sem risco de alterá-lo.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from . import config

#: Marcador de célula suprimida pelo k-anonimato.
SUPRIMIDO = "*"


@dataclass
class RelatorioK:
    """Resultado da medição de k-anonimato."""

    k: int | None = None
    quase_identificadores: list[str] = field(default_factory=list)
    classes_equivalencia: int = 0
    registros_unicos: int = 0
    registros_suprimidos: int = 0
    registros_em_risco: int = 0
    pct_em_risco: float = 0.0


def _colunas_presentes(df: pd.DataFrame, colunas) -> list[str]:
    return [c for c in colunas if c in df.columns]


def medir_k_anonimato(df: pd.DataFrame, quase_ids) -> RelatorioK:
    """k = tamanho da menor classe de equivalência.

    k=1 significa que existe alguém único na combinação de quase-identificadores
    — reidentificável cruzando com qualquer base externa.

    Linhas já totalmente suprimidas ('*' em todos os quase-identificadores) são
    excluídas do cálculo: elas não formam uma classe reidentificável, são o
    "resto" anônimo. Contá-las junto reportaria um k artificialmente baixo para
    a parte da tabela que de fato foi publicada.
    """
    presentes = _colunas_presentes(df, quase_ids)
    if not presentes or df.empty:
        return RelatorioK(quase_identificadores=presentes)

    suprimidas = (df[presentes].astype(str) == SUPRIMIDO).all(axis=1)
    base = df.loc[~suprimidas]
    if base.empty:
        return RelatorioK(
            quase_identificadores=presentes,
            registros_suprimidos=int(suprimidas.sum()),
        )

    grupos = base.groupby(presentes, dropna=False).size()
    em_risco = int(grupos[grupos < config.K_ANONIMATO_PADRAO].sum())

    return RelatorioK(
        k=int(grupos.min()),
        quase_identificadores=presentes,
        classes_equivalencia=int(len(grupos)),
        registros_unicos=int((grupos == 1).sum()),
        registros_suprimidos=int(suprimidas.sum()),
        registros_em_risco=em_risco,
        pct_em_risco=round(100 * em_risco / len(base), 2),
    )


def medir_l_diversidade(df: pd.DataFrame, quase_ids, sensiveis) -> dict[str, int]:
    """l = menor nº de valores distintos de um atributo sensível numa classe.

    Complementa o k-anonimato: se todas as pessoas de uma classe compartilham o
    mesmo valor sensível (l=1), o atributo vaza mesmo com k alto — saber que
    alguém está na classe já revela o valor.
    """
    qids = _colunas_presentes(df, quase_ids)
    cols = _colunas_presentes(df, sensiveis)
    if not qids or not cols or df.empty:
        return {}

    resultado: dict[str, int] = {}
    for coluna in cols:
        distintos = df.groupby(qids, dropna=False)[coluna].nunique()
        resultado[coluna] = int(distintos.min()) if len(distintos) else 0
    return resultado
