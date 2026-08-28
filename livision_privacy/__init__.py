"""
livision_privacy — geração de dados sintéticos e anonimização (LGPD) do Li-Vision.

Organização por responsabilidade:

    config.py       Parâmetros e constantes. Nenhuma lógica.
    console.py      Encoding do terminal e formatação de relatório.
    io_excel.py     Leitura/escrita de planilhas. Único módulo que conhece openpyxl.
    classificacao.py Decide O QUE cada coluna é (risco) e QUAL técnica aplicar.
    tecnicas.py     Implementa COMO transformar um valor. Funções puras.
    registry.py     Liga o nome da técnica à sua implementação. Sem if/elif.
    metricas.py     Mede privacidade (k-anonimato, l-diversidade).
    kanonimato.py   Impõe k-anonimato.
    pipeline.py     Orquestra as etapas acima. Não implementa nenhuma delas.
    geracao/        Produção do dataset sintético (dados fake).

A regra que guia a divisão: `tecnicas` não sabe o que é uma aba, `classificacao`
não sabe transformar valores, e `pipeline` não sabe como uma técnica funciona.
"""

__version__ = "2.0.0"
