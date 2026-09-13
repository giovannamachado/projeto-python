"""Fixtures compartilhadas pelos testes do projeto."""

import pytest

from celular_robo.fabrica import criar_robo_configurado
from celular_robo.pedido import ItemPedido, Pedido

LOTE = "Lote de Testes #482"


@pytest.fixture
def estoque() -> dict[str, int]:
    """Inventário do lote usado nos testes, no mesmo formato de `carregar_lote`."""
    return {
        "Projeto Aurora": 4,
        "Projeto Vesper": 2,
        "Projeto Cobalto": 3,
        "Projeto Miragem": 1,
    }


@pytest.fixture
def coletor():
    """Robô com rota direta no centro de testes padrão."""
    return criar_robo_configurado(
        "RoboColetor", "Coletor-Teste",
        estrategia_nome="direta", area_nome="centro_padrao",
    )


@pytest.fixture
def coletor_cuidadoso():
    """Robô com dupla conferência — o único que aceita itens frágeis."""
    return criar_robo_configurado(
        "RoboColetor", "Coletor-Cuidadoso",
        estrategia_nome="dupla_conferencia", area_nome="centro_padrao",
    )


@pytest.fixture
def pedido_simples() -> Pedido:
    return Pedido(LOTE, [
        ItemPedido("Projeto Aurora", 2, (3, 4), urgente=True),
        ItemPedido("Projeto Cobalto", 1, (7, 2)),
    ])


@pytest.fixture
def pedido_fragil() -> Pedido:
    return Pedido(LOTE, [
        ItemPedido("Projeto Vesper", 1, (7, 2), fragil=True),
    ])
