"""
Orquestração do pipeline de anonimização.

Este módulo COORDENA as etapas; não implementa nenhuma delas. Ele não sabe como
mascarar um e-mail, como calcular k, nem como gravar um Excel — apenas em que
ordem essas coisas acontecem e como o resultado é registrado.

Fluxo por aba:
    classificar → aplicar técnicas → deduplicar destinos → impor k → medir
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from . import classificacao, config, io_excel, kanonimato, metricas, registry
from .classificacao import Risco


# --------------------------------------------------------------------------
# Segredo
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Segredo:
    """Sal do HMAC e a procedência dele (para o relatório)."""

    sal: bytes
    origem: str

    @classmethod
    def carregar(cls) -> "Segredo":
        """Lê o sal do ambiente; sem ele, gera um efêmero.

        O sal nunca é gravado junto da saída — sem ele o HMAC é irreversível.
        Em produção viria de um cofre (Vault, AWS Secrets Manager). Um sal
        efêmero é seguro, mas troca os pseudônimos a cada execução: exportações
        de datas diferentes deixam de ser vinculáveis entre si.
        """
        valor = os.environ.get(config.ENV_SAL)
        if valor:
            return cls(valor.encode("utf-8"), f"variável de ambiente {config.ENV_SAL}")
        return cls(secrets.token_bytes(32),
                   "gerado aleatoriamente nesta execução (não persistido)")


# --------------------------------------------------------------------------
# Registros de auditoria
# --------------------------------------------------------------------------

@dataclass
class EntradaLog:
    """Uma decisão tomada sobre uma coluna."""

    aba: str
    coluna: str
    classe: str
    tecnica: str
    destino: str | None


@dataclass
class MetricasAba:
    """Resumo do que aconteceu com uma aba."""

    aba: str
    linhas: int
    colunas_entrada: int
    colunas_saida: int
    colunas_suprimidas: int
    k_antes: int | None
    k_depois: int | None
    celulas_suprimidas_por_k: int
    colunas_removidas_por_k: str
    registros_unicos_antes: int
    l_diversidade: dict[str, int] = field(default_factory=dict)


@dataclass
class Resultado:
    """Saída completa do pipeline."""

    abas: dict[str, pd.DataFrame]
    log: list[EntradaLog]
    metricas: list[MetricasAba]
    segredo: Segredo

    def log_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            [(e.aba, e.coluna, e.classe, e.tecnica, e.destino) for e in self.log],
            columns=["aba", "coluna", "classe", "tecnica", "destino"],
        )

    def metricas_df(self) -> pd.DataFrame:
        import json

        linhas = []
        for m in self.metricas:
            registro = m.__dict__.copy()
            registro["l_diversidade"] = json.dumps(m.l_diversidade, ensure_ascii=False)
            linhas.append(registro)
        return pd.DataFrame(linhas)


# --------------------------------------------------------------------------
# Anonimização de uma aba
# --------------------------------------------------------------------------

class Anonimizador:
    """Aplica o pipeline. Guarda apenas o estado compartilhado entre abas."""

    def __init__(self, segredo: Segredo, k: int = config.K_ANONIMATO_PADRAO,
                 epsilon: float = config.EPSILON_PADRAO) -> None:
        self.segredo = segredo
        self.k = k
        self.epsilon = epsilon
        # RNG único para toda a execução: seed fixa mantém a saída reprodutível.
        self._rng = np.random.default_rng(config.SEED_RUIDO)

    # -- etapa 1: técnicas por coluna --------------------------------------

    def _transformar_colunas(
        self, df: pd.DataFrame, aba: str
    ) -> tuple[pd.DataFrame, list[EntradaLog]]:
        """Classifica cada coluna e aplica a técnica correspondente.

        A deduplicação por destino acontece aqui: quando duas colunas de origem
        colapsam no mesmo nome (cidade e uf → regiao), a primeira vence e a
        segunda é registrada como redundante.
        """
        saida = pd.DataFrame(index=df.index)
        log: list[EntradaLog] = []

        for decisao in classificacao.classificar(list(df.columns)):
            coluna = decisao.coluna
            ctx = registry.Contexto(
                coluna=coluna,
                serie=df[coluna],
                sal=self.segredo.sal,
                epsilon=self.epsilon,
                rng=self._rng,
            )
            transformada = registry.aplicar(decisao.tecnica, ctx)

            if transformada is None:
                log.append(EntradaLog(aba, coluna, decisao.risco.value,
                                      decisao.tecnica, None))
                continue

            destino = config.RENOMEAR.get(coluna, coluna)
            if destino in saida.columns:
                log.append(EntradaLog(aba, coluna, decisao.risco.value,
                                      "supressao_redundante", None))
                continue

            saida[destino] = transformada
            log.append(EntradaLog(aba, coluna, decisao.risco.value,
                                  decisao.tecnica, destino))

        # Colunas que ficaram inteiramente vazias não carregam informação.
        vazias = saida.astype(str).eq("").all()
        return saida.loc[:, ~vazias], log

    # -- etapa 2: aba completa ---------------------------------------------

    def anonimizar_aba(
        self, df: pd.DataFrame, aba: str
    ) -> tuple[pd.DataFrame, list[EntradaLog], MetricasAba]:
        cfg = config.config_da_aba(aba)
        saida, log = self._transformar_colunas(df, aba)

        antes = metricas.medir_k_anonimato(saida, cfg.quase_identificadores)
        resultado_k = kanonimato.impor_k_anonimato(
            saida, cfg.quase_identificadores, self.k
        )
        saida = resultado_k.df
        depois = metricas.medir_k_anonimato(saida, cfg.quase_identificadores)

        for coluna in resultado_k.colunas_removidas:
            log.append(EntradaLog(aba, coluna, Risco.QUASE.value,
                                  "supressao_por_k_anonimato", None))

        resumo = MetricasAba(
            aba=aba,
            linhas=len(saida),
            colunas_entrada=len(df.columns),
            colunas_saida=len(saida.columns),
            colunas_suprimidas=sum(1 for e in log if e.destino is None),
            k_antes=antes.k,
            k_depois=depois.k,
            celulas_suprimidas_por_k=resultado_k.celulas_suprimidas,
            colunas_removidas_por_k=", ".join(resultado_k.colunas_removidas) or "-",
            registros_unicos_antes=antes.registros_unicos,
            l_diversidade=metricas.medir_l_diversidade(
                saida, cfg.quase_identificadores, cfg.sensiveis
            ),
        )
        return saida, log, resumo

    # -- etapa 3: planilha inteira -----------------------------------------

    def executar(self, livro: dict[str, pd.DataFrame]) -> Resultado:
        abas: dict[str, pd.DataFrame] = {}
        log: list[EntradaLog] = []
        resumos: list[MetricasAba] = []

        for nome, df in livro.items():
            anonimizada, log_aba, resumo = self.anonimizar_aba(df, nome)
            abas[nome] = anonimizada
            log.extend(log_aba)
            resumos.append(resumo)

        return Resultado(abas=abas, log=log, metricas=resumos, segredo=self.segredo)


# --------------------------------------------------------------------------
# Fachada
# --------------------------------------------------------------------------

def anonimizar_planilha(entrada: Path, saida: Path, k: int, epsilon: float) -> Resultado:
    """Lê, anonimiza e grava — incluindo as abas de auditoria."""
    livro = io_excel.ler_planilha(entrada)
    resultado = Anonimizador(Segredo.carregar(), k=k, epsilon=epsilon).executar(livro)

    io_excel.escrever_planilha(saida, {
        **resultado.abas,
        config.ABA_LOG: resultado.log_df(),
        config.ABA_METRICAS: resultado.metricas_df(),
    })
    return resultado
