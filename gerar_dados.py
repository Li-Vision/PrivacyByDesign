"""
Li-Vision — gerador de dataset sintético (dados fake).

Produz um Excel multi-aba reproduzindo a estrutura de dados que o Li-Vision
realmente coleta, derivada dos tipos em features/*/types.ts e services/.
Todos os dados são fictícios e gerados com seed fixa.

    python gerar_dados.py
    python gerar_dados.py --usuarios 500 --amostras 20000

A lógica vive em `livision_privacy.geracao`; este arquivo é só a CLI.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from livision_privacy import config, console, io_excel
from livision_privacy.geracao import gerar_planilha
from livision_privacy.geracao.sintetico import Volume

BASE = Path(__file__).parent


def main() -> None:
    console.configurar_encoding()

    parser = argparse.ArgumentParser(
        description="Gera o dataset sintético do Li-Vision."
    )
    parser.add_argument("--saida", default=config.ARQUIVO_BRUTO)
    parser.add_argument("--usuarios", type=int, default=120)
    parser.add_argument("--amostras", type=int, default=3000)
    parser.add_argument("--sessoes", type=int, default=800)
    args = parser.parse_args()

    print("Gerando dados sintéticos...")
    abas = gerar_planilha(Volume(
        usuarios=args.usuarios,
        amostras=args.amostras,
        sessoes=args.sessoes,
    ))

    destino = io_excel.resolver_caminho(args.saida, BASE)
    io_excel.escrever_planilha(destino, abas)

    console.tabela(
        ["aba", "linhas", "colunas"],
        [(nome, len(df), len(df.columns)) for nome, df in abas.items()],
        larguras=[24, 8, 9],
    )
    print(f"\nArquivo gerado: {destino}")


if __name__ == "__main__":
    main()
