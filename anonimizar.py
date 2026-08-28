"""
Li-Vision — pipeline de anonimização (LGPD).

Lê o Excel bruto, classifica cada coluna quanto ao risco de identificação,
aplica a técnica adequada e valida o resultado com métricas de privacidade.

    python anonimizar.py
    python anonimizar.py --entrada dados.xlsx --k 10 --epsilon 0.5

Técnicas (implementadas em `livision_privacy.tecnicas`):
    suprimir               Remove a coluna.
    pseudonimizar          HMAC-SHA256 com sal secreto; estável e irreversível.
    mascarar_*             Preserva formato, oculta conteúdo.
    generalizar_*          Reduz precisão (data → mês; cidade → região; IP → /16).
    faixa_etaria           Nascimento → faixa de 10 anos, com top-coding em 70+.
    agregar_espacial       lat/lon → grade de ~111 km.
    bucketizar             Numérico contínuo → faixas por quantil.
    ruido_laplace          Privacidade diferencial nas medidas biométricas.
    k-anonimato            Generaliza e suprime quase-identificadores raros.

A lógica vive no pacote `livision_privacy`; este arquivo é só a CLI.
"""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from livision_privacy import config, console, io_excel, pipeline

BASE = Path(__file__).parent


def _relatorio(resultado: pipeline.Resultado, k: int, epsilon: float,
               destino: Path) -> None:
    print(f"\nSal HMAC: {resultado.segredo.origem}")
    print(f"Parâmetros: k={k}, ε={epsilon}")

    console.contagem(
        "Colunas por classificação de risco:",
        dict(Counter(e.classe for e in resultado.log).most_common()),
    )
    console.contagem(
        "Técnicas aplicadas:",
        dict(Counter(e.tecnica for e in resultado.log).most_common()),
    )
    console.tabela(
        ["aba", "linhas", "cols", "suprim", "k antes", "k depois"],
        [(m.aba, m.linhas, m.colunas_saida, m.colunas_suprimidas,
          m.k_antes, m.k_depois) for m in resultado.metricas],
        larguras=[24, 8, 6, 8, 9, 10],
    )
    print(f"\nArquivo gerado: {destino}")


def main() -> None:
    console.configurar_encoding()

    parser = argparse.ArgumentParser(
        description="Anonimiza o dataset do Li-Vision (LGPD)."
    )
    parser.add_argument("--entrada", default=config.ARQUIVO_BRUTO)
    parser.add_argument("--saida", default=config.ARQUIVO_ANONIMIZADO)
    parser.add_argument("--k", type=int, default=config.K_ANONIMATO_PADRAO,
                        help="k mínimo de k-anonimato")
    parser.add_argument("--epsilon", type=float, default=config.EPSILON_PADRAO,
                        help="ε da privacidade diferencial (menor = mais privado)")
    args = parser.parse_args()

    entrada = io_excel.resolver_caminho(args.entrada, BASE)
    destino = io_excel.resolver_caminho(args.saida, BASE)

    try:
        print(f"Lendo {entrada.name}...")
        resultado = pipeline.anonimizar_planilha(
            entrada, destino, k=args.k, epsilon=args.epsilon
        )
    except FileNotFoundError:
        raise SystemExit(
            f"Arquivo não encontrado: {entrada}\nRode antes: python gerar_dados.py"
        )

    _relatorio(resultado, args.k, args.epsilon, destino)


if __name__ == "__main__":
    main()
