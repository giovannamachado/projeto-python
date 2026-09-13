"""Hierarquia de exceções do robô coletor — enunciado, Seção 2.5.

Uma base comum (`ErroColeta`) e duas especializações permitem que quem chama
escolha o nível de granularidade: `except ErroColeta` pega qualquer problema do
domínio, enquanto `except PedidoInvalido` trata só o que veio errado no pedido.
"""


class ErroColeta(Exception):
    """Base de todos os erros do domínio de coleta."""


class ConfiguracaoInvalida(ErroColeta):
    """Combinação inválida de tipo de robô, rota de coleta e área.

    Levantada pelo modelo de features (`modelo_features.validar_configuracao`)
    *antes* de qualquer robô ser instanciado, e também quando a rota configurada
    no robô não atende às exigências dos itens de um pedido (`requires`).
    """


class PedidoInvalido(ErroColeta):
    """Problema no conteúdo do pedido de coleta em si.

    Codinome ausente do lote, quantidade maior que a disponível, pedido vazio ou
    item internamente contraditório (`fragil` e `urgente` ao mesmo tempo).
    """
