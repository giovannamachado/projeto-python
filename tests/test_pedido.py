"""Testes do conteúdo do pedido e das regras de `requires` (Seção 2.7)."""

import pytest

from celular_robo.excecoes import ConfiguracaoInvalida, ErroColeta, PedidoInvalido
from celular_robo.modelo_features import validar_pedido
from celular_robo.pedido import ItemPedido, Pedido
from celular_robo.robo import Bandeja

LOTE = "Lote de Testes #482"


def test_codinome_inexistente_e_recusado(estoque):
    pedido = Pedido(LOTE, [ItemPedido("Projeto Fantasma", 1, (2, 2))])
    with pytest.raises(PedidoInvalido):
        validar_pedido(pedido, estoque)


def test_quantidade_maior_que_o_disponivel_e_recusada(estoque):
    pedido = Pedido(LOTE, [ItemPedido("Projeto Miragem", 2, (2, 8))])
    with pytest.raises(PedidoInvalido):
        validar_pedido(pedido, estoque)


def test_pedido_vazio_e_recusado(estoque):
    with pytest.raises(PedidoInvalido):
        validar_pedido(Pedido(LOTE, []), estoque)


def test_item_fragil_e_urgente_e_recusado(estoque):
    """O conflito é do item, não da configuração: `fragil` e `urgente` no
    mesmo item se contradizem sem que exista robô nenhum envolvido, então
    quem recusa é `PedidoInvalido`.
    """
    pedido = Pedido(LOTE, [
        ItemPedido("Projeto Vesper", 1, (7, 2), fragil=True, urgente=True),
    ])
    with pytest.raises(PedidoInvalido):
        validar_pedido(pedido, estoque)


def test_pedido_que_mistura_fragil_e_urgente_em_itens_diferentes(estoque):
    """Um robô tem uma rota só — o pedido inteiro é recusado antes de coletar."""
    pedido = Pedido(LOTE, [
        ItemPedido("Projeto Aurora", 1, (3, 4), urgente=True),
        ItemPedido("Projeto Vesper", 1, (7, 2), fragil=True),
    ])
    with pytest.raises(PedidoInvalido):
        validar_pedido(pedido, estoque)


def test_pedido_misto_e_recusado_inteiro(coletor, estoque):
    """Atomicidade: um item inválido derruba o pedido, nada é coletado."""
    pedido = Pedido(LOTE, [
        ItemPedido("Projeto Aurora", 1, (3, 4)),
        ItemPedido("Projeto Fantasma", 1, (2, 2)),
    ])
    with pytest.raises(PedidoInvalido):
        validar_pedido(pedido, estoque)
    assert len(coletor.bandeja) == 0


def test_item_fragil_exige_dupla_conferencia(coletor, pedido_fragil):
    """`requires`: a rota direta não carrega protótipo frágil."""
    with pytest.raises(ConfiguracaoInvalida):
        coletor.carregar_pedido(pedido_fragil)


def test_item_fragil_passa_na_rota_com_dupla_conferencia(
    coletor_cuidadoso, pedido_fragil
):
    coletor_cuidadoso.carregar_pedido(pedido_fragil)
    assert coletor_cuidadoso.pedido is pedido_fragil
    assert "Projeto Vesper" in coletor_cuidadoso.bandeja


def test_item_com_json_malformado_e_recusado():
    with pytest.raises(PedidoInvalido):
        ItemPedido.de_dict({"codinome": "Projeto Aurora", "posicao": [3]})
    with pytest.raises(PedidoInvalido):
        ItemPedido.de_dict({"codinome": "", "quantidade": 1, "posicao": [3, 4]})
    with pytest.raises(PedidoInvalido):
        ItemPedido.de_dict(
            {"codinome": "Projeto Aurora", "quantidade": 0, "posicao": [3, 4]}
        )


def test_posicao_fora_da_grade_e_recusada(estoque):
    pedido = Pedido(LOTE, [ItemPedido("Projeto Aurora", 1, (12, 3))])
    with pytest.raises(PedidoInvalido):
        validar_pedido(pedido, estoque)


def test_descriptor_de_quantidade_protege_a_bandeja():
    """`QuantidadeValida`: nunca negativa, nunca acima do solicitado."""
    bandeja = Bandeja()
    bandeja.reservar("Projeto Aurora", 2)

    bandeja.guardar("Projeto Aurora", 2)
    assert len(bandeja) == 2
    assert bandeja.completa

    with pytest.raises(ValueError):
        bandeja.guardar("Projeto Aurora", 1)
    with pytest.raises(ValueError):
        bandeja.retirar("Projeto Aurora", 3)
    assert len(bandeja) == 2


def test_bandeja_recusa_codinome_fora_do_pedido():
    bandeja = Bandeja()
    with pytest.raises(PedidoInvalido):
        bandeja.guardar("Projeto Fantasma")


def test_hierarquia_de_excecoes_permite_tratamento_conjunto(estoque):
    """Um `except ErroColeta` pega os dois lados da hierarquia (Seção 2.5)."""
    assert issubclass(PedidoInvalido, ErroColeta)
    assert issubclass(ConfiguracaoInvalida, ErroColeta)
    with pytest.raises(ErroColeta):
        validar_pedido(Pedido(LOTE, []), estoque)
