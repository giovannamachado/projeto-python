"""Fluxo ponta a ponta: coleta, Observer disparando State, e o handoff."""

import pytest

from celular_robo.excecoes import ErroColeta, PedidoInvalido
from celular_robo.fabrica import criar_robo_configurado
from celular_robo.modos import ModoAguardandoVerificacao, ModoColetando
from celular_robo.observadores import DespachanteTransporte
from celular_robo.pedido import ItemPedido, Pedido
from celular_robo.persistencia import (
    montar_pedido_de_json,
    montar_robo_de_json,
    salvar_auditoria,
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


def test_reprocessar_depois_de_desfazer_nao_duplica(coletor, pedido_simples):
    """Desfazer e processar de novo recoleta só o item devolvido."""
    coletor.carregar_pedido(pedido_simples)
    coletor.processar_pedido()
    coletor.desfazer_ultima_coleta()
    assert len(coletor.bandeja) == 2

    recoletadas = coletor.processar_pedido()

    assert recoletadas == 1
    assert len(coletor.bandeja) == pedido_simples.total_unidades
    assert coletor.bandeja.completa
    assert isinstance(coletor.modo, ModoAguardandoVerificacao)


def test_processar_de_novo_retoma_do_item_que_falhou():
    """Um item inalcançável não faz o pedido recomeçar do zero na 2ª tentativa."""
    coletor = criar_robo_configurado(
        "RoboColetor", "Coletor-Quarentena",
        estrategia_nome="dupla_conferencia", area_nome="area_quarentena",
    )
    # (5, 3) fica dentro do corredor de quarentena, que é obstáculo.
    pedido = Pedido("Lote de Testes #482", [
        ItemPedido("Projeto Vesper", 1, (7, 2), fragil=True),
        ItemPedido("Projeto Miragem", 1, (5, 3), fragil=True),
    ])
    coletor.carregar_pedido(pedido)

    with pytest.raises(PedidoInvalido):
        coletor.processar_pedido()
    assert len(coletor.bandeja) == 1

    # A segunda tentativa falha no mesmo item, sem recoletar o primeiro.
    with pytest.raises(PedidoInvalido):
        coletor.processar_pedido()
    assert coletor.bandeja.quantidade_de("Projeto Vesper") == 1
    assert len(coletor.bandeja) == 1


def test_aprovar_esvazia_a_pilha_de_desfazer(coletor, pedido_simples):
    """Com o lote entregue não há coleta a desfazer — o erro é de domínio."""
    coletor.carregar_pedido(pedido_simples)
    coletor.processar_pedido()
    coletor.equipe.aprovar(coletor)

    with pytest.raises(ErroColeta):
        coletor.desfazer_ultima_coleta()


def test_salvar_auditoria_em_caminho_invalido_vira_erro_de_dominio(coletor, tmp_path):
    """Falha de escrita vira `ErroColeta`, que é o que a CLI sabe mostrar."""
    arquivo = tmp_path / "ocupado"
    arquivo.write_text("não sou diretório", encoding="utf-8")

    with pytest.raises(ErroColeta):
        salvar_auditoria(coletor.auditoria, arquivo / "trilha.json")
