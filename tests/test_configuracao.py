"""Testes do modelo de features e da fábrica (enunciado, Seção 2.7)."""

import itertools

import pytest

from celular_robo.estrategias import RotaColeta
from celular_robo.excecoes import ConfiguracaoInvalida
from celular_robo.fabrica import criar_robo_configurado
from celular_robo.modelo_features import (
    AREAS_VALIDAS,
    ESTRATEGIAS_VALIDAS,
    FABRICA_ROTAS,
    TIPOS_VALIDOS,
    validar_configuracao,
)
from celular_robo.robo_base import Direcao, Robo

CASOS = list(itertools.product(
    sorted(TIPOS_VALIDOS), sorted(ESTRATEGIAS_VALIDAS), sorted(AREAS_VALIDAS)
))


@pytest.mark.parametrize("tipo_nome,estrategia_nome,area_nome", CASOS)
def test_contrato_criar_ou_recusar(tipo_nome, estrategia_nome, area_nome):
    """Toda combinação ou produz o robô exato pedido, ou é recusada.

    Mesmo espírito do exercício avançado da Aula 16: o teste não confere só
    "válido/inválido", confere o contrato inteiro — tipo, rota e área do robô
    resultante. Como os três conjuntos vêm dos registros, um tipo ou uma rota
    nova entram nesta suíte sem nenhuma linha a mais.
    """
    try:
        validar_configuracao(tipo_nome, estrategia_nome, area_nome)
        combinacao_valida = True
    except ConfiguracaoInvalida:
        combinacao_valida = False

    if not combinacao_valida:
        with pytest.raises(ConfiguracaoInvalida):
            criar_robo_configurado(
                tipo_nome, "Teste",
                estrategia_nome=estrategia_nome, area_nome=area_nome,
            )
        return

    robo = criar_robo_configurado(
        tipo_nome, "Teste",
        estrategia_nome=estrategia_nome, area_nome=area_nome,
    )
    assert type(robo).__name__ == tipo_nome
    assert type(robo.estrategia) is FABRICA_ROTAS[estrategia_nome]
    assert robo.area_nome == area_nome
    # A área não é só um rótulo: ela decide o `robo.obstaculos`.
    assert bool(robo.obstaculos) == (area_nome == "area_quarentena")


def test_conjuntos_validos_vem_dos_registros():
    """Nada em `TIPOS_VALIDOS`/`ESTRATEGIAS_VALIDAS` é digitado à mão."""
    assert TIPOS_VALIDOS == set(Robo._registro)
    assert ESTRATEGIAS_VALIDAS == set(RotaColeta._registro_rotas)
    assert "RoboColetor" in TIPOS_VALIDOS
    # As estratégias de movimentação do curso ficam de fora do modelo.
    assert ESTRATEGIAS_VALIDAS.isdisjoint({"padrao", "esquiva", "zigzag"})


def test_rota_desconhecida_e_recusada():
    with pytest.raises(ConfiguracaoInvalida):
        criar_robo_configurado("RoboColetor", "X", estrategia_nome="zigzag")


def test_corredor_de_quarentena_bloqueia_de_fato():
    """A área de quarentena tem obstáculo real, não uma barreira decorativa."""
    robo = criar_robo_configurado(
        "RoboColetor", "Coletor-Q",
        estrategia_nome="dupla_conferencia", area_nome="area_quarentena",
        x=4, y=3,
    )
    assert robo.obstaculos
    assert robo.direcao is Direcao.LESTE
    assert (5, 3) in robo.obstaculos
    assert robo.sensor_frente() is False
    assert robo.avancar() is False
    assert robo.posicao == (4, 3)


def test_transportador_nao_entra_na_quarentena():
    """`excludes` da extensão opcional (Seção 7)."""
    with pytest.raises(ConfiguracaoInvalida):
        criar_robo_configurado(
            "RoboTransportador", "Transportador-Q",
            estrategia_nome="dupla_conferencia", area_nome="area_quarentena",
        )
