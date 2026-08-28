"""
Registro de técnicas: liga o nome decidido pela classificação à implementação.

Existe para eliminar a cadeia de `if/elif` que antes vivia dentro do laço de
anonimização. Com o registro, adicionar uma técnica é escrever a função em
`tecnicas.py` e registrá-la aqui — o pipeline não muda.

Cada handler recebe um `Contexto` (a coluna inteira mais o que a técnica precisa
de estado) e devolve a Series transformada, ou None para suprimir a coluna.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import pandas as pd

from . import tecnicas


@dataclass(frozen=True)
class Contexto:
    """Tudo que uma técnica pode precisar além dos próprios dados.

    Passar o estado explicitamente (em vez de a técnica ler um global ou um
    atributo de instância) é o que mantém `tecnicas.py` puro e testável.
    """

    coluna: str
    serie: pd.Series
    sal: bytes
    epsilon: float
    rng: np.random.Generator


#: Uma técnica devolve a Series transformada, ou None quando a coluna deve sumir.
Handler = Callable[[Contexto], Optional[pd.Series]]


def _manter(ctx: Contexto) -> pd.Series:
    return ctx.serie


def _suprimir(ctx: Contexto) -> None:
    return None


def _pseudonimizar(ctx: Contexto) -> pd.Series:
    prefixo = tecnicas.prefixo_para(ctx.coluna)
    return ctx.serie.apply(lambda v: tecnicas.pseudonimizar(v, ctx.sal, prefixo))


def _mascarar_nome(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.mascarar_nome)


def _mascarar_email(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.mascarar_email)


def _generalizar_ip(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.generalizar_ip)


def _generalizar_data(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.generalizar_data)


def _faixa_etaria(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.faixa_etaria)


def _generalizar_regiao(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.generalizar_regiao)


def _generalizar_device(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.generalizar_device)


def _generalizar_categoria(ctx: Contexto) -> pd.Series:
    # A frequência é da coluna inteira: só dá para saber o que é "raro" olhando
    # a distribuição, não valor a valor.
    frequencias = ctx.serie.value_counts().to_dict()
    return ctx.serie.apply(lambda v: tecnicas.generalizar_categoria(v, frequencias))


def _agregar_espacial(ctx: Contexto) -> pd.Series:
    return ctx.serie.apply(tecnicas.agregar_espacial)


def _ruido_laplace(ctx: Contexto) -> pd.Series:
    return tecnicas.ruido_laplace(ctx.serie, ctx.epsilon, ctx.rng)


def _bucketizar(ctx: Contexto) -> pd.Series:
    return tecnicas.bucketizar(ctx.serie)


HANDLERS: dict[str, Handler] = {
    "manter": _manter,
    "suprimir": _suprimir,
    "pseudonimizar": _pseudonimizar,
    "mascarar_nome": _mascarar_nome,
    "mascarar_email": _mascarar_email,
    "generalizar_ip": _generalizar_ip,
    "generalizar_data": _generalizar_data,
    "faixa_etaria": _faixa_etaria,
    "generalizar_regiao": _generalizar_regiao,
    "generalizar_device": _generalizar_device,
    "generalizar_categoria": _generalizar_categoria,
    "agregar_espacial": _agregar_espacial,
    "ruido_laplace": _ruido_laplace,
    "bucketizar": _bucketizar,
}


def aplicar(tecnica: str, ctx: Contexto) -> Optional[pd.Series]:
    """Executa a técnica registrada.

    Nome desconhecido é erro, não um silencioso "mantém como está": um typo na
    tabela de classificação publicaria a coluna original sem aviso.
    """
    try:
        handler = HANDLERS[tecnica]
    except KeyError:
        raise KeyError(
            f"Técnica '{tecnica}' não registrada em registry.HANDLERS. "
            f"Disponíveis: {', '.join(sorted(HANDLERS))}"
        ) from None
    return handler(ctx)
