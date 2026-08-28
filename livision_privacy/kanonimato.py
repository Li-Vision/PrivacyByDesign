"""
Imposição de k-anonimato.

Separado de `metricas.py`: aqui está a única operação que MODIFICA o DataFrame
em nome do k. A medição fica do outro lado, para que o efeito seja auditável.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from .metricas import SUPRIMIDO


@dataclass
class ResultadoK:
    """O que a imposição de k-anonimato fez com a tabela."""

    df: pd.DataFrame
    celulas_suprimidas: int = 0
    colunas_removidas: list[str] = field(default_factory=list)


def impor_k_anonimato(df: pd.DataFrame, quase_ids, k: int) -> ResultadoK:
    """Garante k-anonimato com a menor perda de informação possível.

    Suprimir células diretamente seria destrutivo: com vários quase-identificadores
    cruzados, quase toda classe de equivalência fica abaixo de k e o resultado é
    uma tabela de '*' — k alto no papel, utilidade analítica zero. Foi exatamente
    o que aconteceu com a aba `usuarios` numa versão anterior (120 linhas, todas
    mascaradas, k reportado como 120).

    Por isso a estratégia tem duas etapas:

    1. **Generalização por remoção.** Enquanto k estiver abaixo do mínimo, remove
       o quase-identificador de MAIOR cardinalidade. Menos colunas cruzadas
       significa classes de equivalência maiores. O atributo mais granular é o
       que mais individualiza, então sai primeiro.

    2. **Supressão residual.** Só então mascara as células das classes que ainda
       ficaram abaixo de k — normalmente uma fração pequena das linhas.

    Suprime a célula, não a linha: as métricas de gesto e acurácia continuam
    válidas para análise, apenas o vínculo com a pessoa é cortado.
    """
    presentes = [c for c in quase_ids if c in df.columns]
    if not presentes or df.empty:
        return ResultadoK(df=df)

    resultado = df.copy()
    ativos = list(presentes)
    removidas: list[str] = []

    # Etapa 1 — generalização por remoção do atributo mais granular.
    while len(ativos) > 1:
        if resultado.groupby(ativos, dropna=False).size().min() >= k:
            break
        alvo = max(ativos, key=lambda c: resultado[c].nunique(dropna=False))
        ativos.remove(alvo)
        removidas.append(alvo)
        resultado = resultado.drop(columns=[alvo])

    # Etapa 2 — supressão residual das classes que restaram abaixo de k.
    tamanhos = resultado.groupby(ativos, dropna=False)[ativos[0]].transform("size")
    raros = tamanhos < k
    if raros.any():
        resultado.loc[raros, ativos] = SUPRIMIDO

    return ResultadoK(
        df=resultado,
        celulas_suprimidas=int(raros.sum()),
        colunas_removidas=removidas,
    )
