"""Fluxo ponta a ponta: coleta, Observer disparando State, e o handoff."""

import pytest

from celular_robo.excecoes import ErroColeta
from celular_robo.modos import ModoAguardandoVerificacao, ModoColetando
from celular_robo.observadores import DespachanteTransporte
from celular_robo.persistencia import (
    montar_pedido_de_json,
    montar_robo_de_json,
)
from celular_robo.robo import RoboTransportador


def test_observer_troca_o_modo_quando_a_bandeja_fica_pronta(coletor):
    """A transição não é decidida pelo modo — quem troca é a `EquipeDeTestes`.

    Não precisa coletar de verdade até encher a bandeja: basta injetar o
    evento, como no exercício de Observer do curso.
    """
    assert isinstance(coletor.modo, ModoColetando)

    coletor.notificar("bandeja_pronta", lote="Lote de Testes #482", unidades=3)

    assert isinstance(coletor.modo, ModoAguardandoVerificacao)
    assert coletor.equipe.aguardando


def test_modo_aguardando_recusa_pedido_novo(coletor, pedido_simples):
    coletor.notificar("bandeja_pronta", lote="Lote de Testes #482", unidades=3)
    with pytest.raises(ErroColeta):
        coletor.carregar_pedido(pedido_simples)


def test_pedido_completo_ate_a_aprovacao(coletor, pedido_simples):
    coletor.carregar_pedido(pedido_simples)
    coletadas = coletor.processar_pedido()

    assert coletadas == pedido_simples.total_unidades
    assert len(coletor.bandeja) == 3
    assert coletor.bandeja.completa
    assert coletor.posicao == (7, 2)
    assert isinstance(coletor.modo, ModoAguardandoVerificacao)

    conteudo = coletor.equipe.aprovar(coletor)

    assert {item.codinome for item in conteudo} == set(pedido_simples.codinomes)
    assert len(coletor.bandeja) == 0
    assert isinstance(coletor.modo, ModoColetando)
    assert coletor.equipe.aprovados == ["Lote de Testes #482"]


def test_lote_rejeitado_mantem_os_itens_na_bandeja(coletor, pedido_simples):
    coletor.carregar_pedido(pedido_simples)
    coletor.processar_pedido()

    coletor.equipe.rejeitar(coletor, "embalagem violada")

    assert isinstance(coletor.modo, ModoColetando)
    assert len(coletor.bandeja) == 3
    assert coletor.equipe.rejeitados == [
        ("Lote de Testes #482", "embalagem violada")
    ]
    assert coletor.auditoria.por_evento("lote_rejeitado")


def test_desfazer_devolve_o_item_e_reabre_a_bandeja(coletor, pedido_simples):
    coletor.carregar_pedido(pedido_simples)
    coletor.processar_pedido()
    assert isinstance(coletor.modo, ModoAguardandoVerificacao)

    comando = coletor.desfazer_ultima_coleta()

    assert comando.codinome == "Projeto Cobalto"
    assert coletor.bandeja.quantidade_de("Projeto Cobalto") == 0
    assert len(coletor.bandeja) == 2
    assert isinstance(coletor.modo, ModoColetando)


def test_auditoria_registra_todos_os_eventos(coletor, pedido_simples):
    coletor.carregar_pedido(pedido_simples)
    coletor.processar_pedido()
    coletor.equipe.aprovar(coletor)

    eventos = [linha.evento for linha in coletor.auditoria]
    assert eventos.count("item_coletado") == len(pedido_simples)
    assert "bandeja_pronta" in eventos
    assert "lote_aprovado" in eventos
    assert all(linha.robo == coletor.nome for linha in coletor.auditoria)


def test_rota_com_dupla_conferencia_confere_antes_e_depois(
    coletor_cuidadoso, pedido_fragil
):
    coletor_cuidadoso.carregar_pedido(pedido_fragil)
    coletor_cuidadoso.processar_pedido()

    conferencias = coletor_cuidadoso.auditoria.por_evento("item_conferido")
    assert len(conferencias) == 2 * len(pedido_fragil)
    assert {linha.dados["etapa"] for linha in conferencias} == {
        "antes da sucção", "antes de depositar",
    }


def test_handoff_do_coletor_para_o_transportador(coletor, pedido_simples):
    """Extensão opcional (Seção 7): aprovar o lote dispara o transportador."""
    despachante = DespachanteTransporte()
    coletor.adicionar_observador(despachante)

    coletor.carregar_pedido(pedido_simples)
    coletor.processar_pedido()
    coletor.equipe.aprovar(coletor)

    assert despachante.entregas == [{"Projeto Aurora": 2, "Projeto Cobalto": 1}]
    assert type(despachante.transportador).__name__ == "RoboTransportador"
    assert despachante.transportador.posicao == RoboTransportador.PONTO_DE_RETIRADA
    assert coletor.auditoria.por_evento("carga_entregue")


def test_fluxo_a_partir_dos_arquivos_de_dados():
    """Os JSONs de `dados/` sobem um robô e um pedido válidos (Seção 2.6)."""
    robo = montar_robo_de_json()
    pedido = montar_pedido_de_json()

    robo.carregar_pedido(pedido)
    robo.processar_pedido()

    assert robo.nome == "Coletor-1"
    assert robo.bandeja.completa
    assert isinstance(robo.modo, ModoAguardandoVerificacao)
